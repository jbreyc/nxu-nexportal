"""intake — the door. A raw request, a requester, a weekday.

Structure check (no LLM), a shortlist of open issues the request may duplicate (title + outcome,
5-character stems, overlap ratio — deterministic and cheap), one call, then the tool disposes of
the duplicate claim: a duplicate the model names outside the shortlist is not honoured.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .adversary import Client, load_prompt, load_schema, prompt_version, render
from .shape import PLACEHOLDERS, Failure

STOPWORDS = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "from", "by",
             "at", "is", "are", "be", "can", "we", "get", "this", "that", "it", "so", "let", "our",
             "us", "them", "they", "have", "has", "had", "do", "does", "not", "now", "one", "all",
             "into", "than", "then", "there", "their", "will", "would", "should", "could", "just"}
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'-]*")
DEFAULT_THRESHOLD = 0.2
DEFAULT_LIMIT = 3


def _stems(s: str) -> set[str]:
    """Lowercased content words, cut to a 5-character stem (students/student, friends/friend)."""
    words = (w for w in _WORD_RE.findall(s.lower()) if len(w) >= 3 and w not in STOPWORDS)
    return {w[:5] for w in words}


def similarity(request: str, issue: dict) -> float:
    """Share of the request's stems found in the issue's title + outcome. 0 when nothing overlaps."""
    r = _stems(request)
    if not r:
        return 0.0
    c = _stems(f"{issue.get('title', '')} {issue.get('outcome', '')}")
    return len(r & c) / len(r)


def structure_check(text: str, requester: str) -> list[Failure]:
    failures = []
    if requester.strip().strip(" .").lower() in PLACEHOLDERS:
        failures.append(Failure("requester", "a name or @handle"))
    if len(text.split()) < 3:
        failures.append(Failure("request", "say what you need in at least a sentence"))
    return failures


def shortlist(text: str, open_issues: list[dict], *, limit: int = DEFAULT_LIMIT,
              threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    scored = [(similarity(text, issue), issue) for issue in open_issues]
    kept = [pair for pair in scored if pair[0] >= threshold]
    kept.sort(key=lambda pair: (-pair[0], pair[1].get("number", 0)))   # ties: lowest issue first
    return [dict(issue, score=round(score, 2)) for score, issue in kept[:limit]]


@dataclass
class IntakeResult:
    status: str                      # triaged | duplicate | rejected
    tier2: dict | None
    duplicate_of: int | None
    failures: list[Failure]
    prompt_version: int
    model: str
    shortlist: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def run_intake(text: str, requester: str, open_issues: list[dict], client: Client, *, key: str,
               prompts_dir: Path, platform: str, model: str, weekday: str) -> IntakeResult:
    prompts_dir = Path(prompts_dir)
    system = load_prompt("system.md", prompts_dir)
    version = prompt_version(system)
    failures = structure_check(text, requester)
    if failures:
        first = failures[0]
        return IntakeResult("rejected", None, None, failures, version, model,
                            reasons=[f"structure: {first.check} — {first.message}"])
    candidates = shortlist(text, open_issues)
    numbers = [c["number"] for c in candidates]
    lines = "\n".join(f"#{c['number']} — {c['title']} — {c.get('outcome', '')}" for c in candidates)
    user = render(load_prompt("intake.md", prompts_dir), request=text.strip(), requester=requester,
                  weekday=weekday, candidates=lines or "none", platform=platform)
    out = client.complete(system, user, load_schema("intake.schema.json", prompts_dir), key=key)
    dup = out.get("duplicate") or {}
    reasons: list[str] = []
    if dup.get("is_duplicate"):
        of = dup.get("of_issue")
        if of in numbers:
            return IntakeResult("duplicate", out, of, [], version, model, numbers,
                                [f"duplicate of #{of}: {dup.get('why', '')}"])
        reasons.append(f"model named #{of} as a duplicate but it is not in the shortlist {numbers} "
                       f"— not treated as a duplicate")
    return IntakeResult("triaged", out, None, [], version, model, numbers, reasons)
