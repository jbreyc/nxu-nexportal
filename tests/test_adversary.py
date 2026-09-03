import json
from pathlib import Path

import pytest

from nexportal_gate import adversary
from nexportal_gate.text import body_hash

PROMPTS = Path("prompts")
PLATFORM = Path("context/platform.md").read_text(encoding="utf-8")
GOOD = Path("fixtures/01-referral-brief.md").read_text(encoding="utf-8").split("---\n", 2)[2]


def out(**over):
    base = {"verdict": "ready", "steelman": "s", "ambiguities": [], "untestable_criteria": [],
            "hidden_dependencies": [], "size": {"band": "S", "confidence": 0.8, "risk": "r"},
            "refinement_agenda": [], "requester_message": "m"}
    base.update(over)
    return base


def amb(owner, blocking):
    return {"text": "t", "why_it_bites_mid_build": "w", "owner": owner, "blocking": blocking}


def run(body, client, key="k"):
    return adversary.run_gate(body, client, key=key, prompts_dir=PROMPTS, platform=PLATFORM, model="m")


# --- dispose: the gating rule -------------------------------------------------------------------

def test_dispose_blocking_requester_ambiguity_is_needs_info():
    verdict, reasons = adversary.dispose(out(ambiguities=[amb("requester", True)]))
    assert verdict == "needs-info"
    assert reasons and "requester" in reasons[0]


def test_dispose_non_blocking_only_is_ready():
    assert adversary.dispose(out(ambiguities=[amb("requester", False), amb("design", False)]))[0] == "ready"


def test_dispose_blocking_engineering_ambiguity_is_ready():
    assert adversary.dispose(out(ambiguities=[amb("engineering", True)]))[0] == "ready"


def test_dispose_untestable_is_needs_info():
    assert adversary.dispose(out(untestable_criteria=[{"criterion": "c", "rewrite": "r"}]))[0] == "needs-info"


def test_dispose_blocking_hidden_dependency_is_needs_info():
    deps = [{"name": "payments provider", "why": "w", "blocking": True}]
    verdict, reasons = adversary.dispose(out(hidden_dependencies=deps))
    assert verdict == "needs-info" and "payments provider" in reasons[0]


def test_dispose_non_blocking_hidden_dependency_is_ready():
    deps = [{"name": "n", "why": "w", "blocking": False}]
    assert adversary.dispose(out(hidden_dependencies=deps))[0] == "ready"


# --- run_gate -----------------------------------------------------------------------------------

class Raising:
    def complete(self, *a, **k):
        raise AssertionError("Tier 2 must not run on a shape failure")


def test_run_gate_skips_tier2_on_shape_failure():
    r = run("## Outcome\nx", Raising())
    assert r.verdict == "needs-info" and r.model_verdict is None and r.tier2 is None
    assert r.tier1[0].check == "section:users"


def test_run_gate_records_both_verdicts():
    client = adversary.FakeClient({"k": out(verdict="ready", ambiguities=[amb("design", True)])})
    r = run(GOOD, client)
    assert (r.verdict, r.model_verdict) == ("needs-info", "ready")
    assert r.tier1 == [] and r.body_sha256 == body_hash(GOOD) and r.prompt_version == 2 and r.model == "m"


def test_run_gate_passes_system_platform_body_and_schema_to_the_client():
    class Spy:
        def complete(self, system, user, schema, *, key):
            self.system, self.user, self.schema, self.key = system, user, schema, key
            return out()
    spy = Spy()
    run(GOOD, spy, key="fixture-01")
    assert spy.system.startswith("version: 2") and spy.key == "fixture-01"
    assert "Canvas" in spy.user and GOOD.strip() in spy.user
    assert spy.schema["properties"]["verdict"]["enum"] == ["ready", "needs-info"]


# --- ClaudeCodeClient ---------------------------------------------------------------------------

def fake_runner(*envelopes):
    queue, calls = list(envelopes), []

    def runner(argv, **kw):
        calls.append(argv)
        env = queue.pop(0) if len(queue) > 1 else queue[0]

        class P:
            returncode = 0
            stdout = json.dumps(env)
            stderr = ""
        return P()
    runner.calls = calls
    return runner


