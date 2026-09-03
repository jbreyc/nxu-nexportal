import json
from pathlib import Path

import pytest

from nexportal_gate import adversary, intake

PROMPTS = Path("prompts")
PLATFORM = Path("context/platform.md").read_text(encoding="utf-8")
OPEN = json.loads(Path("fixtures/open-issues.json").read_text(encoding="utf-8"))


def request_of(name):
    return Path("fixtures", name).read_text(encoding="utf-8").split("---\n", 2)[2].strip()


DUP = request_of("06-duplicate-referral-link.md")
CEO = request_of("03-ceo-chatbot.md")


def out(**over):
    base = {"outcome": "o", "urgency": {"claim": "c", "evidence": "e", "assessment": "a"},
            "duplicate": {"is_duplicate": False, "of_issue": None, "why": ""},
            "size": {"band": "M", "confidence": 0.6, "risk": "r"},
            "questions": [{"text": "q", "owner": "requester"}], "requester_message": "m"}
    base.update(over)
    return base


def run(text, client, requester="ops", weekday="Wednesday", key="k"):
    return intake.run_intake(text, requester, OPEN, client, key=key, prompts_dir=PROMPTS,
                             platform=PLATFORM, model="m", weekday=weekday)


# --- structure check ----------------------------------------------------------------------------

def test_structure_check_placeholder_requester():
    assert intake.structure_check("Board deck by Monday please", "tbd")[0].check == "requester"


def test_structure_check_short_text():
    assert intake.structure_check("chatbot", "fadl")[0].check == "request"


def test_structure_check_ok():
    assert intake.structure_check(CEO, "fadl") == []


# --- shortlist ----------------------------------------------------------------------------------

def test_shortlist_finds_the_referral_issue_first():
    assert intake.shortlist(DUP, OPEN)[0]["number"] == 1


def test_shortlist_empty_for_unrelated_request():
    assert intake.shortlist(CEO, OPEN) == []


def test_shortlist_respects_limit_and_threshold():
    assert len(intake.shortlist(DUP, OPEN, threshold=0.0, limit=2)) == 2


def test_shortlist_scores_on_title_and_outcome():
    only_outcome = [{"number": 9, "title": "x", "outcome": "students share a referral link with friends"}]
    assert intake.shortlist(DUP, only_outcome)[0]["number"] == 9


# --- run_intake ---------------------------------------------------------------------------------

class Raising:
    def complete(self, *a, **k):
        raise AssertionError("no call on a structure failure")


def test_run_intake_rejected_without_a_call():
    r = run(DUP, Raising(), requester="tbd")
    assert r.status == "rejected" and r.failures[0].check == "requester" and r.tier2 is None


def test_run_intake_triaged():
    r = run(CEO, adversary.FakeClient({"k": out()}), requester="fadl", weekday="Tuesday")
    assert r.status == "triaged" and r.duplicate_of is None and r.tier2 == out()
    assert r.prompt_version == 1 and r.model == "m" and r.failures == []


def test_run_intake_duplicate_confirmed():
    client = adversary.FakeClient({"k": out(duplicate={"is_duplicate": True, "of_issue": 1, "why": "same card"})})
    r = run(DUP, client)
    assert r.status == "duplicate" and r.duplicate_of == 1


def test_run_intake_duplicate_outside_shortlist_is_not_a_duplicate():
    client = adversary.FakeClient({"k": out(duplicate={"is_duplicate": True, "of_issue": 42, "why": "?"})})
    r = run(DUP, client)
    assert r.status == "triaged" and r.duplicate_of is None
    assert any("42" in reason for reason in r.reasons)


def test_run_intake_passes_candidates_weekday_platform_and_schema():
    class Spy:
        def complete(self, system, user, schema, *, key):
            self.system, self.user, self.schema = system, user, schema
            return out()
    spy = Spy()
    run(DUP, spy, requester="ops", weekday="Friday")
    assert spy.system.startswith("version: 1")
    assert "#1 — Refer a friend" in spy.user and "Friday" in spy.user and "Canvas" in spy.user
    assert DUP in spy.user and "ops" in spy.user
    assert spy.schema["properties"]["duplicate"]["required"] == ["is_duplicate", "of_issue", "why"]


def test_run_intake_says_none_when_no_candidates():
    class Spy:
        def complete(self, system, user, schema, *, key):
            self.user = user
            return out()
    spy = Spy()
    run(CEO, spy, requester="fadl")
    assert "none" in spy.user.split("## Open issues", 1)[1].split("## Platform", 1)[0]
