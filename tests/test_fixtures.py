import json
from pathlib import Path

from nexportal_gate import adversary, fixtures
from nexportal_gate.__main__ import main

FIXTURES = Path("fixtures")
PROMPTS = Path("prompts")
PLATFORM = Path("context/platform.md").read_text(encoding="utf-8")
OPEN = json.loads((FIXTURES / "open-issues.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def gate_out(**over):
    base = {"verdict": "ready", "steelman": "s", "ambiguities": [], "untestable_criteria": [],
            "hidden_dependencies": [], "size": {"band": "S", "confidence": 0.85, "risk": "r"},
            "refinement_agenda": [], "requester_message": "m"}
    base.update(over)
    return base


def intake_out(**over):
    base = {"outcome": "o", "urgency": {"claim": "c", "evidence": "e", "assessment": "a"},
            "duplicate": {"is_duplicate": False, "of_issue": None, "why": ""},
            "size": {"band": "M", "confidence": 0.6, "risk": "r"},
            "questions": [{"text": "q", "owner": "requester"}], "requester_message": "m"}
    base.update(over)
    return base


def amb(owner):
    return {"text": "t", "why_it_bites_mid_build": "w", "owner": owner, "blocking": True}


def satisfying():
    """Responses that meet every frozen expectation — the runner under test, not the model."""
    return {
        "01": gate_out(),
        "02": gate_out(verdict="needs-info", ambiguities=[amb("requester"), amb("design"), amb("requester")]),
        "03": intake_out(size={"band": "XL", "confidence": 0.3, "risk": "r"},
                         requester_message="Filed as #3. For it to go this sprint, the deadline rail moves out — decision Thursday."),
        "04": intake_out(size={"band": "M", "confidence": 0.6, "risk": "r"},
                         requester_message="Triage is Thursday; Monday 9am is before that. Send the data source today."),
        "05": gate_out(verdict="needs-info",
                       hidden_dependencies=[{"name": "payments provider partial-payment support", "why": "w", "blocking": True}]),
        "06": intake_out(duplicate={"is_duplicate": True, "of_issue": 1, "why": "same card"}),
    }


def run_rows(client):
    return fixtures.run_all(client, fixtures_dir=FIXTURES, prompts_dir=PROMPTS, platform=PLATFORM,
                            open_issues=OPEN, model="m")


def test_load_fixtures_parses_frontmatter_in_id_order():
    fx = fixtures.load_fixtures(FIXTURES)
    assert [f.id for f in fx] == ["01", "02", "03", "04", "05", "06"]
    ceo = fx[2]
    assert (ceo.entry, ceo.requester, ceo.weekday) == ("intake", "ceo", "Tuesday")
    assert ceo.text.startswith("Can we get an AI chatbot") and ceo.title == "AI chatbot, this sprint"
    assert fx[0].entry == "gate" and fx[0].text.startswith("## Outcome")


def test_expected_has_exactly_the_six_ids():
    assert sorted(EXPECTED) == ["01", "02", "03", "04", "05", "06"]


def test_evaluate_predicates():
    actual = {"verdict": "needs-info", "size_confidence": 0.4, "blocking_ambiguities": 2,
              "ambiguity_owners": ["design", "requester"], "message": "Decision Thursday, either way.",
              "hidden_dependency_names": ["Payments provider"], "question_owners": ["requester"]}
    checks = {c.name: c for c in fixtures.evaluate(
        {"verdict": "needs-info", "size_confidence_max": 0.5, "size_confidence_min": 0.5,
         "blocking_ambiguities_min": 3, "ambiguity_owners_include": ["requester"],
         "message_mentions_all": ["Thursday"], "message_mentions_any": ["nope", "decision"],
         "hidden_dependency_mentions_any": ["payment"], "question_owners_include": ["design"],
         "bogus": 1}, actual)}
    assert checks["verdict"].passed and checks["size_confidence_max"].passed
    assert not checks["size_confidence_min"].passed and not checks["blocking_ambiguities_min"].passed
    assert checks["ambiguity_owners_include"].passed and checks["message_mentions_all"].passed
    assert checks["message_mentions_any"].passed and checks["hidden_dependency_mentions_any"].passed
    assert not checks["question_owners_include"].passed and not checks["bogus"].passed
    assert "expected" in checks["blocking_ambiguities_min"].detail


def test_run_all_with_satisfying_fake_passes_every_check():
    rows = run_rows(adversary.FakeClient(satisfying()))
    assert [f.id for f, _, _ in rows] == ["01", "02", "03", "04", "05", "06"]
    for f, view, checks in rows:
        assert all(c.passed for c in checks), (f.id, [c for c in checks if not c.passed])
    assert rows[5][1]["duplicate_of"] == 1 and rows[4][1]["tier1_failed"] is False


def test_actual_view_of_a_tier1_failure_has_no_size():
    r = adversary.run_gate("## Outcome\nx", adversary.FakeClient({}), key="k", prompts_dir=PROMPTS,
                           platform=PLATFORM, model="m")
    view = fixtures.actual_view(r)
    assert view["tier1_failed"] and view["tier1_first"] == "section:users" and view["size_band"] is None


def test_render_results_marks_miss_with_reading():
    responses = satisfying()
    responses["01"] = gate_out(size={"band": "M", "confidence": 0.9, "risk": "r"})
    rows = run_rows(adversary.FakeClient(responses))
    table = fixtures.render_results(rows, {"01": "sized M: the toast counted as a second surface"})
    assert "| 01 |" in table and "MISS" in table and "size_band" in table
    assert "sized M: the toast counted" in table and "5/6" in table
    assert table.count("PASS") == 5


def test_cli_fixtures_replay_end_to_end(tmp_path, capsys):
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    for key, out in satisfying().items():
        (recorded / f"{key}.json").write_text(json.dumps({"structured_output": out}))
    out_path = tmp_path / "results.md"
    rc = main(["fixtures", "--replay", "--recorded-dir", str(recorded), "--out", str(out_path)])
    assert rc == 0
    assert "6/6" in capsys.readouterr().out and "| 06 |" in out_path.read_text()


def test_cli_replay_missing_recording_is_loud(tmp_path, capsys):
    rc = main(["fixtures", "--replay", "--recorded-dir", str(tmp_path), "--only", "01",
               "--out", str(tmp_path / "r.md")])
    assert rc == 1 and "--record" in capsys.readouterr().err


def test_cli_gate_file_offline_prints_the_comment(capsys, tmp_path):
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    (recorded / "01.json").write_text(json.dumps({"structured_output": gate_out()}))
    rc = main(["gate", "--file", "fixtures/01-referral-brief.md", "--replay", "--recorded-dir", str(recorded)])
    out = capsys.readouterr().out
    assert rc == 0 and out.startswith("NX-GATE: ready\n") and "body_sha256" in out


def test_title_cuts_at_a_word_boundary_and_drops_the_sentence_end():
    from nexportal_gate.__main__ import _title
    long = "Show on the course-load card how many days are left to add a second course, the first week of term. Students keep missing the window."
    t = _title(long)
    assert len(t) <= 72 and not t.endswith("cour") and t.endswith("second") or t.endswith("course,")
    assert _title("Can we get an AI chatbot, this sprint? More text.") == "Can we get an AI chatbot, this sprint"
