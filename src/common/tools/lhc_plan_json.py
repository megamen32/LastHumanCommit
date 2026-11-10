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
import contextvars
import lhc_assignment as assignments
import fcntl
import hashlib
from datetime import datetime, timezone
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
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
TIERS = ("fast", "middle", "frontier")
COMPLEXITIES = ("S", "M", "L")
COST_SOURCES = ("measured", "provisional")

# The format (PLAN_REPORT.md, TASK_GRAPH.md) says a leaf is about fifteen minutes
# and a longer job is two leaves. That cap lived only in the prose; the collector
# silently accepted a 30–50 minute leaf. `check` now names the breach and exits
# nonzero, unless the leaf records, in its own words, why it is deliberately
# larger — so the rule is a signpost, not a blind barrier.
LEAF_ESTIMATE_CAP_MINUTES = 15
LEAF_KINDS = ("task", "milestone", "research")
ESTIMATE_KEYS = ("estimate_minutes", "estimate", "estimate_min", "estimate_max")
PLAN_MODES = ("quickfix", "fullcycle")
DELIVERABLES = ("plan", "implementation")
DECOMPOSITIONS = ("progressive", "complete")

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
    "kind",
    "parent",
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
    "assignment",
    "assignment_history",
    # The Worker that owns the leaf: id, branch, worktree, run_dir, run_host,
    # registered_at and removed_at. worker-finish merges and removes it.
    "worker",
    "supersedes",
    "origin",
    "duration_estimate_minutes",
)

# The plan-level fields. They belong to the plan, not to a leaf, so they live
# in one file instead of being copied into every leaf.
PLAN_FIELDS = (
    "current_goal_lead",
    "default_model",
    "title",
    "goal",
    "business_result",
    "business_results",
    "acceptance_scenarios",
    "acceptance_scenario",
    "recon",
    "mode",
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
    "decomposition_check",
    "deliverable",
    "decomposition",
    "estimate_policy",
)

CLOCK_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


class LeafError(ValueError):
    """A leaf that cannot be collected. The message always names the file."""


_LENIENT: contextvars.ContextVar = contextvars.ContextVar("lhc_lenient_reading", default=None)


@contextlib.contextmanager
def lenient_reading():
    """Read an existing plan to mirror it: gates apply to writes, not to reading.

    Inside the block a field the schema does not know is dropped and named in
    the yielded list of warnings instead of raising LeafError. Creating and
    updating a leaf stays strict, outside the block."""

    warnings: list[str] = []
    token = _LENIENT.set(warnings)
    try:
        yield warnings
    finally:
        _LENIENT.reset(token)


def _lenient_note(path: Path, text: str) -> bool:
    sink = _LENIENT.get()
    if sink is None:
        return False
    message = f"{Path(path).name}: {text}"
    if message not in sink:
        sink.append(message)
    return True


def _tolerate_unknown(path: Path, unknown: list[str], kind: str) -> bool:
    sink = _LENIENT.get()
    if sink is None:
        return False
    message = f"{Path(path).name}: неизвестные поля {kind} не зеркалируются — {', '.join(unknown)}"
    if message not in sink:
        sink.append(message)
    return True


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
        if not _tolerate_unknown(path, unknown, "листа"):
            raise unknown_field_error(path, unknown)
        legacy_title = raw.get("title")
        raw = {key: value for key, value in raw.items() if key in LEAF_FIELDS}
        if not raw.get("label") and isinstance(legacy_title, str) and legacy_title.strip():
            raw["label"] = legacy_title.strip()  # old leaves named themselves title

    leaf_id = _text(raw, "id", path)
    if not leaf_id:
        raise LeafError(f"{path}: нет поля id")
    if leaf_id != path.stem:
        raise LeafError(
            f"{path}: id «{leaf_id}» не совпадает с именем файла «{path.stem}»"
        )

    label = _text(raw, "label", path)
    if not label and _lenient_note(path, "нет названия листа, показан id"):
        label = leaf_id
    if not label:
        raise LeafError(f"{path}: нет названия листа (label)")

    task: dict[str, Any] = {
        "id": leaf_id,
        "label": label,
        "status": _status(raw.get("status"), path),
    }

    # A leaf is a task unless it says it is a milestone: a stage whose leaves are
    # not known yet. A milestone is never worked on; its leaves name it in the
    # field parent, and its status is read from them (split_milestones).
    kind = _text(raw, "kind", path)
    if kind:
        if kind not in LEAF_KINDS:
            raise LeafError(f"{path}: kind должен быть один из: " + ", ".join(LEAF_KINDS))
        if kind != "task":
            task["kind"] = kind
    parent = _text(raw, "parent", path)
    if parent:
        task["parent"] = parent

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
        not isinstance(e, dict) or set(e) - {"at", "note", "changes", "session", "harness", "actor"}
        or not isinstance(e.get("at"), str) or not isinstance(e.get("note", ""), str)
        or not isinstance(e.get("changes", {}), dict) for e in events
    ):
        raise LeafError(f"{path}: неверные progress_events")
    if events:
        task["progress_events"] = events
    for event in events:
        if "actor" in event:
            assignments.validate_actor(event["actor"])
    if "assignment" in raw:
        task["assignment"] = assignments.validate_assignment(raw["assignment"])
    if "assignment_history" in raw:
        history = raw["assignment_history"]
        if not isinstance(history, list):
            raise LeafError("assignment_history must be a list")
        task["assignment_history"] = [assignments.validate_assignment(item) for item in history]

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
    # The start and end of a leaf are in its own history even when nobody
    # stamped them: the first move to running and the last move to a final
    # status. Without them the page cannot show how long a leaf really took.
    events = [event for event in raw.get("progress_events") or []
              if isinstance(event, dict) and isinstance(event.get("changes"), dict)
              and origin_time(str(event.get("at") or "")) is not None]
    if "started_at" not in task:
        began = next((event["at"] for event in events if event["changes"].get("status") == "running"), None)
        if began:
            task["started_at"] = began
    if "finished_at" not in task and raw.get("status") in {"done", "dropped"}:
        ended = next((event["at"] for event in reversed(events)
                      if event["changes"].get("status") in {"done", "dropped"}), None)
        if ended:
            task["finished_at"] = ended

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


def _estimate_policy(value: Any, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"leaf_cap_minutes", "reason"}:
        raise LeafError(f"{path}: estimate_policy: нужны leaf_cap_minutes и reason")
    cap, reason = value["leaf_cap_minutes"], value["reason"]
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise LeafError(f"{path}: estimate_policy.leaf_cap_minutes должно быть целым числом от 1")
    if not isinstance(reason, str) or not reason.strip():
        raise LeafError(f"{path}: estimate_policy.reason: запишите решение пользователя")
    return {"leaf_cap_minutes": cap, "reason": reason.strip()}


def leaf_estimate_cap(metadata: Optional[dict[str, Any]] = None) -> int:
    """One plan's recorded policy; never change the process-wide default."""
    if metadata is None or "estimate_policy" not in metadata:
        return LEAF_ESTIMATE_CAP_MINUTES
    return _estimate_policy(metadata["estimate_policy"], Path(PLAN_FILE))["leaf_cap_minutes"]


