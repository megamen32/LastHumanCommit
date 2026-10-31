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


def test_plan_audit_demands_a_replan_when_a_leaf_runs_past_its_estimate(tmp_path, monkeypatch):
    import json, time
    from datetime import datetime, timedelta
    import lhc_entry as entry
    began = (datetime.now().astimezone() - timedelta(minutes=118)).isoformat(timespec="seconds")
    repo, plan = _plan(tmp_path, [{"id": "L01", "status": "running", "started_at": began,
                                   "estimate_minutes": {"minimum": 60, "maximum": 120},
                                   "estimate_over_limit_reason": "one long build"}])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    event = {"cwd": str(repo), "session_id": "s1"}
    assert entry.plan_audit(event, ROOT, now=time.time()) is None  # 118 of 120 min: still inside
    later = entry.plan_audit(event, ROOT, now=time.time() + 15 * 60)
    assert "L01 has run" in later and "re-plan" in later and "revisions" in later
    assert entry.plan_audit(event, ROOT, now=time.time() + 15 * 60 + 30) is None  # once per 15 min


def test_plan_revisions_reach_the_page(tmp_path):
    import json, subprocess, sys
    repo, plan = _plan(tmp_path, [{"id": "L01", "status": "done", "label": "first", "estimate_minutes": {"minimum": 10, "maximum": 15}}],
                       meta={"title": "T", "goal": "g", "business_result": "r",
                             "revisions": [{"at": "2026-10-30T19:00:00+03:00", "reason": "leaf ran 2 h", "summary": "split into 8 leaves"}]})
    tools = ROOT / "src/common/tools"
    subprocess.run([sys.executable, str(tools / "lhc_plan_json.py"), "build", str(plan)], check=True, capture_output=True)
    graph = json.loads((plan / "plan.graph.json").read_text())
    assert graph["revisions"][0]["reason"] == "leaf ran 2 h"
    subprocess.run([sys.executable, str(tools / "lhc_grid.py"), "render", str(plan / "plan.graph.json"), "--out-dir", str(plan)],
                   check=True, capture_output=True)
    html = (plan / "plan.html").read_text()
    assert "Версии плана" in html and "split into 8 leaves" in html


def _stages(tmp_path, extra=()):
    leaves = [
        {"id": "L01", "label": "Look at stash and trees", "kind": "milestone", "status": "queued"},
        {"id": "L02", "label": "List", "status": "done", "parent": "L01", "depends_on": []},
        {"id": "L03", "label": "Decide", "status": "queued", "parent": "L01", "depends_on": ["L02"]},
        {"id": "L04", "label": "Merge", "status": "queued", "depends_on": ["L01"]},
        *extra]
    return _plan(tmp_path, leaves)


def test_a_milestone_is_read_from_its_leaves_and_dependents_wait_for_all(tmp_path):
    import lhc_plan_json as pj
    repo, plan = _stages(tmp_path)
    doc = pj.build_document(plan)
    assert [t["id"] for t in doc["tasks"]] == ["L02", "L03", "L04"]
    assert next(t for t in doc["tasks"] if t["id"] == "L04")["depends_on"] == ["L02", "L03"]
    stage = doc["milestones"][0]
    assert (stage["id"], stage["status"], stage["done"], stage["total"]) == ("L01", "running", 1, 2)
    leaf = plan / "leaves/L03.json"
    leaf.write_text(leaf.read_text().replace("queued", "done"))
    assert pj.build_document(plan)["milestones"][0]["status"] == "done"


def test_a_milestone_without_leaves_stays_one_queued_leaf_and_bad_parents_fail(tmp_path):
    import lhc_plan_json as pj
    repo, plan = _plan(tmp_path, [{"id": "L01", "label": "Stage", "kind": "milestone", "status": "done"}])
    doc = pj.build_document(plan)
    assert doc["tasks"][0]["status"] == "queued" and doc["tasks"][0]["label"].startswith("Этап")
    repo, plan = _plan(tmp_path / "x", [{"id": "L01", "label": "A", "status": "queued", "parent": "L09"}])
    with pytest.raises(pj.LeafError):
        pj.build_document(plan)
    repo, plan = _plan(tmp_path / "y", [{"id": "L01", "label": "A", "status": "queued"},
                                         {"id": "L02", "label": "B", "status": "queued", "parent": "L01"}])
    with pytest.raises(pj.LeafError):
        pj.build_document(plan)


def test_plan_audit_says_once_that_a_leaf_is_too_long_and_which_stage_is_next(tmp_path, monkeypatch):
    import lhc_entry as entry
    repo, plan = _plan(tmp_path, [
        {"id": "L01", "status": "queued", "estimate_minutes": {"minimum": 60, "maximum": 120}},
        {"id": "L02", "status": "queued", "estimate_minutes": 15}])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    event = {"cwd": str(repo), "session_id": "s1"}
    text = entry.plan_audit(event, ROOT, now=1_800_000_000)
    assert "L01 (120 min)" in text and "L02" not in text and "milestone" in text
    assert entry.plan_audit(event, ROOT, now=1_800_000_060) is None
    repo, plan = _plan(tmp_path / "s", [
        {"id": "L01", "kind": "milestone", "status": "queued"},
        {"id": "L02", "status": "done", "parent": "L01"},
        {"id": "L03", "kind": "milestone", "status": "queued"},
        {"id": "L04", "kind": "milestone", "status": "queued"}])
    event = {"cwd": str(repo), "session_id": "s2"}
    text = entry.plan_audit(event, ROOT, now=1_800_000_000)
    assert "L03 is a milestone with no leaves" in text and "L04" not in text


