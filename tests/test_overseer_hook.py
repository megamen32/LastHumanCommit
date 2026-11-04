"""The automatic Overseer review: a default-on hook asks the Lead every 30 min of an active plan."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_entry as entry  # noqa: E402
import lhc_overseer_ack as ack  # noqa: E402

HALF_HOUR = 1800
ENTRIES = ["plugins/last-human-commit/tools/lhc_entry.py",
           "plugins/last-human-commit/native/codex/tools/lhc_entry.py"]
HOOK_FILES = ["plugins/last-human-commit/hooks/hooks.json", "plugins/last-human-commit/hooks/zcode-hooks.json",
              "plugins/last-human-commit/com.openai/hooks/hooks.json",
              "plugins/last-human-commit/native/codex/hooks/hooks.json",
              "plugins/last-human-commit/native/codex/hooks/zcode-hooks.json",
              "plugins/last-human-commit/native/codex/com.openai/hooks/hooks.json"]


def make_plan(tmp_path, statuses=(("L01", "running"),), name="20261104-x"):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    plan = repo / ".agents/tasks" / name
    (plan / "leaves").mkdir(parents=True, exist_ok=True)
    (plan / "plan.json").write_text("{}")
    for ident, status in statuses:
        (plan / "leaves" / f"{ident}.json").write_text(json.dumps({"id": ident, "status": status}))
    return repo, plan


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("LHC_OVERSEER", raising=False)


def test_stop_blocks_when_the_plan_is_active_and_not_reviewed_for_30_minutes(tmp_path):
    repo, plan = make_plan(tmp_path)
    event = {"cwd": str(repo), "session_id": "s1"}
    now = time.time()
    assert entry.overseer_review(event, ROOT, "stop", now=now) is None            # the first sight starts the clock
    assert entry.overseer_review(event, ROOT, "stop", now=now + 600) is None      # fresh
    text = entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 5)
    assert "Overseer" in text and "zero-knowledge" in text and "read-only" in text
    assert "original owner request" in text and "plan report" in text and "lhc_overseer_ack.py" in text
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 60) is None   # once per boundary
    assert entry.overseer_review(event, ROOT, "stop", now=now + 2 * HALF_HOUR + 5)        # next boundary


def test_a_review_mark_restarts_the_clock(tmp_path):
    repo, plan = make_plan(tmp_path)
    event = {"cwd": str(repo), "session_id": "s1"}
    now = time.time()
    entry.overseer_review(event, ROOT, "stop", now=now)
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 1)
    assert ack.ack(plan, now=now + HALF_HOUR + 120)
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 120 + 600) is None   # fresh review
    assert entry.overseer_review(event, ROOT, "stop", now=now + 2 * HALF_HOUR + 200)               # due again


def test_post_tool_use_reminds_once_per_boundary_independently_of_stop(tmp_path):
    repo, plan = make_plan(tmp_path)
    event = {"cwd": str(repo), "session_id": "s1"}
    now = time.time()
    entry.overseer_review(event, ROOT, "post", now=now)
    assert entry.overseer_review(event, ROOT, "post", now=now + HALF_HOUR + 1)
    assert entry.overseer_review(event, ROOT, "post", now=now + HALF_HOUR + 90) is None
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 100)   # Stop still asks once


def test_no_block_without_a_plan_for_finished_plans_subagents_and_refusals(tmp_path, monkeypatch):
    now = time.time()
    bare = tmp_path / "bare"
    (bare / ".git").mkdir(parents=True)
    event = {"cwd": str(bare), "session_id": "s1"}
    assert entry.overseer_review(event, ROOT, "stop", now=now + 99999) is None      # no plan: a trivial turn
    repo, plan = make_plan(tmp_path / "a", (("L01", "done"),))
    event = {"cwd": str(repo), "session_id": "s1"}
    entry.overseer_review(event, ROOT, "stop", now=now)
    assert entry.overseer_review(event, ROOT, "stop", now=now + 4 * HALF_HOUR) is None   # nothing is active
    repo, plan = make_plan(tmp_path / "b")
    event = {"cwd": str(repo), "session_id": "s1"}
    entry.overseer_review(event, ROOT, "stop", now=now)
    assert entry.overseer_review({**event, "agent_id": "w"}, ROOT, "stop", now=now + HALF_HOUR + 5) is None
    monkeypatch.setenv("LHC_OVERSEER", "off")
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 5) is None
    monkeypatch.delenv("LHC_OVERSEER")
    assert ack.main(["--off", "--plan", str(plan)]) == 0     # the owner said STOP
    assert entry.overseer_review(event, ROOT, "stop", now=now + HALF_HOUR + 5) is None


def test_failures_open_silently(tmp_path, monkeypatch):
    repo, plan = make_plan(tmp_path)
    event = {"cwd": str(repo), "session_id": "s1"}
    now = time.time()
    entry.overseer_review(event, ROOT, "stop", now=now)
    ack.state_file(plan).write_text("{not json")
    assert entry.overseer_review(event, ROOT, "stop", now=now + 99999) is None      # corrupt state: restarts the clock
    monkeypatch.setattr(ack, "write_state", lambda *a, **k: False)
    assert entry.overseer_review(event, ROOT, "stop", now=now + 99999) is None      # cannot persist a mark: no loop
    (plan / "leaves/L02.json").write_text("{broken")
    assert entry.overseer_review(event, ROOT, "stop", now=now + 99999) is None
    assert entry.overseer_review({"cwd": 5, "session_id": "s1"}, ROOT, "stop") is None
    assert entry.overseer_review({}, ROOT, "stop") is None


def run_entry(entry_path, flag, event, env, tmp_path):
    return subprocess.run([sys.executable, str(ROOT / entry_path), "--event", flag[0], flag[1]],
                          input=event if isinstance(event, str) else json.dumps(event),
                          capture_output=True, text=True, env={**os.environ, **env, "HOME": str(tmp_path / "home")})


@pytest.mark.parametrize("entry_path", ENTRIES)
def test_stop_hook_prints_the_block_decision_like_the_git_guard(entry_path, tmp_path):
    repo, plan = make_plan(tmp_path)
    env = {"XDG_STATE_HOME": str(tmp_path / "state")}
    ack.write_state(plan, {"since": time.time() - 2 * HALF_HOUR})
    event = {"cwd": str(repo), "session_id": "s1"}
    done = run_entry(entry_path, ("Stop", "--stop-gate"), event, env, tmp_path)
    out = json.loads(done.stdout)
    assert out["decision"] == "block" and "zero-knowledge" in out["reason"], done.stderr
    assert (ROOT / entry_path).with_name("lhc_overseer_ack.py").is_file()
    assert "zero-knowledge" not in run_entry(entry_path, ("Stop", "--stop-gate"), event, env, tmp_path).stdout  # once per boundary
    assert run_entry(entry_path, ("Stop", "--stop-gate"), {**event, "stop_hook_active": True}, env, tmp_path).stdout == ""
    assert run_entry(entry_path, ("Stop", "--stop-gate"), "not json", env, tmp_path).stdout == ""  # fail open


@pytest.mark.parametrize("entry_path", ENTRIES)
def test_post_tool_use_hook_adds_the_reminder_to_the_context(entry_path, tmp_path):
    repo, plan = make_plan(tmp_path)
    env = {"XDG_STATE_HOME": str(tmp_path / "state")}
    ack.write_state(plan, {"since": time.time() - 2 * HALF_HOUR})
    done = run_entry(entry_path, ("PostToolUse", "--heartbeat-only"),
                     {"cwd": str(repo), "session_id": "s1", "tool_name": "Bash"}, env, tmp_path)
    contexts = [json.loads(line)["hookSpecificOutput"]["additionalContext"] for line in done.stdout.splitlines()
                if line.startswith("{") and "hookSpecificOutput" in line]
    assert any("Overseer review" in c for c in contexts), (done.stdout, done.stderr)


def test_the_mark_command_records_a_review_and_the_published_copies_carry_it(tmp_path):
    repo, plan = make_plan(tmp_path)
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path / "state")}
    for tools in ("src/common/tools", "plugins/last-human-commit/tools", "plugins/last-human-commit/common/tools",
                  "plugins/last-human-commit/native/codex/tools", "plugins/last-human-commit/native/codex/common/tools"):
        done = subprocess.run([sys.executable, str(ROOT / tools / "lhc_overseer_ack.py")], cwd=repo, env=env,
                              capture_output=True, text=True)
        assert done.returncode == 0 and "review recorded" in done.stdout, (tools, done.stderr)
        assert ack.read_state(plan)["last_review"] > time.time() - 60


@pytest.mark.parametrize("hook_file", HOOK_FILES)
def test_the_hook_runs_from_every_hooks_json(hook_file):
    hooks = json.loads((ROOT / hook_file).read_text())["hooks"]
    commands = {event: " ".join(h["command"] for r in hooks[event] for h in r["hooks"]) for event in ("Stop", "PostToolUse")}
    assert "lhc_entry.py" in commands["Stop"] and "--stop-gate" in commands["Stop"]
    assert "lhc_entry.py" in commands["PostToolUse"] and "--heartbeat-only" in commands["PostToolUse"]


def test_opencode_runs_the_same_stop_gate_on_idle():
    source = (ROOT / "plugins/last-human-commit/opencode/lhc-v2.ts").read_text()
    assert '"--stop-gate"' in source and "session.idle" in source
