"""adversary — Tier 2: the LLM behind a `Client` protocol, and the rule that disposes of its verdict.

LLM proposes / gate disposes. The model returns a verdict; `dispose` overrides it to `needs-info`
whenever a blocking ambiguity (owner ≠ engineering), an untestable criterion or a blocking hidden
dependency is present. Both verdicts are recorded, so the claim is inspectable on every trail.

Backends — deliberately not the Anthropic SDK: the team already runs Claude Code, so the gate is one
more invocation on the existing subscription, with no new vendor and no API key anywhere.
  * ClaudeCodeClient — `claude -p` headless with `--json-schema` (the default).
  * ReplayClient    — `fixtures/recorded/<key>.json`, keyless reproduction of the results table.
  * RecordingClient — wraps a client and saves what it returned, for the replay above.
  * FakeClient      — canned responses, for tests.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from . import shape, text
from .shape import Failure

DEFAULT_MODEL = "claude-fable-5-1"
DISALLOWED_TOOLS = "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Agent"
_VERSION_RE = re.compile(r"^version:\s*(\d+)\s*$")


class AdversaryError(Exception):
    pass


class Client(Protocol):
    def complete(self, system: str, user: str, schema: dict, *, key: str) -> dict: ...


class ClaudeCodeClient:
    """`claude -p` headless. Verified 2026-09-03 on Claude Code 2.1.259: the parsed object lands in
    the envelope's `structured_output`; `--setting-sources project` keeps user-level plugins and
    hooks (this plugin's own wall included) out of the gate's context; `--max-turns 1` plus the
    tool denial keeps it to one call; `--bare` is API-key-only and is never used."""

    def __init__(self, model: str = DEFAULT_MODEL, runner=subprocess.run, cwd: Path | None = None,
                 timeout: int = 180):
        self.model, self.runner, self.cwd, self.timeout = model, runner, cwd, timeout

    def argv(self, user: str, schema: dict, system: str) -> list[str]:
        return ["claude", "-p", user, "--model", self.model, "--system-prompt", system,
                "--json-schema", json.dumps(schema), "--output-format", "json", "--max-turns", "1",
                "--setting-sources", "project", "--no-session-persistence",
                "--disallowedTools", DISALLOWED_TOOLS]

    def complete(self, system: str, user: str, schema: dict, *, key: str) -> dict:
        last = "claude returned nothing"
        for _ in range(2):                                   # one retry on a malformed reply
            proc = self.runner(self.argv(user, schema, system), capture_output=True, text=True,
                               timeout=self.timeout, cwd=self.cwd)
            try:
                envelope = json.loads(proc.stdout)
            except json.JSONDecodeError:
                detail = (proc.stderr or proc.stdout or "").strip()[:300]
                last = f"claude returned no JSON envelope (rc={proc.returncode}): {detail}"
                continue
            if envelope.get("is_error"):
                detail = (f"claude reported an error (subtype={envelope.get('subtype')}): "
                          f"{envelope.get('result')!r}; stderr: {(proc.stderr or '').strip()[:300]!r}")
                if "log" in str(envelope.get("result") or "").lower():   # not logged in — retrying won't help
                    raise AdversaryError(detail)
                last = detail                                             # transient: one retry
                continue
            out = envelope.get("structured_output")
            if isinstance(out, dict):
                return out
            try:                                             # older envelopes: JSON text in `result`
                out = json.loads(envelope.get("result") or "")
                if isinstance(out, dict):
                    return out
            except (json.JSONDecodeError, TypeError):
                pass
            last = "claude returned no structured output"
        raise AdversaryError(last)


class ReplayClient:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def complete(self, system: str, user: str, schema: dict, *, key: str) -> dict:
        path = self.directory / f"{key}.json"
        if not path.exists():
            raise AdversaryError(f"no recorded response for {key!r} at {path} — run with --record first")
        return json.loads(path.read_text(encoding="utf-8"))["structured_output"]


class RecordingClient:
    def __init__(self, inner: Client, directory: Path, *, model: str, prompt_version: int):
        self.inner, self.directory = inner, Path(directory)
        self.model, self.prompt_version = model, prompt_version

    def complete(self, system: str, user: str, schema: dict, *, key: str) -> dict:
        out = self.inner.complete(system, user, schema, key=key)
        self.directory.mkdir(parents=True, exist_ok=True)
        record = {"key": key, "model": self.model, "prompt_version": self.prompt_version,
                  "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "structured_output": out}
        (self.directory / f"{key}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                                    encoding="utf-8")
        return out


class FakeClient:
    def __init__(self, responses: dict[str, dict]):
        self.responses = responses

    def complete(self, system: str, user: str, schema: dict, *, key: str) -> dict:
        if key not in self.responses:
            raise AdversaryError(f"FakeClient has no response for {key!r}")
        return self.responses[key]


# --- prompts ------------------------------------------------------------------------------------

def load_prompt(name: str, prompts_dir: Path) -> str:
    return (Path(prompts_dir) / name).read_text(encoding="utf-8")


def load_schema(name: str, prompts_dir: Path) -> dict:
    return json.loads(load_prompt(name, prompts_dir))


def prompt_version(system_text: str) -> int:
    first = system_text.split("\n", 1)[0]
    m = _VERSION_RE.match(first)
    if not m:
        raise AdversaryError("prompts/system.md must start with a 'version: N' line")
    return int(m.group(1))


def render(template: str, **fields) -> str:
    """Replace `{{name}}` tokens only — braces elsewhere (JSON in a template) are left alone."""
    for name, value in fields.items():
        template = template.replace("{{" + name + "}}", str(value))
    return template


# --- the rule -----------------------------------------------------------------------------------

def dispose(out: dict) -> tuple[str, list[str]]:
    """The gate's own verdict over the model's output: `needs-info` iff a trigger is present."""
    reasons = []
    for a in out.get("ambiguities") or []:
        if a.get("blocking") and a.get("owner") != "engineering":
            reasons.append(f"blocking ambiguity owned by {a.get('owner')}: {a.get('text')}")
    for c in out.get("untestable_criteria") or []:
        reasons.append(f"untestable criterion: {c.get('criterion')}")
    for d in out.get("hidden_dependencies") or []:
        if d.get("blocking"):
            reasons.append(f"blocking hidden dependency: {d.get('name')}")
    return ("needs-info" if reasons else "ready"), reasons


@dataclass
class GateResult:
    verdict: str
    model_verdict: str | None
    tier1: list[Failure]
    tier2: dict | None
    body_sha256: str
    prompt_version: int
    model: str
    reasons: list[str]


def run_gate(body: str, client: Client, *, key: str, prompts_dir: Path, platform: str,
             model: str) -> GateResult:
    """Tier 1 first; on any shape failure Tier 2 never runs. Otherwise one call, then `dispose`."""
    prompts_dir = Path(prompts_dir)
    system = load_prompt("system.md", prompts_dir)
    version = prompt_version(system)
    sha = text.body_hash(body)
    tier1 = shape.check(body)
    if tier1:
        first = tier1[0]
        return GateResult("needs-info", None, tier1, None, sha, version, model,
                          [f"shape: {first.check} — {first.message}"])
    schema = load_schema("gate.schema.json", prompts_dir)
    user = render(load_prompt("gate.md", prompts_dir), platform=platform, body=text.normalise(body))
    out = client.complete(system, user, schema, key=key)
    verdict, reasons = dispose(out)
    return GateResult(verdict, out.get("verdict"), [], out, sha, version, model, reasons)
