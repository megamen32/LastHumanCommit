#!/usr/bin/env python3
"""One JSON file per leaf: the single source of truth of a plan.

A plan lives in one directory. Every leaf of the plan is one JSON file in the
``leaves/`` subdirectory, named after the leaf: ``leaves/L12.json``. The owner
of a leaf changes his own file and nothing else, so two workers never write the
same file and never wait for each other.

Those files are collected into one ``plan.graph.json`` of the existing graph
schema, which the renderer already reads without a single change. The
collector is deterministic: the same inputs produce byte for byte the same
graph, so a rebuilt plan is comparable with the one before it and the order of
the leaves does not depend on the order the filesystem hands them over.

Plan-level facts - the goal, the business result, the number of slots - are
not a leaf's business. They live in ``plan.json`` next to ``leaves/``. When
that file is absent the collector falls back to the plan-level fields of the
existing ``plan.graph.json``, and to the defaults of the reader when there is
none. A plan without a ``leaves/`` directory is not this collector's plan:
the behaviour of such a plan stays exactly as it was.

Usage::

    python3 lhc_plan_json.py build <plan-dir>   # collect the leaves into plan.graph.json
    python3 lhc_plan_json.py check <plan-dir>   # validate the leaves, write nothing
    python3 lhc_plan_json.py activate <plan-dir> <leaf-id>  # bind the selected live leaf offline
    python3 lhc_plan_json.py report <plan-dir>  # print the canonical «## Plan» block
    python3 lhc_plan_json.py report <plan-dir> --write   # rewrite it in task.md
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
from datetime import datetime, timezone
import difflib
import importlib.util
import json
import os
import re
import sys
import ctypes
import struct
from pathlib import Path
from typing import Any, Optional

LEAVES_DIRNAME = "leaves"
PLAN_FILE = "plan.json"
GRAPH_FILE = "plan.graph.json"

# The economics vocabulary of a leaf. A leaf declares its own model class and
# its own complexity; the plan kernel turns those two into a model, a token
# estimate and a dollar cost (`lhc_grid.py` prices them from the live catalog).
# These are the only accepted spellings, and they are enums on purpose: a free
# string here would let one executor invent a fourth class of model and a plan
# would price it as if it were a fact.
TIERS = ("fast", "frontier")
COMPLEXITIES = ("S", "M", "L")
COST_SOURCES = ("measured", "provisional")

# The format (PLAN_REPORT.md, TASK_GRAPH.md) says a leaf is about fifteen minutes
# and a longer job is two leaves. That cap lived only in the prose; the collector
# silently accepted a 30–50 minute leaf. `check` now names the breach and exits
# nonzero, unless the leaf records, in its own words, why it is deliberately
# larger — so the rule is a signpost, not a blind barrier.
LEAF_ESTIMATE_CAP_MINUTES = 15

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_WAITING = "waiting"
STATUS_DEFERRED = "deferred"
STATUS_DONE = "done"

STATUSES = (
    STATUS_DONE,
    STATUS_RUNNING,
    STATUS_BLOCKED,
    STATUS_WAITING,
    STATUS_DEFERRED,
    STATUS_QUEUED,
)

# The words a worker may write instead of the canonical status. The markers of
# the markdown report are here too, so moving a leaf from the report to its own
# file does not lose the vocabulary it was written in.
STATUS_ALIASES = {
    "done": STATUS_DONE,
    "complete": STATUS_DONE,
    "completed": STATUS_DONE,
    "finished": STATUS_DONE,
    "готово": STATUS_DONE,
    "✅": STATUS_DONE,
    "running": STATUS_RUNNING,
    "in_progress": STATUS_RUNNING,
    "active": STATUS_RUNNING,
    "в_работе": STATUS_RUNNING,
    "🔄": STATUS_RUNNING,
    "blocked": STATUS_BLOCKED,
    "blocker": STATUS_BLOCKED,
    "заблокировано": STATUS_BLOCKED,
    "⛔": STATUS_BLOCKED,
    "waiting": STATUS_WAITING,
    "wait": STATUS_WAITING,
    "ожидание": STATUS_WAITING,
    "⌛": STATUS_WAITING,
    "deferred": STATUS_DEFERRED,
    "defer": STATUS_DEFERRED,
    "отложено": STATUS_DEFERRED,
    "отложен": STATUS_DEFERRED,
    "отложено_владельцем": STATUS_DEFERRED,
    "⏸": STATUS_DEFERRED,
    "queued": STATUS_QUEUED,
    "todo": STATUS_QUEUED,
    "pending": STATUS_QUEUED,
    "в_очереди": STATUS_QUEUED,
    "⏳": STATUS_QUEUED,
    "⋯": STATUS_QUEUED,
}

# The fields one leaf file may carry. The names are the names of a task of the
# graph schema, so a collected leaf is a task the existing reader understands
# without a translation table.
#
# `result` is the executor's own answer for the leaf: it happened today that a
# finished worker wrote `result` into his leaf file, the collector rejected the
# unknown field, and the whole build stopped - one extra word of one executor
# broke the chain. A leaf's result is real leaf data, so it is a first-class
# field here, not a text smuggled into `note`.
LEAF_FIELDS = (
    "id",
    "label",
    "description",
    "acceptance",
    "result",
    "affected_files",
    "status",
    "owner",
    "session",
    "harness",
    "model",
    "model_class",
    "tier",
    "complexity",
    "token_estimate",
    "cost_usd",
    "cost_source",
    "depends_on",
    "parallel_with",
    "estimate_minutes",
    "estimate",
    "estimate_min",
    "estimate_max",
    "estimate_unknown_reason",
    # A leaf longer than the 15-minute cap is a real situation (the cost kernel
    # itself is one), but it must never pass silently: the leaf names why it is
    # deliberately large, and only that named reason lets it through `check`.
    "estimate_over_limit_reason",
    # What a leaf in the queue owes the report: why it cannot start yet, and the
    # planned start and finish. The format promises these; without fields to hold
    # them the projection of a human plan cannot say them.
    "wait_reason",
    "planned_start",
    "planned_finish",
    "actual_minutes",
    "created_at",
    "started_at",
    "finished_at",
    "blocker",
    "blocker_details",
    "note",
    "wave",
    "updated_at",
    "progress_events",
    "supersedes",
    "origin",
    "duration_estimate_minutes",
)

# The plan-level fields. They belong to the plan, not to a leaf, so they live
# in one file instead of being copied into every leaf.
PLAN_FIELDS = (
    "default_model",
    "title",
    "goal",
    "business_result",
    "business_results",
    "acceptance_scenarios",
    "current_progress",
    "revisions",
    "external_waits",
    "slots",
    "budget_usd",
    "updated_at",
    "journal",
    "planned_start_at",
    "started_at",
    "finished_at",
)

CLOCK_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


class LeafError(ValueError):
    """A leaf that cannot be collected. The message always names the file."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def natural_key(text: str) -> tuple:
    """Sort key that puts L2 before L10 and keeps the order of the ids."""

    parts = re.split(r"(\d+)", text or "")
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part)
        for part in parts
        if part != ""
    )


