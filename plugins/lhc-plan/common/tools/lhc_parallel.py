#!/usr/bin/env python3
"""Answer one operational question about an LHC task graph: what can start now.

The task graph is the machine artifact of a plan. It knows the leaves, their
status, their dependencies, their estimates and how many lanes may run at the
same time. This tool turns that artifact into a dispatch decision:

    which lines can be started right now, what is already running, what is
    still in the way, and which slot each ready line belongs to.

Usage::

    python3 lhc_parallel.py PLAN_GRAPH [--json] [--slot]

The readable answer is in Russian, because it is read by a Russian-speaking
operator and by the agent that dispatches the work. The machine answer
(``--json``) carries the same facts for a caller that parses them.

The module is self-contained on purpose: it parses the graph on its own and
never imports the sibling task-graph renderer, so both tools can change
without one another. It uses the standard library only.

Rules
-----
A line is *ready to start* when all of the following hold:

* its status is ``queued`` (it was never started and is not held);
* it carries no blocker text (a concrete obstacle means it is not ready);
* every id in ``depends_on`` exists in the graph and is ``done``;
* a free slot exists: ``slots`` minus the number of running lines.

A queued line whose dependencies are not met is *waiting*: the tool names the
dependency that is not ready and its current status. A line whose status is
``blocked``, or that carries blocker text, is *blocked*: the tool prints the
reason. A ready line that does not fit into a free slot is *deferred*: it is
ready in every other respect and only capacity holds it back.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSIONS = (1, 2)

STATUS_DONE = "done"
STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_WAITING = "waiting"
STATUS_DEFERRED = "deferred"
STATUS_QUEUED = "queued"

STATUSES = (STATUS_DONE, STATUS_RUNNING, STATUS_BLOCKED, STATUS_WAITING, STATUS_DEFERRED, STATUS_QUEUED)

STATUS_LABELS = {
    STATUS_DONE: "Готово",
    STATUS_RUNNING: "В работе",
    STATUS_BLOCKED: "Заблокировано",
    STATUS_WAITING: "Ожидание",
    STATUS_DEFERRED: "Отложено владельцем",
    STATUS_QUEUED: "В очереди",
}

# Status names a graph may use for the same state. A name outside this table
# is kept as it is and reported as unknown: an unreadable state must never be
# silently treated as "ready to start".
STATUS_ALIASES = {
    "done": STATUS_DONE, "complete": STATUS_DONE, "completed": STATUS_DONE,
    "finished": STATUS_DONE, "готово": STATUS_DONE,
    "running": STATUS_RUNNING, "in_progress": STATUS_RUNNING, "active": STATUS_RUNNING,
    "в_работе": STATUS_RUNNING,
    "blocked": STATUS_BLOCKED, "blocker": STATUS_BLOCKED, "заблокировано": STATUS_BLOCKED,
    "waiting": STATUS_WAITING, "wait": STATUS_WAITING, "ожидание": STATUS_WAITING,
    "deferred": STATUS_DEFERRED, "defer": STATUS_DEFERRED, "отложено": STATUS_DEFERRED,
    "отложен": STATUS_DEFERRED, "отложено_владельцем": STATUS_DEFERRED,
    "queued": STATUS_QUEUED, "todo": STATUS_QUEUED, "pending": STATUS_QUEUED,
    "в_очереди": STATUS_QUEUED,
}

GRAPH_HINT = (
    "ожидается файл графа задач: JSON-объект со списком \"tasks\", где у каждой "
    "задачи есть id, label, status и depends_on"
)


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------


@dataclass
class Task:
    """One leaf of the task graph."""

    id: str
    label: str = ""
    status: str = STATUS_QUEUED
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    estimate_min: Optional[float] = None
    estimate_max: Optional[float] = None
    actual_minutes: Optional[float] = None
    blocker: str = ""
    blocker_details: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    owner: str = ""
    session: str = ""
    started_at: str = ""
    finished_at: str = ""
    wave: Optional[int] = None
    order: int = 0

    @property
    def estimate_label(self) -> str:
        """The estimate as one short readable fragment."""

        if self.estimate_min is None and self.estimate_max is None:
            return "оценка не указана"
        low = self.estimate_min if self.estimate_min is not None else self.estimate_max
        high = self.estimate_max if self.estimate_max is not None else self.estimate_min
        if low is None or high is None:
            return "оценка не указана"
        if low == high:
            return f"оценка {fmt_minutes(low)}"
        return f"оценка {fmt_range(low, high)}"

    @property
    def blocker_reason(self) -> str:
        """The concrete obstacle of a blocked leaf.

        The flat ``blocker`` field comes first. A ``blocker_details.reason``
        written by another part of the repository is used when the flat field
        is empty; its absence is never an error.
        """

        if self.blocker:
            return self.blocker
        detail = self.blocker_details.get("reason")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if self.note:
            return self.note
        return "причина не указана"

    @property
    def duration(self) -> float:
        """The weight of this line in the critical path: its upper estimate."""

        for value in (self.estimate_max, self.estimate_min):
            if value is not None:
                return float(value)
        return 1.0


@dataclass
class Graph:
    """The parsed task graph: the plan's machine artifact."""

    title: str = ""
    goal: str = ""
    business_result: str = ""
    slots: Optional[int] = None
    updated_at: str = ""
    tasks: list[Task] = field(default_factory=list)
    source_path: str = ""

    def by_id(self) -> dict[str, Task]:
        """Index the leaves by id."""

        return {task.id: task for task in self.tasks}


