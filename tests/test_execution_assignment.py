"""Execution identity is provenance, separate from historical declarations."""
import copy
import json
import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_plan_json as pj

LEAD = {"host_id": "test-host", "harness": "codex", "session_id": "test-lead"}
EXEC = {"host_id": "test-host", "harness": "codex", "session_id": "test-worker"}

@pytest.fixture
def plan(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "absent"))
    (tmp_path / "leaves").mkdir()
    (tmp_path / "plan.json").write_text(json.dumps({"title": "identity test"}))
    (tmp_path / "leaves/L01.json").write_text(json.dumps(
        {"id": "L01", "label": "test", "status": "queued", "session": "legacy-assignee", "harness": "codex"}))
    return tmp_path

def read(plan):
    return json.loads((plan / "leaves/L01.json").read_text())

def assignment(attempt="attempt-1"):
    return {"schema_version": 1, "attempt_id": attempt, "executor_kind": "subagent",
            "lead": LEAD, "executor": EXEC, "parent": LEAD, "state": "assigned"}

def test_events_never_borrow_assignee_and_preserve_old_history(plan, monkeypatch):
    old = {"at": "2026-01-01T00:00:00Z", "changes": {}, "session": "old-assignee", "harness": "codex"}
    leaf = read(plan)
    leaf["progress_events"] = [old]
    (plan / "leaves/L01.json").write_text(json.dumps(leaf))
    monkeypatch.setenv("CODEX_THREAD_ID", "11111111-1111-1111-1111-111111111111")
    pj.update_leaf(plan, "L01", {"note": "actual writer"})
    leaf = read(plan)
    assert leaf["session"] == "legacy-assignee"
    assert leaf["progress_events"][0] == old
    event = leaf["progress_events"][-1]
    assert event["actor"]["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert event["actor"]["source"] == "native_environment"
    assert event["session"] != "legacy-assignee"

def test_unknown_and_declared_actor_are_explicit(plan):
    pj.update_leaf(plan, "L01", {"note": "no caller"})
    assert read(plan)["progress_events"][-1]["actor"]["source"] == "unknown"
    pj.update_leaf(plan, "L01", {"note": "declared"}, actor={**LEAD, "source": "native_verified"})
    assert read(plan)["progress_events"][-1]["actor"]["source"] == "declared"

def test_assignment_and_lifecycle_roundtrip(plan):
    pj.assign_leaf(plan, "L01", assignment())
    leaf = read(plan)
    assert leaf["status"] == "queued"
    assert leaf["assignment"]["state"] == "assigned"
    assert pj.task_from_leaf(leaf, plan / "leaves/L01.json")["assignment"]["executor"] == EXEC
    pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                       receipt={"dispatch": {"request_id": "request-1", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "submitted",
                       receipt={"dispatch": {"request_id": "request-1", "status": "accepted", "turn_id": "turn-1"}})
    assert read(plan)["status"] == "queued"
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "running")
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "running",
                           receipt={"observed_runtime": {"state": "running", "turn_id": "other"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "running",
                       receipt={"observed_runtime": {"state": "running", "turn_id": "turn-1", "source": "test-native"}})
    assert read(plan)["assignment"]["state"] == "running"
    assert read(plan)["status"] == "queued"
    pj.transition_leaf(plan, "L01", "attempt-1", "result_ready",
                       receipt={"observed_runtime": {"state": "completed", "turn_id": "turn-1", "source": "test-native"}})
    assert read(plan)["status"] != "done"
    pj.transition_leaf(plan, "L01", "attempt-1", "accepted")
    assert read(plan)["status"] == "done"

def test_unknown_delivery_retries_once_and_history_survives(plan):
    pj.assign_leaf(plan, "L01", assignment())
    pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                       receipt={"dispatch": {"request_id": "request-1", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "delivery_unknown",
                       receipt={"dispatch": {"request_id": "request-1", "status": "unknown", "reason": "timeout"}})
    # ACTION_POLICY: exactly one guarded retry re-enters dispatching with the
    # same durable request id; the event history counts the budget forever.
    retry = pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                               receipt={"dispatch": {"request_id": "request-1", "status": "dispatching",
                                                     "retries": 1}})
    assert retry["assignment"]["dispatch"]["retries"] == 1
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                           receipt={"dispatch": {"request_id": "request-1", "status": "dispatching"}})
    with pytest.raises(ValueError):
        pj.assign_leaf(plan, "L01", assignment("attempt-2"))
    pj.transition_leaf(plan, "L01", "attempt-1", "cancelled",
                       receipt={"dispatch": {"request_id": "request-1", "status": "not_attempted", "reason": "confirmed no effect"}})
    completed = read(plan)["assignment"]
    pj.assign_leaf(plan, "L01", assignment("attempt-2"))
    leaf = read(plan)
    assert leaf["assignment_history"] == [completed]
    assert leaf["assignment"]["lead"] == LEAD
    assert leaf["assignment"].get("dispatch") is None

def test_assignment_bypass_and_mismatched_attempt_are_refused(plan):
    with pytest.raises(ValueError):
        pj.update_leaf(plan, "L01", {"assignment": assignment()})
    pj.assign_leaf(plan, "L01", assignment())
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "other", "blocked")
    with pytest.raises(ValueError):
        pj.assign_leaf(plan, "L01", {**assignment("attempt-2"), "lead": EXEC})

