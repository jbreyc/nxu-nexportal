# nxu-nexportal — a readiness gate for NexPortal

A working prototype of the AI piece of NexPortal's operating model: a **readiness gate** at two positions — `intake` at the door (a raw request), `gate` before refinement (a drafted spec) — so nothing unscoped reaches an engineer, and **one enforced rule**: no card moves to Ready without a fresh gate record for the body as it is now. Built for the surfaces the team already has — GitHub issues, a Projects board, the terminal, Claude Code — and scaled down from the [Yellow Robots dev factory](https://github.com/yellow-robots/factory). The writeup is [`WRITEUP.md`](WRITEUP.md); the board is [jbreyc/projects/1](https://github.com/users/jbreyc/projects/1); one issue end to end, recorded, is below.

![one issue end to end](demo/nexportal-gate.gif)

```
Inbox → Triaged → Drafted → Ready → In Sprint → Done
                      ↑          |
                      └──────────┘  (Needs-info, Reason set)
```

| Command | Position | What it does · what it writes |
|---|---|---|
| `nexportal-gate intake "<text>" --requester <name>` | the door | Structure check → shortlist of open issues it may duplicate → one model call. Files the issue with an `NX-INTAKE:` record (outcome, urgency vs evidence, size + confidence, routed questions, the message back), sets Triaged / Size / Requester. A confirmed duplicate posts the note on the existing issue and creates nothing. |
| `nexportal-gate draft <n>` | Triaged → Drafted | Fills the Definition-of-Ready form from the intake record. A template, no model — the PRD agent is assumed, not built. Open questions ride the body as `NX-OPEN-QUESTION:` lines, so the gate fails on them until answered. |
| `nexportal-gate gate <n>` | before refinement | Tier 1 (no model): the form's shape. Tier 2 (Claude Code headless, JSON schema): steelman, blocking vs non-blocking ambiguities with owners, untestable criteria, hidden dependencies against [`context/platform.md`](context/platform.md), size, a ≤ 3-item agenda, the message. Posts one `NX-GATE:` record carrying `body_sha256`; sets or clears Reason. The tool disposes of the verdict; the model's own is kept beside it. |
| `nexportal-gate flip <n> <Status>` | the guarded door | Ready needs the newest `NX-GATE:` record to say `ready` **and** to hash to the current body. Refusal: exit 3, nothing written, the command named. |
| `nexportal-gate audit` | the door that can't be locked | Ready items whose newest record is missing, not `ready`, or stale (a card dragged in the web UI). Detect where prevention is impossible. |
| `/intake`, `/gate` + a PreToolUse hook | the Claude Code plugin | The two commands call the CLI and relay the record. The hook denies a raw `gh project item-edit` on this board's Status and points at `flip` — [`hooks/DENIAL.md`](hooks/DENIAL.md) is a live transcript. |

## Verify it — three postures

**1. Nothing installed — read the trail.**