def _plan_fields(raw: dict[str, Any], path: Path) -> dict[str, Any]:
    """The plan-level facts of one file, validated."""

    if not isinstance(raw, dict):
        raise LeafError(f"{path}: файл плана должен быть объектом JSON")
    unknown = sorted(set(raw) - set(PLAN_FIELDS))
    if unknown:
        if not _tolerate_unknown(path, unknown, "плана"):
            raise LeafError(
                f"{path}: неизвестные поля: {', '.join(unknown)}; "
                f"допустимые поля: {', '.join(sorted(PLAN_FIELDS))}"
            )
        raw = {key: value for key, value in raw.items() if key in PLAN_FIELDS}
    fields: dict[str, Any] = {}
    if "current_goal_lead" in raw:
        import lhc_plan_control
        try:
            fields["current_goal_lead"] = lhc_plan_control.validate_current_goal_lead(raw["current_goal_lead"])
        except ValueError as error:
            raise LeafError(f"{path}: current_goal_lead: {error}") from None
    for field, allowed in (("deliverable", DELIVERABLES), ("decomposition", DECOMPOSITIONS)):
        if field not in raw:
            continue
        value = raw[field]
        if value not in allowed:
            raise LeafError(f"{path}: поле {field} должно быть одним из: " + ", ".join(allowed))
        fields[field] = value
    if "estimate_policy" in raw:
        fields["estimate_policy"] = _estimate_policy(raw["estimate_policy"], path)
    if "decomposition_check" in raw:
        if not isinstance(raw["decomposition_check"], dict):
            raise LeafError(f"{path}: поле decomposition_check должно быть объектом")
        fields["decomposition_check"] = raw["decomposition_check"]
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
            if isinstance(value, list) and all(isinstance(item, str) for item in value) and _lenient_note(
                    path, f"поле {field} — список, склеен в строку"):
                value = "; ".join(item.strip() for item in value if item.strip())
            else:
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
    one = raw.get("acceptance_scenario")
    if one is not None:
        if not isinstance(one, str):
            raise LeafError(f"{path}: поле acceptance_scenario должно быть строкой")
        one = one.strip()
        if one:
            fields["acceptance_scenario"] = one
            fields["acceptance_scenarios"] = [one] + [
                item for item in fields.get("acceptance_scenarios", []) if item != one]
    recon = raw.get("recon")
    if recon is not None:
        if not isinstance(recon, list) or not all(isinstance(item, str) for item in recon):
            raise LeafError(f"{path}: поле recon должно быть списком строк")
        fields["recon"] = [item.strip() for item in recon if item.strip()]
    mode = raw.get("mode")
    if mode is not None:
        if mode not in PLAN_MODES:
            raise LeafError(f"{path}: поле mode должно быть одним из: " + ", ".join(PLAN_MODES))
        fields["mode"] = mode
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
            recon = raw.get("recon")
            if isinstance(recon, list) and all(isinstance(item, str) for item in recon):
                fields["recon"] = [item.strip() for item in recon if item.strip()]
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
            fields.update(_plan_fields({key: raw[key] for key in
                          ("deliverable", "decomposition", "estimate_policy", "decomposition_check")
                          if key in raw}, graph_file))
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
        if isinstance(item, str) and item.strip():
            item = {"reason": item}  # a plain line is a reason, never dropped
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


def _milestone_status(statuses: list) -> str:
    """The status of a milestone, read from the statuses of its leaves."""

    if "blocked" in statuses:
        return "blocked"
    if all(item in ("done", "deferred") for item in statuses):
        return "done" if "done" in statuses else "deferred"
    if "running" in statuses or "done" in statuses:
        return "running"
    if "waiting" in statuses:
        return "waiting"
    return "queued"


def split_milestones(tasks, sources=None, strict=True):
    """Take the milestones that have leaves out of the list of tasks.

    A milestone with leaves is a container: it is never worked on, its status is
    read from its leaves, and whoever depends on it waits for all of them. The
    graph, the schedule and every count then see only real work, once. A
    milestone without leaves stays in the list as one queued leaf, so a plan
    cannot look finished while a stage is still undecomposed. Returns the tasks
    and the list of all milestones. Nesting is one level: a parent is a
    milestone and a milestone has no parent. With strict=False (hooks) a broken
    link is ignored instead of raised.
    """

    by_id = {task["id"]: task for task in tasks}
    kids: dict = {}

    def fail(task, text):
        if strict:
            where = (sources or {}).get(task["id"], task["id"])
            raise LeafError(f"{where}: {text}")

    for task in tasks:
        parent = task.get("parent")
        if not parent:
            continue
        holder = by_id.get(parent)
        if holder is None:
            fail(task, f"parent «{parent}» не существует")
        elif holder.get("kind") != "milestone":
            fail(task, f"parent «{parent}» не этап (kind: milestone)")
        elif task.get("kind") == "milestone" or holder.get("parent"):
            fail(task, "этап не вкладывается в этап: вложенность один уровень")
        else:
            kids.setdefault(parent, []).append(task["id"])
            continue
        task.pop("parent", None)

    def expand(items, skip):
        out: list = []
        for item in items:
            for one in kids.get(item) or [item]:
                if one not in out and one not in skip:
                    out.append(one)
        return out

    rest = []
    for task in tasks:
        if task["id"] in kids:
            continue
        own = {task["id"]}
        deps = expand(task.get("depends_on") or [], own)
        holder = task.get("parent")
        if holder in kids:
            inherited = expand(by_id[holder].get("depends_on") or [], own | set(kids[holder]))
            deps = inherited + [item for item in deps if item not in inherited]
        task["depends_on"] = deps
        if task.get("parallel_with"):
            task["parallel_with"] = expand(task["parallel_with"], own)
        rest.append(task)

    milestones = []
    for task in tasks:
        if task.get("kind") != "milestone":
            continue
        ids = kids.get(task["id"], [])
        label = str(task.get("label") or task["id"])
        if ids:
            status = _milestone_status([str(by_id[item].get("status")) for item in ids])
        else:
            status = "deferred" if task.get("status") == "deferred" else "queued"
            task["status"] = status
            task["label"] = "Этап · " + label
        milestones.append({
            "id": task["id"], "label": label, "status": status, "children": list(ids),
            "estimate_minutes": task.get("estimate_minutes"),
            "done": sum(1 for item in ids if by_id[item].get("status") == "done"),
            "total": len(ids),
        })
    milestones.sort(key=lambda item: natural_key(item["id"]))
    return rest, milestones


def _goal_control_adapter():
    try:
        import lhc_plan_control
    except ModuleNotFoundError as error:
        if error.name != "lhc_plan_control":
            raise
        return None
    return lhc_plan_control


def goal_control(plan_dir: Path) -> dict[str, Any]:
    """Read current native control; graph projections are never authority."""
    adapter = _goal_control_adapter()
    if adapter is None:
        return {"goal_status": "unknown", "frontier": "unknown", "next_decision": "none",
                "fingerprint": None, "reason": "native_control_adapter_unavailable"}
    return adapter.resolve_control(Path(plan_dir).resolve())


def build_document(plan_dir: Path) -> dict[str, Any]:
    """The graph document of a plan, collected from its leaf files."""

    plan_dir = Path(plan_dir)
    tasks, sources, stamps = _collect(plan_dir)
    tasks, milestones = split_milestones(tasks, sources)
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
        "goal_control": goal_control(plan_dir),
        "business_result": business_result,
        "business_results": results,
        "acceptance_scenarios": list(metadata.get("acceptance_scenarios") or []),
        "recon": list(metadata.get("recon") or []),
        "current_progress": str(metadata.get("current_progress") or ""),
        "deliverable": metadata.get("deliverable", "implementation"),
        "decomposition": metadata.get("decomposition", "progressive"),
        "revisions": list(metadata.get("revisions") or []),
        "external_waits": str(metadata.get("external_waits") or ""),
        "slots": int(metadata.get("slots") or 1),
        "updated_at": stamp,
        "tasks": tasks,
        "leaf_count": len(tasks),
    }
    if milestones:
        document["milestones"] = milestones
    for field in ("estimate_policy", "decomposition_check", "current_goal_lead"):
        if field in metadata:
            document[field] = metadata[field]
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
    lines.append(plan_intent(document))
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