def _read_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise LeafError(f"{path}: файл не прочитан: {error}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise LeafError(f"{path}: битый JSON: {error}") from error


def _text(raw: dict[str, Any], field: str, path: Path) -> str:
    value = raw.get(field)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise LeafError(f"{path}: поле {field} должно быть строкой")
    return value.strip()


def _string_list(raw: dict[str, Any], field: str, path: Path) -> list[str]:
    value = raw.get(field)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LeafError(f"{path}: поле {field} должно быть списком строк")
    return [item.strip() for item in value if item.strip()]


def _minutes(value: Any, field: str, path: Path) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LeafError(f"{path}: поле {field} должно быть числом минут")
    if value < 0:
        raise LeafError(f"{path}: поле {field} не может быть отрицательным")
    return float(value)


def _estimate_bounds(value: Any, field: str, path: Path) -> dict[str, float]:
    """The bounds of an estimate, written in any of the accepted shapes."""

    if isinstance(value, bool):
        raise LeafError(f"{path}: поле {field} должно быть числом или объектом границ")
    if isinstance(value, (int, float)):
        number = _minutes(value, field, path)
        assert number is not None
        return {"minimum": number, "maximum": number}
    if not isinstance(value, dict):
        raise LeafError(f"{path}: поле {field} должно быть числом или объектом границ")
    low = value.get("minimum", value.get("min"))
    high = value.get("maximum", value.get("max"))
    bounds: dict[str, float] = {}
    if low is not None:
        number = _minutes(low, f"{field}.minimum", path)
        assert number is not None
        bounds["minimum"] = number
    if high is not None:
        number = _minutes(high, f"{field}.maximum", path)
        assert number is not None
        bounds["maximum"] = number
    if not bounds:
        raise LeafError(f"{path}: поле {field} не содержит границ оценки")
    return bounds


def _estimate(raw: dict[str, Any], path: Path) -> Optional[dict[str, float]]:
    for field in ("estimate_minutes", "estimate"):
        value = raw.get(field)
        if value is not None:
            return _estimate_bounds(value, field, path)
    low = raw.get("estimate_min")
    high = raw.get("estimate_max")
    if low is None and high is None:
        return None
    bounds: dict[str, float] = {}
    if low is not None:
        number = _minutes(low, "estimate_min", path)
        assert number is not None
        bounds["minimum"] = number
    if high is not None:
        number = _minutes(high, "estimate_max", path)
        assert number is not None
        bounds["maximum"] = number
    return bounds


def _clock(raw: dict[str, Any], field: str, path: Path) -> str:
    value = _text(raw, field, path)
    if not value:
        return ""
    if not CLOCK_RE.match(value):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone required")
        except ValueError as error:
            raise LeafError(
                f"{path}: {field}: нужен ЧЧ:ММ либо ISO timestamp с часовым поясом"
            ) from error
    return value


def _status(value: Any, path: Path) -> str:
    if value is None or value == "":
        return STATUS_QUEUED
    if not isinstance(value, str):
        raise LeafError(f"{path}: поле status должно быть строкой")
    text = value.strip().lower().replace(" ", "_").replace("-", "_")
    if text in STATUS_ALIASES:
        return STATUS_ALIASES[text]
    if text in STATUSES:
        return text
    raise LeafError(
        f"{path}: неизвестный статус «{value}»; допустимые статусы: "
        + ", ".join(STATUSES)
    )


def _enum(raw: dict[str, Any], field: str, allowed: tuple[str, ...], path: Path,
          *, fold: str = "lower") -> str:
    """One value of a closed vocabulary, or a message that names the vocabulary."""

    value = _text(raw, field, path)
    if not value:
        return ""
    candidate = value.lower() if fold == "lower" else value.upper()
    if candidate not in allowed:
        raise LeafError(
            f"{path}: поле {field} = «{value}»; допустимы только {', '.join(allowed)}"
        )
    return candidate


def _whole_count(raw: dict[str, Any], field: str, path: Path) -> Optional[int]:
    """A counted quantity (tokens): a whole, non-negative number, never a string."""

    value = raw.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise LeafError(f"{path}: поле {field} должно быть целым числом токенов")
    if value < 0:
        raise LeafError(f"{path}: поле {field} не может быть отрицательным")
    return value


def _money(raw: dict[str, Any], field: str, path: Path) -> Optional[float]:
    """A declared amount of money: a number, never a word, never negative."""

    value = raw.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LeafError(f"{path}: поле {field} должно быть числом долларов")
    if value < 0:
        raise LeafError(f"{path}: поле {field} не может быть отрицательным")
    return float(value)


def unknown_field_error(path: Path, unknown: list[str]) -> LeafError:
    """The gate stays shut, but it says what to do instead of reciting the schema.

    A bare list of every accepted field is what stopped a finished worker today:
    he had one extra word and no clue which field it belonged to. Each rejected
    name is now answered with its nearest accepted alternatives, with the plan
    file when the name is a plan-level fact, and with the honest way to add a
    genuinely new field.
    """

    lines = []
    for field in unknown:
        close = difflib.get_close_matches(field, LEAF_FIELDS, n=3, cutoff=0.4)
        parts = []
        if field in PLAN_FIELDS:
            parts.append(
                f"«{field}» — факт уровня плана, он пишется в {PLAN_FILE}, а не в лист"
            )
        if close:
            parts.append("ближайшие принятые поля листа: " + ", ".join(close))
        if field in {"result", "итог", "результат"}:
            parts.append("для ответа исполнителя есть поле result")
        if field in {"cost", "price", "usd", "dollars"}:
            parts.append("для стоимости есть пара cost_usd + cost_source (measured|provisional)")
        if field in {"class", "model_tier", "класс"}:
            parts.append("для класса модели есть поле tier (fast|frontier)")
        if not parts:
            parts.append("принятое поле с таким именем отсутствует")
        parts.append(
            "если поле правда новое — его добавляет правка схемы в LEAF_FIELDS, "
            "а не молча проглоченное значение"
        )
        lines.append(f"  - {field}: " + "; ".join(parts))
    return LeafError(
        f"{path}: неизвестные поля листа — {', '.join(unknown)}. "
        + " Исправь так: "
        + " ".join(lines)
    )


# --------------------------------------------------------------------------
# one leaf
# --------------------------------------------------------------------------


def task_from_leaf(raw: Any, path: Path) -> dict[str, Any]:
    """One leaf file into one task of the graph schema."""

    if not isinstance(raw, dict):
        raise LeafError(f"{path}: лист должен быть объектом JSON")
    unknown = sorted(set(raw) - set(LEAF_FIELDS))
    if unknown:
        raise unknown_field_error(path, unknown)

    leaf_id = _text(raw, "id", path)
    if not leaf_id:
        raise LeafError(f"{path}: нет поля id")
    if leaf_id != path.stem:
        raise LeafError(
            f"{path}: id «{leaf_id}» не совпадает с именем файла «{path.stem}»"
        )

    label = _text(raw, "label", path)
    if not label:
        raise LeafError(f"{path}: нет названия листа (label)")

    task: dict[str, Any] = {
        "id": leaf_id,
        "label": label,
        "status": _status(raw.get("status"), path),
    }

    for field in ("description", "acceptance", "result", "owner", "session", "harness",
                  "model", "model_class", "note", "blocker",
                  "estimate_unknown_reason", "estimate_over_limit_reason", "wait_reason"):
        value = _text(raw, field, path)
        if value:
            task[field] = value

    # The economics of the leaf. `tier` and `complexity` are what the leaf
    # declares about itself; `token_estimate`/`cost_usd`/`cost_source` are the
    # numbers it already knows, and a number of money without its provenance is
    # not a number a person may read as a fact.
    tier = _enum(raw, "tier", TIERS, path)
    if tier:
        task["tier"] = tier
    complexity = _enum(raw, "complexity", COMPLEXITIES, path, fold="upper")
    if complexity:
        task["complexity"] = complexity
    cost_source = _enum(raw, "cost_source", COST_SOURCES, path)
    tokens = _whole_count(raw, "token_estimate", path)
    if tokens is not None:
        task["token_estimate"] = tokens
    cost = _money(raw, "cost_usd", path)
    if cost is not None:
        if not cost_source:
            raise LeafError(
                f"{path}: cost_usd = {cost} без cost_source: цифра в долларах обязана "
                "говорить, откуда она (measured — снято с замера или каталога, "
                "provisional — условная константа планирования); "
                "без метки источника стоимость не показывается"
            )
        task["cost_usd"] = cost
    if cost_source:
        task["cost_source"] = cost_source

    task["origin"] = _text(raw, "origin", path)
    task["supersedes"] = _string_list(raw, "supersedes", path)
    events = raw.get("progress_events", [])
    if not isinstance(events, list) or any(
        not isinstance(e, dict) or set(e) - {"at", "note", "changes", "session", "harness"}
        or not isinstance(e.get("at"), str) or not isinstance(e.get("note", ""), str)
        or not isinstance(e.get("changes", {}), dict) for e in events
    ):
        raise LeafError(f"{path}: неверные progress_events")
    if events:
        task["progress_events"] = events

    affected = _string_list(raw, "affected_files", path)
    if affected:
        task["affected_files"] = affected

    # `depends_on` is required per task by the graph contract and by the
    # offline checker, so it is always written - an empty list says "nothing
    # blocks this leaf" in the same words the contract uses.
    task["depends_on"] = _string_list(raw, "depends_on", path)
    values = _string_list(raw, "parallel_with", path)
    if values:
        task["parallel_with"] = values

    bounds = _estimate(raw, path)
    if bounds is not None:
        task["estimate_minutes"] = bounds

    actual = _minutes(raw.get("actual_minutes"), "actual_minutes", path)
    if actual is not None:
        task["actual_minutes"] = actual

    if raw.get("created_at"):
        if origin_time(raw["created_at"]) is None:
            raise LeafError(f"{path}: created_at требует ISO с часовым поясом")
        task["created_at"] = raw["created_at"]
    for field in ("started_at", "finished_at", "planned_start", "planned_finish"):
        value = _clock(raw, field, path)
        if value:
            task[field] = value

    details = raw.get("blocker_details")
    if details is not None:
        if not isinstance(details, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in details.items()
        ):
            raise LeafError(f"{path}: поле blocker_details должно быть объектом строк")
        if details:
            task["blocker_details"] = {key: value.strip() for key, value in details.items()}

    wave = raw.get("wave")
    if wave is not None:
        if isinstance(wave, bool) or not isinstance(wave, int) or wave < 0:
            raise LeafError(f"{path}: поле wave должно быть неотрицательным целым числом")
        task["wave"] = wave

    return task


def read_leaf(path: Path) -> dict[str, Any]:
    """Read and validate one leaf file into one task of the graph schema."""

    return task_from_leaf(_read_json(Path(path)), Path(path))


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------


def _collect(
    plan_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Path], dict[str, str]]:
    """The leaves of a plan, the file each came from and its own stamp."""

    default_model = plan_metadata(plan_dir).get("default_model")
    leaves_dir = Path(plan_dir) / LEAVES_DIRNAME
    if not leaves_dir.is_dir():
        raise LeafError(f"{plan_dir}: каталог {LEAVES_DIRNAME}/ не найден")
    paths = sorted(leaves_dir.glob("*.json"), key=lambda item: natural_key(item.stem))
    tasks: list[dict[str, Any]] = []
    sources: dict[str, Path] = {}
    stamps: dict[str, str] = {}
    for path in paths:
        raw = _read_json(path)
        task = task_from_leaf(raw, path)
        _inherit_default_model(task, default_model)
        leaf_id = task["id"]
        if leaf_id in sources:
            raise LeafError(f"{path}: лист «{leaf_id}» уже есть в {sources[leaf_id]}")
        sources[leaf_id] = path
        stamp = raw.get("updated_at") if isinstance(raw, dict) else None
        stamps[leaf_id] = stamp.strip() if isinstance(stamp, str) else ""
        tasks.append(task)
    if not tasks:
        raise LeafError(f"{leaves_dir}: в каталоге нет ни одного листа")
    return tasks, sources, stamps


