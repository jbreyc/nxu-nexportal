import re
from pathlib import Path

from nexportal_gate import shape


def body_of(name):
    return Path("fixtures", name).read_text(encoding="utf-8").split("---\n", 2)[2]


def with_section(body, heading, content):
    pat = re.compile(rf"(## {re.escape(heading)}\n)(.*?)(?=\n## |\Z)", re.S)
    assert pat.search(body), heading
    return pat.sub(lambda m: m.group(1) + "\n" + content + "\n", body, count=1)


def first(body):
    failures = shape.check(body)
    assert failures, "expected a failure"
    return failures[0].check


GOOD = body_of("01-referral-brief.md")


def test_good_spec_passes():
    assert shape.check(GOOD) == []


def test_vague_and_trap_fixtures_pass_shape():
    # their defects are Tier 2's job — shape is complete
    assert shape.check(body_of("02-vague-dashboard.md")) == []
    assert shape.check(body_of("05-pay-selected-invoices.md")) == []


def test_open_question_is_first():
    broken = GOOD.replace("## Users", "## People")
    assert first("NX-OPEN-QUESTION: which market?\n" + broken) == "open-question"


def test_indented_open_question_is_prose():
    assert shape.check("  NX-OPEN-QUESTION: not a record\n" + GOOD) == []


def test_missing_section_named():
    assert first(GOOD.replace("## Users", "## People")) == "section:users"


def test_section_empty_after_comment_stripping():
    assert first(with_section(GOOD, "Users", "<!-- who, in which moment -->")) == "section:users"


def test_failures_list_every_defect_first_named_in_order():
    body = with_section(with_section(GOOD, "Size", "S"), "Requester", "tbd")
    checks = [f.check for f in shape.check(body)]
    assert checks == ["size", "requester"]


def test_one_criterion_fails():
    assert first(with_section(GOOD, "Acceptance criteria", "- [ ] THE SYSTEM SHALL render the card.")) == "acceptance-criteria"


def test_non_ears_criterion_fails():
    ac = "- make it nice\n- THE SYSTEM SHALL render the card."
    assert first(with_section(GOOD, "Acceptance criteria", ac)) == "acceptance-criteria"


def test_given_when_then_ok():
    ac = ("- Given an eligible learner, when the card renders, then the link is primary.\n"
          "- Given a referral credited, when the card renders, then the amount shows.")
    assert shape.check(with_section(GOOD, "Acceptance criteria", ac)) == []


def test_design_url_ok():
    assert shape.check(with_section(GOOD, "Design", "https://www.figma.com/file/x")) == []


def test_design_no_ui_hyphen_ok():
    assert shape.check(with_section(GOOD, "Design", "n/a - no UI")) == []


def test_design_prose_fails():
    assert first(with_section(GOOD, "Design", "we'll figure it out in refinement")) == "design"


def test_brief_missing_change_line_fails():
    brief = "brief:\nGoal: share taps\nKeep: position\nOut of scope: amounts"
    assert first(with_section(GOOD, "Design", brief)) == "design"


def test_dependencies_none_with_reason_ok():
    assert shape.check(with_section(GOOD, "Dependencies", "none — reads state that already exists")) == []


def test_size_without_rationale_fails():
    assert first(with_section(GOOD, "Size", "S")) == "size"


def test_size_unknown_band_fails():
    assert first(with_section(GOOD, "Size", "XXL — enormous, many sprints")) == "size"


def test_requester_placeholder_fails():
    assert first(with_section(GOOD, "Requester", "tbd")) == "requester"


def test_users_placeholder_fails():
    assert first(with_section(GOOD, "Users", "?")) == "users"
