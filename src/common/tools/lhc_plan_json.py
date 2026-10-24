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
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

LEAVES_DIRNAME = "leaves"
PLAN_FILE = "plan.json"
GRAPH_FILE = "plan.graph.json"

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
LEAF_FIELDS = (
    "id",
    "label",
    "description",
    "acceptance",
    "affected_files",
    "status",
    "owner",
    "session",
    "harness",
    "model",
    "model_class",
    "depends_on",
    "parallel_with",
    "estimate_minutes",
    "estimate",
    "estimate_min",
    "estimate_max",
    "estimate_unknown_reason",
    "actual_minutes",
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
    "title",
    "goal",
    "business_result",
    "business_results",
    "current_progress",
    "external_waits",
    "slots",
    "updated_at",
    "journal",
    "planned_start_at",
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
    if not math.isfinite(value) or value < 0:
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
            raise LeafError(f"{path}: {field}: нужен ЧЧ:ММ либо ISO timestamp с часовым поясом") from error
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


# --------------------------------------------------------------------------
# one leaf
# --------------------------------------------------------------------------


def task_from_leaf(raw: Any, path: Path) -> dict[str, Any]:
    """One leaf file into one task of the graph schema."""

    if not isinstance(raw, dict):
        raise LeafError(f"{path}: лист должен быть объектом JSON")
    unknown = sorted(set(raw) - set(LEAF_FIELDS))
    if unknown:
        raise LeafError(
            f"{path}: неизвестные поля: {', '.join(unknown)}; "
            f"допустимые поля: {', '.join(sorted(LEAF_FIELDS))}"
        )

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

    for field in ("description", "acceptance", "owner", "session", "harness",
                  "model", "model_class", "note", "blocker",
                  "estimate_unknown_reason", "origin", "updated_at"):
        value = _text(raw, field, path)
        if value:
            task[field] = value

    affected = _string_list(raw, "affected_files", path)
    if affected:
        task["affected_files"] = affected
    task["supersedes"] = _string_list(raw, "supersedes", path)
    events = raw.get("progress_events", [])
    if not isinstance(events, list) or any(
        not isinstance(e, dict) or set(e) - {"at", "note", "changes", "session", "harness"}
        or not isinstance(e.get("at"), str) or not isinstance(e.get("note", ""), str)
        or not isinstance(e.get("changes", {}), dict) for e in events
    ):
        raise LeafError(f"{path}: неверный progress_events")
    if events:
        task["progress_events"] = events

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
    duration_estimate = _minutes(raw.get("duration_estimate_minutes"), "duration_estimate_minutes", path)
    if duration_estimate is not None:
        task["duration_estimate_minutes"] = duration_estimate

    for field in ("started_at", "finished_at"):
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
    for field in ("title", "goal", "business_result", "current_progress",
                  "external_waits", "updated_at", "planned_start_at"):
        value = raw.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise LeafError(f"{path}: поле {field} должно быть строкой")
        value = value.strip()
        if value:
            fields[field] = value
    results = raw.get("business_results")
    if results is not None:
        if not isinstance(results, list) or not all(
            isinstance(item, str) for item in results
        ):
            raise LeafError(f"{path}: поле business_results должно быть списком строк")
        values = [item.strip() for item in results if item.strip()]
        if values:
            fields["business_results"] = values
    slots = raw.get("slots")
    if slots is not None:
        if isinstance(slots, bool) or not isinstance(slots, int) or slots < 1:
            raise LeafError(f"{path}: поле slots должно быть целым числом от 1")
        fields["slots"] = slots
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
                          "external_waits", "updated_at"):
                value = raw.get(field)
                if isinstance(value, str) and value.strip():
                    fields[field] = value.strip()
            results = raw.get("business_results")
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