def test_worker_registration_is_not_native_start(plan, tmp_path, monkeypatch):
    tree = tmp_path / "tree"
    tree.mkdir()
    monkeypatch.setattr(pj, "_git", lambda *a, **k: type("Result", (), {"stdout": "test-branch\n"})())
    pj.worker_register(plan, "L01", "test-worker", "test-branch", str(tree))
    assert read(plan)["status"] == "queued"
    assert "assignment" not in read(plan)

def test_pure_assignment_validates_subagent_and_unknown_actor():
    import lhc_assignment as a
    with pytest.raises(ValueError):
        a.validate_assignment({**assignment(), "parent": None})
    assert a.resolve_actor(environ={})["source"] == "unknown"


def test_explicit_activation_preserves_assignment_without_claiming_runtime(plan, monkeypatch):
    import lhc_plan_mirror as mirror
    monkeypatch.setattr(mirror, "worktree_root", lambda p: plan)
    monkeypatch.setattr(pj, "check_activation", lambda *args: None)
    pj.assign_leaf(plan, "L01", assignment())
    result = mirror.activate(plan, "L01", session="test-lead", harness="codex", owner="lead",
                             config_path=plan / "absent")
    assert result["status"] == "assigned"
    assert read(plan)["status"] == "queued"
    assert read(plan)["assignment"]["state"] == "assigned"
    assert read(plan)["assignment"]["observed_runtime"] is None

def test_generic_done_cannot_skip_explicit_result_acceptance(plan):
    pj.assign_leaf(plan, "L01", assignment())
    with pytest.raises(ValueError):
        pj.update_leaf(plan, "L01", {"status": "done"})

def test_trusted_metadata_is_not_an_explicit_provenance_claim(plan):
    import lhc_assignment as a
    actor = a.resolve_actor(trusted_caller=LEAD)
    pj.update_leaf(plan, "L01", {"note": "metadata"}, actor=actor)
    assert read(plan)["progress_events"][-1]["actor"]["source"] == "mcp_metadata"

def test_turn_and_wake_identity_are_stable(plan):
    pj.assign_leaf(plan, "L01", assignment())
    pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                       receipt={"dispatch": {"request_id": "r", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "submitted",
                       receipt={"dispatch": {"request_id": "r", "status": "accepted", "turn_id": "t"}})
    before = read(plan)
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "running",
                           receipt={"dispatch": {"turn_id": "other"},
                                    "observed_runtime": {"state": "running", "turn_id": "other", "source": "native"}})
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "running",
                           receipt={"wake": {"wait_id": "w", "captured_turn_id": "other"},
                                    "observed_runtime": {"state": "running", "turn_id": "t", "source": "native"}})
    assert read(plan) == before


