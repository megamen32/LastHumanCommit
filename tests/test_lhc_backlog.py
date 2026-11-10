# LHC:COVERS src/common/tools/lhc_backlog.py src/common/tools/lhc_entry.py
"""Overdue backlog lines and legacy marks are printed by the SessionStart hook."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from _inprocess import git_repo, load_module, run_cli

ROOT = Path(__file__).resolve().parents[1]
backlog = load_module(ROOT / "src/common/tools/lhc_backlog.py", name="lhc_backlog_test")
entry = load_module(ROOT / "src/common/tools/lhc_entry.py", name="lhc_entry_backlog_test")
TODAY = date(2026, 11, 10)


def test_overdue_backlog_keeps_only_unchecked_past_dates() -> None:
    text = "\n".join([
        "# Roadmap", "## Backlog",
        "- [ ] 2026-11-01 old thing (chat)",
        "- [ ] 2026-11-10 due today (chat)",
        "- [ ] 2026-12-01 future (chat)",
        "- [x] 2026-10-01 done (chat)",
    ])
    items = backlog.overdue_backlog(text, TODAY)
    assert items == [{"line_no": 3, "due": "2026-11-01", "text": "old thing (chat)", "days_late": 9}]


def test_overdue_legacy_parses_dates_and_reports_undated() -> None:
    matches = [
        ("a.py", 3, "# LHC:LEGACY remove=2026-10-01 old shim"),
        ("b.py", 4, "# LHC:LEGACY remove=2027-01-01 later"),
        ("c.py", 5, "# LHC:LEGACY no date here"),
    ]
    got = backlog.overdue_legacy(matches, TODAY)
    assert [(g["path"], g["line_no"], g["due"]) for g in got] == [("a.py", 3, "2026-10-01"), ("c.py", 5, None)]
    assert got[0]["text"] == "old shim"
    assert "undated" in backlog.render([], got)


def test_render_empty_and_limit() -> None:
    assert backlog.render([], []) == ""
    items = [{"line_no": n, "due": "2026-11-01", "text": f"t{n}", "days_late": 9} for n in range(10)]
    out = backlog.render(items, [], limit=3)
    assert "Overdue backlog (ROADMAP.md)" in out
    assert "- 2026-11-01 (9 days late) t0" in out
    assert "t3" not in out and "… and 7 more" in out


def test_session_start_prints_overdue_block(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    repo = git_repo(tmp_path / "repo")
    (repo / "ROADMAP.md").write_text("## Backlog\n- [ ] 2020-01-01 pay the debt (chat)\n", encoding="utf-8")
    (repo / "mod.py").write_text("# LHC:LEGACY remove=2020-01-01 delete me\n", encoding="utf-8")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    done = run_cli(entry, ["--root", str(ROOT), "--event", "SessionStart", "--instructions-only"],
                   stdin="{}", cwd=repo)
    assert done.returncode == 0, done.stderr
    context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Overdue backlog (ROADMAP.md)" in context and "pay the debt" in context
    if shutil.which("rg"):
        assert "mod.py:1 remove=2020-01-01 delete me" in context
    compact = run_cli(entry, ["--root", str(ROOT), "--event", "PostCompact", "--instructions-only"],
                      stdin="{}", cwd=repo)
    assert "pay the debt" not in compact.stdout
