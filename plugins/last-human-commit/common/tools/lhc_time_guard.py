#!/usr/bin/env python3
"""Emit idempotent hourly and estimate-overrun business-control prompts."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


BUSINESS_FIRST_HEADER = "Меньше безопасности, больше бизнес-результата."
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
        "reported": "явно передано вызывающей стороной",
        "task-card": "явно записано в task-card",
        "hook-observed": "наблюдалось хуком; точное active-time не контролировалось",
    }[active_source]
    lines = [
        BUSINESS_FIRST_HEADER,
        f"Цикл: {state['cycle_id']}",
        (
            "План: "
            f"{planned['minimum']}–{planned['maximum']} активных минут; "
            f"факт: {active_minutes} активных ({active_note}) / "
            f"{wall_minutes} wall-clock минут."
        ),
        "Какие реальные задачи закрыты?",
        list_line("Закрытые задачи", completed_tasks, "не указаны"),
        f"Реальная бизнес-дельта: {business_delta or 'не указана'}",
        "Выведи все завершённые файлы.",
        list_line("Завершённые файлы", completed_files, "не указаны"),
        "Что мешает?",
        list_line("Какие гейты помешали?", gates, "не указаны"),
        list_line(
            "Какие инструкции заставляли больше идти в безопасность вместо бизнеса?",
            instructions,
            "не указаны",
        ),
        "Сколько планировал потратить на задачу, а сколько потратил?",
        f"Ты это как-то контролировал? Ответ: {controlled}.",
    ]

    if "overrun" in events:
        lines.extend(
            [
                (
                    "Превышение исходного maximum: "
                    f"{max(0, active_minutes - planned['maximum'])} активных минут."
                ),
                (
                    "Почему по времени так превысил задачу, но не менял подход "
                    "и делал лишнее, а не бизнес?"
                ),
                f"Маршрут уже менялся: {route_changed}.",
                "Что меняется в маршруте сейчас?",
            ]
        )

    if "estimate_mutation" in events:
        lines.append(
            "Нельзя легализовать прежний маршрут простой заменой оценки; "
            "исходный minimum/maximum остаётся контрольной точкой."
        )

    lines.append(
        "Не ослабляй обязательную безопасность, секретность, пользовательские "
        "полномочия или границы разрушительных действий; убери только процесс, "
        "не нужный для текущего бизнес-результата."
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
            return (
                card,
                parse_time(started.group(1)),
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
                    "Actual active time: unknown / не контролировал\n"
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
                    "Actual active time: unknown / не контролировал\n"
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


def hook(args: argparse.Namespace) -> dict[str, Any] | None:
    """Adapt one native runtime hook to the existing persistent guard."""

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        return None
    cwd = Path(str(payload.get("cwd") or os.getcwd())).expanduser().resolve()
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
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        previous = load_state(state)
        tracked_seconds = int((previous or {}).get("tracked_active_seconds", 0))
        last_tick_raw = (previous or {}).get("last_hook_tick_at")
        if isinstance(last_tick_raw, str):
            elapsed = max(0, int((now - parse_time(last_tick_raw)).total_seconds()))
            tracked_seconds += min(elapsed, args.idle_cap_seconds)
        active_minutes = tracked_seconds // 60
        if explicit_active is not None:
            active_minutes = max(active_minutes, explicit_active)
            tracked_seconds = max(tracked_seconds, explicit_active * 60)
        check_args = argparse.Namespace(
            state=state,
            cycle_id=card.stem,
            started_at=started_at,
            now=now,
            minimum_minutes=minimum,
            maximum_minutes=maximum,
            active_minutes=active_minutes,
            business_delta="см. активную task-card",
            completed_task=[],
            completed_file=[],
            gate=[],
            instruction=[],
            controlled="yes" if explicit_active is not None else "no",
            route_changed="unknown",
            active_source="task-card" if explicit_active is not None else "hook-observed",
        )
        result = check(check_args)
        persisted = load_state(state) or {}
        persisted["last_hook_tick_at"] = now.isoformat()
        persisted["tracked_active_seconds"] = tracked_seconds
        persisted["task_file"] = os.fspath(card)
        write_state(state, persisted)

    prompt = str(result.get("prompt") or "")
    if args.event.casefold() in {"userpromptsubmit", "chat.message"}:
        wall_minutes = int((now - started_at).total_seconds() // 60)
        active_source = "task-card" if explicit_active is not None else "hook-observed"
        source_note = (
            "task-card explicitly reports active time"
            if explicit_active is not None
            else "hook-observed estimate only; exact active time was not continuously controlled"
        )
        status = (
            "LHC timing truth for any status/AskHuman answer: "
            f"started {started_at.isoformat()}; planned {minimum}–{maximum} active minutes; "
            f"actual {active_minutes} active minutes ({source_note}); "
            f"{wall_minutes} wall-clock minutes; active source={active_source}. "
            "Never infer an unknown start or active duration from file mtime or wall-clock."
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
        "--runtime", choices=("codex", "opencode", "hermes"), required=True
    )
    native.add_argument("--event", required=True)
    native.add_argument("--now", type=parse_time)
    native.add_argument("--idle-cap-seconds", type=positive, default=300)
    return root


def main() -> int:
    """Run one subcommand and emit stable UTF-8 JSON."""

    args = parser().parse_args()
    try:
        result = check(args) if args.command == "check" else hook(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"time guard error: {exc}") from exc
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
