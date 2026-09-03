"""nexportal-gate — the CLI.

  intake "<text>" --requester R   the door: triage a raw request, file it (or flag the duplicate)
  draft <n>                       Triaged → Drafted: fill the DoR form from the intake record
  gate <n> | --file <spec.md>     before refinement: Tier 1 + Tier 2, post the NX-GATE record
  flip <n> <Status>               the guarded door: refuses Ready without a fresh record (exit 3)
  audit                           Ready items without a fresh record (the door that can't be locked)
  fixtures [--replay|--record]    the six pre-registered cases → fixtures/results.md
  board-ids --owner O --project N render board.toml from the live project
Exit codes: 0 ok · 1 error · 2 usage · 3 refused.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from . import adversary, board, draft, fixtures as fx, records
from .adversary import AdversaryError, ClaudeCodeClient, RecordingClient, ReplayClient, run_gate
from .board import BoardError
from .intake import run_intake

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _root() -> Path:
    return Path.cwd() if (Path.cwd() / "prompts").is_dir() else PACKAGE_ROOT


def _add_common(p: argparse.ArgumentParser, *, llm=True, github=True):
    p.add_argument("--repo", help="owner/name (default: the current gh repo)")
    p.add_argument("--board", default="board.toml", help="board identifiers (default: board.toml)")
    p.add_argument("--dry-run", action="store_true", help="print what would be posted; write nothing")
    if llm:
        p.add_argument("--model", default=adversary.DEFAULT_MODEL)
        p.add_argument("--replay", action="store_true", help="use recorded responses (no Claude Code)")
        p.add_argument("--record", action="store_true", help="run live and save the responses")
        p.add_argument("--recorded-dir", default=None, help="default: fixtures/recorded")
        p.add_argument("--prompts", default=None, help="default: prompts/")
        p.add_argument("--context", default=None, help="default: context/platform.md")


def _paths(args):
    root = _root()
    prompts = Path(args.prompts) if args.prompts else root / "prompts"
    context = Path(args.context) if args.context else root / "context" / "platform.md"
    recorded = Path(args.recorded_dir) if args.recorded_dir else root / "fixtures" / "recorded"
    return root, prompts, context.read_text(encoding="utf-8"), recorded


def _client(args, prompts: Path, recorded: Path):
    if args.replay:
        return ReplayClient(recorded)
    live = ClaudeCodeClient(model=args.model)
    if args.record:
        version = adversary.prompt_version(adversary.load_prompt("system.md", prompts))
        return RecordingClient(live, recorded, model=args.model, prompt_version=version)
    return live


def _repo(args, gh) -> str:
    if args.repo:
        return args.repo
    return gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()


def _title(text: str) -> str:
    first = re.split(r"(?<=[.?!])\s", text.strip(), maxsplit=1)[0].rstrip(".?!")
    return first[:72].rstrip() if len(first) > 72 else first


# --- commands -----------------------------------------------------------------------------------

def cmd_fixtures(args) -> int:
    root, prompts, platform, recorded = _paths(args)
    fixtures_dir = Path(args.fixtures) if args.fixtures else root / "fixtures"
    open_issues = json.loads((fixtures_dir / "open-issues.json").read_text(encoding="utf-8"))
    rows = fx.run_all(_client(args, prompts, recorded), fixtures_dir=fixtures_dir, prompts_dir=prompts,
                      platform=platform, open_issues=open_issues, model=args.model, only=args.only)
    readings_path = fixtures_dir / "readings.json"
    readings = json.loads(readings_path.read_text(encoding="utf-8")) if readings_path.exists() else {}
    table = fx.render_results(rows, readings)
    out = Path(args.out) if args.out else fixtures_dir / "results.md"
    if not args.only:
        out.write_text(table, encoding="utf-8")
    print(table, end="")
    return 0


def cmd_gate(args) -> int:
    root, prompts, platform, recorded = _paths(args)
    client = _client(args, prompts, recorded)
    if args.file:
        meta, body = fx.split_frontmatter(Path(args.file).read_text(encoding="utf-8"))
        key = meta.get("id") or Path(args.file).stem
        result = run_gate(body, client, key=key, prompts_dir=prompts, platform=platform, model=args.model)
        print(records.render_gate_comment(result, issue=0), end="")
        return 0
    if args.issue is None:
        print("gate: an issue number or --file is required", file=sys.stderr)
        return 2
    gh, n = board.gh_run, args.issue
    repo = _repo(args, gh)
    iss = board.issue(gh, repo, n)
    result = run_gate(iss["body"], client, key=f"issue-{n}", prompts_dir=prompts, platform=platform, model=args.model)
    text = records.render_gate_comment(result, issue=n)
    if args.dry_run:
        print(text, end="")
        return 0
    board.comment(gh, repo, n, text)
    cfg = board.load_board(Path(args.board))
    item = board.project_item(gh, cfg, repo, n)
    if item["id"]:
        board.set_field(gh, cfg, item["id"], "reason", option="Needs-info" if result.verdict == "needs-info" else None)
    print(f"gate: #{n} → {result.verdict}" + (f" — {'; '.join(result.reasons)}" if result.reasons else ""))
    return 0


def cmd_intake(args) -> int:
    root, prompts, platform, recorded = _paths(args)
    client = _client(args, prompts, recorded)
    weekday = args.weekday or dt.date.today().strftime("%A")
    gh = board.gh_run
    if args.open_issues:
        open_issues, repo = json.loads(Path(args.open_issues).read_text(encoding="utf-8")), args.repo or ""
    else:
        repo = _repo(args, gh)
        open_issues = board.open_issues(gh, repo)
    result = run_intake(args.text, args.requester, open_issues, client, key=args.key or "intake",
                        prompts_dir=prompts, platform=platform, model=args.model, weekday=weekday)
    comment_text = records.render_intake_comment(result, requester=args.requester, text=args.text)
    if result.status == "rejected":
        for f in result.failures:
            print(f"intake: rejected at the door — {f.check}: {f.message}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(comment_text, end="")
        return 0
    message = (result.tier2 or {}).get("requester_message", "")
    if result.status == "duplicate":
        board.comment(gh, repo, result.duplicate_of, comment_text)
        print(f"intake: duplicate of #{result.duplicate_of} — no issue created\n\n{message}")
        return 0
    body = f"{args.text.strip()}\n\n— requested by @{args.requester} via `nexportal-gate intake` ({weekday})\n"
    n = board.create_issue(gh, repo, _title(args.text), body)
    board.comment(gh, repo, n, comment_text)
    cfg = board.load_board(Path(args.board))
    item_id = board.add_to_project(gh, cfg, repo, n)
    board.set_field(gh, cfg, item_id, "status", option="Triaged")
    band = ((result.tier2 or {}).get("size") or {}).get("band")
    if band:
        board.set_field(gh, cfg, item_id, "size", option=band)
    board.set_field(gh, cfg, item_id, "requester", text=f"@{args.requester}")
    print(f"intake: #{n} filed → Triaged\n\n{message}")
    return 0


def cmd_draft(args) -> int:
    gh, n = board.gh_run, args.issue
    repo = _repo(args, gh)
    iss = board.issue(gh, repo, n)
    rec = records.newest_record(iss["comments"], records.INTAKE_MARKER)
    if rec is None:
        print(f"draft: no NX-INTAKE record on #{n} — run `nexportal-gate intake` first", file=sys.stderr)
        return 1
    body = draft.render_draft(rec, title=iss["title"])
    if args.dry_run:
        print(body, end="")
        return 0
    board.set_body(gh, repo, n, body)
    cfg = board.load_board(Path(args.board))
    item = board.project_item(gh, cfg, repo, n)
    if item["id"]:
        board.set_field(gh, cfg, item["id"], "status", option="Drafted")
    print(f"draft: #{n} → Drafted ({len((rec.get('tier2') or {}).get('questions') or [])} open questions ride the body)")
    return 0


def cmd_flip(args) -> int:
    gh = board.gh_run
    return board.flip(gh, board.load_board(Path(args.board)), _repo(args, gh), args.issue, args.status)


def cmd_audit(args) -> int:
    gh = board.gh_run
    lines = board.audit(gh, board.load_board(Path(args.board)), _repo(args, gh))
    if not lines:
        print("audit: clean — every Ready item has a fresh NX-GATE record")
        return 0
    print("\n".join(lines))
    return 1


def cmd_board_ids(args) -> int:
    print(board.board_ids(board.gh_run, args.owner, args.project), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="nexportal-gate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake", help="triage a raw request at the door")
    p.add_argument("text")
    p.add_argument("--requester", required=True)
    p.add_argument("--weekday", default=None)
    p.add_argument("--open-issues", default=None, help="a JSON file instead of the live repo (offline)")
    p.add_argument("--key", default=None, help="replay/record key (default: intake)")
    _add_common(p)
    p.set_defaults(fn=cmd_intake)

    p = sub.add_parser("draft", help="fill the DoR form from the intake record")
    p.add_argument("issue", type=int)
    _add_common(p, llm=False)
    p.set_defaults(fn=cmd_draft)

    p = sub.add_parser("gate", help="judge a drafted spec")
    p.add_argument("issue", type=int, nargs="?")
    p.add_argument("--file", default=None, help="judge a spec file offline and print the record")
    _add_common(p)
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("flip", help="move a card — the guarded door")
    p.add_argument("issue", type=int)
    p.add_argument("status", choices=board.STATUSES)
    _add_common(p, llm=False)
    p.set_defaults(fn=cmd_flip)

    p = sub.add_parser("audit", help="Ready items without a fresh record")
    _add_common(p, llm=False)
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("fixtures", help="run the six pre-registered cases")
    p.add_argument("--only", nargs="*", default=None, help="fixture ids to run")
    p.add_argument("--fixtures", default=None, help="default: fixtures/")
    p.add_argument("--out", default=None, help="default: fixtures/results.md")
    _add_common(p, github=False)
    p.set_defaults(fn=cmd_fixtures)

    p = sub.add_parser("board-ids", help="render board.toml from the live project")
    p.add_argument("--owner", required=True)
    p.add_argument("--project", required=True, type=int)
    p.set_defaults(fn=cmd_board_ids)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (AdversaryError, BoardError) as exc:
        print(f"{args.cmd}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
