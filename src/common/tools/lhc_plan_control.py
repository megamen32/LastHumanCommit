#!/usr/bin/env python3
"""Plan goal and frontier facts. No semantic classification, scheduler or transport.

evaluate is pure. The small explicit binding/read helpers reuse native outcome
state; no plan-level goal ledger or implicit acceptance is created.
"""
from __future__ import annotations
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path

DECISIONS = ("continue", "need_fact", "wait_external", "human_stop")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def plan_scope(metadata):
    # Ordinary progress, ordering, timestamps and generated projections are not scope.
    scenarios = list(metadata.get("acceptance_scenarios") or [])
    one = metadata.get("acceptance_scenario")
    if one:
        scenarios = [one] + [item for item in scenarios if item != one]
    return digest({**{key: metadata.get(key) for key in
                     ("goal", "deliverable", "business_result", "business_results",
                      "acceptance", "scope", "constraints")},
                   "acceptance_scenarios": scenarios})


def outcome_scope(outcome):
    canary = outcome.get("canary") or {}
    return digest({**{key: outcome.get(key) for key in
                      ("id", "original_goal", "latest_correction", "corrections", "task_class", "owned_paths")},
                   "canary": {key: canary.get(key) for key in ("scenario", "target", "expected")},
                   "stage_contracts": outcome.get("stage_contracts")})


def evidence_fingerprint(outcome):
    return digest({key: outcome.get(key) for key in
                   ("id", "revision", "stages", "stage_fingerprints", "product_verdict",
                    "canary", "integration_policy", "evidence_after")})


def _binding_matches(metadata, outcome, plan_dir):
    binding = outcome.get("plan_binding") or {}
    return bool(plan_dir and binding.get("plan_dir") == str(plan_dir)
                and binding.get("outcome_id") == outcome.get("id")
                and binding.get("plan_scope") == plan_scope(metadata)
                and binding.get("outcome_scope") == outcome_scope(outcome))


def _human_hold(state, rows):
    hold = (state.get("native_entry") or {}).get("finish_hold")
    if hold in {"HumanStop", "human_stop", "permission_declined", "codex_quota_guard"}:
        return True
    for row in rows:
        assignment = row.get("assignment") or {}
        observed = assignment.get("observed_runtime") or {}
        dispatch = assignment.get("dispatch") or {}
        if (observed.get("source") == "native_verified" and observed.get("state") == "stopped"):
            return True
        if dispatch.get("reason") in {"human_stop", "permission_declined", "codex_quota_guard"}:
            return True
    return False


