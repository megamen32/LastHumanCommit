"""Real time-guard CLI, with deterministic wall clocks and local state only."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


TOOL = Path(__file__).resolve().parents[1] / "src/common/tools/lhc_time_guard.py"


@pytest.fixture(autouse=True)
def project_boundary(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)


def cli(*args, payload=None, ok=True):
    result = subprocess.run(
        [sys.executable, str(TOOL), *map(str, args)],
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True, text=True, timeout=10,
    )
    if ok:
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout) if result.stdout.strip() else None
    assert result.returncode != 0
    return result


def tick(root, now, runtime="codex", event="PostToolUse", session="parent"):
    return cli("hook", "--runtime", runtime, "--event", event, "--now", now,
               payload={"cwd": str(root), "session_id": session})


def message(result):
    return json.dumps(result, ensure_ascii=False)


def ack(root, runtime="codex", **overrides):
    fields = {
        "cwd": root, "runtime": runtime, "session-id": "parent",
        "due-at": "2026-09-09T14:00:00+03:00",
        "now": "2026-09-09T14:05:00+03:00",
        "observation": "Serial expansion delayed the accepted canary.",
        "method-change": "Freeze new scope and execute only the remaining canary.",
        "verification": "tests/test_learning_checkpoint.py: real CLI regression passed.",
        "accepted-result": "Periodic session checkpoint survives cycle changes.",
        "remaining-critical-path": "Root integrates and tests the installed native hooks.",
        "scope-review": "No daemon or new runtime infrastructure.",
        "rework-review": "No further parser rewrite needed.",
    }
    fields.update(overrides)
    args = ["checkpoint"]
    for key, value in fields.items():
        if value is not None:
            args.extend([f"--{key}", str(value)])
    return args


@pytest.mark.parametrize("runtime", ["codex", "opencode", "hermes"])
def test_unmatched_cards_due_repeats_until_evidenced_ack(tmp_path, runtime):
    tasks = tmp_path / ".agents/tasks"
    tasks.mkdir(parents=True)
    (tasks / "unified-node-failover.md").write_text("Unmatched ongoing task")
    tick(tmp_path, "2026-09-09T12:00:00+03:00", runtime)
    assert "improve-workflow" not in message(tick(tmp_path, "2026-09-09T13:59:59+03:00", runtime))
    due = tick(tmp_path, "2026-09-09T14:00:00+03:00", runtime)
    assert "improve-workflow" in message(due)
    for event in ("PreCompact", "PostCompact", "SessionStart", "PostToolUse"):
        assert "improve-workflow" in message(tick(tmp_path, "2026-09-09T14:01:00+03:00", runtime, event))
    cli(*ack(tmp_path, runtime, verification=" "), ok=False)
    assert "improve-workflow" in message(tick(tmp_path, "2026-09-09T14:04:00+03:00", runtime))
    cli(*ack(tmp_path, runtime))
    assert "improve-workflow" not in message(tick(tmp_path, "2026-09-09T16:04:59+03:00", runtime))
    assert "improve-workflow" in message(tick(tmp_path, "2026-09-09T16:05:00+03:00", runtime))


def test_no_agents_directory_or_card_and_new_cycle_cannot_reset(tmp_path):
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    tasks = tmp_path / ".agents/tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    for hour in (13, 14, 17, 21):
        (tasks / "work-new.md").write_text(
            f"Started at: 2026-09-09T{hour}:00:00+03:00\nInitial estimate: 25 / 45\n")
        result = tick(tmp_path, f"2026-09-09T{hour}:00:00+03:00")
        assert ("improve-workflow" in message(result)) == (hour >= 14)
    state_files = list((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    assert len(state_files) == 1
    state = json.loads(state_files[0].read_text())
    assert state["started_at"] == "2026-09-09T12:00:00+03:00"
    assert state["last_checkpoint"] is None
    assert "active_minutes" not in state
    assert "improve-workflow" in message(tick(tmp_path, "2026-09-09T13:00:00+03:00"))


def test_ack_requires_existing_due_and_matching_deadline(tmp_path):
    (tmp_path / ".agents").mkdir()
    cli(*ack(tmp_path), ok=False)
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    cli(*ack(tmp_path, now="2026-09-09T13:00:00+03:00"), ok=False)
    cli(*ack(tmp_path, **{"due-at": "2026-09-09T13:00:00+03:00"}), ok=False)
    cli(*ack(tmp_path, **{"method-change": None, "no-change-reason": "The scoped method passed the real canary; no change justified."}))
    cli(*ack(tmp_path), ok=False)


def test_sessions_are_independent_and_state_is_bounded(tmp_path):
    (tmp_path / ".agents").mkdir()
    tick(tmp_path, "2026-09-09T12:00:00+03:00", session="parent/a")
    tick(tmp_path, "2026-09-09T13:00:00+03:00", session="parent-a")
    assert "improve-workflow" in message(tick(tmp_path, "2026-09-09T14:00:00+03:00", session="parent/a"))
    assert "improve-workflow" not in message(tick(tmp_path, "2026-09-09T14:00:00+03:00", session="parent-a"))
    files = list((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    assert len(files) == 2
    assert all(file.stat().st_size < 32768 for file in files)


def test_due_survives_corrupt_optional_cycle_state(tmp_path):
    tasks = tmp_path / ".agents/tasks"
    tasks.mkdir(parents=True)
    (tasks / "work-current.md").write_text(
        "Started at: 2026-09-09T12:00:00+03:00\nInitial estimate: 25 / 45\n")
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    cycle = next((tmp_path / ".agents/shared-session/time").glob("*.json"))
    cycle.write_text("{invalid JSON")
    result = tick(tmp_path, "2026-09-09T14:00:00+03:00")
    assert "improve-workflow" in message(result)
    assert result["cycle_error"] == "JSONDecodeError"


def test_nested_agents_directory_does_not_reset_parent_clock(tmp_path):
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    child = tmp_path / "src/component"
    (child / ".agents").mkdir(parents=True)
    assert "improve-workflow" in message(tick(child, "2026-09-09T14:00:00+03:00"))
    assert not (child / ".agents/shared-session/learning").exists()


def test_missing_identity_discloses_shared_fallback(tmp_path):
    for now in ("2026-09-09T12:00:00+03:00", "2026-09-09T14:00:00+03:00"):
        result = cli("hook", "--runtime", "codex", "--event", "PostToolUse", "--now", now,
                     payload={"cwd": str(tmp_path)})
    assert "Native session identity unavailable" in message(result)
    assert "isolation is NOT established" in message(result)


def test_same_project_worktree_reuses_clock(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Test",
                    "-c", "user.email=test@invalid", "commit", "--allow-empty", "-qm", "fixture"], check=True)
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    worktree = tmp_path / "trees/second"
    subprocess.run(["git", "-C", str(tmp_path), "worktree", "add", "--detach", str(worktree)],
                   capture_output=True, check=True)
    try:
        (worktree / ".agents").mkdir()
        assert "improve-workflow" in message(tick(worktree, "2026-09-09T14:00:00+03:00"))
        assert not (worktree / ".agents/shared-session/learning").exists()
    finally:
        subprocess.run(["git", "-C", str(tmp_path), "worktree", "remove", "--force", str(worktree)], check=True)


def test_bad_timezone_cycle_state_cannot_hide_due(tmp_path):
    tasks = tmp_path / ".agents/tasks"
    tasks.mkdir(parents=True)
    (tasks / "work-current.md").write_text(
        "Started at: 2026-09-09T12:00:00+03:00\nInitial estimate: 25 / 45\n")
    tick(tmp_path, "2026-09-09T12:00:00+03:00")
    cycle = next((tmp_path / ".agents/shared-session/time").glob("*.json"))
    state = json.loads(cycle.read_text())
    state["last_hook_tick_at"] = "2026-09-09T12:30:00"
    cycle.write_text(json.dumps(state))
    result = tick(tmp_path, "2026-09-09T14:00:00+03:00")
    assert "improve-workflow" in message(result)
    assert result["cycle_error"] == "ArgumentTypeError"
