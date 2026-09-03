---
description: Run the readiness gate on a drafted spec — Tier 1 shape, Tier 2 adversary — and post the NX-GATE record
argument-hint: <issue#>
allowed-tools: Bash(python3 -m nexportal_gate:*), Bash(nexportal-gate:*)
---
Run the gate on issue $ARGUMENTS of the current repo, from the repo root:

    python3 -m nexportal_gate gate $ARGUMENTS

Then relay, in this order and nothing else: the verdict; if Tier 1 failed, the first failing check and the rest; otherwise the reasons, the refinement agenda and the message to the requester — quoted from the record, not paraphrased. Do not edit the issue. Do not re-run. If the verdict is `ready`, say that the human can now run `nexportal-gate flip $ARGUMENTS Ready`.
