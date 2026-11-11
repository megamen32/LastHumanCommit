#!/usr/bin/env python3
"""Native LHC entry: points the agent at its instructions and at the open plan.

Hooks read facts on disk only. No text of a prompt is classified and nothing is blocked.
"""
import argparse
import contextlib
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import io
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


def _verbose_workflow():
    return str(os.environ.get("LHC_VERBOSE_WORKFLOW", "")).lower() in {"1", "true", "yes", "on"}


def _strict_workflow():
    return str(os.environ.get("LHC_STRICT_WORKFLOW", "")).lower() in {"1", "true", "yes", "on"}


def _explicit_plan_request(event):
    prompt = str((event or {}).get("prompt") or (event or {}).get("text") or "")
    return bool(re.search(r"(?:^|\s)(?:/plan|составь план|покажи план|show (?:the )?plan|make a plan)\b", prompt, re.I))

def _plan_entry(event, root):
    if not _explicit_plan_request(event) and not _verbose_workflow():
        return None
    """Return read-only candidates; the model decides whether one fits the goal.

    No prompt is classified and no plan is created, bound, registered or
    announced here. Only one unfinished leaf explicitly bound to this native
    session can be called a continuation; all other open plans remain candidates.
    The plan of this session is found by its binding first (the index that activate and
    create-leaf write: session -> plan dirs), then in the repository of the cwd, so a
    session that works in one project on a plan of another is still held and reminded.
    """
    cwd = Path(event.get("cwd") or ".").expanduser().resolve()
    session = str(event.get("session_id") or event.get("sessionID") or "").strip()
    if not session:
        return None
    tools = method_root(Path(root).resolve()) / "tools"
    mirror = sibling_tool(tools, "lhc_plan_mirror.py")
    if mirror is None:
        return None
    indexed = []
    try:
        pj = sibling_tool(tools, "lhc_plan_json.py")
        indexed = [Path(p) for p in pj.session_plans(session)] if pj else []
    except Exception:  # noqa: BLE001 - without the index the cwd repository is still searched
        indexed = []
    git = sibling_tool(tools, "lhc_gitlayout.py")
    repo = git.worktree_root(cwd) if git and hasattr(git, "worktree_root") else None
    repo = Path(repo or cwd).resolve()
    scan = [(p, True) for p in indexed]
    if (repo / ".git").exists():
        for base in (repo / ".agents" / "tasks", repo / "docs" / "tasks"):
            if base.is_dir():
                scan += [(p, False) for p in sorted(p for p in base.iterdir() if (p / "plan.json").is_file())]
    elif not indexed:
        return None
    open_plans = []
    bound_leaves = []
    status_bindings = []
    seen = set()
    status_seen = set()
    for plan, from_index in scan:
        try:
            plan = plan.resolve()
        except OSError:
            continue
        if plan in seen or not (plan / "plan.json").is_file():
            continue
        leaves = [mirror.read(f, {}) for f in sorted((plan / "leaves").glob("*.json"))]
        def explicit_open(leaf):
            assignment = leaf.get("assignment")
            return (isinstance(assignment, dict) and assignment.get("state") not in {"accepted", "cancelled"}
                    and leaf.get("status") not in {"done", "deferred", "deferred_ai"})
        todo = [leaf for leaf in leaves if leaf.get("status") in {"queued", "running"} or explicit_open(leaf)]
        def bound_here(leaf):
            assignment = leaf.get("assignment") or {}
            if isinstance(assignment, dict) and any(
                isinstance(assignment.get(role), dict) and assignment[role].get("session_id") == session
                for role in ("lead", "executor")
            ):
                return True
            return leaf.get("session") == session
        mine = [leaf for leaf in todo if bound_here(leaf)]
        if plan not in status_seen:
            status_bindings.extend({"plan": str(plan), "leaf": str(leaf.get("id"))}
                                   for leaf in leaves if bound_here(leaf))
            status_seen.add(plan)
        if todo and (mine or not from_index):  # a stale index entry is not a candidate
            seen.add(plan)
            open_plans.append(plan)
            bound_leaves.extend({"plan": str(plan), "leaf": str(leaf.get("id"))} for leaf in mine)
    continuation = bound_leaves[0] if len(bound_leaves) == 1 else None
    candidates = [str(plan) for plan in open_plans
                  if continuation is None or str(plan) != continuation["plan"]]
    status_plans = list(dict.fromkeys(item["plan"] for item in status_bindings))
    return {"continuation": continuation, "candidates": candidates[:8],
            "ambiguous_bindings": bound_leaves if len(bound_leaves) > 1 else [],
            "status_bindings": status_bindings, "status_plans": status_plans}


def _plan_context(result):
    """Explain candidate state without deciding or performing plan operations."""
    parts = []
    continuation = result.get("continuation")
    if continuation:
        parts.append(
            f"Есть одна незавершённая leaf {continuation['leaf']} плана "
            f"{continuation['plan']}, привязанная к этой native session. Это только "
            "кандидат продолжения: сначала сверь его с последней прямой целью человека "
            "и действующим STOP; продолжай только при совпадении."
        )
    if result.get("ambiguous_bindings"):
        bindings = result["ambiguous_bindings"]
        parts.append("К этой native session привязано несколько незавершённых leaf; "
                     "модель должна сопоставить их с актуальной целью и не выбирать "
                     "автоматически: " + ", ".join(
                         f"{item['leaf']} в {item['plan']}" for item in bindings[:8]) + ".")
    status_plans = result.get("status_plans") or []
    if len(status_plans) == 1:
        parts.append("Для просмотра сохранённого плана этой сессии вызови show_plan с plan_dir "
                     + status_plans[0] + "; это только чтение, не команда продолжать работу.")
    elif len(status_plans) > 1:
        parts.append("К этой сессии привязано несколько сохранённых планов; не выбирай "
                     "автоматически для просмотра, уточни выбор: " + ", ".join(status_plans) + ".")
    if result.get("candidates"):
        parts.append("Другие открытые планы — только кандидаты, не команда продолжать "
                     "или связывать сессию: " + ", ".join(result["candidates"]) + ". "
                     "Модель сверяет их с новой целью человека; при равной неоднозначности "
                     "уточняет выбор.")
    return " ".join(parts)


