"""The CLI's live paths through argparse, against a fake gh and replayed model responses."""
import json
from pathlib import Path

import pytest

from nexportal_gate import __main__ as cli
from nexportal_gate import adversary

GOOD = Path("fixtures/01-referral-brief.md").read_text(encoding="utf-8").split("---\n", 2)[2]
BLOCK = {"text": "t", "why_it_bites_mid_build": "w", "owner": "requester", "blocking": True}


def gate_out(verdict="ready", **over):
    base = {"verdict": verdict, "steelman": "s", "ambiguities": [], "untestable_criteria": [],
            "hidden_dependencies": [], "size": {"band": "S", "confidence": 0.8, "risk": "r"},
            "refinement_agenda": [], "requester_message": "m"}
    base.update(over)
    return base


def intake_out():
    return {"outcome": "o", "urgency": {"claim": "c", "evidence": "e", "assessment": "a"},
            "duplicate": {"is_duplicate": False, "of_issue": None, "why": ""},
            "size": {"band": "M", "confidence": 0.6, "risk": "r"},
            "questions": [{"text": "q", "owner": "requester"}], "requester_message": "m"}


class FakeGh:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def __call__(self, argv, *, stdin=None):
        self.calls.append((list(argv), stdin))
        for prefix, out in self.responses:
            if tuple(argv[:len(prefix)]) == tuple(prefix):
                return out
        raise AssertionError(f"unexpected gh call: {argv}")


def item_graphql(status):
    return json.dumps({"data": {"repository": {"issue": {"state": "OPEN", "projectItems": {"nodes": [
        {"id": "PVTI_2", "project": {"number": 1}, "status": {"name": status}, "reason": None}]}}}}})


def recorded(tmp_path, key, out, version=2):
    d = tmp_path / "recorded"
    d.mkdir(exist_ok=True)
    (d / f"{key}.json").write_text(json.dumps({"structured_output": out, "prompt_version": version}))
    return d


# --- finding 3: gate on a Ready card ------------------------------------------------------------

