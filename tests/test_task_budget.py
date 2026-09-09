"""Behavioral and real-process checks for JSON task-plan budgets."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


TOOL = Path(__file__).resolve().parents[1] / "src/common/tools/lhc_task_budget.py"
SPEC = importlib.util.spec_from_file_location("lhc_task_budget", TOOL)
budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)


def task(id, low=1, high=2, deps=None):
    return {"id": id, "min_minutes": low, "max_minutes": high, "deps": deps or []}


def test_fork_join_sums_effort_but_uses_longest_dependency_path():
    # Input deliberately not topologically sorted. Shared ancestors count once.
    result = budget.validate_plan({"tasks": [
        task("join", 2, 3, ["a", "b"]), task("b", 4, 5, ["root"]),
        task("root", 1, 2), task("a", 3, 8, ["root"]),
    ]})
    assert result["effort_minutes"] == {"minimum": 10, "maximum": 18}
    assert result["critical_path_minutes"] == {"minimum": 7, "maximum": 13}
    assert result["duration_minutes"] == {"minimum": 7, "maximum": 13}
    assert result["duration_kind"] == "dependency_lower_bound"
    assert result["capacity_accounted_for"] is False
    assert "not an upper bound" in result["explanation"]


def test_serial_plan_accounts_for_all_work_even_without_dependency_edges():
    result = budget.validate_plan({"serial": True, "tasks": [task("a", 2, 5), task("b", 3, 4)]})
    assert result["critical_path_minutes"] == {"minimum": 3, "maximum": 5}
    assert result["duration_minutes"] == {"minimum": 5, "maximum": 9}
    assert result["duration_kind"] == "serial_estimate"
    assert result["capacity_accounted_for"] is True


def test_decimal_minutes_and_inclusive_thirty_minute_limit():
    result = budget.validate_plan({"tasks": [task("a", 0.5, 30)]})
    assert result["effort_minutes"] == {"minimum": 0.5, "maximum": 30}


def test_thirty_minute_cap_is_per_leaf_not_whole_plan():
    result = budget.validate_plan({"tasks": [
        task("build", 20, 30), task("review", 20, 30, ["build"]),
        task("accept", 20, 30, ["review"]),
    ]})
    assert result["effort_minutes"] == {"minimum": 60, "maximum": 90}
    assert result["critical_path_minutes"] == {"minimum": 60, "maximum": 90}


def test_serial_flag_does_not_bypass_cycle_validation():
    with pytest.raises(ValueError, match="cycle"):
        budget.validate_plan({"serial": True, "tasks": [task("a", deps=["a"])]})


@pytest.mark.parametrize("low,high", [
    (0, 1), (-1, 1), (3, 2), (1, 30.01), (31, 31),
    (True, 2), (1, False), ("1", 2), (None, 2),
    (float("nan"), 2), (1, float("inf")), (1, 10**400),
])
def test_invalid_estimates_rejected(low, high):
    with pytest.raises(ValueError, match="minutes"):
        budget.validate_plan({"tasks": [task("bad", low, high)]})


@pytest.mark.parametrize("plan,reason", [
    ([], "object"), ({}, "tasks"), ({"tasks": []}, "tasks"),
    ({"tasks": {}}, "tasks"), ({"tasks": [None]}, "object"),
    ({"tasks": [task("")]}, "id"), ({"tasks": [task(1)]}, "id"),
    ({"tasks": [task("a"), task("a")]}, "duplicate"),
    ({"tasks": [task("a", deps=["missing"])]}, "unknown"),
    ({"tasks": [task("a", deps=["a"])]}, "cycle"),
    ({"tasks": [task("ok"), task("a", deps=["b"]), task("b", deps=["a"])]}, "cycle"),
    ({"tasks": [{**task("a"), "deps": "b"}]}, "deps"),
    ({"tasks": [{**task("a"), "deps": [None]}]}, "deps"),
    ({"tasks": [task("a"), task("b", deps=["a", "a"])]}, "duplicate"),
    ({"tasks": [{"id": "a", "max_minutes": 2}]}, "minutes"),
    ({"serial": "false", "tasks": [task("a")]}, "serial"),
])
def test_invalid_plan_rejected(plan, reason):
    with pytest.raises(ValueError, match=reason):
        budget.validate_plan(plan)


def run_cli(payload, *args):
    return subprocess.run([sys.executable, "-B", str(TOOL), *args],
                          input=payload, text=True, capture_output=True, timeout=10)


def test_real_cli_stdin():
    completed = run_cli(json.dumps({"tasks": [task("build", 10, 20), task("verify", 5, 10, ["build"])]}))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["effort_minutes"] == {"minimum": 15, "maximum": 30}
    assert completed.stderr == ""


def test_real_cli_file(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"serial": True, "tasks": [task("a"), task("b")]}))
    completed = run_cli(None, str(path))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["duration_minutes"] == {"minimum": 2, "maximum": 4}


@pytest.mark.parametrize("payload", ["{", "null", '{"tasks":[]}',
    json.dumps({"tasks": [task("too-long", 1, 31)]}),
    '{"tasks":[{"id":"a","min_minutes":NaN,"max_minutes":2}]}',
])
def test_real_cli_invalid_input_is_json_and_nonzero(payload):
    completed = run_cli(payload, "-")
    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["valid"] is False and result["error"]
    assert "Traceback" not in completed.stderr


def test_real_cli_missing_file(tmp_path):
    completed = run_cli(None, str(tmp_path / "missing.json"))
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["valid"] is False
