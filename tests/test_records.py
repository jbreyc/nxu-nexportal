import json

from nexportal_gate import records
from nexportal_gate.adversary import GateResult
from nexportal_gate.intake import IntakeResult
from nexportal_gate.shape import Failure

TIER2 = {"verdict": "ready", "steelman": "s",
         "ambiguities": [{"text": "which market", "why_it_bites_mid_build": "w", "owner": "requester", "blocking": True}],
         "untestable_criteria": [], "hidden_dependencies": [],
         "size": {"band": "M", "confidence": 0.6, "risk": "r"},
         "refinement_agenda": ["decide the market", "agree the copy"], "requester_message": "Send me the market list by Thursday."}
GATE = GateResult("needs-info", "ready", [], TIER2, "abc123", 1, "claude-fable-5-1",
                  ["blocking ambiguity owned by requester: which market"])
INTAKE_OUT = {"outcome": "o", "urgency": {"claim": "c", "evidence": "e", "assessment": "a"},
              "duplicate": {"is_duplicate": False, "of_issue": None, "why": ""},
              "size": {"band": "XL", "confidence": 0.3, "risk": "r"},
              "questions": [{"text": "q1", "owner": "requester"}], "requester_message": "m"}


def test_gate_comment_round_trip():
    c = records.render_gate_comment(GATE, issue=12)
    assert c.startswith("NX-GATE: needs-info\n")
    rec = records.parse_record(c)
    assert rec["_marker"] == records.GATE_MARKER and rec["_verdict"] == "needs-info"
    assert rec["verdict"] == "needs-info" and rec["model_verdict"] == "ready"
    assert rec["body_sha256"] == "abc123" and rec["tier2"] == TIER2 and rec["prompt_version"] == 1
    assert rec["model"] == "claude-fable-5-1" and "ts" in rec and rec["schema"] == "nx-gate/1"


def test_gate_comment_summary_carries_agenda_and_message():
    c = records.render_gate_comment(GATE, issue=12)
    assert "decide the market" in c and "Send me the market list by Thursday." in c
    assert "which market" in c


def test_gate_comment_tier1_failure_names_first_check_and_the_command():
    r = GateResult("needs-info", None, [Failure("design", "no link"), Failure("size", "no rationale")],
                   None, "abc", 1, "m", ["shape: design — no link"])
    c = records.render_gate_comment(r, issue=12)
    assert "Tier 1 failed at `design`" in c and "nexportal-gate gate 12" in c
    rec = records.parse_record(c)
    assert rec["tier1"] == [["design", "no link"], ["size", "no rationale"]] and rec["tier2"] is None


def test_intake_comment_round_trip():
    r = IntakeResult("triaged", INTAKE_OUT, None, [], 1, "m", [1], [])
    c = records.render_intake_comment(r, requester="ceo", text="Can we get an AI chatbot?")
    assert c.startswith("NX-INTAKE: triaged\n")
    rec = records.parse_record(c)
    assert rec["_marker"] == records.INTAKE_MARKER and rec["status"] == "triaged"
    assert rec["requester"] == "ceo" and rec["request"] == "Can we get an AI chatbot?"
    assert rec["tier2"] == INTAKE_OUT and rec["schema"] == "nx-intake/1" and rec["shortlist"] == [1]


def test_intake_duplicate_comment_names_the_issue():
    out = dict(INTAKE_OUT, duplicate={"is_duplicate": True, "of_issue": 1, "why": "same card"})
    r = IntakeResult("duplicate", out, 1, [], 1, "m", [1], ["duplicate of #1: same card"])
    c = records.render_intake_comment(r, requester="ops", text="share a referral link")
    assert c.startswith("NX-INTAKE: duplicate\n") and "#1" in c and "@ops" in c
    assert records.parse_record(c)["duplicate_of"] == 1


def test_indented_or_quoted_marker_is_not_a_record():
    assert records.parse_record("  NX-GATE: ready\n```json\n{}\n```") is None
    assert records.parse_record("> NX-GATE: ready\n```json\n{}\n```") is None


def test_marker_without_fence_is_not_a_record():
    assert records.parse_record("NX-GATE: ready\nno json here") is None


def test_crlf_comment_parses():
    c = records.render_gate_comment(GATE, issue=1).replace("\n", "\r\n")
    assert records.parse_record(c)["verdict"] == "needs-info"


def test_newest_record_picks_latest_matching_marker():
    ready = GateResult("ready", "ready", [], dict(TIER2, ambiguities=[]), "def", 1, "m", [])
    intake = IntakeResult("triaged", INTAKE_OUT, None, [], 1, "m", [], [])
    comments = [
        {"body": records.render_gate_comment(GATE, issue=1), "createdAt": "2026-09-03T10:00:00Z"},
        {"body": "just a comment", "createdAt": "2026-09-03T11:00:00Z"},
        {"body": records.render_gate_comment(ready, issue=1), "createdAt": "2026-09-03T11:30:00Z"},
        {"body": records.render_intake_comment(intake, requester="x", text="t"), "createdAt": "2026-09-03T12:00:00Z"},
    ]
    assert records.newest_record(comments, records.GATE_MARKER)["verdict"] == "ready"
    assert records.newest_record(comments, records.INTAKE_MARKER)["status"] == "triaged"
    assert records.newest_record([], records.GATE_MARKER) is None
    assert records.newest_record(comments[1:2], records.GATE_MARKER) is None


def test_payload_is_valid_json_with_no_trailing_text():
    c = records.render_gate_comment(GATE, issue=1)
    fence = c.split("```json\n", 1)[1]
    payload, rest = fence.split("\n```", 1)
    json.loads(payload)
    assert rest.strip() == ""