def test_gate_on_a_ready_card_records_and_warns_to_flip_back(tmp_path, monkeypatch, capsys):
    d = recorded(tmp_path, "issue-2", gate_out("needs-info", ambiguities=[BLOCK]))
    gh = FakeGh([(("issue", "view"), json.dumps({"number": 2, "title": "t", "body": GOOD, "state": "OPEN", "comments": []})),
                 (("api", "graphql"), item_graphql("Ready")), (("issue", "comment"), ""), (("project", "item-edit"), "")])
    monkeypatch.setattr(cli, "GH", gh)
    rc = cli.main(["gate", "2", "--replay", "--recorded-dir", str(d), "--repo", "o/r", "--board", "board.toml"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "Ready" in err and "flip 2 Drafted" in err
    assert any(a[:2] == ["issue", "comment"] and s.startswith("NX-GATE: needs-info") for a, s in gh.calls)


def test_gate_on_a_drafted_card_does_not_warn(tmp_path, monkeypatch, capsys):
    d = recorded(tmp_path, "issue-2", gate_out("needs-info", ambiguities=[BLOCK]))
    gh = FakeGh([(("issue", "view"), json.dumps({"number": 2, "title": "t", "body": GOOD, "state": "OPEN", "comments": []})),
                 (("api", "graphql"), item_graphql("Drafted")), (("issue", "comment"), ""), (("project", "item-edit"), "")])
    monkeypatch.setattr(cli, "GH", gh)
    assert cli.main(["gate", "2", "--replay", "--recorded-dir", str(d), "--repo", "o/r", "--board", "board.toml"]) == 0
    assert "flip 2 Drafted" not in capsys.readouterr().err


# --- finding 5: cosmetic keys -------------------------------------------------------------------

def test_gate_file_names_the_file_in_the_rerun_hint(tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_text('---\nid: "x"\n---\n## Outcome\nx\n')
    rc = cli.main(["gate", "--file", str(bad), "--replay", "--recorded-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0 and f"nexportal-gate gate --file {bad}" in out and "gate 0" not in out


def test_intake_record_key_is_content_addressed(tmp_path, capsys):
    text = "Can we get an AI chatbot, this sprint? It should be quick."
    key = cli.intake_key(text)
    assert key.startswith("intake-") and len(key) == len("intake-") + 8 and key == cli.intake_key(text + " ")
    d = recorded(tmp_path, key, intake_out())
    rc = cli.main(["intake", text, "--requester", "ceo", "--replay", "--recorded-dir", str(d),
                   "--open-issues", "fixtures/open-issues.json", "--dry-run"])
    assert rc == 0 and capsys.readouterr().out.startswith("NX-INTAKE: triaged")


# --- finding 1: the timeout -----------------------------------------------------------------------

def test_default_timeout_is_300_and_the_flag_reaches_the_client():
    assert adversary.ClaudeCodeClient().timeout == 300
    args = cli.build_parser().parse_args(["gate", "1", "--timeout", "42"])
    assert cli._client(args, Path("prompts"), Path("x")).timeout == 42


def test_client_passes_its_timeout_to_the_runner():
    seen = {}

    def runner(argv, **kw):
        seen.update(kw)

        class P:
            returncode, stdout, stderr = 0, json.dumps({"is_error": False, "structured_output": {"ok": 1}}), ""
        return P()
    adversary.ClaudeCodeClient(runner=runner, timeout=7).complete("s", "u", {}, key="k")
    assert seen["timeout"] == 7


# --- finding 2: replay checks the recorded prompt version ------------------------------------------

def test_replay_tracks_versions_and_warns_on_mismatch(tmp_path, capsys):
    (tmp_path / "k.json").write_text(json.dumps({"structured_output": {"v": 1}, "prompt_version": 1}))
    c = adversary.ReplayClient(tmp_path, prompt_version=2)
    assert c.complete("s", "u", {}, key="k") == {"v": 1}
    assert c.versions_seen == {1} and "prompt v1" in capsys.readouterr().err


def test_replay_is_silent_when_versions_match(tmp_path, capsys):
    (tmp_path / "k.json").write_text(json.dumps({"structured_output": {"v": 2}, "prompt_version": 2}))
    adversary.ReplayClient(tmp_path, prompt_version=2).complete("s", "u", {}, key="k")
    assert capsys.readouterr().err == ""


def test_fixtures_replay_notes_the_recorded_prompt_version_in_the_table(tmp_path, capsys):
    outs = {"01": gate_out(), "02": gate_out("needs-info", ambiguities=[BLOCK, dict(BLOCK, owner="design"), BLOCK]),
            "03": intake_out(), "04": intake_out(), "05": gate_out("needs-info"), "06": intake_out()}
    d = tmp_path / "recorded"
    d.mkdir()
    for k, o in outs.items():
        (d / f"{k}.json").write_text(json.dumps({"structured_output": o, "prompt_version": 1}))
    out_path = tmp_path / "results.md"
    assert cli.main(["fixtures", "--replay", "--recorded-dir", str(d), "--out", str(out_path)]) == 0
    table = out_path.read_text()
    assert "recorded under prompt v1" in table and "current prompt is v2" in table and "WARNING" in table


# --- finding 4: body <n> --file ------------------------------------------------------------------

def test_body_sets_the_issue_body_from_a_file_stripping_frontmatter(tmp_path, monkeypatch, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text('---\ntitle: "t"\nversion: 3\n---\n## Outcome\n\nx\n')
    gh = FakeGh([(("issue", "edit"), ""), (("api", "graphql"), item_graphql("Drafted"))])
    monkeypatch.setattr(cli, "GH", gh)
    assert cli.main(["body", "2", "--file", str(spec), "--repo", "o/r", "--board", "board.toml"]) == 0
    argv, stdin = next((a, s) for a, s in gh.calls if a[:2] == ["issue", "edit"])
    assert stdin == "## Outcome\n\nx\n" and argv[argv.index("--body-file") + 1] == "-"
    out = capsys.readouterr()
    assert "body: #2" in out.out and out.err == ""


def test_body_on_a_ready_card_warns_that_the_record_is_stale(tmp_path, monkeypatch, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("## Outcome\n\ny\n")
    gh = FakeGh([(("issue", "edit"), ""), (("api", "graphql"), item_graphql("Ready"))])
    monkeypatch.setattr(cli, "GH", gh)
    assert cli.main(["body", "2", "--file", str(spec), "--repo", "o/r", "--board", "board.toml"]) == 0
    err = capsys.readouterr().err
    assert "Ready" in err and "gate 2" in err and "flip 2 Drafted" in err


def test_body_dry_run_prints_and_writes_nothing(tmp_path, monkeypatch, capsys):
    spec = tmp_path / "spec.md"
    spec.write_text("## Outcome\n\nz\n")
    gh = FakeGh([])
    monkeypatch.setattr(cli, "GH", gh)
    assert cli.main(["body", "2", "--file", str(spec), "--repo", "o/r", "--dry-run"]) == 0
    assert capsys.readouterr().out == "## Outcome\n\nz\n" and gh.calls == []
