#!/usr/bin/env python3
"""Emit idempotent hourly and estimate-overrun business-control prompts."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BUSINESS_FIRST_HEADER = "Less process overhead, more business results."
MAX_HANDOFF_TASK_CHARS = 16_000
MAX_NATIVE_HANDOFF_CHARS = 16_000
MAX_HANDOFF_PLAN_CHARS = 8_000
STARTED_AT = re.compile(
    r"^\s*(?:-\s*)?Started at(?:\s*\(UTC\+3\))?:\s*([^\s(]+)",
    re.MULTILINE | re.IGNORECASE,
)
INITIAL_ESTIMATE = re.compile(
    r"^\s*(?:-\s*)?Initial estimate(?:\s*\(minimum\s*/\s*maximum\s+active minutes\))?:\s*"
    r"(\d+)\s*/\s*(\d+)(?:\s+active minutes)?",
    re.MULTILINE | re.IGNORECASE,
)
ACTIVE_MINUTES = re.compile(
    r"^\s*-\s*(?:Active minutes|Actual active minutes):\s*(\d+)",
    re.MULTILINE | re.IGNORECASE,
)
HERDER_ENVELOPE = re.compile(
    r'<agent-herder-(?:coordination|repo-peers)\b[^>]*>.*?</agent-herder-(?:coordination|repo-peers)\s*>',
    re.IGNORECASE | re.DOTALL,
)


def prompt_excerpt(value: str) -> str:
    """Keep Herder coordination metadata out of repeated task reminders."""

    return HERDER_ENVELOPE.sub("", value).strip()


STATUS_OR_ACK_PROMPT = re.compile(
    r"^\s*(?:status|progress|update|any news|any update|how is it going|"
    r"ack(?:nowledged)?|ok(?:ay)?|thanks?(?:,\s*got it)?|got it|понятно|принято|спасибо|статус|"
    r"как дела|есть новости)\b\s*[:.!?…-]*\s*$|"
    r"^\s*(?:status|progress|update|any news|any update|how is it going|статус|как дела|есть новости)\s*[:?].*$",
    re.I | re.S,
)
EXPLICIT_RESUME = re.compile(
    r"^\s*(?:(?:please|yes|okay|ok|пожалуйста|да|хорошо)\s+)*(?:resume|continue|carry on|"
    r"proceed with|go ahead with|возобнови|продолжай|продолжи|продолжай с|вернись к)\b",
    re.I,
)
RESUME_PREVIOUS_TASK = re.compile(r"\b(?:previous|original|current|paused)\s+(?:task|work|request)\b|(?:исходн|текущ|прерван).{0,20}(?:задач|работ)", re.I)
RESUME_DEFERRED_OR_NEGATED = re.compile(
    r"\b(?:only\s+after|until|unless|when\s+(?:i|we)\s+(?:say|approve|confirm)|"
    r"if\s+(?:i|we)\s+(?:say|approve|confirm)|for\s+now\b.{0,60}\b(?:stop|stopp?ed|pause|paused|hold)|"
    r"(?:do\s+not|don't|never)\s+(?:resume|continue|proceed)|"
    r"keep\s+(?:it|this|the\s+(?:task|work))\s+(?:stopped|paused|on\s+hold)|"
    r"только\s+после|пока\s+не|до\s+(?:моего\s+)?(?:одобрени\w*|разрешени\w*)|"
    r"если\s+(?:я|мы)\s+(?:одобр\w*|разреш\w*|скажу)|"
    r"когда\s+(?:я|мы)\s+(?:скажу|одобр\w*|разреш\w*)|"
    r"не\s+(?:продолжай|продолжи|возобновляй|возобнови|делай)|"
    r"(?:оставь|держи)\s+(?:это\s+)?(?:остановленн\w*|приостановленн\w*|на\s+паузе))\b",
    re.I,
)
GENERIC_TASK_WORDS = {
    "please", "yes", "okay", "ok", "the", "a", "an", "now", "with", "to", "on", "and", "for",
    "task", "work", "request", "original", "current", "previous", "paused", "continue", "resume",
    "carry", "proceed", "ahead", "that", "this", "it", "мы", "это", "задачу", "задача", "работу",
    "работа", "исходную", "текущую", "прерванную", "продолжай", "продолжи", "возобнови", "пожалуйста",
}


def prompt_metadata(prompt: str) -> tuple[str, str]:
    """Use the outcome parser's exact transport framing for raw native prompts."""
    import lhc_outcome

    return lhc_outcome.source_origin(prompt), lhc_outcome.semantic_scope(prompt)


def _semantic_text(prompt: str) -> str:
    import lhc_outcome

    return lhc_outcome.semantic_scope(prompt).strip()


def prompt_can_resume_hold(prompt: str, active_prompt: str | list[str] | tuple[str, ...], *,
                           hold: str | None = None, origin: str | None = None) -> bool:
    """Only a fresh, unmarked, substantive native prompt resumes manual holds."""
    import lhc_outcome

    if not isinstance(prompt, str) or not prompt.strip():
        return False
    origin = origin or lhc_outcome.source_origin(prompt)
    if origin == "agent-relay":
        return False
    scope = lhc_outcome.semantic_scope(prompt)
    if not scope or STATUS_OR_ACK_PROMPT.fullmatch(scope.strip()):
        return False
    active_prompts = active_prompt if isinstance(active_prompt, (list, tuple)) else (active_prompt,)
    active_scopes = {lhc_outcome.semantic_scope(value).strip() for value in active_prompts if value}
    if scope.strip() in active_scopes:
        return False
    # Manual Interrupt/SessionEnd holds require an explicit continuation of
    # that paused work. A new unrelated task is not implicit permission to
    # resume. Tool failures retain the established direct-prompt recovery path.
    if hold in {"Interrupt", "SessionEnd", "session.error"}:
        if not EXPLICIT_RESUME.match(scope):
            return False
        if RESUME_DEFERRED_OR_NEGATED.search(scope):
            return False
        if RESUME_PREVIOUS_TASK.search(scope):
            return True
        words = {word.casefold() for word in re.findall(r"[\w'-]+", scope) if len(word) >= 4}
        words -= GENERIC_TASK_WORDS
        active_words = set()
        for value in active_scopes:
            active_words.update(word.casefold() for word in re.findall(r"[\w'-]+", value) if len(word) >= 4)
        active_words -= GENERIC_TASK_WORDS
        return bool(words & active_words)
    return True


def prompt_should_promote_latest(prompt: str, business: dict, *, origin: str | None = None) -> bool:
    """Keep captured transport rows while excluding relays/status/old duplicates from active scope."""
    import lhc_outcome

    if not isinstance(prompt, str) or not prompt.strip():
        return False
    origin = origin or lhc_outcome.source_origin(prompt)
    if origin == "agent-relay" and business.get("original_prompt"):
        return False
    scope = lhc_outcome.semantic_scope(prompt).strip()
    if not scope or STATUS_OR_ACK_PROMPT.fullmatch(scope):
        return False
    original = lhc_outcome.semantic_scope(
        business.get("original_prompt_full") or business.get("original_prompt") or ""
    ).strip()
    latest = lhc_outcome.semantic_scope(
        business.get("latest_prompt_full") or business.get("latest_prompt") or ""
    ).strip()
    if scope == latest:
        return False
    if original and scope == original and latest and latest != original:
        return False
    return True


def active_business_prompts(business: dict) -> tuple[str, str]:
    """Derive active task text without promoting stored relay/status contamination."""
    import lhc_outcome

    original_raw = business.get("original_prompt_full") or business.get("original_prompt") or ""
    original = (business.get("original_scope_prompt") or lhc_outcome.semantic_scope(original_raw)).strip()
    latest_raw = business.get("latest_prompt_full") or business.get("latest_prompt") or ""
    latest = _eligible_active_scope(latest_raw, business, original,
                                    scope_hint=business.get("latest_scope_prompt"))
    if latest and latest != original:
        return original, latest
    context = business.get("execution_context") or {}
    for row in reversed(context.get("direct_user_messages") or []):
        if not isinstance(row, dict):
            continue
        raw = row.get("prompt", "")
        candidate = _eligible_active_scope(raw, business, original, origin=row.get("origin"),
                                           scope_hint=row.get("scope_prompt"))
        if candidate and candidate != original:
            return original, candidate
    return original, ""


def _eligible_active_scope(prompt: str, business: dict, original: str, *, origin: str | None = None,
                           scope_hint: str | None = None) -> str:
    import lhc_outcome

    if not isinstance(prompt, str) or not prompt.strip():
        return ""
    origin = origin or lhc_outcome.source_origin(prompt)
    scope = lhc_outcome.semantic_scope(prompt_excerpt(scope_hint or prompt)).strip()
    if (origin == "agent-relay" or not scope or STATUS_OR_ACK_PROMPT.fullmatch(scope) or
            scope == original):
        return ""
    return scope


def capture_native_dispatch(business: dict, payload: dict, parent_logical_id: str,
                            observed_at: str) -> None:
    """Retain only exact native spawn pre-call text; it is pending until child join."""
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or payload.get("tool") or "")
    if not (tool_name == "spawn_agent" or tool_name.endswith("spawn_agent")):
        return
    call_id = (payload.get("tool_call_id") or payload.get("tool_use_id") or payload.get("toolUseId")
               or payload.get("toolUseID") or payload.get("call_id") or payload.get("callId"))
    if not isinstance(call_id, str) or not call_id.strip():
        business["native_dispatch_capture_error"] = "spawn pre-call has no native tool call id"
        return
    import lhc_native_identity

    parent_journal = payload.get("transcript_path") or payload.get("transcriptPath")
    tool_input = payload.get("tool_input")
    if tool_input is None:
        tool_input = payload.get("arguments")
    if tool_input is None:
        tool_input = payload.get("input")
    try:
        record = lhc_native_identity.capture_spawn_intent(
            parent_logical_id, parent_journal_path=parent_journal,
            tool_name=tool_name, tool_call_id=call_id, tool_input=tool_input,
            observed_at=observed_at,
        )
        record["join_status"] = "pending"
        business["native_dispatches"] = lhc_native_identity.merge_dispatch_records(
            business.get("native_dispatches", []), record
        )
        business.pop("native_dispatch_capture_error", None)
    except (OSError, TypeError, ValueError) as exc:
        errors = business.setdefault("native_dispatch_errors", [])
        error = {"call_id": call_id, "reason": f"{type(exc).__name__}: {str(exc)[:256]}",
                 "observed_at": observed_at}
        existing = next((row for row in errors if row.get("call_id") == call_id), None)
        if existing is None and len(errors) < 64:
            errors.append(error)
        elif existing is not None and existing.get("reason") != error["reason"]:
            business["native_dispatch_capture_error"] = "conflicting unavailable pre-call for an existing tool id"
        elif len(errors) >= 64 and existing is None:
            business["native_dispatch_capture_error"] = "dispatch capture error capacity reached; no entries were evicted"


