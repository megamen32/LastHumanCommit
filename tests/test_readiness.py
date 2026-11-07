"""Regression scenarios for dependency candidates and actual dispatch admission."""
import importlib.util
import json
import sys

import pytest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
NOW = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)

def module(name):
    spec = importlib.util.spec_from_file_location("readiness_test_" + name, TOOLS / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value

def assignment(state="assigned", runtime="idle", at="2026-11-07T15:00:00Z", sid="worker"):
    return {"schema_version": 1, "attempt_id": "attempt", "state": state,
            "executor_kind": "session", "lead": {"host_id": "h", "harness": "codex", "session_id": "lead"},
            "executor": {"host_id": "h", "harness": "codex", "session_id": sid},
            "observed_runtime": {"state": runtime, "observed_at": at, "source": "herder"}}

def test_parallel_waiting_json_is_a_real_cli_answer(tmp_path):
    p = module("lhc_parallel")
    document = {"slots": 2, "tasks": [{"id": "A", "status": "queued"},
        {"id": "B", "status": "queued", "depends_on": ["A"]}]}
    result = p.to_dict(p.analyze(p.parse_graph_json(document)))
    assert result["waiting"][0]["waits_for"] == [{"id": "A", "label": "", "status": "queued"}]
    graph = tmp_path / "plan.graph.json"
    graph.write_text(json.dumps(document))
    import subprocess
    run = subprocess.run([sys.executable, str(TOOLS / "lhc_parallel.py"), str(graph), "--json"], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["waiting"][0]["id"] == "B"

def test_unassigned_is_a_candidate_without_a_dispatch_claim():
    r = module("lhc_readiness").evaluate([{"id": "A", "status": "queued"}], slots=2, now=NOW)
    assert r["ready"] == ["A"]
    assert r["dispatchable"] == []
    assert r["by_id"]["A"]["dependencies_satisfied"] is True
    assert r["by_id"]["A"]["dispatchable"] is None
    assert r["by_id"]["A"]["reason_code"] == "assignment_unknown"

def test_known_idle_executor_can_dispatch_but_unknown_or_stale_runtime_cannot():
    evaluate = module("lhc_readiness").evaluate
    for state, at, expected in [("idle", "2026-11-07T15:00:00Z", True),
                                ("unknown", "2026-11-07T15:00:00Z", None),
                                ("idle", "2026-11-07T14:00:00Z", None)]:
        r = evaluate([{"id": "A", "status": "queued", "assignment": assignment(runtime=state, at=at)}], slots=1, now=NOW)
        assert r["by_id"]["A"]["dispatchable"] is expected

def test_owner_busy_and_deferred_dependency_agree_in_every_consumer():
    p, g = module("lhc_parallel"), module("lhc_grid")
    for tasks, reason in [([{ "id": "A", "status": "running", "owner": "worker"},
                           {"id": "B", "status": "queued", "owner": "worker"}], "waiting_for_owner"),
                          ([{"id": "A", "status": "deferred"},
                            {"id": "B", "status": "queued", "depends_on": ["A"]}], "waiting_for_leaf")]:
        graph = g.parse_graph_json({"schema_version": 2, "slots": 3, "tasks": tasks})
        assert [t.id for t in p.analyze(p.parse_graph_json({"schema_version": 2, "slots": 3, "tasks": tasks})).ready] == []
        assert g.wait_reasons(graph)[reason] == ["B"]
        for answer in (g.plan_now(graph), g._plan_now_port(graph)):
            assert answer["ready"] == []
            assert answer["readiness"]["B"]["dispatchable"] is False

def test_one_native_executor_occupies_one_slot_even_if_owner_labels_differ():
    evaluate = module("lhc_readiness").evaluate
    r = evaluate([{"id": "A", "status": "running", "owner": "one", "assignment": assignment(state="running")},
                  {"id": "B", "status": "running", "owner": "two", "assignment": assignment(state="running")},
                  {"id": "C", "status": "queued"}], slots=2, now=NOW)
    assert r["occupied_slots"] == 1
    assert r["free_slots"] == 1
    assert r["ready"] == ["C"]

def test_slot_zero_is_not_unlimited():
    p, g = module("lhc_parallel"), module("lhc_grid")
    tasks = [{"id": "A", "status": "queued"}]
    assert p.analyze(p.parse_graph_json({"schema_version": 2, "slots": 0, "tasks": tasks})).ready == []
    for answer in (g.plan_now(g.parse_graph_json({"schema_version": 2, "slots": 0, "tasks": tasks})),
                   g._plan_now_port(g.parse_graph_json({"schema_version": 2, "slots": 0, "tasks": tasks}))):
        assert answer["ready"] == []
        assert answer["free_slots"] == 0

def test_external_waiting_unknown_dependencies_and_unsafe_replay_never_dispatch():
    evaluate = module("lhc_readiness").evaluate
    tasks = [{"id": "A", "status": "waiting"},
             {"id": "B", "status": "queued", "depends_on": ["missing"]},
             {"id": "C", "status": "mystery"}]
    for state in ("dispatching", "submitted", "running", "result_ready", "accepted", "blocked", "delivery_unknown", "cancelled"):
        tasks.append({"id": state, "status": "queued", "assignment": assignment(state=state)})
    result = evaluate(tasks, slots=20, now=NOW)
    assert not result["dispatchable"]
    assert result["by_id"]["A"]["reason_code"] == "external_waiting"
    assert result["by_id"]["B"]["unmet_ids"] == ["missing"]
    assert result["by_id"]["C"]["dispatchable"] is None
    assert result["by_id"]["delivery_unknown"]["reason_code"] == "delivery_unknown"

def test_quota_stop_and_wake_delivery_blockers_are_visible():
    evaluate = module("lhc_readiness").evaluate
    for state, wake in [("quota_guard", None), ("stopped", None), ("idle", {"state": "delivery_blocked", "reason_code": "quota_guard"})]:
        a = assignment(runtime=state)
        a["wake"] = wake
        r = evaluate([{"id": "A", "status": "queued", "assignment": a}], slots=1, now=NOW)["by_id"]["A"]
        assert r["dispatchable"] is False
        assert r["reason_code"] in {"quota_guard", "stopped", "wake_delivery_blocked"}


def test_explicit_assignment_reaches_parallel_grid_and_fallback():
    p, g = module("lhc_parallel"), module("lhc_grid")
    a = assignment(at=datetime.now(timezone.utc).isoformat())
    document = {"schema_version": 2, "slots": 1,
                "tasks": [{"id": "A", "status": "queued", "assignment": a}]}
    summary = p.analyze(p.parse_graph_json(document))
    assert [task.id for task in summary.dispatchable] == ["A"]
    graph = g.parse_graph_json(document)
    for answer in (g.plan_now(graph), g._plan_now_port(graph)):
        assert [row["id"] for row in answer["dispatchable"]] == ["A"]
        assert answer["readiness"]["A"]["reason_code"] == "dispatchable"


def test_two_queued_leaves_do_not_dispatch_to_the_same_executor_twice():
    evaluate = module("lhc_readiness").evaluate
    result = evaluate([{"id": "A", "status": "queued", "assignment": assignment()},
                       {"id": "B", "status": "queued", "assignment": assignment()}], slots=2, now=NOW)
    assert result["dispatchable"] == ["A"]
    assert result["waiting_for_owner"] == ["B"]


def test_unknown_candidate_does_not_reserve_the_only_dispatch_slot():
    evaluate = module("lhc_readiness").evaluate
    result = evaluate([{"id": "legacy", "status": "queued"},
                       {"id": "explicit", "status": "queued", "assignment": assignment()}], slots=1, now=NOW)
    assert result["dispatchable"] == ["explicit"]
    assert result["ready"] == ["explicit"]
    assert result["dependency_ready"] == ["legacy", "explicit"]


def test_blocked_assignment_preserves_specific_quota_reason():
    a = assignment(state="blocked", runtime="unknown")
    a["observed_runtime"]["reason_code"] = "quota_guard"
    r = module("lhc_readiness").evaluate([{"id": "A", "status": "queued", "assignment": a}], slots=1, now=NOW)
    assert r["by_id"]["A"]["reason_code"] == "quota_guard"
    assert r["by_id"]["A"]["dispatchable"] is False


def test_bridge_reason_strings_and_explicit_completion_control_capacity():
    evaluate = module("lhc_readiness").evaluate
    a = assignment(state="blocked")
    a["dispatch"] = {"reason": "codex_quota_guard"}
    assert evaluate([{"id": "A", "status": "queued", "assignment": a}], slots=1, now=NOW)["by_id"]["A"]["reason_code"] == "codex_quota_guard"


def test_explicit_completion_releases_saved_running_capacity_but_unknown_reserves():
    evaluate = module("lhc_readiness").evaluate
    for state, occupied in [("result_ready", 0), ("accepted", 0), ("cancelled", 0), ("assigned", 0),
                            ("running", 1), ("submitted", 1), ("dispatching", 1), ("delivery_unknown", 1)]:
        result = evaluate([{"id": "A", "status": "running", "assignment": assignment(state=state)},
                           {"id": "B", "status": "queued"}], slots=1, now=NOW)
        assert result["occupied_slots"] == occupied, state
        assert ("B" in result["ready"]) is (occupied == 0), state


def test_undecomposed_stage_is_visible_but_never_a_candidate():
    result = module("lhc_readiness").evaluate(
        [{"id": "M01", "kind": "milestone", "status": "queued"}], slots=1, now=NOW)
    row = result["by_id"]["M01"]
    assert row["reason_code"] == "stage_undecomposed"
    assert row["candidate"] is False and row["dispatchable"] is False
    assert result["ready"] == result["dispatchable"] == result["dependency_ready"] == []
    assert result["occupied_slots"] == 0 and result["free_slots"] == 1


def test_fresh_idle_assignment_cannot_make_an_undecomposed_stage_dispatchable():
    result = module("lhc_readiness").evaluate(
        [{"id": "M01", "kind": "milestone", "status": "queued", "assignment": assignment()}],
        slots=1, now=NOW)
    row = result["by_id"]["M01"]
    assert row["dispatchable"] is False and row["candidate"] is False
    assert row["reason_code"] == "stage_undecomposed"
    assert result["dispatchable"] == result["ready"] == []


@pytest.mark.parametrize("stage_state", [None, "assigned", "running", "delivery_unknown"])
def test_undecomposed_stage_does_not_reserve_capacity_or_owner_for_a_leaf(stage_state):
    stage = {"id": "M01", "kind": "milestone", "status": "queued", "owner": "worker"}
    if stage_state is not None:
        stage["assignment"] = assignment(state=stage_state)
    leaf = {"id": "L01", "status": "queued", "owner": "worker", "assignment": assignment()}
    result = module("lhc_readiness").evaluate([stage, leaf], slots=1, now=NOW)
    assert result["ready"] == result["dispatchable"] == ["L01"]
    assert result["dependency_ready"] == ["L01"]
    assert result["occupied_slots"] == 0 and result["free_slots"] == 1
    assert result["occupied_executor_keys"] == result["reserved_unknown"] == []
    assert result["by_id"]["M01"]["reason_code"] == "stage_undecomposed"
