#!/usr/bin/env python3
"""Render an LHC task graph as one self-contained HTML dashboard.

The dashboard answers, in one screen: what is done, what runs now, what is
blocked, roughly when the work finishes and how much of it runs in parallel.

Inputs
------
* a task graph JSON (``schema_version`` 1 or 2);
* a canonical LHC plan report (``common/protocols/PLAN_REPORT.md``);
* any task record that carries a ``## Plan`` block;
* a free-form business-first replan with a decomposition table and wave log.

One command, one artifact::

    python3 lhc_grid.py render PLAN [-o plan.html] [--open]

The renderer is offline and dependency-free: the output is a single HTML file
with inline CSS/JS, safe to attach to a message or open from a phone.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

SCHEMA_VERSIONS = (1, 2)

STATUS_DONE = "done"
STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_WAITING = "waiting"
STATUS_QUEUED = "queued"

STATUSES = (STATUS_DONE, STATUS_RUNNING, STATUS_BLOCKED, STATUS_WAITING, STATUS_QUEUED)

STATUS_LABELS = {
    STATUS_DONE: "Готово",
    STATUS_RUNNING: "В работе",
    STATUS_BLOCKED: "Заблокировано",
    STATUS_WAITING: "Ожидание",
    STATUS_QUEUED: "В очереди",
}

STATUS_GLYPHS = {
    STATUS_DONE: "✅",
    STATUS_RUNNING: "🔄",
    STATUS_BLOCKED: "⛔",
    STATUS_WAITING: "⏳",
    STATUS_QUEUED: "⋯",
}

STATUS_COLORS = {
    STATUS_DONE: "#2ecc71",
    STATUS_RUNNING: "#4f9cf9",
    STATUS_BLOCKED: "#ef4d64",
    STATUS_WAITING: "#f0a742",
    STATUS_QUEUED: "#7c8aa3",
}

WAVE_LABELS = {}


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------


@dataclass
class Leaf:
    """One decomposed leaf of the task graph."""

    id: str
    label: str = ""
    acceptance: str = ""
    status: str = STATUS_QUEUED
    owner: str = ""
    session: str = ""
    harness: str = ""
    model: str = ""
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    estimate_min: Optional[float] = None
    estimate_max: Optional[float] = None
    estimate_unknown_reason: str = ""
    actual_minutes: Optional[float] = None
    started_at: str = ""
    finished_at: str = ""
    blocker: str = ""
    blocker_details: dict[str, str] = field(default_factory=dict)
    note: str = ""
    wave: Optional[int] = None
    order: int = 0
    origin: str = ""

    @property
    def estimate(self) -> Optional[float]:
        if self.estimate_max is not None:
            return self.estimate_max
        return self.estimate_min

    @property
    def duration_label(self) -> str:
        low, high = self.estimate_min, self.estimate_max
        if low is None and high is None:
            return "Срок неизвестен" if self.estimate_unknown_reason else "—"
        if low is None or high is None:
            value = high if high is not None else low
            return f"{fmt_minutes(value)}"
        if abs(high - low) < 0.01:
            return fmt_minutes(low)
        return f"{fmt_minutes(low)}–{fmt_minutes(high)}"

    @property
    def overrun(self) -> bool:
        if self.actual_minutes is None or self.estimate_max is None:
            return False
        return self.actual_minutes > self.estimate_max + 0.01


@dataclass
class Graph:
    """A whole task graph plus its live state."""

    title: str = "LHC · граф задач"
    goal: str = ""
    business_result: str = ""
    current_progress: str = ""
    external_waits: str = ""
    leaves: list[Leaf] = field(default_factory=list)
    slots: int = 1
    declared_parallel: Optional[int] = None
    declared_leaves: Optional[int] = None
    declared_waves: Optional[int] = None
    updated_at: str = ""
    source_path: str = ""
    source_kind: str = ""
    live_items: list[dict[str, Any]] = field(default_factory=list)
    live_log: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def by_id(self) -> dict[str, Leaf]:
        return {leaf.id: leaf for leaf in self.leaves}

    def resolve_dependencies(self) -> None:
        """Drop unknown dependencies and keep the order stable."""
        known = {leaf.id for leaf in self.leaves}
        for leaf in self.leaves:
            leaf.depends_on = [dep for dep in leaf.depends_on if dep in known and dep != leaf.id]
            leaf.parallel_with = [peer for peer in leaf.parallel_with if peer in known and peer != leaf.id]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def fmt_minutes(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if abs(value - round(value)) < 0.01:
        value = round(value)
    if value < 60:
        return f"{int(value)} мин"
    hours = int(value // 60)
    minutes = int(round(value - hours * 60))
    if minutes == 0:
        return f"{hours} ч"
    return f"{hours} ч {minutes:02d} мин"


def fmt_hours(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if abs(value - round(value)) < 0.01:
        value = round(value)
    return f"{value:,.1f}".replace(",", " ") if value < 10 else f"{value:.0f}"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def tokens(text: str) -> set[str]:
    words = re.findall(r"[0-9A-Za-zА-Яа-яЁё_]{3,}", (text or "").lower())
    stop = {
        "для", "или", "после", "перед", "что", "это", "как", "при", "под", "над", "без",
        "the", "and", "for", "with", "that", "this", "not", "was", "его", "её", "их",
        "задач", "задачи", "лист", "листа", "работы", "работу", "проверку", "минут",
    }
    return {word for word in words if word not in stop}


MINUTE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:[-–—]\s*(\d+(?:[.,]\d+)?))?\s*(?:мин(?:ут|ута|ы)?|минуты|minute)",
    re.IGNORECASE,
)


def parse_minutes(text: str) -> tuple[Optional[float], Optional[float], float]:
    """Return (minimum, maximum, external_wait) minutes found in free text."""
    low: Optional[float] = None
    high: Optional[float] = None
    wait = 0.0
    source = text or ""
    matches = list(MINUTE_RE.finditer(source))
    for index, match in enumerate(matches):
        start = float(match.group(1).replace(",", "."))
        end = float(match.group(2).replace(",", ".")) if match.group(2) else start
        previous_end = matches[index - 1].end() if index else 0
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        before = source[previous_end:match.start()].lower()
        after = source[match.end():next_start].lower()
        passive = "пассивн" in before or "пассивн" in after
        waiting = any(word in before for word in ("ожидани", "ожидаем", "ожидает", "ожидать"))
        if passive or waiting:
            wait += max(start, end)
            continue
        low = start if low is None else min(low, start)
        high = end if high is None else max(high, end)
    return low, high, wait


def parse_clock(value: str) -> Optional[int]:
    """Parse ``HH:MM`` into minutes since midnight."""
    match = re.search(r"(\d{1,2}):(\d{2})", value or "")
    if not match:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def format_clock(minutes: Optional[int]) -> str:
    if minutes is None:
        return ""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def now_clock() -> int:
    return datetime.now().hour * 60 + datetime.now().minute


# --------------------------------------------------------------------------
# parsing: canonical plan report
# --------------------------------------------------------------------------


HEADER_RE = re.compile(r"^\s*(Цель|Бизнес-результат|Декомпозиция)\s*:\s*(.+?)\s*$")
LEAF_LINE_RE = re.compile(r"^\s*([✅🔄⏳⛔])\s*(.*)$")
LABEL_RE = re.compile(r"\(([^)]*)\)")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
ESTIMATE_RE = re.compile(r"оценка\s+([^,;.]+)", re.IGNORECASE)
ACTUAL_RE = re.compile(r"(?:факт|прошло)\s+([^,;.]+)", re.IGNORECASE)
PARALLEL_RE = re.compile(r"параллельно с листом\s+(\d+)", re.IGNORECASE)
AFTER_LEAF_RE = re.compile(r"после листа\s+(\d+)", re.IGNORECASE)
OVERRUN_RE = re.compile(r"отстаём потому что\s*:\s*(.+)$", re.IGNORECASE)
BLOCK_RE = re.compile(r"блокер\s*:\s*(.+)$", re.IGNORECASE)

DECOMP_LEAVES_RE = re.compile(r"(\d+)\s+(?:предварительных\s+)?лист(?:ьев|а|ы)?\b", re.IGNORECASE)
DECOMP_PARALLEL_RE = re.compile(r"(?:до\s+)?(\d+)\s+параллельно", re.IGNORECASE)
DECOMP_WAVES_RE = re.compile(r"(\d+)\s+волн", re.IGNORECASE)
DECOMP_SLOTS_RE = re.compile(r"слотов\s*:?\s*(\d+)", re.IGNORECASE)


def parse_plan_report(text: str) -> Optional[Graph]:
    """Parse the canonical live plan report format."""
    graph = Graph(source_kind="plan-report")
    leaves: list[Leaf] = []
    pending_parallel: list[tuple[int, int]] = []
    pending_after: list[tuple[int, int]] = []
    seen_leaf = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        header = HEADER_RE.match(line)
        if header and not seen_leaf:
            key, value = header.group(1), header.group(2)
            if key == "Цель":
                graph.goal = value.strip()
            elif key == "Бизнес-результат":
                graph.business_result = value.strip()
            else:
                graph.declared_leaves = _int_or_none(DECOMP_LEAVES_RE.search(value))
                graph.declared_parallel = _int_or_none(DECOMP_PARALLEL_RE.search(value))
                graph.declared_waves = _int_or_none(DECOMP_WAVES_RE.search(value))
                graph.slots = graph.declared_parallel or _int_or_none(DECOMP_SLOTS_RE.search(value)) or 1
            continue
        match = LEAF_LINE_RE.match(line)
        if not match:
            continue
        glyph, rest = match.group(1), match.group(2).strip()
        if not rest:
            continue
        seen_leaf = True
        index = len(leaves)
        status = {
            "✅": STATUS_DONE,
            "🔄": STATUS_RUNNING,
            "⏳": STATUS_QUEUED,
            "⛔": STATUS_BLOCKED,
        }.get(glyph, STATUS_QUEUED)
        if rest.startswith("работаем "):
            rest = rest[len("работаем "):]
        label_match = LABEL_RE.search(rest)
        label = normalize(label_match.group(1)) if label_match else normalize(rest.split(",")[0])
        leaf = Leaf(id=f"L{index + 1:02d}", label=label, status=status, origin="report")

        estimate_text = ESTIMATE_RE.search(rest)
        if estimate_text:
            low, high, _wait = parse_minutes(estimate_text.group(1))
            leaf.estimate_min, leaf.estimate_max = low, high
        actual_text = ACTUAL_RE.search(rest)
        if actual_text:
            if "не измерено" in actual_text.group(1).lower():
                leaf.actual_minutes = None
            else:
                low, high, _wait = parse_minutes(actual_text.group(1))
                if high is not None:
                    leaf.actual_minutes = high
        times = TIME_RE.findall(rest)
        if times:
            leaf.started_at = times[0]
            if len(times) > 1:
                leaf.finished_at = times[1]
        overrun = OVERRUN_RE.search(rest)
        if overrun:
            leaf.note = normalize(overrun.group(1))
        blocker = BLOCK_RE.search(rest)
        if blocker:
            leaf.blocker = normalize(blocker.group(1))
        parallel = PARALLEL_RE.search(rest)
        if parallel:
            pending_parallel.append((index, int(parallel.group(1))))
        after = AFTER_LEAF_RE.search(rest)
        if after:
            pending_after.append((index, int(after.group(1))))
        leaves.append(leaf)

    if not leaves:
        return None

    for index, peer in pending_parallel:
        leaves[index].parallel_with.append(f"L{peer:02d}")
    for index, peer in pending_after:
        leaves[index].depends_on.append(f"L{peer:02d}")

    graph.leaves = leaves
    graph.live_items = [
        {"status": leaf.status, "text": leaf.label or leaf.id, "leaf": leaf.id}
        for leaf in leaves
    ]
    graph.slots = graph.slots or 1
    return graph


def _int_or_none(match: Optional[re.Match]) -> Optional[int]:
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# parsing: free-form business-first replan (decomposition table + wave log)
# --------------------------------------------------------------------------

TABLE_ROW_RE = re.compile(r"^\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")
LIVE_ITEM_RE = re.compile(r"^\s*[-*]\s*([✅🔄⏳⛔])\s*(.+?)\s*$")
WAVE_HEADER_RE = re.compile(r"^##\s*(.+?)\s*$", re.IGNORECASE)
DEP_TOKEN_RE = re.compile(r"[0-9]+[а-яa-z]?")


def _table_blocks(lines: list[str]) -> list[list[list[str]]]:
    """Split a markdown document into its pipe tables."""
    blocks: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells if cell):
                continue
            current.append(cells)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _pick_decomposition_table(blocks: list[list[list[str]]]) -> Optional[list[list[str]]]:
    """Find the leaf table: it carries an id column plus estimate or dependency."""
    fallback: Optional[list[list[str]]] = None
    for block in blocks:
        if len(block) < 2:
            continue
        header = [cell.lower() for cell in block[0]]
        id_index = _column_index(header, ("№", "#", "id", "n "))
        estimate_index = _column_index(header, ("оценк", "время", "длительн", "estimate", "мин"))
        dependency_index = _column_index(header, ("зависим", "depend"))
        if id_index is None:
            continue
        if dependency_index is not None:
            return block
        if estimate_index is not None and fallback is None:
            fallback = block
    return fallback


def _column_index(header: list[str], needles: tuple[str, ...]) -> Optional[int]:
    for index, cell in enumerate(header):
        text = cell.strip().lower()
        if any(needle in text for needle in needles):
            return index
    return None


def parse_legacy_plan(text: str) -> Optional[Graph]:
    """Parse a free-form replan: decomposition table plus a wave log."""
    graph = Graph(source_kind="plan")
    lines = text.splitlines()

    goal = re.search(r"\*\*Цель:?\*\*\s*(.+)", text)
    if goal:
        graph.goal = normalize(goal.group(1))
    result = re.search(r"\*\*Бизнес-результат:?\*\*\s*(.+)", text)
    if result:
        graph.business_result = normalize(result.group(1))
    for match in DECOMP_LEAVES_RE.finditer(text):
        graph.declared_leaves = _int_or_none(match)
        break
    for match in DECOMP_PARALLEL_RE.finditer(text):
        graph.declared_parallel = _int_or_none(match)
        break
    for match in DECOMP_WAVES_RE.finditer(text):
        graph.declared_waves = _int_or_none(match)
        break
    for match in DECOMP_SLOTS_RE.finditer(text):
        graph.slots = int(match.group(1))
        break

    table_leaves: list[Leaf] = []
    block = _pick_decomposition_table(_table_blocks(lines))
    if block:
        header = [cell.lower() for cell in block[0]]
        id_index = _column_index(header, ("№", "#", "id", "n "))
        estimate_index = _column_index(header, ("оценк", "время", "длительн", "estimate", "мин"))
        dependency_index = _column_index(header, ("зависим", "depend"))
        status_index = _column_index(header, ("статус", "состояни", "state"))
        label_index = 1 if len(header) > 1 else id_index
        for order, row in enumerate(block[1:]):
            if id_index is None or id_index >= len(row):
                continue
            number = row[id_index].strip()
            if not re.fullmatch(r"[0-9]+[а-яa-z]?", number):
                continue
            label = row[label_index].strip() if label_index < len(row) else ""
            leaf = Leaf(id=number, label=normalize(label), origin="table", order=order)
            if estimate_index is not None and estimate_index < len(row):
                low, high, wait = parse_minutes(row[estimate_index])
                leaf.estimate_min, leaf.estimate_max = low, high
                if wait:
                    leaf.note = f"внешнее ожидание ≈{fmt_minutes(wait)}"
            if dependency_index is not None and dependency_index < len(row):
                leaf.depends_on = parse_dependency_cell(row[dependency_index])
            if status_index is not None and status_index < len(row):
                leaf.status = normalize_status(row[status_index])
            table_leaves.append(leaf)

    live_items: list[tuple[str, str]] = []
    for raw in lines:
        live = LIVE_ITEM_RE.match(raw)
        if live:
            glyph, body = live.group(1), normalize(live.group(2))
            status = {
                "✅": STATUS_DONE,
                "🔄": STATUS_RUNNING,
                "⏳": STATUS_QUEUED,
                "⛔": STATUS_BLOCKED,
            }.get(glyph, STATUS_QUEUED)
            live_items.append((status, body))

    if not table_leaves and not live_items:
        return None

    matched: dict[str, dict[str, Any]] = {}
    for status, body in live_items:
        target = match_live_item(body, table_leaves)
        leaf_id = ""
        if target is None:
            graph.live_log.append({"status": status, "text": body})
        else:
            leaf_id = target.id
            entry = matched.setdefault(target.id, {"status": status, "text": body})
            if status == STATUS_DONE:
                entry["status"] = STATUS_DONE
            low, high, _wait = parse_minutes(body)
            if high is not None:
                target.actual_minutes = high
            times = TIME_RE.findall(body)
            if times:
                target.started_at = times[0]
                if len(times) > 1:
                    target.finished_at = times[1]
            if status == STATUS_BLOCKED:
                target.blocker = body
            if status == STATUS_RUNNING and not target.note:
                target.note = body
        graph.live_items.append({"status": status, "text": body, "leaf": leaf_id})

    for leaf in table_leaves:
        if leaf.id in matched:
            leaf.status = matched[leaf.id]["status"]
        elif leaf.status == STATUS_QUEUED and not leaf.depends_on:
            leaf.status = STATUS_QUEUED

    graph.leaves = table_leaves
    graph.slots = graph.slots or graph.declared_parallel or 1
    if not graph.leaves:
        graph.leaves = [
            Leaf(id=f"L{index + 1:02d}", label=item["text"], status=item["status"], origin="log")
            for index, item in enumerate(graph.live_log)
        ]
        graph.live_log = []
    return graph


def parse_dependency_cell(cell: str) -> list[str]:
    """Parse a dependency cell such as ``03,04`` or ``нет, первая волна``."""
    text = (cell or "").strip().lower()
    if not text or text.startswith("нет"):
        return []
    found: list[str] = []
    for chunk in re.split(r"[,;/]", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        range_match = re.match(r"^([0-9]+[а-яa-z]?)\s*[–—-]\s*([0-9]+[а-яa-z]?)$", chunk)
        if range_match:
            start, end = range_match.group(1), range_match.group(2)
            prefix = re.sub(r"[0-9]", "", start)
            width = len(re.sub(r"[^0-9]", "", start))
            try:
                low = int(re.sub(r"[^0-9]", "", start))
                high = int(re.sub(r"[^0-9]", "", end))
            except ValueError:
                continue
            for number in range(low, high + 1):
                found.append(f"{number:0{width}d}{prefix}")
            continue
        for token in DEP_TOKEN_RE.findall(chunk):
            found.append(token)
    seen: set[str] = set()
    unique: list[str] = []
    for token in found:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def match_live_item(body: str, leaves: list[Leaf]) -> Optional[Leaf]:
    """Bind a live wave entry to the leaf it describes.

    A weak word overlap is not evidence: a wrong match would paint a leaf as
    finished when the journal never said so. Only an explicit leaf reference or
    a strong, mostly-covered label match binds.
    """
    explicit = re.search(r"лист[а-я]*\s+([0-9]+[а-яa-z]?)", body, re.IGNORECASE)
    if explicit:
        wanted = explicit.group(1)
        for leaf in leaves:
            if leaf.id.lower() == wanted.lower():
                return leaf
    body_tokens = tokens(body)
    best: Optional[Leaf] = None
    best_score = 0.0
    for leaf in leaves:
        leaf_tokens = tokens(leaf.label)
        if len(leaf_tokens) < 3:
            continue
        overlap = body_tokens & leaf_tokens
        if len(overlap) < 3:
            continue
        coverage = len(overlap) / len(leaf_tokens)
        if coverage < 0.6:
            continue
        score = coverage * len(overlap)
        if score > best_score:
            best, best_score = leaf, score
    return best


# --------------------------------------------------------------------------
# parsing: graph JSON
# --------------------------------------------------------------------------


def parse_graph_json(document: Any) -> Graph:
    if not isinstance(document, dict):
        raise ValueError("graph must be a JSON object")
    version = document.get("schema_version")
    if version not in SCHEMA_VERSIONS:
        raise ValueError(f"unsupported schema_version: {version!r}")
    graph = Graph(source_kind="graph-json")
    graph.title = str(document.get("title") or graph.title)
    graph.goal = str(document.get("goal") or "")
    graph.business_result = str(document.get("business_result") or "")
    graph.current_progress = str(document.get("current_progress") or "")
    graph.external_waits = str(document.get("external_waits") or "")
    graph.updated_at = str(document.get("updated_at") or "")
    graph.slots = int(document.get("slots") or 1)
    graph.declared_parallel = document.get("parallel")
    graph.declared_leaves = document.get("leaf_count")
    graph.declared_waves = document.get("wave_count")

    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a nonempty list")
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] must be an object")
        raw_blocker_details = task.get("blocker_details")
        if not isinstance(raw_blocker_details, dict):
            raw_blocker_details = {}
        leaf = Leaf(
            id=str(task.get("id") or f"task-{index + 1}"),
            label=normalize(str(task.get("label") or task.get("outcome") or task.get("acceptance") or "")),
            acceptance=normalize(str(task.get("acceptance") or task.get("description") or "")),
            status=normalize_status(task.get("status") or STATUS_QUEUED),
            owner=str(task.get("owner") or task.get("role") or ""),
            session=str(task.get("session") or ""),
            harness=str(task.get("harness") or ""),
            model=str(task.get("model") or task.get("model_class") or ""),
            depends_on=[str(item) for item in (task.get("depends_on") or [])],
            parallel_with=[str(item) for item in (task.get("parallel_with") or [])],
            started_at=str(task.get("started_at") or ""),
            finished_at=str(task.get("finished_at") or ""),
            blocker=normalize(str(task.get("blocker") or "")),
            blocker_details={
                str(key): normalize(str(value))
                for key, value in raw_blocker_details.items()
                if key in {"reason", "responsible", "next_action", "human_required", "human_action"}
                and value is not None
            },
            note=normalize(str(task.get("note") or "")),
            wave=task.get("wave") if isinstance(task.get("wave"), int) else None,
            order=index,
            origin="graph",
        )
        estimate = task.get("estimate_minutes")
        if isinstance(estimate, dict):
            leaf.estimate_min = _number(estimate.get("minimum"))
            leaf.estimate_max = _number(estimate.get("maximum"))
        elif isinstance(estimate, (int, float)):
            leaf.estimate_min = leaf.estimate_max = float(estimate)
        leaf.estimate_unknown_reason = normalize(str(task.get("estimate_unknown_reason") or ""))
        actual = task.get("actual_minutes")
        if actual is not None:
            leaf.actual_minutes = _number(actual)
        graph.leaves.append(leaf)
    return graph


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:[.,]\d+)?", value)
        if match:
            return float(match.group(0).replace(",", "."))
    return None


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    aliases = {
        "done": STATUS_DONE, "complete": STATUS_DONE, "completed": STATUS_DONE,
        "finished": STATUS_DONE, "готово": STATUS_DONE,
        "running": STATUS_RUNNING, "in_progress": STATUS_RUNNING, "active": STATUS_RUNNING,
        "в_работе": STATUS_RUNNING,
        "blocked": STATUS_BLOCKED, "blocker": STATUS_BLOCKED, "заблокировано": STATUS_BLOCKED,
        "waiting": STATUS_WAITING, "wait": STATUS_WAITING, "ожидание": STATUS_WAITING,
        "queued": STATUS_QUEUED, "todo": STATUS_QUEUED, "pending": STATUS_QUEUED,
        "в_очереди": STATUS_QUEUED,
    }
    return aliases.get(text, STATUS_QUEUED)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def load_graph(path: Path) -> Graph:
    text = path.read_text(encoding="utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            document = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON: {error}") from error
        graph = parse_graph_json(document)
    else:
        graph = parse_plan_report(text) or parse_legacy_plan(text)
        if graph is None:
            raise ValueError("no LHC plan or graph found in this file")
    graph.source_path = str(path)
    if not graph.title:
        graph.title = path.stem
    graph.resolve_dependencies()
    return graph


def discover_graph(path: Path) -> Graph:
    """Accept a file or a directory holding a plan record or graph."""
    if path.is_dir():
        candidates = [
            path / "plan.graph.json",
            path / "graph.json",
            path / "tasks.graph.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return load_graph(candidate)
        for candidate in sorted(path.glob("*.md")):
            graph = parse_plan_report(candidate.read_text(encoding="utf-8", errors="replace"))
            if graph and graph.leaves:
                graph.source_path = str(candidate)
                graph.resolve_dependencies()
                return graph
        raise ValueError(f"no graph or plan found in {path}")
    return load_graph(path)


# --------------------------------------------------------------------------
# scheduling
# --------------------------------------------------------------------------


@dataclass
class Schedule:
    starts: dict[str, float] = field(default_factory=dict)
    finishes: dict[str, float] = field(default_factory=dict)
    makespan: float = 0.0
    waves: dict[str, int] = field(default_factory=dict)
    concurrency: list[tuple[float, float, int]] = field(default_factory=list)
    peak: int = 0
    critical_path: list[str] = field(default_factory=list)
    effort: float = 0.0


def schedule_graph(graph: Graph, use_max: bool = True, only_pending: bool = False) -> Schedule:
    """List-schedule the leaves with a hard slot limit."""
    leaves = {leaf.id: leaf for leaf in graph.leaves}
    durations: dict[str, float] = {}
    for leaf in graph.leaves:
        if only_pending and leaf.status == STATUS_DONE:
            durations[leaf.id] = 0.0
            continue
        value = leaf.estimate_max if use_max else leaf.estimate_min
        if value is None:
            value = leaf.estimate_min if leaf.estimate_max is None else leaf.estimate_max
        durations[leaf.id] = float(value or 0.0)

    order = _topological_order(leaves)
    result = Schedule(effort=sum(durations.values()))
    if not order:
        return result

    remaining = set(order)
    running: dict[str, float] = {}
    finished: set[str] = set()
    time = 0.0
    while remaining or running:
        ready = [
            leaf_id for leaf_id in order
            if leaf_id in remaining and all(dep in finished for dep in leaves[leaf_id].depends_on)
        ]
        free_slots = max(1, graph.slots) - len(running)
        for leaf_id in ready:
            if free_slots <= 0:
                break
            result.starts[leaf_id] = time
            running[leaf_id] = time + durations[leaf_id]
            remaining.discard(leaf_id)
            free_slots -= 1
        if not running:
            break
        next_time = min(running.values())
        finished_now = [leaf_id for leaf_id, end in running.items() if end <= next_time + 1e-9]
        for leaf_id in finished_now:
            result.finishes[leaf_id] = running.pop(leaf_id)
            finished.add(leaf_id)
        time = next_time
    result.makespan = max(result.finishes.values()) if result.finishes else 0.0

    layers = _layers(leaves)
    for leaf_id, layer in layers.items():
        result.waves[leaf_id] = layer
    for leaf in graph.leaves:
        if leaf.wave is not None:
            result.waves[leaf.id] = leaf.wave

    profile = _concurrency_profile(result.starts, result.finishes, durations)
    result.concurrency = profile
    result.peak = max((count for _start, _end, count in profile), default=0)
    result.critical_path = _critical_path(leaves, durations)
    return result


def _topological_order(leaves: dict[str, Leaf]) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(leaf_id: str) -> None:
        if leaf_id in seen or leaf_id in visiting:
            return
        visiting.add(leaf_id)
        for dep in leaves[leaf_id].depends_on:
            if dep in leaves:
                visit(dep)
        visiting.discard(leaf_id)
        seen.add(leaf_id)
        order.append(leaf_id)

    for leaf_id in leaves:
        visit(leaf_id)
    return order


def _layers(leaves: dict[str, Leaf]) -> dict[str, int]:
    layers: dict[str, int] = {}
    for leaf_id in _topological_order(leaves):
        deps = [dep for dep in leaves[leaf_id].depends_on if dep in leaves]
        layers[leaf_id] = 1 + max((layers.get(dep, 0) for dep in deps), default=-1)
    return layers


def _concurrency_profile(
    starts: dict[str, float], finishes: dict[str, float], durations: dict[str, float]
) -> list[tuple[float, float, int]]:
    points: list[float] = [0.0]
    for value in list(starts.values()) + list(finishes.values()):
        points.append(float(value))
    points = sorted(set(points))
    profile: list[tuple[float, float, int]] = []
    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        if end <= start:
            continue
        count = sum(
            1 for leaf_id, begin in starts.items()
            if begin <= start and finishes.get(leaf_id, begin) > start
        )
        profile.append((start, end, count))
    return profile


def _critical_path(leaves: dict[str, Leaf], durations: dict[str, float]) -> list[str]:
    best: dict[str, float] = {}
    parent: dict[str, Optional[str]] = {}
    for leaf_id in _topological_order(leaves):
        deps = [dep for dep in leaves[leaf_id].depends_on if dep in leaves]
        if deps:
            chosen = max(deps, key=lambda dep: best.get(dep, 0.0))
            best[leaf_id] = best.get(chosen, 0.0) + durations.get(leaf_id, 0.0)
            parent[leaf_id] = chosen
        else:
            best[leaf_id] = durations.get(leaf_id, 0.0)
            parent[leaf_id] = None
    if not best:
        return []
    tail = max(best, key=lambda key: best[key])
    chain: list[str] = []
    current: Optional[str] = tail
    while current:
        chain.append(current)
        current = parent.get(current)
    chain.reverse()
    return chain


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def build_metrics(graph: Graph) -> dict[str, Any]:
    counts = {status: 0 for status in STATUSES}
    for leaf in graph.leaves:
        counts[leaf.status] = counts.get(leaf.status, 0) + 1
    total = len(graph.leaves)

    # The live layer is what actually happened; the graph layer is the plan.
    live_counts = {status: 0 for status in STATUSES}
    for item in graph.live_items:
        live_counts[item.get("status", STATUS_QUEUED)] = (
            live_counts.get(item.get("status", STATUS_QUEUED), 0) + 1
        )
    live_total = len(graph.live_items)
    use_live = live_total > 0
    headline = live_counts if use_live else counts
    headline_total = live_total if use_live else total
    done = headline.get(STATUS_DONE, 0)
    running = headline.get(STATUS_RUNNING, 0)
    blocked = headline.get(STATUS_BLOCKED, 0)
    queued = headline.get(STATUS_QUEUED, 0)
    waiting = headline.get(STATUS_WAITING, 0)

    schedule_max = schedule_graph(graph, use_max=True)
    schedule_min = schedule_graph(graph, use_max=False)
    pending_max = schedule_graph(graph, use_max=True, only_pending=True)
    pending_min = schedule_graph(graph, use_max=False, only_pending=True)

    unknown_estimate_pending = [
        leaf for leaf in graph.leaves
        if leaf.status != STATUS_DONE and leaf.estimate_min is None and leaf.estimate_max is None
    ]
    unknown_estimate_all = [
        leaf for leaf in graph.leaves
        if leaf.estimate_min is None and leaf.estimate_max is None
    ]

    effort = sum(leaf.estimate or 0.0 for leaf in graph.leaves)
    critical = schedule_max.critical_path
    critical_minutes = sum(
        (leaf.estimate_max or 0.0) for leaf in graph.leaves if leaf.id in critical
    )

    current_peak = running
    slot_limit = graph.slots or 1
    blocked_minutes = sum(
        (leaf.estimate_max or 0.0) for leaf in graph.leaves if leaf.status == STATUS_BLOCKED
    )

    now = now_clock()
    eta_min = pending_min.makespan
    eta_max = pending_max.makespan
    eta_from = now
    # The plan may already be inside a working day; anchor the forecast on the
    # last observed activity so a stale "now" does not distort the horizon.
    anchor = _plan_anchor(graph)
    if anchor is not None:
        # A historic activity timestamp must never place the forecast in the past.
        eta_from = max(anchor, now)
    external_wait_unknown = bool(graph.external_waits.strip())
    eta_known = not unknown_estimate_pending and not external_wait_unknown

    return {
        "total": total,
        "live_total": live_total,
        "use_live": use_live,
        "counts": counts,
        "live_counts": live_counts,
        "headline_counts": headline,
        "headline_total": headline_total,
        "done": done,
        "running": running,
        "blocked": blocked,
        "queued": queued,
        "waiting": waiting,
        "progress_pct": round(100.0 * done / headline_total, 1) if headline_total else 0.0,
        "graph_progress_pct": round(100.0 * counts[STATUS_DONE] / total, 1) if total else 0.0,
        "effort_minutes": effort,
        "delivery_minutes_min": schedule_min.makespan,
        "delivery_minutes_max": schedule_max.makespan,
        "remaining_minutes_min": eta_min,
        "remaining_minutes_max": eta_max,
        "blocked_minutes": blocked_minutes,
        "slots": slot_limit,
        "current_parallel": current_peak,
        "planned_peak_parallel": schedule_max.peak,
        "critical_path": critical,
        "critical_minutes": critical_minutes,
        "unknown_estimate_pending": len(unknown_estimate_pending),
        "unknown_estimate_all": len(unknown_estimate_all),
        "external_wait_unknown": external_wait_unknown,
        "eta_clock_min": "" if not eta_known else format_clock((eta_from + int(round(eta_max))) % (24 * 60)),
        "eta_clock_max": "" if not eta_known else format_clock((eta_from + int(round(eta_min))) % (24 * 60)),
        "schedule": schedule_max,
        "schedule_min": schedule_min,
        "pending": pending_max,
    }


def _plan_anchor(graph: Graph) -> Optional[int]:
    stamps: list[int] = []
    for leaf in graph.leaves:
        for value in (leaf.started_at, leaf.finished_at):
            parsed = parse_clock(value)
            if parsed is not None:
                stamps.append(parsed)
    return max(stamps) if stamps else None


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(graph: Graph, metrics: dict[str, Any]) -> str:
    schedule: Schedule = metrics["schedule"]
    leaves = sorted(graph.leaves, key=lambda leaf: (schedule.waves.get(leaf.id, 0), leaf.order))
    label_by_id = {leaf.id: leaf.label or leaf.id for leaf in graph.leaves}
    total = metrics["total"]
    now = now_clock()

    # ----- KPI cards -----------------------------------------------------
    headline_total = metrics["headline_total"]
    cards = [
        (
            "Готово",
            f"{metrics['done']} / {headline_total}",
            f"{metrics['progress_pct']}%"
            + (" по журналу волны" if metrics["use_live"] else " листьев"),
            STATUS_DONE,
        ),
        ("В работе", str(metrics["running"]), "сейчас выполняется", STATUS_RUNNING),
        ("Заблокировано", str(metrics["blocked"]), "нужен внешний ход", STATUS_BLOCKED),
        ("Осталось", str(metrics["queued"] + metrics["waiting"]), "в очереди и ожидании", STATUS_QUEUED),
        (
            "Параллельность",
            f"{metrics['current_parallel']} / {metrics['slots']}",
            f"пик по плану {metrics['planned_peak_parallel']}",
            STATUS_RUNNING,
        ),
        (
            ("Известная часть работы" if metrics["unknown_estimate_pending"] or metrics["external_wait_unknown"]
             else "Осталось по плану"),
            fmt_minutes(metrics["remaining_minutes_max"]),
            ("без неизвестных оценок и ожиданий" if metrics["unknown_estimate_pending"] or metrics["external_wait_unknown"]
             else f"минимум {fmt_minutes(metrics['remaining_minutes_min'])}"),
            STATUS_WAITING,
        ),
        (
            "Прогноз финиша",
            metrics["eta_clock_max"] or "Срок неизвестен",
            ("Есть внешние ожидания без подтверждённого срока" if metrics["external_wait_unknown"] else
             f"{metrics['unknown_estimate_pending']} листьев без оценки" if metrics["unknown_estimate_pending"]
             else f"если остаток стартует сейчас · мин. {metrics['eta_clock_min']}"),
            STATUS_DONE,
        ),
        (
            "Усилие",
            fmt_minutes(metrics["effort_minutes"]),
            f"критический путь {fmt_minutes(metrics['critical_minutes'])}",
            STATUS_QUEUED,
        ),
    ]
    card_html = "".join(
        f'<div class="kpi" style="--accent:{STATUS_COLORS.get(tone, "#6ea8fe")}">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(value)}</div>'
        f'<div class="kpi-hint">{escape(hint)}</div>'
        "</div>"
        for label, value, hint, tone in cards
    )

    # ----- progress bar --------------------------------------------------
    headline = metrics["headline_counts"]
    segments = []
    for status in STATUSES:
        count = headline.get(status, 0)
        if not count:
            continue
        segments.append(
            f'<div class="seg" style="width:{100.0 * count / max(headline_total, 1):.4f}%;'
            f'background:{STATUS_COLORS[status]}" title="{STATUS_LABELS[status]}: {count}"></div>'
        )
    legend = "".join(
        f'<span class="legend-item"><i style="background:{STATUS_COLORS[status]}"></i>'
        f"{STATUS_LABELS[status]} · {headline.get(status, 0)}</span>"
        for status in STATUSES
        if headline.get(status, 0)
    )

    # ----- gantt ---------------------------------------------------------
    horizon = max(schedule.makespan, metrics["delivery_minutes_max"], 1.0)
    ticks = 6
    axis = "".join(
        f'<div class="tick tick-{index}" style="left:{100.0 * index / ticks:.4f}%">'
        f"{fmt_minutes(horizon * index / ticks)}</div>"
        for index in range(ticks + 1)
    )
    gantt_rows: list[str] = []
    current_wave: Optional[int] = None
    wave_counts: dict[int, int] = {}
    for leaf in leaves:
        wave_counts[schedule.waves.get(leaf.id, 0)] = wave_counts.get(schedule.waves.get(leaf.id, 0), 0) + 1
    for leaf in leaves:
        wave = schedule.waves.get(leaf.id, 0)
        if wave != current_wave:
            current_wave = wave
            gantt_rows.append(
                f'<div class="wave-row"><span>Волна {wave + 1}</span>'
                f'<span class="wave-count">{wave_counts.get(wave, 0)} листьев</span></div>'
            )
        start = schedule.starts.get(leaf.id, 0.0)
        finish = schedule.finishes.get(leaf.id, start)
        left = 100.0 * start / horizon
        width = max(0.6, 100.0 * max(finish - start, 0.0) / horizon)
        color = STATUS_COLORS[leaf.status]
        critical = leaf.id in metrics["critical_path"]
        tooltip = (
            f"{leaf.label}\n"
            f"статус: {STATUS_LABELS[leaf.status]}\n"
            f"оценка: {leaf.duration_label}"
            + (f"\nфакт: {fmt_minutes(leaf.actual_minutes)}" if leaf.actual_minutes is not None else "")
            + (f"\nначало: {leaf.started_at}" if leaf.started_at else "")
            + (f"\nконец: {leaf.finished_at}" if leaf.finished_at else "")
            + (f"\nзависит: {', '.join(label_by_id.get(dep, dep) for dep in leaf.depends_on)}" if leaf.depends_on else "")
            + (f"\nпараллельно: {', '.join(label_by_id.get(peer, peer) for peer in leaf.parallel_with)}" if leaf.parallel_with else "")
            + (f"\nблокер: {leaf.blocker}" if leaf.blocker else "")
            + ("\nна критическом пути" if critical else "")
        )
        title = escape(tooltip)
        critical_mark = '<span class="crit" title="критический путь">◆</span>' if critical else ""
        gantt_rows.append(
            f'<div class="gantt-row" data-status="{leaf.status}" data-leaf="{escape(leaf.id)}">'
            f'<div class="gantt-label" title="{escape(leaf.label)}">'
            f'<span class="dot" style="background:{color}"></span>'
            f'<span class="gantt-text">{escape(leaf.label)}</span>'
            f"{critical_mark}</div>"
            f'<div class="gantt-track">'
            f'<div class="bar" style="left:{left:.4f}%;width:{width:.4f}%;background:{color}" title="{title}">'
            f"</div></div></div>"
        )
    gantt_html = "".join(gantt_rows)

    # ----- blockers ------------------------------------------------------
    blockers = [leaf for leaf in leaves if leaf.status == STATUS_BLOCKED]
    blocker_html = ""
    if blockers:
        items = []
        for leaf in blockers:
            details = leaf.blocker_details
            reason = details.get("reason") or leaf.blocker or leaf.note or "Причина не указана."
            responsible = details.get("responsible") or leaf.owner or "Исполнитель не указан."
            next_action = details.get("next_action") or leaf.note or "Следующий шаг не указан."
            required = details.get("human_required", "unknown").lower()
            human_label = {"yes": "Да", "no": "Нет", "unknown": "Пока неизвестно"}.get(required, "Пока неизвестно")
            human_action = details.get("human_action") or "Действие человека не уточнено."
            waits = ", ".join(label_by_id.get(dep, dep) for dep in leaf.depends_on) if leaf.depends_on else "Внешнее условие"
            items.append(
                f'<div class="blocker"><div class="blocker-head">'
                f'<span class="badge" style="background:{STATUS_COLORS[STATUS_BLOCKED]}">'
                "Ожидает</span>"
                f"<b>{escape(leaf.label or leaf.id)}</b></div>"
                f'<div class="blocker-reason"><b>Почему ждём:</b> {escape(reason)}</div>'
                f'<div class="blocker-meta"><b>Кто делает:</b> {escape(responsible)}</div>'
                f'<div class="blocker-meta"><b>Следующий шаг:</b> {escape(next_action)}</div>'
                f'<div class="blocker-meta"><b>Нужен ли человек:</b> {escape(human_label)}. {escape(human_action)}</div>'
                f'<div class="blocker-meta"><b>Зависит от:</b> {escape(waits)} · оценка {escape(leaf.duration_label)}</div>'
                "</div>"
            )
        blocker_html = "".join(items)
    else:
        blocker_html = '<div class="empty">Активных блокеров нет.</div>'

    # ----- sessions ------------------------------------------------------
    session_rows = []
    for leaf in leaves:
        if not (leaf.owner or leaf.session or leaf.harness or leaf.model):
            continue
        session_rows.append(
            "<tr>"
            f'<td><span class="dot" style="background:{STATUS_COLORS[leaf.status]}"></span>'
            f"{escape(leaf.id)}</td>"
            f"<td>{escape(leaf.label[:70])}</td>"
            f"<td>{escape(leaf.owner or '—')}</td>"
            f"<td>{escape(leaf.session or '—')}</td>"
            f"<td>{escape(leaf.harness or '—')}</td>"
            f"<td>{escape(leaf.model or '—')}</td>"
            f"<td>{escape(STATUS_LABELS[leaf.status])}</td>"
            "</tr>"
        )
    sessions_html = (
        "<div class='table-scroll'><table class='table'><thead><tr><th>ID</th><th>Лист</th><th>Владелец</th>"
        "<th>Сессия</th><th>Harness</th><th>Модель</th><th>Статус</th></tr></thead><tbody>"
        + "".join(session_rows)
        + "</tbody></table></div>"
        if session_rows
        else '<div class="empty">Владельцы и сессии в графе не указаны.</div>'
    )

    # ----- leaves table --------------------------------------------------
    table_rows = []
    detail_templates = []
    for details_index, leaf in enumerate(leaves):
        deps = ", ".join(label_by_id.get(dep, dep) for dep in leaf.depends_on) or "—"
        peer = ", ".join(label_by_id.get(other, other) for other in leaf.parallel_with) or "—"
        actual = fmt_minutes(leaf.actual_minutes) if leaf.actual_minutes is not None else "не измерено"
        over = " over" if leaf.overrun else ""
        details = (
            f"<dl class='task-details'><dt>Код</dt><dd>{escape(leaf.id)}</dd>"
            + (f"<dt>Ожидаемый результат</dt><dd>{escape(leaf.acceptance)}</dd>" if leaf.acceptance else "")
            + f"<dt>Владелец</dt><dd>{escape(leaf.owner or '—')}</dd>"
            f"<dt>Зависит от</dt><dd>{escape(deps)}</dd>"
            f"<dt>Параллельно с</dt><dd>{escape(peer)}</dd>"
            f"<dt>Блокер / примечание</dt><dd>{escape(leaf.blocker or leaf.note or '—')}</dd>"
            f"<dt>Сессия</dt><dd>{escape(leaf.session or '—')}</dd></dl>"
        )
        detail_templates.append(
            f"<template id='task-details-template-{details_index}'><div class='task-details-card'>"
            f"<div class='task-details-head'><h3>{escape(leaf.label)}</h3>"
            "<button type='button' class='task-details-close'>Закрыть</button></div>"
            f"{details}</div></template>"
        )
        table_rows.append(
            f'<tr data-status="{leaf.status}" data-text="{escape((leaf.id + " " + leaf.label).lower())}">'
            f"<td class='task-title'>{escape(leaf.label)}</td>"
            f'<td><span class="status" style="--c:{STATUS_COLORS[leaf.status]}">'
            f"{STATUS_GLYPHS[leaf.status]} {STATUS_LABELS[leaf.status]}</span></td>"
            f"<td>{escape(leaf.duration_label)}</td>"
            f'<td class="{over.strip()}">{escape(actual)}</td>'
            f"<td><button type='button' class='task-details-trigger' data-details-id='{details_index}' "
            "aria-expanded='false'>Подробности</button></td>"
            "</tr>"
        )
    leaves_table = (
        "<div class='table-scroll'><table class='table table-leaves'><thead><tr><th>Задача</th><th>Статус</th>"
        "<th>Оценка</th><th>Факт</th><th>Детали</th></tr></thead><tbody>"
        + "".join(table_rows)
        + "</tbody></table></div>"
    )
    leaves_details = (
        "<div id='task-details-host' class='task-details-host' hidden></div>"
        + "".join(detail_templates)
    )

    # ----- live journal --------------------------------------------------
    journal = graph.live_items or [
        {"status": leaf.status, "text": leaf.label or leaf.id, "leaf": leaf.id}
        for leaf in leaves
    ]
    live_html = ""
    if journal:
        items = []
        for item in journal:
            status = item.get("status", STATUS_QUEUED)
            color = STATUS_COLORS.get(status, STATUS_COLORS[STATUS_QUEUED])
            leaf_tag = ""
            if item.get("leaf"):
                leaf_name = label_by_id.get(str(item["leaf"]))
                if leaf_name:
                    leaf_tag = f'<span class="leaf-tag">{escape(leaf_name)}</span>'
            items.append(
                f'<li><span class="dot" style="background:{color}"></span>'
                f'<span class="live-text">{escape(item.get("text", ""))}</span>{leaf_tag}</li>'
            )
        live_html = f'<ul class="live">{"".join(items)}</ul>'
    else:
        live_html = '<div class="empty">Журнал волны пуст.</div>'

    # ----- forecast ------------------------------------------------------
    critical_chain = " → ".join(label_by_id.get(item, item) for item in metrics["critical_path"]) or "—"
    unknown_forecast = (
        f"<li><b>Срок ожидания</b>: неизвестен — {metrics['unknown_estimate_pending']} незавершённых листьев без оценки</li>"
        if metrics["unknown_estimate_pending"] else ""
    )
    external_forecast = (
        "<li><b>Срок завершения</b>: неизвестен из-за ожиданий вне активной работы</li>"
        if metrics["external_wait_unknown"] else ""
    )
    unknown_effort = (
        f" · {metrics['unknown_estimate_all']} оценок неизвестны"
        if metrics["unknown_estimate_all"] else ""
    )
    forecast_html = (
        "<ul class='facts'>"
        f"<li><b>Усилие</b> (сумма известных оценок): {escape(fmt_minutes(metrics['effort_minutes']))}"
        f"{escape(unknown_effort)}</li>"
        f"<li><b>{'Известная активная работа' if metrics['unknown_estimate_pending'] or metrics['external_wait_unknown'] else 'Длительность'}"
        f" (план с {metrics['slots']} слотами): "
        f"{escape(fmt_minutes(metrics['delivery_minutes_max']))}</li>"
        f"<li><b>Осталось</b> (без завершённых): "
        f"{escape(fmt_minutes(metrics['remaining_minutes_max']))}</li>"
        f"<li><b>Пик параллельности</b> по плану: {metrics['planned_peak_parallel']} "
        f"из {metrics['slots']} слотов</li>"
        f"<li><b>Критический путь</b>: {escape(critical_chain)}</li>"
        f"<li><b>Заблокировано</b> работы: {escape(fmt_minutes(metrics['blocked_minutes']))}</li>"
        f"{unknown_forecast}"
        f"{external_forecast}"
        "</ul>"
    )

    notes_html = ""
    if graph.notes:
        notes_html = "<ul class='notes'>" + "".join(
            f"<li>{escape(note)}</li>" for note in graph.notes
        ) + "</ul>"

    source_label = graph.source_path or "—"
    generated = datetime.now().strftime("%d.%m.%Y %H:%M")
    if metrics["use_live"]:
        layer_hint = (
            f'<div class="hint">прогресс — по журналу волны ({metrics["live_total"]} пунктов), '
            f'в графе {metrics["total"]} листьев. Статус листа проставлен только там, '
            f"где журнал прямо называет лист.</div>"
        )
    else:
        layer_hint = (
            f'<div class="hint">граф: {metrics["total"]} листьев · слотов: {metrics["slots"]} · '
            f"пик параллельности {metrics['planned_peak_parallel']}</div>"
        )
    goal_block = ""
    if graph.goal or graph.business_result or graph.current_progress:
        goal_block = (
            "<div class='goal'>"
            + (f"<div><span>Цель</span>{escape(graph.goal)}</div>" if graph.goal else "")
            + (f"<div><span>Ожидаемый бизнес-результат</span>{escape(graph.business_result)}</div>"
               if graph.business_result else "")
            + (f"<div><span>Подтверждённый прогресс</span>{escape(graph.current_progress)}</div>"
               if graph.current_progress else "")
            + (f"<div><span>Внешние ожидания</span>{escape(graph.external_waits)}</div>"
               if graph.external_waits else "")
            + "</div>"
        )

    return HTML_TEMPLATE.format(
        title=escape(graph.title),
        generated=generated,
        source=escape(source_label),
        kind=escape(graph.source_kind),
        cards=card_html,
        segments="".join(segments),
        legend=legend,
        goal_block=goal_block,
        axis=axis,
        gantt=gantt_html,
        blockers=blocker_html,
        sessions=sessions_html,
        leaves_table=leaves_table,
        leaves_details=leaves_details,
        layer_hint=layer_hint,
        live=live_html,
        forecast=forecast_html,
        notes=notes_html,
        total=total,
    )



HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · LHC</title>
<style>
  :root {{
    --bg: #0d1117;
    --panel: #151b26;
    --panel-2: #1b2331;
    --line: #26303f;
    --text: #e6edf6;
    --muted: #93a1b5;
    --accent: #6ea8fe;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg);
    color: var(--text);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, "Helvetica Neue", Arial, sans-serif;
    padding: 24px clamp(12px, 3vw, 40px) 64px;
    min-height: 100%;
    overflow-x: hidden;
  }}
  body::before {{
    content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background: radial-gradient(1200px 600px at 10% -10%, #16233a 0%, #0d1117 55%);
  }}
  a {{ color: var(--accent); }}
  header {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline; justify-content: space-between;
    margin-bottom: 18px; }}
  h1 {{ font-size: 22px; margin: 0; letter-spacing: -0.2px; overflow-wrap: anywhere; }}
  header > div {{ min-width: 0; max-width: 100%; }}
  .sub {{ color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
  .panel {{ background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 16px; min-width: 0; }}
  .panel h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
    margin: 0 0 12px; font-weight: 600; }}
  .kpis {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-bottom: 16px; }}
  .kpi {{ background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 12px; padding: 12px 14px; }}
  .kpi-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .07em; }}
  .kpi-value {{ font-size: 22px; font-weight: 650; margin: 4px 0 2px; letter-spacing: -0.4px; }}
  .kpi-hint {{ color: var(--muted); font-size: 11.5px; }}
  .progress {{ display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: #0b1018;
    border: 1px solid var(--line); }}
  .seg {{ height: 100%; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 14px; margin-top: 10px; color: var(--muted); font-size: 12px; }}
  .legend-item i {{ display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 6px; }}
  .goal {{ display: grid; gap: 10px; margin-bottom: 14px; }}
  .goal div {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }}
  .goal span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: .07em; margin-bottom: 3px; }}
  .gantt {{ overflow-x: auto; max-width: 100%; }}
  .gantt-inner {{ min-width: 760px; }}
  .gantt-axis-row, .gantt-row {{ display: grid; grid-template-columns: minmax(240px, 320px) minmax(360px, 1fr);
    gap: 10px; min-width: 680px; }}
  .gantt-axis-spacer {{ min-width: 0; }}
  .gantt-axis {{ position: relative; height: 22px; min-width: 0; border-bottom: 1px solid var(--line); }}
  .tick {{ position: absolute; top: 2px; transform: translateX(-50%); font-size: 11px; color: var(--muted);
    white-space: nowrap; }}
  .tick-0 {{ transform: none; }}
  .tick-6 {{ transform: translateX(-100%); }}
  .gantt-row {{ align-items: center; border-bottom: 1px solid #1e2632; }}
  .gantt-row:hover {{ background: #18202d; }}
  .gantt-label {{ display: flex; align-items: center; gap: 8px; padding: 5px 0; min-width: 0; overflow: hidden; }}
  .gantt-text {{ min-width: 0; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
    overflow: hidden; overflow-wrap: anywhere; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex: none; }}
  .crit {{ color: #f0a742; font-size: 10px; }}
  .gantt-track {{ position: relative; height: 26px; min-width: 0; }}
  .bar {{ position: absolute; top: 6px; height: 15px; border-radius: 5px; min-width: 3px;
    box-shadow: 0 0 0 1px rgba(0,0,0,.25) inset; }}
  .wave-row {{ display: flex; justify-content: space-between; padding: 12px 0 6px; color: var(--muted);
    font-size: 12px; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid var(--line);
    margin-top: 6px; }}
  .wave-count {{ text-transform: none; letter-spacing: 0; }}
  .grid {{ display: grid; gap: 16px; grid-template-columns: minmax(0, 1.35fr) minmax(0, .65fr);
    align-items: start; }}
  .grid > * {{ min-width: 0; }}
  @media (max-width: 1000px) {{ .grid {{ grid-template-columns: minmax(0, 1fr); }} }}
  @media (max-width: 640px) {{
    body {{ padding: 14px 10px 36px; }}
    .panel {{ padding: 12px; border-radius: 11px; }}
    h1 {{ font-size: 19px; }}
    .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .kpi {{ padding: 9px 10px; }}
    .kpi-value {{ font-size: 19px; }}
    .toolbar input {{ min-width: 0; width: 100%; }}
    .task-details {{ grid-template-columns: minmax(0, 1fr); gap: 0; }}
    .task-details dd {{ margin-bottom: 8px; }}
  }}
  .blocker {{ background: var(--panel-2); border: 1px solid #3a2530; border-left: 3px solid #ef4d64;
    border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }}
  .blocker-head {{ display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }}
  .blocker-reason {{ color: #d7e0ec; }}
  .blocker-meta {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .badge {{ font-size: 11px; font-weight: 700; color: #0d1117; border-radius: 5px; padding: 1px 6px; }}
  .facts {{ margin: 0; padding-left: 18px; color: var(--muted); }}
  .facts li {{ margin-bottom: 6px; }}
  .facts b {{ color: var(--text); }}
  .live {{ list-style: none; margin: 0; padding: 0; }}
  .live li {{ display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid #1e2632; align-items: baseline; }}
  .live-text {{ flex: 1; }}
  .leaf-tag {{ color: var(--muted); font-size: 11px; border: 1px solid var(--line); border-radius: 5px;
    padding: 0 5px; min-width: 0; white-space: normal; overflow-wrap: anywhere; }}
  .table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .table th {{ text-align: left; color: var(--muted); font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .05em; padding: 6px 8px; border-bottom: 1px solid var(--line);
    background: var(--panel); }}
  .table td {{ padding: 6px 8px; border-bottom: 1px solid #1c2431; vertical-align: top; }}
  .table-leaves {{ min-width: 920px; width: 100%; table-layout: fixed; }}
  .table-scroll {{ max-width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; }}
  .table-leaves th:nth-child(1) {{ width: 42%; }}
  .table-leaves th:nth-child(2) {{ width: 120px; }}
  .table-leaves th:nth-child(3), .table-leaves th:nth-child(4) {{ width: 86px; }}
  .table-leaves th:nth-child(5) {{ width: 120px; }}
  .task-title {{ font-weight: 550; overflow-wrap: anywhere; }}
  .table-leaves .status {{ white-space: nowrap; }}
  .task-details-trigger, .task-details-close {{ color: var(--accent); background: transparent; border: 1px solid var(--line);
    border-radius: 6px; cursor: pointer; font: inherit; padding: 3px 7px; }}
  .task-details-host {{ position: static; width: 100%; margin-top: 12px; }}
  .task-details-card {{ width: 100%; min-width: 0; background: var(--panel-2); border: 1px solid var(--line);
    border-radius: 10px; padding: 12px; }}
  .task-details-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }}
  .task-details-head h3 {{ min-width: 0; margin: 0; font-size: 14px; overflow-wrap: anywhere; }}
  .task-details {{ display: grid; grid-template-columns: minmax(110px, auto) minmax(0, 1fr); gap: 3px 12px; margin: 8px 0 2px; }}
  .task-details dt {{ color: var(--muted); }}
  .task-details dd {{ margin: 0; min-width: 0; width: 100%; overflow-wrap: anywhere; word-break: break-word; }}
  details > summary {{ color: var(--accent); cursor: pointer; }}
  .technical {{ font-size: 12px; }}
  .status {{ color: var(--c); font-weight: 600; white-space: nowrap; }}
  .over {{ color: #f0a742; }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .notes {{ color: var(--muted); margin: 0; padding-left: 18px; }}
  .hint {{ color: var(--muted); font-size: 12px; margin: -6px 0 10px; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }}
  .toolbar input {{ background: #0e141d; border: 1px solid var(--line); color: var(--text); border-radius: 8px;
    padding: 6px 10px; min-width: 200px; font: inherit; }}
  .chip {{ background: #0e141d; border: 1px solid var(--line); color: var(--muted); border-radius: 999px;
    padding: 4px 11px; cursor: pointer; font: inherit; font-size: 12px; }}
  .chip.active {{ background: var(--accent); color: #0d1117; border-color: var(--accent); font-weight: 600; }}
  footer {{ color: var(--muted); font-size: 11.5px; margin-top: 22px; border-top: 1px solid var(--line);
    padding-top: 12px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>{title}</h1>
    <div class="sub">LHC · {kind} · обновлено {generated}</div>
  </div>
  <div class="sub">{total} задач в графе</div>
</header>

<div class="panel">
  {goal_block}
  <div class="progress">{segments}</div>
  <div class="legend">{legend}</div>
</div>

<div class="kpis">{cards}</div>

<div class="panel">
  <h2>Гант · листья и параллельные волны</h2>
  <div class="gantt"><div class="gantt-inner">
    <div class="gantt-axis-row"><div class="gantt-axis-spacer"></div><div class="gantt-axis">{axis}</div></div>
    {gantt}
  </div></div>
</div>

<div class="grid">
  <div class="panel">
    <h2>Листья</h2>
    {layer_hint}
    <div class="toolbar">
      <input id="search" type="search" placeholder="Поиск по листу, id или владельцу…">
      <button class="chip active" data-filter="all">все</button>
      <button class="chip" data-filter="done">готово</button>
      <button class="chip" data-filter="running">в работе</button>
      <button class="chip" data-filter="blocked">блокеры</button>
      <button class="chip" data-filter="queued">в очереди</button>
    </div>
    {leaves_table}
    {leaves_details}
  </div>
  <div>
    <div class="panel">
      <h2>Блокеры</h2>
      {blockers}
    </div>
    <div class="panel">
      <h2>Технические привязки</h2>
      <details class="technical"><summary>Владельцы, сессии, harness и модели</summary>
        {sessions}
      </details>
    </div>
    <div class="panel">
      <h2>Прогноз</h2>
      {forecast}
      {notes}
    </div>
    <div class="panel">
      <h2>Журнал волны</h2>
      {live}
    </div>
  </div>
</div>

<footer>
  LHC task graph · один файл, без внешних зависимостей · собран {generated}
  <details class="technical"><summary>Путь исходного плана</summary><code>{source}</code></details>
</footer>

<script>
(function () {{
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('.table-leaves tbody tr'));
  var input = document.getElementById('search');
  var detailsHost = document.getElementById('task-details-host');
  var activeDetailsButton = null;
  var filter = 'all';
  function apply() {{
    var query = (input && input.value || '').trim().toLowerCase();
    rows.forEach(function (row) {{
      var okFilter = filter === 'all' || row.dataset.status === filter;
      var okQuery = !query || (row.dataset.text || '').indexOf(query) !== -1;
      row.style.display = (okFilter && okQuery) ? '' : 'none';
    }});
  }}
  chips.forEach(function (chip) {{
    chip.addEventListener('click', function () {{
      chips.forEach(function (other) {{ other.classList.remove('active'); }});
      chip.classList.add('active');
      filter = chip.dataset.filter;
      apply();
    }});
  }});
  if (input) {{ input.addEventListener('input', apply); }}
  document.querySelectorAll('.task-details-trigger').forEach(function (button) {{
    button.addEventListener('click', function () {{
      if (activeDetailsButton) {{ activeDetailsButton.setAttribute('aria-expanded', 'false'); }}
      var template = document.getElementById('task-details-template-' + button.dataset.detailsId);
      if (!template || !detailsHost) {{ return; }}
      detailsHost.replaceChildren(template.content.cloneNode(true));
      detailsHost.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      activeDetailsButton = button;
      detailsHost.scrollIntoView({{ block: 'nearest' }});
      detailsHost.querySelector('.task-details-close').addEventListener('click', function () {{
        detailsHost.hidden = true;
        detailsHost.replaceChildren();
        button.setAttribute('aria-expanded', 'false');
        activeDetailsButton = null;
        button.focus();
      }});
    }});
  }});
  apply();
}})();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# text summary
# --------------------------------------------------------------------------


def render_text(graph: Graph, metrics: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Граф задач: {graph.title}")
    if graph.goal:
        lines.append(f"Цель: {graph.goal}")
    if graph.business_result:
        lines.append(f"Бизнес-результат: {graph.business_result}")
    scope = "по журналу волны" if metrics["use_live"] else "по листьям графа"
    lines.append(
        "Прогресс ({scope}): {done}/{total} готово ({pct}%) · в работе {running} · "
        "заблокировано {blocked} · осталось {left}".format(
            scope=scope,
            done=metrics["done"], total=metrics["headline_total"], pct=metrics["progress_pct"],
            running=metrics["running"], blocked=metrics["blocked"],
            left=metrics["queued"] + metrics["waiting"],
        )
    )
    lines.append(
        f"Листьев в графе: {metrics['total']} · слотов: {metrics['slots']}"
    )
    lines.append(
        "Параллельность: сейчас {current} из {slots} слотов, пик по плану {peak}".format(
            current=metrics["current_parallel"], slots=metrics["slots"],
            peak=metrics["planned_peak_parallel"],
        )
    )
    lines.append(
        "Прогноз: {work_label} {remaining} (мин. {minimum}), финиш {eta}".format(
            work_label=("известная активная часть" if metrics["unknown_estimate_pending"] or metrics["external_wait_unknown"] else "осталось"),
            remaining=fmt_minutes(metrics["remaining_minutes_max"]),
            minimum=fmt_minutes(metrics["remaining_minutes_min"]),
            eta=("неизвестен из-за внешнего ожидания" if metrics["external_wait_unknown"] else
                 f"неизвестен: {metrics['unknown_estimate_pending']} листьев без оценки"
                 if metrics["unknown_estimate_pending"] else metrics["eta_clock_max"]),
        )
    )
    if metrics["critical_path"]:
        labels = {leaf.id: leaf.label or leaf.id for leaf in graph.leaves}
        lines.append("Критический путь: " + " → ".join(labels.get(item, item) for item in metrics["critical_path"]))
    blockers = [leaf for leaf in graph.leaves if leaf.status == STATUS_BLOCKED]
    if blockers:
        lines.append("Блокеры:")
        for leaf in blockers:
            details = leaf.blocker_details
            lines.append(f"  - Почему ждём: {details.get('reason') or leaf.blocker or leaf.note or 'Причина не указана.'}")
            lines.append(f"    Кто делает: {details.get('responsible') or leaf.owner or 'Исполнитель не указан.'}")
            lines.append(f"    Следующий шаг: {details.get('next_action') or leaf.note or 'Следующий шаг не указан.'}")
            required = details.get("human_required", "unknown").lower()
            human_label = {"yes": "Да", "no": "Нет", "unknown": "Пока неизвестно"}.get(required, "Пока неизвестно")
            lines.append(f"    Нужен ли человек: {human_label}. {details.get('human_action') or 'Действие человека не уточнено.'}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------


def export_graph(graph: Graph) -> dict[str, Any]:
    metrics = build_metrics(graph)
    tasks: list[dict[str, Any]] = []
    for leaf in sorted(graph.leaves, key=lambda item: item.order):
        task: dict[str, Any] = {
            "id": leaf.id,
            "label": leaf.label,
            "status": leaf.status,
            "depends_on": leaf.depends_on,
        }
        if leaf.parallel_with:
            task["parallel_with"] = leaf.parallel_with
        if leaf.estimate_min is not None or leaf.estimate_max is not None:
            task["estimate_minutes"] = {
                "minimum": leaf.estimate_min,
                "maximum": leaf.estimate_max,
            }
        if leaf.estimate_unknown_reason:
            task["estimate_unknown_reason"] = leaf.estimate_unknown_reason
        if leaf.actual_minutes is not None:
            task["actual_minutes"] = leaf.actual_minutes
        if leaf.started_at:
            task["started_at"] = leaf.started_at
        if leaf.finished_at:
            task["finished_at"] = leaf.finished_at
        if leaf.owner:
            task["owner"] = leaf.owner
        if leaf.session:
            task["session"] = leaf.session
        if leaf.harness:
            task["harness"] = leaf.harness
        if leaf.model:
            task["model"] = leaf.model
        if leaf.blocker:
            task["blocker"] = leaf.blocker
        if leaf.acceptance:
            task["acceptance"] = leaf.acceptance
        if leaf.blocker_details:
            task["blocker_details"] = leaf.blocker_details
        if leaf.note:
            task["note"] = leaf.note
        if leaf.wave is not None:
            task["wave"] = leaf.wave
        tasks.append(task)
    document = {
        "schema_version": 2,
        "title": graph.title,
        "goal": graph.goal,
        "business_result": graph.business_result,
        "current_progress": graph.current_progress,
        "external_waits": graph.external_waits,
        "slots": graph.slots,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": tasks,
    }
    if metrics["total"]:
        document["leaf_count"] = metrics["total"]
    return document


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lhc_grid.py",
        description="Render an LHC task graph as one self-contained HTML dashboard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Build the HTML dashboard")
    render.add_argument("input", type=Path, help="plan record, plan report or graph JSON")
    render.add_argument("-o", "--output", type=Path, help="output HTML path")
    render.add_argument("--open", action="store_true", help="open the result in a browser")
    render.add_argument("--title", help="override the dashboard title")

    status = sub.add_parser("status", help="Print a compact text summary")
    status.add_argument("input", type=Path)

    export = sub.add_parser("export", help="Convert a plan into the standard graph JSON")
    export.add_argument("input", type=Path)
    export.add_argument("-o", "--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="Check the graph structure")
    validate.add_argument("input", type=Path)
    return parser


def command_render(args: argparse.Namespace) -> int:
    graph = discover_graph(args.input)
    if args.title:
        graph.title = args.title
    metrics = build_metrics(graph)
    html = render_html(graph, metrics)
    output = args.output
    if output is None:
        stem = Path(graph.source_path).stem if graph.source_path else "lhc-grid"
        output = Path.cwd() / f"{stem}.grid.html"
    output.write_text(html, encoding="utf-8")
    print(f"{output}")
    if args.open:
        try:
            webbrowser.open(output.resolve().as_uri())
        except Exception:  # pragma: no cover - headless hosts have no browser
            print("browser not available", file=sys.stderr)
    return 0


def command_status(args: argparse.Namespace) -> int:
    graph = discover_graph(args.input)
    metrics = build_metrics(graph)
    print(render_text(graph, metrics))
    return 0


def command_export(args: argparse.Namespace) -> int:
    graph = discover_graph(args.input)
    document = export_graph(graph)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{args.output}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    graph = discover_graph(args.input)
    graph.resolve_dependencies()
    errors: list[str] = []
    if not graph.leaves:
        errors.append("graph has no leaves")
    ids = [leaf.id for leaf in graph.leaves]
    if len(ids) != len(set(ids)):
        errors.append("duplicate leaf ids")
    known = set(ids)
    for leaf in graph.leaves:
        for dep in leaf.depends_on:
            if dep not in known:
                errors.append(f"{leaf.id}: unknown dependency {dep}")
        if leaf.status not in STATUSES:
            errors.append(f"{leaf.id}: unknown status {leaf.status}")
    payload = {
        "valid": not errors,
        "errors": errors,
        "leaves": len(graph.leaves),
        "slots": graph.slots,
        "source": graph.source_path,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "render": command_render,
        "status": command_status,
        "export": command_export,
        "validate": command_validate,
    }
    try:
        return handlers[args.command](args)
    except (OSError, ValueError) as error:
        print(f"lhc_grid: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