def build_document(plan_dir: Path) -> dict[str, Any]:
    """The graph document of a plan, collected from its leaf files."""

    plan_dir = Path(plan_dir)
    tasks, sources, stamps = _collect(plan_dir)
    tasks = _order(tasks, sources)
    metadata = plan_metadata(plan_dir)

    stamp = ""
    for value in stamps.values():
        if value and (not stamp or value > stamp):
            stamp = value
    if not stamp:
        stamp = str(metadata.get("updated_at") or "")

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
        "current_progress": str(metadata.get("current_progress") or ""),
        "external_waits": str(metadata.get("external_waits") or ""),
        "slots": int(metadata.get("slots") or 1),
        "updated_at": stamp,
        "tasks": tasks,
        "leaf_count": len(tasks),
    }
    journal = metadata.get("journal")
    if journal:
        document["journal"] = journal
    if metadata.get("planned_start_at"):
        document["planned_start_at"] = metadata["planned_start_at"]
    return document


def build_graph(plan_dir: Path) -> Path:
    """Collect the leaves of a plan into its plan.graph.json."""

    plan_dir = Path(plan_dir)
    document = build_document(plan_dir)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    target = plan_dir / GRAPH_FILE
    _write_atomic(target, text)
    auto_publish(plan_dir)
    return target


def auto_publish(plan_dir: Path) -> None:
    """Opt-in only; publishing failure never prevents the work being recorded."""
    if not (Path(plan_dir) / ".lhc-publication/state.json").is_file():
        return
    try:
        tool_dir = str(Path(__file__).resolve().parent)
        if tool_dir not in sys.path:
            sys.path.insert(0, tool_dir)
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
        if "id" in fields and fields["id"] != leaf_id:
            raise LeafError("id нельзя менять")
        merged = {**raw, **fields, "id": leaf_id}
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        # Only Codex's documented thread environment is auto-bound. Other
        # harnesses pass explicit session/harness; no process-title inference.
        if not merged.get("session"):
            native = os.environ.get("CODEX_THREAD_ID", "")
            if re.fullmatch(r"[0-9a-f-]{36}", native):
                merged["session"], merged["harness"] = native, "codex"
        merged["updated_at"] = stamp
        events = list(raw.get("progress_events", []))
        changes = {k: v for k, v in fields.items() if raw.get(k) != v}
        events.append({"at": stamp, "note": note or "", "changes": changes,
                       "session": merged.get("session", "unknown"),
                       "harness": merged.get("harness", "unknown")})
        merged["progress_events"] = events
        candidate = task_from_leaf(merged, path)
        tasks = [t for t in collect_leaves(plan_dir) if t["id"] != leaf_id] if (Path(plan_dir) / LEAVES_DIRNAME).is_dir() and any((Path(plan_dir) / LEAVES_DIRNAME).glob("*.json")) else []
        tasks.append(candidate)
        _order(tasks, {t["id"]: path.parent / (t["id"] + ".json") for t in tasks})
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
        _write_atomic(path, serialized)
        own_hash = hashlib.sha256(serialized.encode()).hexdigest()
    return {"id": leaf_id, "sha256": own_hash}


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
# the command line
# --------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lhc_plan_json.py",
        description="Collect the leaf files of a plan into one plan.graph.json.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="collect the leaves into plan.graph.json")
    build.add_argument("plan_dir", type=Path)
    whole = sub.add_parser("build-plan", help="collect and render the same plan")
    whole.add_argument("plan_dir", type=Path)
    whole.add_argument("--report", type=Path)
    whole.add_argument("--graph", type=Path)
    check = sub.add_parser("check", help="validate the leaves, write nothing")
    check.add_argument("plan_dir", type=Path)
    for name in ("create-leaf", "update-leaf", "progress"):
        edit = sub.add_parser(name)
        edit.add_argument("plan_dir", type=Path)
        edit.add_argument("leaf_id")
        edit.add_argument("--fields", default="{}", help="JSON object")
        edit.add_argument("--expected-hash")
        edit.add_argument("--note")
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
        elif args.command == "check":
            build_document(args.plan_dir)
            print(f"{args.plan_dir}: листы согласованы")
        else:
            result = update_leaf(args.plan_dir, args.leaf_id, json.loads(args.fields),
                                 create=args.command == "create-leaf", note=args.note,
                                 expected_hash=args.expected_hash)
            build_graph(args.plan_dir)
            print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError) as error:
        print(f"LHC: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