def collect_leaves(plan_dir: Path) -> list[dict[str, Any]]:
    """The leaves of a plan, validated and ready to be collected."""

    tasks, _sources, _stamps = _collect(Path(plan_dir))
    return tasks


def _inherit_default_model(task: dict[str, Any], default_model: Optional[str]) -> None:
    """Apply an explicit planning choice, never infer the actual runtime model."""
    if default_model and not any(task.get(field) for field in ("model", "tier", "model_class")):
        task["model"] = default_model


def _plan_fields(raw: dict[str, Any], path: Path) -> dict[str, Any]:
    """The plan-level facts of one file, validated."""

    if not isinstance(raw, dict):
        raise LeafError(f"{path}: файл плана должен быть объектом JSON")
    unknown = sorted(set(raw) - set(PLAN_FIELDS))
    if unknown:
        raise LeafError(
            f"{path}: неизвестные поля: {', '.join(unknown)}; "
            f"допустимые поля: {', '.join(sorted(PLAN_FIELDS))}"
        )
    fields: dict[str, Any] = {}
    if "default_model" in raw:
        value = raw["default_model"]
        if not isinstance(value, str) or not value.strip():
            raise LeafError(f"{path}: поле default_model должно быть непустой строкой")
        fields["default_model"] = value.strip()
    for field in ("title", "goal", "business_result", "current_progress",
                  "external_waits", "updated_at", "planned_start_at", "started_at", "finished_at"):
        value = raw.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise LeafError(f"{path}: поле {field} должно быть строкой")
        value = value.strip()
        if value:
            fields[field] = value
    for field in ("started_at", "finished_at"):
        if fields.get(field):
            _clock(fields, field, path)
    results = raw.get("business_results")
    if results is not None:
        if not isinstance(results, list) or not all(
            isinstance(item, str) for item in results
        ):
            raise LeafError(f"{path}: поле business_results должно быть списком строк")
        values = [item.strip() for item in results if item.strip()]
        if values:
            fields["business_results"] = values
    scenarios = raw.get("acceptance_scenarios")
    if scenarios is not None:
        if not isinstance(scenarios, list) or not all(isinstance(item, str) for item in scenarios):
            raise LeafError(f"{path}: поле acceptance_scenarios должно быть списком строк")
        fields["acceptance_scenarios"] = [item.strip() for item in scenarios if item.strip()]
    if isinstance(raw.get("revisions"), list):
        fields["revisions"] = _revisions(raw["revisions"])
    slots = raw.get("slots")
    if slots is not None:
        if isinstance(slots, bool) or not isinstance(slots, int) or slots < 1:
            raise LeafError(f"{path}: поле slots должно быть целым числом от 1")
        fields["slots"] = slots
    budget = _money(raw, "budget_usd", path)
    if budget is not None:
        fields["budget_usd"] = budget
    journal = raw.get("journal")
    if journal is not None:
        if not isinstance(journal, list) or not all(
            isinstance(item, dict) for item in journal
        ):
            raise LeafError(f"{path}: поле journal должно быть списком объектов")
        if journal:
            fields["journal"] = journal
    return fields


