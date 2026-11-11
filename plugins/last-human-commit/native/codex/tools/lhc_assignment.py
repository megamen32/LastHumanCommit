"""Pure assignment lifecycle and provenance; no dispatch or filesystem effects."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import os
import re

STATES = ("assigned", "dispatching", "submitted", "running", "result_ready",
          "accepted", "blocked", "delivery_unknown", "cancelled")
REF_FIELDS = ("host_id", "harness", "session_id")
TERMINAL = {"accepted", "cancelled"}
ALLOWED = {
    "assigned": {"assigned", "dispatching", "blocked", "cancelled"},
    "dispatching": {"submitted", "running", "delivery_unknown", "blocked", "cancelled"},
    "submitted": {"submitted", "running", "result_ready", "blocked", "delivery_unknown", "cancelled"},
    "running": {"running", "result_ready", "blocked", "delivery_unknown", "cancelled"},
    "result_ready": {"result_ready", "accepted", "blocked", "cancelled"},
    "blocked": {"assigned", "dispatching", "running", "result_ready", "cancelled"},
    # ACTION_POLICY: an UNKNOWN delivery keeps recording fresh reads (self-loop)
    # and admits exactly one guarded re-dispatch under the immutable request_id.
    "delivery_unknown": {"delivery_unknown", "dispatching", "submitted", "running", "result_ready", "cancelled"},
    "accepted": set(), "cancelled": set(),
}

# The single guarded retry event counted from the immutable attempt history.
RETRY_EVENT = ("delivery_unknown", "dispatching")


def retryable_unknown(assignment):
    """ACTION_POLICY: one guarded re-dispatch of an UNKNOWN delivery is admissible.

    The retry reuses the attempt's immutable request id and the exact persisted
    payload; a confirmed turn belongs to reconciliation, never to a re-send.
    """
    if assignment.get("state") != "delivery_unknown":
        return False
    dispatch = assignment.get("dispatch")
    if not isinstance(dispatch, dict) or not dispatch.get("request_id") or dispatch.get("turn_id"):
        return False
    if int(dispatch.get("retries") or 0) >= 1:
        return False
    events = assignment.get("events")
    return not any(isinstance(event, dict) and (event.get("from"), event.get("to")) == RETRY_EVENT
                   for event in events or [])

class ActorRef(dict):
    """Request-local provenance marker, never reconstructed from JSON claims."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def validate_ref(value, *, allow_unknown=True):
    if not isinstance(value, dict) or set(value) - set(REF_FIELDS):
        raise ValueError("ref requires only host_id, harness, session_id")
    result = {}
    for key in REF_FIELDS:
        item = value.get(key)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            raise ValueError(f"ref.{key} must be a nonempty string or null")
        result[key] = item.strip() if isinstance(item, str) else None
    if not allow_unknown and not all(result.values()):
        raise ValueError("executor requires exact host_id, harness, session_id")
    return result

def validate_actor(value):
    if not isinstance(value, dict) or set(value) - set(REF_FIELDS) - {"source"}:
        raise ValueError("actor requires ref fields and source")
    result = validate_ref({k: value.get(k) for k in REF_FIELDS})
    source = value.get("source")
    if source not in {"unknown", "declared", "native_environment", "native_metadata", "mcp_metadata"}:
        raise ValueError("actor source must describe provenance")
    result["source"] = source
    return result

def resolve_actor(actor=None, *, trusted_caller=None, environ=None):
    """Explicit input is a declaration; only a trusted adapter may pass metadata."""
    if trusted_caller is not None:
        result = validate_ref({k: trusted_caller.get(k) for k in REF_FIELDS})
        return ActorRef({**result, "source": "mcp_metadata"})
    if isinstance(actor, ActorRef):
        return ActorRef(validate_actor(actor))
    if actor is not None:
        result = validate_ref({k: actor.get(k) for k in REF_FIELDS})
        return {**result, "source": "declared"}
    env = os.environ if environ is None else environ
    native = env.get("CODEX_THREAD_ID", "")
    if re.fullmatch(r"[0-9a-fA-F-]{36}", native):
        return ActorRef({"host_id": None, "harness": "codex", "session_id": native,
                         "source": "native_environment"})
    return {**dict.fromkeys(REF_FIELDS), "source": "unknown"}

def validate_assignment(value):
    if not isinstance(value, dict):
        raise ValueError("assignment must be an object")
    permitted = {"schema_version", "attempt_id", "executor_kind", "lead", "executor",
                 "parent", "state", "dispatch", "wake", "observed_runtime", "events"}
    if set(value) - permitted or value.get("schema_version") != 1:
        raise ValueError("assignment schema_version must be 1 with known fields")
    result = deepcopy(value)
    if not isinstance(result.get("attempt_id"), str) or not result["attempt_id"].strip():
        raise ValueError("assignment requires attempt_id")
    if result.get("executor_kind") not in {"self", "session", "subagent"}:
        raise ValueError("executor_kind must be self, session or subagent")
    for key in ("lead", "executor"):
        result[key] = validate_ref(result.get(key))
    parent = result.get("parent")
    if result["executor_kind"] == "subagent" and parent is None:
        raise ValueError("subagent requires parent ref")
    if parent is not None:
        result["parent"] = validate_ref(parent)
        if result["parent"] == result["executor"]:
            raise ValueError("subagent parent and executor must differ")
    else:
        result["parent"] = None
    if result.get("state") not in STATES:
        raise ValueError("unknown assignment state")
    for key in ("dispatch", "wake", "observed_runtime"):
        record = result.setdefault(key, None)
        if record is not None and not isinstance(record, dict):
            raise ValueError(f"assignment.{key} must be an object or null")
    events = result.setdefault("events", [])
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise ValueError("assignment.events must be a list of objects")
    return result

