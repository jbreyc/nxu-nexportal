#!/usr/bin/env bash
# SessionStart: the state machine and the two commands. Nothing else.
python3 - <<'PY'
import json
text = """nexportal-gate — the readiness gate for NexPortal (the student portal), on the team's own surfaces.
State machine: Inbox → Triaged → Drafted → Ready → In Sprint → Done   (Drafted ↔ Needs-info)
  /intake "<text>" --requester <name>   the door: triage a raw request, file it or flag the duplicate
  /gate <issue#>                        before refinement: Tier 1 shape, Tier 2 adversary, NX-GATE record
  nexportal-gate flip <issue#> <Status> the guarded door — refuses Ready without a fresh NX-GATE record (exit 3)
  nexportal-gate audit                  Ready items without a fresh record
Door 2 is locked: a raw `gh project item-edit` on this board's Status is denied by the PreToolUse hook. Use flip."""
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
PY
exit 0