def plan_metadata(plan_dir: Path) -> dict[str, Any]:
    """The plan-level facts: plan.json first, the existing graph second.

    The graph is only a fallback: the leaves are the source of truth of the
    leaves, and the plan-level facts of a plan that has a plan.json are never
    taken from the graph, so a stale graph cannot keep a fact alive.
    """

    plan_dir = Path(plan_dir)
    plan_file = plan_dir / PLAN_FILE
    if plan_file.is_file():
        return _plan_fields(_read_json(plan_file), plan_file)
    graph_file = plan_dir / GRAPH_FILE
    if graph_file.is_file():
        raw = _read_json(graph_file)
        if isinstance(raw, dict):
            fields: dict[str, Any] = {}
            for field in ("title", "goal", "business_result", "current_progress",
                          "external_waits", "updated_at", "planned_start_at", "started_at", "finished_at"):
                value = raw.get(field)
                if isinstance(value, str) and value.strip():
                    fields[field] = value.strip()
            results = raw.get("business_results")
            scenarios = raw.get("acceptance_scenarios")
            if isinstance(scenarios, list) and all(isinstance(item, str) for item in scenarios):
                fields["acceptance_scenarios"] = [item.strip() for item in scenarios if item.strip()]
            if isinstance(results, list):
                values = [
                    item.strip()
                    for item in results
                    if isinstance(item, str) and item.strip()
                ]
                if values:
                    fields["business_results"] = values
            slots = raw.get("slots")
            if isinstance(slots, int) and not isinstance(slots, bool) and slots >= 1:
                fields["slots"] = slots
            budget = raw.get("budget_usd")
            if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget >= 0:
                fields["budget_usd"] = float(budget)
            journal = raw.get("journal")
            if isinstance(journal, list) and all(
                isinstance(item, dict) for item in journal
            ):
                fields["journal"] = journal
            return fields
    return {}


def _order(
    tasks: list[dict[str, Any]], sources: dict[str, Path]
) -> list[dict[str, Any]]:
    """The leaves in the order of the work: a dependency before its leaf."""

    by_id = {task["id"]: task for task in tasks}
    known = set(by_id)
    for task in tasks:
        source = sources[task["id"]]
        for field in ("depends_on", "parallel_with"):
            for dependency in task.get(field, []):
                if dependency == task["id"]:
                    raise LeafError(f"{source}: лист ссылается на себя в {field}")
                if dependency not in known:
                    raise LeafError(
                        f"{source}: поле {field} ссылается на несуществующий лист "
                        f"«{dependency}»"
                    )

    layers: dict[str, int] = {}
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(leaf_id: str) -> None:
        state[leaf_id] = 1
        stack.append(leaf_id)
        dependencies = [
            dependency
            for dependency in by_id[leaf_id].get("depends_on", [])
            if dependency in known
        ]
        for dependency in dependencies:
            if state.get(dependency) == 1:
                cycle = stack[stack.index(dependency):] + [dependency]
                raise LeafError(
                    f"{sources[leaf_id]}: цикл зависимостей: {' → '.join(cycle)}"
                )
            if dependency not in state:
                visit(dependency)
        stack.pop()
        state[leaf_id] = 2
        layers[leaf_id] = 1 + max(
            (layers.get(dependency, 0) for dependency in dependencies), default=-1
        )

    for task in tasks:
        if task["id"] not in state:
            visit(task["id"])

    return sorted(
        tasks,
        key=lambda task: (layers[task["id"]], natural_key(task["id"])),
    )


def origin_time(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return stamp if stamp.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def file_birthtime(path):
    """Source host only. Never substitute modification or inode change time."""
    try:
        birth = getattr(path.stat(), 'st_birthtime', None)
        if birth is None and sys.platform.startswith('linux'):
            # Linux UAPI statx is a fixed 256-byte structure; btime is at 80.
            # Request only STATX_BTIME and check the returned mask.
            libc = ctypes.CDLL(None, use_errno=True)
            statx = libc.statx
            statx.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                             ctypes.c_uint, ctypes.c_void_p]
            statx.restype = ctypes.c_int
            data = ctypes.create_string_buffer(256)
            if statx(-100, os.fsencode(path), 0, 0x800, data) == 0:
                if struct.unpack_from('=I', data.raw)[0] & 0x800:
                    seconds, nanos = struct.unpack_from('=qI', data.raw, 80)
                    birth = seconds + nanos / 1_000_000_000
        if birth and birth > 0:
            return datetime.fromtimestamp(birth, timezone.utc).isoformat()
    except (OSError, ValueError, OverflowError, AttributeError):
        pass
    return ''


def _revisions(items):
    """The plan versions after the first: when the plan was rewritten and why."""
    out = []
    for item in items:
        if isinstance(item, dict):
            row = {k: str(item[k]).strip() for k in ("at", "reason", "summary") if item.get(k)}
            if row.get("reason"):
                out.append(row)
    return out


