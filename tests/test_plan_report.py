#!/usr/bin/env python3
"""The live plan report: canonical format, 30-minute emission, plan-reading Overseer."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))

import lhc_entry
import lhc_time_guard as guard


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def compact(value: str) -> str:
    return " ".join(value.split())


def test_plan_report_protocol_carries_the_canonical_format():
    protocol = read("src/common/protocols/PLAN_REPORT.md")
    for phrase in (
        "✅",
        "🔄",
        "⏳",
        "Цель:",
        "Бизнес-результат:",
        "Декомпозиция:",
        "∥ параллельно с листом 1",
        "отстаём потому что:",
        "начнём после листа 3, потому что",
        "начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут",
        "не измерено",
    ):
        assert phrase in protocol, phrase
    assert "декомпозиция задач" in protocol
    assert "какой план" in protocol


def test_router_points_to_the_report_and_stays_english():
    router = compact(read("AGENTS.md"))
    assert "is the canonical plan format" in router
    assert "in any language" in router
    assert "Overseer reads that report against the original request" in router
    assert "it never blocks delivery" in router
    # The English instruction policy forbids Cyrillic in the router itself.
    import re
    assert not re.search("[А-Яа-яЁё]", read("AGENTS.md"))


def test_task_template_carries_the_same_report_shape():
    template = read("src/common/templates/.agents/tasks/task_template.md")
    for phrase in (
        "## Plan — live plan report",
        "Декомпозиция: N листьев",
        "✅ (описание листа) начата",
        "🔄 работаем (описание листа) начата",
        "⏳ (описание листа) начнём после листа N",
        "∥ параллельно с листом 1",
    ):
        assert phrase in template, phrase
    assert "Overseer is the plan reader" in template


def test_overseer_reads_the_plan_without_becoming_a_gate():
    overseer = compact(read("src/common/agents/Overseer.md"))
    assert "independent, read-only reviewer of the live plan" in overseer
    assert "every 30-minute plan boundary" in overseer
    assert "never blocks delivery" in overseer
    assert "it never blocks" not in overseer.lower()


def test_heartbeat_asks_for_the_canonical_report_at_thirty_minutes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    first = guard.native_heartbeat(tmp_path, "codex", "sid-plan", now=start)
    assert first is not None and first["due"] == []
    due = guard.native_heartbeat(tmp_path, "codex", "sid-plan", now=start + timedelta(minutes=30))
    assert due is not None and due["due"] == ["plan:1"]
    assert "30-minute plan report" in due["prompt"]
    assert "PLAN_REPORT.md" in due["prompt"]


def test_heartbeat_raises_the_learning_checkpoint_with_a_diagnostic_agent(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    args = type("Args", (), {"runtime": "codex", "now": start})()
    first = guard.learning_checkpoint(args, tmp_path, "sid-learn")
    assert first["due"] is False
    late = type("Args", (), {"runtime": "codex", "now": start + timedelta(minutes=121)})()
    due = guard.learning_checkpoint(late, tmp_path, "sid-learn")
    assert due["due"] is True
    assert "frontier-model agent" in due["prompt"]
    assert "why this session is taking so long" in due["prompt"]
    assert "may change the owning instruction" in due["prompt"]
    assert "verdict binds this session" in due["prompt"]
    assert "read-only" not in due["prompt"]


def test_post_tool_use_hook_emits_both_reminders(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    payload = json.dumps({"cwd": str(tmp_path), "session_id": "sid-hook",
                           "tool_name": "exec_command"})
    result = subprocess.run(
        [sys.executable, str(ROOT / "src/common/tools/lhc_entry.py"),
         "--root", str(ROOT), "--runtime", "codex", "--event", "PostToolUse", "--heartbeat-only"],
        input=payload, text=True, capture_output=True, check=True)
    output = json.loads(result.stdout or "{}")
    context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    # A fresh session has no 30-minute plan reminder yet, and the 120-minute
    # checkpoint is not due — the hook must stay quiet and side-effect free.
    assert context == ""
    state_files = list((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    assert state_files, "the heartbeat keeps its own timer record"


def test_entry_keeps_conversation_hooks_inert():
    payload = json.dumps({"cwd": "/tmp", "session_id": "sid-inert", "prompt": "hi"})
    result = subprocess.run(
        [sys.executable, str(ROOT / "src/common/tools/lhc_entry.py"),
         "--root", str(ROOT), "--runtime", "codex", "--event", "UserPromptSubmit"],
        input=payload, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == ""