@dataclass
class Summary:
    """The answer to "what can start right now", computed from one graph."""

    graph: Graph
    ready: list[Task] = field(default_factory=list)
    deferred: list[Task] = field(default_factory=list)
    running: list[Task] = field(default_factory=list)
    blocked: list[tuple[Task, str]] = field(default_factory=list)
    waiting: list[tuple[Task, list[str]]] = field(default_factory=list)
    unknown_status: list[Task] = field(default_factory=list)
    free_slots: Optional[int] = None
    critical_path: list[str] = field(default_factory=list)
    slot_of: dict[str, int] = field(default_factory=dict)

    @property
    def slots(self) -> Optional[int]:
        """The declared number of parallel lanes, when the graph declares it."""

        return self.graph.slots

    def unblocks(self, task: Task) -> list[str]:
        """Ids of the lines that wait for this one."""

        return [
            other.id for other in self.graph.tasks
            if task.id in other.depends_on
        ]

    def next_step(self) -> Optional[Task]:
        """The ready line that unblocks the most work: the first step."""

        if not self.ready:
            return None
        for task_id in self.critical_path:
            for task in self.ready:
                if task.id == task_id:
                    return task
        return self.ready[0]


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------


def fmt_minutes(value: Optional[float]) -> str:
    """Render a minute count as a short Russian fragment."""

    if value is None:
        return "н/д"
    if float(value).is_integer():
        return f"{int(value)} мин"
    return f"{value:.1f} мин".replace(".", ",")


def fmt_range(low: Optional[float], high: Optional[float]) -> str:
    """Render an estimate range with the unit written once."""

    if low is None or high is None:
        return "н/д"
    if low == high:
        return fmt_minutes(low)
    left = f"{int(low)}" if float(low).is_integer() else f"{low:.1f}".replace(".", ",")
    right = f"{int(high)}" if float(high).is_integer() else f"{high:.1f}".replace(".", ",")
    return f"{left}–{right} мин"


def normalize_status(value: Any) -> str:
    """Map a graph status onto a known state, or keep it as an unknown name."""

    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if text in STATUSES:
        return text
    return STATUS_ALIASES.get(text, text)


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ".").strip())
        except ValueError:
            return None
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------