def validate_plan_origin(value):
    if not isinstance(value, dict) or value.get('source') not in {
            'leaf_created_at', 'file_birthtime', 'recorded_start', 'unknown'}:
        raise LeafError('неверный источник начала плана')
    if value.get('at') and origin_time(value['at']) is None:
        raise LeafError('неверная дата начала плана')
    if value.get('source') != 'unknown' and not value.get('at'):
        raise LeafError('источник начала плана требует дату')
    if not re.fullmatch(r'[A-Za-z0-9_-]{0,80}', value.get('leaf_id', '')):
        raise LeafError('неверный id источника начала плана')
    return value


def read_plan_origin(plan_dir):
    path = Path(plan_dir) / '.lhc-publication/plan-origin.json'
    if path.exists():
        value = _read_json(path)
        return validate_plan_origin(value)
    # Import/copy carrying graph metadata retains the source's provenance.
    graph_path = Path(plan_dir) / GRAPH_FILE
    if graph_path.is_file():
        value = _read_json(graph_path).get('plan_origin')
        if value is not None:
            return validate_plan_origin(value)
    return None


def ensure_plan_origin(plan_dir):
    """Freeze once on SOURCE, independent of publication/network and revisions.

    Separate lock avoids reentering leaves/publish locks held by callers.
    A sidecar copied with a plan remains authoritative, even after leaf deletion.
    """
    plan_dir = Path(plan_dir)
    dest = plan_dir / '.lhc-publication'
    with file_lock(dest / 'origin.lock'):
        fixed = read_plan_origin(plan_dir)
        if fixed is not None:
            if not (dest / 'plan-origin.json').exists():
                _write_atomic(dest / 'plan-origin.json', json.dumps(fixed, ensure_ascii=False, indent=2) + '\n')
            return fixed
        tasks, sources, _ = _collect(plan_dir)
        candidates = []
        def add(value, source, leaf_id=''):
            stamp = origin_time(value)
            if stamp and stamp <= datetime.now(timezone.utc):
                candidates.append((stamp, value, source, leaf_id))
        for task in tasks:
            leaf_id = task['id']
            if task.get('created_at'):
                add(task['created_at'], 'leaf_created_at', leaf_id)
            else:
                add(file_birthtime(sources[leaf_id]), 'file_birthtime', leaf_id)
            add(task.get('started_at'), 'recorded_start', leaf_id)
        add(plan_metadata(plan_dir).get('started_at'), 'recorded_start')
        # Historical graph/observations can retain earlier work after a raw edit.
        for path in (plan_dir / GRAPH_FILE, dest / 'observed.json'):
            if path.is_file():
                data = _read_json(path)
                if path.name == GRAPH_FILE:
                    add(data.get('started_at'), 'recorded_start')
                    facts = data.get('tasks', [])
                else:
                    facts = [fact for item in data.values()
                             for fact in [item.get('task', {}), *item.get('completed', [])]]
                for fact in facts:
                    add(fact.get('started_at'), 'recorded_start', fact.get('id', ''))
        _, at, source, leaf_id = min(candidates, key=lambda item: item[0]) if candidates else (None, '', 'unknown', '')
        fixed = {'at': at, 'source': source, 'leaf_id': leaf_id,
                 'recorded_at': datetime.now(timezone.utc).isoformat()}
        _write_atomic(dest / 'plan-origin.json', json.dumps(fixed, ensure_ascii=False, indent=2) + '\n')
        return fixed


def build_document(plan_dir: Path) -> dict[str, Any]:
    """The graph document of a plan, collected from its leaf files."""

    plan_dir = Path(plan_dir)
    tasks, sources, stamps = _collect(plan_dir)
    tasks = _order(tasks, sources)
    metadata = plan_metadata(plan_dir)

    candidates = [*stamps.values(), str(metadata.get("updated_at") or "")]
    absolute_stamps = []
    for value in candidates:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                absolute_stamps.append((parsed, value))
        except ValueError:
            pass
    # Compare instants, not strings: offsets and midnight change lexical order.
    stamp = max(absolute_stamps)[1] if absolute_stamps else max(candidates, default="")

    results = list(metadata.get("business_results") or [])
    business_result = str(metadata.get("business_result") or "")
    if not results and business_result:
        results = [business_result]

    document: dict[str, Any] = {
        "schema_version": 2,
        "title": str(metadata.get("title") or plan_dir.name),
        "goal": str(metadata.get("goal") or ""),
        "business_result": business_result,
        "business_results": results,
        "acceptance_scenarios": list(metadata.get("acceptance_scenarios") or []),
        "current_progress": str(metadata.get("current_progress") or ""),
        "revisions": list(metadata.get("revisions") or []),
        "external_waits": str(metadata.get("external_waits") or ""),
        "slots": int(metadata.get("slots") or 1),
        "updated_at": stamp,
        "tasks": tasks,
        "leaf_count": len(tasks),
    }
    budget = metadata.get("budget_usd")
    if budget is not None:
        document["budget_usd"] = budget
    journal = metadata.get("journal")
    if journal:
        document["journal"] = journal
    anchor = str(metadata.get("planned_start_at") or "")
    if anchor:
        document["planned_start_at"] = anchor
    for field in ("started_at", "finished_at"):
        if metadata.get(field):
            document[field] = _clock(metadata, field, plan_dir / PLAN_FILE)
    fixed = read_plan_origin(plan_dir)
    if fixed is not None:
        document['plan_origin'] = fixed
    return document


def build_graph(plan_dir: Path) -> Path:
    """Collect the leaves of a plan into its plan.graph.json."""

    plan_dir = Path(plan_dir)
    ensure_plan_origin(plan_dir)
    document = build_document(plan_dir)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    target = plan_dir / GRAPH_FILE
    _write_atomic(target, text)
    auto_publish(plan_dir)
    return target


def _write_atomic(target: Path, text: str) -> None:
    """Write a file so a reader never sees half of it.

    The temporary name carries the process id, so two workers whose leaves are
    collected at the same time never write into the same temporary file.
    """

    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


# --------------------------------------------------------------------------
# the report block: the projection of the leaves into the canonical report
# --------------------------------------------------------------------------

# The section of the task record that carries the report. PLAN_REPORT.md keeps
# it under this heading, and the block that goes there is a projection: the
# next render erases whatever a model wrote into it by hand.
REPORT_SECTION = "## Plan"

# The markers of the canonical report (PLAN_REPORT.md). The grid keeps the
# same table in `GLYPH_STATUS`, and the block and the parser that reads it
# back must agree on what a marker means; the test of this table pins the two
# copies together, so neither of them can drift from the other.
STATUS_GLYPHS = {
    STATUS_DONE: "✅",
    STATUS_RUNNING: "🔄",
    STATUS_BLOCKED: "⛔",
    STATUS_WAITING: "⌛",
    STATUS_DEFERRED: "⏸",
    STATUS_QUEUED: "⏳",
}

# The groups of the report stand in this order - finished, running, blocked,
# waiting, deferred, queued - and an empty group is dropped.
GROUP_ORDER = (
    STATUS_DONE,
    STATUS_RUNNING,
    STATUS_BLOCKED,
    STATUS_WAITING,
    STATUS_DEFERRED,
    STATUS_QUEUED,
)