def resolve_native_child_assignment(event: dict, logical_session_id: str,
                                    runtime: str, observed_native_cwd: Path) -> dict:
    """Verify a child against its exact parent journal, native receipt and captured intent."""
    import lhc_native_identity

    parent_native_id = str(event.get("session_id") or event.get("sessionID") or "")
    child_native_id = str(event.get("agent_id") or "")
    if not parent_native_id or not child_native_id:
        return {"verified": False, "status": "unavailable", "reason": "native parent or child id is missing"}
    try:
        parent_journal = lhc_native_identity.find_native_journal(parent_native_id)
        parent_header = lhc_native_identity.read_native_header(parent_journal)
        child_journal = event.get("transcript_path") or event.get("transcriptPath")
        if not child_journal:
            child_journal = lhc_native_identity.find_native_journal(child_native_id)
        parent_state_path = learning_path(Path(parent_header["native_cwd"]), runtime, parent_native_id)
        parent_state = load_state(parent_state_path) or {}
        parent_business = parent_state.get("business", {})
        identity = lhc_native_identity.resolve_child_identity(
            logical_session_id, parent_journal, child_journal,
            observed_native_cwd=os.fspath(observed_native_cwd),
            captured_intents=parent_business.get("native_dispatches", []),
        )
        identity["parent_state_path"] = os.fspath(parent_state_path)
        return identity
    except (OSError, TypeError, ValueError) as exc:
        return {"verified": False, "status": "unavailable",
                "parent_native_id": parent_native_id, "native_id": child_native_id,
                "reason": f"{type(exc).__name__}: {str(exc)[:256]}"}


