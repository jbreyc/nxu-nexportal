import json
import tomllib

import pytest

from nexportal_gate import board, records
from nexportal_gate.adversary import GateResult
from nexportal_gate.text import body_hash

CFG = {"owner": "jbreyc", "project_number": 1, "project_id": "PVT_x",
       "fields": {"status": "F_STATUS", "reason": "F_REASON", "size": "F_SIZE", "requester": "F_REQ"},
       "options": {"status": {"Inbox": "o_in", "Triaged": "o_tr", "Drafted": "o_dr", "Ready": "o_rd",
                              "In Sprint": "o_sp", "Done": "o_dn"},
                   "reason": {"Needs-info": "o_ni"}, "size": {"S": "s", "M": "m", "L": "l", "XL": "xl"}}}
REPO = "jbreyc/nxu-nexportal"
BODY = "## Outcome\n\nx\n"
TIER2 = {"verdict": "ready", "steelman": "", "ambiguities": [], "untestable_criteria": [],
         "hidden_dependencies": [], "size": {"band": "S", "confidence": 0.9, "risk": ""},
         "refinement_agenda": [], "requester_message": ""}


def gate_comment(verdict, sha, created):
    r = GateResult(verdict, verdict, [], TIER2, sha, 1, "m", [])
    return {"body": records.render_gate_comment(r, issue=2), "createdAt": created}


class FakeGh:
    """argv-prefix → stdout. Records every call so a test can assert what was NOT written."""

    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def __call__(self, argv, *, stdin=None):
        self.calls.append((list(argv), stdin))
        for prefix, out in self.responses:
            if tuple(argv[:len(prefix)]) == tuple(prefix):
                return out
        raise AssertionError(f"unexpected gh call: {argv}")

    def writes(self):
        return [a for a, _ in self.calls if a[:2] == ["project", "item-edit"]]


def item_graphql(status="Drafted", reason="Needs-info", project_number=1):
    return json.dumps({"data": {"repository": {"issue": {"state": "OPEN", "projectItems": {"nodes": [
        {"id": "PVTI_other", "project": {"number": 7}, "status": {"name": "Done"}, "reason": None},
        {"id": "PVTI_ours", "project": {"number": project_number}, "status": {"name": status},
         "reason": {"name": reason} if reason else None}]}}}}})


def issue_json(body=BODY, comments=()):
    return json.dumps({"number": 2, "title": "t", "body": body, "state": "OPEN", "comments": list(comments)})


# --- the rule -----------------------------------------------------------------------------------

def test_check_flip_no_record():
    d = board.check_flip(BODY, [])
    assert not d.allowed and "no NX-GATE record" in d.reason


def test_check_flip_needs_info():
    d = board.check_flip(BODY, [gate_comment("needs-info", body_hash(BODY), "2026-09-03T10:00:00Z")])
    assert not d.allowed and "needs-info" in d.reason


def test_check_flip_stale_hash():
    d = board.check_flip(BODY + "edited\n", [gate_comment("ready", body_hash(BODY), "2026-09-03T10:00:00Z")])
    assert not d.allowed and "different body" in d.reason
    assert body_hash(BODY)[:8] in d.reason and body_hash(BODY + "edited\n")[:8] in d.reason


def test_check_flip_fresh():
    d = board.check_flip(BODY, [gate_comment("ready", body_hash(BODY), "2026-09-03T10:00:00Z")])
    assert d.allowed and body_hash(BODY)[:8] in d.reason


def test_check_flip_uses_the_newest_record():
    comments = [gate_comment("ready", body_hash(BODY), "2026-09-03T10:00:00Z"),
                gate_comment("needs-info", body_hash(BODY), "2026-09-03T11:00:00Z")]
    assert not board.check_flip(BODY, comments).allowed


# --- flip: the guarded door ---------------------------------------------------------------------

def test_flip_ready_refused_writes_nothing(capsys):
    gh = FakeGh([(("issue", "view"), issue_json()), (("api", "graphql"), item_graphql())])
    assert board.flip(gh, CFG, REPO, 2, "Ready") == 3
    assert gh.writes() == []
    assert "run: nexportal-gate gate 2" in capsys.readouterr().err


def test_flip_ready_allowed_writes_status_once():
    fresh = gate_comment("ready", body_hash(BODY), "2026-09-03T10:00:00Z")
    gh = FakeGh([(("issue", "view"), issue_json(comments=[fresh])), (("api", "graphql"), item_graphql()),
                 (("project", "item-edit"), "")])
    assert board.flip(gh, CFG, REPO, 2, "Ready") == 0
    writes = gh.writes()
    assert len(writes) == 1
    w = writes[0]
    assert w[w.index("--id") + 1] == "PVTI_ours" and w[w.index("--field-id") + 1] == "F_STATUS"
    assert w[w.index("--single-select-option-id") + 1] == "o_rd"


def test_flip_other_status_skips_the_rule():
    gh = FakeGh([(("api", "graphql"), item_graphql()), (("project", "item-edit"), "")])   # no issue view registered
    assert board.flip(gh, CFG, REPO, 2, "In Sprint") == 0
    assert gh.writes()[0][gh.writes()[0].index("--single-select-option-id") + 1] == "o_sp"


def test_flip_unknown_status_raises():
    with pytest.raises(board.BoardError):
        board.flip(FakeGh([]), CFG, REPO, 2, "Shipped")


def test_flip_not_on_board_raises():
    gh = FakeGh([(("api", "graphql"), item_graphql(project_number=9))])
    with pytest.raises(board.BoardError, match="not on"):
        board.flip(gh, CFG, REPO, 2, "In Sprint")


# --- plumbing -----------------------------------------------------------------------------------

