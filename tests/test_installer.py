#!/usr/bin/env python3
"""Black-box tests for the dependency-free installer."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"


def run(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run installer and capture text output."""
    return subprocess.run(
        ["sh", str(INSTALLER), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_project_install_preserves_existing_files_and_roadmap(tmp_path: Path) -> None:
    """Project install adds managed blocks and never replaces roadmap text."""
    project = tmp_path / "project & one"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("before\n", encoding="utf-8")
    roadmap = project / "ROADMAP.md"
    roadmap.write_text("operator roadmap\n", encoding="utf-8")
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("project", str(project), cwd=project, env=env)

    assert result.returncode == 0, result.stderr
    assert "before\n" in agents.read_text(encoding="utf-8")
    assert roadmap.read_text(encoding="utf-8") == "operator roadmap\n"
    assert (project / ".last-human-commit/common/agents/Lead.md").is_file()
    assert "last-human-commit:begin" in agents.read_text(encoding="utf-8")


def test_project_install_is_idempotent(tmp_path: Path) -> None:
    """Second install does not duplicate the managed block."""
    project = tmp_path / "project"
    project.mkdir()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    first = run("project", str(project), cwd=project, env=env)
    second = run("project", str(project), cwd=project, env=env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    content = (project / "AGENTS.md").read_text(encoding="utf-8")
    assert content.count("last-human-commit:begin") == 1


def test_project_install_uses_per_file_bug_tracking(tmp_path: Path) -> None:
    """Project installation ships bug files without duplicate shared registries."""
    project = tmp_path / "project"
    project.mkdir()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("project", str(project), cwd=project, env=env)

    assert result.returncode == 0, result.stderr
    templates = project / ".last-human-commit/common/templates/.agents"
    assert (templates / "bugs/bug_template.md").is_file()
    assert (templates / "tasks/task_template.md").is_file()
    assert not (templates / "bugs.md").exists()
    assert not (templates / "subagents.jsonl").exists()


def test_project_install_rejects_malformed_markers_without_writes(tmp_path: Path) -> None:
    """Malformed managed markers abort before changing the target."""
    project = tmp_path / "project"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("<!-- last-human-commit:begin -->\n", encoding="utf-8")
    before = agents.read_bytes()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("project", str(project), cwd=project, env=env)

    assert result.returncode != 0
    assert agents.read_bytes() == before


def test_project_uninstall_rejects_malformed_markers_without_writes(tmp_path: Path) -> None:
    """Project uninstall fails before rewriting malformed managed entries."""
    project = tmp_path / "project"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("before\n<!-- last-human-commit:begin -->\n", encoding="utf-8")
    before = agents.read_bytes()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("uninstall", "project", str(project), cwd=project, env=env)

    assert result.returncode != 0
    assert agents.read_bytes() == before


def test_host_install_uses_overrides_and_is_idempotent(tmp_path: Path) -> None:
    """Host install honors XDG and CODEX_HOME without touching real home."""
    home = tmp_path / "home"
    codex = tmp_path / "codex"
    data = tmp_path / "data"
    env = {**os.environ, "HOME": str(home), "CODEX_HOME": str(codex), "XDG_DATA_HOME": str(data)}

    first = run("host", "codex", cwd=tmp_path, env=env)
    second = run("host", "codex", cwd=tmp_path, env=env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    installed = codex / "AGENTS.md"
    assert installed.is_file()
    assert installed.read_text(encoding="utf-8").count("last-human-commit:begin") == 1
    assert (data / "last-human-commit/versions/0.2.0/common/agents/Lead.md").is_file()
