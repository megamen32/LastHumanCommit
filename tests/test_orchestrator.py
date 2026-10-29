"""Orchestrator agenda from facts, and the coordination reminders."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_orchestrator as orch  # noqa: E402
import lhc_mail as mail  # noqa: E402
import lhc_entry as entry  # noqa: E402


def repo(tmp_path):
    path = tmp_path / "proj"
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_tick_names_dead_silent_unregistered_and_running(tmp_path):
    root = repo(tmp_path)
    doc = orch.load(root)
    doc["orchestrator"] = "O"
    for sid, status in (("A", "working"), ("B", "working"), ("C", "working"), ("D", "released")):
        orch.upsert(doc, sid, name="n" + sid, task="t" + sid, acceptance="acc" + sid, status=status, next="step")
    orch.save(root, doc)
    now = time.time()
    live = [{"id": "A", "name": "a", "runtime": "codex", "seen": now - 60},
            {"id": "B", "name": "b", "runtime": "opencode", "seen": now - 4 * 3600},
            {"id": "X", "name": "x", "runtime": "codex", "seen": now - 120},
            {"id": "O", "name": "orch", "runtime": "codex", "seen": now}]
    lines = orch.tick(root, live, now=now)
    kinds = sorted(line.split()[0] for line in lines)
    assert kinds == ["DEAD", "RUNNING", "SILENT", "UNREGISTERED"]  # C dead, A running, B silent, X unknown
    assert not any(line.startswith("DEAD D") for line in lines)


def test_live_sources_read_codex_and_opencode_for_the_project(tmp_path):
    home = tmp_path / "codex"
    day = home / "sessions/2026/10/29"
    day.mkdir(parents=True)
    mine = day / "rollout-2026-10-29T01-00-00-01a18452-d524-75d2-8076-b9c9e3ee3320.jsonl"
    mine.write_text(json.dumps({"type": "session_meta", "payload": {"cwd": "/w/worktrees/f9/Proj"}}) + "\n")
    other = day / "rollout-2026-10-29T01-00-00-01a18452-d524-75d2-8076-aaaaaaaaaaaa.jsonl"
    other.write_text(json.dumps({"type": "session_meta", "payload": {"cwd": "/w/other"}}) + "\n")
    found = orch.codex_live("proj", time.time() - 600, home=home)
    assert [s["id"] for s in found] == ["01a18452-d524-75d2-8076-b9c9e3ee3320"]
    assert orch.opencode_live("proj", 0, database=tmp_path / "none.db") == []


def test_archive_keeps_the_registry_to_the_current_state(tmp_path):
    root = repo(tmp_path)
    doc = orch.load(root)
    orch.upsert(doc, "A", status="released")
    orch.upsert(doc, "B", status="working")
    doc["sessions"][0]["last_seen"] = "2026-10-01T00:00:00+00:00"
    orch.save(root, doc)
    assert [r["id"] for r in orch.archive(root, hours=6)] == ["A"]
    assert [r["id"] for r in orch.load(root)["sessions"]] == ["B"]
    assert '"A"' in root.joinpath(".agents/sessions-archive.jsonl").read_text()


def test_coordination_pulse_for_orchestrator_registry_and_unread_mail(tmp_path, monkeypatch):
    root = repo(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    doc = orch.load(root)
    doc["orchestrator"] = "O"
    orch.save(root, doc)
    old = time.time() - 3600
    os.utime(orch.reg_file(root), (old, old))
    mail.send(root, "S", "O", "step", "do the next thing")
    event = {"cwd": str(root), "session_id": "O"}
    text = entry.coordination_pulse(event, ROOT)
    assert "registry" in text and "lhc_orchestrator.py tick" in text
    assert entry.coordination_pulse(event, ROOT) is None  # once per window
    worker = entry.coordination_pulse({"cwd": str(root), "session_id": "S"}, ROOT)
    assert "unread" in worker and "lhc_mail.py" in worker


def test_relative_root_still_finds_the_project_name(tmp_path, monkeypatch):
    root = repo(tmp_path)
    monkeypatch.chdir(root)
    seen = []
    monkeypatch.setattr(orch, "codex_live", lambda project, since, home=None: seen.append(project) or [])
    monkeypatch.setattr(orch, "opencode_live", lambda project, since, database=None: [])
    orch.live_sessions(Path("."))
    assert seen == ["proj"]
