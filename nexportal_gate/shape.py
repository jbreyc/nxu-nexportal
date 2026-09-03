"""shape — Tier 1: the deterministic shape check over the DoR form. No LLM.

Fails closed. The first failure is the one the record names; the rest are listed after it. Rules,
in order: no open question riding the body (the airlock), every section present and non-empty
once HTML comments are stripped, then the per-section rules. "Outcome is one sentence" stays
advisory (the form's placeholder says so); counting sentences reliably is not worth a false refusal.
"""
import re
from collections import namedtuple

from . import text

Failure = namedtuple("Failure", "check message")

SECTIONS = ("outcome", "users", "acceptance criteria", "design", "dependencies",
            "out of scope", "size", "requester")
PLACEHOLDERS = {"", "tbd", "?", "unknown", "n/a", "todo", "-", "none", "..."}
OPEN_QUESTION = "NX-OPEN-QUESTION:"

EARS_RE = re.compile(r"^(?:(?:WHEN|IF|WHILE|WHERE)\b.*\b)?THE SYSTEM SHALL\b", re.I)
GWT_RE = re.compile(r"^GIVEN\b.*\bWHEN\b.*\bTHEN\b", re.I | re.S)
URL_RE = re.compile(r"https?://\S+")
NO_UI_RE = re.compile(r"^n/a\s*[—–-]\s*no ui$", re.I)
BRIEF_LINES = ("goal:", "keep:", "change:", "out of scope:")
SIZE_RE = re.compile(r"^(S|M|L|XL)\s*[—–-]\s*(\S+\s+){2,}\S+", re.I)   # band, dash, ≥ 3 words


def _is_placeholder(s: str) -> bool:
    return s.strip().strip(" .").lower() in PLACEHOLDERS


def _brief_ok(design: str) -> bool:
    lines = [line.strip().lower() for line in design.split("\n") if line.strip()]
    if not any(line.startswith("brief:") for line in lines):
        return False
    return all(any(line.startswith(prefix) for line in lines) for prefix in BRIEF_LINES)


def _check_acceptance(content: str) -> Failure | None:
    items = text.list_items(content)
    if len(items) < 2:
        return Failure("acceptance-criteria", f"{len(items)} criterion — need at least 2")
    for item in items:
        if not (EARS_RE.match(item.strip()) or GWT_RE.match(item.strip())):
            return Failure("acceptance-criteria",
                           f"not EARS (WHEN … THE SYSTEM SHALL …) or Given/When/Then: {item!r}")
    return None


def _check_design(content: str) -> Failure | None:
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if URL_RE.search(content) or any(NO_UI_RE.match(line) for line in lines) or _brief_ok(content):
        return None
    return Failure("design", "no design link, no 'n/a — no UI', and no complete brief: "
                             "(Goal: / Keep: / Change: / Out of scope:)")


def _check_placeholder(check: str, hint: str):
    def rule(content: str) -> Failure | None:
        return Failure(check, hint) if _is_placeholder(content) else None
    return rule


def _check_size(content: str) -> Failure | None:
    if SIZE_RE.match(content.strip()):
        return None
    return Failure("size", "want '<S|M|L|XL> — <one-line rationale>'")


RULES = {
    "users": _check_placeholder("users", "name who, in which moment"),
    "acceptance criteria": _check_acceptance,
    "design": _check_design,
    "dependencies": _check_placeholder("dependencies", "name them, or 'none — <reason>'"),
    "out of scope": _check_placeholder("out-of-scope", "say what is deliberately left out"),
    "size": _check_size,
    "requester": _check_placeholder("requester", "a name or @handle"),
}


def check(body: str) -> list[Failure]:
    """[] ⇒ the body passes shape. Otherwise every failure, first-to-name first."""
    failures = [Failure("open-question", line.strip())
                for line in body.split("\n") if text.marker_line_matches(line, OPEN_QUESTION)]
    secs = text.sections(body)
    for name in SECTIONS:
        raw = secs.get(name)
        if raw is None:
            failures.append(Failure(f"section:{name}", f"section '{name}' is missing"))
            continue
        content = text.strip_comments(raw).strip()
        if not content:
            failures.append(Failure(f"section:{name}", f"section '{name}' is empty"))
            continue
        rule = RULES.get(name)
        failure = rule(content) if rule else None
        if failure:
            failures.append(failure)
    return failures
