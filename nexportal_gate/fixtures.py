"""fixtures — the six pre-registered cases, the runner, and the results table.

`expected.json` is frozen before the first live run and never edited after (git history is the
proof); `results.md` is generated; a miss stays in the table with a one-line reading from
`readings.json`. The runner judges the tool's outputs against predicates, never the model's prose.
"""
from __future__ import annotations

import json
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path

from .adversary import Client, GateResult, run_gate
from .intake import run_intake


@dataclass
class Fixture:
    id: str
    entry: str          # gate | intake
    title: str
    requester: str
    weekday: str
    text: str           # the spec body (gate) or the raw request (intake)
    path: Path


def split_frontmatter(raw: str) -> tuple[dict, str]:
    parts = raw.split("---\n", 2)
    if len(parts) < 3:
        return {}, raw
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, parts[2]


def load_fixtures(directory: Path) -> list[Fixture]:
    out = []
    for path in sorted(Path(directory).glob("[0-9][0-9]-*.md")):
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        entry = meta.get("entry", "gate")
        out.append(Fixture(meta.get("id", path.name[:2]), entry, meta.get("title", ""),
                           meta.get("requester", ""), meta.get("weekday", "Thursday"),
                           body if entry == "gate" else body.strip(), path))
    return sorted(out, key=lambda f: f.id)


def actual_view(result) -> dict:
    """The comparable facts of a result — what the predicates in expected.json read."""
    if isinstance(result, GateResult):
        t2 = result.tier2 or {}
        blocking = [a for a in t2.get("ambiguities") or [] if a.get("blocking") and a.get("owner") != "engineering"]
        size = t2.get("size") or {}
        return {"kind": "gate", "verdict": result.verdict, "model_verdict": result.model_verdict,
                "tier1_failed": bool(result.tier1),
                "tier1_first": result.tier1[0].check if result.tier1 else None,
                "size_band": size.get("band"), "size_confidence": size.get("confidence"),
                "blocking_ambiguities": len(blocking),
                "ambiguity_owners": sorted({a.get("owner", "?") for a in blocking}),
                "hidden_dependency_names": [d.get("name", "") for d in t2.get("hidden_dependencies") or []],
                "message": t2.get("requester_message", "")}
    t2 = result.tier2 or {}
    size = t2.get("size") or {}
    return {"kind": "intake", "status": result.status, "duplicate_of": result.duplicate_of,
            "size_band": size.get("band"), "size_confidence": size.get("confidence"),
            "question_owners": sorted({q.get("owner", "?") for q in t2.get("questions") or []}),
            "message": t2.get("requester_message", "")}


Check = namedtuple("Check", "name passed detail")


def _mentions_any(text: str | None, terms: list[str]) -> bool:
    hay = (text or "").lower()
    return any(t.lower() in hay for t in terms)


def evaluate(expected: dict, actual: dict) -> list[Check]:
    checks = []
    for name, want in expected.items():
        got, ok = None, False
        if name in ("verdict", "status", "size_band", "tier1_failed", "duplicate_of"):
            got, ok = actual.get(name), actual.get(name) == want
        elif name in ("size_confidence_min", "size_confidence_max", "blocking_ambiguities_min",
                      "blocking_ambiguities_max"):
            got = actual.get(name[:-4])
            ok = got is not None and (got >= want if name.endswith("_min") else got <= want)
        elif name in ("ambiguity_owners_include", "question_owners_include"):
            got = actual.get(name[:-8]) or []
            ok = all(w in got for w in want)
        elif name == "hidden_dependency_mentions_any":
            got = actual.get("hidden_dependency_names") or []
            ok = any(_mentions_any(n, want) for n in got)
        elif name == "message_mentions_all":
            got = actual.get("message")
            ok = all(t.lower() in (got or "").lower() for t in want)
        elif name == "message_mentions_any":
            got = actual.get("message")
            ok = _mentions_any(got, want)
        else:
            checks.append(Check(name, False, f"unknown predicate {name!r}"))
            continue
        checks.append(Check(name, ok, f"expected {name} {want!r}, got {got!r}"))
    return checks


def run_all(client: Client, *, fixtures_dir: Path, prompts_dir: Path, platform: str,
            open_issues: list[dict], model: str, only: list[str] | None = None):
    """[(fixture, actual view, checks)] in id order; the view carries `expected` for the table."""
    fixtures_dir = Path(fixtures_dir)
    expected = json.loads((fixtures_dir / "expected.json").read_text(encoding="utf-8"))
    rows = []
    for f in load_fixtures(fixtures_dir):
        if only and f.id not in only:
            continue
        if f.entry == "gate":
            result = run_gate(f.text, client, key=f.id, prompts_dir=prompts_dir, platform=platform, model=model)
        else:
            result = run_intake(f.text, f.requester, open_issues, client, key=f.id, prompts_dir=prompts_dir,
                                platform=platform, model=model, weekday=f.weekday)
        view = actual_view(result)
        view["expected"] = expected.get(f.id, {})
        rows.append((f, view, evaluate(view["expected"], view)))
    return rows


def _esc(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _fmt_expected(exp: dict) -> str:
    parts = []
    for k, v in exp.items():
        if k.endswith("_min"):
            parts.append(f"{k[:-4]} ≥ {v}")
        elif k.endswith("_max"):
            parts.append(f"{k[:-4]} ≤ {v}")
        elif k.endswith("_include"):
            parts.append(f"{k[:-8]} ⊇ {{{', '.join(v)}}}")
        elif k.endswith("_mentions_any"):
            parts.append(f"{k[:-13]} mentions any of {', '.join(v)}")
        elif k.endswith("_mentions_all"):
            parts.append(f"{k[:-13]} mentions {', '.join(v)}")
        else:
            parts.append(f"{k} = {v}")
    return "; ".join(parts)


def _fmt_actual(view: dict) -> str:
    if view["kind"] == "gate":
        if view["tier1_failed"]:
            return f"needs-info (Tier 1: {view['tier1_first']})"
        deps = ", ".join(view["hidden_dependency_names"]) or "none"
        return (f"{view['verdict']} · {view['size_band']} ({view['size_confidence']}) · "
                f"{view['blocking_ambiguities']} blocking [{', '.join(view['ambiguity_owners'])}] · deps: {deps}")
    dup = f" · dup of #{view['duplicate_of']}" if view.get("duplicate_of") else ""
    return (f"{view['status']}{dup} · {view['size_band']} ({view['size_confidence']}) · "
            f"questions → {', '.join(view['question_owners']) or 'none'}")


def render_results(rows, readings: dict[str, str]) -> str:
    passed = sum(1 for _, _, checks in rows if all(c.passed for c in checks))
    lines = ["# Results — expected vs actual", "",
             "Generated by `python -m nexportal_gate fixtures`. `expected.json` was frozen before the first "
             "live run and is never edited; a miss stays here with a one-line reading from `readings.json`.",
             "", f"**{passed}/{len(rows)} pass.**", "",
             "| # | Fixture | Entry | Expected | Actual | Result | Reading |",
             "|---|---|---|---|---|---|---|"]
    for f, view, checks in rows:
        failed = [c.name for c in checks if not c.passed]
        result = "PASS" if not failed else "MISS: " + ", ".join(failed)
        lines.append(f"| {f.id} | {_esc(f.title)} | {f.entry} | {_esc(_fmt_expected(view.get('expected', {})))} | "
                     f"{_esc(_fmt_actual(view))} | {result} | {_esc(readings.get(f.id, ''))} |")
    return "\n".join(lines) + "\n"
