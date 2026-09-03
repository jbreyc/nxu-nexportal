"""nexportal-gate — a readiness gate at two positions of NexPortal's operating model.

`intake` at the door (a raw request), `gate` before refinement (a drafted spec); one enforced rule:
no Ready without a fresh gate record. Stdlib only; the LLM tier runs through Claude Code headless.
"""

__version__ = "0.1.0"
