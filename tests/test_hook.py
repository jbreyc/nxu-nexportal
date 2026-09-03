"""hooks/wall.py — the lock on door 2: a raw `gh project item-edit` against this board's Status."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
WALL = ROOT / "hooks" / "wall.py"
CFG = tomllib.loads((ROOT / "board.toml").read_text(encoding="utf-8"))


def load_wall():
    spec = importlib.util.spec_from_file_location("wall", WALL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": "s"}


RAW = (f"gh project item-edit --id PVTI_x --project-id {CFG['project_id']} "
       f"--field-id {CFG['fields']['status']} --single-select-option-id {CFG['options']['status']['Ready']}")


def test_denies_a_raw_status_write():
    out = load_wall().decide(bash(RAW), CFG)
    h = out["hookSpecificOutput"]
    assert h["hookEventName"] == "PreToolUse" and h["permissionDecision"] == "deny"
    assert "nexportal-gate flip" in h["permissionDecisionReason"]


def test_denies_by_project_id_alone():
    cmd = f"gh project item-edit --id PVTI_x --project-id {CFG['project_id']} --field-id F --clear"
    assert load_wall().decide(bash(cmd), CFG)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_denies_the_compound_bypass():
    cmd = "python -m nexportal_gate flip 2 Ready; " + RAW
    assert load_wall().decide(bash(cmd), CFG) is not None


def test_silent_on_the_sanctioned_door():
    assert load_wall().decide(bash("python -m nexportal_gate flip 2 Ready"), CFG) is None
    assert load_wall().decide(bash("nexportal-gate flip 2 Ready"), CFG) is None


def test_silent_on_unrelated_commands_and_tools():
    wall = load_wall()
    assert wall.decide(bash("gh issue list --repo jbreyc/nxu-nexportal"), CFG) is None
    assert wall.decide(bash("gh project item-edit --id X --project-id PVT_other --field-id F --clear"), CFG) is None
    assert wall.decide({"tool_name": "Read", "tool_input": {"file_path": "x"}}, CFG) is None


def test_silent_when_there_is_no_board():
    assert load_wall().decide(bash(RAW), None) is None


def test_script_reads_hook_json_from_stdin_and_finds_board_toml_via_plugin_root():
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(ROOT))
    proc = subprocess.run([sys.executable, str(WALL)], input=json.dumps(bash(RAW)), capture_output=True,
                          text=True, env=env, cwd="/")
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_script_is_silent_and_exits_zero_on_garbage():
    proc = subprocess.run([sys.executable, str(WALL)], input="not json", capture_output=True, text=True)
    assert proc.returncode == 0 and proc.stdout.strip() == ""
