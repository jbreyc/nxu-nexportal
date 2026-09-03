from nexportal_gate import draft, shape, text

REC = {
    "schema": "nx-intake/1", "status": "triaged", "requester": "fadl",
    "request": "Can we get an AI chatbot, this sprint?",
    "tier2": {
        "outcome": "Learners get answers to programme questions without waiting for support.",
        "size": {"band": "XL", "confidence": 0.3, "risk": "No learner outcome stated; scope unbounded."},
        "questions": [{"text": "What should a learner be able to do on day one?", "owner": "requester"},
                      {"text": "Which surface — dashboard or Canvas?", "owner": "design"}],
    },
}


def test_draft_has_all_eight_sections():
    body = draft.render_draft(REC, title="AI chatbot")
    assert set(shape.SECTIONS) <= set(text.sections(body))


def test_draft_opens_with_the_questions_as_open_question_lines():
    body = draft.render_draft(REC, title="AI chatbot")
    lines = [line for line in body.split("\n") if line.startswith("NX-OPEN-QUESTION:")]
    assert lines == ["NX-OPEN-QUESTION: What should a learner be able to do on day one? (owner: requester)",
                     "NX-OPEN-QUESTION: Which surface — dashboard or Canvas? (owner: design)"]
    assert shape.check(body)[0].check == "open-question"


def test_draft_without_questions_fails_at_users():
    rec = dict(REC, tier2=dict(REC["tier2"], questions=[]))
    body = draft.render_draft(rec, title="AI chatbot")
    assert "NX-OPEN-QUESTION" not in body
    assert shape.check(body)[0].check == "section:users"


def test_draft_fills_outcome_size_requester():
    secs = text.sections(draft.render_draft(REC, title="AI chatbot"))
    assert secs["outcome"] == REC["tier2"]["outcome"]
    assert secs["size"].startswith("XL —") and "scope unbounded" in secs["size"]
    assert secs["requester"] == "@fadl"
    assert shape.RULES["size"](secs["size"]) is None


def test_draft_does_not_double_the_handle():
    secs = text.sections(draft.render_draft(dict(REC, requester="@fadl"), title="t"))
    assert secs["requester"] == "@fadl"


def test_draft_keeps_the_original_request_for_provenance():
    assert "Can we get an AI chatbot" in draft.render_draft(REC, title="AI chatbot")


def test_draft_title_is_the_h1():
    assert draft.render_draft(REC, title="AI chatbot").startswith("# AI chatbot\n")
