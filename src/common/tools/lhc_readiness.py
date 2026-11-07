#!/usr/bin/env python3
"""Pure plan readiness. Dependency candidates never prove runtime availability.

No I/O, dispatch, state mutation, or implicit assignment migration happens here.
Callers can pass ``now`` to evaluate a saved snapshot reproducibly. Runtime
observations expire after five minutes; absence is unknown, never permission.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

RUNTIME_MAX_AGE_SECONDS = 300
_STATUSES = {"queued", "running", "done", "deferred", "blocked", "waiting"}
_IN_FLIGHT = {"dispatching", "submitted", "running"}


def _get(task: Any, key: str, default: Any = None) -> Any:
    return task.get(key, default) if isinstance(task, Mapping) else getattr(task, key, default)


def _assignment(task: Any) -> dict:
    value = _get(task, "assignment")
    return value if isinstance(value, dict) else {}


def executor_key(task: Any) -> str:
    """Prefer the actual executor ref, never its lead/parent route.

    Legacy owners are only capacity hints, not verified runtime identities.
    Distinct anonymous leaves consume distinct planned slots.
    """
    ref = _assignment(task).get("executor") or {}
    if isinstance(ref, dict) and ref.get("session_id") and ref.get("harness"):
        return "native:" + json.dumps([ref.get("host_id"), ref["harness"], ref["session_id"]], separators=(",", ":"))
    owner = str(_get(task, "owner") or "").strip().lower()
    if owner:
        return "owner:" + owner
    session = str(_get(task, "session") or "").strip()
    if session:
        return "legacy:" + json.dumps([_get(task, "harness", ""), session], separators=(",", ":"))
    return "leaf:" + str(_get(task, "id"))


def _time(value: Any) -> float | None:
    if isinstance(value, datetime):
        return value.timestamp() if value.tzinfo else None
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.timestamp() if parsed.tzinfo else None
        except ValueError:
            pass
    return None


def _execution_gate(task: Any, now: float, max_age: float) -> tuple[bool | None, str]:
    assignment = _assignment(task)
    if not assignment:
        return None, "assignment_unknown"
    state = assignment.get("state")
    if state == "delivery_unknown":
        return None, "delivery_unknown"
    if state not in {"assigned", "dispatching", "submitted", "running", "result_ready", "accepted", "blocked", "cancelled"}:
        return None, "assignment_unknown"
    if state == "blocked":
        for field in ("observed_runtime", "dispatch", "wake"):
            detail = assignment.get(field)
            if isinstance(detail, dict) and detail.get("reason_code"):
                return False, str(detail["reason_code"])
        return False, "assignment_blocked"
    if state != "assigned":
        return False, "assignment_" + str(state)
    runtime = assignment.get("observed_runtime") or {}
    runtime = runtime if isinstance(runtime, dict) else {}
    wake = assignment.get("wake") or {}
    if isinstance(wake, dict) and wake.get("state") in {"delivery_blocked", "blocked", "stopped", "cancelled"}:
        return False, "wake_" + str(wake["state"])
    runtime_state = str(runtime.get("state") or "unknown")
    reason = str(runtime.get("reason_code") or "")
    if runtime_state in {"quota_guard", "quota_blocked", "stopped", "stop", "stopping", "blocked", "unavailable", "running", "busy"}:
        return False, reason or runtime_state
    if reason in {"quota_guard", "owner_stop", "stop", "permission_denied"}:
        return False, reason
    ref = assignment.get("executor") or {}
    if not isinstance(ref, dict) or not all(ref.get(k) for k in ("host_id", "harness", "session_id")):
        return None, "executor_unknown"
    observed = _time(runtime.get("observed_at"))
    if observed is None or not runtime.get("source"):
        return None, "runtime_unknown"
    age = now - observed
    if age < -5 or age > max_age:
        return None, "runtime_stale"
    if runtime_state not in {"idle", "ready"}:
        return None, "runtime_unknown"
    return True, "dispatchable"


def evaluate(tasks: Any, slots: int | None = None, *, now: Any = None,
             runtime_max_age: float = RUNTIME_MAX_AGE_SECONDS) -> dict[str, Any]:
    """Return dependency readiness, legacy candidates, and dispatch admission.

    ``ready`` preserves the legacy candidate list, subject to owner/capacity.
    Only ``dispatchable`` has an explicit target plus fresh idle runtime.
    A None dispatchability means evidence is missing or delivery is ambiguous.
    Deferred prerequisites remain unmet. Waiting is an external recorded state.
    """
    rows = list(tasks)
    by_task = {str(_get(task, "id")): task for task in rows}
    current = _time(now) if now is not None else datetime.now(timezone.utc).timestamp()
    if current is None:
        raise ValueError("now must include a timezone or be epoch seconds")
    if slots is not None and (not isinstance(slots, int) or isinstance(slots, bool) or slots < 0):
        raise ValueError("slots must be a nonnegative integer or None")
    busy = {executor_key(task) for task in rows
            if _get(task, "status", "queued") == "running" or _assignment(task).get("state") in _IN_FLIGHT}
    free = None if slots is None else max(0, slots - len(busy))
    remaining = free
    allocated: set[str] = set()
    depths: dict[str, int] = {}

    def depth(task_id: str, active: frozenset[str] = frozenset()) -> int:
        if task_id in depths:
            return depths[task_id]
        if task_id in active or task_id not in by_task:
            return 0
        deps = _get(by_task[task_id], "depends_on", []) or []
        value = max((depth(str(dep), active | {task_id}) + 1 for dep in deps), default=0)
        depths[task_id] = value
        return value

    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (_get(pair[1], "wave") if _get(pair[1], "wave") is not None
                                  else depth(str(_get(pair[1], "id"))), _get(pair[1], "order", pair[0])))
    dependency_order = {str(_get(task, "id")): index for index, (_, task) in enumerate(indexed)}
    # Unknown legacy candidates cannot reserve a real slot ahead of a known idle target.
    # Stable sorting preserves wave/order within both evidence groups.
    indexed.sort(key=lambda pair: _execution_gate(pair[1], current, runtime_max_age)[0] is not True)
    result: dict[str, Any] = {name: [] for name in ("dependency_ready", "ready", "dispatchable", "deferred",
        "waiting_for_leaf", "waiting_for_owner", "external_waiting", "unknown")}
    result.update(by_id={}, occupied_slots=len(busy), free_slots=free)
    for _, task in indexed:
        task_id = str(_get(task, "id"))
        status = _get(task, "status", "queued")
        unmet = [str(dep) for dep in (_get(task, "depends_on", []) or [])
                 if str(dep) not in by_task or _get(by_task[str(dep)], "status", "queued") != "done"]
        key = executor_key(task)
        row = {"dependencies_satisfied": not unmet, "unmet_ids": unmet,
               "executor_key": key, "candidate": False, "dispatchable": False, "reason_code": "not_queued"}
        result["by_id"][task_id] = row
        if status not in _STATUSES:
            row.update(dispatchable=None, reason_code="status_unknown")
            result["unknown"].append(task_id)
            continue
        if status in {"blocked", "waiting"}:
            row["reason_code"] = "external_" + status
            result["external_waiting"].append(task_id)
            continue
        if status != "queued":
            continue
        if unmet:
            row["reason_code"] = "dependencies_unmet"
            result["waiting_for_leaf"].append(task_id)
            continue
        result["dependency_ready"].append(task_id)
        admission, reason = _execution_gate(task, current, runtime_max_age)
        # Ambiguous dispatch outcomes must remain visible and must not be replayed.
        if reason == "delivery_unknown":
            row.update(dispatchable=None, reason_code=reason)
            result["unknown"].append(task_id)
            continue
        if admission is False:
            row["reason_code"] = reason
            result["external_waiting"].append(task_id)
            continue
        if key in busy or key in allocated:
            row["reason_code"] = "owner_busy"
            result["waiting_for_owner"].append(task_id)
            continue
        if remaining == 0:
            row["reason_code"] = "capacity_full"
            result["deferred"].append(task_id)
            continue
        row.update(candidate=True, dispatchable=admission, reason_code=reason)
        result["ready"].append(task_id)
        allocated.add(key)
        if remaining is not None:
            remaining -= 1
        if admission:
            result["dispatchable"].append(task_id)
        else:
            result["unknown"].append(task_id)
    result["dependency_ready"].sort(key=dependency_order.__getitem__)
    return result
