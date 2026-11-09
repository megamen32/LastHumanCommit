"""Current goal role is explicit, while historical executors remain history."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_plan_control as control
import lhc_plan_json as plans
import lhc_time_guard as guard

LEAD = {"host_id": "host100", "harness": "codex", "session_id": "current"}
OTHER = {"host_id": "host100", "harness": "codex", "session_id": "other"}
SOURCE = "records/I1/current-native-owner.md"


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    plan = tmp_path / ".agents/tasks/role"
    (plan / "leaves").mkdir(parents=True)
    metadata = {"goal": "Deliver usable native workflow", "deliverable": "implementation",
                "business_result": "The current executor and next step are clear",
                "acceptance_scenario": "Run the native workflow",
                "current_goal_lead": {**LEAD, "source_ref": SOURCE}}
    (plan / "plan.json").write_text(json.dumps(metadata))
    rows = [
        {"id": "F", "status": "done", "session": "unverified-old-root", "harness": "codex"},
        {"id": "H", "status": "done", "session": "historical-worker", "harness": "codex"},
        {"id": "Q", "status": "blocked", "session": "qa", "harness": "codex"},
        {"id": "I", "status": "running", "session": "current", "harness": "codex"},
    ]
    for row in rows:
        (plan / "leaves" / (row["id"] + ".json")).write_text(json.dumps(row))
    plans.record_session_plan("current", plan, "I")
    outcome = {"id": "current-outcome", "owner": {"harness": "codex", "session_id": "current"},
               "cwd": str(tmp_path), "original_goal": metadata["goal"],
               "latest_correction": metadata["goal"], "task_class": "fullcycle",
               "contract_confirmed": True, "finish_verdict": "pending",
               "canary": {"scenario": "Native workflow", "target": "dev", "expected": "clear executor", "status": "pending"},
               "stages": {key: {"status": "pending"} for key in
                          ("technical", "deploy", "consumer", "publication", "integration")}}
    outcome["plan_binding"] = control.binding(metadata, outcome, plan)
    path = guard.learning_path(tmp_path, "codex", "current")
    guard.write_state(path, {"business": {"outcome": outcome}})
    return plan, metadata, rows, path, outcome


def test_mixed_history_resolves_explicit_current_bound_native_lead(case):
    plan, metadata, rows, path, outcome = case
    before = {p.name: p.read_bytes() for p in (plan / "leaves").glob("*.json")}
    view = control.resolve_control(plan)
    assert view["reason"] == "bound_native_outcome", view
    assert view["goal_status"] == "unaccepted"  # pending stays pending
    assert view["source"]["session_id"] == "current"
    assert view["source"]["host_id"] == "host100"
    assert before == {p.name: p.read_bytes() for p in (plan / "leaves").glob("*.json")}
    assert guard.load_state(path)["business"]["outcome"] == outcome  # read has no native-state mutation


def test_handoff_uses_existing_public_update_plan_schema(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    result = plans.update_plan(plan, {"current_goal_lead": {**LEAD, "source_ref": SOURCE}},
                               {"reason": "Explicit delegated operational Lead handoff", "summary": "Preserve authors"})
    assert "current_goal_lead" in result["changed"]
    assert control.resolve_control(plan)["source"]["session_id"] == "current"


def test_two_current_typed_role_claims_remain_unknown(case):
    plan, metadata, rows, path, outcome = case
    conflict = {"id": "OTHER", "status": "running", "assignment":
                {"lead": OTHER, "executor": OTHER, "state": "running", "attempt_id": "attempt-other"}}
    (plan / "leaves/OTHER.json").write_text(json.dumps(conflict))
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "current_goal_lead_conflict"


def test_missing_current_native_outcome_is_not_replaced_by_old_accepted(case):
    plan, metadata, rows, path, outcome = case
    path.unlink()
    old = copy.deepcopy(outcome)
    old["id"] = "old"
    old["owner"]["session_id"] = "unverified-old-root"
    old["stages"] = {key: {"status": "not-applicable"} for key in old["stages"]}
    old["finish_verdict"] = "complete"
    old["plan_binding"] = control.binding(metadata, old, plan, accepted=True)
    guard.write_state(guard.learning_path(plan, "codex", "unverified-old-root"),
                      {"business": {"outcome": old}})
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "native_outcome_missing"


def test_ordinary_worker_activation_cannot_change_or_take_current_goal_role(case):
    plan, metadata, rows, path, outcome = case
    plans.record_session_plan("qa", plan, "Q")
    worker = copy.deepcopy(outcome)
    worker["id"], worker["owner"]["session_id"] = "qa-outcome", "qa"
    worker.pop("plan_binding")
    worker_path = guard.learning_path(plan, "codex", "qa")
    guard.write_state(worker_path, {"business": {"outcome": worker}})
    before = worker_path.read_bytes()
    result = control.bind_session_plan(plan, "qa", plan, runtime="codex")
    assert result == {"binding": "unknown", "reason": "current_goal_lead_mismatch"}
    assert worker_path.read_bytes() == before
    assert json.loads((plan / "plan.json").read_text())["current_goal_lead"] == metadata["current_goal_lead"]


def test_progress_does_not_change_goal_or_owner_resolution(case):
    plan, metadata, rows, path, outcome = case
    scope = control.plan_scope(metadata)
    metadata["current_progress"] = "Integration advances"
    metadata["updated_at"] = "2026-11-08T00:00:00Z"
    (plan / "plan.json").write_text(json.dumps(metadata))
    assert control.plan_scope(metadata) == scope
    assert control.resolve_control(plan)["goal_status"] == "unaccepted"


def test_legacy_mixed_refs_without_pointer_remain_unknown(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    assert control.resolve_control(plan)["reason"] == "native_lead_ref_ambiguous"


@pytest.mark.parametrize("pointer", [
    {"harness": "codex", "session_id": "current", "source_ref": SOURCE},
    {**LEAD, "source_ref": ""},
    {**LEAD, "source_ref": SOURCE, "acceptance": "PASS"},
])
def test_current_role_requires_exact_native_ref_and_auditable_source(case, pointer):
    plan, metadata, rows, path, outcome = case
    with pytest.raises(plans.LeafError, match="current_goal_lead"):
        plans.update_plan(plan, {"current_goal_lead": pointer})



def test_typed_current_lead_ignores_historical_completed_typed_lead(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    current = {"id": "T", "status": "running", "assignment": {
        "lead": LEAD, "executor": OTHER, "state": "running", "attempt_id": "current-attempt"}}
    historical = {"id": "OLD", "status": "done", "assignment": {
        "lead": OTHER, "executor": OTHER, "state": "accepted", "attempt_id": "old-attempt"}}
    for row in (current, historical):
        (plan / "leaves" / (row["id"] + ".json")).write_text(json.dumps(row))
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unaccepted"
    assert view["source"]["session_id"] == "current"


def test_same_session_on_conflicting_typed_host_does_not_match_pointer(case):
    plan, metadata, rows, path, outcome = case
    other_host = {**LEAD, "host_id": "host200"}
    row = {"id": "X", "status": "running", "assignment": {
        "lead": other_host, "executor": other_host, "state": "running", "attempt_id": "other-host"}}
    (plan / "leaves/X.json").write_text(json.dumps(row))
    assert control.resolve_control(plan)["reason"] == "current_goal_lead_conflict"
    assert control.bind_session_plan(plan, "current", plan, runtime="codex")["reason"] == "current_goal_lead_conflict"


def test_role_pointer_never_transfers_acceptance_to_new_owner(case):
    plan, metadata, rows, path, outcome = case
    outcome["stages"] = {key: {"status": "complete" if key != "integration" else "not-applicable"}
                         for key in outcome["stages"]}
    outcome["finish_verdict"] = "complete"
    outcome["plan_binding"] = control.binding(metadata, outcome, plan, accepted=True)
    guard.write_state(path, {"business": {"outcome": outcome}})
    assert control.resolve_control(plan)["goal_status"] == "accepted"
    changed = {**metadata, "current_goal_lead": {**OTHER, "source_ref": "records/next-handoff.md"}}
    assert control.evaluate(changed, rows, outcome, plan_dir=plan)["goal_status"] != "accepted"
    (plan / "plan.json").write_text(json.dumps(changed))
    assert control.resolve_control(plan)["goal_status"] == "unknown"


def test_role_change_requires_existing_revision_audit_path(case):
    plan, metadata, rows, path, outcome = case
    with pytest.raises(plans.LeafError, match="handoff requires an explicit revision"):
        plans.update_plan(plan, {"current_goal_lead": {**OTHER, "source_ref": "records/new-handoff.md"}})
    assert json.loads((plan / "plan.json").read_text())["current_goal_lead"] == metadata["current_goal_lead"]



def test_pointer_does_not_override_conflicting_recorded_native_host(case):
    plan, metadata, rows, path, outcome = case
    outcome["owner"]["host_id"] = "host200"
    guard.write_state(path, {"business": {"outcome": outcome}})
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "native_outcome_binding_stale"


def test_completed_last_assignment_preserves_unique_lead_without_pointer(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    last = rows[-1]
    last["status"] = "done"
    last["assignment"] = {
        "lead": LEAD, "executor": OTHER, "state": "accepted", "attempt_id": "finished-attempt",
    }
    (plan / "leaves/I.json").write_text(json.dumps(last))
    view = control.resolve_control(plan)
    assert view["reason"] == "bound_native_outcome", view
    assert view["source"]["session_id"] == "current"
    assert view["goal_status"] == "unaccepted"


def test_two_conflicting_finished_leads_stay_ambiguous_without_pointer(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    for leaf_id, lead in (("I", LEAD), ("OLD", OTHER)):
        row = {"id": leaf_id, "status": "done", "assignment": {
            "lead": lead, "executor": lead, "state": "accepted", "attempt_id": f"done-{leaf_id}",
        }}
        (plan / "leaves" / f"{leaf_id}.json").write_text(json.dumps(row))
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "native_lead_ref_ambiguous"


def test_invalid_finished_lead_is_not_treated_as_verified(case):
    plan, metadata, rows, path, outcome = case
    metadata.pop("current_goal_lead")
    (plan / "plan.json").write_text(json.dumps(metadata))
    row = {"id": "I", "status": "done", "assignment": {
        "lead": {"harness": "codex", "session_id": "current"},
        "executor": OTHER, "state": "accepted", "attempt_id": "done-invalid",
    }}
    (plan / "leaves/I.json").write_text(json.dumps(row))
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "native_lead_ref_unverified"