def test_claude_argv_shape():
    argv = adversary.ClaudeCodeClient(model="claude-fable-5-1").argv("hello", {"type": "object"}, "SYS")
    assert argv[:3] == ["claude", "-p", "hello"]
    assert argv[argv.index("--model") + 1] == "claude-fable-5-1"
    assert argv[argv.index("--system-prompt") + 1] == "SYS"
    assert json.loads(argv[argv.index("--json-schema") + 1]) == {"type": "object"}
    assert argv[argv.index("--setting-sources") + 1] == "project"
    assert argv[argv.index("--max-turns") + 1] == "1"
    assert "--no-session-persistence" in argv and "--bare" not in argv


def test_claude_complete_parses_structured_output():
    runner = fake_runner({"is_error": False, "structured_output": {"verdict": "ready"}, "result": "{}"})
    client = adversary.ClaudeCodeClient(runner=runner)
    assert client.complete("sys", "user", {"type": "object"}, key="k") == {"verdict": "ready"}
    assert len(runner.calls) == 1


def test_claude_complete_falls_back_to_result_json():
    runner = fake_runner({"is_error": False, "result": json.dumps({"verdict": "ready"})})
    assert adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k") == {"verdict": "ready"}


def test_claude_complete_raises_on_is_error():
    runner = fake_runner({"is_error": True, "result": "Not logged in · Please run /login"})
    with pytest.raises(adversary.AdversaryError, match="Not logged in"):
        adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k")


def test_claude_complete_retries_once_then_raises():
    runner = fake_runner({"is_error": False, "result": "not json"})
    with pytest.raises(adversary.AdversaryError):
        adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k")
    assert len(runner.calls) == 2


# --- replay / recording / fake -------------------------------------------------------------------

def test_replay_reads_recorded_key(tmp_path):
    (tmp_path / "k.json").write_text(json.dumps({"structured_output": {"verdict": "ready"}}))
    assert adversary.ReplayClient(tmp_path).complete("s", "u", {}, key="k") == {"verdict": "ready"}


def test_replay_missing_key_names_record_flag(tmp_path):
    with pytest.raises(adversary.AdversaryError, match="--record"):
        adversary.ReplayClient(tmp_path).complete("s", "u", {}, key="missing")


def test_recording_client_writes_file(tmp_path):
    rec = adversary.RecordingClient(adversary.FakeClient({"k": out()}), tmp_path, model="m", prompt_version=1)
    assert rec.complete("s", "u", {}, key="k") == out()
    saved = json.loads((tmp_path / "k.json").read_text())
    assert saved["structured_output"] == out() and saved["model"] == "m" and saved["prompt_version"] == 1
    assert "ts" in saved


def test_fake_client_unknown_key_raises():
    with pytest.raises(adversary.AdversaryError):
        adversary.FakeClient({}).complete("s", "u", {}, key="k")


# --- prompts ------------------------------------------------------------------------------------

def test_prompt_version_reads_first_line():
    assert adversary.prompt_version("version: 3\n\nrest") == 3
    with pytest.raises(adversary.AdversaryError):
        adversary.prompt_version("no version line")


def test_render_replaces_tokens_only():
    assert adversary.render("a {{x}} {not} {{y}}", x="1", y="2") == "a 1 {not} 2"


def test_claude_transient_error_retries_once_then_raises_with_subtype():
    runner = fake_runner({"is_error": True, "subtype": "error_during_execution", "result": None})
    with pytest.raises(adversary.AdversaryError, match="error_during_execution"):
        adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k")
    assert len(runner.calls) == 2


def test_claude_login_error_does_not_retry():
    runner = fake_runner({"is_error": True, "result": "Not logged in · Please run /login"})
    with pytest.raises(adversary.AdversaryError, match="Not logged in"):
        adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k")
    assert len(runner.calls) == 1


def test_claude_transient_error_then_success():
    runner = fake_runner({"is_error": True, "subtype": "error_during_execution", "result": None},
                         {"is_error": False, "structured_output": {"verdict": "ready"}})
    assert adversary.ClaudeCodeClient(runner=runner).complete("s", "u", {}, key="k") == {"verdict": "ready"}
