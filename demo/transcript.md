# Demo transcript — one issue end to end

Recorded 2026-09-03 with asciinema (`demo/nexportal-gate.cast`, rendered to `demo/nexportal-gate.gif`) by running `scripts/demo.sh` against the live repo and board. Every command is the real CLI; the model calls are Claude Code headless with prompt v2.

```text
$ python3 -m nexportal_gate intake Show on the course-load card how many days are left to add a second course, the first week of term. Students keep missing the window. --requester registrar --weekday Wednesday --repo jbreyc/nxu-nexportal
intake: #10 filed → Triaged

Your request is in the Inbox and goes to triage tomorrow, Thursday. It is a small build if the team can get the date, and it will not be built for this term — adds close this week, so the earliest it can help is the October start.

Two things are owed from you before tomorrow, because nobody on the team can supply them:

1. The exact rule. "Day 5 of the term" — counted from which date, calendar or business days, inclusive or not, what time of day and which timezone the window shuts, and whether the seminar counts as one of the two courses. If the engineer has to guess this, students will see the wrong number.
2. Where the date lives. Which system or person holds the term start date or the add-close date today. myNXU has no such field; if it has to come from the SIS as a new feed, the work roughly doubles.

Also useful, not required for the build: how many students missed the window in the last three starts and how you know. That decides where it sits in the queue, not whether it is done.

If this jumps ahead at triage, it takes a slot from whatever is last in the Ready column for the sprint that starts after triage; I will name that item in the room tomorrow so the trade is explicit. I cannot give you a landing date until the two questions above are answered and the team has sized it with the source in hand.

$ python3 -m nexportal_gate draft 10 --repo jbreyc/nxu-nexportal
draft: #10 → Drafted (8 open questions ride the body)

$ python3 -m nexportal_gate gate 10 --repo jbreyc/nxu-nexportal
gate: #10 → needs-info — shape: open-question — NX-OPEN-QUESTION: BLOCKING — the exact rule: 'day 5 of the term' counts from which date (first day of the monthly start? Canvas course open date?), calendar or business days, inclusive or exclusive, cutoff time and timezone, and whether the seminar counts as a course toward the two-course limit. Due before Thursday triage. (owner: requester)

$ python3 -m nexportal_gate flip 10 Ready --repo jbreyc/nxu-nexportal
flip: REFUSED #10 → Ready — newest NX-GATE record says needs-info — run: nexportal-gate gate 10

$ # the requester answers the questions — the body becomes the spec
body replaced

$ python3 -m nexportal_gate gate 10 --repo jbreyc/nxu-nexportal
gate: #10 → ready

$ python3 -m nexportal_gate flip 10 Ready --repo jbreyc/nxu-nexportal
flip: #10 → Ready (fresh NX-GATE record 3a8c8e52)

$ # done — issue #10 carries the whole trail
```
