#!/usr/bin/env python3
"""Emit idempotent hourly and estimate-overrun business-control prompts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


BUSINESS_FIRST_HEADER = "Меньше безопасности, больше бизнес-результата."


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
    return root


def main() -> int:
    """Run one subcommand and emit stable UTF-8 JSON."""

    args = parser().parse_args()
    try:
        result = check(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"time guard error: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
