"""Orphaned work: an active owner, no owner by age, no session at all, and uncertainty judged by mtime."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_orphan_work as orphan  # noqa: E402


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("LHC_CODEX_HOME", str(tmp_path / "nocodex"))
    monkeypatch.setenv("LHC_OPENCODE_DB", str(tmp_path / "none.db"))
    root = tmp_path / "repo"
    root.mkdir()
    run("git", "init", "-q", "-b", "main", cwd=root)
    run("git", "config", "user.email", "t@example.com", cwd=root)
    run("git", "config", "user.name", "t", cwd=root)
    (root / "a.txt").write_text("a")
    run("git", "add", "-A", cwd=root)
    run("git", "commit", "-q", "-m", "first", cwd=root)
    return root


def write_file(root, name, minutes_old):
    path = root / name
    path.write_text("x")
    stamp = time.time() - minutes_old * 60
    os.utime(path, (stamp, stamp))
    return path


def heartbeat(root, session, minutes_ago, cwd=None, raw=None):
    folder = root / ".agents" / "shared-session" / "learning"
    folder.mkdir(parents=True, exist_ok=True)
    seen = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    body = raw if raw is not None else json.dumps({"native_heartbeat": {
        "session_id": session, "runtime": "codex", "cwd": str(cwd or root), "last_seen_at": seen.isoformat()}})
    (folder / (session + ".json")).write_text(body)


def only(result):
    assert len(result["files"]) == 1, result
    return result["files"][0]


def test_live_heartbeat_in_the_directory_means_an_active_owner(repo):
    write_file(repo, "mine.txt", minutes_old=300)
    heartbeat(repo, "sess-1", minutes_ago=3)
    row = only(orphan.verdict(repo, 30))
    assert row["owner"]["state"] == "active" and row["owner"]["who"] == "sess-1"
    assert row["owner"]["seen_min_ago"] == 3 and "SendMessage" in row["instruction"]


def test_quiet_session_and_old_file_leave_no_owner(repo):
    write_file(repo, "left.txt", minutes_old=300)
    heartbeat(repo, "sess-1", minutes_ago=120)
    result = orphan.verdict(repo, 30)
    row = only(result)
    assert row["owner"]["state"] == "none" and result["overall"] == "none"
    assert "do not ask the owner" in row["instruction"] and result["orphans"] == [row["path"]]


def test_no_session_at_all_and_an_old_file_has_no_owner(repo):
    write_file(repo, "left.txt", minutes_old=90)
    result = orphan.verdict(repo, 30)
    assert result["checked"]["sessions_seen"] == 0
    assert only(result)["owner"]["state"] == "none"


def test_a_file_written_a_minute_ago_without_any_session_is_not_yet_orphaned(repo):
    write_file(repo, "fresh.txt", minutes_old=1)
    row = only(orphan.verdict(repo, 30))
    assert row["owner"] == {"state": "active", "who": "unknown writer", "source": "mtime", "seen_min_ago": 1}


def test_unreadable_heartbeat_is_judged_by_mtime_not_ambiguous(repo):
    heartbeat(repo, "broken", minutes_ago=0, raw="{not json")
    write_file(repo, "old.txt", minutes_old=200)
    old = orphan.verdict(repo, 30)
    assert old["checked"]["unreadable_heartbeats"] == 1
    assert only(old)["owner"]["state"] == "none"
    write_file(repo, "old.txt", minutes_old=2)
    assert only(orphan.verdict(repo, 30))["owner"]["state"] == "active"


def test_my_own_heartbeat_is_not_another_owner(repo):
    write_file(repo, "mine.txt", minutes_old=300)
    heartbeat(repo, "me", minutes_ago=0)
    assert only(orphan.verdict(repo, 30, me="me"))["owner"]["state"] == "none"


def test_a_heartbeat_in_another_directory_does_not_cover_the_file(repo, tmp_path):
    write_file(repo, "left.txt", minutes_old=300)
    other = tmp_path / "elsewhere"
    other.mkdir()
    heartbeat(repo, "sess-2", minutes_ago=1, cwd=other)
    assert only(orphan.verdict(repo, 30))["owner"]["state"] == "none"


def test_a_clean_repo_reports_clean(repo):
    assert orphan.verdict(repo, 30)["overall"] == "clean"


def test_cli_prints_json(repo):
    write_file(repo, "left.txt", minutes_old=300)
    out = run(sys.executable, str(ROOT / "src/common/tools/lhc_orphan_work.py"), "--repo", str(repo), cwd=repo)
    assert json.loads(out)["overall"] == "none"


@pytest.mark.parametrize("tool", ["plugins/last-human-commit/tools/lhc_orphan_work.py",
                                  "plugins/last-human-commit/native/codex/tools/lhc_orphan_work.py"])
def test_the_published_entry_points_run(tool, repo):
    write_file(repo, "left.txt", minutes_old=300)
    out = run(sys.executable, str(ROOT / tool), "--repo", str(repo), cwd=repo)
    assert json.loads(out)["orphans"]