def parse_graph_json(document: Any) -> Graph:
    """Build a graph from one decoded JSON document."""

    if not isinstance(document, dict):
        raise ValueError(f"граф задач должен быть JSON-объектом, а не {type(document).__name__}")
    version = document.get("schema_version")
    if version is not None and version not in SCHEMA_VERSIONS:
        raise ValueError(f"неподдерживаемая версия schema_version: {version!r}")
    graph = Graph(
        title=_text(document.get("title")),
        goal=_text(document.get("goal")),
        business_result=_text(document.get("business_result")),
        updated_at=_text(document.get("updated_at")),
    )
    slots = _number(document.get("slots"))
    if slots is not None:
        graph.slots = int(slots) if slots >= 0 else None
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError(f"в графе нет списка \"tasks\": {GRAPH_HINT}")
    if not tasks:
        raise ValueError("граф не содержит ни одной задачи")
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] должен быть объектом, а не {type(task).__name__}")
        task_id = _text(task.get("id"))
        if not task_id:
            raise ValueError(f"tasks[{index}]: отсутствует обязательное поле id")
        depends_on = task.get("depends_on")
        if depends_on is None:
            depends_on = []
        if not isinstance(depends_on, list):
            raise ValueError(f"tasks[{index}] ({task_id}): depends_on должен быть списком")
        estimate = task.get("estimate_minutes")
        estimate_min = estimate_max = None
        if isinstance(estimate, dict):
            estimate_min = _number(estimate.get("minimum"))
            estimate_max = _number(estimate.get("maximum"))
        elif isinstance(estimate, (int, float)) and not isinstance(estimate, bool):
            estimate_min = estimate_max = float(estimate)
        wave = task.get("wave")
        blocker_details = task.get("blocker_details")
        if not isinstance(blocker_details, dict):
            blocker_details = {}
        graph.tasks.append(
            Task(
                id=task_id,
                label=_text(task.get("label")),
                status=normalize_status(task.get("status") or STATUS_QUEUED),
                depends_on=[_text(item) for item in depends_on if _text(item)],
                parallel_with=[_text(item) for item in (task.get("parallel_with") or []) if _text(item)],
                estimate_min=estimate_min,
                estimate_max=estimate_max,
                actual_minutes=_number(task.get("actual_minutes")),
                blocker=_text(task.get("blocker")),
                blocker_details={str(key): value for key, value in blocker_details.items()},
                note=_text(task.get("note")),
                owner=_text(task.get("owner")),
                session=_text(task.get("session")),
                started_at=_text(task.get("started_at")),
                finished_at=_text(task.get("finished_at")),
                wave=wave if isinstance(wave, int) and not isinstance(wave, bool) else None,
                order=index,
            )
        )
    return graph


