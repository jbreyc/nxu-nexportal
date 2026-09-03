"""seed — the demo board, lived-in.

The six fixtures in the order that makes their numbers true (#1, #2 drafted specs; #3, #4 through
intake; #5 drafted; 06 through intake and flagged as a duplicate of #1, creating nothing), four
fillers in their states, then the choreography that leaves a real trail: gate records on #1, #2, #5;
a draft and a Tier 1 failure on #3; a refused flip on #2; the brief's v2 on #1, gated and flipped.
Every write goes through `board`; every judgement through `run_gate` / `run_intake` — the seed adds
no rule of its own.
"""
from __future__ import annotations

from pathlib import Path

from . import board, draft, records
from .adversary import Client, run_gate
from .fixtures import Fixture, load_fixtures, split_frontmatter
from .intake import run_intake
from .text import sections


def size_band(body: str) -> str | None:
    s = sections(body).get("size", "").strip()
    return s.split()[0].upper() if s else None


class Seeder:
    def __init__(self, gh, cfg: dict, repo: str, client: Client, *, prompts_dir: Path, platform: str,
                 model: str, fixtures_dir: Path, seed_dir: Path, log=print):
        self.gh, self.cfg, self.repo, self.client = gh, cfg, repo, client
        self.prompts_dir, self.platform, self.model = Path(prompts_dir), platform, model
        self.fixtures_dir, self.seed_dir, self.log = Path(fixtures_dir), Path(seed_dir), log
        self.duplicates: dict[str, int] = {}

    @staticmethod
    def _handle(requester: str) -> str:
        return requester if requester.startswith("@") else f"@{requester}"

    def _set(self, item_id: str, *, status=None, size=None, requester=None) -> None:
        if status:
            board.set_field(self.gh, self.cfg, item_id, "status", option=status)
        if size:
            board.set_field(self.gh, self.cfg, item_id, "size", option=size)
        if requester:
            board.set_field(self.gh, self.cfg, item_id, "requester", text=self._handle(requester))

    def file_spec(self, title: str, body: str, requester: str, size: str | None, status: str) -> int:
        n = board.create_issue(self.gh, self.repo, title, body)
        item_id = board.add_to_project(self.gh, self.cfg, self.repo, n)
        self._set(item_id, status=status, size=size, requester=requester)
        self.log(f"seed: #{n} {title!r} → {status}")
        return n

    def gate(self, n: int):
        iss = board.issue(self.gh, self.repo, n)
        result = run_gate(iss["body"], self.client, key=f"issue-{n}", prompts_dir=self.prompts_dir,
                          platform=self.platform, model=self.model)
        board.comment(self.gh, self.repo, n, records.render_gate_comment(result, issue=n))
        item = board.project_item(self.gh, self.cfg, self.repo, n)
        if item["id"]:
            board.set_field(self.gh, self.cfg, item["id"], "reason",
                            option="Needs-info" if result.verdict == "needs-info" else None)
        self.log(f"seed: gate #{n} → {result.verdict}")
        return result

    def intake(self, f: Fixture) -> int | None:
        open_issues = board.open_issues(self.gh, self.repo)
        result = run_intake(f.text, f.requester, open_issues, self.client, key=f"intake-{f.id}",
                            prompts_dir=self.prompts_dir, platform=self.platform, model=self.model,
                            weekday=f.weekday)
        text = records.render_intake_comment(result, requester=f.requester, text=f.text)
        if result.status == "duplicate":
            board.comment(self.gh, self.repo, result.duplicate_of, text)
            self.duplicates[f.id] = result.duplicate_of
            self.log(f"seed: intake {f.id} → duplicate of #{result.duplicate_of}, no issue")
            return None
        if result.status == "rejected":
            raise board.BoardError(f"seed: intake {f.id} rejected at the door: {result.failures}")
        body = f"{f.text}\n\n— requested by @{f.requester} via `nexportal-gate intake` ({f.weekday})\n"
        n = board.create_issue(self.gh, self.repo, f.title, body)
        board.comment(self.gh, self.repo, n, text)
        item_id = board.add_to_project(self.gh, self.cfg, self.repo, n)
        band = ((result.tier2 or {}).get("size") or {}).get("band")
        self._set(item_id, status="Triaged", size=band, requester=f.requester)
        self.log(f"seed: intake {f.id} → #{n} Triaged ({band})")
        return n

    def draft(self, n: int) -> None:
        iss = board.issue(self.gh, self.repo, n)
        rec = records.newest_record(iss["comments"], records.INTAKE_MARKER)
        if rec is None:
            raise board.BoardError(f"seed: no NX-INTAKE record on #{n}")
        board.set_body(self.gh, self.repo, n, draft.render_draft(rec, title=iss["title"]))
        item = board.project_item(self.gh, self.cfg, self.repo, n)
        if item["id"]:
            board.set_field(self.gh, self.cfg, item["id"], "status", option="Drafted")
        self.log(f"seed: draft #{n} → Drafted")

    def flip(self, n: int, status: str) -> int:
        rc = board.flip(self.gh, self.cfg, self.repo, n, status)
        if rc == 3:
            iss = board.issue(self.gh, self.repo, n)
            decision = board.check_flip(iss["body"], iss["comments"])
            board.comment(self.gh, self.repo, n,
                          f"`nexportal-gate flip {n} {status}` → **REFUSED** — {decision.reason} — "
                          f"run: `nexportal-gate gate {n}`\n\nThe wall wrote nothing; this note is the seed "
                          f"recording the refusal so the trail shows it.")
        self.log(f"seed: flip #{n} {status} → {'refused' if rc == 3 else 'ok'}")
        return rc

    def run(self) -> dict:
        fx = {f.id: f for f in load_fixtures(self.fixtures_dir)}
        numbers: dict[str, int] = {}
        for fid in ("01", "02"):
            f = fx[fid]
            numbers[fid] = self.file_spec(f.title, f.text, f.requester, size_band(f.text), "Drafted")
        for fid in ("03", "04"):
            n = self.intake(fx[fid])
            if n:
                numbers[fid] = n
        f = fx["05"]
        numbers["05"] = self.file_spec(f.title, f.text, f.requester, size_band(f.text), "Drafted")
        self.intake(fx["06"])
        for path in sorted(self.seed_dir.glob("*.md")):
            meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
            status = meta.get("status")
            if not status:                                   # the brief's v2 is a body, not an issue
                continue
            n = self.file_spec(meta["title"], body, meta.get("requester", ""), meta.get("size") or size_band(body),
                               "Drafted" if status == "Ready" else status)
            numbers[path.stem] = n
            if status == "Ready":
                self.gate(n)
                self.flip(n, "Ready")
            elif status == "Done":
                board.close_issue(self.gh, self.repo, n, "Shipped.")
        # the choreography: records, a draft that fails Tier 1, a refused flip, the v2, an allowed flip
        for fid in ("01", "02", "05"):
            self.gate(numbers[fid])
        if "03" in numbers:
            self.draft(numbers["03"])
            self.gate(numbers["03"])
        self.flip(numbers["02"], "Ready")
        _, v2 = split_frontmatter((self.seed_dir / "01-referral-brief-v2.md").read_text(encoding="utf-8"))
        board.set_body(self.gh, self.repo, numbers["01"], v2)
        self.gate(numbers["01"])
        self.flip(numbers["01"], "Ready")
        return {"issues": numbers, "duplicate": self.duplicates}