def estimate_cap_findings(tasks: list[dict[str, Any]], cap: Optional[int] = None) -> list[dict[str, Any]]:
    """Leaves whose estimate passes the effective cap without saying why.

    The cap belongs to the format, not to a single tool, so the finding is a
    plain list the command line and any other caller can read: a leaf longer
    than the cap is either split into two leaves or records the reason it is
    deliberately larger. Silence is what this function exists to end.
    """

    cap = LEAF_ESTIMATE_CAP_MINUTES if cap is None else cap
    findings: list[dict[str, Any]] = []
    for task in tasks:
        if task.get("kind") == "milestone":
            continue
        bounds = task.get("estimate_minutes") or {}
        high = bounds.get("maximum")
        if high is None or high <= cap:
            continue
        reason = str(task.get("estimate_over_limit_reason") or "").strip()
        if reason:
            continue
        findings.append({
            "id": task.get("id", ""),
            "minutes": float(high),
            "cap": cap,
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

NO_RECON_MESSAGE = ("сначала исследуй: что есть сейчас и как проверим. "
                    "recon: каждый факт с доказательством (команда/путь/URL) и ≥3 факта для fullcycle "
                    "(для остальных планов ≥2). В plan.json recon - список строк вида "
                    "«факт не короче 30 знаков :: evidence», где evidence - команда, путь, URL или хост; "
                    "факты не повторяются. Нужен и непустой acceptance_scenario (что запускаем и что "
                    "должно быть видно). Первым листом без них допускается только лист исследования "
                    "(kind=research, в пределах лимита плана)")
RECON_MIN_TEXT = 30
RECON_FULLCYCLE_FACTS = 3
RECON_OTHER_FACTS = 2


def recon_review(recon: Any, fullcycle: bool) -> dict[str, Any]:
    """Judge a plan's recon. Facts of the text only: the evidence is not run here.

    New format: "fact (30+ chars) :: evidence" with evidence a command, path, URL or host.
    The old format (plain strings) is still read: it is 'legacy' and is not refused for a
    plan that already works, only for a plan that is being started."""
    items = [i.strip() for i in recon if isinstance(i, str) and i.strip()] if isinstance(recon, list) else []
    need = RECON_FULLCYCLE_FACTS if fullcycle else RECON_OTHER_FACTS
    split = [re.split(r"\s::\s", item, maxsplit=1) for item in items]
    structured = [p for p in split if len(p) == 2]
    if not structured:
        unique = {re.sub(r"\s+", " ", i).casefold() for i in items}
        return {"strict": False, "legacy": len(unique) >= RECON_OTHER_FACTS, "need": need,
                "problem": "recon без доказательств («факт :: evidence»)" if items else "recon пуст"}
    problem, seen = "", set()
    if len(structured) != len(items):
        problem = "в recon есть пункт без « :: evidence»"
    for text, evidence in structured:
        text, evidence = text.strip(), evidence.strip()
        key = re.sub(r"\s+", " ", text).casefold()
        if len(text) < RECON_MIN_TEXT:
            problem = problem or f"факт короче {RECON_MIN_TEXT} знаков: «{text[:40]}»"
        elif not evidence:
            problem = problem or f"у факта нет evidence: «{text[:40]}»"
        elif key in seen:
            problem = problem or f"факт повторяется: «{text[:40]}»"
        seen.add(key)
    if not problem and len(seen) < need:
        problem = f"фактов {len(seen)} из {need}"
    return {"strict": not problem, "legacy": False, "need": need, "problem": problem}


def _state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "lhc" / "sessions"


def _session_file(session: str) -> Optional[Path]:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", session or ""):
        return None
    return _state_dir() / (re.sub(r"[^A-Za-z0-9_.-]", "_", session) + ".json")


def record_session_plan(session: Any, plan_dir: Any, leaf_id: Any = None) -> bool:
    """Remember that this session works a leaf of this plan (index session -> plan dirs).

    The plan stays authoritative; the index only says where to look, so a session whose
    cwd is another project is still found by its Stop gate. Any failure is silent."""
    import time
    try:
        path = _session_file(str(session or ""))
        if path is None:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        plans = data.get("plans") if isinstance(data, dict) and isinstance(data.get("plans"), dict) else {}
        plans[str(Path(plan_dir).expanduser().resolve())] = {"leaf": leaf_id, "at": time.time()}
        for old in sorted(plans, key=lambda k: float((plans[k] or {}).get("at") or 0))[:-20]:
            plans.pop(old, None)
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"session": str(session), "plans": plans}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001 - the index is a convenience, never a failure
        return False


def session_plans(session: Any) -> list[str]:
    """Plan directories this session was bound to (newest first); [] on any failure."""
    try:
        path = _session_file(str(session or ""))
        if path is None or not path.is_file():
            return []
        plans = json.loads(path.read_text(encoding="utf-8")).get("plans") or {}
        ordered = sorted(plans, key=lambda k: float((plans[k] or {}).get("at") or 0), reverse=True)
        return [p for p in ordered if Path(p).is_dir()]
    except Exception:  # noqa: BLE001
        return []


def leaf_max_minutes(task: dict[str, Any]) -> Optional[float]:
    bounds = task.get("estimate_minutes") or {}
    value = bounds.get("maximum", bounds.get("minimum"))
    return float(value) if value is not None else None


def _plan_gate_state(plan_dir: Path) -> dict[str, Any]:
    plan_file = Path(plan_dir) / PLAN_FILE
    raw: Any = {}
    if plan_file.is_file():
        try:
            raw = _read_json(plan_file)
        except (LeafError, OSError, ValueError):
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    fullcycle = raw.get("mode") == "fullcycle"
    review = recon_review(raw.get("recon"), fullcycle)
    one = raw.get("acceptance_scenario")
    many = raw.get("acceptance_scenarios")
    scenario = (isinstance(one, str) and one.strip()) or (
        isinstance(many, list) and any(isinstance(i, str) and i.strip() for i in many))
    return {"fullcycle": fullcycle,
            "recon_ok": review["strict"] and bool(scenario),
            "recon_legacy": review["legacy"] and bool(scenario),
            "recon_problem": review["problem"] if raw.get("recon") is not None else ""}


def check_leaf_gates(plan_dir: Path, candidate: dict[str, Any], *, create: bool,
                     touches_estimate: bool, others: list[dict[str, Any]]) -> None:
    """Refuse a leaf above its plan's cap and a plan without recon.

    No flag bypasses the cap on a write. A leaf that is already over it in an
    old plan stays readable and renderable; it only draws a warning."""

    cap = leaf_estimate_cap(plan_metadata(plan_dir))
    if candidate.get("kind") != "milestone":
        high = leaf_max_minutes(candidate)
        if high is not None and high > cap:
            if create or touches_estimate:
                raise LeafError(
                    f"лист {candidate.get('id')} >{cap} мин: разбей на листья "
                    f"по ≤{cap} мин (исследование, шаг, проверка)")
            print(f"LHC: предупреждение: лист {candidate.get('id')} длиннее "
                  f"{cap} мин; разбей его на листья по ≤{cap} мин",
                  file=sys.stderr)
    if not create:
        return
    state = _plan_gate_state(plan_dir)
    real = [t for t in others if t.get("kind") != "milestone"]
    became_plan = len(real) == 1  # the plan goes from one leaf to two
    if not (state["fullcycle"] or became_plan) or candidate.get("kind") == "milestone":
        return
    if state["recon_ok"]:
        return
    if candidate.get("kind") == "research" and not real:
        return
    if state["recon_legacy"] and any(t.get("kind") != "research" for t in real):
        print("LHC: предупреждение: recon в старом формате (без «факт :: evidence»); "
              "для нового плана каждый факт нужен с доказательством", file=sys.stderr)
        return
    raise LeafError(NO_RECON_MESSAGE + (f" [{state['recon_problem']}]" if state["recon_problem"] else ""))


def check_activation(plan_dir: Path, leaf: dict[str, Any]) -> None:
    """Called before a leaf is bound to a session."""

    if leaf.get("kind") == "milestone":
        return
    task = {"id": leaf.get("id"), "kind": leaf.get("kind")}
    try:
        estimate = _estimate(leaf, Path(plan_dir) / LEAVES_DIRNAME / (str(leaf.get("id")) + ".json"))
    except LeafError:
        estimate = None
    if estimate:
        task["estimate_minutes"] = estimate
    high = leaf_max_minutes(task)
    cap = leaf_estimate_cap(plan_metadata(plan_dir))
    if high is not None and high > cap:
        print(f"LHC: предупреждение: лист {leaf.get('id')} длиннее {cap} мин; "
              f"разбей на листья по ≤{cap} мин", file=sys.stderr)
    state = _plan_gate_state(plan_dir)
    if state["fullcycle"] and not state["recon_ok"] and leaf.get("kind") != "research":
        if state["recon_legacy"]:
            print("LHC: предупреждение: recon в старом формате (без «факт :: evidence»); "
                  "допиши доказательства к фактам и третий факт", file=sys.stderr)
            return
        raise LeafError(NO_RECON_MESSAGE + (f" [{state['recon_problem']}]" if state["recon_problem"] else ""))


OVERRUN_FLOOR_MINUTES = 45


def overrun(leaf: dict, now=None, fallback_start=None):
    """(elapsed, estimate) in minutes when a running leaf is past twice its
    estimate and at least OVERRUN_FLOOR_MINUTES; otherwise None.

    The start is started_at, else the last event that set the leaf running."""
    began = leaf.get("started_at")
    if not began:
        for event in reversed(leaf.get("progress_events") or []):
            if isinstance(event, dict) and (event.get("changes") or {}).get("status") == "running":
                began = event.get("at")
                break
    began = began or fallback_start
    if not began:
        return None
    try:
        start = datetime.fromisoformat(str(began).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.astimezone()
    except ValueError:
        return None
    if now is None:
        wall = datetime.now().astimezone()
    else:
        wall = datetime.fromtimestamp(now).astimezone() if isinstance(now, (int, float)) else now
    elapsed = (wall - start).total_seconds() / 60
    planned = leaf.get("estimate_minutes") or leaf.get("estimate") or leaf.get("estimate_max")
    if isinstance(planned, dict):
        planned = planned.get("maximum", planned.get("max", planned.get("minimum")))
    try:
        planned = float(planned)
    except (TypeError, ValueError):
        planned = float(LEAF_ESTIMATE_CAP_MINUTES)
    if elapsed > max(2 * planned, OVERRUN_FLOOR_MINUTES):
        return int(elapsed), int(planned)
    return None


def mutation_actor(actor=None):
    """Internal request-local MCP attribution handoff, never an authority grant."""
    context = os.environ.get("LHC_MCP_ACTOR_CONTEXT")
    if context is not None:
        try:
            parsed = json.loads(context)
            parsed = assignments.validate_actor(parsed)
            if parsed["source"] not in {"mcp_metadata", "declared", "unknown"}:
                raise ValueError("invalid request provenance")
            return assignments.ActorRef(parsed)
        except (ValueError, TypeError):
            return assignments.resolve_actor(environ={})
    return assignments.resolve_actor(actor)

def repair_move_field(plan_dir: Path, leaf_id: str, *, source: str, target: str,
                      expected_hash: str) -> dict:
    """Move one unknown top-level field into result/note, with a byte-exact backup.

    This recovery operation validates only the repaired leaf: a malformed sibling
    must not prevent its repair. It does not normalize fields, rewrite timestamps
    or append progress; an ordinary update records subsequent workflow changes.
    The appended JSON object preserves the source name, value and JSON type.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", leaf_id):
        raise LeafError("небезопасный id листа")
    if source in LEAF_FIELDS:
        raise LeafError("repair refuses known source fields")
    if target not in {"result", "note"}:
        raise LeafError("repair target must be result or note")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise LeafError("repair requires an explicit SHA-256 expected hash")
    plan_dir = Path(plan_dir)
    path = plan_dir / LEAVES_DIRNAME / (leaf_id + ".json")
    with file_lock(plan_dir / ".lhc-leaves.lock"):
        if path.is_symlink():
            raise LeafError("symlink листа запрещён")
        before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != expected_hash:
            raise LeafError("конфликт: лист изменён, перечитайте его")
        raw = json.loads(before)
        if not isinstance(raw, dict) or source not in raw:
            raise LeafError("repair source field is missing")
        existing = raw.get(target, "")
        if not isinstance(existing, str):
            raise LeafError("repair target must contain text")
        moved = json.dumps({source: raw[source]}, ensure_ascii=False)
        repaired = {key: value for key, value in raw.items() if key != source}
        repaired[target] = existing + ("\n\n" if existing else "") + moved
        # Do not use a lenient projection as the repaired source of truth.
        unknown = sorted(set(repaired) - set(LEAF_FIELDS))
        if unknown:
            raise unknown_field_error(path, unknown)
        task_from_leaf(repaired, path)
        serialized = json.dumps(repaired, ensure_ascii=False, indent=2) + "\n"
        backup_dir = plan_dir / ".lhc-repair-backups"
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"{leaf_id}.{expected_hash}.json"
        # Exclusive creation prevents overwriting an earlier recovery artifact.
        with backup.open("xb") as stream:
            stream.write(before)
            stream.flush()
            os.fsync(stream.fileno())
        _write_atomic(path, serialized)
    return {"id": leaf_id, "operation": "repair-move-field",
            "source": source, "target": target,
            "before_sha256": expected_hash,
            "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "backup_path": str(backup.resolve())}


def update_leaf(plan_dir: Path, leaf_id: str, fields: dict, *, create=False,
                note=None, expected_hash=None, actor=None, assignment_op=None) -> dict:
    """Serialized read/merge/validate/replace; stale optimistic writes fail."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", leaf_id):
        raise LeafError("небезопасный id листа")
    if not isinstance(fields, dict) or "progress_events" in fields:
        raise LeafError("fields: объект; историю меняет только progress")
    if set(fields) & {"assignment", "assignment_history"}:
        raise LeafError("use assign_leaf/transition_leaf to preserve assignment history")
    handoff_payload = None
    who = mutation_actor(actor)
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
        if raw.get("assignment") and fields.get("status") == "done":
            if raw["assignment"].get("state") != "accepted":
                raise LeafError("accept the explicit assignment through transition_leaf")
            if "result" in fields and fields["result"] != raw.get("result"):
                raise LeafError("accepted result cannot be changed by a metadata refresh")
        if (raw.get("assignment", {}).get("state") == "accepted" and
                "result" in fields and fields["result"] != raw.get("result")):
            raise LeafError("accepted result cannot be changed by a metadata refresh")
        if 'created_at' in fields and fields['created_at'] != raw.get('created_at'):
            raise LeafError('created_at устанавливается автоматически и не меняется')
        if "id" in fields and fields["id"] != leaf_id:
            raise LeafError("id нельзя менять")
        merged = {**raw, **fields, "id": leaf_id}
        if assignment_op is not None:
            op = assignment_op
            if op["operation"] == "assign":
                history = list(raw.get("assignment_history", []))
                previous = raw.get("assignment")
                current = assignments.new_attempt(op["assignment"], previous=previous,
                                                  history=history, actor=who)
                if previous is not None:
                    history.append(previous)
                merged["assignment"], merged["assignment_history"] = current, history
            elif op["operation"] in {"transition", "admit"}:
                if "assignment" not in raw:
                    raise LeafError("leaf has no explicit assignment")
                if raw["assignment"].get("attempt_id") != op["attempt_id"]:
                    raise LeafError("assignment_attempt_mismatch")
                if op["operation"] == "admit":
                    # One plan lock covers dependency/capacity admission and durable intent.
                    from lhc_readiness import evaluate
                    tasks, _ = split_milestones(collect_leaves(plan_dir))
                    readiness = evaluate(tasks, plan_metadata(plan_dir).get("slots"))
                    admitted = readiness["by_id"].get(leaf_id, {})
                    if admitted.get("dispatchable") is not True:
                        raise LeafError("dispatch_not_admitted:" + str(admitted.get("reason_code", "leaf_unknown")))
                if op["operation"] == "admit" and op.get("handoff_message") is not None:
                    from lhc_handoff import prepare
                    identity, handoff_payload = prepare(plan_dir, leaf_id, raw["assignment"], before,
                                                       op["handoff_message"], plan_metadata(plan_dir))
                    op["receipt"]["dispatch"]["handoff"] = identity
                merged["assignment"] = assignments.transition(
                    raw["assignment"], op["state"], attempt_id=op["attempt_id"],
                    receipt=op.get("receipt"), actor=who)
                if op["state"] == "accepted":
                    merged["status"] = "done"
                    if "result" in (op.get("receipt") or {}):
                        merged["result"] = op["receipt"]["result"].strip()
            else:
                raise LeafError("unknown assignment operation")
        if assignment_op is None and not create and raw.get("status") == "running" and merged.get("status") == "running":
            late = overrun(raw)
            if late:
                raise LeafError(
                    f"лист {leaf_id} идёт {late[0]} мин при оценке {late[1]} мин. Разбей его: доказанное "
                    "закрой (status: done, result), остальное — новые листы, по листу на объект (среда, "
                    "узел, сервис); независимые запускай параллельно. Заметки к этому листу не "
                    "принимаются, пока он не закрыт.")
        _inherit_default_model(merged, plan_metadata(plan_dir).get("default_model"))
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        if create:
            merged['created_at'] = stamp
        # Preserve legacy self-work binding only when no separate execution
        # context exists. The writer of Worker/assignment progress is not its
        # executor; explicit activate still supplies the selected self session.
        if not merged.get("session") and not (merged.get("worker") or merged.get("assignment")):
            native = os.environ.get("CODEX_THREAD_ID", "")
            if re.fullmatch(r"[0-9a-f-]{36}", native):
                merged["session"], merged["harness"] = native, "codex"
        merged["updated_at"] = stamp
        events = list(raw.get("progress_events", []))
        changes = {k: v for k, v in fields.items() if raw.get(k) != v}
        if assignment_op is not None:
            for key in ("status", "result"):
                if raw.get(key) != merged.get(key):
                    changes[key] = merged.get(key)
        if merged.get("model") and raw.get("model") != merged["model"]:
            changes["model"] = merged["model"]
        events.append({"at": stamp, "note": note or "", "changes": changes,
                       "actor": who,
                       "session": who.get("session_id") or "unknown",
                       "harness": who.get("harness") or "unknown"})
        merged["progress_events"] = events
        candidate = task_from_leaf(merged, path)
        tasks = [t for t in collect_leaves(plan_dir) if t["id"] != leaf_id] if (Path(plan_dir) / LEAVES_DIRNAME).is_dir() and any((Path(plan_dir) / LEAVES_DIRNAME).glob("*.json")) else []
        check_leaf_gates(plan_dir, candidate, create=create,
                         touches_estimate=any(k in fields for k in ESTIMATE_KEYS) or
                         (raw.get("kind") == "milestone" and candidate.get("kind") != "milestone"),
                         others=list(tasks))
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
        if handoff_payload is not None:
            from lhc_handoff import sync_intent
            sync_intent(path)
        own_hash = hashlib.sha256(serialized.encode()).hexdigest()
        if merged.get("session") and merged.get("status", "queued") in {"queued", "running"}:
            record_session_plan(merged["session"], plan_dir, leaf_id)
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
    result = {"id": leaf_id, "sha256": own_hash}
    if assignment_op is not None:
        result["assignment"] = merged["assignment"]
    if handoff_payload is not None:
        result["handoff_payload"] = handoff_payload
    return result


def assign_leaf(plan_dir, leaf_id, assignment, actor=None, expected_hash=None):
    """Atomically declare a new execution attempt without claiming native start."""
    return update_leaf(plan_dir, leaf_id, {}, actor=actor, expected_hash=expected_hash,
                       assignment_op={"operation": "assign", "assignment": assignment})


def admit_leaf(plan_dir, leaf_id, attempt_id, receipt, actor=None, expected_hash=None, handoff_message=None):
    """Atomically gate real submission and persist its intent before network I/O."""
    return update_leaf(plan_dir, leaf_id, {}, actor=actor, expected_hash=expected_hash,
                       assignment_op={"operation": "admit", "attempt_id": attempt_id,
                                      "state": "dispatching", "receipt": receipt,
                                      "handoff_message": handoff_message})


def transition_leaf(plan_dir, leaf_id, attempt_id, state, receipt=None, actor=None,
                    expected_hash=None):
    """Append a receipt to the exact current attempt under the leaf lock/CAS."""
    return update_leaf(plan_dir, leaf_id, {}, actor=actor, expected_hash=expected_hash,
                       assignment_op={"operation": "transition", "attempt_id": attempt_id,
                                      "state": state, "receipt": receipt})


# --------------------------------------------------------------------------
# the state of a plan, said in a few lines (hooks, show, every MCP answer)
# --------------------------------------------------------------------------


def _short(text: Any, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _leaf_rows(plan_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((Path(plan_dir) / LEAVES_DIRNAME).glob("*.json")):
        try:
            leaf = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(leaf, dict):
            leaf.setdefault("id", path.stem)
            rows.append(leaf)
    return rows


def _leaf_name(leaf: dict[str, Any]) -> str:
    return f"{leaf.get('id')} «{_short(leaf.get('label') or leaf.get('title'), 90)}»"


def _open_worker(leaf: dict[str, Any]) -> bool:
    worker = leaf.get("worker")
    return isinstance(worker, dict) and not worker.get("removed_at")


def plan_intent(metadata: dict[str, Any]) -> str:
    return (f"deliverable: {metadata.get('deliverable', 'implementation')}; "
            f"decomposition: {metadata.get('decomposition', 'progressive')}; "
            f"leaf cap: {leaf_estimate_cap(metadata)} min")


def undecomposed_stages(milestones: list[dict[str, Any]]) -> list[str]:
    return [str(stage["id"]) for stage in milestones
            if not stage.get("children") and stage.get("status") != "deferred"]


def handoff_findings(document: dict[str, Any]) -> list[str]:
    """Readiness is an explicit check, separate from structural validity."""
    findings = []
    if document.get("decomposition") == "complete":
        findings += [f"{ident}: этап не разложен на исполнимые листья"
                     for ident in undecomposed_stages(document.get("milestones", []))]
    for task in document.get("tasks", []):
        if task.get("kind") == "milestone" or task.get("status") == "deferred":
            continue
        missing = [key for key in ("description", "acceptance") if not str(task.get(key) or "").strip()]
        if missing:
            findings.append(f"{task['id']}: заполните {', '.join(missing)}")
    return findings


def plan_summary(plan_dir: Path, current: Any = ()) -> list[str]:
    """Done leaves with results, the current leaves with their last note, what
    runs elsewhere, what is next, overruns and Workers not yet merged."""

    rows, milestones = split_milestones(_leaf_rows(plan_dir), strict=False)
    current = [str(item) for item in current]
    explicit = [leaf for leaf in rows if isinstance(leaf.get("assignment"), dict)]
    control = goal_control(plan_dir)
    lines: list[str] = [plan_intent(plan_metadata(plan_dir)),
                        f"goal={control.get('goal_status', 'unknown')}, "
                        f"frontier={control.get('frontier', 'unknown')}, "
                        f"next_decision={control.get('next_decision', 'none')}"]
    pending_stages = undecomposed_stages(milestones)
    if pending_stages:
        lines.append("Undecomposed stages: " + ", ".join(pending_stages))
    done = [leaf for leaf in rows if leaf.get("status") == "done" and leaf.get("kind") != "milestone"]
    if done:
        lines.append("Done:")
        lines += [f"- {_leaf_name(leaf)} — {_short(leaf.get('result'), 220) or 'no result written'}"
                  for leaf in done[-12:]]
    for leaf in rows:
        if str(leaf.get("id")) in current and leaf.get("status") == "running":
            notes = [event.get("note") for event in leaf.get("progress_events") or []
                     if isinstance(event, dict) and event.get("note")]
            lines.append(f"Now: {_leaf_name(leaf)} — last note: {_short(notes[-1] if notes else '', 400) or 'none'}")
    others = [leaf for leaf in rows if leaf.get("status") in {"queued", "running"}
              and str(leaf.get("id")) not in current and leaf.get("kind") != "milestone"]
    elsewhere = [_leaf_name(leaf) for leaf in others if leaf.get("status") == "running"]
    later = [_leaf_name(leaf) for leaf in others if leaf.get("status") != "running"]
    if elsewhere:
        lines.append("Running in other sessions or Workers: " + "; ".join(elsewhere[:8]))
    if later:
        lines.append(("Saved queue: " if explicit else "Next: ") + "; ".join(later[:8]))
    late = [f"{leaf.get('id')} ({over[0]} of {over[1]} min)" for leaf in rows
            if leaf.get("status") == "running" for over in [overrun(leaf)] if over]
    if late:
        lines.append("Past twice the estimate, split by object: " + ", ".join(late[:6]))
    workers = [f"{leaf.get('id')} ({leaf['worker'].get('branch')})" for leaf in rows if _open_worker(leaf)]
    if workers:
        lines.append("Workers not merged and removed yet: " + ", ".join(workers[:8]))
    if explicit:
        lines.append(plan_state(plan_dir))
        if any(leaf["assignment"].get("state") == "delivery_unknown" or
               (leaf["assignment"].get("wake") or {}).get("state") in {"registering", "delivery_unknown"}
               for leaf in explicit):
            lines.append("Next action: reconcile the saved attempt and its existing wait. "
                         "Do not automatically repeat dispatch or register another wait.")
        elif any(leaf["assignment"].get("state") == "result_ready" for leaf in explicit):
            lines.append("Next action: verify and integrate the result, then accept the exact attempt.")
        else:
            lines.append("Next action: inspect current execution, recorded blockers and admission before dispatch.")
    lines.append(f"Whole plan: {Path(plan_dir) / 'plan.md'}")
    return lines


def plan_state(plan_dir: Path) -> str:
    """Saved progress, dependency candidates and evidenced admission are separate."""
    rows, milestones = split_milestones(_leaf_rows(plan_dir), strict=False)
    status = {str(leaf.get("id")): leaf.get("status") for leaf in rows}
    metadata = plan_metadata(plan_dir)
    module = grid_module()._load_sibling("lhc_readiness")
    decision = module.evaluate(rows, slots=metadata.get("slots")) if module else None
    done = sum(1 for value in status.values() if value == "done")
    running = [str(leaf.get("id")) for leaf in rows if leaf.get("status") == "running"]
    control = goal_control(plan_dir)
    parts = [f"Plan {Path(plan_dir).name}: {done}/{len(rows)} done", plan_intent(metadata),
             f"goal={control.get('goal_status', 'unknown')}, "
             f"frontier={control.get('frontier', 'unknown')}, "
             f"next_decision={control.get('next_decision', 'none')}"]
    pending_stages = undecomposed_stages(milestones)
    if pending_stages:
        parts.append("undecomposed stages: " + ", ".join(pending_stages))
    if running:
        parts.append("saved running " + ", ".join(running[:8]))
    if decision is None:
        parts.append("readiness unknown: evaluator unavailable; dispatchable none")
    else:
        parts.append("candidates by dependencies/capacity " + (", ".join(decision["ready"][:8]) or "none"))
        parts.append("dispatchable " + (", ".join(decision["dispatchable"][:8]) or "none"))
        reasons = [key + "=" + row["reason_code"] for key, row in decision["by_id"].items()
                   if row["dispatchable"] is not True and status.get(key) in {"queued", "blocked", "waiting"}]
        if reasons:
            parts.append("admission " + ", ".join(reasons[:8]))
    execution = []
    execution_rows = sorted(rows, key=lambda leaf:
        (leaf.get("assignment") or {}).get("state") in {"accepted", "cancelled"})
    for leaf in execution_rows:
        assignment = leaf.get("assignment")
        if not isinstance(assignment, dict):
            continue
        runtime, wake = assignment.get("observed_runtime") or {}, assignment.get("wake") or {}
        reason = wake.get("reason_code") or wake.get("reason") or (assignment.get("dispatch") or {}).get("reason")
        execution.append(f"{leaf.get('id')}: assignment={assignment.get('state') or 'unknown'}, "
                         f"runtime={runtime.get('state') or 'unknown'}, wake={wake.get('state') or 'unknown'}"
                         + (f", reason={_short(reason, 160)}" if reason else "")
                         + (f", next={wake['next_at']}" if wake.get("next_at") else ""))
    if execution:
        parts.append("execution " + " | ".join(execution[:4]))
    late = [f"{leaf.get('id')} {over[0]}/{over[1]} min" for leaf in rows
            if leaf.get("status") == "running" for over in [overrun(leaf)] if over]
    if late:
        parts.append("split now: " + ", ".join(late[:6]))
    workers = [str(leaf.get("id")) for leaf in rows if _open_worker(leaf)]
    if workers:
        parts.append("Workers to merge and remove: " + ", ".join(workers[:8]))
    return "; ".join(parts) + "."


# --------------------------------------------------------------------------
# plan.json fields and revisions: a tool, so nobody edits the file by hand
# --------------------------------------------------------------------------


def update_plan(plan_dir: Path, fields: Optional[dict] = None, revision: Optional[dict] = None) -> dict:
    """Set plan-level fields and/or append one revision, validated before writing."""

    fields = {} if fields is None else fields
    if not isinstance(fields, dict):
        raise LeafError("fields: an object of plan fields")
    unknown = sorted(set(fields) - set(PLAN_FIELDS))
    if unknown:
        raise LeafError(f"unknown plan fields: {', '.join(unknown)}; allowed: {', '.join(sorted(PLAN_FIELDS))}")
    if "revisions" in fields:
        raise LeafError('revisions are appended one at a time: pass revision {"reason": "...", "summary": "..."}')
    if revision is not None:
        if not isinstance(revision, dict) or not isinstance(revision.get("reason"), str) \
                or not revision["reason"].strip():
            raise LeafError('revision must be {"reason": "why the plan changed", "summary": "what changed"}')
        extra = sorted(set(revision) - {"reason", "summary"})
        if extra:
            raise LeafError(f"revision has unknown keys: {', '.join(extra)}; allowed: reason, summary")
    if not fields and revision is None:
        raise LeafError("nothing to change: pass fields or revision")
    path = Path(plan_dir) / PLAN_FILE
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with file_lock(Path(plan_dir) / ".lhc-leaves.lock"):
        raw = _read_json(path) if path.is_file() else {}
        if not isinstance(raw, dict):
            raise LeafError(f"{path}: the plan file must be a JSON object")
        if ("current_goal_lead" in fields and fields["current_goal_lead"] != raw.get("current_goal_lead")
                and revision is None):
            raise LeafError("current_goal_lead handoff requires an explicit revision and source_ref")
        merged = {**raw, **fields}
        if revision is not None:
            history = merged.get("revisions") if isinstance(merged.get("revisions"), list) else []
            row = {"at": stamp, "reason": revision["reason"].strip(), "actor": mutation_actor()}
            if str(revision.get("summary") or "").strip():
                row["summary"] = str(revision["summary"]).strip()
            merged["revisions"] = [*history, row]
        merged["updated_at"] = stamp
        _plan_fields(merged, path)  # the same check every reader applies: refuse before writing
        _write_atomic(path, json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    return {"plan": str(plan_dir), "changed": sorted(fields) + (["revisions"] if revision is not None else [])}


# --------------------------------------------------------------------------
# Workers: registered on their leaf, merged and removed before the leaf closes
# --------------------------------------------------------------------------


def _git(cwd: Any, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise LeafError(f"git {' '.join(args)} in {cwd}: {(done.stderr or done.stdout).strip()}")
    return done


def _safe_run_dir(path: str) -> str:
    candidate = Path(path)
    home = os.path.expanduser("~")
    if not candidate.is_absolute() or len(candidate.parts) < 4 or str(candidate) in {home, "/"}:
        raise LeafError(f"run_dir {path!r}: an absolute directory at least three levels deep, not home")
    return str(candidate)


def worker_register(plan_dir: Path, leaf_id: str, worker: str, branch: str, worktree: str,
                    run_dir: Optional[str] = None, run_host: Optional[str] = None) -> dict:
    """Bind one Worker, its branch, worktree and run directory to a leaf."""

    path = Path(plan_dir) / LEAVES_DIRNAME / f"{leaf_id}.json"
    if not path.is_file():
        raise LeafError(f"no leaf {leaf_id}: create it first, one leaf per object")
    leaf = _read_json(path)
    if _open_worker(leaf):
        raise LeafError(f"leaf {leaf_id} already has Worker {leaf['worker'].get('id')} on "
                        f"{leaf['worker'].get('branch')}: finish it with worker-finish first")
    if not str(worker or "").strip() or not str(branch or "").strip():
        raise LeafError("worker and branch are required")
    tree = Path(worktree).expanduser()
    if not tree.is_dir():
        raise LeafError(f"worktree {worktree} does not exist: create it with lhc_worktree.py create")
    head = _git(tree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if head != branch:
        raise LeafError(f"worktree {worktree} is on {head}, not on {branch}")
    if run_dir:
        _safe_run_dir(run_dir)
    record = {"id": worker.strip(), "branch": branch, "worktree": str(tree.resolve()),
              "registered_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    if run_dir:
        record["run_dir"] = run_dir
    if run_host:
        record["run_host"] = run_host
    fields: dict[str, Any] = {"worker": record, "owner": worker.strip()}
    return update_leaf(plan_dir, leaf_id, fields, note=f"Worker {worker} registered on {branch}")


def worker_finish(plan_dir: Path, leaf_id: str, task_worktree: str, result: str) -> dict:
    """Merge the Worker branch into the task branch, remove its worktree, branch
    and run directory, then close the leaf. Every step can be repeated."""

    if not str(result or "").strip():
        raise LeafError("result is required: what works; where: files, commit, receipt; not proven: ...")
    path = Path(plan_dir) / LEAVES_DIRNAME / f"{leaf_id}.json"
    if not path.is_file():
        raise LeafError(f"no leaf {leaf_id}")
    leaf = _read_json(path)
    worker = leaf.get("worker")
    if not isinstance(worker, dict):
        raise LeafError(f"leaf {leaf_id} has no registered Worker; close it with update-leaf")
    assignment = leaf.get("assignment")
    if assignment:
        if assignment.get("state") not in {"result_ready", "accepted"}:
            raise LeafError("Worker result must be result_ready before integration and acceptance")
        if assignment.get("state") == "accepted" and leaf.get("result") != result.strip():
            raise LeafError("accepted Worker result differs; reread the accepted result")
    if worker.get("removed_at"):
        if assignment and assignment.get("state") == "accepted":
            return {"id": leaf_id, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "assignment": assignment, "reused": True}
        raise LeafError(f"Worker of {leaf_id} was already merged and removed at {worker['removed_at']}")
    task = Path(task_worktree).expanduser()
    branch = str(worker.get("branch"))
    tree = Path(str(worker.get("worktree")))
    if _git(task, "status", "--porcelain").stdout.strip():
        raise LeafError(f"task worktree {task} has uncommitted changes: commit them before merging {branch}")
    exists = _git(task, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0
    if tree.is_dir() and _git(tree, "status", "--porcelain").stdout.strip():
        raise LeafError(f"Worker worktree {tree} has uncommitted changes: commit them on {branch} first")
    if assignment and assignment.get("state") == "result_ready" and not exists:
        raise LeafError("Worker branch is missing; cannot verify integration before acceptance")
    if exists and _git(task, "merge-base", "--is-ancestor", branch, "HEAD", check=False).returncode != 0:
        merged = _git(task, "merge", "--no-edit", "--no-ff", branch, check=False)
        if merged.returncode != 0:
            _git(task, "merge", "--abort", check=False)
            raise LeafError(f"merging {branch} into {task} conflicts; the merge was aborted and the leaf stays "
                            f"open: resolve it on {branch} and run worker-finish again. "
                            f"{(merged.stdout + merged.stderr).strip()[:400]}")
    if assignment and assignment.get("state") == "result_ready":
        # Integration is visible before acceptance; cleanup can safely be retried later.
        integrated = _git(task, "rev-parse", "HEAD").stdout.strip()
        transition_leaf(plan_dir, leaf_id, assignment["attempt_id"], "accepted",
                        receipt={"result": result.strip(),
                                 "integration": {"branch": branch, "commit": integrated,
                                                 "task_worktree": str(task.resolve())}})
    if tree.is_dir():
        _git(task, "worktree", "remove", str(tree))
    if exists:
        _git(task, "branch", "-d", branch)
    run_dir = worker.get("run_dir")
    if run_dir:
        target = _safe_run_dir(str(run_dir))
        if worker.get("run_host"):
            done = subprocess.run(["ssh", "-o", "BatchMode=yes", str(worker["run_host"]), "rm", "-rf", "--", target],
                                  capture_output=True, text=True, check=False)
            if done.returncode != 0:
                raise LeafError(f"merged and worktree removed, but run directory {worker['run_host']}:{target} "
                                f"was not removed: {done.stderr.strip()}; run worker-finish again")
        elif Path(target).exists():
            shutil.rmtree(target)
    record = {**worker, "removed_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    return update_leaf(plan_dir, leaf_id, {"status": "done", "result": result.strip(), "worker": record},
                       note=f"Worker {worker.get('id')}: {branch} merged, worktree, branch and run directory removed")


def check_plan(plan_dir: Path, *, handoff: bool = False) -> int:
    document = build_document(plan_dir)
    print(f"{plan_dir}: листы согласованы")
    cap = leaf_estimate_cap(document)
    findings = estimate_cap_findings(document.get("tasks", []), cap)
    if findings:
        print(f"ПРЕВЫШЕН ПРЕДЕЛ ОЦЕНКИ ЛИСТА ({cap} мин): "
              "разбейте длинную работу или поясните существующее исключение в estimate_over_limit_reason:",
              file=sys.stderr)
        for item in findings:
            print(f"  - лист {item['id']}: оценка {fmt_cap_minutes(item['minutes'])} "
                  f"при пределе {item['cap']} мин", file=sys.stderr)
        return 1
    if handoff:
        print(plan_intent(document))
        pending = undecomposed_stages(document.get("milestones", []))
        if pending:
            print("Undecomposed stages: " + ", ".join(pending))
        problems = handoff_findings(document)
        if problems:
            print("LHC: план пока не готов к передаче:\n  - " + "\n  - ".join(problems), file=sys.stderr)
            return 1
        if document.get("decomposition") == "complete":
            print("Handoff ready: complete decomposition of the declared active scope.")
        else:
            print("Handoff ready: progressive, only the decomposed work; later stages remain open.")
    return 0


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
    whole.add_argument("--handoff", action="store_true", help="also check readiness for the declared decomposition")
    build = sub.add_parser("build", help="collect the leaves into plan.graph.json")
    build.add_argument("plan_dir", type=Path)
    check = sub.add_parser("check", help="validate the leaves, write nothing")
    check.add_argument("plan_dir", type=Path)
    check.add_argument("--handoff", action="store_true", help="also check readiness for the declared decomposition")
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
    control = sub.add_parser("goal-control", help="read live native goal control or record an explicit frontier decision")
    control.add_argument("plan_dir", type=Path)
    control.add_argument("--session")
    control.add_argument("--harness")
    control.add_argument("--decision", help="explicit frontier decision JSON object")
    for name in ("create-leaf", "update-leaf", "progress"):
        edit = sub.add_parser(name)
        edit.add_argument("plan_dir", type=Path)
        edit.add_argument("leaf_id")
        edit.add_argument("--fields", default="{}", help="JSON object")
        edit.add_argument("--expected-hash")
        edit.add_argument("--note")
        edit.add_argument("--actor", help="Declared ref JSON")
    for name in ("assign-leaf", "dispatch-leaf", "reconcile-leaf", "accept-leaf"):
        operation = sub.add_parser(name)
        operation.add_argument("plan_dir", type=Path)
        operation.add_argument("leaf_id")
        operation.add_argument("--expected-hash")
        operation.add_argument("--actor", help="Declared ref JSON; never native caller metadata")
        if name == "assign-leaf":
            operation.add_argument("--assignment", required=True, help="Explicit Assignment v1 JSON")
        else:
            operation.add_argument("--attempt-id", required=True)
        if name == "dispatch-leaf":
            operation.add_argument("--message", required=True)
        if name == "accept-leaf":
            operation.add_argument("--result", required=True)

    repair = sub.add_parser("repair-move-field", help="back up and move one unknown leaf field into result/note")
    repair.add_argument("plan_dir", type=Path)
    repair.add_argument("leaf_id")
    repair.add_argument("--source", required=True)
    repair.add_argument("--target", required=True, choices=("result", "note"))
    repair.add_argument("--expected-hash", required=True)
    show = sub.add_parser("show", help="where the plan is: done leaves with results, current, next, overruns")
    show.add_argument("plan_dir", type=Path)
    show.add_argument("--current", action="append", default=[], help="leaf id of this session (repeatable)")
    plan_edit = sub.add_parser("update-plan", help="set plan.json fields and/or append one revision, validated")
    plan_edit.add_argument("plan_dir", type=Path)
    plan_edit.add_argument("--fields", default="{}", help="JSON object of plan fields")
    plan_edit.add_argument("--revision", help='JSON {"reason": "...", "summary": "..."}')
    register = sub.add_parser("worker-register", help="bind a Worker, its branch, worktree and run dir to a leaf")
    register.add_argument("plan_dir", type=Path)
    register.add_argument("leaf_id")
    register.add_argument("--worker", required=True)
    register.add_argument("--branch", required=True)
    register.add_argument("--worktree", required=True)
    register.add_argument("--run-dir")
    register.add_argument("--run-host")
    finish = sub.add_parser("worker-finish",
                            help="merge the Worker branch, remove its worktree, branch and run dir, close the leaf")
    finish.add_argument("plan_dir", type=Path)
    finish.add_argument("leaf_id")
    finish.add_argument("--task-worktree", required=True)
    finish.add_argument("--result", required=True)
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
            rendered = lhc_grid.main(["render", str(graph), "--out-dir", str(args.plan_dir)])
            if rendered:
                return rendered
            if args.report:
                checked = lhc_grid.main(["check-plan", str(args.report), str(args.graph or graph)])
                if checked:
                    return checked
            if args.handoff:
                return check_plan(args.plan_dir, handoff=True)
        elif args.command == "build":
            print(str(build_graph(args.plan_dir)))
        elif args.command == "activate":
            tool_dir = str(Path(__file__).resolve().parent)
            if tool_dir not in sys.path:
                sys.path.insert(0, tool_dir)
            import lhc_plan_mirror
            try:
                result = lhc_plan_mirror.activate(
                    args.plan_dir, args.leaf_id, config_path=args.config,
                    session=args.session, harness=args.harness, owner=args.owner,
                    note=args.note,
                )
            except lhc_plan_mirror.ActivationError as error:
                raise LeafError(str(error)) from None
            adapter = _goal_control_adapter()
            result["goal_binding"] = (adapter.bind_session_plan(
                args.plan_dir, result["session"], args.plan_dir, runtime=result["harness"])
                if adapter else {"binding": "unknown", "reason": "native_control_adapter_unavailable"})
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == "goal-control":
            if args.decision is None:
                result = goal_control(args.plan_dir)
            else:
                adapter = _goal_control_adapter()
                if adapter is None:
                    raise LeafError("native control adapter unavailable")
                session = args.session or os.environ.get("CODEX_THREAD_ID")
                if not session:
                    raise LeafError("explicit native session required for a frontier decision")
                harness = args.harness or ("codex" if session == os.environ.get("CODEX_THREAD_ID") else None)
                decision = json.loads(args.decision)
                if not isinstance(decision, dict):
                    raise LeafError("frontier decision must be an object")
                result = adapter.record_session_decision(args.plan_dir, session, args.plan_dir,
                                                         decision, runtime=harness)
            print(json.dumps(result, ensure_ascii=False))
        elif args.command in ("assign-leaf", "dispatch-leaf", "reconcile-leaf", "accept-leaf"):
            try:
                actor = json.loads(args.actor) if args.actor else None
                if args.command == "assign-leaf":
                    result = assign_leaf(args.plan_dir, args.leaf_id, json.loads(args.assignment),
                                         actor=actor, expected_hash=args.expected_hash)
                elif args.command == "accept-leaf":
                    result = transition_leaf(args.plan_dir, args.leaf_id, args.attempt_id, "accepted",
                                             receipt={"result": args.result}, actor=actor,
                                             expected_hash=args.expected_hash)
                else:
                    import lhc_execution
                    operation = (lhc_execution.dispatch_leaf if args.command == "dispatch-leaf"
                                 else lhc_execution.reconcile_leaf)
                    positional = [args.plan_dir, args.leaf_id, args.attempt_id]
                    if args.command == "dispatch-leaf":
                        positional.append(args.message)
                    result = operation(*positional, actor=mutation_actor(actor),
                                       expected_hash=args.expected_hash)
            except ValueError as error:
                raise LeafError(str(error)) from None
            print(json.dumps(result, ensure_ascii=False))
            print(plan_state(args.plan_dir))

        elif args.command == "repair-move-field":
            result = repair_move_field(args.plan_dir, args.leaf_id, source=args.source,
                                       target=args.target, expected_hash=args.expected_hash)
            print(json.dumps(result, ensure_ascii=False))
        elif args.command in ("create-leaf", "update-leaf", "progress"):
            result = update_leaf(args.plan_dir, args.leaf_id, json.loads(args.fields),
                                 create=args.command == "create-leaf", note=args.note,
                                 expected_hash=args.expected_hash,
                                 actor=json.loads(args.actor) if args.actor else None)
            build_graph(args.plan_dir)
            print(json.dumps(result, ensure_ascii=False))
            print(plan_state(args.plan_dir))
        elif args.command == "show":
            print("\n".join(plan_summary(args.plan_dir, args.current)))
        elif args.command == "update-plan":
            revision = json.loads(args.revision) if args.revision else None
            result = update_plan(args.plan_dir, json.loads(args.fields), revision)
            print(json.dumps(result, ensure_ascii=False))
            print(plan_state(args.plan_dir))
        elif args.command == "worker-register":
            result = worker_register(args.plan_dir, args.leaf_id, args.worker, args.branch, args.worktree,
                                     args.run_dir, args.run_host)
            build_graph(args.plan_dir)
            print(json.dumps(result, ensure_ascii=False))
            print(plan_state(args.plan_dir))
        elif args.command == "worker-finish":
            result = worker_finish(args.plan_dir, args.leaf_id, args.task_worktree, args.result)
            build_graph(args.plan_dir)
            print(json.dumps(result, ensure_ascii=False))
            print(plan_state(args.plan_dir))
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
            return check_plan(args.plan_dir, handoff=args.handoff)
    except (LeafError, OSError, json.JSONDecodeError) as error:
        print(f"LHC: {error}", file=sys.stderr)
        plan_dir = getattr(args, "plan_dir", None)
        if plan_dir is not None and (Path(plan_dir) / LEAVES_DIRNAME).is_dir():
            with contextlib.suppress(Exception):
                print(plan_state(plan_dir), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