def grid_module() -> Any:
    """The neighbour that reads and renders the graph, loaded from next to this file.

    The grid is loaded by path in the tests and by the CLI in the package, so
    the neighbour cannot always be found by a plain import. The shape of the
    work (the number of leaves, the width of the widest wave, the number of
    slots) and the fingerprint of the revision are computed there, and a second
    copy of that arithmetic here would drift away from the very numbers
    `check-plan` compares the report with.
    """

    try:
        import lhc_grid

        return lhc_grid
    except ModuleNotFoundError:
        path = Path(__file__).resolve().with_name("lhc_grid.py")
        spec = importlib.util.spec_from_file_location("lhc_grid_sibling", path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def _minutes_text(value: Any) -> str:
    """One number of minutes in the words of the report: «15», «7.5»."""

    number = float(value)
    if abs(number - round(number)) < 0.01:
        return str(int(round(number)))
    return f"{number:.1f}"


def estimate_text(task: dict[str, Any]) -> str:
    """The estimate of a leaf, in the words of the report.

    «оценка» is the leaf's original estimate and it is never rewritten to fit
    reality. A leaf that has none says so instead of borrowing a zero.
    """

    bounds = task.get("estimate_minutes") or {}
    low = bounds.get("minimum")
    high = bounds.get("maximum")
    if low is None and high is None:
        return "оценка не записана"
    if low is None:
        low = high
    if high is None:
        high = low
    if abs(float(high) - float(low)) < 0.01:
        return f"оценка {_minutes_text(low)} минут"
    return f"оценка {_minutes_text(low)}–{_minutes_text(high)} минут"


def fact_text(task: dict[str, Any], status: str) -> str:
    """The measured time of a leaf: «факт 7 минут» or «прошло 22 минут».

    The numbers are measured, never typed in by hand, and a leaf that was not
    measured reads «не измерено» instead of a zero.
    """

    word = "прошло" if status == STATUS_RUNNING else "факт"
    actual = task.get("actual_minutes")
    if actual is None:
        return f"{word} не измерено"
    return f"{word} {_minutes_text(actual)} минут"


def overrun_text(task: dict[str, Any]) -> str:
    """The cause of an overrun, in the slot the format gives it.

    The format asks for the cause whenever the measured time is longer than
    the estimate. The leaf file has no field for that cause - its `note` is
    the place where the executor writes it - so the block points at the leaf
    instead of inventing a reason of its own.
    """

    actual = task.get("actual_minutes")
    bounds = task.get("estimate_minutes") or {}
    high = bounds.get("maximum")
    if actual is None or high is None:
        return ""
    if float(actual) <= float(high):
        return ""
    reason = "причина в листе" if task.get("note") else "причина не записана в листе"
    return f"отстаём потому что: {reason}"


def relations_text(task: dict[str, Any]) -> list[str]:
    """The relations of a leaf: who runs beside it and who it waits for.

    The parallel mark is the one of the format («∥ параллельно с листом 1»).
    The dependencies of a leaf that does not wait for anybody yet are named in
    the slot of the format itself («начнём после листа 3»); the dependencies of
    every other leaf are named in the relations cell of the projection, the
    same word the page uses («зависит: L01, L05b»).
    """

    parts: list[str] = []
    peers = [str(peer) for peer in (task.get("parallel_with") or [])]
    if len(peers) == 1:
        parts.append(f"∥ параллельно с листом {peers[0]}")
    elif peers:
        parts.append("∥ параллельно с листами " + ", ".join(peers))
    return parts


def render_leaf_line(task: dict[str, Any]) -> str:
    """One leaf as one line of the canonical report.

    The id of the leaf stands before the marker, so the parser of the report
    binds the line to that leaf by its id and never by the position of its row:
    a line without an id is a positional guess, and a guess is what made the
    hand-written report and the graph disagree twice in one day.
    """

    status = task["status"]
    glyph = STATUS_GLYPHS.get(status, STATUS_GLYPHS[STATUS_QUEUED])
    head = f"{task['id']} {glyph}"
    if status == STATUS_RUNNING:
        head += " работаем"
    # The label stands in parentheses: the parser of the report reads the first
    # pair of parentheses as the name of the leaf, so a label that carries
    # parentheses of its own is read up to the first closing one.
    head += f" ({task.get('label') or ''})"

    fields: list[str] = []
    reason = str(task.get("wait_reason") or "").strip()

    if status == STATUS_QUEUED:
        dependencies = [str(item) for item in (task.get("depends_on") or [])]
        if dependencies:
            # The format names the leaf a queued one waits for: one leaf is
            # «после листа N», several are «после листов N, M».
            word = "листа" if len(dependencies) == 1 else "листов"
            fields.append(f"начнём после {word} " + ", ".join(dependencies))
            if reason:
                fields.append("потому что " + reason)
        elif reason:
            fields.append("потому что " + reason)
        else:
            fields.append("исполнитель ещё не назначен")
        if task.get("planned_start"):
            fields.append(f"примерно в {task['planned_start']}")
        fields.append(estimate_text(task))
        if task.get("planned_finish"):
            fields.append(f"закончим в {task['planned_finish']}")
        return head + ", " + ", ".join(fields)

    started = str(task.get("started_at") or "")
    finished = str(task.get("finished_at") or "")
    times = ""
    if started:
        times = f"начата {started}"
        # A finish belongs to a leaf that finished. A leaf that runs again
        # keeps the old finish in its file, and the report does not show a
        # finish of a work that is still going on.
        if finished and status == STATUS_DONE:
            times += f" закончена {finished}"
    elif finished and status == STATUS_DONE:
        times = f"закончена {finished}"

    if status == STATUS_WAITING:
        fields.append("ждём ответа внешнего источника")
        if reason:
            fields.append("потому что " + reason)
        fields.append(estimate_text(task))
    elif status == STATUS_DEFERRED:
        fields.append("владелец отложил лист")
        fields.append(estimate_text(task))
    elif status == STATUS_BLOCKED:
        fields.append(estimate_text(task))
        blocker = str(task.get("blocker") or "").strip()
        fields.append("блокер: " + (blocker or "не записан в листе"))
    else:
        fields.append(estimate_text(task))
        fields.append(fact_text(task, status))

    overrun = overrun_text(task)
    if overrun:
        fields.append(overrun)
    fields.extend(relations_text(task))
    dependencies = [str(item) for item in (task.get("depends_on") or [])]
    if dependencies:
        # The relations cell is the last thing on the line: the parser reads it
        # up to the end of the line, and a word after it would be read as a
        # dependency of the leaf.
        fields.append("зависит: " + ", ".join(dependencies))

    body = ", ".join(fields)
    if times:
        return f"{head} {times}, {body}"
    return f"{head} {body}"


def report_block(plan_dir: Path) -> str:
    """The `## Plan` block of the task record, projected from the leaf files.

    The block is built from the same graph the page is built from, so the
    report and the page carry one revision of one plan: the numbers of the
    header are computed from the graph, never typed in by hand, and the
    fingerprint of the revision is the one the page prints.
    """

    return report_block_of(build_document(Path(plan_dir)))


def report_block_of(document: dict[str, Any]) -> str:
    """The `## Plan` block of one collected document."""

    grid = grid_module()
    graph = grid.parse_graph_json(document)
    metrics = grid.build_metrics(graph)
    parallel, waves, slots = grid.plan_shape(graph, metrics)

    lines: list[str] = []
    goal = str(document.get("goal") or "")
    if goal:
        lines.append(f"Цель: {goal}")
    results = [str(item).strip() for item in (document.get("business_results") or [])]
    results = [item for item in results if item]
    if not results and document.get("business_result"):
        results = [str(document["business_result"]).strip()]
    for result in results:
        lines.append(f"Бизнес-результат: {result}")
    for scenario in document.get('acceptance_scenarios', []):
        lines.append(f"Как проверим: {scenario}")
    lines.append(
        "Декомпозиция: {leaves} · {parallel} параллельно · {waves} · слотов: {slots}".format(
            leaves=grid.count_russian(len(document["tasks"]), "лист", "листа", "листьев"),
            parallel=parallel,
            waves=grid.count_russian(waves, "волна", "волны", "волн"),
            slots=slots,
        )
    )
    lines.append(f"Ревизия плана: {grid.graph_revision(graph)}")
    lines.append("")
    for status in GROUP_ORDER:
        group = [task for task in document["tasks"] if task["status"] == status]
        if not group:
            continue
        for task in group:
            lines.append(render_leaf_line(task))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_report_block(task_path: Path, block: str) -> Path:
    """Rewrite the `## Plan` section of the task record with the projection.

    The section is replaced as a whole: a hand-written line inside it is a
    defect, because the next render erases it anyway.
    """

    path = Path(task_path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == REPORT_SECTION:
            start = index
            break
    if start is None:
        raise LeafError(f"{path}: в записи задачи нет раздела «{REPORT_SECTION}»")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    replacement = [""] + block.rstrip("\n").splitlines() + [""]
    written = "\n".join(lines[: start + 1] + replacement + lines[end:])
    if text.endswith("\n"):
        written += "\n"
    _write_atomic(path, written)
    return path


def stale_graph_reason(plan_dir: Path, document: dict[str, Any]) -> str:
    """Why the graph on disk no longer says what the leaves say.

    The report is compared with the graph, not with the leaves: when the graph
    is older than the leaves, the report and the graph disagree by definition,
    and the reason is named instead of the divergence being discovered later.
    """

    graph_file = Path(plan_dir) / GRAPH_FILE
    if not graph_file.is_file():
        return "файла графа нет"
    try:
        raw = _read_json(graph_file)
    except LeafError:
        return "файл графа не прочитан"
    if not isinstance(raw, dict):
        return "файл графа не является объектом"
    stored = raw.get("tasks")
    if not isinstance(stored, list):
        return "в файле графа нет списка задач"
    by_id = {
        str(task.get("id")): task
        for task in stored
        if isinstance(task, dict)
    }
    for task in document["tasks"]:
        other = by_id.get(task["id"])
        if other is None:
            return f"в графе нет листа {task['id']}"
        if str(other.get("status") or "") != task["status"]:
            return f"статус листа {task['id']} в графе другой"
        if [str(item) for item in (other.get("depends_on") or [])] != [
            str(item) for item in (task.get("depends_on") or [])
        ]:
            return f"зависимости листа {task['id']} в графе другие"
    if len(by_id) != len(document["tasks"]):
        return "в графе листьев больше, чем в каталоге"
    return ""


# --------------------------------------------------------------------------
# the command line
# --------------------------------------------------------------------------


def fmt_cap_minutes(value: float) -> str:
    if abs(value - round(value)) < 0.01:
        return f"{int(round(value))} мин"
    return f"{value:.1f} мин"


def estimate_cap_findings(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Leaves whose estimate passes the 15-minute cap without saying why.

    The cap belongs to the format, not to a single tool, so the finding is a
    plain list the command line and any other caller can read: a leaf longer
    than the cap is either split into two leaves or records the reason it is
    deliberately larger. Silence is what this function exists to end.
    """

    findings: list[dict[str, Any]] = []
    for task in tasks:
        bounds = task.get("estimate_minutes") or {}
        high = bounds.get("maximum")
        if high is None or high <= LEAF_ESTIMATE_CAP_MINUTES:
            continue
        reason = str(task.get("estimate_over_limit_reason") or "").strip()
        if reason:
            continue
        findings.append({
            "id": task.get("id", ""),
            "minutes": float(high),
            "cap": LEAF_ESTIMATE_CAP_MINUTES,
        })
    return findings


def auto_publish(plan_dir: Path) -> None:
    """Opt-in only; publishing failure never prevents the work being recorded."""
    try:
        tool_dir = str(Path(__file__).resolve().parent)
        if tool_dir not in sys.path:
            sys.path.insert(0, tool_dir)
        from lhc_plan_mirror import mark
        if mark(plan_dir):
            return
        if not (Path(plan_dir) / ".lhc-publication/state.json").is_file():
            return
        from lhc_plan_publish import publish
        publish(Path(plan_dir), automatic=True)
    except Exception as error:
        print(f"LHC: публикация не обновлена: {error}", file=sys.stderr)

@contextlib.contextmanager
def file_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield

def update_leaf(plan_dir: Path, leaf_id: str, fields: dict, *, create=False,
                note=None, expected_hash=None) -> dict:
    """Serialized read/merge/validate/replace; stale optimistic writes fail."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", leaf_id):
        raise LeafError("небезопасный id листа")
    if not isinstance(fields, dict) or "progress_events" in fields:
        raise LeafError("fields: объект; историю меняет только progress")
    path = Path(plan_dir) / LEAVES_DIRNAME / (leaf_id + ".json")
    with file_lock(Path(plan_dir) / ".lhc-leaves.lock"):
        if path.is_symlink():
            raise LeafError("symlink листа запрещён")
        if create and path.exists():
            raise LeafError("лист уже существует")
        before = path.read_bytes() if not create else b""
        if expected_hash and hashlib.sha256(before).hexdigest() != expected_hash:
            raise LeafError("конфликт: лист изменён, перечитайте его")
        raw = json.loads(before) if before else {}
        if 'created_at' in fields and fields['created_at'] != raw.get('created_at'):
            raise LeafError('created_at устанавливается автоматически и не меняется')
        if "id" in fields and fields["id"] != leaf_id:
            raise LeafError("id нельзя менять")
        merged = {**raw, **fields, "id": leaf_id}
        _inherit_default_model(merged, plan_metadata(plan_dir).get("default_model"))
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        if create:
            merged['created_at'] = stamp
        # Only Codex's documented thread environment is auto-bound. Other
        # harnesses pass explicit session/harness; no process-title inference.
        if not merged.get("session"):
            native = os.environ.get("CODEX_THREAD_ID", "")
            if re.fullmatch(r"[0-9a-f-]{36}", native):
                merged["session"], merged["harness"] = native, "codex"
        merged["updated_at"] = stamp
        events = list(raw.get("progress_events", []))
        changes = {k: v for k, v in fields.items() if raw.get(k) != v}
        if merged.get("model") and raw.get("model") != merged["model"]:
            changes["model"] = merged["model"]
        events.append({"at": stamp, "note": note or "", "changes": changes,
                       "session": merged.get("session", "unknown"),
                       "harness": merged.get("harness", "unknown")})
        merged["progress_events"] = events
        candidate = task_from_leaf(merged, path)
        tasks = [t for t in collect_leaves(plan_dir) if t["id"] != leaf_id] if (Path(plan_dir) / LEAVES_DIRNAME).is_dir() and any((Path(plan_dir) / LEAVES_DIRNAME).glob("*.json")) else []
        tasks.append(candidate)
        _order(tasks, {t["id"]: path.parent / (t["id"] + ".json") for t in tasks})
        # Recover legacy birth BEFORE atomic replacement destroys that evidence.
        if before:
            try:
                ensure_plan_origin(plan_dir)
            except (OSError, ValueError) as error:
                print(f'LHC: начало плана пока не зафиксировано: {error}', file=sys.stderr)
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
        _write_atomic(path, serialized)
        own_hash = hashlib.sha256(serialized.encode()).hexdigest()
        try:
            ensure_plan_origin(plan_dir)
        except (OSError, ValueError) as error:
            print(f'LHC: лист сохранён; начало плана пока не зафиксировано: {error}', file=sys.stderr)
    # A registered mirror records only local dirtiness. Legacy publication is
    # still triggered by build_graph, as before, never by a bare leaf edit.
    try:
        from lhc_plan_mirror import binding, mark
        if binding(plan_dir):
            mark(plan_dir)
    except Exception:
        print('LHC: лист сохранён; локальную отметку зеркала проверит наблюдатель', file=sys.stderr)
    return {"id": leaf_id, "sha256": own_hash}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lhc_plan_json.py",
        description="Collect the leaf files of a plan into one plan.graph.json.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    whole = sub.add_parser("build-plan", help="collect and render the same plan")
    whole.add_argument("plan_dir", type=Path)
    whole.add_argument("--report", type=Path)
    whole.add_argument("--graph", type=Path)
    build = sub.add_parser("build", help="collect the leaves into plan.graph.json")
    build.add_argument("plan_dir", type=Path)
    check = sub.add_parser("check", help="validate the leaves, write nothing")
    check.add_argument("plan_dir", type=Path)
    activate = sub.add_parser(
        "activate",
        help="bind one explicitly selected plan leaf to this local session and observer",
    )
    activate.add_argument("plan_dir", type=Path)
    activate.add_argument("leaf_id")
    activate.add_argument("--config", type=Path, help="local mirror client config (defaults to the installed config)")
    activate.add_argument("--session", help="actual current session id; Codex normally supplies CODEX_THREAD_ID")
    activate.add_argument("--harness", help="actual harness when it cannot be inferred as Codex")
    activate.add_argument("--owner", help="actual leaf owner; defaults to the current OS user")
    activate.add_argument("--note", help="progress event note")
    for name in ("create-leaf", "update-leaf", "progress"):
        edit = sub.add_parser(name)
        edit.add_argument("plan_dir", type=Path)
        edit.add_argument("leaf_id")
        edit.add_argument("--fields", default="{}", help="JSON object")
        edit.add_argument("--expected-hash")
        edit.add_argument("--note")
    report = sub.add_parser(
        "report",
        help="print the canonical «## Plan» block of the task record",
    )
    report.add_argument("plan_dir", type=Path)
    report.add_argument(
        "--write",
        action="store_true",
        help="rewrite the «## Plan» block in the task record",
    )
    report.add_argument(
        "--task",
        type=Path,
        default=None,
        help="the task record to rewrite (default: <plan-dir>/task.md)",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "build-plan":
            import lhc_grid
            graph = build_graph(args.plan_dir)
            lhc_grid.main(["render", str(graph), "--out-dir", str(args.plan_dir)])
            if args.report:
                return lhc_grid.main(["check-plan", str(args.report), str(args.graph or graph)])
        elif args.command == "build":
            print(str(build_graph(args.plan_dir)))
        elif args.command == "activate":
            tool_dir = str(Path(__file__).resolve().parent)
            if tool_dir not in sys.path:
                sys.path.insert(0, tool_dir)
            import lhc_plan_mirror
            result = lhc_plan_mirror.activate(
                args.plan_dir, args.leaf_id, config_path=args.config,
                session=args.session, harness=args.harness, owner=args.owner,
                note=args.note,
            )
            print(json.dumps(result, ensure_ascii=False))
        elif args.command in ("create-leaf", "update-leaf", "progress"):
            result = update_leaf(args.plan_dir, args.leaf_id, json.loads(args.fields),
                                 create=args.command == "create-leaf", note=args.note,
                                 expected_hash=args.expected_hash)
            build_graph(args.plan_dir)
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == "report":
            document = build_document(args.plan_dir)
            block = report_block_of(document)
            reason = stale_graph_reason(args.plan_dir, document)
            if reason:
                print(
                    f"LHC: файл {GRAPH_FILE} в каталоге устарел ({reason}); "
                    "соберите граф командой build, иначе сверка увидит расхождение",
                    file=sys.stderr,
                )
            if args.write:
                task_path = args.task or (Path(args.plan_dir) / "task.md")
                print(str(write_report_block(task_path, block)))
            else:
                sys.stdout.write(block)
        else:
            document = build_document(args.plan_dir)
            print(f"{args.plan_dir}: листы согласованы")
            findings = estimate_cap_findings(document.get("tasks", []))
            if findings:
                print(
                    f"ПРЕВЫШЕН ПРЕДЕЛ ОЦЕНКИ ЛИСТА ({LEAF_ESTIMATE_CAP_MINUTES} мин) — "
                    "длинную работу надо разбить на два листа, либо записать в листе "
                    "estimate_over_limit_reason, почему он сознательно больше:",
                    file=sys.stderr,
                )
                for item in findings:
                    print(
                        f"  - лист {item['id']}: оценка {fmt_cap_minutes(item['minutes'])} "
                        f"при пределе {item['cap']} мин — чего не хватает: разбиения или "
                        "причины превышения",
                        file=sys.stderr,
                    )
                return 1
    except (LeafError, OSError) as error:
        print(f"LHC: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
