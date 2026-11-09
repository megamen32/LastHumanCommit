"""Unaccepted goals remain visible when the final implementation card closes."""
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_entry as entry
import lhc_plan_json as plans


def fixture_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    plan = tmp_path / "project/.agents/tasks/test"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"goal": "Deliver the working screen", "deliverable": "implementation"}))
    (plan / "leaves/F1.json").write_text(json.dumps({"id": "F1", "status": "done", "session": "lead"}))
    plans.record_session_plan("lead", plan, "F1")
    return plan, {"cwd": str(tmp_path / "project"), "session_id": "lead"}


def test_exhausted_bound_implementation_requires_useful_decision(tmp_path, monkeypatch):
    plan, event = fixture_plan(tmp_path, monkeypatch)
    reason = entry.stop_gate(event, ROOT)
    assert reason and "goal" in reason.lower() and "decision" in reason.lower()
    assert "research" in reason.lower() and "resume" in reason.lower()
    assert entry.stop_gate(event, ROOT) is None  # one reminder per exact frontier
    assert entry.stop_gate({**event, "stop_hook_active": True}, ROOT) is None


def test_unbound_finished_plan_is_not_reopened(tmp_path, monkeypatch):
    _plan, event = fixture_plan(tmp_path, monkeypatch)
    assert entry.stop_gate({**event, "session_id": "unrelated"}, ROOT) is None


import copy
import lhc_plan_control as control


def outcome_for(metadata, plan, complete=False):
    outcome = {"id": "goal", "task_class": "fullcycle", "contract_confirmed": True,
               "original_goal": metadata["goal"], "latest_correction": metadata["goal"],
               "finish_verdict": "complete" if complete else "pending",
               "canary": {"scenario": "Open screen", "target": "dev", "expected": "Useful result"},
               "stages": {key: {"status": "complete" if complete else "pending", "basis": "native evidence"}
                          for key in ("technical", "deploy", "consumer", "publication", "integration")}}
    outcome["plan_binding"] = control.binding(metadata, outcome, plan, accepted=complete)
    return outcome


