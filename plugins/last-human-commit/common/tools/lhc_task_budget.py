#!/usr/bin/env python3
"""Validate a leaf-task JSON plan and calculate its whole-plan budget.

Usage: python3 lhc_task_budget.py [PLAN.json|-] (default: stdin).
Input: {"serial": false, "tasks": [
    {"id": "build", "min_minutes": 5, "max_minutes": 20, "deps": []},
    {"id": "test", "min_minutes": 2, "max_minutes": 5, "deps": ["build"]}
]}
Each task has finite numeric 0 < min_minutes <= max_minutes. Estimates above
30 minutes are flagged for further decomposition, not rejected as invalid tasks.
Thirty minutes is planning granularity, never an actual execution timeout.
All execution, integration, review and testing work must be included as leaves
by the caller. Optional metadata (e.g. role) does not affect the calculation.
Dependencies may reference tasks later in the list; deps defaults to [].

Effort sums every leaf. The dependency critical path is computed separately for
minimum and maximum estimates, which may have different longest paths. Both
are lower bounds for their respective duration scenarios, excluding capacity
and external waits. Even the maximum-estimate path is NOT a delivery upper
bound. No resource scheduling is performed. Only an explicitly serial plan
uses summed effort as duration, assuming continuous execution without waits.

Stdout is JSON: exit 0 for a valid plan, exit 1 for invalid JSON/plan or read
failure. Argument-usage errors follow argparse (stderr, exit 2).
"""

from __future__ import annotations

import argparse
from collections import deque
import json
import math
from pathlib import Path
import sys


def validate_plan(plan: object) -> dict:
    """Return arithmetic and its proof boundary; raise ValueError on bad plans."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a nonempty list of leaf objects")
    serial = plan.get("serial", False)
    if type(serial) is not bool:
        raise ValueError("serial must be a boolean")

    by_id = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] must be an object")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f"tasks[{index}].id must be a nonempty string")
        if task_id in by_id:
            raise ValueError(f"duplicate task id: {task_id}")
        low, high = task.get("min_minutes"), task.get("max_minutes")
        for field, value in (("min_minutes", low), ("max_minutes", high)):
            try:
                valid = type(value) in (int, float) and value > 0 and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{task_id}.{field} must be finite positive minutes")
        if low > high:
            raise ValueError(f"{task_id}: min_minutes must be <= max_minutes")
        deps = task.get("deps", [])
        if not isinstance(deps, list) or any(
            not isinstance(dep, str) or not dep.strip() for dep in deps
        ):
            raise ValueError(f"{task_id}.deps must be a list of nonempty task ids")
        if len(set(deps)) != len(deps):
            raise ValueError(f"{task_id}.deps contains duplicate dependencies")
        by_id[task_id] = (low, high, deps)

    successors = {task_id: [] for task_id in by_id}
    remaining = {}
    for task_id, (_, _, deps) in by_id.items():
        remaining[task_id] = len(deps)
        for dep in deps:
            if dep not in by_id:
                raise ValueError(f"{task_id}: unknown dependency {dep}")
            successors[dep].append(task_id)

    ready = deque(task_id for task_id in by_id if remaining[task_id] == 0)
    finish_min, finish_max = {}, {}
    while ready:
        task_id = ready.popleft()
        low, high, deps = by_id[task_id]
        finish_min[task_id] = low + max((finish_min[d] for d in deps), default=0)
        finish_max[task_id] = high + max((finish_max[d] for d in deps), default=0)
        for successor in successors[task_id]:
            remaining[successor] -= 1
            if remaining[successor] == 0:
                ready.append(successor)
    if len(finish_min) != len(by_id):
        raise ValueError("dependency cycle detected")

    effort = {"minimum": sum(t[0] for t in by_id.values()),
              "maximum": sum(t[1] for t in by_id.values())}
    critical_path = {"minimum": max(finish_min.values()),
                     "maximum": max(finish_max.values())}
    return {
        "valid": True,
        "task_count": len(tasks),
        "decomposition_target_minutes": 30,
        "needs_decomposition": [task_id for task_id, (_, high, _) in by_id.items() if high > 30],
        "runtime_limit_minutes": None,
        "serial": serial,
        "effort_minutes": effort,
        "critical_path_minutes": critical_path,
        "critical_path_kind": "dependency_lower_bound_excluding_capacity",
        "duration_minutes": dict(effort if serial else critical_path),
        "duration_kind": "serial_estimate" if serial else "dependency_lower_bound",
        "capacity_accounted_for": serial,
        "explanation": (
            "Dependency critical-path minimum/maximum are lower bounds for their "
            "respective estimate scenarios, excluding capacity; maximum is not an "
            "upper bound on delivery time. "
            + ("Serial duration sums all effort, assuming continuous execution without external waits."
               if serial else "Duration repeats these dependency-only bounds; resource scheduling and external waits are excluded.")
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", nargs="?", default="-", help="JSON file, or - for stdin")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.plan == "-" else Path(args.plan).read_text(encoding="utf-8")
        result = validate_plan(json.loads(raw))
    except (ValueError, OSError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, allow_nan=False))
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
