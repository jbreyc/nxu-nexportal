"""board — the GitHub plumbing (injectable `gh`) and the one guarded door.

Every read and write of the board goes through here: the issue read (body + comments), create /
comment / edit, the per-issue project item (GraphQL, user-owned project), the single field write
(`gh project item-edit`), and `flip` — the only sanctioned way Status changes. `check_flip` is THE
rule: a `Ready` flip needs the newest `NX-GATE:` record to say `ready` and to carry the hash of the
body as it is now. A refusal writes nothing and names the command that would fix it. `audit` lists
Ready items that would fail the rule — the door that cannot be locked (the web UI) is at least
visible.

`gh` is always injected as a callable — `gh(argv, *, stdin=None) -> stdout` — so every path is
unit-testable with no live GitHub (the factory's seam, reimplemented).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from collections import namedtuple
from pathlib import Path

from . import records
from .text import body_hash, sections

STATUSES = ("Inbox", "Triaged", "Drafted", "Ready", "In Sprint", "Done")
FIELD_NAMES = {"status": "Status", "reason": "Reason", "size": "Size", "requester": "Requester"}


class BoardError(Exception):
    pass


def gh_run(argv: list[str], *, stdin: str | None = None) -> str:
    """The default `gh`: run `<GH_BIN> <argv…>`, return stdout, raise loud on a non-zero exit."""
    proc = subprocess.run([os.environ.get("GH_BIN", "gh"), *argv], capture_output=True, text=True, input=stdin)
    if proc.returncode != 0:
        raise BoardError(f"gh {' '.join(argv[:3])} … failed ({proc.returncode}): {proc.stderr.strip()[:400]}")
    return proc.stdout


def _json(out):
    return out if isinstance(out, (dict, list)) else json.loads(out)


def load_board(path: Path = Path("board.toml")) -> dict:
    path = Path(path)
    if not path.exists():
        raise BoardError(f"{path} not found — run `nexportal-gate board-ids --owner <o> --project <n> > board.toml`")
    return tomllib.loads(path.read_text(encoding="utf-8"))


# --- issues -------------------------------------------------------------------------------------

def issue(gh, repo: str, number: int) -> dict:
    data = _json(gh(["issue", "view", str(number), "--repo", repo, "--json", "number,title,body,state,comments"]))
    data["comments"] = [{"body": c.get("body", ""), "createdAt": c.get("createdAt", "")}
                        for c in data.get("comments") or []]
    return data


def create_issue(gh, repo: str, title: str, body: str) -> int:
    out = gh(["issue", "create", "--repo", repo, "--title", title, "--body-file", "-"], stdin=body)
    url = out.strip().split("\n")[-1]
    try:
        return int(url.rstrip("/").rsplit("/", 1)[1])
    except (ValueError, IndexError):
        raise BoardError(f"could not parse the issue number from: {out.strip()!r}") from None


def comment(gh, repo: str, number: int, body: str) -> None:
    gh(["issue", "comment", str(number), "--repo", repo, "--body-file", "-"], stdin=body)


def set_body(gh, repo: str, number: int, body: str) -> None:
    gh(["issue", "edit", str(number), "--repo", repo, "--body-file", "-"], stdin=body)


def _outcome_of(item: dict) -> str:
    rec = records.newest_record(item.get("comments") or [], records.INTAKE_MARKER)
    if rec and (rec.get("tier2") or {}).get("outcome"):
        return rec["tier2"]["outcome"]
    return sections(item.get("body") or "").get("outcome", "").strip()


def open_issues(gh, repo: str) -> list[dict]:
    """What intake dedupes against: number, title, and the outcome (newest intake record, else the
    body's Outcome section, else empty)."""
    items = _json(gh(["issue", "list", "--repo", repo, "--state", "open", "--limit", "100",
                      "--json", "number,title,body,comments"]))
    return [{"number": i["number"], "title": i.get("title", ""), "outcome": _outcome_of(i)} for i in items]


# --- the project item and the field write --------------------------------------------------------

_ISSUE_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      state
      projectItems(first: 20) {
        nodes {
          id
          project { number }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
          reason: fieldValueByName(name: "Reason") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
        }
      }
    }
  }
}
"""


def project_item(gh, cfg: dict, repo: str, number: int) -> dict:
    """The per-issue read (authoritative for one issue; `item-list` lags): the node on OUR board."""
    owner, name = repo.split("/", 1)
    data = _json(gh(["api", "graphql", "-f", "query=" + _ISSUE_QUERY, "-F", f"owner={owner}",
                     "-F", f"name={name}", "-F", f"number={number}"]))
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    nodes = ((((data.get("repository") or {}).get("issue") or {}).get("projectItems") or {}).get("nodes")) or []
    for n in nodes:
        if ((n.get("project") or {}).get("number")) == cfg["project_number"]:
            return {"id": n.get("id") or "", "status": ((n.get("status") or {}).get("name")) or "",
                    "reason": ((n.get("reason") or {}).get("name")) or ""}
    return {"id": "", "status": "", "reason": ""}


def add_to_project(gh, cfg: dict, repo: str, number: int) -> str:
    out = _json(gh(["project", "item-add", str(cfg["project_number"]), "--owner", cfg["owner"],
                    "--url", f"https://github.com/{repo}/issues/{number}", "--format", "json"]))
    return out.get("id") or ""


def set_field(gh, cfg: dict, item_id: str, field: str, option: str | None = None, text: str | None = None) -> None:
    """The one field write: a single-select option, `--clear`, or a text value."""
    try:
        field_id = cfg["fields"][field]
    except KeyError:
        raise BoardError(f"no field id for {field!r} in board.toml") from None
    argv = ["project", "item-edit", "--id", item_id, "--project-id", cfg["project_id"], "--field-id", field_id]
    if text is not None:
        argv += ["--text", text]
    elif option is None:
        argv.append("--clear")
    else:
        opt = ((cfg.get("options") or {}).get(field) or {}).get(option)
        if not opt:
            raise BoardError(f"no option id for {field}={option!r} in board.toml")
        argv += ["--single-select-option-id", opt]
    gh(argv)


# --- the rule, the door, the audit --------------------------------------------------------------

Decision = namedtuple("Decision", "allowed reason")


def check_flip(current_body: str, comments: list[dict]) -> Decision:
    """No Ready without a fresh gate record: newest `NX-GATE:` says `ready` AND its hash is the body's."""
    rec = records.newest_record(comments, records.GATE_MARKER)
    if rec is None:
        return Decision(False, "no NX-GATE record on the trail")
    if rec.get("verdict") != "ready":
        return Decision(False, f"newest NX-GATE record says {rec.get('verdict')}")
    now, then = body_hash(current_body), rec.get("body_sha256") or ""
    if then != now:
        return Decision(False, f"newest NX-GATE record (ready) judged a different body: {then[:8]} ≠ {now[:8]}")
    return Decision(True, f"fresh NX-GATE record {now[:8]}")


