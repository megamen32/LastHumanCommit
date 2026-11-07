"""Regressions found by independent release consumers, through real admission/show."""
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import pytest
from _inprocess import load_module
from test_execution_display import leaf as execution_leaf

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
pj = load_module(TOOLS / "lhc_plan_json.py", name="lhc_release_acceptance_regressions")

def make_plan(tmp_path, monkeypatch, rows):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("LHC_MCP_ACTOR_CONTEXT", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "absent"))
    plan = tmp_path / "plan"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"title": "Release acceptance", "slots": 1}))
    for row in rows:
        value = {"label": row["id"], "status": "queued", "kind": "task", **row}
        (plan / "leaves" / (value["id"] + ".json")).write_text(json.dumps(value))
    return plan

def assign_idle(plan, leaf_id):
    lead = {"host_id": "fixture-host", "harness": "codex", "session_id": "lead"}
    pj.assign_leaf(plan, leaf_id, {"schema_version": 1, "attempt_id": "attempt",
        "executor_kind": "session", "lead": lead, "executor": {**lead, "session_id": "worker"},
        "parent": None, "state": "assigned"})
    pj.transition_leaf(plan, leaf_id, "attempt", "assigned", receipt={"observed_runtime": {
        "state": "idle", "source": "native_verified", "observed_at": datetime.now(timezone.utc).isoformat()}})
    return {"dispatch": {"request_id": "fixture-request", "status": "dispatching"}}

def test_atomic_admission_inherits_milestone_prerequisite(tmp_path, monkeypatch):
    plan = make_plan(tmp_path, monkeypatch, [
        {"id": "P"}, {"id": "M", "kind": "milestone", "depends_on": ["P"]},
        {"id": "C", "parent": "M"}])
    receipt = assign_idle(plan, "C")
    with pytest.raises(pj.LeafError, match="dependencies_unmet"):
        pj.admit_leaf(plan, "C", "attempt", receipt)
    assert json.loads((plan / "leaves/C.json").read_text())["assignment"]["state"] == "assigned"

def test_atomic_admission_uses_completed_children_of_milestone(tmp_path, monkeypatch):
    plan = make_plan(tmp_path, monkeypatch, [
        {"id": "M", "kind": "milestone"}, {"id": "C", "parent": "M", "status": "done"},
        {"id": "N", "depends_on": ["M"]}])
    receipt = assign_idle(plan, "N")
    accepted = pj.admit_leaf(plan, "N", "attempt", receipt)
    assert accepted["assignment"]["state"] == "dispatching"

@pytest.mark.parametrize("state,reason", [
    ("delivery_unknown", "delivery_unknown"), ("blocked", "codex_quota_guard"),
    ("running", "assignment_running")])
def test_public_show_names_execution_instead_of_an_unconditional_next(tmp_path, monkeypatch, state, reason):
    value = execution_leaf(state=state)
    if state == "running":
        value["assignment"]["observed_runtime"]["state"] = "running"
        value["assignment"]["wake"].update(state="waiting", reason=None)
    plan = make_plan(tmp_path, monkeypatch, [value])
    result = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_json.py"), "show", str(plan)],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "Next: L01" not in result.stdout
    assert "assignment=" + state in result.stdout
    assert reason in result.stdout
    assert "dispatchable none" in result.stdout

def test_show_prioritizes_pending_attempt_over_old_accepted_history(tmp_path, monkeypatch):
    rows = []
    for i in range(4):
        done = execution_leaf(state="accepted", status="done")
        done.update(id="A" + str(i))
        rows.append(done)
    pending = execution_leaf(state="delivery_unknown")
    pending.update(id="Z99")
    plan = make_plan(tmp_path, monkeypatch, rows + [pending])
    assert "Z99: assignment=delivery_unknown" in "\n".join(pj.plan_summary(plan))