def test_create_issue_parses_number_and_sends_body_on_stdin():
    gh = FakeGh([(("issue", "create"), "https://github.com/jbreyc/nxu-nexportal/issues/12\n")])
    assert board.create_issue(gh, REPO, "t", "b") == 12
    argv, stdin = gh.calls[0]
    assert stdin == "b" and argv[argv.index("--body-file") + 1] == "-" and argv[argv.index("--repo") + 1] == REPO


def test_comment_and_set_body_send_stdin():
    gh = FakeGh([(("issue", "comment"), ""), (("issue", "edit"), "")])
    board.comment(gh, REPO, 2, "c")
    board.set_body(gh, REPO, 2, "new body")
    assert gh.calls[0][1] == "c" and gh.calls[1][1] == "new body"


def test_set_field_variants():
    gh = FakeGh([(("project", "item-edit"), "")])
    board.set_field(gh, CFG, "I", "status", option="Ready")
    board.set_field(gh, CFG, "I", "reason", option=None)
    board.set_field(gh, CFG, "I", "requester", text="@ceo")
    a, b, c = (argv for argv, _ in gh.calls)
    assert a[a.index("--single-select-option-id") + 1] == "o_rd" and a[a.index("--project-id") + 1] == "PVT_x"
    assert "--clear" in b and b[b.index("--field-id") + 1] == "F_REASON"
    assert c[c.index("--text") + 1] == "@ceo"
    with pytest.raises(board.BoardError):
        board.set_field(gh, CFG, "I", "size", option="XXL")


def test_project_item_selects_our_project():
    gh = FakeGh([(("api", "graphql"), item_graphql())])
    assert board.project_item(gh, CFG, REPO, 2) == {"id": "PVTI_ours", "status": "Drafted", "reason": "Needs-info"}


def test_open_issues_outcome_from_record_then_section():
    from nexportal_gate.intake import IntakeResult
    out = {"outcome": "from the record", "urgency": {}, "duplicate": {}, "size": {}, "questions": [], "requester_message": ""}
    rec = records.render_intake_comment(IntakeResult("triaged", out, None, [], 1, "m", [], []), requester="x", text="t")
    listing = json.dumps([
        {"number": 3, "title": "a", "body": "", "comments": [{"body": rec, "createdAt": "2026-09-03T10:00:00Z"}]},
        {"number": 1, "title": "b", "body": "## Outcome\n\nfrom the section\n\n## Users\n\nu", "comments": []},
        {"number": 9, "title": "c", "body": "no sections", "comments": []},
    ])
    gh = FakeGh([(("issue", "list"), listing)])
    assert board.open_issues(gh, REPO) == [
        {"number": 3, "title": "a", "outcome": "from the record"},
        {"number": 1, "title": "b", "outcome": "from the section"},
        {"number": 9, "title": "c", "outcome": ""}]


def test_audit_names_ready_items_without_a_fresh_record():
    fresh = gate_comment("ready", body_hash(BODY), "2026-09-03T10:00:00Z")
    stale = gate_comment("ready", body_hash("other"), "2026-09-03T10:00:00Z")
    nodes = [
        {"content": {"number": 1, "body": BODY, "comments": {"nodes": [fresh]}}, "status": {"name": "Ready"}},
        {"content": {"number": 2, "body": BODY, "comments": {"nodes": [stale]}}, "status": {"name": "Ready"}},
        {"content": {"number": 3, "body": BODY, "comments": {"nodes": []}}, "status": {"name": "Drafted"}},
        {"content": {"number": 4, "body": BODY, "comments": {"nodes": []}}, "status": {"name": "Ready"}},
    ]
    gh = FakeGh([(("api", "graphql"), json.dumps({"data": {"user": {"projectV2": {"items": {"nodes": nodes}}}}}))])
    lines = board.audit(gh, CFG, REPO)
    assert [line.split(":")[0] for line in lines] == ["#2", "#4"]


def test_board_ids_renders_toml():
    view = json.dumps({"id": "PVT_x", "number": 1})
    fields = json.dumps({"fields": [
        {"id": "F_STATUS", "name": "Status", "type": "ProjectV2SingleSelectField",
         "options": [{"id": "o_rd", "name": "Ready"}, {"id": "o_dr", "name": "Drafted"}]},
        {"id": "F_REASON", "name": "Reason", "type": "ProjectV2SingleSelectField", "options": [{"id": "o_ni", "name": "Needs-info"}]},
        {"id": "F_SIZE", "name": "Size", "type": "ProjectV2SingleSelectField", "options": [{"id": "s", "name": "S"}]},
        {"id": "F_REQ", "name": "Requester", "type": "ProjectV2Field"},
        {"id": "F_TITLE", "name": "Title", "type": "ProjectV2Field"},
    ]})
    gh = FakeGh([(("project", "view"), view), (("project", "field-list"), fields)])
    cfg = tomllib.loads(board.board_ids(gh, "jbreyc", 1))
    assert cfg["owner"] == "jbreyc" and cfg["project_id"] == "PVT_x" and cfg["project_number"] == 1
    assert cfg["fields"] == {"status": "F_STATUS", "reason": "F_REASON", "size": "F_SIZE", "requester": "F_REQ"}
    assert cfg["options"]["status"]["Ready"] == "o_rd" and cfg["options"]["reason"]["Needs-info"] == "o_ni"


def test_load_board_reads_toml(tmp_path):
    p = tmp_path / "board.toml"
    p.write_text(board.board_ids(FakeGh([(("project", "view"), json.dumps({"id": "PVT_y", "number": 3})),
                                         (("project", "field-list"), json.dumps({"fields": []}))]), "o", 3))
    assert board.load_board(p)["project_id"] == "PVT_y"
    with pytest.raises(board.BoardError):
        board.load_board(tmp_path / "missing.toml")