def evaluate(metadata, rows, outcome=None, state=None, readiness=None, *, plan_dir=None):
    """Return goal_status/frontier/next_decision and a decision freshness digest.

    Only a matching explicit native-outcome binding with a current verified
    acceptance fingerprint can accept the goal. Counts never accept it.
    """
    metadata, outcome, state = metadata or {}, outcome or {}, state or {}
    rows = [dict(row) for row in rows if isinstance(row, dict)]
    if readiness is None:
        import lhc_readiness
        readiness = lhc_readiness.evaluate(rows, slots=metadata.get("slots"))
    binding_matches = _binding_matches(metadata, outcome, plan_dir)
    stages = outcome.get("stages") or {}
    accepted = bool(binding_matches and not (outcome.get("plan_binding") or {}).get("contract_required")
                    and outcome.get("task_class") not in {None, "status"}
                    and outcome.get("contract_confirmed")
                    and all(key in stages for key in ("technical", "deploy", "consumer", "publication", "integration"))
                    and all(isinstance(stage, dict) and stage.get("status") in
                            {"complete", "not-applicable"} for stage in stages.values())
                    and outcome.get("finish_verdict") == "complete"
                    and not outcome.get("blockers")
                    and (outcome.get("plan_binding") or {}).get("acceptance_fingerprint") ==
                    evidence_fingerprint(outcome))
    replacement = outcome.get("plan_replacement") or {}
    superseded = bool(plan_dir and replacement.get("plan_dir") == str(plan_dir)
                      and replacement.get("replacement_plan_dir") not in {None, str(plan_dir)}
                      and replacement.get("source_ref") and replacement.get("plan_scope") == plan_scope(metadata)
                      and replacement.get("outcome_id") == outcome.get("id"))
    goal = "superseded" if superseded else "accepted" if accepted else "unaccepted" if binding_matches else "unknown"
    active = any(row.get("status") == "running" or
                 (row.get("assignment") or {}).get("state") in {"dispatching", "submitted", "running", "result_ready"}
                 for row in rows)
    candidates = list(readiness.get("dependency_ready") or [])
    ambiguous = bool(readiness.get("reserved_unknown") or readiness.get("unknown"))
    frontier = ("active" if active else "admission_unknown" if ambiguous else
                "admission_blocked" if candidates and not readiness.get("ready") else
                "runnable" if candidates else "exhausted")
    fingerprint = digest([plan_scope(metadata), str(plan_dir) if plan_dir else None,
                          outcome_scope(outcome), evidence_fingerprint(outcome),
                          [(row.get("id"), row.get("status"), row.get("depends_on"),
                            row.get("supersedes"), row.get("assignment")) for row in rows]])
    decision = outcome.get("frontier_decision") or {}
    fresh = bool(binding_matches and decision.get("fingerprint") == fingerprint
                 and decision.get("plan_dir") == str(plan_dir)
                 and all(isinstance(decision.get(k), str) and decision[k].strip()
                         for k in ("decision", "evidence", "action", "owner", "uncertainty")))
    next_decision = "none"
    if _human_hold(state, rows):
        next_decision = "human_stop"
    elif goal not in {"accepted", "superseded"} and frontier == "exhausted":
        if fresh and decision.get("decision") == "wait_external" and decision.get("resume_condition"):
            next_decision = "wait_external"
        elif fresh and decision.get("decision") in {"continue", "need_fact"}:
            next_decision = "work"
        else:
            next_decision = "required"
    return {"goal_status": goal, "frontier": frontier, "next_decision": next_decision,
            "fingerprint": fingerprint, "decision_fresh": fresh, "candidates": candidates,
            "decision": copy.deepcopy(decision) if fresh else None}


def read_plan(plan_dir):
    plan = Path(plan_dir).resolve()
    metadata = json.loads((plan / "plan.json").read_text())
    rows = [json.loads(path.read_text()) for path in sorted((plan / "leaves").glob("*.json"))]
    if not isinstance(metadata, dict) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("plan metadata and leaves must be objects")
    # Container milestones with real children are not executable leaves.
    parents = {row.get("parent") for row in rows if row.get("parent")}
    rows = [row for row in rows if row.get("id") not in parents]
    return metadata, rows


def read_context(plan_dir, session, cwd, runtime=None):
    """Read existing native state only; ambiguous/missing ownership stays unknown."""
    import lhc_time_guard as guard
    contexts = []
    for candidate in ([runtime] if runtime else ("codex", "opencode", "zcode", "claude")):
        path = guard.learning_path(Path(cwd).resolve(), candidate, session)
        if not path.is_file():
            continue
        state = guard.load_state(path) or {}
        outcome = (state.get("business") or {}).get("outcome") or {}
        owner = outcome.get("owner") or {}
        if owner.get("session_id") == session and owner.get("harness") == candidate:
            contexts.append((path, state, outcome))
    return contexts[0] if len(contexts) == 1 else (None, {}, {})


def binding(metadata, outcome, plan_dir, *, accepted=False):
    value = {"plan_dir": str(plan_dir), "plan_scope": plan_scope(metadata),
             "outcome_scope": outcome_scope(outcome), "outcome_id": outcome.get("id")}
    if accepted:
        value["acceptance_fingerprint"] = evidence_fingerprint(outcome)
    return value


