---
description: Triage a raw request at the door — outcome, urgency vs evidence, duplicate check, provisional size, routed questions, the message back
argument-hint: "<request text>" --requester <name>
allowed-tools: Bash(python3 -m nexportal_gate:*), Bash(nexportal-gate:*)
---
Run intake with the arguments exactly as given, from the repo root:

    python3 -m nexportal_gate intake $ARGUMENTS

Then relay, in this order and nothing else: the issue number filed (or the duplicate it matched, and that no issue was created); the outcome the record states; the size band and confidence; the questions with their owners; the message to the requester, quoted. Do not file anything yourself. Do not answer the questions on the requester's behalf.
