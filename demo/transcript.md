# Demo transcript — one issue end to end

Recorded 2026-09-03 with asciinema (`demo/nexportal-gate.cast`, rendered to `demo/nexportal-gate.gif`) by running `scripts/demo.sh` against the live repo and board. Every step is the CLI; the model calls are Claude Code headless with prompt v2.

```text
$ python3 -m nexportal_gate intake Can the big career card start collapsed once a student is past the first phase? It takes half the screen and most of them have seen it a hundred times. --requester learner-success --weekday Wednesday --repo jbreyc/nxu-nexportal
intake: #11 filed → Triaged

Thanks — this is in the Inbox and will be looked at in triage tomorrow (Thursday).

One thing is owed from you before it can go further, ideally by Thursday morning: a definition of "past the first phase" that the team can check against learner data. For example: "has completed their first term", "has earned their first credential", or "has been enrolled more than N weeks". The team does not own that concept and will not guess it. If you can also tell me what you expect learners to reach faster once the card is collapsed (course cards? the deadline rail?), that becomes the acceptance test.

Two smaller questions that can wait for refinement but you can answer now if easy: should a learner be able to pin the card open, and should it ever re-expand on its own?

Provisional size: small — a few days, one change — provided the phase rule can be derived from data the portal already holds. If it depends on progress inside Canvas, it grows and I will come back to you.

The current sprint is committed to what is already In Sprint. If this were pulled ahead of the queue, a same-sized item from Ready would move back to make room; I will name which one at triage if that comes up. No date is promised until it is sized with the definition in hand.

$ python3 -m nexportal_gate draft 11 --repo jbreyc/nxu-nexportal
draft: #11 → Drafted (5 open questions ride the body)

$ python3 -m nexportal_gate gate 11 --repo jbreyc/nxu-nexportal
gate: #11 → needs-info — shape: open-question — NX-OPEN-QUESTION: BLOCKING — Define 'past the first phase' as a rule the team can check: which fact about the learner flips it (completed first term? first course? earned first credential? N weeks enrolled?). The team does not own this concept and cannot pick it for you. (owner: requester)

$ python3 -m nexportal_gate flip 11 Ready --repo jbreyc/nxu-nexportal
flip: REFUSED #11 → Ready — newest NX-GATE record says needs-info — run: nexportal-gate gate 11

$ # the requester answers the questions — the body becomes the spec

$ python3 -m nexportal_gate body 11 --file seed/11-career-card-collapsed.md --repo jbreyc/nxu-nexportal
body: #11 replaced from seed/11-career-card-collapsed.md (hash 0a61e0ff)

$ python3 -m nexportal_gate gate 11 --repo jbreyc/nxu-nexportal
gate: #11 → ready

$ python3 -m nexportal_gate flip 11 Ready --repo jbreyc/nxu-nexportal
flip: #11 → Ready (fresh NX-GATE record 0a61e0ff)

$ # done — issue #11 carries the whole trail
```