def parse_time(value: str) -> datetime:
    """Parse one timezone-aware ISO-8601 timestamp."""

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def non_negative(value: str) -> int:
    """Parse one non-negative integer CLI value."""

    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def positive(value: str) -> int:
    """Parse one positive integer CLI value."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def load_state(path: Path) -> dict[str, Any] | None:
    """Load existing JSON state, returning None when the cycle is new."""

    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("time-guard state must be a JSON object")
    return value


def write_state(path: Path, value: dict[str, Any]) -> None:
    """Atomically persist one cycle state beside its final path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_text(path: Path, value: str) -> None:
    """Atomically replace one UTF-8 text file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def list_line(label: str, values: list[str], empty: str) -> str:
    """Render one compact diagnostic line from repeated CLI values."""

    return f"{label}: {', '.join(values) if values else empty}"


def render_prompt(
    *,
    events: list[str],
    state: dict[str, Any],
    active_minutes: int,
    wall_minutes: int,
    business_delta: str,
    completed_tasks: list[str],
    completed_files: list[str],
    gates: list[str],
    instructions: list[str],
    controlled: str,
    route_changed: str,
    active_source: str,
) -> str:
    """Render the Russian Lead-facing control prompt for new events."""

    if not events:
        return ""

    planned = state["planned_minutes"]
    active_note = {
        "reported": "explicitly supplied by caller",
        "task-card": "explicitly recorded in task card",
        "hook-observed": "hook-observed; exact active time was not measured",
        "interval-ledger": "explicit monotonic intervals; open interval is provisional",
    }[active_source]
    lines = [
        BUSINESS_FIRST_HEADER,
        f"Cycle: {state['cycle_id']}",
        (
            "Plan: "
            f"{planned['minimum']}–{planned['maximum']} active minutes; "
            f"actual: {active_minutes} active ({active_note}) / "
            f"{wall_minutes} wall-clock minutes."
        ),
        "Which real tasks were completed?",
        list_line("Completed tasks", completed_tasks, "not specified"),
        f"Actual business delta: {business_delta or 'not specified'}",
        "List all completed files.",
        list_line("Completed files", completed_files, "not specified"),
        "What is blocking progress?",
        list_line("Which gates delayed progress?", gates, "not specified"),
        list_line(
            "Which instructions caused safety process overhead instead of business progress?",
            instructions,
            "not specified",
        ),
        "How much time was planned and actually spent?",
        f"Did you track it? Answer: {controlled}.",
    ]

    if "overrun" in events:
        lines.extend(
            [
                (
                    "Original maximum exceeded by: "
                    f"{max(0, active_minutes - planned['maximum'])} active minutes."
                ),
                (
                    "Why did the task overrun without changing approach "
                    "while doing extra process instead of business work?"
                ),
                f"Route already changed: {route_changed}.",
                "What changes in the route now?",
            ]
        )

    if "estimate_mutation" in events:
        lines.append(
            "Do not legitimize the old route by replacing the estimate; "
            "original minimum/maximum remain the checkpoint."
        )

    lines.append(
        "Do not weaken mandatory safety, secrecy, user "
        "authority or destructive-action boundaries; remove only process "
        "unneeded for the current business result."
    )
    return "\n".join(lines)


def check(args: argparse.Namespace) -> dict[str, Any]:
    """Evaluate one cycle, persist new event markers, and return a JSON result."""

    now = args.now or datetime.now().astimezone()
    if now < args.started_at:
        raise ValueError("now must not precede started-at")
    if args.minimum_minutes > args.maximum_minutes:
        raise ValueError("minimum-minutes must not exceed maximum-minutes")

    state = load_state(args.state)
    if state is None:
        state = {
            "schema_version": 1,
            "cycle_id": args.cycle_id,
            "started_at": args.started_at.isoformat(),
            "planned_minutes": {
                "minimum": args.minimum_minutes,
                "maximum": args.maximum_minutes,
            },
            "reported_hours": 0,
            "overrun_reported": False,
            "estimate_mutations": [],
        }
    elif state.get("cycle_id") != args.cycle_id:
        raise ValueError("state cycle-id does not match the requested cycle")

    wall_minutes = int((now - args.started_at).total_seconds() // 60)
    crossed_hour = wall_minutes // 60
    previous_hour = int(state.get("reported_hours", 0))
    crossed_hours = list(range(previous_hour + 1, crossed_hour + 1))
    events: list[str] = []
    if crossed_hours:
        events.append("hourly")
        state["reported_hours"] = crossed_hour

    planned = state["planned_minutes"]
    requested = {"minimum": args.minimum_minutes, "maximum": args.maximum_minutes}
    mutation_key = f"{args.minimum_minutes}:{args.maximum_minutes}"
    mutations = state.setdefault("estimate_mutations", [])
    if requested != planned and mutation_key not in mutations:
        events.append("estimate_mutation")
        mutations.append(mutation_key)

    overrun_minutes = max(0, args.active_minutes - int(planned["maximum"]))
    if overrun_minutes > 0 and not state.get("overrun_reported", False):
        events.append("overrun")
        state["overrun_reported"] = True

    state["last_checked_at"] = now.isoformat()
    state["last_active_minutes"] = args.active_minutes
    write_state(args.state, state)

    prompt = render_prompt(
        events=events,
        state=state,
        active_minutes=args.active_minutes,
        wall_minutes=wall_minutes,
        business_delta=args.business_delta,
        completed_tasks=args.completed_task,
        completed_files=args.completed_file,
        gates=args.gate,
        instructions=args.instruction,
        controlled=args.controlled,
        route_changed=args.route_changed,
        active_source=args.active_source,
    )
    return {
        "active_minutes": args.active_minutes,
        "crossed_hours": crossed_hours,
        "cycle_id": args.cycle_id,
        "events": events,
        "overrun_minutes": overrun_minutes,
        "planned_minutes": planned,
        "prompt": prompt,
        "state": str(args.state),
        "wall_minutes": wall_minutes,
    }


def find_active_task(cwd: Path) -> tuple[Path, datetime, int, int, int | None] | None:
    """Find the newest usable work card in cwd or one of its parents."""

    for root in (cwd, *cwd.parents):
        tasks = root / ".agents" / "tasks"
        if not tasks.is_dir():
            continue
        candidates = sorted(
            tasks.glob("work-*.md"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for card in candidates:
            text = card.read_text(encoding="utf-8")
            started = STARTED_AT.search(text)
            estimate = INITIAL_ESTIMATE.search(text)
            if started is None or estimate is None:
                continue
            explicit_active = ACTIVE_MINUTES.findall(text)
            try:
                started_at = parse_time(started.group(1))
            except (ValueError, argparse.ArgumentTypeError):
                continue
            return (
                card,
                started_at,
                int(estimate.group(1)),
                int(estimate.group(2)),
                int(explicit_active[-1]) if explicit_active else None,
            )
    return None


def safe_session_id(payload: dict[str, Any]) -> str:
    """Return a filesystem-safe native session identity without inventing one."""

    raw = str(payload.get("session_id") or payload.get("sessionID") or "unknown-session")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-.")
    return safe[:120] or "unknown-session"


def find_agents_root(cwd: Path) -> Path | None:
    """Find the nearest project-local .agents root."""

    for root in (cwd, *cwd.parents):
        candidate = root / ".agents"
        if candidate.is_dir():
            return candidate
    return None


def git_snapshot(cwd: Path) -> str:
    """Return bounded branch/HEAD/changed-file continuity evidence."""

    repository = _git_worktree_root(cwd)
    branch = _git_current_branch(cwd)
    lines: list[str] = [
        f"Repository:\n{repository if repository is not None else 'unavailable'}",
        f"Branch:\n{branch if branch is not None else 'unavailable'}",
    ]
    for label, command in (
        ("HEAD", ["git", "rev-parse", "--short=12", "HEAD"]),
        ("Changed paths", ["git", "status", "--short"]),
    ):
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
        value = completed.stdout.strip() if completed.returncode == 0 else "unavailable"
        if label == "Changed paths":
            changed = value.splitlines()
            value = "\n".join(changed[:200]) or "clean"
            if len(changed) > 200:
                value += f"\n... {len(changed) - 200} more paths omitted"
        lines.append(f"{label}:\n{value}")
    return "\n\n".join(lines)


def compaction_paths(agents_root: Path, payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    """Resolve bounded per-session compaction state paths."""

    root = agents_root / "shared-session" / "compaction" / safe_session_id(payload)
    return root / "state.json", root / "current-handoff.md", root / "state.lock"


_GRID_TOOL = None


def _grid_tool():
    """Load the sibling task-graph tool; it owns the one text rendering of a graph."""

    global _GRID_TOOL
    if _GRID_TOOL is None:
        import importlib.util

        source = Path(__file__).with_name("lhc_grid.py")
        spec = importlib.util.spec_from_file_location("lhc_grid_handoff", source)
        if spec is None or spec.loader is None:
            raise OSError(f"task-graph tool not found next to the guard: {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _GRID_TOOL = module
    return _GRID_TOOL


def find_plan_graph(cwd: Path) -> Path | None:
    """Find the session's canonical task graph next to the project's task records.

    The search never crosses a repository boundary: a project that happens to sit
    inside another project (a test checkout, a nested service) must not borrow the
    outer project's task graph, or the plan of one project silently replaces the
    plan of another.
    """

    for root in (cwd, *cwd.parents):
        tasks = root / ".agents" / "tasks"
        if tasks.is_dir():
            candidates = [path for path in tasks.glob("*/plan.graph.json") if path.is_file()]
            candidates += [path for path in tasks.glob("plan.graph.json") if path.is_file()]
            if candidates:
                return max(candidates, key=lambda path: path.stat().st_mtime)
        if (root / ".git").exists():
            return None
    return None


_PARALLEL_TOOL = None


def _parallel_tool():
    """Load the sibling parallel-lane tool; it owns the reading of a graph."""

    global _PARALLEL_TOOL
    if _PARALLEL_TOOL is None:
        import importlib.util

        source = Path(__file__).with_name("lhc_parallel.py")
        spec = importlib.util.spec_from_file_location("lhc_parallel_reminder", source)
        if spec is None or spec.loader is None:
            raise OSError(f"parallel-lane tool not found next to the guard: {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _PARALLEL_TOOL = module
    return _PARALLEL_TOOL


def render_parallel_lines(cwd: Path) -> str:
    """Name the parallel lanes that can start right now, read from the plan graph.

    This reads the canonical graph and lists the lanes: what runs now, what is
    ready to start, what waits and what is blocked. It never estimates,
    reviews, judges or blocks, and a missing graph is reported as missing
    instead of being filled in from anything else. The function is total: a
    reminder must never break the heartbeat that carries it.
    """

    try:
        return _render_parallel_lines(cwd)
    except (OSError, ImportError, ValueError, TypeError, KeyError, AttributeError) as error:
        return (
            f"LHC параллельные линии: план-граф прочитать не удалось ({error}). "
            "Параллельные линии не определены."
        )


def _render_parallel_lines(cwd: Path) -> str:
    """Build the parallel-lines reminder text from the canonical graph."""

    path = find_plan_graph(cwd)
    if path is None:
        return (
            "LHC параллельные линии: план-граф не найден — нет plan.graph.json в "
            "<project>/.agents/tasks/, поэтому параллельные линии не определены. "
            "Постройте план-граф и прочитайте линии из него; здесь ничего не "
            "выдумывается."
        )
    try:
        parallel = _parallel_tool()
    except (OSError, ImportError) as error:
        return (
            f"LHC параллельные линии: план-граф {path}. Инструмент параллельных "
            f"линий недоступен ({error})."
        )
    try:
        summary = parallel.summarize(path)
    except (OSError, ValueError) as error:
        return (
            f"LHC параллельные линии: план-граф {path} прочитать как граф задач "
            f"не удалось ({error}). Параллельные линии не определены."
        )

    free = summary.free_slots
    free_text = str(free) if free is not None else "без ограничения"
    running = ", ".join(f"{task.id} «{task.label}»" for task in summary.running) or "нет"
    lines = [
        f"LHC параллельные линии (план-граф {path}):",
        f"Сейчас в работе: {running}. Свободно слотов: {free_text}.",
    ]
    if summary.ready:
        ready = "; ".join(
            f"{task.id} «{task.label}» ({task.estimate_label})" for task in summary.ready
        )
        lines.append(f"Готовы к запуску: {ready}.")
    else:
        lines.append("Готовы к запуску: нет.")
    if summary.waiting:
        waiting = "; ".join(
            f"{task.id} «{task.label}» ждёт {', '.join(unmet)}"
            for task, unmet in summary.waiting
        )
        lines.append(f"Ждут: {waiting}.")
    if summary.blocked:
        blocked = "; ".join(
            f"{task.id} «{task.label}» — {reason}" for task, reason in summary.blocked
        )
        lines.append(f"Заблокированы: {blocked}.")
    next_task = summary.next_step()
    if next_task is not None:
        lines.append(f"Следующий шаг: запустить {next_task.id} «{next_task.label}».")
    lines.append(
        "Запусти параллельные линии, которые готовы, а не работай только над одной. "
        "This reminder names the lanes that can start now; it never estimates, "
        "reviews, judges or blocks."
    )
    return "\n".join(lines)


def render_plan_section(cwd: Path) -> str:
    """Return the human-readable plan/graph text for the compaction handoff.

    The text comes from the canonical graph file, never from a JSON dump: the
    graph stays the machine artifact, the handoff carries the readable view.
    """

    path = find_plan_graph(cwd)
    if path is None:
        return (
            "Plan graph not found: no plan.graph.json under <project>/.agents/tasks/. "
            "The plan state after compaction is unknown; rebuild it from the `## Plan` "
            "section of the canonical task record."
        )
    try:
        grid = _grid_tool()
    except (OSError, ImportError) as error:
        return f"Plan graph: {path}. The graph renderer is unavailable ({error})."
    try:
        graph = grid.load_graph(path)
        metrics = grid.build_metrics(graph)
        text = grid.render_text(graph, metrics)
    except (OSError, ValueError) as error:
        return (
            f"Plan graph: {path}. It could not be read as a task graph ({error}). "
            "The plan state after compaction is unknown."
        )
    body = f"Plan graph: {path}\n\n{text}"
    if len(body) > MAX_HANDOFF_PLAN_CHARS:
        head = MAX_HANDOFF_PLAN_CHARS * 2 // 3
        body = body[:head] + "\n[... plan text truncated; the full graph stays in plan.graph.json ...]"
    return body


def render_handoff(
    *,
    count: int,
    now: datetime,
    task: Path | None,
    task_text: str,
    payload: dict[str, Any],
    recent: list[dict[str, Any]],
    cwd: Path,
    native_handoff: str = "",
    plan_text: str = "",
) -> str:
    """Build one decision-complete, bounded current handoff."""

    recent_lines = [
        f"- #{mark['count']} at {mark['at']} — {mark['status']}"
        for mark in recent[-3:]
    ]
    bounded_task_text = task_text.rstrip()
    task_label = os.fspath(task) if task is not None else "unavailable; native prompt fallback"
    if len(bounded_task_text) > MAX_HANDOFF_TASK_CHARS:
        head = MAX_HANDOFF_TASK_CHARS * 2 // 3
        tail = MAX_HANDOFF_TASK_CHARS - head
        bounded_task_text = (
            bounded_task_text[:head]
            + "\n\n[legacy task-card middle omitted from handoff; authoritative file: "
            + task_label
            + "]\n\n"
            + bounded_task_text[-tail:]
        )
    native_handoff = native_handoff.strip()
    if len(native_handoff) > MAX_NATIVE_HANDOFF_CHARS:
        native_handoff = (
            native_handoff[:MAX_NATIVE_HANDOFF_CHARS]
            + "\n...[native runtime handoff truncated]"
        )
    native_section = (
        [
            "## Native runtime compaction handoff (bounded)",
            "",
            native_handoff,
            "",
        ]
        if native_handoff
        else []
    )
    plan_section = (
        [
            "## Current plan and task graph (text view; the JSON stays in plan.graph.json)",
            "",
            plan_text.strip(),
            "",
        ]
        if plan_text.strip()
        else []
    )
    return "\n".join(
        [
            "# LHC Current Handoff",
            "",
            f"Compaction count: {count}",
            f"Prepared at: {now.isoformat()}",
            f"Runtime session: {safe_session_id(payload)}",
            f"Trigger: {payload.get('trigger') or 'unknown'}",
            f"Active task: {task_label}",
            "",
            "Continue from this handoff. Do not restart completed investigation, "
            "silently widen the accepted DoD, or infer missing timing/status data.",
            "",
            "## Last three compaction marks",
            "",
            *(recent_lines or ["- none"]),
            "",
            "## Current task contract and handoff (bounded; source path above is authoritative)",
            "",
            bounded_task_text,
            "",
            *plan_section,
            *native_section,
            "## Workspace snapshot",
            "",
            "```text",
            git_snapshot(cwd),
            "```",
            "",
        ]
    )


def compaction_hook(
    args: argparse.Namespace,
    payload: dict[str, Any],
    cwd: Path,
) -> dict[str, Any] | None:
    """Persist, count, and restore one bounded current compaction handoff."""

    agents_root = find_agents_root(cwd)
    if agents_root is None:
        return None
    state_path, handoff_path, lock_path = compaction_paths(agents_root, payload)
    event = args.event.casefold()

    if event == "sessionstart":
        if not handoff_path.is_file():
            return None
        handoff = handoff_path.read_text(encoding="utf-8")
        if args.runtime == "codex":
            return {
                "hookSpecificOutput": {
                    "hookEventName": args.event,
                    "additionalContext": handoff,
                }
            }
        return {"handoff": handoff, "handoff_path": os.fspath(handoff_path)}

    task = find_active_task(cwd)
    card = task[0] if task is not None else None
    now = args.now or datetime.now().astimezone()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = load_state(state_path) or {
            "schema_version": 1,
            "compaction_count": 0,
            "recent": [],
        }
        recent = list(state.get("recent", []))
        count = int(state.get("compaction_count", 0))

        if event == "precompact":
            for mark in recent:
                if mark.get("status") == "pending":
                    mark["status"] = "completion-unknown"
            count += 1
            recent.append({"count": count, "at": now.isoformat(), "status": "pending"})
            recent = recent[-3:]
            fallback_prompt = _active_compaction_prompt(cwd, args.runtime, payload, state.get("last_user_prompt"))
            task_text = (
                card.read_text(encoding="utf-8")
                if card is not None
                else (
                    "No active task-card was available.\n\n"
                    f"Latest captured user prompt: {fallback_prompt}\n"
                    "Started at: unknown\n"
                    "Initial estimate: unknown\n"
                    "Actual active time: unknown / not measured\n"
                    "Current blocker: unknown\n"
                    "Next shortest action: reconstruct only from the prompt and workspace snapshot."
                )
            )
            handoff = render_handoff(
                count=count,
                now=now,
                task=card,
                task_text=task_text,
                payload=payload,
                recent=recent,
                cwd=cwd,
                native_handoff=str(payload.get("native_handoff") or ""),
                plan_text=render_plan_section(cwd),
            )
            write_text(handoff_path, handoff)
        elif event == "postcompact":
            if recent and recent[-1].get("status") == "pending":
                recent[-1]["status"] = "completed"
            fallback_prompt = _active_compaction_prompt(cwd, args.runtime, payload, state.get("last_user_prompt"))
            task_text = (
                card.read_text(encoding="utf-8")
                if card is not None
                else (
                    "No active task-card was available.\n\n"
                    f"Latest captured user prompt: {fallback_prompt}\n"
                    "Started at: unknown\n"
                    "Initial estimate: unknown\n"
                    "Actual active time: unknown / not measured\n"
                    "Current blocker: unknown\n"
                    "Next shortest action: reconstruct only from the prompt and workspace snapshot."
                )
            )
            handoff = render_handoff(
                count=count,
                now=now,
                task=card,
                task_text=task_text,
                payload=payload,
                recent=recent,
                cwd=cwd,
                native_handoff=str(payload.get("native_handoff") or ""),
                plan_text=render_plan_section(cwd),
            )
            write_text(handoff_path, handoff)
        else:
            return None

        state.update(
            {
                "compaction_count": count,
                "handoff_path": os.fspath(handoff_path),
                "last_event": args.event,
                "last_event_at": now.isoformat(),
                "recent": recent[-3:],
            }
        )
        write_state(state_path, state)

    if args.runtime == "codex":
        return {
            "systemMessage": (
                f"LHC compaction #{count}: current handoff saved at {handoff_path}. "
                "The next SessionStart must restore it before work continues."
            )
        }
    return {
        "compaction_count": count,
        "handoff": handoff,
        "handoff_path": os.fspath(handoff_path),
    }


# --------------------------------------------------------------------------
# Git layout answers
#
# The guard resolves the owner of the learning state from the repository
# layout.  That answer is a filesystem fact, so it is read from disk instead
# of paying for two git processes on every lookup.  The canon answers the
# questions about the layout of a repository in one place, the reader of the
# layout, and this module asks it.  Every answer is read at the moment of the
# call and nothing is cached, so a worktree that changed between two calls is
# never answered from a stale value.  A layout the reader does not model
# answers None and the git binary is asked instead.
# --------------------------------------------------------------------------

_GIT_LAYOUT = None
_GIT_LAYOUT_LOADED = False


def git_layout():
    """The reader of the layout of a repository, loaded from next to this file.

    ``None`` means the reader is not there at all; every question is then
    answered by the git binary, the way it was answered before the reader
    existed.
    """

    global _GIT_LAYOUT, _GIT_LAYOUT_LOADED
    if not _GIT_LAYOUT_LOADED:
        _GIT_LAYOUT = _load_git_layout()
        _GIT_LAYOUT_LOADED = True
    return _GIT_LAYOUT


def _load_git_layout():
    """Load the reader of the layout of a repository from next to this file."""

    try:
        import lhc_gitlayout

        return lhc_gitlayout
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name("lhc_gitlayout.py")
    try:
        spec = importlib.util.spec_from_file_location("lhc_gitlayout_sibling", path)
        if spec is None or spec.loader is None:
            return None
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - a missing reader is answered by git
        sys.modules.pop("lhc_gitlayout_sibling", None)
        return None


def _git_common_dir_of(cwd: Path) -> Path | None:
    """Answer ``git rev-parse --path-format=absolute --git-common-dir``."""

    layout = git_layout()
    return layout.common_dir_of(cwd) if layout is not None else None


def _git_worktree_list_porcelain(common_dir: Path) -> str | None:
    """Answer ``git --git-dir <common> worktree list --porcelain``.

    The output is byte for byte the output of git for the layouts the reader
    models.  ``None`` means the layout is not modelled and the git binary has
    to answer.
    """

    layout = git_layout()
    return layout.worktree_list_porcelain(common_dir) if layout is not None else None


def _git_primary_worktree(cwd: Path) -> Path | None:
    """Return the primary worktree of the repository that owns a directory.

    The answer is read from the repository layout at the moment of the call.
    ``None`` means the layout is not modelled and the git binary has to answer.
    """

    layout = git_layout()
    return layout.primary_worktree(cwd) if layout is not None else None


def _git_worktree_root(cwd: Path) -> Path | None:
    """Answer ``git rev-parse --show-toplevel`` for a directory.

    The work tree of a repository is the directory that holds its git
    directory.  ``None`` means the directory is not inside a work tree, or the
    layout is not one this code models, and the git binary has to answer.
    """

    layout = git_layout()
    return layout.worktree_root(cwd) if layout is not None else None


def _git_current_branch(cwd: Path) -> str | None:
    """Answer ``git branch --show-current`` for a directory.

    The current branch is the branch the HEAD of the work tree points at.  An
    empty answer is a detached HEAD, which git reports as an empty branch.
    ``None`` means the directory is not in a repository, the HEAD points
    outside ``refs/heads``, or the layout is not one this code models.
    """

    layout = git_layout()
    return layout.current_branch(cwd) if layout is not None else None


def _primary_worktree(cwd: Path) -> Path | None:
    """Return the primary worktree of the repository that owns a directory.

    The answer is read from the repository layout on disk at the moment of the
    call, so a worktree that changed between two calls is never answered from
    a stale value.  ``None`` means the layout is not one the code below models
    and the git binary has to answer.
    """

    return _git_primary_worktree(cwd)


def learning_path(cwd: Path, runtime: str, session_id: str) -> Path:
    """Keep the parent clock independent of cards, cycle ids and handoffs."""

    digest = hashlib.sha256(f"{runtime}\0{session_id}".encode()).hexdigest()
    suffix = Path("shared-session") / "learning" / f"{digest}.json"
    # Reuse a pre-existing ancestor clock before choosing a new storage owner.
    for root in (cwd, *cwd.parents):
        existing = root / ".agents" / suffix
        if existing.is_file():
            return existing
        if (root / ".git").exists():
            break
    agents = find_agents_root(cwd) or cwd / ".agents"
    git_root = next((root for root in (cwd, *cwd.parents) if (root / ".git").exists()), None)
    if git_root is not None:
        primary = _primary_worktree(cwd)
        if primary is None:
            common = subprocess.run(
                ["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                capture_output=True, text=True, check=True, timeout=2,
            ).stdout.strip()
            # Git's first worktree is the primary checkout, including separate git dirs.
            worktrees = subprocess.run(
                ["git", "--git-dir", common, "worktree", "list", "--porcelain"],
                capture_output=True, text=True, check=True, timeout=2,
            ).stdout.splitlines()
            primary = next(line.removeprefix("worktree ") for line in worktrees
                           if line.startswith("worktree "))
        agents = Path(primary) / ".agents"
    return agents / suffix


def native_heartbeat(cwd: Path, runtime: str, session_id: str,
                     *, now: datetime | None = None) -> dict[str, Any] | None:
    """Record only a per-native-session wall clock and emit due reminders once.

    This deliberately does not inspect prompts, task cards, outcomes, tools,
    milestones or permission text. Active time is not inferred from tool gaps.
    """
    if runtime not in {"codex", "claude", "opencode", "zcode"}:
        return None
    if not isinstance(session_id, str) or not session_id.strip() or session_id.strip() == "unknown-session":
        return None
    if len(session_id) > 256 or any(ord(char) < 32 for char in session_id):
        return None
    if not isinstance(cwd, Path) or not cwd.is_absolute():
        return None
    try:
        native_cwd = cwd.resolve(strict=True)
    except OSError:
        return None
    if not native_cwd.is_dir():
        return None
    now = now or datetime.now().astimezone()
    if now.tzinfo is None or now.utcoffset() is None:
        return None

    path = learning_path(native_cwd, runtime, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            state = load_state(path)
        except (OSError, UnicodeError, ValueError):
            return None
        if state is None:
            if path.is_file():
                return None
            state = {}
        if not isinstance(state, dict):
            return None
        business = state.get("business", {})
        if not isinstance(business, dict):
            return None
        if business:
            if business.get("runtime") not in (None, runtime):
                return None
            identity = business.get("native_identity", {})
            if not isinstance(identity, dict):
                return None
            if identity.get("verified") is True:
                if identity.get("logical_session_id") not in (None, session_id):
                    return None
                if identity.get("native_cwd") not in (None, os.fspath(native_cwd)):
                    return None
        native_entry = state.get("native_entry", {})
        milestone = state.get("milestone", {})
        if not isinstance(native_entry, dict) or not isinstance(milestone, dict):
            return None
        if native_entry.get("finish_hold") or milestone.get("hold"):
            return None

        timer = state.get("native_heartbeat", {})
        if not isinstance(timer, dict):
            return None
        if timer:
            if timer.get("session_id") != session_id or timer.get("runtime") != runtime or timer.get("cwd") != os.fspath(native_cwd):
                return None
            try:
                started = parse_time(timer["started_at"])
                last_seen = parse_time(timer["last_seen_at"])
            except (KeyError, ValueError, TypeError, argparse.ArgumentTypeError):
                return None
            if now < started or now < last_seen:
                return None
            last_plan_bucket = timer.get("last_plan_bucket")
            last_goal_bucket = timer.get("last_goal_bucket")
            if (not isinstance(last_plan_bucket, int) or last_plan_bucket < 0 or
                    not isinstance(last_goal_bucket, int) or last_goal_bucket < 0):
                return None
        else:
            started = now
            last_plan_bucket = 0
            last_goal_bucket = 0
            timer = {
                "schema": "lhc.native-heartbeat.v1",
                "runtime": runtime,
                "session_id": session_id,
                "cwd": os.fspath(native_cwd),
                "started_at": now.isoformat(),
                "last_plan_bucket": 0,
                "last_goal_bucket": 0,
            }

        elapsed = now - started
        elapsed_seconds = max(0, int(elapsed.total_seconds()))
        plan_bucket = elapsed_seconds // 1800
        goal_bucket = elapsed_seconds // 3600
        due: list[str] = []
        if plan_bucket > last_plan_bucket:
            due.append(f"plan:{plan_bucket}")
            timer["last_plan_bucket"] = plan_bucket
        if goal_bucket > last_goal_bucket:
            due.append(f"goal:{goal_bucket}")
            timer["last_goal_bucket"] = goal_bucket
        timer["last_seen_at"] = now.isoformat()
        state["native_heartbeat"] = timer
        write_state(path, state)

    reminders = []
    if any(item.startswith("plan:") for item in due):
        reminders.append(
            "LHC 30-minute plan report: the time is over and the task is not finished. "
            "What blocked you? Remove any blocker you can remove yourself, now. If you "
            "were doing checks, planning, hardening or reports for their own sake, stop "
            "and take the nearest step to the owner's business result and keep working. Compare the "
            "owner's latest correction with what works in the real caller and update "
            "only the leaves whose facts changed (common/protocols/PLAN_REPORT.md). "
            "This reminder is not a task and never ends the turn."
        )
        # The same checkpoint names the lanes that can start right now. It reads
        # the canonical graph and lists them; it never estimates or judges.
        reminders.append(render_parallel_lines(native_cwd))
    if any(item.startswith("goal:") for item in due):
        reminders.append(
            "LHC 60-minute direction check: still not finished. Reread the original direct user goal "
            "and the latest correction, name the blocker and the nearest step to "
            "the business result, and do it. Checks that verify nothing new are the "
            "delay: stop them. Not a task, never a reason to stop."
        )
    return {"state": os.fspath(path), "elapsed_wall_seconds": max(0, int(elapsed.total_seconds())),
            "due": due, "prompt": "\n\n".join(reminders)}


def learning_checkpoint(args: argparse.Namespace, cwd: Path, session_id: str,
                        *, acknowledge: bool = False) -> dict[str, Any]:
    """Observe a persistent wall deadline; only an evidenced ack advances it."""

    path = learning_path(cwd, args.runtime, session_id)
    now = args.now or datetime.now().astimezone()
    lock = path.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = load_state(path)
        if state is None:
            if acknowledge:
                raise ValueError("no observed session checkpoint exists")
            state = {
                "schema_version": 1,
                "started_at": now.isoformat(),
                "clock_source": "first native hook observation; wall time only",
                "due_at": (now + timedelta(minutes=120)).isoformat(),
                "last_observed_at": now.isoformat(),
                "last_checkpoint": None,
            }
        # A backwards clock must not erase an already observed deadline.
        observed = max(now, parse_time(state["last_observed_at"]))
        due = observed >= parse_time(state["due_at"])
        if acknowledge:
            if not due or args.due_at != parse_time(state["due_at"]):
                raise ValueError("checkpoint is not due or due-at does not match")
            if now < parse_time(state["last_observed_at"]):
                raise ValueError("acknowledgement clock precedes last observation")
            evidence = {}
            for field in ("observation", "verification", "accepted_result",
                          "remaining_critical_path", "scope_review", "rework_review"):
                value = getattr(args, field)
                if not value.strip() or len(value) > 2048:
                    raise ValueError(f"{field} must contain 1..2048 nonblank characters")
                evidence[field] = value.strip()
            outcome = "method_change" if args.method_change is not None else "no_change_reason"
            value = getattr(args, outcome)
            if not value.strip() or len(value) > 2048:
                raise ValueError(f"{outcome} must contain 1..2048 nonblank characters")
            evidence[outcome] = value.strip()
            state["last_checkpoint"] = {
                "due_at": state["due_at"], "acknowledged_at": now.isoformat(), **evidence,
            }
            state["due_at"] = (now + timedelta(minutes=120)).isoformat()
            due = False
        state["last_observed_at"] = observed.isoformat()
        write_state(path, state)
    prompt = ""
    if due:
        prompt = (
            "LHC session checkpoint: 120 wall-clock minutes and the task is not finished. "
            "What slowed it: a blocker you could remove yourself, a check or ritual, a "
            "wrong route? Stop that and take the nearest step to the business result; if "
            "the route is unclear, follow the escalation chain in AGENTS.md (Adviser, then "
            "Overseer). Not a task and never a reason to stop. "
            f"Session={session_id}; due-at={state['due_at']}; first observed={state['started_at']}."
        )
        if session_id == "unknown-session":
            prompt += (
                " Native session identity unavailable: this project/runtime fallback is shared; "
                "per-session/user-goal isolation is NOT established."
            )
    return {"due": due, "due_at": state["due_at"], "state": str(path), "prompt": prompt}



_ACTIVE_TOOL = None


def active_tool():
    """Reuse the existing monotonic interval implementation without a second ledger."""
    global _ACTIVE_TOOL
    if _ACTIVE_TOOL is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lhc_business_intervals", Path(__file__).with_name("lhc_active_time.py"))
        _ACTIVE_TOOL = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ACTIVE_TOOL)
    return _ACTIVE_TOOL


def business_clock_sample():
    return active_tool().clock_sample()


def update_execution_context(business, prompt, payload, session_id):
    """Preserve native user scope as source context, never as an auth token."""
    context = business.setdefault("execution_context", {
        "purpose": "preserve direct user scope and exceptions; harness remains the authority",
        "direct_user_messages": [],
    })
    turn_ref = payload.get("turn_id") or payload.get("turnId") or "current"
    prompt_ref = f"{turn_ref}:{hashlib.sha256(prompt.strip().encode()).hexdigest()[:12]}"
    source = f"native-user-prompt:{session_id}:{prompt_ref}"
    raw_prompt = prompt.strip()
    safe_prompt = prompt_excerpt(raw_prompt)
    # Share the outcome parser so truncation, deferred frames, and supported
    # native attribution headers have one exact interpretation.
    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import lhc_outcome
    safe_prompt = lhc_outcome.semantic_scope(safe_prompt)
    origin = lhc_outcome.source_origin(raw_prompt, safe_prompt)
    rows = context.setdefault("direct_user_messages", [])
    if not rows or rows[-1].get("source") != source:
        rows.append({"source": source, "prompt": raw_prompt[:2048],
                     "scope_prompt": safe_prompt[:4096], "origin": origin,
                     "observed_at": str(payload.get("timestamp") or "native-event")[:64]})
    else:
        # A source recorded by an older hook may predate this origin field.
        rows[-1].update(prompt=raw_prompt[:2048], scope_prompt=safe_prompt[:4096], origin=origin)
    del rows[:-4]


def native_operation(payload):
    """Extract an operation from executable fields, excluding workdir/log prose."""
    name = str(payload.get("tool_name") or payload.get("toolName") or payload.get("tool") or "").casefold()
    raw = payload.get("tool_input") or payload.get("arguments") or {}
    command = (raw.get("cmd") or raw.get("command") or raw.get("script") or "") if isinstance(raw, dict) else str(raw)
    try:
        words = shlex.split(str(command))
    except ValueError:
        words = []
    executable = Path(words[0]).name.casefold() if words else ""
    if executable in {"bash", "sh", "zsh"}:
        index = next((i for i, word in enumerate(words) if word in {"-c", "-lc"}), None)
        if index is not None and index + 1 < len(words):
            nested = dict(payload, tool_input={"cmd": words[index + 1]})
            return native_operation(nested)
    if executable in {"echo", "printf", "cat", "pwd", "ls", "rg", "grep", "find"}:
        return "unknown", "unknown"
    if executable == "git" and len(words) > 1:
        if words[1] in {"status", "diff", "show", "log"}:
            return "inspection", "unknown"
    verbs = {"deploy", "deployment", "rollout", "publish", "release", "check", "test", "verify",
             "build", "build-status", "build-start"}
    operation = ""
    if executable in verbs:
        operation = executable
    elif executable in {"python", "python3", "node", "bash", "sh"}:
        script_index = next((i for i, word in enumerate(words[1:], 1)
                             if Path(word).suffix in {".py", ".js", ".mjs", ".sh"}), None)
        if script_index is not None and script_index + 1 < len(words):
            candidate = words[script_index + 1].casefold()
            if candidate in verbs:
                operation = candidate
    elif executable in {"npm", "pnpm", "yarn"} and len(words) > 2 and words[1] in {"run", "exec"}:
        candidate = words[2].casefold().split(":", 1)[0]
        if candidate in verbs:
            operation = candidate
    if not operation:
        specialized = re.search(r"(?:^|[._-])(deploy|publish|release|browser|playwright)(?:$|[._-])", name)
        operation = specialized.group(1) if specialized else ""
    target = "unknown"
    operation_index = next((i for i, word in enumerate(words) if word.casefold() == operation), None)
    if operation and operation_index is not None:
        args = words[operation_index + 1:]
        target = next((word.casefold() for word in args if word.casefold() in {"demo", "private", "production"}), "unknown")
        if target == "unknown":
            target = next((word.split("=", 1)[1].casefold() for word in args
                           if word.startswith("--target=") and word.split("=", 1)[1].casefold() in {"demo", "private", "production"}), "unknown")
    return operation or "unknown", target


def record_native_action(business, payload, event, session_id, now):
    """Record references to observed native tool outcomes; never infer delivery."""
    if event in {"posttooluse", "posttoolusefailure", "tool.execute.after"}:
        response = payload.get("tool_response") or payload.get("result") or {}
        if not isinstance(response, dict):
            response = {}
        name = str(payload.get("tool_name") or payload.get("toolName") or payload.get("tool") or "native-tool")[:100]
        call_id = str(payload.get("tool_call_id") or payload.get("call_id") or payload.get("toolUseId") or "")[:120]
        operation, target = native_operation(payload)
        status = str(response.get("status") or response.get("state") or "")[:40].lower()
        output = str(response.get("output") or response.get("stdout") or response.get("content") or "")
        job_id = str(response.get("job_id") or response.get("jobId") or response.get("session_id") or "")[:120]
        terminal_status = status in {"completed", "complete", "succeeded", "success", "failed",
                                     "error", "cancelled", "canceled", "terminated", "exited", "done", "finished"}
        terminal_exit = response.get("exit_code") is not None
        terminal = terminal_status or terminal_exit
        running = not terminal and (status in {"running", "queued", "pending"} or (
            response.get("exit_code") is None and bool(job_id)) or bool(
                re.search(r"process running with session id|session id\s*[:=]?\s*\d+", output, re.I)))
        if not job_id and running:
            match = re.search(r"session id\s*[:=]?\s*(\d+)", output, re.I)
            if match:
                job_id = match.group(1)
        jobs = business.setdefault("running_jobs", {})
        if job_id and running:
            jobs[job_id] = {"tool": name, "status": status or "running", "operation": operation,
                            "target": target, "source": f"native-tool:{session_id}:{call_id or name}",
                            "observed_at": now.isoformat()}
        elif job_id and job_id in jobs:
            jobs.pop(job_id, None)
        if (response.get("exit_code", 0) not in {0, None} or response.get("isError") or
                status in {"failed", "error", "cancelled", "canceled", "terminated"} or
                event == "posttoolusefailure"):
            outcome = "failed"
        elif running:
            outcome = "running"
        else:
            outcome = "returned"
        evidence = business.setdefault("tool_observations", [])
        review = business.get("last_review") or {}
        proposed = str(review.get("proposed_next_action") or review.get("next_action") or "").casefold()
        relevant = False
        if proposed and operation != "unknown":
            if re.search(r"deploy|deployment|выкат|развер", proposed):
                relevant = operation in {"deploy", "deployment", "rollout"}
            elif re.search(r"consumer|потребител", proposed):
                relevant = operation in {"check", "browser", "playwright"}
            elif re.search(r"test|verify|check|провер|тест", proposed):
                relevant = operation in {"check", "test", "verify", "browser", "playwright"}
            elif re.search(r"build|сборк", proposed):
                relevant = operation in {"build", "build-status", "build-start"}
        observation = {"source": f"native-tool:{session_id}:{call_id or name}", "tool": name,
                         "operation": operation, "target": target,
                         "outcome": outcome, "relation": "relevant" if relevant else ("unrelated" if proposed else "unclassified"),
                         "observed_at": now.isoformat()}
        evidence.append(observation)
        del evidence[:-16]
        relevant_evidence = business.setdefault("action_evidence", [])
        if relevant:
            relevant_evidence.append(observation)
            del relevant_evidence[:-16]
            if review:
                review["action_status"] = ("action-running" if outcome == "running" else
                                           "action-attempt-failed" if outcome == "failed" else "action-result-observed")
            business["action_evidence_sequence"] = max(
                business.get("action_evidence_sequence", 0), len(relevant_evidence) - 1
            ) + 1


def business_checkpoint(args, cwd: Path, session_id: str, payload: dict,
                        *, acknowledge: bool = False) -> dict[str, Any]:
    """Record hourly original-goal direction, independently of milestone acceptance.

    Native work intervals are monotonic and pause at explicit idle/permission/stop
    events. Missing lifecycle coverage uses a labelled wall deadline, not fake
    active minutes. Merely emitting context never acknowledges a review.
    """
    path = learning_path(cwd, args.runtime, session_id)
    now = args.now or datetime.now().astimezone()
    event = str(getattr(args, "event", "")).casefold()
    pauses = {"stop", "interrupt", "sessionend", "permissionrequest", "session.idle", "session.error", "permission.asked"}
    starts = {"userpromptsubmit", "pretooluse", "posttooluse", "posttoolusefailure", "tool.execute.before", "tool.execute.after", "chat.message", "permission.replied"}
    lifecycle = args.runtime in {"codex", "claude", "opencode", "zcode"} and session_id != "unknown-session"
    lock = path.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = load_state(path)
        if state is None:
            raise ValueError("observe the session hook before recording a business review")
        business = state.setdefault("business", {
            "started_at": now.isoformat(), "wall_due_at": (now+timedelta(hours=1)).isoformat(),
            "next_active_seconds": 3600, "original_prompt": "", "latest_prompt": "",
            "review_sequence": 0, "pending": None, "last_review": None,
        })
        business["runtime"] = args.runtime
        if event == "pretooluse":
            capture_native_dispatch(business, payload, session_id, now.isoformat())
        child_identity = payload.get("_lhc_verified_native_identity")
        previous_identity = business.get("native_identity") or {}
        assignment = child_identity.get("assignment") if isinstance(child_identity, dict) else None
        assignment_prompt = assignment.get("prompt") if isinstance(assignment, dict) else None
        assignment_bound = bool(
            isinstance(child_identity, dict) and child_identity.get("verified") is True
            and isinstance(assignment, dict) and assignment.get("status") == "bound"
            and isinstance(assignment_prompt, str) and assignment_prompt.strip()
            and assignment.get("child_id") == payload.get("agent_id")
            and assignment.get("prompt_sha256") == hashlib.sha256(assignment_prompt.encode()).hexdigest()
        )
        prior_assignment = previous_identity.get("assignment") if isinstance(previous_identity, dict) else None
        identity_conflict = bool(
            assignment_bound and isinstance(previous_identity, dict) and previous_identity.get("verified") is True
            and previous_identity.get("dispatch_call_id")
            and (previous_identity.get("dispatch_call_id") != child_identity.get("dispatch_call_id")
                 or (isinstance(prior_assignment, dict) and prior_assignment.get("status") == "bound"
                     and prior_assignment.get("prompt_sha256") != assignment.get("prompt_sha256")))
        )
        if identity_conflict:
            assignment_bound = False
            business["native_identity_error"] = "verified child dispatch conflicts with the previously bound native assignment"
        elif isinstance(child_identity, dict) and child_identity.get("verified") is True:
            business["native_identity"] = child_identity
            business.pop("native_identity_error", None)
        elif isinstance(child_identity, dict):
            if not (isinstance(previous_identity, dict) and previous_identity.get("verified") is True):
                business["native_identity"] = child_identity
            business["native_identity_error"] = child_identity.get("reason") or "current native child assignment is unavailable"
        if assignment_bound:
            # Older hook state may contain a relayed prompt without a verified
            # dispatch join. Preserve it as history, then seed only the current
            # captured plaintext assignment.
            if business.get("original_prompt") and not (
                    isinstance(previous_identity, dict) and previous_identity.get("verified") is True
                    and isinstance(prior_assignment, dict) and prior_assignment.get("status") == "bound"):
                history = business.setdefault("unverified_prompt_history", [])
                history.append({"original_prompt": business.get("original_prompt"),
                                "latest_prompt": business.get("latest_prompt")})
                del history[:-4]
            business["original_prompt"] = assignment_prompt.strip()[:4096]
            business["latest_prompt"] = assignment_prompt.strip()[:4096]
            business["original_scope_prompt"] = _semantic_text(assignment_prompt)[:4096]
            business["latest_scope_prompt"] = business["original_scope_prompt"]
            business["native_assignment_source"] = {
                "source_kind": "native-parent-dispatch",
                "source": "native-parent-dispatch:" + str(child_identity.get("parent_native_id")) + ":" +
                          str(child_identity.get("dispatch_call_id")) + ":" + assignment["prompt_sha256"],
                "prompt": assignment_prompt,
                "scope_prompt": _semantic_text(assignment_prompt),
                "origin": "agent-relay",
                "parent_native_id": child_identity.get("parent_native_id"),
                "child_native_id": child_identity.get("native_id"),
                "dispatch_call_id": child_identity.get("dispatch_call_id"),
                "parent_journal_path": child_identity.get("parent_journal_path"),
                "child_journal_path": child_identity.get("journal_path"),
                "observed_at": assignment.get("observed_at"),
                "prompt_sha256": assignment["prompt_sha256"],
            }
            if len(assignment_prompt.encode("utf-8")) > 4096:
                business["original_prompt_full"] = assignment_prompt.strip()
                business["latest_prompt_full"] = assignment_prompt.strip()
            else:
                business.pop("original_prompt_full", None)
                business.pop("latest_prompt_full", None)
        # Only native prompt events set user intent. A generated task-card never
        # becomes the source of the accepted business objective.
        prompt = payload.get("prompt") or payload.get("text")
        if event in {"userpromptsubmit", "chat.message"} and isinstance(prompt, str) and prompt.strip():
            full_prompt = prompt.strip()
            update_execution_context(business, full_prompt, payload, session_id)
            if assignment_bound:
                source_rows = business.get("execution_context", {}).get("direct_user_messages", [])
                if source_rows:
                    source_rows[-1].update(
                        origin="agent-relay", scope_prompt=business["original_scope_prompt"],
                        assignment_call_id=child_identity.get("dispatch_call_id"),
                        assignment_prompt_sha256=assignment.get("prompt_sha256"),
                    )
            effective_prompt = full_prompt
            is_original_prompt = not business.get("original_prompt")
            unverified_child = bool(payload.get("_lhc_subagent") and is_original_prompt and not assignment_bound)
            if is_original_prompt and not unverified_child:
                business["original_prompt"] = effective_prompt[:4096]
            import lhc_outcome
            origin = lhc_outcome.source_origin(full_prompt)
            promote_latest = (is_original_prompt and not unverified_child) or (
                not is_original_prompt and not payload.get("_lhc_subagent") and
                prompt_should_promote_latest(full_prompt, business, origin=origin)
            )
            scope_excerpt = lhc_outcome.semantic_scope(prompt_excerpt(effective_prompt))[:4096]
            if is_original_prompt:
                if not unverified_child:
                    business["original_scope_prompt"] = scope_excerpt
                    if len(effective_prompt) > 4096:
                        business["original_prompt_full"] = effective_prompt
            if promote_latest:
                business["latest_prompt"] = effective_prompt[:4096]
                business["latest_scope_prompt"] = scope_excerpt
                original_full = business.get("original_prompt_full") or business.get("original_prompt", "")
                if effective_prompt == original_full:
                    business.pop("latest_prompt_full", None)
                elif len(effective_prompt) > 4096:
                    business["latest_prompt_full"] = effective_prompt
                else:
                    business.pop("latest_prompt_full", None)
            if payload.get("transcript_path") and args.runtime != "zcode":
                business["transcript_path"] = str(payload["transcript_path"])[:1024]
        record_native_action(business, payload, event, session_id, now)
        measured = None
        clock_source = "wall-clock fallback: complete native active/idle lifecycle unavailable"
        interval = business.get("interval")
        if lifecycle:
            try:
                sample = business_clock_sample()
                module = active_tool()
                if interval is not None:
                    was_running = interval["status"] == "running"
                    discontinuity = (not module.same_boot(interval["last_sample"], sample)
                        or sample["monotonic_ns"] < interval["last_sample"]["monotonic_ns"]
                        or (event == "sessionstart" and payload.get("source") != "compact"))
                    if discontinuity:
                        # Keep measured previous intervals; discard an unknown
                        # open gap after reconnect/reboot instead of backfilling.
                        interval = dict(interval, status="paused", open_monotonic_ns=None,
                                        last_sample=sample, stopped=None)
                        business["coverage_gap"] = "Open gap discarded at native reconnect or changed clock; earlier intervals retained"
                    if interval["status"] == "running" and not acknowledge:
                        interval = module.transition(interval, "pause", sample)
                    if event in starts or ((event in {"precompact", "postcompact"} or (event == "sessionstart" and payload.get("source") == "compact")) and was_running and not discontinuity):
                        interval = module.transition(interval, "resume", sample)
                elif event in starts:
                    interval = module.transition(None, "start", sample, actor=session_id, task="original-user-goal")
                if interval is not None:
                    business["interval"] = interval
                    measured = module.report(interval, sample)["measured_active_seconds"]
                    clock_source = "monotonic native work intervals; coverage begins at observed work, not CPU time"
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
                business["clock_error"] = type(exc).__name__
        pending = business.get("pending")
        if pending is None and (measured >= business["next_active_seconds"] if measured is not None
                                else now >= parse_time(business["wall_due_at"])):
            sequence = business["review_sequence"] + 1
            pending = {"id": f"business-{sequence}", "due_at": now.isoformat()}
            business["pending"] = pending
        if acknowledge:
            if not pending or args.review_id != pending["id"]:
                raise ValueError("business review is not due or review-id does not match")
            if now < parse_time(pending["due_at"]):
                raise ValueError("review clock precedes its due observation")
            def text(name):
                value = getattr(args, name, None)
                if not isinstance(value, str) or not value.strip() or len(value) > 4096:
                    raise ValueError(f"{name} requires 1..4096 nonblank characters")
                return value.strip()
            refs = getattr(args, "source_ref", [])
            if not refs or len(refs) > 8 or any(not isinstance(v,str) or not v.strip() or len(v)>1024 for v in refs):
                raise ValueError("cite 1..8 original user source references")
            review = {"id": pending["id"], "at": now.isoformat(), "source_refs": refs,
                      **{field: text(field) for field in ("business_result", "scope_decision", "next_action")}}
            action_evidence = business.get("action_evidence", [])
            sequence = business.get("action_evidence_sequence", len(action_evidence))
            review.update(action_status="decision-only", action_evidence_count=sequence)
            previous = business.get("last_review") or {}
            if (previous.get("next_action") == review["next_action"] and
                    previous.get("action_evidence_count", 0) == sequence):
                review["repeated_review_without_action"] = True
                review["proposed_next_action"] = review["next_action"]
                review["next_action"] = (
                    "Change the next step: perform the nearest permitted action or record the exact external dependency; "
                    "do not repeat the same access/status check."
                )
            # 1.4.3: keep old callers' optional observations without requiring a
            # blind test every hour or interpreting them as milestone acceptance.
            zk_fields = ("zk_session", "zk_result", "zk_evidence")
            supplied = [getattr(args, field, None) is not None for field in zk_fields]
            if getattr(args, "zk_unavailable", None) is not None:
                if any(supplied):
                    raise ValueError("unavailable verifier cannot also be a verified result")
                review["zk_unavailable"] = text("zk_unavailable")
            elif any(supplied):
                if not all(supplied):
                    raise ValueError("optional verifier evidence must include session, result and evidence")
                review.update({field: text(field) for field in zk_fields})
            review.update(status="direction_reviewed", milestone_acceptance="not_evaluated")
            business["review_sequence"] += 1
            business["pending"] = pending = None
            business["next_active_seconds"] = (measured or 0)+3600
            business["wall_due_at"] = (now+timedelta(hours=1)).isoformat()
            business["last_review"] = review
        due = pending is not None
        reminder = ""
        previous = business.get("last_injected_at")
        if due and not acknowledge and event not in pauses and not (args.runtime == "codex" and event in {"precompact", "postcompact"}) and not (args.runtime == "opencode" and event in {"tool.execute.before", "permission.replied"}) and (not previous or
                business.get("last_injected_review_id") != pending["id"] or
                (now-parse_time(previous)).total_seconds() >= 300):
            reminder = (
                "Mandatory hourly LHC direction check: reread the original assignment and latest user corrections, "
                "not only your plan. What result did the user receive this hour? SHA/test counts/registry updates alone do not answer. "
                "If the latest result only repaired/reviewed a receipt, do not start another audit: separate actual unverified risk "
                "from metadata and choose the next user-available change. Correct metadata locally over known unchanged source; "
                "verify only the needed new delta/unknown coverage. Never bypass release gates or real tests. "
                "Continue the necessary route, reduce invented scope, change approach or perform available independent work. "
                "This is direction control, not milestone acceptance. Zero Knowledge with varied personas/full feedback belongs "
                "at ready major milestones (~3 hours), not every hour/change. Read common/protocols/BUSINESS_CHECKPOINT.md. "
                "Record source/result/decision/next action through lhc_time_guard.py business-review; it is not product acceptance. "
                f"review-id={pending['id']}; runtime={args.runtime}; session={session_id}; state={path}. "
                f"Clock: {clock_source}. A reminder does not close review; milestone acceptance is separate. "
                "Without new information, do not send another user status."
            )
            original_scope, latest_scope = active_business_prompts(business)
            if original_scope:
                reminder += "\nOriginal input (excerpt; check full source): " + original_scope[:1000]
            if latest_scope and latest_scope != original_scope:
                reminder += "\nLatest correction (excerpt): " + latest_scope[:1000]
            business["last_injected_at"] = now.isoformat()
            business["last_injected_review_id"] = pending["id"]
        write_state(path, state)
    return {"due": due, "review_id": pending["id"] if pending else None, "state": str(path),
            "active_seconds": measured, "clock_source": clock_source, "prompt": reminder}

def hook(args: argparse.Namespace) -> dict[str, Any] | None:
    """Emit parent checkpoints even when task discovery or compaction returns early."""

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        return None
    cwd = Path(str(payload.get("cwd") or os.getcwd())).expanduser().resolve()
    session_id = str(payload.get("session_id") or payload.get("sessionID") or "unknown-session")
    if payload.get("agent_id"):
        session_id += ":subagent:" + str(payload["agent_id"])
    learning = learning_checkpoint(args, cwd, session_id)
    business = business_checkpoint(args, cwd, session_id, payload)
    combined_prompt = "\n\n".join(v for v in (business["prompt"], learning["prompt"]) if v)
    try:
        result = None if getattr(args, "session_only", False) else cycle_hook(args, payload, cwd)
    except (OSError, ValueError, argparse.ArgumentTypeError) as exc:
        # A malformed or future-dated card must not hide the parent obligation.
        if not learning["due"] and not business["due"]:
            raise
        result = {"cycle_error": type(exc).__name__}
    if not combined_prompt:
        return result
    if args.event.casefold() in {"stop", "interrupt", "sessionend", "permissionrequest"}:
        return result
    result = result or {}
    if args.runtime == "codex":
        if args.event.casefold() in {"precompact", "postcompact"}:
            result["systemMessage"] = "\n\n".join(
                str(value) for value in (result.get("systemMessage"), combined_prompt) if value)
        else:
            specific = result.setdefault("hookSpecificOutput", {"hookEventName": args.event})
            specific["additionalContext"] = "\n\n".join(
                str(value) for value in (specific.get("additionalContext"), combined_prompt) if value)
    else:
        result["prompt"] = "\n\n".join(
            str(value) for value in (result.get("prompt"), combined_prompt) if value)
        if "handoff" in result:
            # OpenCode's compacting consumer reads handoff, not prompt.
            result["handoff"] = f"{result['handoff']}\n\n{combined_prompt}"
    return result


def _active_compaction_prompt(cwd: Path, runtime: str, payload: dict, captured: str | None) -> str:
    """Prefer the active task scope over a legacy relay/status compaction value."""
    session_id = str(payload.get("session_id") or payload.get("sessionID") or "unknown-session")
    if payload.get("agent_id"):
        session_id += ":subagent:" + str(payload["agent_id"])
    business_state = load_state(learning_path(cwd, runtime, session_id)) or {}
    business = business_state.get("business") or {}
    if business:
        original, latest = active_business_prompts(business)
        if latest or original:
            return latest or original
    fallback = _eligible_active_scope(captured or "", business, "")
    return fallback or "unknown"


def cycle_hook(args: argparse.Namespace, payload: dict[str, Any],
               cwd: Path) -> dict[str, Any] | None:
    """Adapt task-local timing and compaction without owning the parent clock."""

    if args.event.casefold() in {"userpromptsubmit", "chat.message"}:
        agents_root = find_agents_root(cwd)
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            prompt = payload.get("text")
        if agents_root is not None and isinstance(prompt, str) and prompt.strip():
            origin, semantic_prompt = prompt_metadata(prompt)
            session_id = str(payload.get("session_id") or payload.get("sessionID") or "unknown-session")
            if payload.get("agent_id"):
                session_id += ":subagent:" + str(payload["agent_id"])
            parent = load_state(learning_path(cwd, args.runtime, session_id)) or {}
            business = parent.get("business", {})
            # The raw event is already captured in execution_context. Keep the
            # compaction handoff on the active task prompt, not relay/status or
            # a duplicate of the superseded original prompt.
            promote = (not payload.get("agent_id") and origin != "agent-relay" and bool(semantic_prompt.strip())
                       and not STATUS_OR_ACK_PROMPT.fullmatch(semantic_prompt.strip()))
            original = business.get("original_prompt_full") or business.get("original_prompt") or ""
            latest = business.get("latest_prompt_full") or business.get("latest_prompt") or ""
            if original and semantic_prompt.strip() == _semantic_text(original) and latest and semantic_prompt.strip() != _semantic_text(latest):
                promote = False
            if promote:
                compaction_state, _, compaction_lock = compaction_paths(agents_root, payload)
                compaction_lock.parent.mkdir(parents=True, exist_ok=True)
                with compaction_lock.open("a", encoding="utf-8") as handle:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                    current = load_state(compaction_state) or {
                        "schema_version": 1,
                        "compaction_count": 0,
                        "recent": [],
                    }
                    current["last_user_prompt"] = prompt.strip()
                    write_state(compaction_state, current)
    if args.event.casefold() in {"precompact", "postcompact"}:
        return compaction_hook(args, payload, cwd)
    restored = compaction_hook(args, payload, cwd) if args.event.casefold() == "sessionstart" else None
    task = find_active_task(cwd)
    if task is None:
        return restored
    card, started_at, minimum, maximum, explicit_active = task
    now = args.now or datetime.now().astimezone()
    digest = hashlib.sha256(os.fspath(card).encode()).hexdigest()[:12]
    state = card.parents[1] / "shared-session" / "time" / f"{card.stem}-{digest}.json"
    lock = state.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    actor = str(payload.get("session_id") or payload.get("sessionID") or "unknown-session")
    actor_digest = hashlib.sha256(actor.encode()).hexdigest()[:12]
    interval_state = state.parent / f"{card.stem}-{actor_digest}.active.json"
    interval_report = None
    measurement_note = ""
    if interval_state.exists():
        # The ledger answers the same report from this process, so the report
        # is read here instead of starting a second interpreter for it.  A
        # missing, malformed or cross-boot ledger is unavailable measurement,
        # never zero.
        try:
            candidate = active_tool().status(str(interval_state))
        except (OSError, ValueError, KeyError, TypeError):
            candidate = None
        if (isinstance(candidate, dict)
                and actor != "unknown-session"
                and candidate.get("actor") == actor
                and candidate.get("task") == card.stem
                and candidate.get("status") in {"running", "paused"}):
            interval_report = candidate
    if interval_report is None:
        measurement_note = (
            "Active interval accounting is missing or unavailable. Historical unknown time "
            "stays unknown. When practical, begin measuring forward with lhc_active_time.py; "
            "resume an existing ledger without resetting its total and pause during idle waits. "
            "Missing historical accounting is disclosed, not a prerequisite or veto for "
            "authorized work."
        )
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        previous = load_state(state)
        tracked_seconds = int((previous or {}).get("tracked_active_seconds", 0))
        last_tick_raw = (previous or {}).get("last_hook_tick_at")
        if isinstance(last_tick_raw, str):
            elapsed = max(0, int((now - parse_time(last_tick_raw)).total_seconds()))
            tracked_seconds += min(elapsed, args.idle_cap_seconds)
        active_minutes = tracked_seconds // 60
        active_source = "hook-observed"
        if explicit_active is not None:
            active_minutes = explicit_active
            active_source = "task-card"
        check_args = argparse.Namespace(
            state=state,
            cycle_id=card.stem,
            started_at=started_at,
            now=now,
            minimum_minutes=minimum,
            maximum_minutes=maximum,
            active_minutes=active_minutes,
            business_delta="see active task card",
            completed_task=[],
            completed_file=[],
            gate=[],
            instruction=[],
            controlled="unknown",
            route_changed="unknown",
            active_source=active_source,
        )
        result = check(check_args)
        persisted = load_state(state) or {}
        persisted["last_hook_tick_at"] = now.isoformat()
        persisted["tracked_active_seconds"] = tracked_seconds
        persisted["task_file"] = os.fspath(card)
        write_state(state, persisted)

    prompt = str(result.get("prompt") or "")
    if prompt or args.event.casefold() in {"sessionstart", "userpromptsubmit", "chat.message"}:
        prompt = "\n\n".join(value for value in (prompt, measurement_note) if value)
    if args.event.casefold() in {"userpromptsubmit", "chat.message"}:
        wall_minutes = int((now - started_at).total_seconds() // 60)
        source_note = (
            "task-card explicitly reports active time"
            if explicit_active is not None
            else "hook-observed estimate only; exact active time was not continuously controlled"
        )
        interval_note = ""
        if interval_report is not None:
            interval_note = (
                f" Separate measurement source=interval-ledger: {interval_report['measured_active_seconds']} "
                f"seconds at {interval_state}; coverage begins {interval_report['wall_anchor_utc']}; "
                f"open interval provisional={interval_report['measurement_still_open']}. "
                "Operator-declared intervals, not CPU time. Does not replace the objective's "
                "reported history; do not sum overlapping or unknown intervals."
            )
        status = (
            "LHC timing truth for any status/AskHuman answer: "
            f"started {started_at.isoformat()}; planned {minimum}–{maximum} active minutes; "
            f"{'estimated' if active_source == 'hook-observed' else 'reported'} "
            f"{active_minutes} active minutes ({source_note}); "
            f"{wall_minutes} wall-clock minutes; active source={active_source}. "
            "Never infer an unknown start or active duration from file mtime or wall-clock."
            + interval_note
        )
        prompt = "\n\n".join(value for value in (prompt, status) if value)
    restored_text = ""
    if isinstance(restored, dict):
        if args.runtime == "codex":
            restored_text = str(restored.get("hookSpecificOutput", {}).get("additionalContext") or "")
        else:
            restored_text = str(restored.get("handoff") or "")
    prompt = "\n\n".join(value for value in (restored_text, prompt) if value)
    if not prompt:
        return None
    if args.runtime == "codex":
        return {
            "hookSpecificOutput": {
                "hookEventName": args.event,
                "additionalContext": prompt,
            }
        }
    return {"prompt": prompt}


def parser() -> argparse.ArgumentParser:
    """Build the dependency-free command-line parser."""

    root = argparse.ArgumentParser(description=__doc__)
    subcommands = root.add_subparsers(dest="command", required=True)
    command = subcommands.add_parser("check", help="evaluate one active work cycle")
    command.add_argument("--state", type=Path, required=True)
    command.add_argument("--cycle-id", required=True)
    command.add_argument("--started-at", type=parse_time, required=True)
    command.add_argument("--now", type=parse_time)
    command.add_argument("--minimum-minutes", type=positive, required=True)
    command.add_argument("--maximum-minutes", type=positive, required=True)
    command.add_argument("--active-minutes", type=non_negative, required=True)
    command.add_argument("--business-delta", default="")
    command.add_argument("--completed-task", action="append", default=[])
    command.add_argument("--completed-file", action="append", default=[])
    command.add_argument("--gate", action="append", default=[])
    command.add_argument("--instruction", action="append", default=[])
    command.add_argument("--controlled", choices=("yes", "no", "unknown"), default="unknown")
    command.add_argument("--route-changed", choices=("yes", "no", "unknown"), default="unknown")
    command.add_argument(
        "--active-source",
        choices=("reported", "task-card", "hook-observed"),
        default="reported",
    )
    native = subcommands.add_parser("hook", help="adapt one native Codex or OpenCode hook")
    native.add_argument(
        "--runtime", choices=("codex", "claude", "opencode", "hermes", "zcode"), required=True
    )
    native.add_argument("--event", required=True)
    native.add_argument("--session-only", action="store_true", help="use the source-bound session checks without unrelated legacy task-card discovery")
    native.add_argument("--now", type=parse_time)
    native.add_argument("--idle-cap-seconds", type=positive, default=300)
    checkpoint = subcommands.add_parser("checkpoint", help="acknowledge a due session learning review")
    checkpoint.add_argument("--cwd", type=Path, required=True)
    checkpoint.add_argument("--runtime", choices=("codex", "claude", "opencode", "hermes", "zcode"), required=True)
    checkpoint.add_argument("--session-id", required=True)
    checkpoint.add_argument("--due-at", type=parse_time, required=True)
    checkpoint.add_argument("--now", type=parse_time)
    for field in ("observation", "verification", "accepted-result", "remaining-critical-path",
                  "scope-review", "rework-review"):
        checkpoint.add_argument(f"--{field}", required=True)
    outcome = checkpoint.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--method-change")
    outcome.add_argument("--no-change-reason")
    review = subcommands.add_parser("business-review", help="record hourly original-source direction; this does not accept a product milestone")
    review.add_argument("--cwd", type=Path, required=True)
    review.add_argument("--runtime", choices=("codex", "claude", "opencode", "hermes", "zcode"), required=True)
    review.add_argument("--session-id", required=True)
    review.add_argument("--review-id", required=True)
    review.add_argument("--now", type=parse_time)
    review.add_argument("--source-ref", action="append", required=True)
    for field in ("business-result", "scope-decision", "next-action"):
        review.add_argument(f"--{field}", required=True)
    for field in ("zk-session", "zk-result", "zk-evidence", "zk-unavailable"):
        review.add_argument(f"--{field}", help="optional legacy observation; not milestone acceptance")
    return root


def main() -> int:
    """Run one subcommand and emit stable UTF-8 JSON."""

    args = parser().parse_args()
    try:
        if args.command == "business-review":
            result = business_checkpoint(args, args.cwd.expanduser().resolve(), args.session_id, {}, acknowledge=True)
        elif args.command == "checkpoint":
            result = learning_checkpoint(args, args.cwd.expanduser().resolve(),
                                         args.session_id, acknowledge=True)
        else:
            result = check(args) if args.command == "check" else hook(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"time guard error: {exc}") from exc
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
