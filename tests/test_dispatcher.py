"""Dispatcher agenda from facts, the coordination reminders, and the pre-1.10 names that still work."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_dispatcher as orch  # noqa: E402
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
    doc["dispatcher"] = "O"
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


def test_coordination_pulse_for_dispatcher_registry_and_unread_mail(tmp_path, monkeypatch):
    root = repo(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    doc = orch.load(root)
    doc["dispatcher"] = "O"
    orch.save(root, doc)
    old = time.time() - 3600
    os.utime(orch.reg_file(root), (old, old))
    mail.send(root, "S", "O", "step", "do the next thing")
    event = {"cwd": str(root), "session_id": "O"}
    text = entry.coordination_pulse(event, ROOT)
    assert "registry" in text and "lhc_dispatcher.py tick" in text
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


def test_old_tool_name_is_the_same_module_and_still_runs(tmp_path):
    import importlib
    old = importlib.import_module("lhc_orchestrator")
    assert old is orch and old.load is orch.load
    root = repo(tmp_path)
    done = subprocess.run([sys.executable, str(ROOT / "src/common/tools/lhc_orchestrator.py"), "--root", str(root), "init", "S1"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert json.loads(orch.reg_file(root).read_text())["dispatcher"] == "S1"
    tick = subprocess.run([sys.executable, str(ROOT / "src/common/tools/lhc_orchestrator.py"), "--root", str(root), "tick"],
                          capture_output=True, text=True, env={**os.environ, "LHC_CODEX_HOME": str(tmp_path / "none"),
                                                              "LHC_OPENCODE_DB": str(tmp_path / "none.db")})
    assert tick.returncode == 0 and "dispatcher S1" in tick.stdout and "rchestr" not in tick.stdout


def test_registry_with_the_old_key_reads_as_dispatcher_and_keeps_the_old_key_in_step(tmp_path):
    root = repo(tmp_path)
    orch.reg_file(root).parent.mkdir(parents=True)
    orch.reg_file(root).write_text(json.dumps({"orchestrator": "OLD", "sessions": []}))
    doc = orch.load(root)
    assert doc["dispatcher"] == "OLD" and "orchestrator" not in doc
    doc["dispatcher"] = "NEW"
    orch.save(root, doc)
    saved = json.loads(orch.reg_file(root).read_text())
    assert saved["dispatcher"] == "NEW" and saved["orchestrator"] == "NEW"  # older hooks still read it
    (tmp_path / "x").mkdir()
    fresh = repo(tmp_path / "x")
    orch.save(fresh, orch.load(fresh))
    assert "orchestrator" not in json.loads(orch.reg_file(fresh).read_text())


def test_mail_to_the_old_address_reaches_the_dispatcher_and_old_files_are_still_read(tmp_path):
    root = repo(tmp_path)
    old = mail.box(root, "ORCHESTRATOR")
    assert old.name == "DISPATCHER" and mail.box(root, "dispatcher") == old
    path = mail.send(root, "ORCHESTRATOR", "sentinel", "result", "facts")
    assert path.parent.name == "DISPATCHER"
    legacy = root / ".agents/mail/ORCHESTRATOR"
    legacy.mkdir(parents=True)
    (legacy / "20200101T000000000000-x-ping.md").write_text("from: x\nkind: ping\n\nold\n")
    names = [p.name for p in mail.inbox(root, "ORCHESTRATOR")]
    assert names[0].startswith("2020") and len(names) == 2 and mail.inbox(root, "DISPATCHER") == mail.inbox(root, "ORCHESTRATOR")
    mail.ack(root, "ORCHESTRATOR", names[0])
    assert len(mail.inbox(root, "DISPATCHER")) == 1


def test_dispatcher_session_sees_role_address_mail_and_old_key_in_the_pulse(tmp_path, monkeypatch):
    root = repo(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    orch.reg_file(root).parent.mkdir(parents=True)
    orch.reg_file(root).write_text(json.dumps({"orchestrator": "D", "sessions": []}))
    mail.send(root, "ORCHESTRATOR", "S", "result", "done")
    text = entry.coordination_pulse({"cwd": str(root), "session_id": "D"}, ROOT)
    assert "dispatcher" in text and "unread" in text and "rchestr" not in text
