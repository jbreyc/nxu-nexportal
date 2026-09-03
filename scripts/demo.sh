#!/usr/bin/env bash
# scripts/demo.sh — one issue end to end, for the recording (≤ 2 minutes of terminal).
#   intake → draft → gate (fails Tier 1 on the open questions) → flip refused → the questions answered
#   → gate (Tier 2) → flip allowed. Every step is the real CLI against the real board.
# Usage: scripts/demo.sh [--repo owner/name]   (run from the repo root, Claude Code logged in, gh with project scope)
set -euo pipefail
REPO="${2:-jbreyc/nxu-nexportal}"
say() { printf '\n\033[1;36m$ %s\033[0m\n' "$*"; sleep "${PAUSE:-1.5}"; }
run() { say "$*"; "$@" || true; }

run python3 -m nexportal_gate intake "Show on the course-load card how many days are left to add a second course, the first week of term. Students keep missing the window." --requester registrar --weekday Wednesday --repo "$REPO" | tee /tmp/nx-demo-intake.txt
N="$(grep -oE 'intake: #[0-9]+' /tmp/nx-demo-intake.txt | grep -oE '[0-9]+' | head -1)"
[ -n "$N" ] || { echo "no issue number in the intake output"; exit 1; }

run python3 -m nexportal_gate draft "$N" --repo "$REPO"
run python3 -m nexportal_gate gate "$N" --repo "$REPO"
run python3 -m nexportal_gate flip "$N" Ready --repo "$REPO"

say "# the requester answers the questions — the body becomes the spec"
python3 -c "from nexportal_gate.fixtures import split_frontmatter; print(split_frontmatter(open('seed/10-adds-close-countdown.md').read())[1], end='')" | gh issue edit "$N" --repo "$REPO" --body-file - >/dev/null && echo "body replaced"

run python3 -m nexportal_gate gate "$N" --repo "$REPO"
run python3 -m nexportal_gate flip "$N" Ready --repo "$REPO"
say "# done — issue #$N carries the whole trail"
