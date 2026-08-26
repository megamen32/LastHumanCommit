#!/usr/bin/env python3
"""Native hook adapters reach the shared fail-open LHC time guard."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_time_guard.py"
PLUGIN = ROOT / "plugins/last-human-commit"


def task(root: Path, *, active: int | None = None) -> None:
    tasks = root / ".agents/tasks"
    tasks.mkdir(parents=True)
    started = datetime.now(timezone.utc) - timedelta(minutes=65)
    extra = f"\n- Active minutes: {active}" if active is not None else ""
    (tasks / "work-hook-canary.md").write_text(
        f"- Started at: {started.isoformat()}\n- Initial estimate: 5 / 120 active minutes{extra}\n",
        encoding="utf-8",
    )


def run(root: Path, runtime: str, event: str) -> dict[str, object] | None:
    completed = subprocess.run(
        [sys.executable, str(TOOL), "hook", "--runtime", runtime, "--event", event],
        input=json.dumps({"cwd": str(root)}),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def test_codex_hook_emits_one_idempotent_hourly_context(tmp_path: Path) -> None:
    task(tmp_path)
    first = run(tmp_path, "codex", "PostToolUse")
    assert first is not None
    specific = first["hookSpecificOutput"]
    assert specific["hookEventName"] == "PostToolUse"
    assert "Какие реальные задачи закрыты" in specific["additionalContext"]
    assert run(tmp_path, "codex", "PostToolUse") is None


def test_opencode_hook_reports_explicit_active_overrun(tmp_path: Path) -> None:
    task(tmp_path, active=125)
    result = run(tmp_path, "opencode", "tool.execute.after")
    assert result is not None
    assert "Превышение исходного maximum: 5 активных минут" in result["prompt"]


def test_hook_is_fail_open_without_task_card(tmp_path: Path) -> None:
    assert run(tmp_path, "codex", "SessionStart") is None


def test_package_declares_both_native_adapters() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["extensions"]["com.openai"]["hooks"] == "./hooks/hooks.json"
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))
    assert set(hooks["hooks"]) >= {"SessionStart", "PostToolUse"}
    assert (PLUGIN / "opencode/lhc-time-guard.ts").is_file()
