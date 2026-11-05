"""File mail reaches an idle session through the hooks: injected as context, and a Stop is held once per task letter."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_entry as entry  # noqa: E402
import lhc_mail as mail  # noqa: E402

ENTRIES = ["plugins/last-human-commit/tools/lhc_entry.py",
           "plugins/last-human-commit/native/codex/tools/lhc_entry.py"]


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def letter(repo, kind="task", text="restore browser search\nthen verify", to="s1", sender="lead"):
    return mail.send(repo, to, sender, kind, text)


def test_letter_is_found_and_injected(tmp_path):
    repo = make_repo(tmp_path)
    path = letter(repo)
    event = {"cwd": str(repo), "session_id": "s1"}
    text = entry.mail_context(event)
    assert "letter from lead (task)" in text and "restore browser search" in text and path.name in text
    assert entry.mail_context({**event, "session_id": "other"}) is None
    assert entry.mail_context({**event, "agent_id": "a1"}) is None
    assert entry.mail_context({"cwd": str(repo)}) is None
    assert entry.mail_context(event, throttle=300) is not None
    assert entry.mail_context(event, throttle=300) is None  # throttled on PostToolUse


def test_stop_blocks_an_unacked_task_once_and_not_after_ack(tmp_path):
    repo = make_repo(tmp_path)
    path = letter(repo)
    event = {"cwd": str(repo), "session_id": "s1"}
    assert "unacknowledged task letter" in entry.mail_stop(event)
    assert entry.mail_stop(event) is None  # once per letter
    second = letter(repo, kind="step", text="next step")
    assert "next step" in entry.mail_stop(event)
    mail.ack(repo, "s1", path.name)
    mail.ack(repo, "s1", second.name)
    assert entry.mail_stop(event) is None


def test_stop_ignores_non_task_letters_and_subagents(tmp_path):
    repo = make_repo(tmp_path)
    letter(repo, kind="ping", text="hello")
    event = {"cwd": str(repo), "session_id": "s1"}
    assert entry.mail_stop(event) is None
    letter(repo)
    assert entry.mail_stop({**event, "agent_id": "a1"}) is None
    assert entry.mail_stop({"cwd": str(repo)}) is None


def test_failures_open(tmp_path):
    assert entry.mail_stop({"cwd": str(tmp_path / "missing"), "session_id": "s1"}) is None
    assert entry.mail_context({"cwd": str(tmp_path / "missing"), "session_id": "s1"}) is None
    assert entry.mail_stop({"cwd": 5, "session_id": "s1"}) is None
    assert entry.mail_stop({}) is None


def run(entry_path, flag, event, tmp_path):
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path / "state"), "XDG_CONFIG_HOME": str(tmp_path / "cfg"),
           "HOME": str(tmp_path / "home")}
    return subprocess.run([sys.executable, str(ROOT / entry_path), "--event", flag[0], flag[1]],
                          input=event if isinstance(event, str) else json.dumps(event),
                          capture_output=True, text=True, env=env)


@pytest.mark.parametrize("entry_path", ENTRIES)
def test_published_entry_points_deliver_mail(entry_path, tmp_path):
    repo = make_repo(tmp_path)
    letter(repo)
    event = {"cwd": str(repo), "session_id": "s1"}
    start = run(entry_path, ("SessionStart", "--instructions-only"), event, tmp_path)
    assert "letter from lead" in json.loads(start.stdout)["hookSpecificOutput"]["additionalContext"], start.stderr
    post = run(entry_path, ("PostToolUse", "--heartbeat-only"), {**event, "tool_name": "Bash"}, tmp_path)
    contexts = [json.loads(line)["hookSpecificOutput"]["additionalContext"] for line in post.stdout.splitlines()
                if line.startswith("{") and "hookSpecificOutput" in line]
    assert any("letter from lead" in c for c in contexts), (post.stdout, post.stderr)
    stop = run(entry_path, ("Stop", "--stop-gate"), event, tmp_path)
    out = json.loads(stop.stdout)
    assert out["decision"] == "block" and "unacknowledged task letter" in out["reason"], stop.stderr
    assert run(entry_path, ("Stop", "--stop-gate"), event, tmp_path).stdout == ""
    assert run(entry_path, ("Stop", "--stop-gate"), "not json", tmp_path).stdout == ""
    assert (ROOT / entry_path).with_name("lhc_mail.py").is_file()
