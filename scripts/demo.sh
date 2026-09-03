#!/usr/bin/env bash
# scripts/demo.sh — one issue end to end, for the recording (≤ 2 minutes of terminal).
#   intake → draft → gate (fails Tier 1 on the open questions) → flip refused → the questions answered
#   → gate (Tier 2) → flip allowed. Every step is the real CLI against the real board.
# Usage: scripts/demo.sh [--repo owner/name]   (run from the repo root, Claude Code logged in, gh with project scope)
set -euo pipefail
REPO="${2:-jbreyc/nxu-nexportal}"
REQUEST="${REQUEST:-Can the big career card start collapsed once a student is past the first phase? It takes half the screen and most of them have seen it a hundred times.}"
REQUESTER="${REQUESTER:-learner-success}"
SPEC="${SPEC:-seed/11-career-card-collapsed.md}"
say() { printf '\n\033[1;36m$ %s\033[0m\n' "$*"; sleep "${PAUSE:-1.5}"; }
run() { say "$*"; "$@" || true; }

run python3 -m nexportal_gate intake "$REQUEST" --requester "$REQUESTER" --weekday Wednesday --repo "$REPO" | tee /tmp/nx-demo-intake.txt
N="$(grep -oE 'intake: #[0-9]+' /tmp/nx-demo-intake.txt | grep -oE '[0-9]+' | head -1)"
[ -n "$N" ] || { echo "no issue was filed (a duplicate, or a rejection) — change REQUEST and run again"; exit 1; }

run python3 -m nexportal_gate draft "$N" --repo "$REPO"
run python3 -m nexportal_gate gate "$N" --repo "$REPO"
run python3 -m nexportal_gate flip "$N" Ready --repo "$REPO"

say "# the requester answers the questions — the body becomes the spec"
run python3 -m nexportal_gate body "$N" --file "$SPEC" --repo "$REPO"

run python3 -m nexportal_gate gate "$N" --repo "$REPO"
run python3 -m nexportal_gate flip "$N" Ready --repo "$REPO"
say "# done — issue #$N carries the whole trail"
