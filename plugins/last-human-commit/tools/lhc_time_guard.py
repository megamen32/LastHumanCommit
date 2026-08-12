#!/usr/bin/env python3
"""Emit idempotent hourly and estimate-overrun business-control prompts."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


BUSINESS_FIRST_HEADER = "Меньше безопасности, больше бизнес-результата."
STARTED_AT = re.compile(r"^\s*-\s*Started at:\s*([^\s(]+)", re.MULTILINE)
INITIAL_ESTIMATE = re.compile(
    r"^\s*-\s*Initial estimate:\s*(\d+)\s*/\s*(\d+)\s+active minutes",
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
) -> str:
    """Render the Russian Lead-facing control prompt for new events."""

    if not events:
        return ""

    planned = state["planned_minutes"]
    lines = [
        BUSINESS_FIRST_HEADER,
        f"Цикл: {state['cycle_id']}",
        (
            "План: "
            f"{planned['minimum']}–{planned['maximum']} активных минут; "
            f"факт: {active_minutes} активных / {wall_minutes} wall-clock минут."
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


def hook(args: argparse.Namespace) -> dict[str, Any] | None:
    """Adapt one native runtime hook to the existing persistent guard."""

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        return None
    cwd = Path(str(payload.get("cwd") or os.getcwd())).expanduser().resolve()
    task = find_active_task(cwd)
    if task is None:
        return None
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
            controlled="unknown",
            route_changed="unknown",
        )
        result = check(check_args)
        persisted = load_state(state) or {}
        persisted["last_hook_tick_at"] = now.isoformat()
        persisted["tracked_active_seconds"] = tracked_seconds
        persisted["task_file"] = os.fspath(card)
        write_state(state, persisted)

    prompt = str(result.get("prompt") or "")
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
    native = subcommands.add_parser("hook", help="adapt one native Codex or OpenCode hook")
    native.add_argument("--runtime", choices=("codex", "opencode"), required=True)
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
