"""text — the small helpers every module reads through.

Body normalisation and hashing (the freshness rule compares hashes, never clocks), HTML-comment
stripping, the sections map, list items, and the marker matcher. The marker matcher is prefix mode
at column 0 with no whitespace tolerance: an indented or blockquoted marker is prose, not a record.
"""
import hashlib
import re

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# `##` or `###` both open a section: GitHub issue forms render every field as `### Label`, hand-written
# bodies use `## `. Deeper headings stay content.
_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$")
_ITEM_RE = re.compile(r"^\s*(?:[-*]\s+(?:\[[ xX]\]\s+)?|\d+[.)]\s+)(.*\S)\s*$")


def normalise(body: str) -> str:
    """CRLF→LF, trailing whitespace stripped per line, outer blank lines dropped."""
    lines = [line.rstrip() for line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def body_hash(body: str) -> str:
    """sha256 of the normalised body — what a record stores and what the wall recomputes."""
    return hashlib.sha256(normalise(body).encode("utf-8")).hexdigest()


def strip_comments(s: str) -> str:
    return _COMMENT_RE.sub("", s)


def sections(body: str) -> dict[str, str]:
    """Map heading text (lowercased) → its content, outer blank lines stripped."""
    out: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.split("\n"):
        m = _HEADING_RE.match(line)
        if m:
            if current is not None:
                out[current] = "\n".join(buf).strip("\n")
            current, buf = m.group(1).strip().lower(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip("\n")
    return out


def list_items(text: str) -> list[str]:
    """Items from `- `, `* `, `- [ ] `, `- [x] ` and `1. ` lines, bullet stripped."""
    items = []
    for line in text.split("\n"):
        m = _ITEM_RE.match(line)
        if m:
            items.append(m.group(1))
    return items


def marker_line_matches(line: str, marker: str) -> bool:
    """Prefix mode: the RAW line begins with `marker` at column 0."""
    return line.startswith(marker)
