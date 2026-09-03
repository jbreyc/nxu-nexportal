"""The seed choreography, asserted offline against a small stateful fake GitHub."""
import json
from pathlib import Path

from nexportal_gate import records, seed
from nexportal_gate.adversary import AdversaryError
from nexportal_gate.fixtures import load_fixtures, split_frontmatter

CFG = json.loads(Path("tests/board.fixture.json").read_text()) if Path("tests/board.fixture.json").exists() else {
    "owner": "jbreyc", "project_number": 1, "project_id": "PVT_x",
    "fields": {"status": "F_STATUS", "reason": "F_REASON", "size": "F_SIZE", "requester": "F_REQ"},
    "options": {"status": {"Inbox": "o_in", "Triaged": "o_tr", "Drafted": "o_dr", "Ready": "o_rd",
                           "In Sprint": "o_sp", "Done": "o_dn"},
                "reason": {"Needs-info": "o_ni"}, "size": {"S": "s", "M": "m", "L": "l", "XL": "xl"}}}
REPO = "jbreyc/nxu-nexportal"
PROMPTS, PLATFORM = Path("prompts"), Path("context/platform.md").read_text(encoding="utf-8")
FIELD_BY_ID = {v: k for k, v in CFG["fields"].items()}
OPTION_NAME = {oid: (field, name) for field, opts in CFG["options"].items() for name, oid in opts.items()}


class FakeGitHub:
    def __init__(self):
        self.issues, self.items, self.calls, self.next, self.tick = {}, {}, [], 1, 0

    def _stamp(self):
        self.tick += 1
        return f"2026-09-03T{10 + self.tick // 3600:02d}:{(self.tick // 60) % 60:02d}:{self.tick % 60:02d}Z"

    def __call__(self, argv, *, stdin=None):
        self.calls.append((list(argv), stdin))
        cmd = tuple(argv[:2])
        if cmd == ("issue", "create"):
            n, self.next = self.next, self.next + 1
            self.issues[n] = {"number": n, "title": argv[argv.index("--title") + 1], "body": stdin,
                              "state": "OPEN", "comments": []}
            return f"https://github.com/{REPO}/issues/{n}\n"
        if cmd == ("issue", "view"):
            return json.dumps(self.issues[int(argv[2])])
        if cmd == ("issue", "comment"):
            self.issues[int(argv[2])]["comments"].append({"body": stdin, "createdAt": self._stamp()})
            return ""
        if cmd == ("issue", "edit"):
            self.issues[int(argv[2])]["body"] = stdin
            return ""
        if cmd == ("issue", "close"):
            self.issues[int(argv[2])]["state"] = "CLOSED"
            return ""
        if cmd == ("issue", "list"):
            return json.dumps([i for i in self.issues.values() if i["state"] == "OPEN"])
        if cmd == ("project", "item-add"):
            n = int(argv[argv.index("--url") + 1].rsplit("/", 1)[1])
            self.items[n] = {"id": f"PVTI_{n}", "status": "", "reason": "", "size": "", "requester": ""}
            return json.dumps({"id": f"PVTI_{n}"})
        if cmd == ("project", "item-edit"):
            n = int(argv[argv.index("--id") + 1].split("_")[1])
            field = FIELD_BY_ID[argv[argv.index("--field-id") + 1]]
            if "--clear" in argv:
                self.items[n][field] = ""
            elif "--text" in argv:
                self.items[n][field] = argv[argv.index("--text") + 1]
            else:
                self.items[n][field] = OPTION_NAME[argv[argv.index("--single-select-option-id") + 1]][1]
            return ""
        if cmd == ("api", "graphql"):
            n = int([a for a in argv if a.startswith("number=")][0].split("=")[1])
            item = self.items.get(n)
            nodes = [{"id": item["id"], "project": {"number": 1}, "status": {"name": item["status"]},
                      "reason": {"name": item["reason"]} if item["reason"] else None}] if item else []
            return json.dumps({"data": {"repository": {"issue": {"state": "OPEN", "projectItems": {"nodes": nodes}}}}})
        raise AssertionError(f"unexpected gh call: {argv}")


class SeqClient:
    """Per-key response sequences; the last one repeats."""

    def __init__(self, seqs):
        self.seqs, self.keys = {k: list(v) for k, v in seqs.items()}, []

    def complete(self, system, user, schema, *, key):
        self.keys.append(key)
        if key not in self.seqs:
            raise AdversaryError(f"no response for {key}")
        seq = self.seqs[key]
        return seq.pop(0) if len(seq) > 1 else seq[0]


def gate_out(verdict="ready", **over):
    base = {"verdict": verdict, "steelman": "s", "ambiguities": [], "untestable_criteria": [],
            "hidden_dependencies": [], "size": {"band": "S", "confidence": 0.8, "risk": "r"},
            "refinement_agenda": ["a"], "requester_message": "m"}
    base.update(over)
    return base