| Issue | What it shows |
|---|---|
| [#1](https://github.com/jbreyc/nxu-nexportal/issues/1) | The Part 0 Q4 design brief. v1 → `NX-GATE: needs-info` with five blocking gaps (prompt v1); v2 of the brief → `needs-info` again under prompt v1 and a **refused flip**; under prompt v2 → `ready` and the flip **allowed**. Also the duplicate note from fixture 06. |
| [#2](https://github.com/jbreyc/nxu-nexportal/issues/2) | The vague spec: shape passes; `needs-info` under both prompts (no problem statement, three untestable criteria); a refused flip — the wall wrote nothing. |
| [#3](https://github.com/jbreyc/nxu-nexportal/issues/3) | The CEO's chatbot, through the door: `NX-INTAKE:` (no learner outcome, XL, the message that names Thursday and what moves out) → `draft` → `gate` fails Tier 1 at the first open question. |
| [#4](https://github.com/jbreyc/nxu-nexportal/issues/4) | Marketing's Friday ask: triaged; the message separates the Monday extract from the dashboard. |
| [#5](https://github.com/jbreyc/nxu-nexportal/issues/5) | The trap: Tier 1 passes a well-formed spec; Tier 2 names — under both prompts — whether the payments provider can allocate one payment to a chosen set of invoices. |
| [#6](https://github.com/jbreyc/nxu-nexportal/issues/6) | The deadline rail, three generations: v1, v2 and v3 each drew finer blocking findings under prompt v1 (the calibration lesson below); v3 under prompt v2 → `ready` → flipped. |
| [#10](https://github.com/jbreyc/nxu-nexportal/issues/10) | The recorded demo: `intake` → `draft` (eight open questions) → `gate` fails Tier 1 → `flip` refused → the questions answered → `gate` `ready` → `flip` allowed. [`demo/transcript.md`](demo/transcript.md), [`demo/nexportal-gate.cast`](demo/nexportal-gate.cast). |

The six pre-registered cases: [`fixtures/results.md`](fixtures/results.md) (prompt v2, 4/6) and [`fixtures/results.v1.md`](fixtures/results.v1.md) (prompt v1, 3/6). The verdicts in [`fixtures/expected.json`](fixtures/expected.json) were frozen before the first run and never edited — git history is the proof; misses stay in the table with a reading.

**The calibration lesson.** Prompt v1 defined *blocking* as "an engineer would have to guess mid-build" — and by that bar every real spec has something, forever: three generations of the rail each produced a new layer of true-but-finer findings. The gate sits *before* refinement; its job is to make refinement possible, not to replace it. Prompt v2 ([`prompts/system.md`](prompts/system.md), commit `b8c7256`, made before any re-run) defines blocking as *refinement cannot settle it in the room — the requester must supply something the team does not have*. Under v2 the two specs that had earned it reached Ready; the vague spec and the trap did not. Pre-registration made the miscalibration visible in an afternoon.

**2. Clone, no key — reproduce the table and run the tests.** Python 3.11+, stdlib only.

```
git clone https://github.com/jbreyc/nxu-nexportal && cd nxu-nexportal
python3 -m nexportal_gate fixtures --replay      # the six cases from the recorded responses → fixtures/results.md
python3 -m pytest -q                             # 123 tests, no network, no model
python3 -m nexportal_gate gate --file fixtures/02-vague-dashboard.md --replay   # one record, printed
```

**3. With Claude Code (logged in) and `gh` (with the `project` scope) — run it live.**

```
python3 -m nexportal_gate fixtures                # the six cases, live (~7 min); --record to refresh the recordings
python3 -m nexportal_gate gate 2                  # against the demo repo: posts the record, sets Reason
python3 -m nexportal_gate flip 2 Ready            # refused, exit 3
python3 -m nexportal_gate audit                   # clean
bash scripts/demo.sh                              # one fresh request end to end (what the recording shows)
claude --plugin-dir .                             # then: /gate 2 · /intake "…" --requester you
```

Inside that session, ask Claude to run a raw `gh project item-edit` on the board: the hook denies it with the reason ([`hooks/DENIAL.md`](hooks/DENIAL.md)).

## Layout

```
nexportal_gate/   text · shape (Tier 1) · adversary (Tier 2, three clients) · intake · draft · records · board (the wall) · fixtures · seed · __main__
prompts/          system.md (versioned; v2) · gate.md · intake.md · the two JSON schemas
context/          platform.md — the stated assumptions the gate judges hidden dependencies against
fixtures/         the six cases · expected.json (frozen) · recorded/ · results.md · results.v1.md · readings.json · open-issues.json
seed/             the brief's v2, the rail's v2 and v3, the four fillers, the demo's answered spec
demo/ scripts/    the recording (.cast, .gif, transcript) and the script that produced it
hooks/ commands/ .claude-plugin/   the Claude Code plugin
.github/ISSUE_TEMPLATE/   spec.yml — the form IS the Definition of Ready · request.yml — the stakeholder door
board.toml        the board's identifiers (rendered by `nexportal-gate board-ids`)
```

## Assumptions, stated

- [`context/platform.md`](context/platform.md) is what the gate knows about NexPortal. Correct it and the judgement moves with it.
- The team runs Claude Code. The adversary is `claude -p --json-schema` on the existing subscription — no SDK, no API key. If not, `adversary.py`'s `Client` protocol takes a small SDK client.
- `fixtures/open-issues.json` mirrors the seed order (#1, #2, #5 and the open fillers), so the offline duplicate check reads the same board the live one did.
- The web UI can still drag a card to Ready. `audit` names it; nothing here pretends otherwise.

## Provenance

Scaled down from the [factory](https://github.com/yellow-robots/factory): the patterns kept are *the model proposes, the gate disposes*; records on the trail with a marker readers match at column 0; the board as the system of record; fail-closed to the human at the one-way door. Left out on purpose: dispatch, the runner, epics, the ledger, the bench, the process model. Freshness by body hash instead of timestamps is the one thing that goes back the other way.
