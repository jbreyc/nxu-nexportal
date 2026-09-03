#!/usr/bin/env python3
"""hooks/wall.py — the lock on door 2.

PreToolUse on Bash. The hook sees the command TEXT only. A raw `gh project item-edit` that names this
board's project id or its Status field id is denied and pointed at the sanctioned door —
`nexportal-gate flip <issue> <Status>` — which evaluates the rule (`board.check_flip`). The rule
lives once, in board.py; this file does not re-evaluate it: door 2 is locked, door 1 is guarded.
`flip`'s own nested gh call never appears in a Bash command's text, so it passes by construction;
a compound `…; gh project item-edit …` still carries the raw write and is still caught.

Fail-open honesty: a hook that crashes lets the call through invisibly, so every path here exits 0
and prints either a decision or nothing. No board.toml ⇒ nothing to protect ⇒ silent.
"""
import json
import os
import sys
import tomllib
from pathlib import Path

REASON = ("This board's Status is written only through `nexportal-gate flip <issue> <Status>`, which checks "
          "the newest NX-GATE record against the body as it is now. A raw `gh project item-edit` is the "
          "unguarded door — use flip.")


def load_cfg():
    for root in (os.environ.get("CLAUDE_PLUGIN_ROOT"), os.getcwd()):
        path = Path(root) / "board.toml" if root else None
        if path and path.exists():
            try:
                return tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                return None
    return None


def decide(hook: dict, cfg: dict | None) -> dict | None:
    if not cfg or hook.get("tool_name") != "Bash":
        return None
    cmd = (hook.get("tool_input") or {}).get("command") or ""
    if "gh project item-edit" not in cmd:
        return None
    ids = (cfg.get("project_id"), (cfg.get("fields") or {}).get("status"))
    if not any(i and i in cmd for i in ids):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": REASON}}


def main() -> int:
    try:
        hook = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    out = decide(hook, load_cfg())
    if out:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