def intake_out(band="M", dup=None):
    return {"outcome": "o", "urgency": {"claim": "c", "evidence": "e", "assessment": "a"},
            "duplicate": {"is_duplicate": dup is not None, "of_issue": dup, "why": "same"},
            "size": {"band": band, "confidence": 0.5, "risk": "r"},
            "questions": [{"text": "what on day one?", "owner": "requester"}], "requester_message": "m"}


BLOCK = {"text": "t", "why_it_bites_mid_build": "w", "owner": "requester", "blocking": True}


def run_seed():
    gh = FakeGitHub()
    client = SeqClient({
        "issue-1": [gate_out("needs-info", ambiguities=[BLOCK]), gate_out("ready")],
        "issue-2": [gate_out("needs-info", ambiguities=[BLOCK])],
        "issue-5": [gate_out("needs-info", hidden_dependencies=[{"name": "payments provider", "why": "w", "blocking": True}])],
        "issue-6": [gate_out("ready")],
        "intake-03": [intake_out("XL")], "intake-04": [intake_out("M")], "intake-06": [intake_out("M", dup=1)],
    })
    s = seed.Seeder(gh, CFG, REPO, client, prompts_dir=PROMPTS, platform=PLATFORM, model="m",
                    fixtures_dir=Path("fixtures"), seed_dir=Path("seed"), log=lambda *a: None)
    return gh, client, s.run()


def markers(gh, n):
    return [c["body"].split("\n", 1)[0] for c in gh.issues[n]["comments"]]


def test_issues_are_created_in_the_order_that_makes_the_numbers_true():
    gh, client, summary = run_seed()
    fx = {f.id: f for f in load_fixtures(Path("fixtures"))}
    titles = [gh.issues[n]["title"] for n in sorted(gh.issues)]
    assert titles[:5] == [fx["01"].title, fx["02"].title, fx["03"].title, fx["04"].title, fx["05"].title]
    assert len(gh.issues) == 9 and all(t for t in titles)
    assert summary["duplicate"] == {"06": 1}


def test_issue_one_runs_the_whole_chain_and_ends_ready():
    gh, client, _ = run_seed()
    assert markers(gh, 1) == ["NX-GATE: needs-info", "NX-INTAKE: duplicate", "NX-GATE: ready"] or \
           markers(gh, 1) == ["NX-INTAKE: duplicate", "NX-GATE: needs-info", "NX-GATE: ready"]
    _, v2 = split_frontmatter(Path("seed/01-referral-brief-v2.md").read_text(encoding="utf-8"))
    assert gh.issues[1]["body"] == v2
    assert gh.items[1]["status"] == "Ready" and gh.items[1]["reason"] == ""


def test_issue_two_keeps_needs_info_and_carries_the_refused_flip():
    gh, _, _ = run_seed()
    assert gh.items[2]["status"] == "Drafted" and gh.items[2]["reason"] == "Needs-info"
    bodies = [c["body"] for c in gh.issues[2]["comments"]]
    assert any(b.startswith("NX-GATE: needs-info") for b in bodies)
    assert any("REFUSED" in b and "nexportal-gate gate 2" in b for b in bodies)


def test_issue_three_is_drafted_with_open_questions_and_fails_tier_one():
    gh, client, _ = run_seed()
    assert gh.items[3]["status"] == "Drafted" and gh.items[3]["size"] == "XL" and gh.items[3]["requester"] == "@ceo"
    assert gh.issues[3]["body"].startswith("# ") and "NX-OPEN-QUESTION:" in gh.issues[3]["body"]
    assert markers(gh, 3) == ["NX-INTAKE: triaged", "NX-GATE: needs-info"]
    assert "issue-3" not in client.keys                       # Tier 1 failed: no model call


def test_issue_four_is_triaged_only():
    gh, _, _ = run_seed()
    assert gh.items[4]["status"] == "Triaged" and gh.items[4]["size"] == "M"
    assert markers(gh, 4) == ["NX-INTAKE: triaged"]


def test_issue_five_needs_info_on_the_hidden_dependency():
    gh, _, _ = run_seed()
    assert gh.items[5] == {"id": "PVTI_5", "status": "Drafted", "reason": "Needs-info", "size": "S", "requester": "@finance-ops"}
    rec = records.newest_record(gh.issues[5]["comments"], records.GATE_MARKER)
    assert rec["verdict"] == "needs-info" and "payments provider" in rec["reasons"][0]


def test_fillers_land_in_their_states():
    gh, _, _ = run_seed()
    assert gh.items[6]["status"] == "Ready" and markers(gh, 6) == ["NX-GATE: ready"]
    assert gh.items[7]["status"] == "In Sprint" and gh.issues[7]["state"] == "OPEN"
    assert gh.items[8]["status"] == "Done" and gh.issues[8]["state"] == "CLOSED"
    assert gh.items[9]["status"] == "Done" and gh.issues[9]["state"] == "CLOSED"
