#!/usr/bin/env python3
"""Regression: the heartbeat must not swallow the wall-time reminders.

The ``--heartbeat-only`` branch of the native entry observes two independent
clocks: the 120-minute learning checkpoint and the 30/60-minute heartbeat
buckets. The learning checkpoint owns ``last_observed_at``; the heartbeat owns
``native_heartbeat``. When the heartbeat ran first it created the state file
without ``last_observed_at``, the learning checkpoint then raised ``KeyError``
and every time reminder was lost for every harness.

The live path is the corrected branch, so the regression is covered end to end:
one heartbeat run must leave both clocks in the state, and an elapsed deadline
must still produce its reminder.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _inprocess import git_repo, load_module, run_cli

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/common/tools/lhc_entry.py"
entry = load_module(ENTRY, name="lhc_entry_heartbeat_regression_test")


def run_heartbeat(project: Path, session_id: str, prompt: str | None = None) -> str:
    """Run the live heartbeat-only hook and return its stdout."""
    payload = {"cwd": str(project), "session_id": session_id, "tool_name": "exec_command"}
    if prompt is not None:
        payload["prompt"] = prompt
    result = run_cli(
        entry, ["--root", str(ROOT), "--runtime", "codex",
                "--event", "PostToolUse", "--heartbeat-only"],
        stdin=json.dumps(payload, ensure_ascii=False))
    assert result.returncode == 0, result.stderr
    return result.stdout


def state_path(project: Path) -> Path:
    files = list((project / ".agents/shared-session/learning").glob("*.json"))
    assert len(files) == 1, files
    return files[0]


def rewind(state_file: Path, minutes: int) -> None:
    """Move the observed wall clock and the heartbeat start into the past."""
    state = json.loads(state_file.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    state["started_at"] = past.isoformat()
    state["last_observed_at"] = past.isoformat()
    state["due_at"] = (past + timedelta(minutes=120)).isoformat()
    timer = state["native_heartbeat"]
    timer["started_at"] = past.isoformat()
    timer["last_seen_at"] = past.isoformat()
    state_file.write_text(json.dumps(state), encoding="utf-8")


def additional_context(stdout: str) -> str:
    payload = json.loads(stdout or "{}")
    return payload.get("hookSpecificOutput", {}).get("additionalContext", "")


def test_heartbeat_state_keeps_both_the_observation_and_the_timer(tmp_path):
    git_repo(tmp_path)

    stdout = run_heartbeat(tmp_path, "heartbeat-regression")

    state = json.loads(state_path(tmp_path).read_text(encoding="utf-8"))
    # The learning checkpoint owns last_observed_at; the heartbeat owns
    # native_heartbeat. Both must survive one heartbeat run.
    assert "last_observed_at" in state
    assert "native_heartbeat" in state
    # A timestamp that cannot be parsed would hide the deadline again.
    datetime.fromisoformat(state["last_observed_at"])
    datetime.fromisoformat(state["native_heartbeat"]["started_at"])
    assert state["native_heartbeat"]["session_id"] == "heartbeat-regression"
    assert state["native_heartbeat"]["runtime"] == "codex"
    # A fresh session is not due yet, so the hook stays quiet.
    assert additional_context(stdout) == ""


def test_elapsed_time_still_emits_the_plan_reminder(tmp_path):
    git_repo(tmp_path)
    run_heartbeat(tmp_path, "heartbeat-elapsed")

    rewind(state_path(tmp_path), 31)
    context = additional_context(run_heartbeat(tmp_path, "heartbeat-elapsed"))

    assert "30-minute plan report" in context
    assert "PLAN_REPORT.md" in context


def test_elapsed_learning_checkpoint_is_not_swallowed_by_the_heartbeat(tmp_path):
    git_repo(tmp_path)
    run_heartbeat(tmp_path, "heartbeat-learning")

    # The 120-minute deadline passes while the heartbeat keeps running.
    rewind(state_path(tmp_path), 121)
    context = additional_context(run_heartbeat(tmp_path, "heartbeat-learning"))

    # The learning checkpoint reminder is exactly what the reversed call order
    # used to drop: it must still be emitted next to the plan reminder.
    assert "LHC session checkpoint" in context
    assert "120 wall-clock minutes" in context
    assert "30-minute plan report" in context


def test_the_hook_never_writes_a_state_without_the_observed_timestamp(tmp_path):
    git_repo(tmp_path)

    # Two consecutive heartbeats must not lose the observation clock either.
    run_heartbeat(tmp_path, "heartbeat-repeat")
    run_heartbeat(tmp_path, "heartbeat-repeat")

    state = json.loads(state_path(tmp_path).read_text(encoding="utf-8"))
    assert "last_observed_at" in state
    assert "native_heartbeat" in state
    assert state["native_heartbeat"]["last_plan_bucket"] == 0
    assert state["native_heartbeat"]["last_goal_bucket"] == 0