def test_blocked_delivery_cannot_be_reset_to_repeat_accepted_send(plan):
    pj.assign_leaf(plan, "L01", assignment())
    pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                       receipt={"dispatch": {"request_id": "r", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "submitted",
                       receipt={"dispatch": {"request_id": "r", "status": "accepted", "turn_id": "t"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "blocked")
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "assigned")


@pytest.mark.parametrize("outcome", ["failed", "cancelled", "interrupted"])
def test_terminal_native_outcome_is_result_ready_not_automatic_success(plan, outcome):
    pj.assign_leaf(plan, "L01", assignment())
    pj.transition_leaf(plan, "L01", "attempt-1", "dispatching",
                       receipt={"dispatch": {"request_id": "r", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "submitted",
                       receipt={"dispatch": {"request_id": "r", "status": "accepted"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "submitted",
                       receipt={"wake": {"state": "blocked", "reason": "native turn unknown"}})
    pj.transition_leaf(plan, "L01", "attempt-1", "result_ready",
                       receipt={"dispatch": {"turn_id": "t"},
                                "observed_runtime": {"state": outcome, "turn_id": "t", "source": "native"}})
    assert read(plan)["status"] == "queued"
    pj.transition_leaf(plan, "L01", "attempt-1", "result_ready",
                       receipt={"wake": {"state": "registered", "wait_id": "w", "captured_turn_id": "t"}})
    assert read(plan)["assignment"]["observed_runtime"]["state"] == outcome

def test_assignment_cas_rejects_stale_write(plan):
    import hashlib
    digest = hashlib.sha256((plan / "leaves/L01.json").read_bytes()).hexdigest()
    pj.assign_leaf(plan, "L01", assignment(), expected_hash=digest)
    with pytest.raises(ValueError):
        pj.transition_leaf(plan, "L01", "attempt-1", "blocked", expected_hash=digest)
    assert read(plan)["assignment"]["state"] == "assigned"


@pytest.mark.parametrize("execution_context", ["worker", "assignment"])
def test_generic_worker_progress_never_autobinds_the_actor_as_executor(plan, monkeypatch, execution_context):
    leaf = read(plan)
    leaf.pop("session", None)
    leaf.pop("harness", None)
    if execution_context == "worker":
        leaf["worker"] = {"id": "different-worker", "branch": "lhc/different-worker",
                          "worktree": str(plan / "different-worker")}
    else:
        leaf["assignment"] = assignment()
    (plan / "leaves/L01.json").write_text(json.dumps(leaf))
    actor = "11111111-1111-1111-1111-111111111111"
    monkeypatch.setenv("CODEX_THREAD_ID", actor)
    recorded = []
    monkeypatch.setattr(pj, "record_session_plan", lambda *args: recorded.append(args))
    pj.update_leaf(plan, "L01", {"status": "running", "note": "Lead records progress"})
    updated = read(plan)
    assert not updated.get("session")
    assert not updated.get("harness")
    assert updated["progress_events"][-1]["actor"]["session_id"] == actor
    assert not recorded

def test_generic_self_progress_keeps_legacy_environment_binding(plan, monkeypatch):
    leaf = read(plan)
    leaf.pop("session", None)
    leaf.pop("harness", None)
    (plan / "leaves/L01.json").write_text(json.dumps(leaf))
    actor = "11111111-1111-1111-1111-111111111111"
    monkeypatch.setenv("CODEX_THREAD_ID", actor)
    pj.update_leaf(plan, "L01", {"note": "Self work"})
    assert read(plan)["session"] == actor and read(plan)["harness"] == "codex"
