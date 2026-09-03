"""records — the NX- record grammar on the issue trail.

One comment per run. Line 1 at column 0 is the marker and the verdict (`NX-GATE: ready`,
`NX-INTAKE: duplicate`); readers match by prefix with no whitespace tolerance — an indented or
blockquoted marker is prose, not a record. Then a
human summary; then exactly one fenced JSON payload, the machine-read record. `body_sha256` in a
gate record is what the wall compares against the body as it is now.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .adversary import GateResult
from .intake import IntakeResult
from .text import marker_line_matches

GATE_MARKER = "NX-GATE:"
INTAKE_MARKER = "NX-INTAKE:"
MARKERS = (GATE_MARKER, INTAKE_MARKER)
_FENCE_RE = re.compile(r"```json\n(.*?)\n```", re.S)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fence(payload: dict) -> str:
    return "```json\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n```\n"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def render_gate_comment(result: GateResult, *, issue: int) -> str:
    t2 = result.tier2 or {}
    if result.tier1:
        first, rest = result.tier1[0], result.tier1[1:]
        also = (" · also: " + "; ".join(f"`{f.check}` — {f.message}" for f in rest)) if rest else ""
        summary = (f"**Tier 1 failed at `{first.check}`:** {first.message}{also}\n"
                   f"Tier 2 skipped. Fix and rerun `nexportal-gate gate {issue}`.\n")
    else:
        blocking = [a for a in t2.get("ambiguities") or [] if a.get("blocking") and a.get("owner") != "engineering"]
        owners = ", ".join(sorted({a.get("owner", "?") for a in blocking})) or "none"
        size = t2.get("size") or {}
        summary = (f"**Tier 1:** passed · **Tier 2:** {_plural(len(blocking), 'blocking ambiguity', 'blocking ambiguities')} "
                   f"({owners}) · {_plural(len(t2.get('untestable_criteria') or []), 'untestable criterion', 'untestable criteria')} · "
                   f"{_plural(len(t2.get('hidden_dependencies') or []), 'hidden dependency', 'hidden dependencies')} · "
                   f"size {size.get('band')} ({size.get('confidence')})\n")
        if result.reasons:
            summary += "**Why:** " + " · ".join(result.reasons) + "\n"
        if t2.get("steelman"):
            summary += f"**Steelman:** {t2['steelman']}\n"
        agenda = t2.get("refinement_agenda") or []
        if agenda:
            summary += "**Agenda:** " + " ".join(f"{i}) {a}" for i, a in enumerate(agenda, 1)) + "\n"
        if t2.get("requester_message"):
            summary += f"**Message to the requester:** {t2['requester_message']}\n"
    payload = {"schema": "nx-gate/1", "verdict": result.verdict, "model_verdict": result.model_verdict,
               "body_sha256": result.body_sha256, "prompt_version": result.prompt_version,
               "model": result.model, "ts": _ts(),
               "tier1": [[f.check, f.message] for f in result.tier1], "tier2": result.tier2,
               "reasons": result.reasons}
    return f"{GATE_MARKER} {result.verdict}\n{summary}\n{_fence(payload)}"


def render_intake_comment(result: IntakeResult, *, requester: str, text: str) -> str:
    t2 = result.tier2 or {}
    handle = requester if requester.startswith("@") else f"@{requester}"
    request = text.strip()
    if result.status == "duplicate":
        dup = t2.get("duplicate") or {}
        summary = (f"**Duplicate of #{result.duplicate_of}** — {dup.get('why', '')}\n"
                   f"Asked again by {handle}: \"{request}\". No new issue created.\n")
    elif result.status == "rejected":
        first = result.failures[0]
        summary = f"**Rejected at the door:** `{first.check}` — {first.message}\n"
    else:
        size, urgency = t2.get("size") or {}, t2.get("urgency") or {}
        questions = t2.get("questions") or []
        summary = (f"**Requester:** {handle} · **Request:** \"{request}\"\n"
                   f"**Outcome:** {t2.get('outcome', '')}\n"
                   f"**Urgency:** {urgency.get('assessment', '')}\n"
                   f"**Size:** {size.get('band')} ({size.get('confidence')}) — {size.get('risk', '')}\n")
        if questions:
            summary += "**Questions:** " + " ".join(f"{i}) {q.get('text', '')} ({q.get('owner', '?')})"
                                                     for i, q in enumerate(questions, 1)) + "\n"
        if result.reasons:
            summary += "**Note:** " + " · ".join(result.reasons) + "\n"
    if result.status != "rejected" and t2.get("requester_message"):
        summary += f"**Message to {handle}:** {t2['requester_message']}\n"
    payload = {"schema": "nx-intake/1", "status": result.status, "requester": requester,
               "request": request, "prompt_version": result.prompt_version, "model": result.model,
               "ts": _ts(), "duplicate_of": result.duplicate_of, "shortlist": result.shortlist,
               "tier2": result.tier2, "reasons": result.reasons}
    return f"{INTAKE_MARKER} {result.status}\n{summary}\n{_fence(payload)}"


def parse_record(comment_body: str) -> dict | None:
    """The payload of a record comment, plus `_marker` and `_verdict`; None for anything else."""
    body = comment_body.replace("\r\n", "\n")
    first = body.split("\n", 1)[0]
    for marker in MARKERS:
        if not marker_line_matches(first, marker):
            continue
        m = _FENCE_RE.search(body)
        if not m:
            return None
        try:
            payload = json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        payload["_marker"] = marker
        payload["_verdict"] = first[len(marker):].strip()
        return payload
    return None


def newest_record(comments: list[dict], marker: str) -> dict | None:
    """The most recent comment (by `createdAt`) that parses as a record with `marker`."""
    for c in sorted(comments, key=lambda c: c.get("createdAt", ""), reverse=True):
        rec = parse_record(c.get("body", ""))
        if rec and rec["_marker"] == marker:
            return rec
    return None
