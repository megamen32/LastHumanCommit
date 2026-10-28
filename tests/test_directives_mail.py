"""Owner directives (term, history) and file mail between sessions."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_directives as d  # noqa: E402
import lhc_mail as mail  # noqa: E402

T0 = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def test_a_directive_needs_a_term_or_permanent():
    doc = d.empty()
    with pytest.raises(ValueError):
        d.add(doc, "turn it off", "", now=T0)
    assert d.add(doc, "keep calm", "permanent", now=T0)["until"] is None
    assert d.add(doc, "turn it off", "+2d", now=T0)["until"] == "2026-10-30T12:00:00+00:00"


def test_an_expired_directive_leaves_the_main_list_for_the_history():
    doc = d.empty()
    d.add(doc, "turn it off", "+2d", "switch it back on", now=T0)
    d.add(doc, "always blue-green", "permanent", now=T0)
    d.sweep(doc, T0 + timedelta(days=3))
    assert [i["text"] for i in doc["active"]] == ["always blue-green"]
    assert doc["history"][0]["reason"] == "expired"
    view = d.view(doc, T0 + timedelta(days=3))
    assert view["just_ended"][0]["on_expire"] == "switch it back on"
    assert not d.view(doc, T0 + timedelta(days=9))["just_ended"]


def test_owner_actions_and_agent_context():
    doc = d.empty()
    d.apply(doc, {"action": "add", "text": "stop deploys", "until": "+6h"}, T0)
    ident = doc["active"][0]["id"]
    d.apply(doc, {"action": "update", "id": ident, "until": "permanent"}, T0)
    assert doc["active"][0]["until"] is None
    snap = d.apply(doc, {"action": "end", "id": ident}, T0)
    assert not snap["active"] and doc["history"][0]["reason"] == "cancelled"
    with pytest.raises(ValueError):
        d.apply(doc, {"action": "nope"}, T0)
    live = d.apply(d.empty(), {"action": "add", "text": "stop deploys", "until": "+6h"}, T0)
    assert "stop deploys" in d.context(live)
    assert d.context(d.view(d.empty(), T0)) == ""


def test_file_mail_round_trip_between_worktrees(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    root = mail.primary_root(repo)
    path = mail.send(root, "s2", "orch", "task", "finish the deploy", T0)
    assert mail.inbox(root, "s2") == [path]
    assert "finish the deploy" in path.read_text() and "from: orch" in path.read_text()
    with pytest.raises(ValueError):
        mail.send(root, "s2", "orch", "chat", "x")
    mail.ack(root, "s2", path.name)
    assert mail.inbox(root, "s2") == [] and (path.parent / "done" / path.name).exists()


def test_plan_pulse_fires_once_when_leaves_stand_still(tmp_path, monkeypatch):
    import json, os, time
    import lhc_entry as entry
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    plan = repo / ".agents/tasks/20261028-x"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text("{}")
    leaf = plan / "leaves/L01.json"
    leaf.write_text(json.dumps({"id": "L01", "status": "running"}))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    event = {"cwd": str(repo), "session_id": "s1"}
    now = time.time()
    assert entry.plan_pulse(event, ROOT, now=now) is None  # leaf just changed
    old = now - 3600
    os.utime(leaf, (old, old))
    text = entry.plan_pulse(event, ROOT, now=now)
    assert "L01" in text and "has not changed" in text
    assert entry.plan_pulse(event, ROOT, now=now + 60) is None  # once per window
    assert entry.plan_pulse({**event, "agent_id": "a"}, ROOT, now=now + 9999) is None
