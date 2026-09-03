"""draft — the PRD stub. Triaged → Drafted by filling the DoR form from the NX-INTAKE record.

No LLM: the point is that the PRD agent is not ours to build. Every routed question rides the body as
an `NX-OPEN-QUESTION:` line, so Tier 1 fails at the first one until they are answered off the
grammar; the sections intake cannot fill are HTML comments, so they fail Tier 1 as empty until
someone writes them. Outcome, Size and Requester come from the record.
"""
from __future__ import annotations

SECTIONS_TAIL = """## Users

<!-- who, in which moment -->

## Acceptance criteria

<!-- at least two, each testable:
- [ ] WHEN <trigger>, THE SYSTEM SHALL <observable result>.
- [ ] THE SYSTEM SHALL <observable result>. -->

## Design

<!-- a link, "n/a — no UI", or brief: with Goal: / Keep: / Change: / Out of scope: lines -->

## Dependencies

<!-- systems, teams, rules, vendors this touches — or "none — <reason>" -->

## Out of scope

<!-- what is deliberately left out -->

## Size

{size}

## Requester

{requester}
"""


def render_draft(record: dict, *, title: str) -> str:
    """`record` is the parsed NX-INTAKE payload (`requester`, `request`, `tier2`)."""
    tier2 = record.get("tier2") or {}
    size = tier2.get("size") or {}
    requester = (record.get("requester") or "").strip()
    handle = requester if requester.startswith("@") else f"@{requester}"
    request = (record.get("request") or "").replace("-->", "-- >")
    out = [f"# {title}", "",
           f"<!-- Drafted by `nexportal-gate draft` from the NX-INTAKE record. Original request: \"{request}\" -->",
           ""]
    questions = tier2.get("questions") or []
    if questions:
        out += [f"NX-OPEN-QUESTION: {q.get('text', '')} (owner: {q.get('owner', 'requester')})" for q in questions]
        out.append("")
    out += ["## Outcome", "", tier2.get("outcome", "").strip(), ""]
    size_line = (f"{size.get('band', 'M')} — provisional from intake "
                 f"({float(size.get('confidence', 0)):.0%} confidence): {size.get('risk', '')}").strip()
    out.append(SECTIONS_TAIL.format(size=size_line, requester=handle))
    return "\n".join(out)