PULSE_AFTER = 1200  # seconds: how often one plan audit note may repeat


CODEX_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?")


def restore_codex_routes(tools=None, codex_home=None, state_home=None):
    """Give every Codex LHC version this host has seen its hook tools back.

    Codex upgrades the plugin by itself and prunes the old version directory,
    while chats opened on that version still call its hooks. A new session runs
    this hook from the new version: it records its own version and links the
    tools of every recorded version that lost them to the marketplace tools.
    Existing files and links are never replaced. Returns the restored versions.
    """
    tools = Path(tools or Path(__file__).resolve().parent)
    package, cache = tools.parent, tools.parent.parent
    if cache.name != "last-human-commit" or not CODEX_VERSION.fullmatch(package.name):
        return []
    codex_home = Path(codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    if codex_home.resolve() not in cache.resolve().parents:
        return []
    record = Path(state_home or os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") \
        / "lhc/codex-plugin-versions.json"
    try:
        seen = json.loads(record.read_text(encoding="utf-8"))
        seen = [item for item in seen if isinstance(item, str) and CODEX_VERSION.fullmatch(item)]
    except (OSError, ValueError, TypeError):
        seen = []
    present = [path.name for path in cache.iterdir() if path.is_dir() and CODEX_VERSION.fullmatch(path.name)]
    versions = sorted(set(seen) | set(present) | {package.name})
    if set(versions) != set(seen):
        record.parent.mkdir(parents=True, exist_ok=True)
        temporary = record.with_suffix(".tmp")
        temporary.write_text(json.dumps(versions, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, record)
    source = codex_home / ".tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/tools"
    if not (source / "lhc_entry.py").is_file():
        return []
    restored = []
    for version in versions:
        target = cache / version / "tools"
        if target.exists() or target.is_symlink() or (cache / version).is_symlink():
            continue
        (cache / version).mkdir(exist_ok=True)
        try:
            target.symlink_to(source.resolve(), target_is_directory=True)
            restored.append(version)
        except FileExistsError:
            continue
    return restored



def plan_resume_context(event, root):
    """Read-only recovery of the session-bound plan and its latest saved state."""
    if not isinstance(event, dict) or event.get("agent_id"):
        return None
    found = _plan_entry(event, root)
    if not found:
        return None
    continuation = found.get("continuation")
    bindings = found.get("status_bindings")
    if bindings is None:  # compatibility with callers that provide the older result shape
        bindings = [continuation] if continuation else found.get("ambiguous_bindings") or []
    if not bindings:
        context = _goal_frontier_context(event)
        return _frontier_text(context) if context else None
    precedence = "Latest direct human request and STOP take precedence; reconcile them before continuing."
    plans = {item["plan"]: item for item in reversed(bindings)}
    if len(plans) > 1:
        # Several leaves in one plan do not make the plan ambiguous. Several
        # plans do: preserve their identities without borrowing another's IDs.
        return ("LHC: several plans are bound to this session. " + precedence + "\n" +
                _plan_context({"ambiguous_bindings": found.get("ambiguous_bindings") or [],
                               "status_plans": list(plans)}))[:4000]
    plan = Path(bindings[0]["plan"])
    if not any((plan / "leaves").glob("*.json")):
        return None
    import lhc_plan_json
    try:
        metadata = json.loads((plan / "plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    short = lhc_plan_json._short
    lines = [f"LHC: session-bound plan {plan.name} ({plan}). Saved state for recovery. " + precedence]
    for key, label, limit in (("goal", "Goal", 600), ("current_progress", "Current progress", 500)):
        if metadata.get(key):
            lines.append(f"{label}: {short(metadata[key], limit)}")
    revisions = metadata.get("revisions")
    if isinstance(revisions, list) and revisions:
        latest = revisions[-1]
        latest = {"reason": latest} if isinstance(latest, str) else latest
        if isinstance(latest, dict):
            lines.append(f"Latest revision {len(revisions)}: " + "; ".join(
                short(latest[key], limit) for key, limit in (("at", 50), ("reason", 200), ("summary", 400))
                if latest.get(key)))
    policy = metadata.get("estimate_policy") or {}
    policy = policy if isinstance(policy, dict) else {}
    cap = _plan_leaf_cap(metadata)
    lines.append(f"Plan policy: deliverable={short(metadata.get('deliverable') or 'implementation', 40)}, "
                 f"decomposition={short(metadata.get('decomposition') or 'progressive', 40)}, leaf_cap_minutes={cap}.")
    if policy.get("reason"):
        lines.append("Estimate reason: " + short(policy["reason"], 200))
    lines.append(f"Whole plan: {plan / 'plan.md'}")
    bound_ids = {str(item["leaf"]) for item in bindings}
    current = [str(leaf.get("id")) for leaf in lhc_plan_json._leaf_rows(plan)
               if str(leaf.get("id")) in bound_ids and leaf.get("status") == "running"
               and leaf.get("kind") != "milestone"]
    summary = lhc_plan_json.plan_summary(plan, current)
    if not current:
        lines.append("Now: no running leaf bound to this session.")
    # Keep the current note and next work ahead of potentially long Done history.
    # The canonical summary owns the status wording and leaf facts.
    priority = ("Now:", "Next:", "Running in other sessions or Workers:")
    lines += [line for line in summary if line.startswith(priority)]
    rows, _milestones = lhc_plan_json.split_milestones(lhc_plan_json._leaf_rows(plan), strict=False)
    grid = lhc_plan_json.grid_module()
    readiness = grid._load_sibling("lhc_readiness")
    decision = readiness.evaluate(rows, slots=metadata.get("slots")) if readiness else None
    if decision:
        lines.append("Readiness: candidates by dependencies/capacity=" + (", ".join(decision["ready"][:8]) or "none")
                     + "; dispatchable=" + (", ".join(decision["dispatchable"][:8]) or "none") + ".")
    lines.append("Do not automatically retry ambiguous delivery, bypass STOP/quota, or create another wake for a recorded wait.")
    bound = [leaf for leaf in rows if str(leaf.get("id")) in bound_ids and isinstance(leaf.get("assignment"), dict)]
    bound.sort(key=lambda leaf: (leaf["assignment"].get("state") not in {"blocked", "delivery_unknown", "result_ready"},
                                 leaf.get("status") != "running"))
    for leaf in bound[:2]:
        assignment = leaf["assignment"]
        view = grid.execution_view(leaf, (decision or {}).get("by_id", {}).get(str(leaf.get("id"))))
        state = assignment.get("state")
        if state == "result_ready":
            action = "Lead reviews and accepts/rejects this exact attempt result, then recomputes readiness."
        elif state in {"blocked", "delivery_unknown", "dispatching"} or view["wake"].get("state") in {"blocked", "delivery_blocked", "delivery_unknown"}:
            action = "Reconcile the exact attempt/turn and recorded wake; inspect the blocker before any new dispatch."
        elif state in {"submitted", "running"}:
            action = "Reconcile the exact native turn and reuse its recorded wake; turn completion still needs Lead acceptance."
        else:
            action = "Observe the exact executor and latest human goal; dispatch only an explicitly assigned candidate with confirmed admission."
        lines.append(f"Next action: {leaf.get('id')} attempt={assignment.get('attempt_id') or 'unknown'}: " + action)
        lines.append(short("Execution " + str(leaf.get("id")) + ": " + " | ".join(grid.execution_lines(leaf, view["readiness"])), 1800))
    if not bound:
        lines.append("Next action: Lead checks the latest goal, selects a dependency candidate, and explicitly identifies an executor; legacy session metadata is not runtime proof.")
    lines += [line for line in summary if not line.startswith(priority + ("Whole plan:",))]
    context = _goal_frontier_context(event)
    if context:
        lines.insert(1, _frontier_text(context))
    return "\n".join(lines)[:4000]


def _plan_leaf_cap(metadata):
    """Use the saved plan's scoped estimate policy, with the format default."""
    import lhc_plan_json
    return lhc_plan_json.leaf_estimate_cap(metadata)


def _split_leaves(leaves):
    """The leaves without the milestones that have leaves, and all milestones.

    Facts of the files only: a milestone is read from its leaves the way the
    page reads it, so the hook and the page never disagree about a stage.
    """
    if not any(isinstance(leaf, dict) and (leaf.get("kind") == "milestone" or leaf.get("parent"))
               for leaf in leaves.values()):
        return leaves, []
    try:
        tools = str(Path(__file__).resolve().parent)
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from lhc_plan_json import split_milestones
    except ImportError:
        return leaves, []
    rows = []
    for ident, leaf in leaves.items():
        row = dict(leaf)
        row["id"] = str(ident)
        rows.append(row)
    tasks, stages = split_milestones(rows, strict=False)
    return {task["id"]: task for task in tasks}, stages


def _estimate_max(leaf):
    estimate = leaf.get("estimate_minutes") or leaf.get("estimate") or leaf.get("estimate_max")
    if isinstance(estimate, dict):
        estimate = estimate.get("maximum", estimate.get("max"))
    try:
        return float(estimate)
    except (TypeError, ValueError):
        return None


STOP_FIRES = 4          # a stop is held this many times per window while only queued leaves remain
STOP_MAX = 6            # hard limit per window, also for a running leaf nobody closed or escalated
STOP_WINDOW = 6 * 3600  # a plan untouched this long is not this session's live work


def _escalation_sent(session, starts, since, tools):
    """True when this session wrote a question/result letter into a project's .agents/mail.

    Facts of the files only: <primary>/.agents/mail/<to>[/done]/<time>-<session>-<kind>.md,
    which lhc_mail.py send names after the sender. since is epoch seconds."""
    try:
        mail = sibling_tool(tools, "lhc_mail.py")
        for start in starts:
            try:
                folder = mail.primary_root(start) / ".agents" / "mail"
            except Exception:  # noqa: BLE001 - not a git directory
                continue
            if not folder.is_dir():
                continue
            for kind in ("question", "result"):
                for path in list(folder.glob(f"*/*-{session}-{kind}.md")) + list(folder.glob(f"*/done/*-{session}-{kind}.md")):
                    if path.stat().st_mtime >= since:
                        return True
    except Exception:  # noqa: BLE001 - fail open: unreadable mail is not a reason to hold
        return False
    return False



def _goal_frontier_context(event):
    """Only durable explicit Lead bindings can recover a finished frontier."""
    session = str(event.get("session_id") or event.get("sessionID") or "")
    if not session or event.get("agent_id"):
        return None
    import lhc_plan_control as control
    import lhc_plan_json as plans
    matches = []
    for name in plans.session_plans(session):
        plan = Path(name).resolve()
        try:
            metadata, rows = control.read_plan(plan)
        except (OSError, ValueError, TypeError):
            continue
        def bound(row):
            assignment = row.get("assignment") or {}
            if assignment:
                return (assignment.get("lead") or {}).get("session_id") == session
            return row.get("session") == session
        if not any(bound(row) for row in rows):
            continue
        if not metadata.get("goal") or metadata.get("deliverable", "implementation") != "implementation":
            continue
        _, state, outcome = control.read_context(plan, session, event.get("cwd") or ".", event.get("runtime"))
        if outcome:
            import copy
            import lhc_outcome
            outcome = copy.deepcopy(outcome)
            try:
                outcome["finish_verdict"] = lhc_outcome.verdict(outcome, state)
            except (OSError, ValueError, KeyError, TypeError):
                outcome["finish_verdict"] = "pending"
        view = control.evaluate(metadata, rows, outcome, state, plan_dir=plan)
        matches.append((plan, metadata, rows, outcome, view))
    unfinished = [item for item in matches if item[-1]["goal_status"] not in {"accepted", "superseded"}]
    if unfinished:
        matches = unfinished
    return matches[0] if len(matches) == 1 else None


def _frontier_text(context):
    plan, _metadata, _rows, _outcome, view = context
    decision = view.get("decision") or {}
    text = (f"LHC: plan {plan.name}: goal={view['goal_status']}; frontier={view['frontier']}; "
            f"next decision={view['next_decision']}. ")
    if view["frontier"] in {"admission_unknown", "admission_blocked"}:
        return text + ("Inspect the exact native admission/attempt and existing blocker; runtime unknown is not an exhausted "
                       "goal. Preserve UNKNOWN delivery and actual HumanStop/quota; never replay or dispatch automatically.")
    if view["next_decision"] == "required":
        return text + ("Finished cards do not accept the original goal. Lead compares the saved goal with the actual user result "
                       "and records a concrete permitted next leaf, scoped research/decomposition, or a genuine external wait "
                       "with owner, evidence and resume condition. Respect actual HumanStop/revocation and reconcile UNKNOWN "
                       "delivery without replay. Use lhc_outcome.py bind-plan/frontier for this exact native outcome.")
    if decision:
        return text + f"Owner={decision['owner']}; action={decision['action']}; evidence={decision['evidence']}; " + (
            f"resume condition={decision['resume_condition']}." if decision.get("resume_condition") else
            f"uncertainty={decision['uncertainty']}.")
    return text


def _frontier_stop(event, now):
    """Bounded once-per-frontier advice; never dispatch or reinterpret a Stop."""
    if event.get("human_stop") is True:
        return True, None
    context = _goal_frontier_context(event)
    if context is None:
        return False, None
    view = context[-1]
    if view["next_decision"] in {"human_stop", "wait_external"} or view["goal_status"] in {"accepted", "superseded"}:
        return True, None
    if view["frontier"] not in {"exhausted", "admission_unknown", "admission_blocked"}:
        return False, None
    if event.get("stop_hook_active"):
        return True, None
    if view["next_decision"] == "work":
        return True, None
    session = str(event.get("session_id") or event.get("sessionID"))
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "lhc/pulse"
    mark = base / (re.sub(r"[^A-Za-z0-9_.-]", "_", session) + ".frontier")
    try:
        saved = json.loads(mark.read_text())
    except (OSError, ValueError, TypeError):
        saved = {}
    if now - saved.get("since", now) > STOP_WINDOW:
        saved = {}
    fingerprints = saved.get("fingerprints", [])
    if view["fingerprint"] in fingerprints or len(fingerprints) >= STOP_FIRES:
        return True, None
    try:
        base.mkdir(parents=True, exist_ok=True)
        mark.write_text(json.dumps({"since": saved.get("since", now),
                                    "fingerprints": fingerprints + [view["fingerprint"]]}))
    except OSError:
        return True, None
    return True, _frontier_text(context)

def stop_gate(event, root, now=None):
    if not _strict_workflow():
        return None
    """Hold a stop while the session's plan still has untouched work.

    Facts only: queued or running leaves on disk. The text of the turn is never
    read. "Part done, part not confirmed" is not an end state. The hold is bounded:
    STOP_FIRES reminders for queued leaves; a leaf of this session still running goes on
    holding (also after stop_hook_active) until it is closed (done/blocked/dropped) or a
    question/result letter is on file in .agents/mail, and at most STOP_MAX times a window.
    """
    import time
    session = str(event.get("session_id") or event.get("sessionID") or "")
    if not session or event.get("agent_id"):
        return None
    handled, reason = _frontier_stop(event, now or time.time())
    if handled:
        return reason
    found = _plan_entry(event, root)
    if not found:
        return None
    own = (found.get("continuation") or {}).get("plan")
    pick = own or (found["candidates"][0] if len(found.get("candidates", [])) == 1 else None)
    if not pick:
        return None
    plan = Path(pick)
    files = sorted((plan / "leaves").glob("*.json"))
    now = now or time.time()
    if not files or now - max(f.stat().st_mtime for f in files) > STOP_WINDOW:
        return None
    todo, blocked = [], 0
    rows = {}
    for f in files:
        try:
            leaf = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(leaf, dict):
            rows[str(leaf.get("id") or f.stem)] = leaf
    rows, _stages = _split_leaves(rows)
    running = []
    for ident, leaf in rows.items():
        if leaf.get("status") in {"queued", "running"}:
            todo.append(ident)
            if leaf.get("status") == "running" and leaf.get("session") == session:
                running.append(ident)
        elif leaf.get("status") == "blocked":
            blocked += 1
    if not todo:
        return None
    if event.get("stop_hook_active") and not running:
        return None
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "lhc" / "pulse"
    mark = base / (re.sub(r"[^A-Za-z0-9_.-]", "_", session) + ".stop")
    fires, since = 0, now
    try:
        fires, since = json.loads(mark.read_text())
    except (OSError, ValueError, TypeError):
        pass
    if now - since > STOP_WINDOW:
        fires, since = 0, now
    if fires >= STOP_MAX:
        return None
    if fires >= STOP_FIRES:
        if not running:
            return None
        cwd = event.get("cwd")
        starts = [plan] + ([Path(cwd)] if isinstance(cwd, str) and cwd else [])
        tools = method_root(Path(root).resolve()) / "tools"
        if _escalation_sent(session, starts, now - STOP_WINDOW, tools):
            return None
    try:
        base.mkdir(parents=True, exist_ok=True)
        mark.write_text(json.dumps([fires + 1, since]))
    except OSError:
        return None
    shown = ", ".join(todo[:6]) + (" ..." if len(todo) > 6 else "")
    if fires >= STOP_FIRES:
        last = fires + 1 >= STOP_MAX
        return (f"LHC: leaf {', '.join(running)} of plan {plan.name} is still running: part done, part not confirmed "
                "is not an end state. Close it (done, blocked or dropped in the leaf) or escalate "
                "(python3 src/common/tools/lhc_mail.py send --kind question|result to the duty session or "
                "the chain, with what is done, what is unconfirmed and what you need)."
                + (" This is the last reminder: escalate and stop." if last else ""))
    return (f"LHC: you are stopping, but plan {plan.name} still has {len(todo)} leaves not done ({shown}) "
            f"and {blocked} blocked. Part done, part not confirmed is not an end state. A stop is right when "
            "the business result is reached or only the owner can unblock it. Otherwise do not stop: take the "
            "next queued leaf that is not blocked and work it now; for a blocked leaf send the blocker up the "
            "chain (python3 src/common/tools/lhc_mail.py send to the L, Adviser or Boss) and go on to the "
            "next leaf instead of waiting. Report when the leaves are done or escalated, not when the first "
            "one is stuck.")


def _due(session, key, now, window):
    """True once per window for this session and reminder: the mark is a small state file."""
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "lhc" / "pulse"
    mark = base / (re.sub(r"[^A-Za-z0-9_.-]", "_", session) + "." + key)
    try:
        if now - float(mark.read_text()) < window:
            return False
    except (OSError, ValueError):
        pass
    try:
        base.mkdir(parents=True, exist_ok=True)
        mark.write_text(str(now))
    except OSError:
        return False
    return True


def coordination_pulse(event, root, now=None):
    """Remind the dispatcher of a registry that stands still, and anyone of waiting file mail."""
    import time
    session = str(event.get("session_id") or event.get("sessionID") or "")
    if not session or event.get("agent_id"):
        return None
    tools = method_root(Path(root).resolve()) / "tools"
    mail, orch = sibling_tool(tools, "lhc_mail.py"), sibling_tool(tools, "lhc_dispatcher.py")
    if mail is None or orch is None:
        return None
    try:
        primary = mail.primary_root(Path(event.get("cwd") or "."))
    except (OSError, subprocess.SubprocessError):
        return None
    now = now or time.time()
    notes = []
    registry = orch.reg_file(primary)
    if registry.is_file() and orch.load(primary).get("dispatcher") == session:
        quiet = now - registry.stat().st_mtime
        if quiet >= PULSE_AFTER and _due(session, "registry", now, PULSE_AFTER):
            notes.append(f"LHC: your session registry has not changed for {int(quiet // 60)} min. Run "
                         "python3 src/common/tools/lhc_dispatcher.py tick and act on every line; "
                         "a tick without an action on a session is not a tick.")
    if registry.is_file():
        data = orch.load(primary)
        mr = method_root(Path(root).resolve())
        def role_file(name):
            return next((str(c / f"{name}.md") for c in (mr / "common" / "agents", mr / "src" / "common" / "agents",
                                                           Path(root) / "common" / "agents") if (c / f"{name}.md").is_file()), name + ".md")
        if data.get("dispatcher") == session:
            if _due(session, "dispatcher-role", now, 3600):
                notes.append(f"LHC: the registry names you the dispatcher of this project. You watch the sessions and "
                             f"do not do the work. Read {role_file('Dispatcher')} now. {registry} is the only list of "
                             "sessions (a sessions.md is legacy: carry its live rows over, then stop writing it); act on "
                             "every session through the registry and file mail, and release what they finish.")
        else:
            row = next((r for r in data.get("sessions", []) if r.get("id") == session), None)
            if row and _due(session, "registry-row", now, 1800):
                sentinel = f" Read {role_file('Sentinel')}." if row.get("role") == "sentinel" else ""
                notes.append(f"LHC: you are a row in {registry.name}. Task: {row.get('task')}. Acceptance: "
                             f"{row.get('acceptance')}. Next: {row.get('next')}.{sentinel} Work toward the acceptance and "
                             "tell the dispatcher by file mail (lhc_mail.py send) when it is met or blocked.")
    waiting = mail.inbox(primary, session)
    if registry.is_file() and orch.load(primary).get("dispatcher") == session:
        waiting = sorted(waiting + mail.inbox(primary, "DISPATCHER"), key=lambda p: p.name)  # the role address
    if waiting and _due(session, "mail", now, 600):
        notes.append(f"LHC: {len(waiting)} unread file mail for you. Run python3 src/common/tools/lhc_mail.py "
                     f"inbox --me {session}, act on each, then ack it.")
    return "\n\n".join(notes) or None


def _mail_letters(event):
    """(session, letters) of this session's file mail; letters are (name, sender, kind, body)."""
    session = str(event.get("session_id") or event.get("sessionID") or "")
    if not session or event.get("agent_id"):
        return session, []
    import lhc_mail
    primary = lhc_mail.primary_root(Path(event.get("cwd") or "."))
    letters = []
    for path in lhc_mail.inbox(primary, session):
        head, _, body = path.read_text(encoding="utf-8").partition("\n\n")
        meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
        letters.append((path.name, meta.get("from", "?"), meta.get("kind", ""), body.strip()))
    return session, letters


def mail_context(event, now=None, throttle=0):
    """Put unread file mail into the context: the harness messaging may never reach an idle session.

    Never for a subagent or without a session id; any failure is silent. throttle (seconds) limits how
    often the same session is reminded; SessionStart passes 0.
    """
    import time
    try:
        session, letters = _mail_letters(event)
        if not letters:
            return None
        if throttle and not _due(session, "mailbody", now or time.time(), throttle):
            return None
        rows = []
        for name, sender, kind, body in letters[:3]:
            first = " / ".join(line.strip() for line in body.splitlines() if line.strip())[:400]
            rows.append(f"LHC: you have a letter from {sender} ({kind or 'step'}): {first}. Do it, then ack: "
                        f"python3 src/common/tools/lhc_mail.py ack --me {session} {name}")
        return "\n".join(rows)
    except Exception:  # noqa: BLE001 - fail open
        return None


def mail_stop(event):
    """Hold a Stop once per letter while a task/step letter is not acked; never twice for the same letter."""
    try:
        session, letters = _mail_letters(event)
        todo = [row for row in letters if row[2] in {"task", "step"}]
        if not todo:
            return None
        base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "lhc" / "pulse"
        mark = base / (re.sub(r"[^A-Za-z0-9_.-]", "_", session) + ".mailstop")
        try:
            seen = json.loads(mark.read_text())
        except (OSError, ValueError, TypeError):
            seen = []
        fresh = [row for row in todo if row[0] not in seen]
        if not fresh:
            return None
        base.mkdir(parents=True, exist_ok=True)
        mark.write_text(json.dumps(seen[-200:] + [row[0] for row in fresh]))
        name, sender, kind, body = fresh[0]
        first = " / ".join(line.strip() for line in body.splitlines() if line.strip())[:400]
        return (f"LHC: you are stopping with an unacknowledged {kind} letter from {sender}: {first}. Do not stop: "
                f"run python3 src/common/tools/lhc_mail.py inbox --me {session}, do what it says, then ack: "
                f"python3 src/common/tools/lhc_mail.py ack --me {session} {name}")
    except Exception:  # noqa: BLE001 - fail open
        return None


def context_for(event, root):
    Path(root).resolve()
    return (
        "LHC outcome-first mode. Follow the current human goal and make the smallest useful "
        "vertical slice. Run a focused test and a real canary/readback, then report done or the "
        "exact external blocker. Plans, workers, reviewers, ACKs, receipts, timers and goal "
        "binding are optional telemetry; use them only when the human explicitly asks for a "
        "plan/review or the task has genuinely independent release lanes. Keep only effect-level "
        "guards for secrets, target ownership, unknown mutations, shared writes and human STOP."
    )

def owner_directives(cwd):
    """The live owner directives of this project, or an empty string. Never raises."""
    try:
        import lhc_directives
        return lhc_directives.session_context(Path(cwd))
    except Exception:  # noqa: BLE001 - a hook must not fail a session
        return ""


def package_version(root):
    for rel in (".codex-plugin/plugin.json", "plugin.json", "plugins/last-human-commit/plugin.json"):
        p = root/rel
        if p.is_file():
            return str(json.loads(p.read_text()).get("version", "unknown"))
    return "source"

def method_root(root):
    return root/"common" if (root/"common/tools/lhc_time_guard.py").is_file() else root/"src/common"

PLAN_FILES = ("plan.graph.json", "plan.report.md")
# The leaf files of a plan: one file per leaf, named after the leaf.
LEAVES_DIRNAME = "leaves"


class PlanBuildError(ValueError):
    """The leaves of a plan cannot be collected into one graph."""


def written_paths(event):
    """The paths a tool has just written, as far as the event shows them."""
    found = []

    def walk(value, depth=0):
        if depth > 4:
            return
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)

    if isinstance(event, dict):
        for key in ("tool_input", "toolInput", "tool_response", "input", "arguments", "files", "paths"):
            if key in event:
                walk(event[key])
    return found


def leaf_plan_dir(path):
    """The plan directory of a leaf file, or None when the path is not a leaf."""
    if path.suffix.lower() != ".json" or path.parent.name != LEAVES_DIRNAME:
        return None
    return path.parent.parent


# The sibling tools this entry runs in its own process instead of starting an
# interpreter for them.  One entry per path, so a tool is loaded once.
_TOOLS = {}


def sibling_tool(tools, name):
    """One sibling tool of the canon, loaded into this process.

    The tool is loaded by the path it has in the package, the way the
    command line would have run it, so the answer of the process is the
    answer of this process.  None when the tool cannot be loaded, and then
    the caller keeps the answer it had.
    """
    key = str(Path(tools) / name)
    cached = _TOOLS.get(key)
    if cached is not None:
        return cached
    path = Path(key)
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("lhc_entry_%s_sibling" % path.stem, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        # The module is known to the interpreter before it runs: a tool that
        # declares its own types looks itself up while it is loaded.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop("lhc_entry_%s_sibling" % path.stem, None)
        return None
    _TOOLS[key] = module
    return module


def rebuild_plan_graph(plan_dir, tools):
    """Collect the leaves of one plan into its plan.graph.json.

    The leaf files are the source of truth of a plan, so the graph is rebuilt
    from them before the page is rendered. A leaf that cannot be read is named
    and the build stops: a broken leaf never becomes a missing leaf.
    """
    collector = Path(tools) / "lhc_plan_json.py"
    if not collector.is_file() or not (Path(plan_dir) / LEAVES_DIRNAME).is_dir():
        return None
    module = sibling_tool(tools, "lhc_plan_json.py")
    if module is None:
        raise PlanBuildError(f"{plan_dir}: сборщик листов не запустился: нет сборщика листов")
    try:
        module.build_graph(Path(plan_dir))
    except (OSError, ValueError) as error:
        # The collector names the leaf it cannot collect; the answer of the
        # command line is that name, and this process gives the same name.
        raise PlanBuildError(f"LHC: {error}") from error
    return Path(plan_dir) / "plan.graph.json"


def stamp_leaf(path, now=None):
    """Record when a leaf started and finished, the first time its file shows the status.

    Agents move statuses and forget the clock, so the plan page had no effort
    to show for any leaf. The hook already sees every leaf write; it adds the
    time of that write and nothing else, and never overwrites a time the agent
    set itself.
    """
    try:
        leaf = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(leaf, dict):
        return
    stamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    status, changed = leaf.get("status"), False
    if status == "running" and not leaf.get("started_at"):
        leaf["started_at"], changed = stamp, True
    if status == "done" and not leaf.get("finished_at"):
        leaf["finished_at"], changed = stamp, True
    if not changed:
        return
    temporary = path.with_name(path.name + ".stamp")
    try:
        temporary.write_text(json.dumps(leaf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)


def plan_audit(event, root, now=None):
    """Facts about the plan the session works on that cannot be true at once.

    A leaf that is done or running while a leaf it depends on is not done, and a
    plan with dependency edges whose decomposition nobody checked. Told once per
    window; nothing is blocked and no text is read.
    """
    import time
    session = str(event.get("session_id") or event.get("sessionID") or "")
    if not session or event.get("agent_id"):
        return None
    found = _plan_entry(event, root)
    if not found:
        return None
    own = (found.get("continuation") or {}).get("plan")
    pick = own or (found["candidates"][0] if len(found.get("candidates", [])) == 1 else None)
    if not pick:
        return None
    plan = Path(pick)
    leaves = {}
    for f in sorted((plan / "leaves").glob("*.json")):
        try:
            leaf = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(leaf, dict):
            leaves[str(leaf.get("id") or f.stem)] = leaf
    leaves, stages = _split_leaves(leaves)
    now = now or time.time()
    notes = []
    broken = []
    for ident, leaf in leaves.items():
        if leaf.get("status") not in {"running", "done"}:
            continue
        waiting = [d for d in (leaf.get("depends_on") or []) if leaves.get(str(d), {}).get("status") != "done"]
        if waiting:
            broken.append(f"{ident} is {leaf.get('status')} while {', '.join(map(str, waiting))} it depends on "
                          f"{'is' if len(waiting) == 1 else 'are'} not done")
    if broken and _due(session, "audit-deps", now, PULSE_AFTER):
        notes.append("LHC: the plan contradicts itself: " + "; ".join(broken[:4]) + ". Either the status is wrong "
                     "(a leaf is done only when what it depends on is done) or the dependency is: if the leaf does "
                     "not read the output of the leaf it waits for, remove that dependency and let them run in parallel.")
    try:
        meta = json.loads((plan / "plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    late = []
    origin_at = ((meta or {}).get("plan_origin") or {}).get("at")
    for ident, leaf in leaves.items():
        if leaf.get("status") != "running":
            continue
        try:
            import lhc_plan_json
            over = lhc_plan_json.overrun(leaf, now=now, fallback_start=origin_at if len(leaves) == 1 else None)
        except Exception:  # noqa: BLE001 - a leaf without times is not late
            over = None
        if over:
            late.append(f"{ident} has run {over[0]} min against an estimate of {over[1]} min")
    if late and _due(session, "audit-overrun", now, 900):
        notes.append("LHC: " + "; ".join(late[:3]) + ". Split it now: close what is proven as done with its "
                     "result, put the rest into new leaves, one leaf per object (environment, host, service), and "
                     "start the independent ones in parallel. Until it is split the tool refuses progress notes on it.")
    cap = _plan_leaf_cap(meta)
    big = [f"{ident} ({int(high)} min)" for ident, leaf in leaves.items()
           if leaf.get("kind") != "milestone" and leaf.get("status") not in {"done", "deferred", "deferred_ai"}
           and not leaf.get("estimate_over_limit_reason")
           for high in [_estimate_max(leaf)] if high and high > cap]
    if big and _due(session, "audit-cap-" + plan.name + "-" + re.sub(r"[^A-Za-z0-9]+", "-", "-".join(sorted(big))),
                    now, 6 * 3600):
        notes.append(f"LHC: this plan's leaf cap is {cap} minutes and these are longer: " + "; ".join(big[:4]) +
                     f". Split each into leaves of at most {cap} minutes. If you cannot yet name what the parts are, "
                     "it is a stage: make it a milestone (kind: milestone), make the first leaf a bounded look at the "
                     "facts (a list, a command output), then cut the stage into leaves from what you found (parent: its "
                     "id). One leaf per object (environment, host, service).")
    pending = []
    for index, stage in enumerate(stages):
        if stage["children"] or stage["status"] in {"done", "deferred", "deferred_ai"}:
            continue
        if all(other["status"] in {"done", "deferred", "deferred_ai"} for other in stages[:index]):
            pending.append(stage["id"])
        break
    if pending and _due(session, "audit-stage-" + plan.name + "-" + pending[0], now, 3600):
        notes.append(f"LHC: {pending[0]} is a milestone with no leaves and it is the next one. Cut it into leaves of "
                     f"at most {cap} minutes now, from facts: if you cannot name the parts, the first leaf is a bounded "
                     "look at what is there. Give the leaves parent: " + pending[0] + ". A milestone is not worked on itself.")
    return "\n\n".join(notes) or None


def render_written_plan(event, root):
    """Rebuild the page of the plan that has just been written.

    The agent writes the plan; the page is generated from it by this hook. The
    agent does not have to remember a command, and the page can never describe
    a plan that is older than the plan itself.

    A leaf file is the source of truth of its leaf, so writing one rebuilds the
    graph of the whole plan from the leaves and then rebuilds the page. The
    chain never loops: the hook reacts to the files the agent wrote, and the
    files the hook writes are not part of that event.

    The root arrives as a Path or as plain text — a caller that reads it from
    a config value must not pay a TypeError for it.
    """
    root = Path(root)
    tools = root / "tools" if (root / "tools" / "lhc_grid.py").is_file() else method_root(root) / "tools"
    tool = tools / "lhc_grid.py"
    if not tool.is_file():
        return None
    base = Path(event.get("cwd") or ".").expanduser() if isinstance(event, dict) else Path(".")
    for raw in written_paths(event):
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = base / path
        directory = leaf_plan_dir(path)
        if directory is not None:
            stamp_leaf(path)
            graph = rebuild_plan_graph(directory, tools)
            if graph is None:
                continue
        elif path.name in PLAN_FILES:
            directory = path.parent
            graph = directory / "plan.graph.json"
            if not graph.is_file():
                continue
        else:
            continue
        module = sibling_tool(tools, "lhc_grid.py")
        if module is None:
            return None
        try:
            # The renderer names the files it wrote; the command line of the
            # renderer kept that answer to itself, and this process does the
            # same.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                module.main(["render", str(graph), "--out-dir", str(directory)])
        except (OSError, subprocess.SubprocessError, ValueError):
            return None
        return directory
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default="SessionStart")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--instructions-only", action="store_true",
                        help="emit optional plan intake when the owner explicitly asks for a plan")
    parser.add_argument("--heartbeat-only", action="store_true",
                        help="record only an isolated wall-time reminder at PostToolUse")
    parser.add_argument("--git-guard", action="store_true",
                        help="at PreToolUse, refuse git stash everywhere and a branch switch in the primary checkout")
    parser.add_argument("--stop-gate", action="store_true",
                        help="at Stop, hold the turn while the plan still has untouched leaves, or once per 30 min without requiring a Boss review")
    parser.add_argument("--plan-entry", action="store_true",
                        help="emit optional planning intake; ordinary prompts remain untouched")
    default_runtime = ("zcode" if os.environ.get("ZCODE_PLUGIN_ROOT") else
                       "claude" if os.environ.get("CLAUDE_PROJECT_DIR") else "codex")
    parser.add_argument("--runtime", choices=("codex", "claude", "opencode", "zcode"), default=default_runtime)
    args = parser.parse_args()
    if args.git_guard:
        if not _strict_workflow():
            return
        if args.event != "PreToolUse":
            return
        try:
            raw = sys.stdin.read(8 * 1024 * 1024 + 1)
            event = json.loads(raw or "{}") if len(raw) <= 8 * 1024 * 1024 else {}
            if not isinstance(event, dict):
                return
            import lhc_git_guard
            reason = lhc_git_guard.check(lhc_git_guard.command_of(event), str(event.get("cwd") or os.getcwd()))
        except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError):
            return  # fail open: a guard that cannot decide never blocks
        if reason:
            print(json.dumps({"decision": "block", "reason": reason,
                              "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": reason}}, ensure_ascii=False))
        return
    if args.heartbeat_only:
        if not _verbose_workflow():
            return
        if args.event != "PostToolUse":
            return
        try:
            raw = sys.stdin.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                return
            event = json.loads(raw or "{}")
            if not isinstance(event, dict):
                return
            cwd_value = event.get("cwd")
            session_id = event.get("session_id") or event.get("sessionID")
            if not isinstance(cwd_value, str) or not isinstance(session_id, str):
                return
            if event.get("agent_id"):
                session_id += ":subagent:" + str(event["agent_id"])
            # The page of the plan is rebuilt before the heartbeat: the plan is
            # the owner's artefact, the reminder is the agent's.
            build_error = None
            try:
                hook_root = (args.root or Path(__file__).resolve().parents[1]).resolve()
                rendered = render_written_plan(event, hook_root)
            except PlanBuildError as error:
                # A leaf that cannot be collected is named: a broken leaf must
                # not pass as a missing one.
                rendered = None
                build_error = str(error)
            except (OSError, ValueError, KeyError, TypeError, NameError, AttributeError,
                    subprocess.SubprocessError):
                rendered = None
            if rendered is not None:
                print(json.dumps({"systemMessage":
                                  f"LHC: страница плана пересобрана из {rendered.name}"},
                                 ensure_ascii=False))
            elif build_error:
                print(json.dumps({"systemMessage":
                                  f"LHC: план не пересобран: {build_error}"},
                                 ensure_ascii=False))
            import lhc_time_guard
            project = Path(cwd_value).expanduser()
            # The 120-minute learning checkpoint runs first: it creates the shared
            # learning state (including "last_observed_at") that the heartbeat reads
            # and then preserves as a sibling key. Running the heartbeat first left
            # the state without that field, so the checkpoint raised KeyError and
            # every time reminder was swallowed for every harness.
            # The checkpoint is time-only as well: it observes a wall deadline and
            # never reads, classifies or vetoes anything.
            learning = lhc_time_guard.learning_checkpoint(
                argparse.Namespace(runtime=args.runtime, now=None), project, session_id)
            result = lhc_time_guard.native_heartbeat(project, args.runtime, session_id)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            return
        prompts = []
        if result and result.get("prompt"):
            prompts.append(result["prompt"])
        if learning and learning.get("prompt"):
            prompts.append(learning["prompt"])
        letters = mail_context(event, throttle=300)
        if letters:
            prompts.append(letters)
        try:
            coordination = coordination_pulse(event, args.root or Path(__file__).resolve().parents[1])
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            coordination = None
        if coordination:
            prompts.append(coordination)
        try:
            audit = plan_audit(event, args.root or Path(__file__).resolve().parents[1])
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            audit = None
        if audit:
            prompts.append(audit)
        if result and result.get("due"):
            extra = owner_directives(cwd_value)
            if extra:
                prompts.append(extra)
        if prompts:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n\n".join(prompts),
            }}, ensure_ascii=False))
        return
    if args.stop_gate:
        if not _strict_workflow() or args.event != "Stop":
            return
        try:
            raw = sys.stdin.read(8 * 1024 * 1024 + 1)
            event = json.loads(raw or "{}") if len(raw) <= 8 * 1024 * 1024 else {}
            hook_root = args.root or Path(__file__).resolve().parents[1]
            reason = (mail_stop(event) or stop_gate(event, hook_root)) if isinstance(event, dict) else None
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            reason = None
        if reason:
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return
    if args.plan_entry:
        if args.event != "UserPromptSubmit":
            return
        try:
            raw = sys.stdin.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                return
            event = json.loads(raw or "{}")
            if not isinstance(event, dict):
                return
            result = _plan_entry(event, args.root or Path(__file__).resolve().parents[1])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError,
                PlanBuildError, subprocess.SubprocessError):
            result = None
        context = context_for(args.event, args.root or Path(__file__).resolve().parents[1])
        if result:
            extra = _plan_context(result)
            if extra:
                context += " " + extra
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }}, ensure_ascii=False))
        return
    # Native hooks only activate the project instructions. Stateful outcome,
    # review and status behavior stays behind the explicit CLI commands.
    # Legacy hook invocations without this flag are intentionally inert.
    if not args.instructions_only or args.event not in {"SessionStart", "PostCompact"}:
        return
    if args.event == "SessionStart":
        try:
            restore_codex_routes()
        except Exception:  # noqa: BLE001 - fail open: routes are a repair, never a reason to stop
            pass
    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    context = context_for(args.event, root)
    extra = owner_directives(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if extra:
        context += "\n\n" + extra
    if args.event == "SessionStart" and _verbose_workflow():
        try:
            import lhc_backlog
            due = lhc_backlog.session_block(Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))
        except Exception:  # noqa: BLE001 - fail open: an optional reminder
            due = ""
        if due:
            context += "\n\n" + due
    start = None
    try:
        import select
        if not sys.stdin.isatty():
            try:
                ready = select.select([sys.stdin], [], [], 0.5)[0]
            except (ValueError, OSError, io.UnsupportedOperation):
                ready = True  # not a descriptor (an in-process caller): read it directly
            if ready:
                start = json.loads(sys.stdin.read(1024 * 1024) or "{}")
    except Exception:  # noqa: BLE001 - fail open
        start = None
    if not _verbose_workflow():
        start = None
    if isinstance(start, dict):
        try:
            resume = plan_resume_context(start, root)
        except Exception:  # noqa: BLE001 - fail open: without the plan the instructions still go out
            resume = None
        if resume:
            context += "\n\n" + resume
        if args.event == "SessionStart":
            try:
                letters = mail_context(start)
            except Exception:  # noqa: BLE001 - fail open
                letters = None
            if letters:
                context += "\n\n" + letters
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": args.event,
        "additionalContext": context,
    }}, ensure_ascii=False))
    return

if __name__ == "__main__": main()
