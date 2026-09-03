"""Replay of the recorded live run must reproduce results.md's PASS/MISS column byte-for-byte."""
import json
import re
from pathlib import Path

import pytest

from nexportal_gate import adversary, fixtures

RECORDED = Path("fixtures/recorded")
RESULTS = Path("fixtures/results.md")


@pytest.mark.skipif(not RECORDED.exists() or not RESULTS.exists(), reason="no live run recorded yet")
def test_replay_reproduces_the_results_table():
    platform = Path("context/platform.md").read_text(encoding="utf-8")
    open_issues = json.loads(Path("fixtures/open-issues.json").read_text(encoding="utf-8"))
    rows = fixtures.run_all(adversary.ReplayClient(RECORDED), fixtures_dir=Path("fixtures"),
                            prompts_dir=Path("prompts"), platform=platform, open_issues=open_issues,
                            model="replay")
    replayed = {f.id: ("PASS" if all(c.passed for c in checks) else "MISS") for f, _, checks in rows}
    committed = {m.group(1): m.group(2)
                 for m in re.finditer(r"^\| (\d\d) \| .*? \| (PASS|MISS)", RESULTS.read_text(encoding="utf-8"), re.M)}
    assert replayed == committed
