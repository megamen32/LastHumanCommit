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


def test_stop_gate_holds_a_stop_while_leaves_are_untouched(tmp_path, monkeypatch):
    import json
    import lhc_entry as entry
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    plan = repo / ".agents/tasks/20261029-x"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text("{}")
    for name, status in (("L01", "done"), ("L02", "queued"), ("L03", "blocked")):
        (plan / f"leaves/{name}.json").write_text(json.dumps({"id": name, "status": status}))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    event = {"cwd": str(repo), "session_id": "s1"}
    text = entry.stop_gate(event, ROOT)
    assert "L02" in text and "1 blocked" in text
    assert entry.stop_gate({**event, "stop_hook_active": True}, ROOT) is None
    assert entry.stop_gate({**event, "agent_id": "a"}, ROOT) is None
    assert entry.stop_gate(event, ROOT)            # second hold
    assert entry.stop_gate(event, ROOT) is None    # then the session is released
    (plan / "leaves/L02.json").write_text(json.dumps({"id": "L02", "status": "done"}))
    assert entry.stop_gate({**event, "session_id": "s2"}, ROOT) is None  # nothing left to do


def test_registry_names_the_orchestrator_and_each_row(tmp_path, monkeypatch):
    import json
    import lhc_entry as entry
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".agents").mkdir()
    (repo / ".agents/sessions.json").write_text(json.dumps({
        "orchestrator": "ses_o",
        "sessions": [{"id": "ses_s", "role": "sentinel", "task": "watch views", "acceptance": "OK-check", "next": "check Telemeter"}]}))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    now = 1_800_000_000
    orch = entry.coordination_pulse({"cwd": str(repo), "session_id": "ses_o"}, ROOT, now=now)
    assert "orchestrator" in orch and "do not do the work" in orch
    assert entry.coordination_pulse({"cwd": str(repo), "session_id": "ses_o"}, ROOT, now=now + 60) is None
    row = entry.coordination_pulse({"cwd": str(repo), "session_id": "ses_s"}, ROOT, now=now)
    assert "watch views" in row and "OK-check" in row and "Sentinel" in row
    assert entry.coordination_pulse({"cwd": str(repo), "session_id": "ses_x"}, ROOT, now=now) is None


def test_opencode_install_registers_the_plan_mcp_and_role_profiles(tmp_path):
    import importlib.util, json
    spec = importlib.util.spec_from_file_location("lhc_install", ROOT / "plugins/last-human-commit/scripts/install_runtime.py")
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)
    home = tmp_path / "home"
    plugin = ROOT / "plugins/last-human-commit"
    config = home / ".config/opencode/opencode.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcp": {"other": {"type": "remote", "url": "x"}}}))
    result = install.configure(home, plugin, "opencode")
    data = json.loads(config.read_text())
    assert data["mcp"]["other"]["url"] == "x"
    assert data["mcp"]["LhcPlan"]["command"][1].endswith("scripts/plan_mcp.py")
    assert (home / ".config/opencode/agents/orchestrator.md").read_text().startswith("---\ndescription:")
    assert (home / ".config/opencode/agents/sentinel.md").is_file()
    assert result["plugin"]["mcp"] == "registered"
    again = install.configure(home, plugin, "opencode")
    assert again["plugin"]["mcp"] == "unchanged"


def test_opencode_install_does_not_duplicate_an_installed_plugin(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("lhc_install2", ROOT / "plugins/last-human-commit/scripts/install_runtime.py")
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)
    home = tmp_path / "home"
    plugin = ROOT / "plugins/last-human-commit"
    plugins = home / ".config/opencode/plugins"
    plugins.mkdir(parents=True)
    (plugins / "last-human-commit.ts").symlink_to(plugin / "opencode/lhc-v2.ts")
    install.configure(home, plugin, "opencode", opencode_plugin_dir=plugins)
    install.configure(home, plugin, "opencode", opencode_plugin_dir=plugins)
    assert sorted(f.name for f in plugins.glob("*.ts")) == ["last-human-commit.ts"]
    fresh = tmp_path / "home2"
    install.configure(fresh, plugin, "opencode")
    install.configure(fresh, plugin, "opencode")
    assert [f.name for f in (fresh / ".config/opencode/plugin").glob("*.ts")] == ["lhc-v2.ts"]


def _plan(tmp_path, leaves, meta=None):
    import json
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    plan = repo / ".agents/tasks/20261030-x"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps(meta or {}))
    for leaf in leaves:
        (plan / "leaves" / (leaf["id"] + ".json")).write_text(json.dumps(leaf))
    return repo, plan


def test_stamp_leaf_records_start_and_finish_once(tmp_path):
    import json
    import lhc_entry as entry
    repo, plan = _plan(tmp_path, [{"id": "L01", "status": "running"}])
    leaf = plan / "leaves/L01.json"
    entry.stamp_leaf(leaf)
    first = json.loads(leaf.read_text())
    assert "T" in first["started_at"] and "finished_at" not in first
    first["status"] = "done"
    leaf.write_text(json.dumps(first))
    entry.stamp_leaf(leaf)
    done = json.loads(leaf.read_text())
    assert done["started_at"] == first["started_at"] and "T" in done["finished_at"]
    stamped = done["finished_at"]
    entry.stamp_leaf(leaf)
    assert json.loads(leaf.read_text())["finished_at"] == stamped


def test_plan_audit_names_a_done_leaf_over_unfinished_dependencies(tmp_path, monkeypatch):
    import lhc_entry as entry
    repo, plan = _plan(tmp_path, [
        {"id": "L01", "status": "done", "depends_on": []},
        {"id": "L02", "status": "running", "depends_on": ["L01"]},
        {"id": "L03", "status": "done", "depends_on": ["L01", "L02"]}])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    event = {"cwd": str(repo), "session_id": "s1"}
    text = entry.plan_audit(event, ROOT, now=1_800_000_000)
    assert "L03 is done while L02" in text and "decomposition" in text
    assert entry.plan_audit(event, ROOT, now=1_800_000_060) is None  # once per window


def test_plan_audit_is_quiet_when_the_decomposition_was_checked(tmp_path, monkeypatch):
    import lhc_entry as entry
    repo, plan = _plan(tmp_path, [
        {"id": "L01", "status": "done"}, {"id": "L02", "status": "running", "depends_on": ["L01"]},
        {"id": "L03", "status": "queued", "depends_on": ["L02"]}], meta={"decomposition_check": {"by": "adviser"}})
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert entry.plan_audit({"cwd": str(repo), "session_id": "s1"}, ROOT, now=1_800_000_000) is None


def test_effort_falls_back_to_the_clock_span():
    import lhc_grid as grid
    leaf = grid.Leaf("L01")
    leaf.started_at, leaf.finished_at = "2026-10-30T10:00:00+03:00", "2026-10-30T10:45:00+03:00"
    assert grid.effort_text(leaf) == "45 мин по часам"
    leaf.actual_minutes = 90
    assert grid.effort_text(leaf) == "1 ч 30 мин"
    leaf.actual_minutes, leaf.started_at, leaf.finished_at = None, "", ""
    assert grid.effort_text(leaf) == "не измерено"