def bind_session_plan(plan_dir, session_id, cwd, runtime=None):
    """Called by explicit activation. Never create a clock or classify a goal."""
    import fcntl
    import lhc_plan_json as plans
    import lhc_time_guard as guard
    import lhc_outcome
    plan = Path(plan_dir).resolve()
    if str(plan) not in [str(Path(p).resolve()) for p in plans.session_plans(session_id)]:
        return {"binding": "unknown", "reason": "session_plan_binding_missing"}
    metadata, rows = read_plan(plan)
    def lead_here(row):
        assignment = row.get("assignment") or {}
        if assignment:
            return (assignment.get("lead") or {}).get("session_id") == session_id
        return row.get("session") == session_id
    if not any(lead_here(row) for row in rows):
        return {"binding": "unknown", "reason": "lead_ownership_missing"}
    path, _, _ = read_context(plan, session_id, cwd, runtime)
    if path is None:
        return {"binding": "unknown", "reason": "native_outcome_missing"}
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        outcome = state["business"]["outcome"]
        outcome["finish_verdict"] = lhc_outcome.verdict(outcome, state)
        if _binding_matches(metadata, outcome, plan):
            # A repeated activation is not a new assessment. Keep its exact proof,
            # and cancel any other tentative destination selected in this session.
            outcome.pop("plan_binding_request", None)
        else:
            selected = outcome.get("plan_binding_request") or outcome.get("plan_binding") or {}
            same_request = (selected.get("plan_dir") == str(plan)
                            and selected.get("plan_scope") == plan_scope(metadata)
                            and selected.get("outcome_id") == outcome.get("id"))
            if not same_request:
                # Retain the old evidence before contract can alter canary/stages.
                snapshot = copy.deepcopy(outcome)
                for key in ("plan_binding", "plan_binding_request", "plan_binding_history"):
                    snapshot.pop(key, None)
                outcome.setdefault("plan_binding_history", []).append({
                    "binding": copy.deepcopy(outcome.get("plan_binding")), "outcome": snapshot})
            pending = {**binding(metadata, outcome, plan), "contract_required": True}
            if outcome.get("plan_binding"):
                outcome["plan_binding_request"] = pending
            else:
                outcome["plan_binding"] = pending
        guard.write_state(path, state)
    return {"binding": "bound", "plan_dir": str(plan), "goal_status":
            evaluate(metadata, rows, outcome, state, plan_dir=plan)["goal_status"]}


def confirm_plan_contract(outcome, session_id):
    """Join the normal explicit contract to the selected plan, never to old PASS.

    Called inside the outcome CLI's native-state lock after contract validation.
    No additional operator bind/review command is needed.
    """
    import lhc_plan_json as plans
    import lhc_outcome
    selected = outcome.get("plan_binding_request") or outcome.get("plan_binding")
    if not selected:
        return
    plan = Path(selected["plan_dir"]).resolve()
    if str(plan) not in [str(Path(p).resolve()) for p in plans.session_plans(session_id)]:
        raise ValueError("explicit session-plan binding is missing for contract")
    metadata, rows = read_plan(plan)
    if (outcome.get("owner") or {}).get("session_id") != session_id or not any(
            ((row.get("assignment") or {}).get("lead") or {}).get("session_id") == session_id
            if row.get("assignment") else row.get("session") == session_id for row in rows):
        raise ValueError("current plan Lead ownership is missing for contract")
    old = outcome.get("plan_binding") or {}
    if (not outcome.get("plan_binding_request") and not old.get("contract_required")
            and _binding_matches(metadata, outcome, plan)):
        return  # Identical contract/progress retains the existing acceptance.
    if (selected.get("contract_required") or old.get("plan_scope") != plan_scope(metadata)):
        lhc_outcome.invalidate_changed_stage_evidence(outcome, None)
        outcome["evidence_after"] = datetime.now().astimezone().isoformat()
        outcome["canary"]["status"] = "pending"
    outcome["plan_binding"] = binding(metadata, outcome, plan)
    outcome.pop("plan_binding_request", None)