def flip(gh, cfg: dict, repo: str, number: int, status: str) -> int:
    """The guarded door. 0 written · 3 refused (nothing written) · BoardError on a gh failure."""
    if status not in (cfg.get("options") or {}).get("status", {}):
        raise BoardError(f"unknown status {status!r} — one of: {', '.join(cfg['options']['status'])}")
    item = project_item(gh, cfg, repo, number)
    if not item["id"]:
        raise BoardError(f"issue #{number} is not on project #{cfg['project_number']}'s board")
    if status == "Ready":
        iss = issue(gh, repo, number)
        decision = check_flip(iss["body"], iss["comments"])
        if not decision.allowed:
            print(f"flip: REFUSED #{number} → Ready — {decision.reason} — run: nexportal-gate gate {number}",
                  file=sys.stderr)
            return 3
        print(f"flip: #{number} → Ready ({decision.reason})")
    else:
        print(f"flip: #{number} → {status}")
    set_field(gh, cfg, item["id"], "status", option=status)
    return 0


_BOARD_QUERY = """
query($owner: String!, $project: Int!) {
  user(login: $owner) {
    projectV2(number: $project) {
      items(first: 100) {
        nodes {
          content { ... on Issue { number body repository { nameWithOwner }
                                   comments(last: 50) { nodes { body createdAt } } } }
          status: fieldValueByName(name: "Status") { ... on ProjectV2ItemFieldSingleSelectValue { name } }
        }
      }
    }
  }
}
"""


def audit(gh, cfg: dict, repo: str) -> list[str]:
    """Ready items whose newest gate record is missing, not `ready`, or stale. [] ⇒ clean."""
    data = _json(gh(["api", "graphql", "-f", "query=" + _BOARD_QUERY, "-F", f"owner={cfg['owner']}",
                     "-F", f"project={cfg['project_number']}"]))
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    nodes = ((((data.get("user") or {}).get("projectV2") or {}).get("items") or {}).get("nodes")) or []
    lines = []
    for n in nodes:
        if ((n.get("status") or {}).get("name")) != "Ready":
            continue
        c = n.get("content") or {}
        if not c.get("number"):
            continue
        repo_name = (c.get("repository") or {}).get("nameWithOwner")
        if repo_name and repo_name != repo:
            continue
        decision = check_flip(c.get("body") or "", ((c.get("comments") or {}).get("nodes")) or [])
        if not decision.allowed:
            lines.append(f"#{c['number']}: Ready without a fresh record — {decision.reason}")
    return lines


def board_ids(gh, owner: str, project_number: int) -> str:
    """Render `board.toml` from the live project: the id, the four field ids, the option ids."""
    view = _json(gh(["project", "view", str(project_number), "--owner", owner, "--format", "json"]))
    fields = _json(gh(["project", "field-list", str(project_number), "--owner", owner, "--format", "json",
                       "--limit", "50"]))
    by_name = {f.get("name"): f for f in fields.get("fields") or []}
    lines = [f'owner = "{owner}"', f"project_number = {project_number}", f'project_id = "{view.get("id", "")}"',
             "", "[fields]"]
    for key, name in FIELD_NAMES.items():
        if name in by_name:
            lines.append(f'{key} = "{by_name[name]["id"]}"')
    for key in ("status", "reason", "size"):
        lines += ["", f"[options.{key}]"]
        for opt in (by_name.get(FIELD_NAMES[key]) or {}).get("options") or []:
            lines.append(f'"{opt["name"]}" = "{opt["id"]}"')
    return "\n".join(lines) + "\n"