def load_graph(path: Path) -> Graph:
    """Read one task graph file and parse it.

    Every failure is a readable diagnostic: an unreadable or broken graph is
    an error to report, never a traceback and never an empty answer.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValueError(f"файл графа не найден: {path}") from error
    except OSError as error:
        raise ValueError(f"файл графа не прочитан: {path} ({error})") from error
    except UnicodeDecodeError as error:
        raise ValueError(f"файл графа не в UTF-8: {path} ({error})") from error
    if not text.strip():
        raise ValueError(f"файл графа пуст: {path}")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"файл графа не является корректным JSON: {path} ({error})") from error
    graph = parse_graph_json(document)
    graph.source_path = str(path)
    if not graph.title:
        graph.title = path.stem
    return graph


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------


def _layers(tasks: dict[str, Task], order: list[str]) -> dict[str, int]:
    """Derive the wave of every leaf from its dependencies."""

    layers: dict[str, int] = {}

    def layer_of(task_id: str, seen: frozenset[str]) -> int:
        if task_id in layers:
            return layers[task_id]
        task = tasks.get(task_id)
        if task is None or task_id in seen:
            return 0
        best = 0
        for dep in task.depends_on:
            if dep in tasks:
                best = max(best, layer_of(dep, seen | {task_id}) + 1)
        layers[task_id] = best
        return best

    for task_id in order:
        layer_of(task_id, frozenset())
    return layers


def _critical_path(tasks: dict[str, Task], order: list[str]) -> list[str]:
    """The longest dependency chain of the unfinished work, by estimate.

    The chain is ordered from the first prerequisite to the last dependent,
    so it reads as "L03 → L05 → L07".
    """

    memo: dict[str, list[str]] = {}
    visiting: set[str] = set()

    def chain_weight(chain_ids: list[str]) -> float:
        return sum(tasks[item].duration for item in chain_ids if item in tasks)

    def chain(task_id: str) -> list[str]:
        if task_id in memo:
            return memo[task_id]
        if task_id in visiting:
            # A dependency cycle is broken here; the graph is reported as is.
            return [task_id]
        visiting.add(task_id)
        task = tasks.get(task_id)
        best: list[str] = []
        if task is not None:
            for dep in task.depends_on:
                if dep in tasks and tasks[dep].status != STATUS_DONE:
                    candidate = chain(dep)
                    if chain_weight(candidate) > chain_weight(best):
                        best = candidate
        visiting.discard(task_id)
        result = best + [task_id]
        memo[task_id] = result
        return result

    best_chain: list[str] = []
    for task_id in order:
        task = tasks.get(task_id)
        if task is None or task.status == STATUS_DONE:
            continue
        candidate = chain(task_id)
        if chain_weight(candidate) > chain_weight(best_chain):
            best_chain = candidate
    return best_chain


def analyze(graph: Graph) -> Summary:
    """Compute the dispatch answer for one graph."""

    tasks = graph.by_id()
    order = [task.id for task in graph.tasks]
    layers = _layers(tasks, order)
    summary = Summary(graph=graph)

    for task in graph.tasks:
        if task.status == STATUS_RUNNING:
            summary.running.append(task)
        elif task.status == STATUS_BLOCKED:
            summary.blocked.append((task, task.blocker_reason))
        elif task.status == STATUS_WAITING:
            summary.waiting.append((task, []))
        elif task.status == STATUS_DEFERRED:
            # The owner deferred this line: no answer is expected, so it waits
            # for nothing and it takes no slot.
            continue
        elif task.status not in STATUSES:
            summary.unknown_status.append(task)

    running_count = len(summary.running)
    if graph.slots is None:
        summary.free_slots = None
    else:
        summary.free_slots = max(0, graph.slots - running_count)

    # One rule of the count of blockers: a line is blocked when its status says
    # so. A blocker text alone does not change the state of a queued line.
    for task in graph.tasks:
        if task.status != STATUS_QUEUED:
            continue
        unmet: list[str] = []
        for dep in task.depends_on:
            dependency = tasks.get(dep)
            if dependency is None:
                unmet.append(dep)
            elif dependency.status != STATUS_DONE:
                unmet.append(dep)
        if unmet:
            summary.waiting.append((task, unmet))
            continue
        summary.ready.append(task)

    def sort_key(task: Task) -> tuple[int, int]:
        wave = task.wave if task.wave is not None else layers.get(task.id, 0)
        return (wave, task.order)

    summary.ready.sort(key=sort_key)
    summary.waiting.sort(key=lambda item: sort_key(item[0]))
    summary.blocked.sort(key=lambda item: sort_key(item[0]))

    if summary.free_slots is None:
        summary.deferred = []
    else:
        summary.deferred = summary.ready[summary.free_slots:]
        summary.ready = summary.ready[:summary.free_slots]

    for index, task in enumerate(summary.ready, start=1):
        summary.slot_of[task.id] = index

    summary.critical_path = _critical_path(tasks, order)
    return summary


def summarize(path: Path) -> Summary:
    """Load one graph file and analyze it."""

    return analyze(load_graph(path))


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _task_dict(summary: Summary, task: Task) -> dict[str, Any]:
    """One task as a machine-readable record."""

    payload: dict[str, Any] = {
        "id": task.id,
        "label": task.label,
        "status": task.status,
        "estimate_minutes": {
            "minimum": task.estimate_min,
            "maximum": task.estimate_max,
        },
        "depends_on": list(task.depends_on),
        "unblocks": summary.unblocks(task),
    }
    if task.owner:
        payload["owner"] = task.owner
    if task.started_at:
        payload["started_at"] = task.started_at
    if task.actual_minutes is not None:
        payload["actual_minutes"] = task.actual_minutes
    if task.wave is not None:
        payload["wave"] = task.wave
    if task.blocker_details:
        payload["blocker_details"] = task.blocker_details
    return payload


def to_dict(summary: Summary, *, show_slots: bool = False) -> dict[str, Any]:
    """The whole answer as a machine-readable object."""

    graph = summary.graph
    payload: dict[str, Any] = {
        "source": graph.source_path,
        "title": graph.title,
        "goal": graph.goal,
        "business_result": graph.business_result,
        "updated_at": graph.updated_at,
        "slots": graph.slots,
        "slots_declared": graph.slots is not None,
        "free_slots": summary.free_slots,
        "counts": {
            "total": len(graph.tasks),
            "done": sum(1 for task in graph.tasks if task.status == STATUS_DONE),
            "running": len(summary.running),
            "blocked": len(summary.blocked),
            "waiting": len(summary.waiting),
            "ready": len(summary.ready),
            "deferred": len(summary.deferred),
        },
        "running": [_task_dict(summary, task) for task in summary.running],
        "ready": [],
        "deferred": [],
        "waiting": [],
        "blocked": [],
        "critical_path": list(summary.critical_path),
    }
    for task in summary.ready:
        record = _task_dict(summary, task)
        if show_slots:
            record["slot"] = summary.slot_of.get(task.id)
        payload["ready"].append(record)
    for task in summary.deferred:
        record = _task_dict(summary, task)
        record["reason"] = "нет свободного слота"
        payload["deferred"].append(record)
    for task, unmet in summary.waiting:
        record = _task_dict(summary, task)
        record["waits_for"] = [
            {
                "id": dep,
                "label": index[dep].label if dep in index else "",
                "status": index[dep].status if dep in index else "unknown",
            }
            for dep in unmet
        ]
        payload["waiting"].append(record)
    for task, reason in summary.blocked:
        record = _task_dict(summary, task)
        record["reason"] = reason
        payload["blocked"].append(record)
    if summary.unknown_status:
        payload["unknown_status"] = [
            {"id": task.id, "label": task.label, "status": task.status}
            for task in summary.unknown_status
        ]
    next_task = summary.next_step()
    payload["next_step"] = _task_dict(summary, next_task) if next_task is not None else None
    return payload


def render_text(summary: Summary, *, show_slots: bool = False) -> str:
    """The answer as one readable Russian text."""

    graph = summary.graph
    tasks = graph.by_id()
    lines: list[str] = []
    lines.append(f"Параллельные линии: {graph.title or 'без названия'}")
    if graph.goal:
        lines.append(f"Цель: {graph.goal}")
    if graph.slots is None:
        lines.append(
            "Слотов в графе нет: ограничения на число параллельных линий не задано."
        )
    else:
        lines.append(
            "Слотов: {slots} · в работе: {running} · свободно: {free}".format(
                slots=graph.slots, running=len(summary.running), free=summary.free_slots
            )
        )

    lines.append("")
    lines.append(f"Сейчас в работе ({len(summary.running)}):")
    if summary.running:
        for task in summary.running:
            parts = [f"  - {task.id}", f"«{task.label}»" if task.label else "", task.estimate_label]
            if task.started_at:
                parts.append(f"старт {task.started_at}")
            if task.owner:
                parts.append(f"владелец {task.owner}")
            lines.append(" · ".join(part for part in parts if part))
    else:
        lines.append("  — ни одна линия сейчас не идёт")

    free_text = "свободно слотов: {}".format(
        summary.free_slots if summary.free_slots is not None else "без ограничения"
    )
    lines.append("")
    lines.append(f"Готовы к запуску ({free_text}):")
    if summary.ready:
        for task in summary.ready:
            parts = [f"  - {task.id}", f"«{task.label}»" if task.label else "", task.estimate_label]
            if show_slots:
                parts.append(f"слот {summary.slot_of.get(task.id, '?')}")
            dependents = summary.unblocks(task)
            if dependents:
                parts.append("разблокирует: " + ", ".join(dependents))
            lines.append(" · ".join(part for part in parts if part))
    else:
        lines.append("  — сейчас запускать нечего")

    if summary.deferred:
        lines.append("")
        lines.append(f"Готовы, но ждут свободного слота ({len(summary.deferred)}):")
        for task in summary.deferred:
            parts = [f"  - {task.id}", f"«{task.label}»" if task.label else "", task.estimate_label]
            lines.append(" · ".join(part for part in parts if part))

    if summary.waiting:
        lines.append("")
        lines.append(f"Ждут зависимостей ({len(summary.waiting)}):")
        for task, unmet in summary.waiting:
            details = []
            for dep in unmet:
                dependency = tasks.get(dep)
                if dependency is None:
                    details.append(f"{dep} (нет такой задачи в графе)")
                else:
                    label = f" «{dependency.label}»" if dependency.label else ""
                    details.append(f"{dep}{label} — {STATUS_LABELS.get(dependency.status, dependency.status)}")
            lines.append(f"  - {task.id} «{task.label}» — ждёт: " + ", ".join(details))

    if summary.blocked:
        lines.append("")
        lines.append(f"Заблокированы ({len(summary.blocked)}):")
        for task, reason in summary.blocked:
            lines.append(f"  - {task.id} «{task.label}» — {reason}")

    # A line the owner deferred is not waiting for anything and it is not
    # blocked: it is named apart, so it does not disappear from the answer.
    deferred_by_owner = [task for task in graph.tasks if task.status == STATUS_DEFERRED]
    if deferred_by_owner:
        lines.append("")
        lines.append(f"Отложено владельцем ({len(deferred_by_owner)}):")
        for task in deferred_by_owner:
            lines.append(f"  - {task.id} «{task.label}» — ответа не ждём")

    if summary.unknown_status:
        lines.append("")
        lines.append(f"Неизвестный статус ({len(summary.unknown_status)}):")
        for task in summary.unknown_status:
            lines.append(f"  - {task.id} «{task.label}» — статус «{task.status}»")

    lines.append("")
    if summary.critical_path:
        lines.append("Критический путь: " + " → ".join(summary.critical_path))
    next_task = summary.next_step()
    if next_task is not None:
        lines.append(
            f"Следующий шаг: запустить {next_task.id} «{next_task.label}»"
            + (f" (слот {summary.slot_of.get(next_task.id)})" if show_slots else "")
        )
    elif summary.running:
        lines.append("Следующий шаг: дождаться текущих линий — новых готовых линий нет.")
    else:
        lines.append("Следующий шаг: готовых линий нет.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lhc_parallel.py",
        description="Показать, какие параллельные линии плана можно запустить прямо сейчас.",
    )
    parser.add_argument("plan_graph", type=Path, help="файл графа задач (plan.graph.json)")
    parser.add_argument("--json", action="store_true", help="вывести машинный JSON вместо текста")
    parser.add_argument(
        "--slot", action="store_true",
        help="показать, в какой слот попадает каждая готовая линия",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = summarize(args.plan_graph)
    except ValueError as error:
        print(f"lhc_parallel: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"lhc_parallel: файл графа недоступен: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(to_dict(summary, show_slots=args.slot), ensure_ascii=False, indent=2))
    else:
        print(render_text(summary, show_slots=args.slot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