def record_decision(metadata, rows, outcome, state, plan_dir, decision):
    if not _binding_matches(metadata, outcome, plan_dir):
        raise ValueError("bind the current native outcome to this exact plan first")
    for key in ("decision", "evidence", "action", "owner", "uncertainty"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError("frontier decision requires " + key)
    if decision["decision"] not in DECISIONS:
        raise ValueError("unsupported frontier decision")
    context = evaluate(metadata, rows, outcome, state, plan_dir=plan_dir)
    if decision["decision"] == "human_stop":
        if not _human_hold(state, rows):
            raise ValueError("human stop requires an existing observed native stop/revocation")
    elif decision["decision"] == "wait_external":
        if context["frontier"] in {"runnable", "active"}:
            raise ValueError("permitted work remains; external wait cannot park it")
        if not isinstance(decision.get("resume_condition"), str) or not decision["resume_condition"].strip():
            raise ValueError("external wait requires resume_condition")
    elif decision.get("action_kind") == "leaf":
        if decision.get("leaf_id") not in context["candidates"]:
            raise ValueError("work decision requires an existing dependency-ready leaf")
    elif decision.get("action_kind") not in {"research", "decompose"}:
        raise ValueError("work decision requires leaf, scoped research or decomposition")
    outcome["frontier_decision"] = {**decision, "plan_dir": str(plan_dir),
                                    "fingerprint": context["fingerprint"]}
    return outcome["frontier_decision"]


def resolve_control(plan_dir):
    """Derived graph/catalog snapshot from exact saved native Lead references."""
    plan = Path(plan_dir).resolve()
    try:
        metadata, rows = read_plan(plan)
    except (OSError, ValueError, TypeError):
        return {"goal_status": "unknown", "frontier": "unknown", "next_decision": "none",
                "fingerprint": None, "reason": "plan_unreadable"}
    refs = set()
    for row in rows:
        assignment = row.get("assignment") or {}
        lead = assignment.get("lead") or {} if assignment else {
            "session_id": row.get("session"), "harness": row.get("harness") or row.get("runtime")}
        if lead.get("session_id") and lead.get("harness"):
            refs.add((lead["harness"], lead["session_id"]))
    unknown = evaluate(metadata, rows, plan_dir=plan)
    if len(refs) != 1:
        return {**unknown, "reason": "native_lead_ref_missing" if not refs else "native_lead_ref_ambiguous"}
    runtime, session = next(iter(refs))
    try:
        path, state, saved = read_context(plan, session, plan, runtime)
        if path is None:
            return {**unknown, "reason": "native_outcome_missing"}
        outcome = copy.deepcopy(saved)
        import lhc_outcome
        outcome["finish_verdict"] = lhc_outcome.verdict(outcome, state)
        result = evaluate(metadata, rows, outcome, state, plan_dir=plan)
        if not _binding_matches(metadata, outcome, plan) and result["goal_status"] != "superseded":
            return {**unknown, "reason": "native_outcome_binding_stale"}
        return {**result, "reason": "bound_native_outcome",
                "source": {"kind": "native_outcome", "harness": runtime, "session_id": session,
                           "outcome_id": outcome.get("id"),
                           "source_fingerprint": digest([outcome_scope(outcome), evidence_fingerprint(outcome)])}}
    except (OSError, ValueError, KeyError, TypeError):
        return {**unknown, "reason": "native_outcome_unreadable"}


def record_session_decision(plan_dir, session_id, cwd, decision, runtime=None):
    """Explicit CLI/MCP mutation of the existing native outcome, under its lock."""
    import fcntl
    import lhc_plan_json as plans
    import lhc_time_guard as guard
    plan = Path(plan_dir).resolve()
    if str(plan) not in [str(Path(p).resolve()) for p in plans.session_plans(session_id)]:
        raise ValueError("explicit session-plan binding is missing")
    path, _, _ = read_context(plan, session_id, cwd, runtime)
    if path is None:
        raise ValueError("exact native outcome is missing or ambiguous")
    metadata, rows = read_plan(plan)
    def lead_here(row):
        assignment = row.get("assignment") or {}
        return ((assignment.get("lead") or {}).get("session_id") == session_id
                if assignment else row.get("session") == session_id)
    if not any(lead_here(row) for row in rows):
        raise ValueError("current plan Lead ownership is missing")
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        outcome = state["business"]["outcome"]
        value = record_decision(metadata, rows, outcome, state, plan, decision)
        guard.write_state(path, state)
    return value
