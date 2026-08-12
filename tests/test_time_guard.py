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
