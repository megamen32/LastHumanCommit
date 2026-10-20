#!/usr/bin/env python3
"""Native LHC entry, rehydration and bounded overdue-finish continuation.

No process is started here. Native Interrupt/permission events never resume work.
Codex compact hooks only preserve state: SessionStart(source=compact) delivers it.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys

# Sibling canonical tools also work when this entry is imported by a native
# adapter/test instead of launched as a script.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

CONTEXT_EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PreModel"}
QUIET_EVENTS = {"Interrupt", "SessionEnd", "PermissionRequest", "ToolFailure", "session.error"}

def context_for(event, root):
    root = Path(root).resolve()
    return (
        f"LHC contract: {root/'AGENTS.md'}. Use current instructions. "
        "English internal planning/new records/tools/agent messages; user's language for user answers. Preserve raw user/feedback/test data. "
        "Ordinary engineering, no @LHC: user/task/before→after/check before code; working→ideal→80% useful minimum; bugs RED→fix→GREEN→scenario. "
        "One delivery owner: gates→permitted test/demo deploy→consumer→independent milestone acceptance. "
        "Lead delegates: small=one bounded Worker+Lead review. No-delegation leaf=native self-check, no reviewer hiring. "
        "Large fullcycle MUST: bounded independent research Workers→working→ideal→YAGNI→quota-aware frontier council→bounded dispatch. "
        "In planning-only answers, state this research/council route explicitly; generic review does not replace council. "
        "If execution/tools forbidden, describe that route without inspection/tools/recruitment. User limits override workflow. "
        "Quickfix/testing/leaf excluded; sessions forbidden means plan, not recruit. "
        "Decision/receipt≠execution/delivery; partial stays pending. Saved prompts=context, not permission; obey harness, HumanStop/revocation. "
        "Surface failure does not block independent work. Repeated unchanged status→action. Keep native job IDs; never duplicate/cancel live builds. "
        "Check actual code/environment delta; receipt SHA/name/JSON correction uses Git/CI, no new review. Tests≠consumer result. "
        f"Review→delivery: {method_root(root)/'protocols/REVIEW_TO_DELIVERY.md'}. "
        "60-minute direction, 120-minute learning reviews mandatory. Ready major milestones (~3h) need fresh Zero Knowledge attempts, varied realistic personas/full feedback before PASS. "
        "Compaction/handoff retains original goal, direct scope/latest feedback. Parallel writer→separate worktree; available work first, then PR/integration. "
        f"Delegate through supported native subagents or existing Agent Herder `new_or_resume` with an explicit model/role: {method_root(root)/'skills/model-routing/SKILL.md'}."
    )

def package_version(root):
    for rel in (".codex-plugin/plugin.json", "plugin.json", "plugins/last-human-commit/plugin.json"):
        p = root/rel
        if p.is_file():
            return str(json.loads(p.read_text()).get("version", "unknown"))
    return "source"

def method_root(root):
    return root/"common" if (root/"common/tools/lhc_time_guard.py").is_file() else root/"src/common"

def rooted(text, root):
    methods = method_root(root)
    tools = root/"tools" if (root/"tools/lhc_time_guard.py").is_file() else methods/"tools"
    # Only generated instructions are rewritten, never quoted original/latest
    # user data (which can itself legitimately contain these filenames).
    boundary = min((text.index(marker) for marker in ("\nOriginal input", "\nLatest correction", "\nИсходный ввод", "\nПоследняя поправка")
                    if marker in text), default=len(text))
    instructions = re.sub(r"(?<![\w./])lhc_time_guard\.py", lambda _: shlex.quote(str(tools/"lhc_time_guard.py")), text[:boundary])
    instructions = instructions.replace("common/protocols/BUSINESS_CHECKPOINT.md", str(methods/"protocols/BUSINESS_CHECKPOINT.md"))
    return instructions + text[boundary:]

def rehydrate(state, state_path=None, *, detail=False):
    import lhc_time_guard as time_guard

    business = state.get("business", {})
    native_identity = business.get("native_identity") or {}
    native_assignment = native_identity.get("assignment") if isinstance(native_identity, dict) else None
    verified_child_assignment = bool(
        isinstance(native_identity, dict) and native_identity.get("verified") is True
        and isinstance(native_assignment, dict) and native_assignment.get("status") == "bound"
    )
    unverified_child = bool(
        isinstance(native_identity, dict) and native_identity.get("parent_native_id")
        and not verified_child_assignment
    )
    # Quoted source data, never an instruction to execute arbitrary transcript text.
    active_original, active_latest = time_guard.active_business_prompts(business)
    restored = {
        "original_prompt": active_original or business.get("original_scope_prompt") or business.get("original_prompt"),
        "latest_prompt": active_latest,
    }
    truncated_prompts = []
    if not detail:
        for key, value in list(restored.items()):
            if isinstance(value, str) and len(value) > 600:
                restored[key] = value[:600] + "… [full source retained in native history]"
                truncated_prompts.append(key)
    restored = {key: value for key, value in restored.items() if value}
    if unverified_child:
        restored.pop("original_prompt", None)
        restored.pop("latest_prompt", None)
        restored["native_assignment_status"] = native_identity.get("reason") or (
            native_assignment.get("reason") if isinstance(native_assignment, dict) else None
        ) or business.get("native_identity_error") or "No current native dispatch assignment has been verified."
    import lhc_outcome as outcomes
    for key in ("original_prompt", "latest_prompt"):
        if key in restored:
            restored[key] = outcomes.semantic_scope(restored[key])
            if not restored[key]:
                restored.pop(key)
    if restored.get("latest_prompt") == restored.get("original_prompt"):
        restored.pop("latest_prompt", None)
    if detail and business.get("transcript_path") and business.get("runtime") != "zcode" and not unverified_child:
        restored["full_native_transcript"] = business["transcript_path"]
    if detail and business.get("execution_context"):
        context = business["execution_context"]
        restored_context = dict(context)
        if unverified_child:
            restored_context.pop("direct_user_messages", None)
        restored_context["direct_user_messages"] = [
            {**{key: value for key, value in row.items() if key != "scope_prompt"},
             "prompt": outcomes.semantic_scope(row.get("scope_prompt") or row.get("prompt", ""))}
            for row in ([] if unverified_child else context.get("direct_user_messages", []))
            if outcomes.semantic_scope(row.get("scope_prompt") or row.get("prompt", ""))
        ]
        if not unverified_child:
            restored["execution_context"] = restored_context
    if business.get("running_jobs"):
        restored["running_jobs"] = business["running_jobs"]
    if detail and business.get("tool_observations") and not unverified_child:
        restored["recent_tool_observations"] = business["tool_observations"][-8:]
    if detail and business.get("action_evidence") and not unverified_child:
        restored["action_evidence"] = business["action_evidence"][-8:]
    if business.get('outcome') and not unverified_child:
        contract_keys = ('id', 'task_class', 'actionable', 'contract_confirmed', 'contract_rejection',
                         'canary', 'stages', 'finish_verdict', 'question')
        if detail:
            contract_keys += ('owner', 'stage_claims', 'revision', 'coverage', 'delegation_prohibited',
                              'verification_level', 'integration_policy', 'release_handoff')
        restored['outcome_contract'] = {key: business['outcome'].get(key) for key in contract_keys}
        if not detail and isinstance(restored['outcome_contract'].get('stages'), dict):
            restored['outcome_contract']['stages'] = {
                stage: {
                    key: row.get(key) for key in ('status', 'basis') if row.get(key) is not None
                } | {
                    'evidence_count': len(row.get('evidence') or []),
                    **({'evidence_manifest': (row.get('evidence') or [{}])[0].get('manifest')}
                       if (row.get('evidence') or [{}])[0].get('manifest') else {}),
                }
                for stage, row in restored['outcome_contract']['stages'].items()
                if isinstance(row, dict)
            }
        # Original/latest native sources already appear above; do not inject
        # duplicate scope histories and full native review text on every resume.
    native_entry = state.get("native_entry") or {}
    if native_entry.get("scoped_failures"):
        restored["scoped_tool_failures"] = native_entry["scoped_failures"][-8:]
    if truncated_prompts and not unverified_child:
        locators = {}
        if "original_prompt" in truncated_prompts:
            if business.get("original_prompt_full"):
                locators["original_prompt"] = "business.original_prompt_full"
            elif business.get("original_scope_prompt"):
                locators["original_prompt"] = "business.original_scope_prompt"
            else:
                locators["original_prompt"] = "business.original_prompt"
        if "latest_prompt" in truncated_prompts:
            current_latest = business.get("latest_prompt_full") or business.get("latest_prompt") or ""
            current_latest_scope = time_guard._eligible_active_scope(
                current_latest, business, active_original,
                scope_hint=business.get("latest_scope_prompt"))
            if current_latest_scope == active_latest and business.get("latest_prompt_full"):
                locators["latest_prompt"] = "business.latest_prompt_full"
            elif current_latest_scope == active_latest and business.get("latest_scope_prompt"):
                locators["latest_prompt"] = "business.latest_scope_prompt"
            else:
                context_rows = (business.get("execution_context") or {}).get("direct_user_messages") or []
                matching = [index for index, row in enumerate(context_rows)
                            if isinstance(row, dict) and time_guard._eligible_active_scope(
                                row.get("prompt", ""), business, active_original,
                                origin=row.get("origin"), scope_hint=row.get("scope_prompt")) == active_latest]
                if matching:
                    row = context_rows[matching[-1]]
                    field = "scope_prompt" if row.get("scope_prompt") else "prompt"
                    locators["latest_prompt"] = f"business.execution_context.direct_user_messages[{matching[-1]}].{field}"
                else:
                    locators["latest_prompt"] = "business.latest_prompt"
        restored["truncated_prompt_source_fields"] = locators
        if state_path is not None:
            restored["full_saved_state"] = str(state_path)
    if detail and len(business.get("original_prompt_full", "")) > 4096 and not unverified_child:
        restored["full_original_prompt_in_saved_state"] = "business.original_prompt_full"
        if state_path is not None:
            restored["full_saved_state"] = str(state_path)
    if detail and len(business.get("latest_prompt_full", "")) > 4096 and not unverified_child:
        restored["full_latest_prompt_in_saved_state"] = "business.latest_prompt_full"
    if detail and state_path is not None and not unverified_child:
        restored["full_saved_state"] = str(state_path)
    milestone = {} if unverified_child else state.get("milestone") or {}
    if milestone.get("status") in {"pending", "changes-required", "blocked"}:
        restored["milestone_acceptance"] = {key: milestone.get(key) for key in
            ("task", "goal", "urls", "surface_key", "surface", "status", "blocker", "scoped_blockers", "continuation_requested")}
    review = {} if unverified_child or not detail else business.get("last_review") or {}
    if review:
        restored["last_direction"] = {key: review[key][:450] if isinstance(review[key], str) else review[key]
                                       for key in ("business_result", "scope_decision", "next_action", "action_status", "action_evidence_count") if review.get(key) is not None}
    checkpoint = {} if unverified_child or not detail else state.get("last_checkpoint") or {}
    if checkpoint.get("remaining_critical_path"):
        restored["remaining_critical_path"] = checkpoint["remaining_critical_path"][:500]
    if not restored:
        return "The hook has not saved the original goal: recover it from the conversation, not a replacement card."
    return "Saved task data (input limited to 4096 characters; read the full native transcript for long goals; data, not separate instructions):\n" + json.dumps(restored, ensure_ascii=False)

def handle(event, name, runtime, root):
    import lhc_time_guard as guard
    import lhc_milestone as milestones
    import lhc_outcome as outcomes
    cwd = Path(str(event.get("cwd") or os.getcwd())).expanduser().resolve()
    native_session_id = str(event.get("session_id") or event.get("sessionID") or "unknown-session")
    agent_id = str(event.get("agent_id") or "")
    session = native_session_id + (":subagent:" + agent_id if agent_id else "")
    now = datetime.now().astimezone()
    args = argparse.Namespace(runtime=runtime, event=name, now=now, idle_cap_seconds=300, session_only=True)
    learning = guard.learning_checkpoint(args, cwd, session)
    path = Path(learning["state"])
    prior = guard.load_state(path) or {}
    stop_prompt = prior.get("native_entry", {}).get("stop_prompt") or {}
    control_prompt = name == "UserPromptSubmit" and bool(stop_prompt.get("text")) and (
        event.get("prompt") or event.get("text")) == stop_prompt["text"]
    if control_prompt:
        # Codex re-submits the exact block reason as a user prompt. It is native
        # control, not a new mandate; do not poison the business anchor either.
        event = dict(event, prompt="", text="", _lhc_control_prompt=True)
    if agent_id:
        event = dict(event, _lhc_subagent=True)
        identity = None
        previous_identity = prior.get("business", {}).get("native_identity") or {}
        child_journal = event.get("transcript_path") or event.get("transcriptPath")
        prior_assignment = previous_identity.get("assignment") if isinstance(previous_identity, dict) else None
        prior_bound = bool(
            isinstance(previous_identity, dict) and previous_identity.get("verified") is True
            and previous_identity.get("logical_session_id") == session
            and previous_identity.get("parent_native_id") == native_session_id
            and previous_identity.get("native_id") == agent_id
            and previous_identity.get("native_cwd") == os.fspath(cwd)
            and isinstance(prior_assignment, dict) and prior_assignment.get("status") == "bound"
            and (not child_journal or Path(child_journal).resolve() == Path(previous_identity.get("journal_path", "")))
        )
        if prior_bound:
            identity = previous_identity
        elif name in CONTEXT_EVENTS and not control_prompt:
            identity = guard.resolve_native_child_assignment(event, session, runtime, cwd)
        if not isinstance(identity, dict):
            identity = {"verified": False, "status": "unavailable",
                        "parent_native_id": native_session_id, "native_id": agent_id,
                        "reason": "current child assignment has not been verified"}
        event["_lhc_verified_native_identity"] = identity
    prior_business = prior.get("business", {})
    prior_outcome = prior_business.get("outcome", {})
    prior_milestone = prior.get("milestone", {})
    event = dict(event, _lhc_previous_active_prompts=[
        prior_business.get("latest_prompt_full") or prior_business.get("latest_prompt") or "",
        prior_business.get("original_prompt_full") or prior_business.get("original_prompt") or "",
        prior_outcome.get("latest_correction") or "",
        prior_outcome.get("original_goal") or "",
        prior_milestone.get("goal") or "",
    ])
    business = guard.business_checkpoint(args, cwd, session, event)
    with path.with_suffix(".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        observer_event = event
        if agent_id and name == "UserPromptSubmit":
            # Keep the relayed native prompt as provenance, while the captured
            # dispatch assignment remains the active task boundary.
            observer_event = dict(event, prompt="", text="", transcript_path=None,
                                  messages=[], _lhc_control_prompt=True)
        child_identity = event.get("_lhc_verified_native_identity") or {}
        child_assignment = child_identity.get("assignment") if isinstance(child_identity, dict) else None
        prior_identity = prior.get("business", {}).get("native_identity") or {}
        prior_assignment = prior_identity.get("assignment") if isinstance(prior_identity, dict) else None
        assignment_conflict = bool(
            isinstance(prior_identity, dict) and prior_identity.get("verified") is True
            and prior_identity.get("dispatch_call_id")
            and isinstance(child_identity, dict)
            and (child_identity.get("dispatch_call_id") != prior_identity.get("dispatch_call_id")
                 or (isinstance(prior_assignment, dict) and prior_assignment.get("status") == "bound"
                     and isinstance(child_assignment, dict)
                     and prior_assignment.get("prompt_sha256") != child_assignment.get("prompt_sha256")))
        )
        child_assignment_bound = bool(
            agent_id and isinstance(child_identity, dict) and child_identity.get("verified") is True
            and not assignment_conflict
            and isinstance(child_assignment, dict) and child_assignment.get("status") == "bound"
            and isinstance(child_assignment.get("prompt"), str)
            and child_assignment.get("prompt_sha256") == hashlib.sha256(
                child_assignment["prompt"].encode()
            ).hexdigest()
            and child_assignment.get("child_id") == agent_id
        )
        if agent_id and not child_assignment_bound:
            # Keep unverified relay history in source context, but do not resume
            # an old task summary or create active review state from it.
            milestone = None
            outcome = None
        else:
            milestone = milestones.observe(state, observer_event, name, cwd, session, now)
            outcome = outcomes.observe(state, observer_event, name, cwd, session, now)
        # A concurrent native hook or an explicit review command may have cleared
        # a debt after our first observation. Decisions use the locked readback.
        current_pending = state.get("business", {}).get("pending")
        if not current_pending or current_pending.get("id") != business.get("review_id"):
            business["prompt"] = ""
        business.update(due=bool(current_pending), review_id=current_pending.get("id") if current_pending else None)
        current_due = state["due_at"]
        still_due = max(now, guard.parse_time(state["last_observed_at"])) >= guard.parse_time(current_due)
        if not still_due or current_due != learning["due_at"]:
            learning["prompt"] = ""
        learning.update(due=still_due, due_at=current_due)
        delivery = state.setdefault("native_entry", {})
        scoped_failure = (milestones.scoped_surface_failure(event)
                          if name == "PostToolUse" and milestones.tool_failed(event) else None)
        if scoped_failure:
            failures = delivery.setdefault("scoped_failures", [])
            if scoped_failure not in failures:
                failures.append(scoped_failure)
            del failures[:-16]
        delivery["last_observed_event"] = name
        if name in QUIET_EVENTS:
            delivery["finish_hold"] = name
        elif name == "UserPromptSubmit" and not agent_id and not control_prompt and delivery.get("finish_hold") != "PermissionRequest":
            raw_prompt = event.get("prompt") or event.get("text") or ""
            origin = outcomes.source_origin(raw_prompt)
            active_business = prior.get("business", {})
            active_prompts = event.get("_lhc_previous_active_prompts") or [
                active_business.get("latest_prompt_full") or active_business.get("latest_prompt") or "",
                active_business.get("original_prompt_full") or active_business.get("original_prompt") or "",
            ]
            if guard.prompt_can_resume_hold(raw_prompt, active_prompts,
                                            hold=delivery.get("finish_hold"), origin=origin):
                delivery.pop("finish_hold", None)
        elif name == "permission.replied" and delivery.get("finish_hold") == "PermissionRequest":
            delivery.pop("finish_hold", None)
        elif name in {"PostToolUse", "PostToolUseFailure"} and (name == "PostToolUseFailure" or milestones.tool_failed(event)):
            if not scoped_failure and delivery.get("finish_hold") not in {"PermissionRequest", "Interrupt", "SessionEnd"}:
                delivery["finish_hold"] = "ToolFailure"
        elif name == "PostToolUse" and delivery.get("finish_hold") in {"ToolFailure", "PermissionRequest"}:
            delivery.pop("finish_hold", None)
        if outcome:
            outcome['finish_verdict'] = outcomes.verdict(outcome, state)
        version = package_version(root)
        signature = json.dumps([str(root), version])
        supported = name in CONTEXT_EVENTS or runtime != "codex"
        refresh = name in {"SessionStart", "PreCompact", "PostCompact"}
        bootstrap = supported and name not in QUIET_EVENTS | {"Stop"} and (
            refresh or event.get("lhc_detail") == "full" or
            delivery.get("loaded") != signature or delivery.get("rehydrate_needed"))
        contexts = []
        if name in {"PreCompact", "PostCompact"}:
            delivery["rehydrate_needed"] = True
        if bootstrap:
            compact_detail = (name in {"PreCompact", "PostCompact"} or
                              (name == "SessionStart" and event.get("source") == "compact") or
                              event.get("lhc_detail") == "full")
            contexts.extend((context_for(event, root), rehydrate(state, path, detail=compact_detail)))
            delivery.update(loaded=signature, version=version, root=str(root), rehydrate_needed=False)
        elif runtime == 'opencode' and event.get('model_boundary'):
            # V2 rebuilds system parts for every model request; loaded state
            # does not carry operating instructions into the next request.
            contexts.append(context_for(event, root))
        outcome_notice = outcomes.reminder(outcome, method_root(root)/'tools/lhc_outcome.py') if outcome and outcome['finish_verdict'] != 'complete' else ''
        rejection = outcome.get('contract_rejection') or {} if outcome else {}
        outcome_notice_fingerprint = json.dumps([
            outcome['id'], outcome.get('latest_correction'),
            [(key, row['status']) for key, row in sorted(outcome.get('stages', {}).items())],
            outcome.get('canary', {}).get('status'), outcome.get('contract_confirmed'),
            rejection.get('scope_fingerprint'), rejection.get('exact_error'), rejection.get('corrective_action'),
        ], ensure_ascii=False) if outcome_notice else None
        rehydrating_outcome = name == 'PostCompact' or (name == 'SessionStart' and event.get('source') == 'compact')
        if outcome_notice and (bootstrap or event.get('model_boundary') or
                               outcome_notice_fingerprint != delivery.get('outcome_notice_fingerprint')) and (
                outcome_notice_fingerprint != delivery.get('outcome_notice_fingerprint') or rehydrating_outcome):
            contexts.append(outcome_notice)
            delivery['outcome_notice_fingerprint'] = outcome_notice_fingerprint
            if not outcome.get('contract_confirmed') and not outcome.get('contract_rejection'):
                outcome['contract_request_fingerprint'] = outcomes.contract_scope_fingerprint(outcome)
        acceptance_pending = milestones.pending(milestone)
        acceptance_notice = milestones.reminder(milestone) if acceptance_pending else ""
        acceptance_id = [milestone.get("surface_key"), milestone["status"]] if acceptance_pending else None
        if acceptance_notice and supported and name not in QUIET_EVENTS | {"Stop"} and not milestone.get("hold"):
            if bootstrap or event.get("model_boundary") or delivery.get("milestone_injected") != acceptance_id:
                contexts.append(acceptance_notice)
                delivery["milestone_injected"] = acceptance_id
        if supported and name not in QUIET_EVENTS | {"Stop"}:
            if business["prompt"]:
                contexts.append(rooted(business["prompt"], root))
            previous = delivery.get("learning_injected_at")
            if learning["prompt"] and (refresh or not previous or
                    delivery.get("learning_due") != learning["due_at"] or
                    (now-guard.parse_time(previous)).total_seconds() >= 300):
                contexts.append(rooted(learning["prompt"], root))
                delivery.update(learning_injected_at=now.isoformat(), learning_due=learning["due_at"])
        output = {}
        if runtime == "opencode" and name == "PreCompact":
            # V2 compaction consumes the native system slot. Restore the actual
            # original/latest human goal, not a stale nearby task card.
            parts = [context_for(event, root), rehydrate(state, path)]
            if business["prompt"]:
                parts.append(rooted(business["prompt"], root))
            if learning["prompt"]:
                parts.append(rooted(learning["prompt"], root))
            if acceptance_notice:
                parts.append(acceptance_notice)
            if outcome_notice:
                parts.append(outcome_notice)
            output = {"handoff": "\n\n".join(parts)}
        held = bool(delivery.get("finish_hold") or (milestone and milestone.get("hold")))
        acceptance_due = acceptance_pending and milestone["status"] != "accepted"
        outcome_due = bool(outcome and (outcome['task_class'] in outcomes.ENGINEERING | {'testing', 'research'} or
                           (outcome['task_class'] == 'unknown' and outcome.get('actionable'))) and outcome['finish_verdict'] != 'complete')
        if runtime in {"codex", "zcode"} and name == "Stop" and not held and (business["due"] or learning["due"] or acceptance_due or outcome_due):
            progress = outcomes.fingerprint(outcome, milestone) if outcome else milestone.get('surface_key')
            identity = [business.get("review_id") if business["due"] else None,
                        learning["due_at"] if learning["due"] else None, progress]
            used = delivery.setdefault('used_progress_continuations', [])
            fresh_acceptance = (acceptance_due or outcome_due) and progress not in used
            deadline_due = (business["due"] or learning["due"]) and delivery.get("stop_continuation") != identity
            if not event.get("stop_hook_active") and (fresh_acceptance or deadline_due):
                delivery["stop_continuation"] = identity
                delivery["stop_pending_notice"] = identity
                if fresh_acceptance:
                    used.append(progress)
                if acceptance_due:
                    milestone["continuation_requested"] = True
                tool = method_root(root)/"tools/lhc_time_guard.py"
                base = f"python3 {shlex.quote(str(tool))}"
                flags = f"--cwd {shlex.quote(str(cwd))} --runtime {runtime} --session-id {shlex.quote(session)}"
                obligations = []
                if business["due"]:
                    obligations.append(f"python3 {shlex.quote(str(tool))} business-review {flags} --review-id {business['review_id']} --source-ref '<original assignment>' --business-result '<actual result>' --scope-decision '<decision>' --next-action '<next action>'")
                if learning["due"]:
                    obligations.append(f"{base} checkpoint {flags} --due-at {shlex.quote(learning['due_at'])} --observation '<observation>' --method-change '<method correction>' --verification '<effect verification>' --accepted-result '<accepted result>' --remaining-critical-path '<remaining work>' --scope-review '<scope review>' --rework-review '<rework review>'")
                if business["due"] and learning["due"]:
                    overdue = "direction/method review and 120-minute learning checkpoint are overdue"
                elif business["due"]:
                    overdue = "direction/method review is overdue"
                else:
                    overdue = "120-minute learning checkpoint is overdue"
                instruction_paths = []
                if business["due"]:
                    instruction_paths.append(str(method_root(root)/"protocols/BUSINESS_CHECKPOINT.md"))
                if learning["due"]:
                    instruction_paths.append(str(method_root(root)/"protocols/SELF_IMPROVE.md"))
                reason = (f"LHC: {overdue} before ordinary completion. "
                          "Complete the due obligation(s) with actual observations; do not start development for a report or call it milestone acceptance. "
                          + ("The learning checkpoint permits an evidence-backed --no-change-reason instead of --method-change. "
                             if learning["due"] else "")
                          + "Instructions: " + " and ".join(instruction_paths) + ".\n"
                          + "\n".join(obligations) + "\n" + rehydrate(state, path))
                if not obligations:
                    reason = ""
                if outcome_due:
                    reason += ("\n" if reason else "") + outcome_notice
                if acceptance_notice:
                    reason += ("\n" if reason else "") + acceptance_notice
                    running_jobs = state.get("business", {}).get("running_jobs", {})
                    if running_jobs:
                        summary = [{"id": key, "operation": value.get("operation", "unknown"),
                                    "target": value.get("target", "unknown")}
                                   for key, value in sorted(running_jobs.items())[:4]]
                        reason += "\nNative running work (do not duplicate or abort; independent actions remain available): " + json.dumps(summary, ensure_ascii=False)
                    scoped_failures = delivery.get("scoped_failures", [])
                    if scoped_failures:
                        summary = [{"target": row.get("target"), "operation": row.get("operation"),
                                    "http_status": row.get("http_status")} for row in scoped_failures[-4:]]
                        reason += "\nThese failures belong only to the listed surface; do not repeat without changed evidence, and continue independent actions: " + json.dumps(summary, ensure_ascii=False)
                delivery["stop_prompt"] = {"identity": identity, "text": reason}
                output = {"decision": "block", "reason": reason}
            else:
                # Native continuation is bounded. Unavailable work remains pending;
                # never loop indefinitely or fake a successful review to finish.
                if delivery.get("stop_pending_notice") != identity:
                    delivery["stop_pending_notice"] = identity
                    output = {"systemMessage": "LHC: pending review preserved; no repeated automatic continuation for this finish. Do not call it completed."}
        elif contexts and supported and name not in QUIET_EVENTS | {"Stop"}:
            output = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": "\n\n".join(contexts)}}
            delivery["last_context_event"] = name
            delivery["last_context_at"] = now.isoformat()
        guard.write_state(path, state)
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default="SessionStart")
    parser.add_argument("--root", type=Path)
    default_runtime = ("zcode" if os.environ.get("ZCODE_PLUGIN_ROOT") else
                       "claude" if os.environ.get("CLAUDE_PROJECT_DIR") else "codex")
    parser.add_argument("--runtime", choices=("codex", "claude", "opencode", "zcode"), default=default_runtime)
    args = parser.parse_args()
    try:
        # Native tool responses routinely exceed 64 KiB. Truncating JSON used to
        # silently erase session_id and update a shared unknown-session clock.
        raw = sys.stdin.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("native payload exceeds the bounded 8 MiB character window")
        event = json.loads(raw or "{}")
        if not isinstance(event, dict) or not (event.get("session_id") or event.get("sessionID")):
            raise ValueError("native session identity is missing")
    except ValueError:
        print(json.dumps({"systemMessage": "LHC: invalid or oversized native payload; event not recorded. Other/unknown session state unchanged."}, ensure_ascii=False))
        return
    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    try:
        output = handle(event, args.event, args.runtime, root)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        warning = "LHC runtime unavailable: " + type(error).__name__ + ". Automatic control unconfirmed; preserve the goal and continue available work."
        output = {"systemMessage": warning}
        if args.event in CONTEXT_EVENTS:
            output["hookSpecificOutput"] = {"hookEventName": args.event, "additionalContext": context_for(event, root)+"\n"+warning}
    if output: print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__": main()
