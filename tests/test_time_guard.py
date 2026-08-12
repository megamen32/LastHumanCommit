#!/usr/bin/env python3
"""Behavioral tests for the persistent LHC business time guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_time_guard.py"


def run_guard(state: Path, now: str, active_minutes: int, *extra: str) -> dict[str, object]:
    """Run one deterministic guard check and decode its JSON result."""

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "check",
            "--state",
            str(state),
            "--cycle-id",
            "demo-cycle",
            "--started-at",
            "2026-08-12T10:00:00+03:00",
            "--now",
            now,
            "--minimum-minutes",
            "30",
            "--maximum-minutes",
            "120",
            "--active-minutes",
            str(active_minutes),
            *extra,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def run_native_hook(
    root: Path,
    event: str,
    *,
    runtime: str = "codex",
    session_id: str = "session-demo",
) -> dict[str, object] | None:
    """Run one native hook against a disposable project root."""

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "hook",
            "--runtime",
            runtime,
            "--event",
            event,
            "--now",
            "2026-08-12T12:00:00+03:00",
        ],
        input=json.dumps(
            {
                "cwd": str(root),
                "hook_event_name": event,
                "session_id": session_id,
                "trigger": "automatic",
            }
        ),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def make_active_project(root: Path) -> Path:
    """Create the smallest active-card source for native-hook tests."""

    task = root / ".agents/tasks/work-demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(
        """# Task

Status: in progress
Latest user request: ship the smallest real result
Accepted business outcome / Definition of Done: one real canary passes
Current blocker: none
Next shortest action: run the canary
Started at (UTC+3): 2026-08-12T10:00:00+03:00
Initial estimate (minimum / maximum active minutes): 30 / 120
Actual active minutes: unknown; do not infer from wall-clock

## Decisive evidence

- changed src/business.py
""",
        encoding="utf-8",
    )
    return task


def test_hourly_report_is_stateful_and_idempotent(tmp_path: Path) -> None:
    state = tmp_path / "time-guard.json"
    first = run_guard(
        state,
        "2026-08-12T11:05:00+03:00",
        55,
        "--completed-task",
        "installed baseline",
        "--completed-file",
        "src/common/agents/Lead.md",
        "--business-delta",
        "baseline is live",
    )

    assert first["events"] == ["hourly"]
    assert first["crossed_hours"] == [1]
    assert first["planned_minutes"] == {"minimum": 30, "maximum": 120}
    assert first["active_minutes"] == 55
    assert "Какие реальные задачи закрыты" in first["prompt"]
    assert "installed baseline" in first["prompt"]
    assert "src/common/agents/Lead.md" in first["prompt"]

    duplicate = run_guard(state, "2026-08-12T11:05:00+03:00", 55)
    assert duplicate["events"] == []
    assert duplicate["prompt"] == ""


def test_overrun_emits_full_business_first_diagnostic_once(tmp_path: Path) -> None:
    state = tmp_path / "time-guard.json"
    run_guard(state, "2026-08-12T11:05:00+03:00", 55)
    overrun = run_guard(
        state,
        "2026-08-12T12:05:00+03:00",
        125,
        "--controlled",
        "no",
        "--route-changed",
        "no",
        "--gate",
        "premature review",
        "--instruction",
        "strict proof before canary",
    )

    assert overrun["events"] == ["hourly", "overrun"]
    assert overrun["crossed_hours"] == [2]
    assert overrun["overrun_minutes"] == 5
    prompt = overrun["prompt"]
    for phrase in (
        "Меньше безопасности, больше бизнес-результата.",
        "Что мешает?",
        "Сколько планировал потратить на задачу, а сколько потратил?",
        "Ты это как-то контролировал?",
        "Выведи все завершённые файлы.",
        "Какие гейты помешали?",
        "Какие инструкции заставляли больше идти в безопасность вместо бизнеса?",
        "Почему по времени так превысил задачу, но не менял подход",
        "Что меняется в маршруте сейчас?",
        "premature review",
        "strict proof before canary",
    ):
        assert phrase in prompt

    duplicate = run_guard(state, "2026-08-12T12:10:00+03:00", 130)
    assert duplicate["events"] == []


def test_estimate_mutation_is_reported_and_original_maximum_is_retained(tmp_path: Path) -> None:
    state = tmp_path / "time-guard.json"
    run_guard(state, "2026-08-12T10:10:00+03:00", 10)

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "check",
            "--state",
            str(state),
            "--cycle-id",
            "demo-cycle",
            "--started-at",
            "2026-08-12T10:00:00+03:00",
            "--now",
            "2026-08-12T11:00:00+03:00",
            "--minimum-minutes",
            "60",
            "--maximum-minutes",
            "240",
            "--active-minutes",
            "125",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert "estimate_mutation" in result["events"]
    assert "overrun" in result["events"]
    assert result["planned_minutes"] == {"minimum": 30, "maximum": 120}
    assert "Нельзя легализовать прежний маршрут простой заменой оценки" in result["prompt"]


def test_compaction_handoff_is_replaced_counted_and_restored(tmp_path: Path) -> None:
    task = make_active_project(tmp_path)

    before = run_native_hook(tmp_path, "PreCompact")
    assert before is not None
    assert "systemMessage" in before

    session_root = tmp_path / ".agents/shared-session/compaction/session-demo"
    handoff = session_root / "current-handoff.md"
    state = session_root / "state.json"
    first_text = handoff.read_text(encoding="utf-8")
    assert "Compaction count: 1" in first_text
    assert task.read_text(encoding="utf-8") in first_text
    assert "append-only" not in first_text.casefold()

    run_native_hook(tmp_path, "PostCompact")
    first_state = json.loads(state.read_text(encoding="utf-8"))
    assert first_state["compaction_count"] == 1
    assert first_state["recent"][-1]["status"] == "completed"

    restored = run_native_hook(tmp_path, "SessionStart")
    assert restored is not None
    restored_context = restored["hookSpecificOutput"]["additionalContext"]
    assert "Compaction count: 1" in restored_context
    assert "Continue from this handoff" in restored_context

    for _ in range(4):
        run_native_hook(tmp_path, "PreCompact")
        run_native_hook(tmp_path, "PostCompact")
    final_state = json.loads(state.read_text(encoding="utf-8"))
    assert final_state["compaction_count"] == 5
    assert [mark["count"] for mark in final_state["recent"]] == [3, 4, 5]
    assert handoff.read_text(encoding="utf-8").count("# LHC Current Handoff") == 1


def test_opencode_compaction_returns_handoff_for_summary_prompt(tmp_path: Path) -> None:
    make_active_project(tmp_path)

    result = run_native_hook(tmp_path, "PreCompact", runtime="opencode")

    assert result is not None
    assert result["compaction_count"] == 1
    assert "Continue from this handoff" in result["handoff"]
    assert result["handoff_path"].endswith("/current-handoff.md")


def test_legacy_large_task_card_cannot_make_handoff_append_forever(tmp_path: Path) -> None:
    task = make_active_project(tmp_path)
    task.write_text(task.read_text(encoding="utf-8") + ("legacy evidence\n" * 4000), encoding="utf-8")

    run_native_hook(tmp_path, "PreCompact")

    handoff = (
        tmp_path / ".agents/shared-session/compaction/session-demo/current-handoff.md"
    ).read_text(encoding="utf-8")
    assert len(handoff) < 30_000
    assert "legacy task-card middle omitted from handoff" in handoff
    assert "source path above is authoritative" in handoff