def new_attempt(assignment, *, previous=None, history=None, actor=None, at=None):
    """Return a fresh attempt; archives are managed by the atomic persistence owner."""
    item = validate_assignment(assignment)
    if item["state"] != "assigned" or item["events"] or any(
            item[k] is not None for k in ("dispatch", "wake", "observed_runtime")):
        raise ValueError("new attempt must be assigned with no reused receipts or history")
    known = list(history or [])
    if previous is not None:
        previous = validate_assignment(previous)
        if previous["state"] not in TERMINAL:
            raise ValueError("finish or reconcile the previous attempt before reassignment")
        if item["lead"] != previous["lead"]:
            raise ValueError("lead route is immutable across attempts")
        known.append(previous)
    if any(x.get("attempt_id") == item["attempt_id"] for x in known):
        raise ValueError("attempt_id cannot be reused")
    who = validate_actor(actor) if actor is not None else resolve_actor(environ={})
    item["events"] = [{"at": at or now(), "actor": who, "from": None, "to": "assigned"}]
    return item

def transition(current, state, *, attempt_id=None, receipt=None, actor=None, at=None):
    item = validate_assignment(current)
    if attempt_id is not None and attempt_id != item["attempt_id"]:
        raise ValueError("attempt_id mismatch; reread current assignment")
    if state not in STATES or state not in ALLOWED[item["state"]]:
        raise ValueError(f"cannot transition {item['state']} to {state}")
    receipt = deepcopy(receipt or {})
    if not isinstance(receipt, dict) or set(receipt) - {"dispatch", "wake", "observed_runtime", "result", "integration"}:
        raise ValueError("receipt accepts dispatch, wake, observed_runtime, result, integration")
    stamp = at or now()
    prior_dispatch = item.get("dispatch") or {}
    if any(key in receipt for key in ("result", "integration")):
        if state != "accepted":
            raise ValueError("result and integration are acceptance receipts")
        if "result" in receipt and (not isinstance(receipt["result"], str) or not receipt["result"].strip()):
            raise ValueError("acceptance result must be nonempty")
        if "integration" in receipt and not isinstance(receipt["integration"], dict):
            raise ValueError("integration receipt must be an object")
    for key, record in receipt.items():
        if key in {"result", "integration"}:
            continue
        if not isinstance(record, dict):
            raise ValueError(f"receipt.{key} must be an object")
        for identity in ("executor", "target"):
            if identity in record and validate_ref(record[identity]) != item["executor"]:
                raise ValueError("receipt executor mismatch")
        merged = {**(item.get(key) or {}), **record}
        merged.setdefault("observed_at", stamp)
        item[key] = merged
    dispatch = item.get("dispatch") or {}
    if prior_dispatch.get("handoff") is not None and dispatch.get("handoff") != prior_dispatch["handoff"]:
        raise ValueError("dispatch handoff identity cannot change within an attempt")
    runtime = item.get("observed_runtime") or {}
    if prior_dispatch.get("request_id") and dispatch.get("request_id") != prior_dispatch["request_id"]:
        raise ValueError("dispatch request_id cannot change within an attempt")
    if prior_dispatch.get("turn_id") and dispatch.get("turn_id") != prior_dispatch["turn_id"]:
        raise ValueError("confirmed native turn cannot change within an attempt")
    if state == "assigned" and prior_dispatch.get("status") not in {None, "not_attempted", "rejected"}:
        raise ValueError("accepted or unknown delivery cannot be reset for replay")
    if state == "dispatching":
        if current["state"] == "delivery_unknown":
            if not retryable_unknown(current):
                raise ValueError("one guarded retry per unknown delivery; reconcile or cancel the attempt")
        elif current["state"] == "blocked" and prior_dispatch.get("status") not in {None, "not_attempted", "rejected"}:
            raise ValueError("prior delivery must be reconciled before dispatch")
        validate_ref(item["executor"], allow_unknown=False)
        if not dispatch.get("request_id") or dispatch.get("status") != "dispatching":
            raise ValueError("dispatching requires durable request_id and dispatching intent")
    if state == "submitted" and (
            not dispatch.get("request_id") or dispatch.get("status") not in {"accepted", "submitted"}):
        raise ValueError("submitted requires accepted dispatch receipt")
    if state == "delivery_unknown" and not dispatch.get("request_id"):
        raise ValueError("unknown delivery must retain request_id")
    if state in {"running", "result_ready"}:
        wanted = {"running"} if state == "running" else {"completed", "complete", "done", "result_ready", "failed", "cancelled", "interrupted"}
        if runtime.get("state") not in wanted or not runtime.get("source") or not runtime.get("turn_id"):
            raise ValueError("native runtime receipt with exact turn and source required")
        if not dispatch.get("turn_id") or runtime["turn_id"] != dispatch["turn_id"]:
            raise ValueError("runtime turn does not match confirmed dispatch turn")
    wake = item.get("wake") or {}
    captured = wake.get("captured_turn_id", wake.get("turn_id"))
    if wake and (wake.get("wait_id") or wake.get("state") != "blocked") and (not captured or captured != dispatch.get("turn_id")):
        raise ValueError("wake must capture the confirmed native turn")
    if current["state"] == "delivery_unknown" and state == "cancelled" and dispatch.get("status") != "not_attempted":
        raise ValueError("unknown delivery cannot be discarded without confirmed no effect")
    if current["state"] == "delivery_unknown" and state == "submitted" and not dispatch.get("turn_id"):
        raise ValueError("unknown delivery reconciliation requires confirmed native turn")
    who = validate_actor(actor) if actor is not None else resolve_actor(environ={})
    item["events"].append({"at": stamp, "actor": who, "from": current["state"],
                           "to": state, "receipt": receipt})
    item["state"] = state
    return item