def test_acceptance_is_bound_to_current_goal_and_evidence(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    accepted = outcome_for(metadata, plan, complete=True)
    assert control.evaluate(metadata, rows, accepted, plan_dir=plan)["goal_status"] == "accepted"
    assert control.evaluate(metadata, rows, accepted, plan_dir=tmp_path / "unrelated")["goal_status"] == "unknown"
    assert control.evaluate({**metadata, "goal": "A changed user goal"}, rows, accepted, plan_dir=plan)["goal_status"] == "unknown"
    changed = copy.deepcopy(accepted)
    changed["latest_correction"] = "Changed user correction"
    assert control.evaluate(metadata, rows, changed, plan_dir=plan)["goal_status"] == "unknown"
    changed = copy.deepcopy(accepted)
    changed["stages"]["consumer"]["basis"] = "different evidence"
    assert control.evaluate(metadata, rows, changed, plan_dir=plan)["goal_status"] != "accepted"
    changed = copy.deepcopy(accepted)
    del changed["stages"]["consumer"]
    changed["plan_binding"] = control.binding(metadata, changed, plan, accepted=True)
    assert control.evaluate(metadata, rows, changed, plan_dir=plan)["goal_status"] != "accepted"


def test_complete_status_outcome_cannot_accept_implementation_goal(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    status = outcome_for(metadata, plan, complete=True)
    status["task_class"] = "status"
    status["plan_binding"] = control.binding(metadata, status, plan, accepted=True)
    assert control.evaluate(metadata, rows, status, plan_dir=plan)["goal_status"] != "accepted"


def test_external_wait_needs_resume_and_preserves_stop(tmp_path, monkeypatch):
    plan, event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan)
    decision = {"decision": "wait_external", "evidence": "provider ticket 42",
                "action": "Wait for provider grant", "owner": "provider on-call",
                "uncertainty": "provider response time"}
    with pytest.raises(ValueError, match="resume_condition"):
        control.record_decision(metadata, rows, outcome, {}, plan, decision)
    decision["resume_condition"] = "ticket 42 grant becomes visible"
    control.record_decision(metadata, rows, outcome, {}, plan, decision)
    assert control.evaluate(metadata, rows, outcome, plan_dir=plan)["next_decision"] == "wait_external"
    monkeypatch.setattr(control, "read_context", lambda *args: (None, {}, outcome))
    assert entry.stop_gate(event, ROOT) is None
    assert "resume condition" in entry.plan_resume_context(event, ROOT)


def test_decision_becomes_stale_after_new_work_or_scope(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan)
    decision = {"decision": "need_fact", "evidence": "consumer result missing",
                "action": "Inspect exact consumer error within one bounded research leaf", "owner": "Lead",
                "uncertainty": "which route failed", "action_kind": "research"}
    control.record_decision(metadata, rows, outcome, {}, plan, decision)
    assert control.evaluate(metadata, rows, outcome, plan_dir=plan)["next_decision"] == "work"
    changed = [{**rows[0], "status": "blocked"}]
    assert control.evaluate(metadata, changed, outcome, plan_dir=plan)["next_decision"] == "required"
    assert not control.evaluate({**metadata, "goal": "Changed goal"}, rows, outcome, plan_dir=plan)["decision_fresh"]
    # A progress note does not change the semantic goal binding.
    assert control.plan_scope(metadata) == control.plan_scope({**metadata, "current_progress": "finished card"})


def test_unknown_admission_is_not_exhausted_or_replayable(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    unknown = [{**rows[0], "status": "queued", "assignment": {"state": "delivery_unknown"}}]
    view = control.evaluate(metadata, unknown, plan_dir=plan)
    assert view["frontier"] == "admission_unknown"
    assert view["next_decision"] == "none"


def test_human_stop_requires_existing_native_fact(tmp_path, monkeypatch):
    plan, event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan)
    decision = {"decision": "human_stop", "evidence": "actual native stop", "action": "Preserve stop",
                "owner": "human", "uncertainty": "none"}
    with pytest.raises(ValueError, match="existing observed"):
        control.record_decision(metadata, rows, outcome, {}, plan, decision)
    state = {"native_entry": {"finish_hold": "HumanStop"}}
    control.record_decision(metadata, rows, outcome, state, plan, decision)
    monkeypatch.setattr(control, "read_context", lambda *args: (None, state, outcome))
    assert entry.stop_gate(event, ROOT) is None


def test_explicit_replacement_is_separate_from_binding_change(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan)
    outcome["plan_binding"]["plan_dir"] = str(tmp_path / "replacement")
    assert control.evaluate(metadata, rows, outcome, plan_dir=plan)["goal_status"] == "unknown"
    outcome["plan_replacement"] = {"plan_dir": str(plan), "replacement_plan_dir": str(tmp_path / "replacement"),
                                   "source_ref": "explicit Lead replacement record",
                                   "outcome_id": outcome["id"], "plan_scope": control.plan_scope(metadata)}
    assert control.evaluate(metadata, rows, outcome, plan_dir=plan)["goal_status"] == "superseded"


def test_finished_plan_without_native_ref_has_explicit_unknown_projection(tmp_path, monkeypatch):
    plan, _event = fixture_plan(tmp_path, monkeypatch)
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unknown"
    assert view["reason"] == "native_lead_ref_missing"



def test_existing_native_outcome_cli_and_projection_use_same_decision(tmp_path, monkeypatch):
    import subprocess
    import lhc_time_guard as guard
    plan, event = fixture_plan(tmp_path, monkeypatch)
    leaf_path = plan / "leaves/F1.json"
    leaf = json.loads(leaf_path.read_text())
    leaf["harness"] = "codex"
    leaf_path.write_text(json.dumps(leaf))
    metadata, _rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan)
    outcome.pop("plan_binding")
    outcome["owner"] = {"harness": "codex", "session_id": "lead"}
    outcome["cwd"] = event["cwd"]
    path = guard.learning_path(Path(event["cwd"]), "codex", "lead")
    guard.write_state(path, {"business": {"outcome": outcome}})
    command = [sys.executable, str(ROOT / "src/common/tools/lhc_outcome.py"),
               "--cwd", event["cwd"], "--runtime", "codex", "--session-id", "lead"]
    bound = subprocess.run(command + ["bind-plan", "--plan-dir", str(plan)], capture_output=True, text=True)
    assert bound.returncode == 0, bound.stderr
    assert json.loads(bound.stdout)["binding"] == "bound"
    decided = subprocess.run(command + ["frontier", "--plan-dir", str(plan),
        "--decision", "wait_external", "--owner", "provider", "--evidence", "ticket 42",
        "--action", "wait for grant", "--uncertainty", "response time",
        "--resume-condition", "grant visible in ticket 42"], capture_output=True, text=True)
    assert decided.returncode == 0, decided.stderr
    view = control.resolve_control(plan)
    assert view["goal_status"] == "unaccepted" and view["next_decision"] == "wait_external"
    assert view["source"]["session_id"] == "lead"
    assert entry.stop_gate(event, ROOT) is None


def test_executor_is_not_implicitly_parent_goal_owner(tmp_path, monkeypatch):
    plan, event = fixture_plan(tmp_path, monkeypatch)
    path = plan / "leaves/F1.json"
    row = json.loads(path.read_text())
    row["assignment"] = {"lead": {"session_id": "actual-lead"}, "executor": {"session_id": "lead"}}
    path.write_text(json.dumps(row))
    assert entry.stop_gate(event, ROOT) is None
    assert control.bind_session_plan(plan, "lead", event["cwd"])["reason"] == "lead_ownership_missing"



def test_current_accepted_goal_releases_stop(tmp_path, monkeypatch):
    plan, event = fixture_plan(tmp_path, monkeypatch)
    metadata, rows = control.read_plan(plan)
    outcome = outcome_for(metadata, plan, complete=True)
    outcome["stages"]["integration"]["status"] = "not-applicable"
    outcome["plan_binding"] = control.binding(metadata, outcome, plan, accepted=True)
    monkeypatch.setattr(control, "read_context", lambda *args: (None, {}, outcome))
    assert entry.stop_gate(event, ROOT) is None
    assert "goal=accepted" in entry.plan_resume_context(event, ROOT)