def test_stop_gate_holds_for_an_uncut_stage_but_not_for_a_finished_one(tmp_path, monkeypatch):
    import time
    import lhc_entry as entry
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    repo, plan = _plan(tmp_path, [{"id": "L01", "kind": "milestone", "status": "queued"}])
    assert entry.stop_gate({"cwd": str(repo), "session_id": "s1"}, ROOT, now=time.time())
    repo, plan = _plan(tmp_path / "d", [{"id": "L01", "kind": "milestone", "status": "running"},
                                         {"id": "L02", "status": "done", "parent": "L01"}])
    assert entry.stop_gate({"cwd": str(repo), "session_id": "s2"}, ROOT, now=time.time()) is None


def test_a_finished_plan_with_clock_only_leaves_shows_its_finish(tmp_path):
    import json, subprocess, sys
    repo, plan = _plan(tmp_path, [
        {"id": "L01", "status": "done", "label": "a", "started_at": "17:19", "finished_at": "17:35",
         "estimate_minutes": {"minimum": 10, "maximum": 15}},
        {"id": "L02", "status": "done", "label": "b", "started_at": "19:00", "finished_at": "19:26",
         "estimate_minutes": {"minimum": 10, "maximum": 15}, "depends_on": ["L01"]}],
        meta={"title": "T", "goal": "g", "business_result": "r", "updated_at": "2026-10-30T20:05:00+00:00"})
    tools = ROOT / "src/common/tools"
    subprocess.run([sys.executable, str(tools / "lhc_plan_json.py"), "build", str(plan)], check=True, capture_output=True)
    subprocess.run([sys.executable, str(tools / "lhc_grid.py"), "render", str(plan / "plan.graph.json"), "--out-dir", str(plan)],
                   check=True, capture_output=True)
    html = (plan / "plan.html").read_text()
    assert "Фактический финиш: 30.10.2026 19:26" in html     # a bare clock is placed on the last day not past the last update
    assert "Фактический финиш не зафиксирован" not in html


def test_price_snapshots_of_an_installed_copy_share_one_user_cache(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("lhc_models_cache", ROOT / "src/common/tools/lhc_models.py")
    models = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = models
    spec.loader.exec_module(models)
    monkeypatch.delenv("LHC_MODELS_CACHE", raising=False)
    assert models.default_cache_dir() == ROOT / ".tmp" / "lhc_models"          # a checkout keeps its own .tmp
    fake = tmp_path / "pkg" / "a" / "b" / "src" / "tool.py"                     # no .git up the tree
    fake.parent.mkdir(parents=True)
    monkeypatch.setattr(models, "__file__", str(fake))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert models.default_cache_dir() == tmp_path / "cache" / "lhc" / "models"
    monkeypatch.setenv("LHC_MODELS_CACHE", str(tmp_path / "pinned"))
    assert models.default_cache_dir() == tmp_path / "pinned"


def test_opencode_install_replaces_a_stale_role_profile_and_links_the_skills(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("lhc_install3", ROOT / "plugins/last-human-commit/scripts/install_runtime.py")
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)
    home = tmp_path / "home"
    plugin = ROOT / "plugins/last-human-commit"
    agents = home / ".config/opencode/agents"
    agents.mkdir(parents=True)
    (agents / "lead.md").write_text("old Lead: present exactly three plans and wait for the human\n")
    hand = home / ".config/opencode/skills/planning"
    hand.mkdir(parents=True)
    (hand / "SKILL.md").write_text("mine")
    install.configure(home, plugin, "opencode")
    assert "three plans" not in (agents / "lead.md").read_text()
    for role in install.OPENCODE_ROLES:
        assert (agents / f"{role.lower()}.md").is_file(), role
    assert (agents / "lead.md").read_text().startswith("---\ndescription:")
    assert any("three plans" in f.read_text() for f in home.rglob("*") if f.is_file() and "backup" in str(f).lower())
    assert (hand / "SKILL.md").read_text() == "mine"                      # a hand-made skill is left alone
    skills = home / ".config/opencode/skills"
    assert any(p.is_symlink() for p in skills.iterdir())
    install.configure(home, plugin, "opencode")                           # a second run changes nothing


def test_an_unanswered_session_checkpoint_is_said_once_not_after_every_tool_call(tmp_path):
    import argparse
    import lhc_time_guard as guard
    t0 = datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc)
    def look(minutes):
        return guard.learning_checkpoint(argparse.Namespace(runtime="claude", now=t0 + timedelta(minutes=minutes)),
                                         tmp_path, "s1")
    assert look(0)["prompt"] == ""                              # first observation starts the clock
    first = look(121)
    assert "120 wall-clock minutes" in first["prompt"] and first["due"]
    for minutes in (122, 130, 170):                             # still due, not repeated
        again = look(minutes)
        assert again["due"] and again["prompt"] == ""
    assert "120 wall-clock minutes" in look(182)["prompt"]      # an hour later it is said again


def test_an_unanswered_hourly_direction_check_is_not_repeated_every_five_minutes(tmp_path):
    import argparse
    import lhc_time_guard as guard
    t0 = datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc)
    def look(minutes):
        args = argparse.Namespace(runtime="claude", now=t0 + timedelta(minutes=minutes), event="")  # no native interval: the wall deadline decides
        guard.learning_checkpoint(args, tmp_path, "s1")      # the hook observes the session first
        return guard.business_checkpoint(args, tmp_path, "s1", {})
    assert look(0)["prompt"] == ""
    first = look(61)
    assert first["due"] and "hourly LHC direction check" in first["prompt"]
    for minutes in (62, 70, 118):
        again = look(minutes)
        assert again["due"] and again["prompt"] == ""
    assert "hourly LHC direction check" in look(125)["prompt"]
