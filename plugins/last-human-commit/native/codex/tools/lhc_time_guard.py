#!/usr/bin/env python3
"""Emit idempotent hourly and estimate-overrun business-control prompts."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
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

    commands = (
        ("Repository", ["git", "rev-parse", "--show-toplevel"]),
        ("Branch", ["git", "branch", "--show-current"]),
        ("HEAD", ["git", "rev-parse", "--short=12", "HEAD"]),
        ("Changed paths", ["git", "status", "--short"]),
    )
    lines: list[str] = []
    for label, command in commands:
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
            fallback_prompt = str(state.get("last_user_prompt") or "unknown")
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
            )
            write_text(handoff_path, handoff)
        elif event == "postcompact":
            if recent and recent[-1].get("status") == "pending":
                recent[-1]["status"] = "completed"
            fallback_prompt = str(state.get("last_user_prompt") or "unknown")
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
            "MANDATORY LHC session/user-goal checkpoint: invoke improve-workflow now. "
            "Review the overall accepted result, remaining critical path, scope expansion "
            "and rework across ALL cycles; stop serial scope expansion. Record observation → "
            "changed method → verification evidence, or an evidence-backed bounded no-change "
            "reason. Notification, compaction, a fresh cycle or a new task card does NOT "
            "acknowledge this checkpoint. Use lhc_time_guard.py checkpoint with --cwd, "
            "--runtime, --session-id, --due-at and the required review/evidence fields. "
            f"Session={session_id}; runtime={args.runtime}; due-at={state['due_at']}; "
            f"first observed={state['started_at']}; state={path}. "
            "This is wall-clock scheduling; active time: not measured."
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
    rows = context.setdefault("direct_user_messages", [])
    if not rows or rows[-1].get("source") != source:
        rows.append({"source": source, "prompt": prompt.strip()[:2048],
                     "scope_prompt": prompt_excerpt(prompt)[:4096],
                     "observed_at": str(payload.get("timestamp") or "native-event")[:64]})
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
        # Only native prompt events set user intent. A generated task-card never
        # becomes the source of the accepted business objective.
        prompt = payload.get("prompt") or payload.get("text")
        if event in {"userpromptsubmit", "chat.message"} and isinstance(prompt, str) and prompt.strip():
            full_prompt = prompt.strip()
            update_execution_context(business, full_prompt, payload, session_id)
            is_original_prompt = not business.get("original_prompt")
            business["original_prompt"] = business["original_prompt"] or full_prompt[:4096]
            business["latest_prompt"] = full_prompt[:4096]
            scope_excerpt = prompt_excerpt(full_prompt)[:4096]
            if is_original_prompt:
                business["original_scope_prompt"] = scope_excerpt
                if len(full_prompt) > 4096:
                    business["original_prompt_full"] = full_prompt
            business["latest_scope_prompt"] = scope_excerpt
            original_full = business.get("original_prompt_full") or business.get("original_prompt", "")
            if full_prompt == original_full:
                business.pop("latest_prompt_full", None)
            elif len(full_prompt) > 4096:
                business["latest_prompt_full"] = full_prompt
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
            original_scope = business.get("original_scope_prompt") or prompt_excerpt(
                business.get("original_prompt_full") or business["original_prompt"]
            )
            latest_scope = business.get("latest_scope_prompt") or prompt_excerpt(
                business.get("latest_prompt_full") or business["latest_prompt"]
            )
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


def cycle_hook(args: argparse.Namespace, payload: dict[str, Any],
               cwd: Path) -> dict[str, Any] | None:
    """Adapt task-local timing and compaction without owning the parent clock."""

    if args.event.casefold() in {"userpromptsubmit", "chat.message"}:
        agents_root = find_agents_root(cwd)
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            prompt = payload.get("text")
        if agents_root is not None and isinstance(prompt, str) and prompt.strip():
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
        measured = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("lhc_active_time.py")),
             "status", "--state", str(interval_state)],
            capture_output=True, text=True, timeout=3, check=False,
        )
        try:
            candidate = json.loads(measured.stdout)
            if (measured.returncode == 0 and isinstance(candidate, dict)
                    and actor != "unknown-session"
                    and candidate.get("actor") == actor
                    and candidate.get("task") == card.stem
                    and candidate.get("status") in {"running", "paused"}):
                interval_report = candidate
        except ValueError:
            pass
    if interval_report is None:
        measurement_note = (
            "Active interval accounting is missing or unavailable. Lead must start or repair "
            f"lhc_active_time.py with --state {interval_state}, --actor {actor}, "
            f"--task {card.stem} on start before new work; "
            "resume an existing stopped/paused ledger explicitly without resetting its total; "
            "pause for idle/user waits and resume for execution. Historical unknown time stays "
            "unknown. Overseer must require repair, not accept a recurring disclaimer."
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
