#!/usr/bin/env python3
"""Behavioral tests for the Worker Research reusable code map."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills/worker-research/scripts/code_map.py"


def run_tool(project: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(project), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def project(tmp_path: Path) -> Path:
    (tmp_path / ".agents").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/resume.py").write_text("def resume():\n    return 'ok'\n", encoding="utf-8")
    return tmp_path


def upsert(root: Path, summary: str = "web -> resume.py::resume") -> dict[str, object]:
    completed = run_tool(
        root,
        "upsert",
        "--key",
        "resume-production-path",
        "--kind",
        "production-path",
        "--summary",
        summary,
        "--location",
        "src/resume.py::resume",
        "--evidence",
        "rg -n 'resume' src",
    )
    return json.loads(completed.stdout)


def test_upsert_search_and_same_key_replacement(tmp_path: Path) -> None:
    root = project(tmp_path)

    first = upsert(root)
    second = upsert(root, "api -> resume.py::resume")
    search = run_tool(root, "search", "resume", "production", "--json")
    hits = json.loads(search.stdout)
    state = json.loads(
        (root / ".agents/shared-session/knowledge/code-map.json").read_text(
            encoding="utf-8"
        )
    )

    assert first["key"] == "resume-production-path"
    assert second["summary"] == "api -> resume.py::resume"
    assert len(state["entries"]) == 1
    assert hits[0]["freshness"] == "fresh"
    assert hits[0]["locations"][0]["symbol"] == "resume"


def test_check_reports_content_drift_without_deleting_knowledge(tmp_path: Path) -> None:
    root = project(tmp_path)
    upsert(root)

    (root / "src/resume.py").write_text("def resume():\n    return 'changed'\n", encoding="utf-8")
    completed = run_tool(
        root,
        "check",
        "--key",
        "resume-production-path",
        "--json",
        check=False,
    )
    checked = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert checked[0]["freshness"] == "stale"
    assert checked[0]["locations"][0]["status"] == "content-changed"
    assert (root / ".agents/shared-session/knowledge/code-map.json").is_file()


def test_remove_drops_invalid_key(tmp_path: Path) -> None:
    root = project(tmp_path)
    upsert(root)

    removed = json.loads(
        run_tool(root, "remove", "--key", "resume-production-path").stdout
    )
    search = run_tool(root, "search", "resume")

    assert removed == {"key": "resume-production-path", "removed": True}
    assert search.stdout.strip() == "no matching code-map entries"


def test_location_cannot_escape_project(tmp_path: Path) -> None:
    root = project(tmp_path)

    completed = run_tool(
        root,
        "upsert",
        "--key",
        "bad-location",
        "--kind",
        "ownership",
        "--summary",
        "invalid",
        "--location",
        "../outside.py",
        check=False,
    )

    assert completed.returncode != 0
    assert "escapes project root" in completed.stderr


def test_verified_entry_rejects_missing_location(tmp_path: Path) -> None:
    root = project(tmp_path)

    completed = run_tool(
        root,
        "upsert",
        "--key",
        "missing-owner",
        "--kind",
        "ownership",
        "--summary",
        "unverified location",
        "--location",
        "src/missing.py::owner",
        check=False,
    )

    assert completed.returncode != 0
    assert "verified entries require existing locations" in completed.stderr
