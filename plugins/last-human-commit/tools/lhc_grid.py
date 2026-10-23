#!/usr/bin/env python3
"""Render an LHC task graph as one self-contained HTML dashboard.

The dashboard answers, in one screen: what is done, what runs now, what is
blocked, roughly when the work finishes and how much of it runs in parallel.

Inputs
------
* a task graph JSON (``schema_version`` 1 or 2);
* a canonical LHC plan report (``src/common/protocols/PLAN_REPORT.md``);
* any task record that carries a ``## Plan`` block;
* a free-form business-first replan with a decomposition table and wave log.

One command, one artifact::

    python3 lhc_grid.py render PLAN [-o plan.html] [--open]

The report and the graph are one unit, and the tool says so out loud::

    python3 lhc_grid.py check-plan PLAN_REPORT.md PLAN_GRAPH.json

The renderer is offline and dependency-free: the output is a single HTML file
with inline CSS/JS, safe to attach to a message or open from a phone.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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

STATUS_GLYPHS = {
    STATUS_DONE: "✅",
    STATUS_RUNNING: "🔄",
    STATUS_BLOCKED: "⛔",
    STATUS_WAITING: "⌛",
    STATUS_DEFERRED: "⏸",
    STATUS_QUEUED: "⋯",
}

STATUS_COLORS = {
    STATUS_DONE: "#2ecc71",
    STATUS_RUNNING: "#4f9cf9",
    STATUS_BLOCKED: "#f25f74",
    STATUS_WAITING: "#f0a742",
    STATUS_DEFERRED: "#b08ce8",
    STATUS_QUEUED: "#7c8aa3",
}

# One table of the report markers: the glyph of every state and the state it
# stands for. The plan report, the live log and the dashboard read the same
# table, so they cannot disagree about what a marker means.
GLYPH_STATUS = {
    "✅": STATUS_DONE,
    "🔄": STATUS_RUNNING,
    "⌛": STATUS_WAITING,
    "⏸": STATUS_DEFERRED,
    "⏳": STATUS_QUEUED,
    "⛔": STATUS_BLOCKED,
}

# The status colors carry meaning only: done, in work, blocked, waiting,
# deferred by the owner, in queue. They are referenced through CSS variables so
# one theme can change them without touching a single markup line.
STATUS_CSS_VARS = {
    STATUS_DONE: "var(--st-done)",
    STATUS_RUNNING: "var(--st-running)",
    STATUS_BLOCKED: "var(--st-blocked)",
    STATUS_WAITING: "var(--st-waiting)",
    STATUS_DEFERRED: "var(--st-deferred)",
    STATUS_QUEUED: "var(--st-queued)",
}

# One palette, two themes. Every surface, text and status color of a theme is
# defined here once, so the light and the dark theme cannot drift apart and a
# contrast test can check both of them.
THEME_PALETTE = {
    "dark": {
        "bg": "#0d1117",
        "panel": "#151b26",
        "panel-2": "#1b2331",
        "line": "#26303f",
        "text": "#e6edf6",
        "muted": "#9fb0c6",
        "accent": "#6ea8fe",
        "ok": "#2ecc71",
        "warn": "#f0a742",
        "bad": "#f25f74",
        "st-done": "#2ecc71",
        "st-running": "#4f9cf9",
        "st-blocked": "#f25f74",
        "st-waiting": "#f0a742",
        "st-deferred": "#b08ce8",
        "st-queued": "#8fa0b8",
    },
    "light": {
        "bg": "#f4f6f9",
        "panel": "#ffffff",
        "panel-2": "#eaeef4",
        "line": "#d3dae3",
        "text": "#15202c",
        "muted": "#58677a",
        "accent": "#1a62cc",
        "ok": "#1a7f37",
        "warn": "#8a6100",
        "bad": "#c02b38",
        "st-done": "#1a7f37",
        "st-running": "#1a62cc",
        "st-blocked": "#c02b38",
        "st-waiting": "#8a6100",
        "st-deferred": "#6b4fa8",
        "st-queued": "#5a6b7f",
    },
}


def palette_css() -> str:
    """The CSS custom properties of both themes."""

    def block(selector: str, values: dict[str, str]) -> str:
        body = " ".join(f"--{key}: {value};" for key, value in values.items())
        return f"{selector} {{ {body} }}"

    return "\n  ".join(
        [
            block(":root, :root[data-theme=\"dark\"]", THEME_PALETTE["dark"]),
            block(":root[data-theme=\"light\"]", THEME_PALETTE["light"]),
        ]
    )

WAVE_LABELS = {}

# The report markers this tool knows. An input that carries none of them is an
# error, never an empty dashboard.
PLAN_REPORT_HINT = (
    'отчёт не распознан: нет строки "Цель:" или "Декомпозиция:" и нет ни одного листа '
    '(ожидаются строки "✅", "🔄", "⛔", "⌛", "⏸" или "⏳")'
)


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------


@dataclass
class Leaf:
    """One decomposed leaf of the task graph."""

    id: str
    label: str = ""
    description: str = ""
    acceptance: str = ""
    affected_files: list[str] = field(default_factory=list)
    status: str = STATUS_QUEUED
    owner: str = ""
    session: str = ""
    harness: str = ""
    model: str = ""
    model_class: str = ""
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
    def actual_span_minutes(self) -> Optional[float]:
        """Calendar length of the work window.

        ``actual_minutes`` is the summed effort of the executors. It can be
        larger than the wall-clock window when several executors worked in the
        same time, and the two numbers answer different questions, so the
        dashboard shows both instead of one silently meaning the other.
        """
        start = parse_clock(self.started_at)
        finish = parse_clock(self.finished_at)
        if start is None or finish is None:
            return None
        return float((finish - start) % (24 * 60))

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

    @property
    def plan_minutes(self) -> Optional[float]:
        """The planned duration of the task.

        The plan is the upper bound of the estimate: that is the time the
        owner counted on. A leaf with one bound only is planned for that
        bound, and a leaf without an estimate has no plan at all - the page
        says so instead of inventing a number.
        """
        return self.estimate

    @property
    def overrun_minutes(self) -> Optional[float]:
        """The wall-clock time spent beyond the plan.

        Only a measured work window can overrun. Without a start and a
        finish there is no real duration to compare with the plan, so the
        number stays absent instead of going stale, and the page shows the
        absence rather than a number nobody measured.
        """
        span = self.actual_span_minutes
        plan = self.plan_minutes
        if span is None or plan is None:
            return None
        extra = span - plan
        return extra if extra > 0.01 else None


DEFAULT_GRAPH_TITLE = "LHC · граф задач"
# The attribution a plan report has no place for. The export writes it when the
# source graph knows it, and a refresh keeps it from the earlier graph.
ATTRIBUTION_FIELDS = (
    "owner",
    "session",
    "harness",
    "model",
    "model_class",
    "role",
    "acceptance",
    "description",
    "affected_files",
    "note",
    "blocker",
    "blocker_details",
    "estimate_unknown_reason",
    "read_paths",
    "write_paths",
    "paths",
)


@dataclass
class Graph:
    """A whole task graph plus its live state."""

    title: str = "LHC · граф задач"
    goal: str = ""
    business_result: str = ""
    # A task may carry several business results. Each one is a capability the
    # user can touch by hand and check on its own; they are not merged into one
    # and they are not the commits and the internal stages.
    business_results: list[str] = field(default_factory=list)
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
    journal: list[dict[str, Any]] = field(default_factory=list)
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
# The markers of the states come from one table, so the report, the live log
# and the dashboard cannot drift apart. The optional variation selector lets a
# report carry "⏸️" as well as "⏸".
LEAF_LINE_RE = re.compile(rf"^\s*([{''.join(GLYPH_STATUS)}])\ufe0f?\s*(.*)$")
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


JOURNAL_SECTION_RE = re.compile(r"^##\s*(журнал изменений|change log)\s*$", re.IGNORECASE)
JOURNAL_ENTRY_RE = re.compile(r"^\s*[-*]\s*(\d{1,2}:\d{2})\s*·\s*(.+?)\s*$")
JOURNAL_LEAF_RE = re.compile(r"^[A-Za-zА-Яа-я]?\d{1,3}[A-Za-zА-Яа-я]?$")


def _parse_journal_entry(line: str) -> Optional[dict[str, Any]]:
    """One line of the change log of a plan report.

    The line reads as time, then the leaf it belongs to, then the action, the
    result and the confirmation. The labels keep the line readable for a
    person and unambiguous for the parser.
    """

    match = JOURNAL_ENTRY_RE.match(line)
    if not match:
        return None
    entry: dict[str, Any] = {"at": match.group(1)}
    action: list[str] = []
    for part in (piece.strip() for piece in match.group(2).split("·")):
        if not part:
            continue
        lowered = part.lower()
        if part.startswith("результат:"):
            entry["result"] = part.split(":", 1)[1].strip()
        elif part.startswith("подтверждение:"):
            entry["evidence"] = part.split(":", 1)[1].strip()
        elif JOURNAL_LEAF_RE.match(part) and "leaf" not in entry:
            entry["leaf"] = part
        else:
            action.append(part)
    if action:
        entry["action"] = " ".join(action).strip()
    # An entry may carry only a result. It still belongs to the history.
    return entry if entry.get("action") or entry.get("result") else None


def parse_plan_report(text: str) -> Optional[Graph]:
    """Parse the canonical live plan report format."""
    graph = Graph(source_kind="plan-report")
    leaves: list[Leaf] = []
    pending_parallel: list[tuple[int, int]] = []
    pending_after: list[tuple[int, int]] = []
    journal_entries: list[dict[str, Any]] = []
    in_journal = False
    seen_leaf = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("# ") and graph.title == DEFAULT_GRAPH_TITLE:
            # The name of the plan is its first line.
            graph.title = stripped[2:].strip()
            continue
        if stripped.startswith("##"):
            # The change log of the report is a section of its own. Without it
            # the dashboard would fall back to the leaf names, which is a
            # second list of the table and not a history.
            in_journal = bool(JOURNAL_SECTION_RE.match(stripped))
            continue
        if in_journal:
            entry = _parse_journal_entry(line)
            if entry:
                journal_entries.append(entry)
            continue
        header = HEADER_RE.match(line)
        if header and not seen_leaf:
            key, value = header.group(1), header.group(2)
            if key == "Цель":
                graph.goal = value.strip()
            elif key == "Бизнес-результат":
                # Several results are allowed in one task: the line may be
                # repeated, and every repeat is a result of its own.
                result = value.strip()
                if result:
                    graph.business_results.append(result)
                    if not graph.business_result:
                        graph.business_result = result
            else:
                graph.declared_leaves = _int_or_none(DECOMP_LEAVES_RE.search(value))
                graph.declared_parallel = _int_or_none(DECOMP_PARALLEL_RE.search(value))
                graph.declared_waves = _int_or_none(DECOMP_WAVES_RE.search(value))
                graph.slots = graph.declared_parallel or _int_or_none(DECOMP_SLOTS_RE.search(value)) or 1
            continue
        detail = re.match(r"^\s+(Описание задачи|Приёмка|Затрагиваемые файлы):\s*(.*)$", line)
        if detail and leaves:
            key, value = detail.groups()
            if key == "Описание задачи":
                leaves[-1].description = normalize(value)
            elif key == "Приёмка":
                leaves[-1].acceptance = normalize(value)
            else:
                quoted_paths = re.findall(r"`([^`]+)`", value)
                leaves[-1].affected_files = quoted_paths or [item.strip() for item in value.split(",") if item.strip()]
            continue
        match = LEAF_LINE_RE.match(line)
        if not match:
            continue
        glyph, rest = match.group(1), match.group(2).strip()
        if not rest:
            continue
        seen_leaf = True
        index = len(leaves)
        status = GLYPH_STATUS.get(glyph, STATUS_QUEUED)
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
    if journal_entries:
        graph.journal = journal_entries
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
LIVE_ITEM_RE = re.compile(rf"^\s*[-*]\s*([{''.join(GLYPH_STATUS)}])\ufe0f?\s*(.+?)\s*$")
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
            status = GLYPH_STATUS.get(glyph, STATUS_QUEUED)
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
    declared_results = document.get("business_results")
    if isinstance(declared_results, list):
        graph.business_results = [str(item).strip() for item in declared_results if str(item).strip()]
    elif graph.business_result:
        graph.business_results = [graph.business_result]
    graph.current_progress = str(document.get("current_progress") or "")
    graph.external_waits = str(document.get("external_waits") or "")
    graph.updated_at = str(document.get("updated_at") or "")
    graph.slots = int(document.get("slots") or 1)
    graph.declared_parallel = document.get("parallel")
    graph.declared_leaves = document.get("leaf_count")
    graph.declared_waves = document.get("wave_count")

    # Optional change log: time, action, result, confirmation.
    raw_journal = document.get("journal")
    if isinstance(raw_journal, list):
        graph.journal = [entry for entry in raw_journal if isinstance(entry, dict)]

    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a nonempty list")
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index}] must be an object")
        raw_blocker_details = task.get("blocker_details")
        if not isinstance(raw_blocker_details, dict):
            raw_blocker_details = {}
        raw_affected_files = task.get("affected_files")
        if raw_affected_files is not None and (
            not isinstance(raw_affected_files, list)
            or not all(isinstance(item, str) for item in raw_affected_files)
        ):
            raise ValueError(f"tasks[{index}].affected_files must be a list of strings")
        leaf = Leaf(
            id=str(task.get("id") or f"task-{index + 1}"),
            label=normalize(str(task.get("label") or task.get("outcome") or task.get("acceptance") or "")),
            description=normalize(str(task.get("description") or "")),
            acceptance=normalize(str(task.get("acceptance") or "")),
            affected_files=list(raw_affected_files or []),
            status=normalize_status(task.get("status") or STATUS_QUEUED),
            owner=str(task.get("owner") or task.get("role") or ""),
            session=str(task.get("session") or ""),
            harness=str(task.get("harness") or ""),
            model=str(task.get("model") or ""),
            model_class=str(task.get("model_class") or ""),
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
        "deferred": STATUS_DEFERRED, "defer": STATUS_DEFERRED, "отложено": STATUS_DEFERRED,
        "отложен": STATUS_DEFERRED, "отложено_владельцем": STATUS_DEFERRED,
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
            raise ValueError(PLAN_REPORT_HINT)
    graph.source_path = str(path)
    if not graph.title:
        graph.title = path.stem
    graph.resolve_dependencies()
    return graph


def require_leaves(graph: Graph) -> Graph:
    """Refuse to work on an empty graph: an unread report is an error."""
    if not graph.leaves:
        raise ValueError(PLAN_REPORT_HINT)
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
        raise ValueError(f"{PLAN_REPORT_HINT} ({path})")
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
    # A leaf the owner deferred is not part of the delivery any more: it takes
    # no slot, no time and no place on the critical path.
    leaves = {
        leaf.id: leaf for leaf in graph.leaves
        if leaf.status != STATUS_DEFERRED
    }
    durations: dict[str, float] = {}
    for leaf in leaves.values():
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
    # A leaf the owner deferred is not owed any more: it is not part of the
    # remainder of the delivery.
    deferred = headline.get(STATUS_DEFERRED, 0)

    schedule_max = schedule_graph(graph, use_max=True)
    schedule_min = schedule_graph(graph, use_max=False)
    pending_max = schedule_graph(graph, use_max=True, only_pending=True)
    pending_min = schedule_graph(graph, use_max=False, only_pending=True)

    # A missing estimate is not a zero estimate. The leaves whose duration is
    # unknown are named here, so every number derived from the schedule can
    # say "unknown" instead of quietly turning the missing time into zero.
    unknown_estimate_all = [
        leaf for leaf in graph.leaves
        if leaf.status != STATUS_DEFERRED
        and leaf.estimate_min is None and leaf.estimate_max is None
    ]
    unknown_estimate_pending = [
        leaf for leaf in unknown_estimate_all if leaf.status != STATUS_DONE
    ]
    unknown_ids_all = {leaf.id for leaf in unknown_estimate_all}
    known_duration_count = sum(
        1 for leaf in graph.leaves
        if leaf.status != STATUS_DEFERRED and leaf.id not in unknown_ids_all
    )
    # The effort, the critical path and the planned peak are whole-plan
    # numbers: one unknown leaf is enough to make all three unknown.
    duration_known = not unknown_estimate_all

    effort = sum(leaf.estimate or 0.0 for leaf in graph.leaves)
    critical = schedule_max.critical_path
    critical_minutes = sum(
        (leaf.estimate or 0.0) for leaf in graph.leaves if leaf.id in critical
    )

    current_peak = running
    slot_limit = graph.slots or 1
    blocked_leaves = [leaf for leaf in graph.leaves if leaf.status == STATUS_BLOCKED]
    blocked_minutes = sum((leaf.estimate or 0.0) for leaf in blocked_leaves)
    blocked_unknown_ids = {
        leaf.id for leaf in blocked_leaves
        if leaf.estimate_min is None and leaf.estimate_max is None
    }
    blocked_known_minutes = sum(
        (leaf.estimate or 0.0) for leaf in blocked_leaves
        if leaf.id not in blocked_unknown_ids
    )

    now = now_clock()
    eta_min = pending_min.makespan
    eta_max = pending_max.makespan
    # The forecast counts from the last confirmed event, not from the moment
    # the page is opened. An idle plan must not push its own finish further
    # away with every minute of silence, so the anchor is the event itself and
    # the idle time is shown instead of being hidden inside the horizon.
    anchor = _plan_anchor(graph)
    eta_from = now if anchor is None else anchor
    idle_minutes = max(0, now - anchor) if anchor is not None else 0
    # A closed leaf with an unknown duration, and a report that still mentions a
    # wait, must not freeze the horizon forever: only a wait that is still
    # waiting makes the finish unknown.
    waiting_now = [
        leaf for leaf in graph.leaves
        if leaf.status in (STATUS_WAITING, STATUS_BLOCKED)
    ]
    # The report may still declare a wait that has been closed since; the
    # declaration is a note, the live wait is what withholds the clock.
    external_wait_declared = bool(graph.external_waits.strip())
    external_wait_unknown = bool(waiting_now)
    # The horizon is computable from the leaves that do have a duration. When
    # some pending leaf has none, the bound is still shown - it is the known
    # part - and marked as imprecise instead of being hidden behind "unknown".
    pending_with_duration = [
        leaf for leaf in graph.leaves
        if leaf.status not in (STATUS_DONE, STATUS_DEFERRED)
        and (leaf.estimate_min is not None or leaf.estimate_max is not None)
    ]
    eta_bounds_available = bool(pending_with_duration) or bool(waiting_now)
    # A leaf that still waits for an external answer withholds the clock: the
    # time of the answer is unknown, so the finish time is unknown whatever the
    # durations are. A leaf that only has no duration does not: its known part
    # is computed and shown, and the imprecision is named.
    # A leaf that really waits (blocked or waiting) withholds the clock: the
    # time of the answer is unknown, so the finish time is unknown whatever the
    # durations are. A declared wait that no open leaf carries any more is a
    # note on an otherwise known horizon, not a reason to hide the number.
    eta_clock_available = eta_bounds_available and not external_wait_unknown
    eta_known = eta_clock_available and not unknown_estimate_pending
    # What makes the bound imprecise, in the words of the owner: a task whose
    # duration is unknown is still open.
    eta_imprecise_reasons = []
    if unknown_estimate_pending:
        eta_imprecise_reasons.append(
            metrics_unknown_phrase(len(unknown_estimate_pending))
        )
    if external_wait_unknown:
        eta_imprecise_reasons.append("срок внешнего ожидания не подтверждён")
    unfinished = max(0, headline_total - done - deferred)

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
        "deferred": deferred,
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
        "unknown_estimate_leaf_ids": [leaf.id for leaf in unknown_estimate_all],
        # The honest state of every number the schedule produces.
        "duration_known": duration_known,
        "known_duration_count": known_duration_count,
        "effort_known": duration_known,
        "critical_known": duration_known,
        "remaining_known": not unknown_estimate_pending,
        "blocked_unknown_count": len(blocked_unknown_ids),
        "blocked_known_minutes": blocked_known_minutes,
        "external_wait_unknown": external_wait_unknown,
        "external_wait_declared": external_wait_declared,
        "eta_clock_min": "" if not eta_clock_available else format_clock((eta_from + int(round(eta_min))) % (24 * 60)),
        "eta_clock_max": "" if not eta_clock_available else format_clock((eta_from + int(round(eta_max))) % (24 * 60)),
        "eta_bounds_available": eta_clock_available,
        "eta_exact": eta_known,
        "eta_imprecise_reasons": eta_imprecise_reasons,
        "eta_anchor_clock": "" if anchor is None else format_clock(anchor % (24 * 60)),
        "eta_anchor_idle_minutes": idle_minutes,
        "eta_overdue": bool(
            unfinished > 0 and eta_known and eta_from + int(round(eta_max)) < now
        ),
        "unfinished": unfinished,
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
# what to do now: the parallel planner's own answer
# --------------------------------------------------------------------------


def _load_sibling(name: str) -> Optional[Any]:
    """Load a sibling tool module by path, if it sits next to this file.

    The renderer stays one self-contained file, so a sibling is never
    imported by package name: it is loaded by path, and a missing or broken
    sibling is not an error — the caller falls back to its own port.
    """

    path = Path(__file__).resolve().parent / f"{name}.py"
    if not path.exists():
        return None
    module_name = f"lhc_{name}_sibling"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        sys.modules.pop(module_name, None)
        return None


def _parallel_graph(module: Any, graph: Graph) -> Any:
    """Build the parallel planner's own graph out of this grid's leaves."""

    tasks = [
        module.Task(
            id=leaf.id,
            label=leaf.label,
            status=leaf.status,
            depends_on=list(leaf.depends_on),
            parallel_with=list(leaf.parallel_with),
            estimate_min=leaf.estimate_min,
            estimate_max=leaf.estimate_max,
            actual_minutes=leaf.actual_minutes,
            blocker=leaf.blocker,
            blocker_details=dict(leaf.blocker_details),
            note=leaf.note,
            owner=leaf.owner,
            session=leaf.session,
            started_at=leaf.started_at,
            finished_at=leaf.finished_at,
            wave=leaf.wave,
            order=leaf.order,
        )
        for leaf in graph.leaves
    ]
    return module.Graph(
        title=graph.title,
        goal=graph.goal,
        business_result=graph.business_result,
        slots=graph.slots or None,
        updated_at=graph.updated_at,
        tasks=tasks,
    )


def _plan_from_summary(summary: Any, source: str) -> dict[str, Any]:
    """Turn the planner's summary into the flat shape the dashboard draws."""

    labels = {task.id: (task.label or task.id) for task in summary.graph.tasks}

    def line(task: Any, **extra: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": task.id,
            "label": task.label or task.id,
            "estimate": task.estimate_label,
            "unblocks": [labels.get(other, other) for other in summary.unblocks(task)],
        }
        data.update(extra)
        return data

    return {
        "source": source,
        "slots": summary.slots,
        "free_slots": summary.free_slots,
        "running": [line(task, since=task.started_at) for task in summary.running],
        "ready": [line(task) for task in summary.ready],
        "deferred": [line(task) for task in summary.deferred],
        "blocked": [line(task, reason=reason) for task, reason in summary.blocked],
        "waiting": [
            line(task, unmet=[labels.get(item, item) for item in unmet], unmet_ids=list(unmet))
            for task, unmet in summary.waiting
        ],
    }


def _port_estimate(leaf: Leaf) -> str:
    """The estimate as the parallel planner words it."""

    low, high = leaf.estimate_min, leaf.estimate_max
    if low is None and high is None:
        return "оценка не указана"
    if low is None:
        low = high
    if high is None:
        high = low
    if low == high:
        return f"оценка {fmt_minutes(low)}"
    return f"оценка {fmt_minutes(low)}–{fmt_minutes(high)}"


def _port_reason(leaf: Leaf) -> str:
    """Why a leaf is blocked, in the planner's own words."""

    if leaf.blocker:
        return leaf.blocker
    detail = (leaf.blocker_details or {}).get("reason")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    if leaf.note:
        return leaf.note
    return "причина не указана"


def _port_layers(tasks: dict[str, Leaf], order: list[str]) -> dict[str, int]:
    """Derive the wave of every leaf from its dependencies."""

    layers: dict[str, int] = {}

    def layer_of(task_id: str, seen: frozenset[str]) -> int:
        if task_id in layers:
            return layers[task_id]
        leaf = tasks.get(task_id)
        if leaf is None or task_id in seen:
            return 0
        best = 0
        for dep in leaf.depends_on:
            if dep in tasks:
                best = max(best, layer_of(dep, seen | {task_id}) + 1)
        layers[task_id] = best
        return best

    for task_id in order:
        layer_of(task_id, frozenset())
    return layers


def _plan_now_port(graph: Graph) -> dict[str, Any]:
    """The planner's answer, ported for a checkout without ``lhc_parallel``.

    The rules are the planner's own: a queued line whose dependencies are all
    done and that still fits into a free slot is ready to launch. This is a
    port of ``lhc_parallel.analyze()``, not a second opinion about it.
    """

    tasks = {leaf.id: leaf for leaf in graph.leaves}
    order = [leaf.id for leaf in graph.leaves]
    layers = _port_layers(tasks, order)

    running: list[Leaf] = []
    blocked: list[tuple[Leaf, str]] = []
    waiting: list[tuple[Leaf, list[str]]] = []
    ready: list[Leaf] = []

    for leaf in graph.leaves:
        if leaf.status == STATUS_RUNNING:
            running.append(leaf)
        elif leaf.status == STATUS_BLOCKED:
            blocked.append((leaf, _port_reason(leaf)))
        elif leaf.status == STATUS_WAITING:
            waiting.append((leaf, []))
        elif leaf.status == STATUS_DEFERRED:
            # The owner deferred this leaf: no answer is expected, so it waits
            # for nothing and it takes no slot.
            continue
        elif leaf.status not in STATUSES:
            continue

    for leaf in graph.leaves:
        if leaf.status != STATUS_QUEUED:
            continue
        unmet = [
            dep for dep in leaf.depends_on
            if dep not in tasks or tasks[dep].status != STATUS_DONE
        ]
        if unmet:
            waiting.append((leaf, unmet))
        else:
            ready.append(leaf)

    def sort_key(leaf: Leaf) -> tuple[int, int]:
        wave = leaf.wave if leaf.wave is not None else layers.get(leaf.id, 0)
        return (wave, leaf.order)

    ready.sort(key=sort_key)
    waiting.sort(key=lambda item: sort_key(item[0]))
    blocked.sort(key=lambda item: sort_key(item[0]))

    slots = graph.slots or None
    free = None if slots is None else max(0, slots - len(running))
    deferred: list[Leaf] = []
    if free is not None:
        deferred = ready[free:]
        ready = ready[:free]

    labels = {leaf.id: (leaf.label or leaf.id) for leaf in graph.leaves}

    def line(leaf: Leaf, **extra: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": leaf.id,
            "label": leaf.label or leaf.id,
            "estimate": _port_estimate(leaf),
            "unblocks": [
                labels.get(other.id, other.id)
                for other in graph.leaves if leaf.id in other.depends_on
            ],
        }
        data.update(extra)
        return data

    return {
        "source": "порядок lhc_parallel (перенос)",
        "slots": slots,
        "free_slots": free,
        "running": [line(leaf, since=leaf.started_at) for leaf in running],
        "ready": [line(leaf) for leaf in ready],
        "deferred": [line(leaf) for leaf in deferred],
        "blocked": [line(leaf, reason=reason) for leaf, reason in blocked],
        "waiting": [
            line(leaf, unmet=[labels.get(item, item) for item in unmet], unmet_ids=list(unmet))
            for leaf, unmet in waiting
        ],
    }


def plan_now(graph: Graph) -> dict[str, Any]:
    """What can start right now, according to the parallel planner.

    The planner's own module answers when it is next to this file; otherwise
    the same rules are applied by the port above. Either way the dashboard
    never invents a launch decision.
    """

    module = _load_sibling("lhc_parallel")
    if module is not None:
        try:
            summary = module.analyze(_parallel_graph(module, graph))
            return _plan_from_summary(summary, "lhc_parallel")
        except Exception:
            # A sibling that is missing or half-written must not take the
            # dashboard down: the port below answers with the same rules.
            pass
    return _plan_now_port(graph)


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


def _search_text(leaf: Leaf) -> str:
    """Everything a row can be found by.

    The search box promises what it searches, so every promised field has to
    be in the searchable text. A promise the data cannot satisfy is a dead
    end the reader cannot see.
    """
    parts = [
        leaf.id,
        leaf.label,
        leaf.owner,
        leaf.session,
        leaf.harness,
        leaf.model,
        leaf.note,
        leaf.blocker,
        leaf.acceptance,
        leaf.description,
        " ".join(leaf.affected_files),
    ]
    return " ".join(part for part in parts if part).lower()


def graph_revision(graph: Graph) -> str:
    """A short, stable fingerprint of the plan content.

    The dashboard and the Markdown summary are generated from one graph, so
    both carry the same revision. Two artifacts with different revisions are
    two versions of the same plan, which is exactly what a single canonical
    source has to prevent.
    """
    payload = [
        [
            leaf.id,
            leaf.label,
            leaf.description,
            leaf.acceptance,
            leaf.affected_files,
            leaf.status,
            leaf.owner,
            leaf.session,
            leaf.estimate_min,
            leaf.estimate_max,
            leaf.actual_minutes,
            leaf.started_at,
            leaf.finished_at,
        ]
        for leaf in sorted(graph.leaves, key=lambda item: item.id)
    ]
    document = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(document.encode("utf-8")).hexdigest()[:12]


SNAPSHOT_NOTE = (
    "Это снимок плана, а не панель управления: фактическое состояние работы "
    "приходит из API владельцев, а не из пересказа агента в графе."
)


def _eta_range_text(metrics: dict[str, Any]) -> str:
    """The finish horizon as a range, when the two bounds differ."""

    early = metrics.get("eta_clock_min") or ""
    late = metrics.get("eta_clock_max") or ""
    if not early or not late:
        return ""
    return early if early == late else f"{early}–{late}"


def _short(text: str, limit: int) -> str:
    """Shorten a long name for a dense list, keeping it readable."""

    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def product_module():
    """The delivery side of the plan, loaded from next to this file.

    The dashboard is loaded by path in the tests and by the CLI in the package,
    so the neighbour cannot be found by a plain import.
    """
    try:
        import lhc_product

        return lhc_product
    except ModuleNotFoundError:
        path = Path(__file__).resolve().with_name("lhc_product.py")
        spec = importlib.util.spec_from_file_location("lhc_product_sibling", path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def live_module():
    """The sibling module that keeps the built page in sync with its file.

    The dashboard is loaded by path in the tests and by the CLI in the package,
    so the neighbour cannot be found by a plain import.
    """
    try:
        import lhc_live

        return lhc_live
    except ModuleNotFoundError:
        path = Path(__file__).resolve().with_name("lhc_live.py")
        spec = importlib.util.spec_from_file_location("lhc_live_sibling", path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def merged_navigation(product_items: tuple) -> str:
    """One navigation for the whole page: the delivery sections and the plan."""
    # The navigation follows the order of the page: the state of the work is
    # above the delivery sections, the leaves and the rest are below them.
    state_items = (("lhc-state", "Состояние"),)
    plan_items = (
        ("lhc-leaves", "Листья"),
        ("lhc-plan-gantt", "Гант плана"),
        ("lhc-blocking", "Что блокирует"),
        ("lhc-forecast", "Прогноз"),
        ("lhc-journal", "Журнал"),
    )
    links = "".join(
        f'<a class="lhc-nav-link" href="#{escape(anchor)}">{escape(label)}</a>'
        for anchor, label in state_items + tuple(product_items) + plan_items
    )
    return f'<nav class="lhc-nav" aria-label="Разделы">{links}</nav>'


def metrics_unknown_phrase(count: int) -> str:
    """How many leaves have no duration, in the words of the owner."""
    if count == 1:
        return "1 лист без оценки"
    if count < 5:
        return f"{count} листа без оценки"
    return f"{count} листьев без оценки"


def render_html(
    graph: Graph,
    metrics: dict[str, Any],
    product: Optional[dict[str, Any]] = None,
) -> str:
    schedule: Schedule = metrics["schedule"]
    leaves = sorted(graph.leaves, key=lambda leaf: (schedule.waves.get(leaf.id, 0), leaf.order))
    label_by_id = {leaf.id: leaf.label or leaf.id for leaf in graph.leaves}
    total = metrics["total"]

    # ----- KPI tiles ------------------------------------------------------
    # The number is the headline; the label and the hint are secondary.
    headline_total = metrics["headline_total"]
    progress_note = "по журналу волны" if metrics["use_live"] else "листьев"
    # The owner asked for this: a task with an unknown duration must not make
    # the whole remainder "unknown". The known part is stated, and the
    # imprecision is named next to it.
    known_remainder = metrics["remaining_minutes_max"] > 0
    # The label names what the time means: a plan with a leaf of unknown
    # duration shows its known part, a plan with known durations shows the
    # remainder. A wait makes the horizon imprecise, not the duration.
    partly_unknown = bool(metrics["unknown_estimate_pending"])
    remaining_label = "Известная часть работы" if partly_unknown else "Осталось по плану"
    remaining_value = (
        f"от {fmt_minutes(metrics['remaining_minutes_min'])} "
        f"до {fmt_minutes(metrics['remaining_minutes_max'])}"
    )
    remaining_hint = remaining_value
    uncertainties = []
    if metrics["unknown_estimate_pending"]:
        uncertainties.append(
            f"Листьев без оценки — {metrics['unknown_estimate_pending']}"
        )
    if metrics["external_wait_unknown"] or metrics["external_wait_declared"]:
        uncertainties.append("срок внешнего ожидания не подтверждён")
    if uncertainties:
        remaining_hint = f"{remaining_value} · неточно: " + "; ".join(uncertainties)
        if not known_remainder:
            remaining_hint = "неизвестно · " + "; ".join(uncertainties)
    if metrics["external_wait_unknown"]:
        eta_hint = "Есть внешние ожидания без подтверждённого срока"
    elif metrics["unknown_estimate_pending"]:
        eta_hint = (
            f"неточно: {metrics['unknown_estimate_pending']} листьев без оценки"
        )
    elif metrics["eta_anchor_clock"]:
        eta_hint = (
            f"отсчёт от последнего события {metrics['eta_anchor_clock']} · "
            f"простой {fmt_minutes(metrics['eta_anchor_idle_minutes'])}"
        )
    else:
        eta_hint = "остаток стартует сейчас"
    if metrics["eta_overdue"]:
        eta_hint = f"срок прошёл, остаток не начался · {eta_hint}"
    eta_range = _eta_range_text(metrics)
    # The peak of the plan is a schedule number: without a duration on every
    # leaf the scheduler has nothing to overlap, so the peak is unknown and
    # not "0".
    peak_hint = (
        f"пик по плану {metrics['planned_peak_parallel']}"
        if metrics["duration_known"] else "пик по плану неизвестен"
    )
    # The effort and the critical path are whole-plan numbers. When a leaf
    # has no estimate, the total is unknown — the known part is kept, and the
    # count of the unknown ones is named instead of a bare "0 мин".
    if metrics["effort_known"]:
        effort_value = fmt_minutes(metrics["effort_minutes"])
        effort_hint = f"критический путь {fmt_minutes(metrics['critical_minutes'])}"
    else:
        effort_value = "неизвестно"
        effort_hint = (
            f"известная часть {fmt_minutes(metrics['effort_minutes'])} · "
            f"критический путь неизвестен · "
            f"{metrics['unknown_estimate_all']} оценок неизвестны"
        )
    cards = [
        ("Готово", f"{metrics['done']} / {headline_total}",
         f"{metrics['progress_pct']}% {progress_note}", STATUS_DONE, True, "done"),
        ("В работе", str(metrics["running"]), "сейчас выполняется", STATUS_RUNNING, True, "running"),
        ("Заблокировано", str(metrics["blocked"]), "нужен внешний ход", STATUS_BLOCKED, True, "blocked"),
        ("В очереди", str(metrics["queued"]), "ждут своего слота", STATUS_QUEUED, True, "queued"),
        ("Отложено владельцем", str(metrics["deferred"]),
         "ответа не ждём, вне остатка", STATUS_DEFERRED, True, "deferred"),
        ("Осталось", str(metrics["unfinished"]),
         f"не завершено · отложено владельцем: {metrics['deferred']} (в остаток не входит)",
         STATUS_QUEUED, True, "unfinished"),
        ("Параллельность", f"{metrics['current_parallel']} / {metrics['slots']}",
         peak_hint, STATUS_RUNNING, False, "parallel"),
        (remaining_label, remaining_value, remaining_hint, STATUS_WAITING, False, "remaining"),
        ("Прогноз финиша", eta_range or "Срок неизвестен",
         eta_hint, STATUS_DONE, False, "forecast"),
        ("Усилие", effort_value, effort_hint, STATUS_QUEUED, False, "effort"),
    ]
    # Every tile knows the tasks behind it: the owner clicks a number and
    # wants to see them, without leaving the page.
    by_status: dict[str, list[str]] = {}
    for leaf in leaves:
        by_status.setdefault(leaf.status, []).append(leaf.id)
    unfinished_ids = [
        leaf.id for leaf in leaves if leaf.status not in (STATUS_DONE, STATUS_DEFERRED)
    ]
    unknown_ids = [
        leaf.id
        for leaf in leaves
        if leaf.estimate_min is None and leaf.status not in (STATUS_DONE, STATUS_DEFERRED)
    ]
    critical_ids = [leaf.id for leaf in leaves if leaf.id in metrics["critical_path"]]
    # Without a duration on every leaf the critical path is not a fact yet,
    # so the effort tile points at the leaves that make it unknown.
    effort_ids = (
        critical_ids if metrics["critical_known"]
        else list(metrics["unknown_estimate_leaf_ids"])
    )
    wave_ids: list[str] = []
    if schedule.waves:
        current_wave = min(
            (schedule.waves.get(leaf.id, 0) for leaf in leaves if leaf.status == STATUS_RUNNING),
            default=0,
        )
        wave_ids = [leaf.id for leaf in leaves if schedule.waves.get(leaf.id, 0) == current_wave]
    forecast_ids = list(
        dict.fromkeys(
            unknown_ids
            + [leaf.id for leaf in leaves if leaf.status == STATUS_WAITING]
            + critical_ids[-1:]
        )
    )
    tile_leaves = {
        "all": [leaf.id for leaf in leaves],
        "done": by_status.get(STATUS_DONE, []),
        "running": by_status.get(STATUS_RUNNING, []),
        "blocked": by_status.get(STATUS_BLOCKED, []),
        "queued": by_status.get(STATUS_QUEUED, []),
        "deferred": by_status.get(STATUS_DEFERRED, []),
        "unfinished": unfinished_ids,
        "parallel": wave_ids or [leaf.id for leaf in leaves],
        "remaining": [i for i in unfinished_ids if i not in unknown_ids] or unfinished_ids,
        "forecast": forecast_ids,
        "effort": effort_ids,
    }
    tile_titles = {key: label for label, _, _, _, _, key in cards}
    tile_titles["all"] = "Все задачи плана"
    card_html = "".join(
        f'<div class="kpi kpi-tile" data-tile="{escape(key)}" role="button" tabindex="0" '
        f'aria-label="{escape(label)}: {escape(value)} — показать задачи" '
        f'style="--accent:{STATUS_CSS_VARS.get(tone, "var(--accent)")}">'
        f'<div class="kpi-label" title="{escape(label)}">'
        + (f"{STATUS_GLYPHS.get(tone, '')} " if is_status else "")
        + f"{escape(label)}</div>"
        f'<div class="kpi-value">{escape(value)}</div>'
        f'<div class="kpi-hint">{escape(hint)}</div>'
        "</div>"
        for label, value, hint, tone, is_status, key in cards
    )
    leaf_index = {
        leaf.id: {
            "id": leaf.id,
            "template": leaves.index(leaf),
            "label": leaf.label or leaf.id,
            "status": leaf.status,
            "status_label": STATUS_LABELS.get(leaf.status, leaf.status),
            "owner": leaf.owner,
            "estimate": leaf.duration_label,
        }
        for leaf in leaves
    }
    tile_payload = json.dumps(
        {"tiles": tile_leaves, "titles": tile_titles, "leaves": leaf_index},
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    tile_island = f'<template id="lhc-tile-index">{tile_payload}</template>'

    # ----- progress bar --------------------------------------------------
    headline = metrics["headline_counts"]
    segments = []
    for status in STATUSES:
        count = headline.get(status, 0)
        if not count:
            continue
        segments.append(
            f'<div class="seg" style="width:{100.0 * count / max(headline_total, 1):.4f}%;'
            f'background:{STATUS_CSS_VARS[status]}" title="{STATUS_LABELS[status]}: {count}"></div>'
        )
    legend = "".join(
        f'<span class="legend-item"><i style="background:{STATUS_CSS_VARS[status]}"></i>'
        f"{STATUS_LABELS[status]} · {headline.get(status, 0)}</span>"
        for status in STATUSES
        if headline.get(status, 0)
    )

    # ----- what blocks, and what needs the owner ----------------------------
    # The owner wants to know, right after the state of the work, what holds
    # it and what he has to decide himself. Both are honest: a leaf that waits
    # is not a leaf that is blocked, and a leaf that needs a person says which
    # person and what exactly.
    stuck_leaves = [leaf for leaf in leaves if leaf.status in (STATUS_BLOCKED, STATUS_WAITING)]
    owner_leaves = [
        leaf
        for leaf in leaves
        if (leaf.blocker_details.get("human_required") or "").lower() == "yes"
    ]
    blocking_rows = []
    holding_rows = []
    for leaf in stuck_leaves:
        details = leaf.blocker_details
        reason = details.get("reason") or leaf.blocker or leaf.note or "Причина не указана."
        responsible = details.get("responsible") or leaf.owner or "Исполнитель не указан."
        next_action = details.get("next_action") or leaf.note or "Следующий шаг не указан."
        required = details.get("human_required", "unknown").lower()
        human_label = {"yes": "Да", "no": "Нет", "unknown": "Пока неизвестно"}.get(
            required, "Пока неизвестно")
        human_action = details.get("human_action") or "Действие человека не уточнено."
        waits = ", ".join(label_by_id.get(dep, dep) for dep in leaf.depends_on) or "внешнее условие"
        item = (
            f'<div class="blocker-head">'
            f'<span class="badge" style="background:{STATUS_CSS_VARS[leaf.status]}">'
            f"{escape(STATUS_LABELS[leaf.status])}</span>"
            f"<b>{escape(leaf.label or leaf.id)}</b></div>"
            f'<div class="blocker-reason"><b>Почему ждём:</b> {escape(reason)}</div>'
            f'<div class="blocker-meta"><b>Ждёт:</b> {escape(waits)}</div>'
            f'<div class="blocker-meta"><b>Кто делает:</b> {escape(responsible)}</div>'
            f'<div class="blocker-meta"><b>Следующий шаг:</b> {escape(next_action)}</div>'
            f'<div class="blocker-meta"><b>Нужен ли человек:</b> {escape(human_label)}. '
            f"{escape(human_action)}</div>"
        )
        if leaf.status == STATUS_BLOCKED:
            blocking_rows.append(f'<div class="blocker">{item}</div>')
        else:
            holding_rows.append(f'<div class="holding">{item}</div>')
    def holder_rows_html(rows: list[str]) -> list[str]:
        return rows

    owner_rows = []
    for leaf in owner_leaves:
        action = leaf.blocker_details.get("human_action") or "Действие человека не уточнено."
        owner_rows.append(
            f'<div class="owner-item"><div class="blocker-head">'
            f'<span class="badge" style="background:{STATUS_CSS_VARS[STATUS_WAITING]}">Нужно от меня</span>'
            f"<b>{escape(leaf.label or leaf.id)}</b></div>"
            f'<div class="blocker-reason">{escape(action)}</div>'
            f'<div class="blocker-meta"><b>Код:</b> {escape(leaf.id)}'
            + (f' · <b>сессия:</b> {escape(leaf.session)}' if leaf.session else "")
            + "</div></div>"
        )
    blocking_parts = []
    if blocking_rows or holding_rows:
        blocking_parts.append(
            '<div class="blocking-group"><h3>Держит работу</h3>'
            + "".join(blocking_rows)
            + "".join(holder_rows_html(holding_rows))
            + "</div>"
        )
    if owner_rows:
        blocking_parts.append(
            '<div class="blocking-group"><h3>Нужно от меня</h3>'
            + "".join(owner_rows)
            + "</div>"
        )
    if not blocking_parts:
        blocking_parts.append('<div class="empty">Ничего не блокировано и от меня ничего не нужно.</div>')
    blocking_html = "".join(blocking_parts)

    # ----- the progress, always in sight ----------------------------------
    # The owner reads the plan on a phone and wants to see the degree of the
    # progress at the very top, in the mobile layout and in the wide one. A
    # slim strip carries the same numbers as the tiles, so the two can never
    # disagree, and it sticks to the top of the window while the page scrolls.
    done_value = f"{metrics['done']} / {headline_total}"
    percent_value = f"{metrics['progress_pct']:g}%"
    remaining_hint = ""
    for label, value, hint, tone, is_status, _key in cards:
        if label == remaining_label:
            remaining_hint = hint
            break
    strip_parts = [
        f'<span class="progress-strip-title">Степень прогресса</span>',
        f'<span class="progress-strip-value">{escape(done_value)}</span>',
        f'<span class="progress-strip-percent">{escape(percent_value)}</span>',
    ]
    if remaining_hint:
        strip_parts.append(f'<span class="progress-strip-hint">{escape(remaining_hint)}</span>')
    progress_strip = (
        '<div class="progress-strip" id="lhc-progress-strip" role="button" tabindex="0" '
        'data-tile="all" aria-label="Степень прогресса — показать все задачи">'
        f'<div class="progress-strip-line">{"".join(strip_parts)}</div>'
        f'<div class="progress-strip-bar">{"".join(segments)}</div>'
        "</div>"
    )

    # ----- what to do now -------------------------------------------------
    # The launch decision is the parallel planner's: this only draws it.
    plan = plan_now(graph)
    slots = plan.get("slots")
    free_slots = plan.get("free_slots")
    if slots is None:
        slots_text = "неизвестно"
    elif free_slots is None:
        slots_text = f"{slots}"
    else:
        slots_text = f"{free_slots} из {slots}"

    def now_item(item: dict[str, Any], detail: str, extra_class: str = "") -> str:
        classes = "now-item" + (f" {extra_class}" if extra_class else "")
        return (
            f'<li class="{classes}">'
            f'<div class="now-head"><span class="now-id">{escape(item["id"])}</span>'
            f'<span class="now-name">{escape(item["label"])}</span></div>'
            f'<div class="now-meta">{escape(detail)}</div></li>'
        )

    running_html = ""
    if plan["running"]:
        running_html = "<ul class=\"now-list\">" + "".join(
            now_item(
                item,
                (f"идёт {fmt_minutes(item['actual'])}" if item.get("actual") is not None
                 else (f"начато в {item['since']}" if item.get("since") else "длительность не измерена")),
            )
            for item in plan["running"]
        ) + "</ul>"
    else:
        running_html = '<div class="now-empty">Сейчас не идёт ни одна линия.</div>'

    ready_html = ""
    if plan["ready"]:
        items = []
        for item in plan["ready"]:
            unblocks = item.get("unblocks") or []
            if unblocks:
                shown = ", ".join(_short(name, 34) for name in unblocks[:5])
                if len(unblocks) > 5:
                    shown += f" и ещё {len(unblocks) - 5}"
                detail = f"{item['estimate']} · разблокирует: {shown}"
            else:
                detail = f"{item['estimate']} · никого не разблокирует"
            items.append(now_item(item, detail))
        ready_html = "<ul class=\"now-list\">" + "".join(items) + "</ul>"
    else:
        ready_html = '<div class="now-empty">Ни одна линия не готова к запуску.</div>'

    deferred_html = ""
    if plan["deferred"]:
        items = []
        for item in plan["deferred"]:
            items.append(
                now_item(item, f"{item['estimate']} · ждёт свободного слота", "deferred")
            )
        deferred_html = (
            f'<div class="now-subtitle">Ждут свободного слота ({len(plan["deferred"])})</div>'
            "<ul class=\"now-list\">" + "".join(items) + "</ul>"
        )

    blocked_html = ""
    if plan["blocked"]:
        blocked_html = "<ul class=\"now-list\">" + "".join(
            now_item(item, item.get("reason") or "причина не указана", "blocked")
            for item in plan["blocked"]
        ) + "</ul>"
    else:
        blocked_html = '<div class="now-empty">Активных блокеров нет.</div>'

    # The lines that wait for others are not blocked: they are a separate,
    # compact list below the three groups, so no column pretends to be empty
    # while the other one carries the whole graph.
    waiting_html = ""
    if plan["waiting"]:
        shown = plan["waiting"][:14]
        chips = []
        for item in shown:
            unmet = item.get("unmet_ids") or []
            arrow = f' ← {escape(", ".join(unmet[:2]))}' if unmet else ""
            chips.append(
                f'<span class="wait-chip" title="{escape(item["label"])}">'
                f'{escape(item["id"])}{arrow}</span>'
            )
        rest = len(plan["waiting"]) - len(shown)
        waiting_html = (
            f'<div class="now-subtitle">Ждут зависимостей ({len(plan["waiting"])})</div>'
            f'<div class="wait-list">{"".join(chips)}'
            + (f'<span class="wait-more">и ещё {rest} — полный список в таблице листьев</span>' if rest > 0 else "")
            + "</div>"
        )

    now_html = (
        '<div class="panel-head">'
        "<h2>Что делать сейчас</h2>"
        f'<div class="slots-badge">Свободных слотов: <b>{escape(slots_text)}</b></div>'
        "</div>"
        '<div class="now-grid">'
        '<section class="now-col">'
        f'<h3><span class="now-glyph">🔄</span> В работе <span class="now-count">'
        f'{len(plan["running"])}</span></h3>{running_html}</section>'
        '<section class="now-col">'
        f'<h3><span class="now-glyph">🚀</span> Готовы к запуску <span class="now-count">'
        f'{len(plan["ready"])}</span></h3>{ready_html}{deferred_html}</section>'
        '<section class="now-col">'
        f'<h3><span class="now-glyph">⛔</span> Заблокированы <span class="now-count">'
        f'{len(plan["blocked"])}</span></h3>{blocked_html}</section>'
        "</div>"
        f"{waiting_html}"
        f'<div class="hint">Источник расчёта: {escape(plan["source"])}.</div>'
    )

    # ----- gantt ---------------------------------------------------------
    # A leaf without an estimate has no duration. The time scale is drawn
    # only when at least one leaf carries a known one; otherwise the panel
    # says the time is unavailable instead of drawing a minute axis that
    # promises a duration nobody measured.
    scheduled = [leaf for leaf in leaves if leaf.id in schedule.waves]
    deferred_leaves = [leaf for leaf in leaves if leaf.id not in schedule.waves]
    timed_leaf_ids = {
        leaf.id for leaf in scheduled
        if leaf.estimate_min is not None or leaf.estimate_max is not None
    }
    timeline_available = bool(timed_leaf_ids)
    if timeline_available:
        horizon = max(schedule.makespan, metrics["delivery_minutes_max"], 1.0)
        ticks = 6
        axis = "".join(
            f'<div class="tick tick-{index}" style="left:{100.0 * index / ticks:.4f}%">'
            f"{fmt_minutes(horizon * index / ticks)}</div>"
            for index in range(ticks + 1)
        )
    else:
        horizon = 1.0
        axis = (
            '<div class="gantt-axis-note">Шкала времени недоступна</div>'
        )
    gantt_rows: list[str] = []
    current_wave: Optional[int] = None
    wave_counts: dict[int, int] = {}

    def gantt_row(leaf: Leaf, start: float, finish: float) -> str:
        color = STATUS_CSS_VARS[leaf.status]
        duration_known = leaf.id in timed_leaf_ids
        # The critical path is a fact only when every leaf carries a
        # duration; until then the marker would name an accident of the
        # schedule, so it is not drawn.
        critical = metrics["critical_known"] and leaf.id in metrics["critical_path"]
        tooltip = (
            f"{leaf.id} · {leaf.label}\n"
            f"статус: {STATUS_LABELS[leaf.status]}\n"
            f"оценка: {leaf.duration_label}"
            + (f"\nусилие (суммарно): {fmt_minutes(leaf.actual_minutes)}" if leaf.actual_minutes is not None else "")
            + (f"\nпо часам: {fmt_minutes(leaf.actual_span_minutes)}" if leaf.actual_span_minutes is not None else "")
            + (f"\nплан: {fmt_minutes(leaf.plan_minutes)}" if leaf.plan_minutes is not None else "")
            + (f"\nсверх плана: {fmt_minutes(leaf.overrun_minutes)}" if leaf.overrun_minutes is not None else "")
            + (f"\nначало: {leaf.started_at}" if leaf.started_at else "")
            + (f"\nконец: {leaf.finished_at}" if leaf.finished_at else "")
            + (f"\nзависит: {', '.join(label_by_id.get(dep, dep) for dep in leaf.depends_on)}" if leaf.depends_on else "")
            + (f"\nпараллельно: {', '.join(label_by_id.get(peer, peer) for peer in leaf.parallel_with)}" if leaf.parallel_with else "")
            + (f"\nблокер: {leaf.blocker}" if leaf.blocker and leaf.status == STATUS_BLOCKED else "")
            + ("\nна критическом пути" if critical else "")
        )
        title = escape(tooltip)
        critical_mark = '<span class="crit" title="критический путь">◆ критический путь</span>' if critical else ""
        if duration_known and timeline_available:
            left = 100.0 * start / horizon
            width = max(0.6, 100.0 * max(finish - start, 0.0) / horizon)
            bar = (
                f'<div class="bar" style="left:{left:.4f}%;width:{width:.4f}%;background:{color}"'
                f' title="{title}"></div>'
            )
        else:
            # No duration, no bar: a drawn width would read as a measured
            # length of time.
            bar = f'<span class="gantt-noduration" title="{title}">—</span>'
        return (
            f'<div class="gantt-row" data-status="{leaf.status}" data-leaf="{escape(leaf.id)}">'
            f'<div class="gantt-label" title="{escape(leaf.label)}">'
            f'<span class="gantt-line">'
            f'<span class="dot" style="background:{color}"></span>'
            f'<span class="gantt-id" title="{escape(leaf.id)}">{escape(leaf.id)}</span>'
            f'<span class="gantt-text">{escape(leaf.label)}</span>'
            f"</span>"
            f'<span class="gantt-line gantt-meta">'
            f'<span class="gantt-status">{STATUS_GLYPHS[leaf.status]} {STATUS_LABELS[leaf.status]}</span>'
            f"{critical_mark}"
            f"</span>"
            f'</div>'
            f'<div class="gantt-track">'
            f"{bar}</div></div>"
        )

    for leaf in scheduled:
        wave_counts[schedule.waves.get(leaf.id, 0)] = wave_counts.get(schedule.waves.get(leaf.id, 0), 0) + 1
    for leaf in scheduled:
        wave = schedule.waves.get(leaf.id, 0)
        if wave != current_wave:
            current_wave = wave
            gantt_rows.append(
                f'<div class="wave-row"><span>Волна {wave + 1}</span>'
                f'<span class="wave-count">{wave_counts.get(wave, 0)} листьев</span></div>'
            )
        start = schedule.starts.get(leaf.id, 0.0)
        finish = schedule.finishes.get(leaf.id, start)
        gantt_rows.append(gantt_row(leaf, start, finish))
    if deferred_leaves:
        gantt_rows.append(
            f'<div class="wave-row"><span>Отложено владельцем</span>'
            f'<span class="wave-count">{len(deferred_leaves)} листьев</span></div>'
        )
        for leaf in deferred_leaves:
            gantt_rows.append(gantt_row(leaf, 0.0, 0.0))
    gantt_html = "".join(gantt_rows)

    # The panel states what its rows do and do not show.
    if timeline_available:
        untimed = [leaf for leaf in scheduled if leaf.id not in timed_leaf_ids]
        gantt_note = (
            f'<div class="hint">Листьев без оценки длительности: {len(untimed)} — '
            "они показаны знаком «—», без полосы длительности.</div>"
            if untimed else ""
        )
    else:
        gantt_note = (
            '<div class="hint">Ни один лист не имеет оценки длительности: строки '
            "показывают состояние и волны, а не длительность. "
            f"Оценок неизвестны: {metrics['unknown_estimate_all']}.</div>"
        )

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
                f'<span class="badge" style="background:{STATUS_CSS_VARS[STATUS_BLOCKED]}">'
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
        if not (leaf.owner or leaf.session or leaf.harness or leaf.model or leaf.model_class):
            continue
        session_rows.append(
            "<tr>"
            f'<td><span class="dot" style="background:{STATUS_CSS_VARS[leaf.status]}"></span>'
            f"{escape(leaf.id)}</td>"
            f"<td>{escape(leaf.label[:70])}</td>"
            f"<td>{escape(leaf.owner or '—')}</td>"
            f"<td>{escape(leaf.session or '—')}</td>"
            f"<td>{escape(leaf.harness or '—')}</td>"
            f"<td>{escape(leaf.model or leaf.model_class or '—')}</td>"
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
        span = fmt_minutes(leaf.actual_span_minutes) if leaf.actual_span_minutes is not None else "—"
        over = " over" if leaf.overrun else ""
        # The owner reads the plan in two colors: the time that was planned
        # is green, everything above it is yellow. Both numbers come from the
        # report - a leaf without an estimate has no plan, and a leaf without
        # a measured window has no overrun, so neither is invented here.
        plan = leaf.plan_minutes
        extra = leaf.overrun_minutes
        if plan is None:
            plan_cell = "<span class='plan-none'>плана нет</span>"
            plan_dd = "<dd>плана нет</dd>"
        else:
            plan_cell = f"<span class='plan-time'>план {escape(fmt_minutes(plan))}</span>"
            plan_dd = f"<dd class='plan-value'>{escape(fmt_minutes(plan))}</dd>"
        if extra is not None:
            plan_cell += (
                f"<span class='cell-sub plan-over'>сверх плана {escape(fmt_minutes(extra))}</span>"
            )
            overrun_dd = f"<dd class='plan-over-value'>{escape(fmt_minutes(extra))}</dd>"
        elif leaf.actual_span_minutes is None:
            overrun_dd = "<dd>длительность не измерена</dd>"
        elif plan is None:
            overrun_dd = "<dd>плана нет</dd>"
        else:
            plan_cell += "<span class='cell-sub'>в пределах плана</span>"
            overrun_dd = "<dd>в пределах плана</dd>"
        if (
            leaf.estimate_min is not None
            and leaf.estimate_max is not None
            and abs(leaf.estimate_max - leaf.estimate_min) > 0.01
        ):
            # A range says more than its upper bound: both bounds stay visible.
            plan_cell += f"<span class='cell-sub'>оценка {escape(leaf.duration_label)}</span>"
            estimate_dd = f"<dt>Оценка</dt><dd>{escape(leaf.duration_label)}</dd>"
        else:
            estimate_dd = ""
        # The real times of the work, or their honest absence.
        times_parts = []
        if leaf.started_at:
            times_parts.append(f"старт {leaf.started_at}")
        if leaf.finished_at:
            times_parts.append(f"финиш {leaf.finished_at}")
        times_text = " · ".join(times_parts) if times_parts else "время не зафиксировано"
        times_html = f"<span class='row-times'>{escape(times_text)}</span>"
        # The owner reads a task and needs the whole of it: what the task is,
        # who works on it, in which session and with which model, what waits
        # for it, and what the next step is. A field that is empty for this
        # leaf is left out; a field that exists is never dropped in favour of
        # another one.
        blocker_details = leaf.blocker_details or {}
        next_action = blocker_details.get("next_action") or ""
        human_action = blocker_details.get("human_action") or ""
        human_required = (blocker_details.get("human_required") or "").strip()
        model = leaf.model or leaf.model_class or ""
        details = (
            f"<dl class='task-details'><dt>Код</dt><dd>{escape(leaf.id)}</dd>"
            + (f"<dt>Описание задачи</dt><dd>{escape(leaf.description)}</dd>" if leaf.description else "")
            + (f"<dt>Ожидаемый результат</dt><dd>{escape(leaf.acceptance)}</dd>" if leaf.acceptance else "")
            + (f"<dt>Затрагиваемые файлы</dt><dd>{escape(', '.join(leaf.affected_files))}</dd>" if leaf.affected_files else "")
            + (f"<dt>Примечание</dt><dd>{escape(leaf.note)}</dd>" if leaf.note else "")
            + f"<dt>Владелец</dt><dd>{escape(leaf.owner or '—')}</dd>"
            f"<dt>Зависит от</dt><dd>{escape(deps)}</dd>"
            f"<dt>Параллельно с</dt><dd>{escape(peer)}</dd>"
            + (f"<dt>Блокер</dt><dd>{escape(leaf.blocker)}</dd>" if leaf.blocker else "")
            + (f"<dt>Следующий шаг</dt><dd>{escape(next_action)}</dd>" if next_action else "")
            + (
                f"<dt>Что нужно от человека</dt><dd>{escape(human_action)}</dd>"
                + (f" <span class='cell-sub'>{escape(human_required)}</span>" if human_required else "")
                + "</dd>"
                if human_action else ""
            )
            + f"<dt>Сессия</dt><dd>{escape(leaf.session or '—')}</dd>"
            + (f"<dt>Модель</dt><dd>{escape(model)}</dd>" if model else "")
            + (f"<dt>Рантайм</dt><dd>{escape(leaf.harness)}</dd>" if leaf.harness else "")
            + f"<dt>Усилие (суммарно)</dt><dd>{escape(actual)}</dd>"
            f"<dt>Длительность по часам</dt><dd>{escape(span)}</dd>"
            + (
                f"<dt>Окно работы</dt><dd>{escape(leaf.started_at)} – {escape(leaf.finished_at)}</dd>"
                if leaf.started_at and leaf.finished_at else ""
            )
            + estimate_dd
            + f"<dt>План</dt>{plan_dd}"
            + f"<dt>Сверх плана</dt>{overrun_dd}"
            + f"<dt>Начало</dt><dd>{escape(leaf.started_at or 'не зафиксировано')}</dd>"
            + f"<dt>Конец</dt><dd>{escape(leaf.finished_at or 'не зафиксировано')}</dd>"
            + (
                f"<dt>Почему нет оценки</dt><dd>{escape(leaf.estimate_unknown_reason)}</dd>"
                if leaf.estimate_unknown_reason else ""
            )
            + (f"<dt>Волна</dt><dd>{escape(str(leaf.wave))}</dd>" if leaf.wave else "")
            + "</dl>"
        )
        detail_templates.append(
            f"<template id='task-details-template-{details_index}'><div class='task-details-card'>"
            f"<div class='task-details-head'><h3>{escape(leaf.label)}</h3>"
            "<button type='button' class='task-details-close'>Закрыть</button></div>"
            f"{details}</div></template>"
        )
        # The row itself opens the task: the owner taps the task, not a
        # button that sits at the far end of the row. The meta line names who
        # works on it, so the owner sees it without opening anything.
        meta_parts = []
        if leaf.owner:
            meta_parts.append(f"владелец: {leaf.owner}")
        if leaf.session:
            meta_parts.append(f"сессия: {leaf.session}")
        if leaf.model or leaf.model_class:
            meta_parts.append(f"модель: {leaf.model or leaf.model_class}")
        meta_html = (
            f"<span class='row-meta'>{escape(' · '.join(meta_parts))}</span>" if meta_parts else ""
        )
        table_rows.append(
            f'<tr data-status="{leaf.status}" data-text="{escape(_search_text(leaf))}" '
            f"data-details-id='{details_index}' class='leaf-row'>"
            f"<td class='task-title'><span class='row-id'>{escape(leaf.id)}</span>"
            f"<span class='row-name'>{escape(leaf.label)}</span>{times_html}{meta_html}</td>"
            f'<td data-label="Статус"><span class="status" style="--c:{STATUS_CSS_VARS[leaf.status]}">'
            f"{STATUS_GLYPHS[leaf.status]} {STATUS_LABELS[leaf.status]}</span></td>"
            f"<td data-label=\"Оценка\"><div class='cell-plan'>{plan_cell}</div></td>"
            f'<td data-label="Усилие" class="{over.strip()}">{escape(actual)}'
            + (
                f'<span class="cell-sub">по часам {escape(span)}</span>'
                if leaf.actual_span_minutes is not None
                else ""
            )
            + "</td>"
            f"<td class='details-cell'><button type='button' class='task-details-trigger' "
            f"data-details-id='{details_index}' aria-expanded='false' "
            f"aria-label='Подробнее: {escape(leaf.label)}'>Подробнее</button></td>"
            "</tr>"
        )
    leaves_table = (
        "<div class='table-scroll'><table class='table table-leaves'><thead><tr><th>Задача</th><th>Статус</th>"
        "<th>Оценка</th><th>Усилие</th><th>Детали</th></tr></thead><tbody>"
        + "".join(table_rows)
        + "</tbody></table></div>"
    )
    leaves_details = (
        "<div id='task-details-host' class='task-details-host' hidden></div>"
        + "".join(detail_templates)
    )

    # ----- live journal --------------------------------------------------
    # A graph may carry its own change log (time, action, result, confirmation).
    # The leaf list is not a journal: it repeats the task names.
    journal = graph.journal or graph.live_items or [
        {"status": leaf.status, "text": leaf.label or leaf.id, "leaf": leaf.id}
        for leaf in leaves
    ]
    live_html = ""
    if journal:
        items = []
        for item in journal:
            status = item.get("status", STATUS_QUEUED)
            color = STATUS_CSS_VARS.get(status, STATUS_CSS_VARS[STATUS_QUEUED])
            leaf_tag = ""
            if item.get("leaf"):
                leaf_name = label_by_id.get(str(item["leaf"]))
                if leaf_name:
                    leaf_tag = f'<span class="leaf-tag">{escape(leaf_name)}</span>'
            stamp = ""
            if item.get("at"):
                stamp = f'<span class="live-at">{escape(str(item["at"]))}</span>'
            # A change log names an action and a result. A journal that only
            # repeats the task names is a second list of the table.
            action = item.get("action") or item.get("text") or item.get("result") or ""
            result_html = ""
            if item.get("result") and item.get("result") != action:
                result_html = f'<span class="live-result">{escape(str(item["result"]))}</span>'
            evidence = ""
            if item.get("evidence"):
                evidence = f'<span class="live-evidence">{escape(str(item["evidence"]))}</span>'
            items.append(
                f'<li><span class="dot" style="background:{color}"></span>'
                f'{stamp}<span class="live-text">{escape(str(action))}</span>'
                f'{result_html}{evidence}{leaf_tag}</li>'
            )
        live_html = f'<ul class="live">{"".join(items)}</ul>'
    else:
        live_html = '<div class="empty">Журнал изменений пуст.</div>'

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
    # The remaining work is a real number only when every unfinished leaf
    # carries an estimate; otherwise the missing time is named, not zeroed.
    if metrics["remaining_known"]:
        remaining_fact = escape(fmt_minutes(metrics["remaining_minutes_max"]))
    else:
        remaining_fact = (
            f"неизвестно — {metrics['unknown_estimate_pending']} листьев без оценки"
        )
    # The blocked work is a real number only when every blocked leaf carries
    # an estimate. No blocked leaf at all is a known zero and stays a zero.
    if not metrics["blocked_unknown_count"]:
        blocked_fact = escape(fmt_minutes(metrics["blocked_minutes"]))
    else:
        blocked_fact = (
            f"неизвестно · известная часть "
            f"{escape(fmt_minutes(metrics['blocked_known_minutes']))} · "
            f"{metrics['blocked_unknown_count']} листьев без оценки"
        )
    if metrics["critical_known"]:
        critical_fact = escape(critical_chain)
    else:
        critical_fact = "неизвестен — оценки длительности не заданы"
    if metrics["duration_known"]:
        peak_fact = f"{metrics['planned_peak_parallel']} из {metrics['slots']} слотов"
    else:
        peak_fact = "неизвестен — оценки длительности не заданы"
    forecast_html = (
        "<ul class='facts'>"
        f"<li><b>Усилие</b> (сумма известных оценок): {escape(fmt_minutes(metrics['effort_minutes']))}"
        f"{escape(unknown_effort)}</li>"
        f"<li><b>{'Известная активная работа' if metrics['unknown_estimate_pending'] or metrics['external_wait_unknown'] else 'Длительность'}"
        f" (план с {metrics['slots']} слотами): "
        f"{escape(fmt_minutes(metrics['delivery_minutes_max']))}</li>"
        f"<li><b>Осталось</b> (без завершённых): "
        f"{remaining_fact}</li>"
        f"<li><b>Пик параллельности</b> по плану: {peak_fact}</li>"
        f"<li><b>Критический путь</b>: {critical_fact}</li>"
        f"<li><b>Заблокировано</b> работы: {blocked_fact}</li>"
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
        peak_text = (
            f"пик параллельности {metrics['planned_peak_parallel']}"
            if metrics["duration_known"] else "пик параллельности неизвестен"
        )
        layer_hint = (
            f'<div class="hint">граф: {metrics["total"]} листьев · слотов: {metrics["slots"]} · '
            f"{peak_text}</div>"
        )

    # ----- brief: what the work is for ------------------------------------
    # The goal and the expected business result are the reason the work
    # exists, so they are shown on the first screen. The confirmed progress and
    # the external waits are the technical wording of the plan and stay folded.
    why_cards = []
    detail_cards = []
    if graph.goal:
        why_cards.append(
            f'<article class="brief-card brief-goal"><h2>Цель</h2>'
            f"<p>{escape(graph.goal)}</p></article>"
        )
    for index, result in enumerate(
        graph.business_results or ([graph.business_result] if graph.business_result else [])
    ):
        heading = "Ожидаемый бизнес-результат" if index == 0 else f"Бизнес-результат {index + 1}"
        why_cards.append(
            f'<article class="brief-card brief-result"><h2>{escape(heading)}</h2>'
            f"<p>{escape(result)}</p></article>"
        )
    if graph.current_progress:
        detail_cards.append(
            f'<article class="brief-card"><h2>Подтверждённый прогресс</h2>'
            f"<p>{escape(graph.current_progress)}</p></article>"
        )
    if graph.external_waits:
        detail_cards.append(
            f'<article class="brief-card brief-wait"><h2>Внешние ожидания</h2>'
            f"<p>{escape(graph.external_waits)}</p></article>"
        )
    why_html = f'<div class="brief brief-why">{"".join(why_cards)}</div>' if why_cards else ""
    brief_html = f'<div class="brief">{"".join(detail_cards)}</div>' if detail_cards else ""
    why_panel = ""
    if why_html:
        why_panel = (
            '<details class="panel brief-details brief-why-details" open>\n'
            "  <summary>Цель и ожидаемый бизнес-результат</summary>\n"
            f"  {why_html}\n"
            "</details>"
        )

    # ----- the delivery side -------------------------------------------
    # The plan state and the delivery narrative are one page: the owner
    # reads why the work exists, what state it is in and what it rests on.
    # One headline, one navigation, one theme switch for the whole page.
    product_sections = ""
    product_plan = ""
    product_evidence = ""
    evidence_fold = ""
    product_styles = ""
    product_scripts = ""
    hero_html = ""
    nav_html = ""
    if product:
        lhc_product = product_module()

        try:
            product_plan = lhc_product.render_product_sections(
                product, include_hero=False, include_nav=False, group="plan"
            )
            product_evidence = lhc_product.render_product_sections(
                product, include_hero=False, include_nav=False, group="evidence"
            )
        except TypeError:
            # The delivery module does not split its sections yet: everything
            # stays together, above the evidence of the plan.
            product_plan = lhc_product.render_product_sections(
                product, include_hero=False, include_nav=False
            )
            product_evidence = ""
        product_sections = product_plan
        evidence_fold = (
            '<details class="evidence-fold"><summary>'
            "Доказательства, требования и сервисы — справочный материал"
            "</summary>"
            + product_evidence
            + "</details>"
            if product_evidence
            else ""
        )
        product_styles = lhc_product.product_styles()
        product_scripts = lhc_product.product_scripts()
        hero_html = lhc_product.product_hero(product, with_theme=True)
        nav_html = merged_navigation(lhc_product.product_nav_items())
    else:
        hero_html = (
            "<header>"
            "<div>"
            f"<h1>{escape(graph.title)}</h1>"
            f'<div class="sub">LHC · {escape(graph.source_kind)} · план обновлён '
            f"{escape(graph.updated_at.replace('T', ' ')) or 'неизвестно'} · ревизия "
            f"{escape(graph_revision(graph))} · собран {escape(generated)}</div>"
            "</div>"
            '<div class="head-actions">'
            '<button type="button" class="theme-toggle" id="theme-toggle" '
            'aria-label="Переключить тему">Тема: как в системе</button>'
            f'<div class="head-count"><b>{escape(str(total))}</b><span>задач в графе</span></div>'
            "</div>"
            "</header>"
        )

    html = HTML_TEMPLATE.format(
        product_styles=product_styles,
        product_scripts=product_scripts,
        product_sections=product_sections,
        product_plan=product_plan,
        product_evidence=product_evidence,
        evidence_fold=evidence_fold,
        plan_gantt_hidden=' hidden' if product else '',
        blocking=blocking_html,
        tile_island=tile_island,
        progress_strip=progress_strip,
        header=hero_html,
        nav=nav_html,
        title=escape(graph.title),
        generated=generated,
        source=escape(source_label),
        kind=escape(graph.source_kind),
        revision=graph_revision(graph),
        graph_updated=escape(graph.updated_at.replace("T", " ")) or "неизвестно",
        snapshot=escape(SNAPSHOT_NOTE),
        palette=palette_css(),
        cards=card_html,
        segments="".join(segments),
        legend=legend,
        brief=brief_html,
        brief_details_open=" open" if graph.current_progress else "",
        why_panel=why_panel,
        now=now_html,
        axis=axis,
        gantt=gantt_html,
        gantt_note=gantt_note,
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

    # The page keeps itself in sync with the file it was built from: a plan
    # that changed a second ago is visible without a reload. The rendering
    # stays in Python; the page only swaps in what Python rendered.
    try:
        html = live_module().inject_live(html)
    except Exception:  # pragma: no cover - a page without the poller is still a page
        pass
    return html


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · LHC</title>
<style>
  {palette}
  * {{ box-sizing: border-box; }}
  /* The page background lives on the canvas itself. No overlay element is
     painted over the content, so nothing can ever hide a block of the
     dashboard behind an opaque layer. */
  html {{ background: var(--bg); }}
  body {{
    margin: 0; background: var(--bg);
    background-image: radial-gradient(1500px 760px at 12% -12%, #1b2b45 0%, rgba(13,17,23,0) 62%);
    background-repeat: no-repeat;
    color: var(--text);
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, "Helvetica Neue", Arial, sans-serif;
    padding: 22px clamp(12px, 3vw, 40px) 56px;
    min-height: 100%;
    overflow-x: hidden;
  }}
  a {{ color: var(--accent); }}
  .page {{ max-width: 2200px; margin: 0 auto; }}

  /* ---- header ---- */
  header {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between;
    margin-bottom: 16px; }}
  h1 {{ font-size: 23px; margin: 0; letter-spacing: -0.3px; overflow-wrap: anywhere; }}
  header > div {{ min-width: 0; max-width: 100%; }}
  .sub {{ color: var(--muted); font-size: 12.5px; overflow-wrap: anywhere; }}
  .head-count {{ display: flex; align-items: baseline; gap: 8px; background: var(--panel);
    border: 1px solid var(--line); border-radius: 12px; padding: 8px 14px; }}
  .head-count b {{ font-size: 22px; font-weight: 650; letter-spacing: -0.4px; }}
  .head-count span {{ color: var(--muted); font-size: 12px; }}
  .theme-toggle {{ background: var(--panel); border: 1px solid var(--line); color: var(--muted);
    border-radius: 10px; padding: 8px 12px; cursor: pointer; font: inherit; font-size: 12.5px;
    min-height: 44px; min-width: 44px; }}
  .theme-toggle:hover {{ color: var(--text); }}
  .head-actions {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
  /* The progress stays in sight while the page scrolls. */
  /* A number you can click: the tasks behind it. */
  .kpi-tile {{ cursor: pointer; }}
  .kpi-tile:hover {{ border-color: var(--accent); }}
  .kpi-tile:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .progress-strip {{ cursor: pointer; }}
  .tile-card {{ margin: 0 0 14px; padding: 10px 12px; border: 1px solid var(--line);
    border-radius: 10px; background: var(--panel-2); }}
  .tile-card-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px;
    margin-bottom: 8px; }}
  .tile-card-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
  .tile-card-item {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px;
    padding: 6px 0; border-top: 1px solid var(--line); cursor: pointer; }}
  .tile-card-item:hover .row-name {{ color: var(--accent); }}
  .tile-card-close, .tile-card-back {{ min-height: 44px; padding: 4px 10px; border-radius: 8px;
    border: 1px solid var(--line); background: transparent; color: var(--muted); cursor: pointer; }}
  .journal-fold summary {{ cursor: pointer; list-style: none; }}
  .journal-fold summary::-webkit-details-marker {{ display: none; }}
  .journal-fold summary h2 {{ margin: 0; font-size: 12px; text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted); }}
  .journal-fold[open] summary h2 {{ color: var(--text); }}
  .evidence-fold {{ margin: 0 0 14px; border: 1px solid var(--line); border-radius: 10px;
    background: var(--panel); }}
  .evidence-fold > summary {{ cursor: pointer; padding: 10px 12px; color: var(--muted);
    font-size: 12.5px; }}
  .evidence-fold[open] > summary {{ color: var(--text); border-bottom: 1px solid var(--line); }}
  .evidence-fold > *:not(summary) {{ margin-left: 12px; margin-right: 12px; }}
  .blocking-group {{ display: grid; gap: 8px; }}
  .blocking-group h3 {{ margin: 0 0 2px; font-size: 11px; text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted); }}
  .blocker-owner {{ border-left-color: var(--warn); }}
  /* The progress strip sticks to the top, so an anchor jump must not land
     a section under it. */
  section, .panel, .kpis, [id^="lhc-"] {{ scroll-margin-top: 76px; }}
  .progress-strip {{ position: sticky; top: 0; z-index: 40; margin: 0 0 12px;
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 8px 12px; }}
  .progress-strip-line {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 10px; }}
  .progress-strip-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); }}
  .progress-strip-value {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .progress-strip-percent {{ font-size: 13px; font-weight: 600; color: var(--accent); }}
  .progress-strip-hint {{ font-size: 12px; color: var(--muted); }}
  .progress-strip-bar {{ display: flex; height: 6px; margin-top: 7px; border-radius: 999px;
    overflow: hidden; background: var(--panel-2); }}
  .progress-strip-bar .seg {{ height: 100%; }}
  .snapshot-note {{ color: var(--muted); font-size: 12.5px; margin: 0 0 14px; padding: 8px 12px;
    border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 10px;
    background: var(--panel); overflow-wrap: anywhere; }}

  /* ---- panels ---- */
  .panel {{ background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 16px; min-width: 0; }}
  .panel h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .09em; color: var(--muted);
    margin: 0 0 12px; font-weight: 600; }}
  .panel-head {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; }}
  .panel-head h2 {{ margin: 0; }}

  /* ---- brief: goal and business result ---- */
  .brief {{ display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-bottom: 16px; }}
  /* The technical wording is a confirmation, not the first thing to read. */
  .brief-details {{ margin-bottom: 16px; }}
  .brief-details > summary {{ cursor: pointer; color: var(--muted); font-size: 12.5px;
    min-height: 44px; display: flex; align-items: center; }}
  .brief-details[open] > summary {{ margin-bottom: 12px; color: var(--text); }}
  .brief-card {{ background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 12px; padding: 14px 16px;
    min-width: 0; }}
  .brief-card h2 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
    margin: 0 0 6px; font-weight: 600; }}
  .brief-card p {{ margin: 0; overflow-wrap: anywhere; }}
  .brief-goal {{ border-left-color: var(--accent); }}
  .brief-result {{ border-left-color: var(--ok); }}
  .brief-wait {{ border-left-color: var(--warn); }}
  /* The why-panel is open on the first screen; it may be folded by the owner. */
  .brief-why-details {{ margin-bottom: 16px; }}
  .brief-why-details > summary {{ color: var(--text); }}
  .brief-why {{ margin-bottom: 0; }}

  /* ---- KPI strip ---- */
  .kpis {{ display: grid; gap: 10px; grid-template-columns: repeat(5, minmax(0, 1fr)); margin-bottom: 14px; }}
  .kpi {{ background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 12px; padding: 11px 13px;
    min-width: 0; }}
  .kpi-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .07em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .kpi-value {{ font-size: 25px; font-weight: 650; margin: 3px 0 2px; letter-spacing: -0.6px; line-height: 1.15;
    overflow-wrap: anywhere; }}
  .kpi-hint {{ color: var(--muted); font-size: 11.5px; overflow-wrap: anywhere; }}

  /* ---- progress and legend ---- */
  .progress {{ display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: #0b1018;
    border: 1px solid var(--line); }}
  .seg {{ height: 100%; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 10px; color: var(--muted); font-size: 12px; }}
  .legend-item i {{ display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 6px; }}

  /* ---- what to do now ---- */
  .slots-badge {{ font-size: 12.5px; color: var(--muted); background: var(--panel-2);
    border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px; }}
  .slots-badge b {{ color: var(--text); font-size: 14px; }}
  .now-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 14px;
    align-items: start; }}
  .now-col {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
    min-width: 0; }}
  .now-col h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .07em; color: var(--muted);
    margin: 0 0 10px; font-weight: 600; display: flex; align-items: center; gap: 6px; }}
  .now-count {{ margin-left: auto; background: #0e141d; border: 1px solid var(--line); border-radius: 999px;
    padding: 0 8px; color: var(--text); font-size: 11.5px; }}
  .now-subtitle {{ color: var(--muted); font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em;
    margin: 12px 0 6px; }}
  .now-list {{ list-style: none; margin: 0; padding: 0; }}
  .now-item {{ padding: 8px 0; border-bottom: 1px solid #232c3a; }}
  .now-item:last-child {{ border-bottom: 0; }}
  .now-head {{ display: flex; gap: 8px; align-items: baseline; min-width: 0; }}
  .now-id {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11.5px;
    color: var(--accent); flex: none; max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .now-name {{ min-width: 0; overflow-wrap: anywhere; }}
  .now-meta {{ color: var(--muted); font-size: 11.5px; margin-top: 2px; overflow-wrap: anywhere; }}
  .now-item.deferred {{ opacity: .75; }}
  .now-item.blocked .now-id {{ color: var(--bad); }}
  .now-empty {{ color: var(--muted); font-style: italic; font-size: 12.5px; }}
  .wait-list {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .wait-chip {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11.5px;
    color: var(--muted); background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px;
    padding: 2px 7px; white-space: nowrap; }}
  .wait-more {{ color: var(--muted); font-size: 11.5px; align-self: center; }}

  /* ---- gantt ---- */
  .gantt {{ overflow-x: auto; max-width: 100%; }}
  .gantt-inner {{ min-width: 760px; }}
  .gantt-axis-row, .gantt-row {{ display: grid; grid-template-columns: minmax(240px, 320px) minmax(360px, 1fr);
    gap: 10px; min-width: 680px; }}
  .gantt-axis-spacer {{ min-width: 0; }}
  .gantt-axis {{ position: relative; height: 22px; min-width: 0; border-bottom: 1px solid var(--line); }}
  .gantt-axis-note {{ font-size: 11px; color: var(--muted); line-height: 22px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }}
  .gantt-noduration {{ color: var(--muted); font-size: 13px; line-height: 26px; opacity: .8; }}
  .tick {{ position: absolute; top: 2px; transform: translateX(-50%); font-size: 11px; color: var(--muted);
    white-space: nowrap; }}
  .tick-0 {{ transform: none; }}
  .tick-6 {{ transform: translateX(-100%); }}
  .gantt-row {{ align-items: center; border-bottom: 1px solid #1e2632; }}
  .gantt-row:hover {{ background: #18202d; }}
  .gantt-label {{ display: flex; flex-direction: column; gap: 1px; padding: 5px 0; min-width: 0; overflow: hidden; }}
  .gantt-line {{ display: flex; align-items: center; gap: 7px; min-width: 0; }}
  .gantt-id {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px;
    color: var(--muted); flex: none; max-width: 34%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .gantt-text {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .gantt-meta {{ gap: 8px; }}
  .gantt-status {{ font-size: 11px; color: var(--muted); white-space: nowrap; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex: none; }}
  .crit {{ color: #f0a742; font-size: 10.5px; white-space: nowrap; }}
  .gantt-track {{ position: relative; height: 26px; min-width: 0; }}
  .bar {{ position: absolute; top: 6px; height: 15px; border-radius: 5px; min-width: 3px;
    box-shadow: 0 0 0 1px rgba(0,0,0,.25) inset; }}
  .wave-row {{ display: flex; justify-content: space-between; align-items: center; gap: 10px;
    margin-top: 14px; padding: 8px 12px; background: var(--panel-2); border: 1px solid var(--line);
    border-left: 3px solid var(--accent); border-radius: 10px; color: var(--muted);
    font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
  .wave-count {{ text-transform: none; letter-spacing: 0; }}

  /* ---- two column work area ---- */
  .grid {{ display: grid; gap: 16px; grid-template-columns: minmax(0, 1.35fr) minmax(0, .65fr);
    align-items: start; }}
  .grid > * {{ min-width: 0; }}
  @media (max-width: 1000px) {{ .grid {{ grid-template-columns: minmax(0, 1fr); }} }}
  @media (min-width: 1700px) {{
    .gantt-axis-row, .gantt-row {{ grid-template-columns: minmax(340px, 460px) minmax(360px, 1fr); }}
  }}
  @media (max-width: 1800px) {{ .kpis {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} }}
  @media (max-width: 1200px) {{ .kpis {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
  @media (max-width: 1100px) {{
    .now-grid {{ grid-template-columns: minmax(0, 1fr); }}
  }}
  @media (max-width: 900px) {{
    .brief {{ grid-template-columns: minmax(0, 1fr); }}
  }}
  @media (max-width: 700px) {{ .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  .blocker {{ background: var(--panel-2); border: 1px solid #3a2530; border-left: 3px solid var(--bad);
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
  .live-at {{ color: #8aa0b8; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .live-result {{ color: var(--text); font-size: 12.5px; }}
  .live-evidence {{ color: #8aa0b8; font-size: 12px; white-space: nowrap; }}
  .leaf-tag {{ color: var(--muted); font-size: 11px; border: 1px solid var(--line); border-radius: 5px;
    padding: 0 5px; min-width: 0; white-space: normal; overflow-wrap: anywhere; }}
  .cell-sub {{ display: block; color: var(--muted); font-size: 11px; }}
  .table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .table th {{ text-align: left; color: var(--muted); font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .05em; padding: 6px 8px; border-bottom: 1px solid var(--line);
    background: var(--panel); }}
  .table td {{ padding: 6px 8px; border-bottom: 1px solid #1c2431; vertical-align: top; }}
  /* The leaves are read as a table, so the panel takes the whole width
     of the page instead of one column of a two-column grid. */
  .panel-leaves {{ grid-column: 1 / -1; }}
  .table-leaves {{ min-width: 920px; width: 100%; table-layout: fixed; }}
  .table-scroll {{ max-width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; }}
  .table-leaves th:nth-child(1) {{ width: 42%; }}
  .table-leaves th:nth-child(2) {{ width: 120px; }}
  .table-leaves th:nth-child(3), .table-leaves th:nth-child(4) {{ width: 110px; }}
  .table-leaves th:nth-child(5) {{ width: 120px; }}
  .task-title {{ font-weight: 550; overflow-wrap: anywhere; }}
  .row-id {{ display: inline-block; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 11px; color: var(--muted); margin-right: 7px; vertical-align: 1px; }}
  .table-leaves .status {{ white-space: nowrap; }}
  .task-details-trigger, .task-details-close {{ color: var(--accent); background: transparent; border: 1px solid var(--line);
    border-radius: 6px; cursor: pointer; font: inherit; padding: 3px 7px; }}
  .task-details-host {{ position: static; width: 100%; margin-top: 12px; }}
  /* The leaf row is the control: the owner taps the task, and the task opens
     right under itself, where the finger already is. */
  .leaf-row {{ cursor: pointer; }}
  .leaf-row:hover .row-name {{ color: var(--accent); }}
  .leaf-row:focus-within {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
  .task-details-row > td {{ padding: 0; border: none; background: transparent; }}
  .task-details-row .task-details-card {{ margin: 0 0 10px; }}
  .row-meta {{ display: block; margin-top: 2px; color: var(--muted); font-size: 12px;
    overflow-wrap: anywhere; }}
  .details-cell {{ text-align: right; }}
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
  /* The overrun of the plan and the plan itself are two facts with two
     colors, and both colors come from the palette of the theme: the planned
     time is green, everything above it is yellow. */
  .over {{ color: var(--warn); }}
  .plan-time {{ display: block; color: var(--ok); font-weight: 600; }}
  .plan-over {{ color: var(--warn); font-weight: 600; }}
  .plan-none {{ color: var(--muted); }}
  .plan-value {{ color: var(--ok); font-weight: 600; }}
  .plan-over-value {{ color: var(--warn); font-weight: 600; }}
  .cell-plan {{ display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }}
  .row-times {{ display: block; margin-top: 2px; color: var(--muted); font-size: 12px;
    font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }}
  .empty {{ color: var(--muted); font-style: italic; }}
  .notes {{ color: var(--muted); margin: 0; padding-left: 18px; }}
  .hint {{ color: var(--muted); font-size: 12px; margin: 10px 0 0; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }}
  .toolbar input {{ background: #0e141d; border: 1px solid var(--line); color: var(--text); border-radius: 8px;
    padding: 6px 10px; min-width: 200px; font: inherit; }}
  .chip {{ background: #0e141d; border: 1px solid var(--line); color: var(--muted); border-radius: 999px;
    padding: 4px 11px; cursor: pointer; font: inherit; font-size: 12px; }}
  .chip.active {{ background: var(--accent); color: #0d1117; border-color: var(--accent); font-weight: 600; }}
  footer {{ color: var(--muted); font-size: 11.5px; margin-top: 22px; border-top: 1px solid var(--line);
    padding-top: 12px; }}
  /* The phone layout comes last, so it wins over every base rule above. */
  @media (max-width: 640px) {{
    /* The state and the action come first; the Gantt opens on its own,
       below the table that carries the same leaves. */
    .page {{ display: flex; flex-direction: column; }}
    /* A flex item keeps its content width by default, so the wide Gantt
       would push the whole page sideways. The panels have to be allowed to
       shrink and scroll inside. */
    .page > * {{ min-width: 0; max-width: 100%; }}
    .panel, .grid > *, .kpis {{ min-width: 0; }}
    .panel-gantt {{ order: 8; }}
    footer {{ order: 9; }}
    body {{ padding: 14px 10px 36px; }}
    .panel {{ padding: 12px; border-radius: 11px; }}
    h1 {{ font-size: 19px; }}
    /* The cards become compact rows: on a phone the state and the action
       have to be visible without a grid of boxes. */
    .kpis {{ grid-template-columns: minmax(0, 1fr); gap: 6px; }}
    .kpi {{ padding: 8px 10px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 10px; }}
    .kpi-label {{ order: 1; flex: 0 0 auto; }}
    .kpi-value {{ order: 2; font-size: 19px; margin: 0; }}
    .kpi-hint {{ order: 3; flex: 1 1 100%; font-size: 11px; }}
    .toolbar input {{ min-width: 0; width: 100%; }}
    /* Every touch target is at least 44 CSS px. */
    .chip, .task-details-trigger, .task-details-close, .toolbar input, .toolbar select {{ min-height: 44px; min-width: 44px; }}
    .task-details {{ grid-template-columns: minmax(0, 1fr); gap: 0; }}
    .task-details dd {{ margin-bottom: 8px; }}
    /* The leaf table becomes one compact row per leaf instead of a wide
       table that has to be scrolled sideways. */
    .table-leaves {{ min-width: 0; display: block; }}
    .table-leaves thead {{ display: none; }}
    .table-leaves tbody {{ display: block; }}
    .table-leaves tr {{ display: block; padding: 8px 0; border-bottom: 1px solid var(--line); }}
    .table-leaves td {{ display: flex; gap: 10px; justify-content: space-between; align-items: baseline;
      border: none; padding: 2px 0; text-align: right; }}
    .table-leaves td::before {{ content: attr(data-label); color: var(--muted); font-size: 11px;
      text-transform: uppercase; letter-spacing: .05em; text-align: left; flex: 0 0 auto; }}
    .table-leaves td.task-title {{ display: block; text-align: left; }}
    .table-leaves td.task-title::before {{ content: none; }}
    /* The plan cell keeps its lines stacked and flush right on a phone. */
    .table-leaves td .cell-plan {{ align-items: flex-end; }}
    .table-leaves td:last-child {{ justify-content: flex-start; }}
    .table-leaves td:last-child::before {{ content: none; }}
    .table-scroll {{ overflow-x: visible; }}
    /* The opened task is a card under its own row, not another table cell. */
    .table-leaves tr.task-details-row {{ display: block; padding: 0; border: none; }}
    .table-leaves tr.task-details-row > td {{ display: block; padding: 0; text-align: left; }}
    .table-leaves tr.task-details-row > td::before {{ content: none; }}
  }}
{product_styles}
</style>
</head>
<body>
<div class="page">
{progress_strip}

{header}

{nav}

<p class="snapshot-note">{snapshot}</p>

<div class="kpis" id="lhc-state">{cards}</div>

<div class="tile-card" id="lhc-tile-card" hidden></div>
{tile_island}

<div class="panel panel-now">
  {now}
</div>

<div class="panel panel-blocking" id="lhc-blocking">
  <h2>Что блокирует</h2>
  {blocking}
</div>

{why_panel}

{product_plan}

<div class="panel panel-progress">
  <div class="progress">{segments}</div>
  <div class="legend">{legend}</div>
</div>

<details class="panel brief-details"{brief_details_open}>
  <summary>Подтверждённый прогресс и внешние ожидания</summary>
  {brief}
</details>

{evidence_fold}

<div class="panel panel-gantt" id="lhc-plan-gantt"{plan_gantt_hidden}>
  <h2>Гант · листья и параллельные волны</h2>
  {gantt_note}
  <div class="gantt"><div class="gantt-inner">
    <div class="gantt-axis-row"><div class="gantt-axis-spacer"></div><div class="gantt-axis">{axis}</div></div>
    {gantt}
  </div></div>
</div>

<div class="grid">
  <div class="panel panel-leaves" id="lhc-leaves">
    <h2>Листья</h2>
    {layer_hint}
    <div class="toolbar">
      <input id="search" type="search" placeholder="Поиск по листу, id, владельцу, сессии или модели…">
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
      <h2>Технические привязки</h2>
      <details class="technical"><summary>Владельцы, сессии, harness и модели</summary>
        {sessions}
      </details>
    </div>
    <div class="panel" id="lhc-forecast">
      <h2>Прогноз</h2>
      {forecast}
      {notes}
    </div>
    <div class="panel journal-fold" id="lhc-journal">
      <details>
        <summary><h2>Журнал изменений</h2></summary>

      <h2>Журнал изменений</h2>
      {live}

      </details>
    </div>
  </div>
</div>
</div>

<footer>
  LHC task graph · ревизия {revision} · один файл, без внешних зависимостей · собран {generated}
  <details class="technical"><summary>Путь исходного плана</summary><code>{source}</code></details>
</footer>

<script>
(function () {{
  // The theme is the reader's choice, remembered between openings. Without a
  // stored choice the dashboard follows the system.
  var root = document.documentElement;
  var stored = null;
  try {{ stored = window.localStorage.getItem('lhc-theme'); }} catch (error) {{ stored = null; }}
  function systemPrefersLight() {{
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches);
  }}
  function applyTheme(state) {{
    if (state === 'light' || state === 'dark') {{
      root.setAttribute('data-theme', state);
    }} else {{
      // "as the system": no attribute, and the light scheme of the system wins.
      root.removeAttribute('data-theme');
      if (systemPrefersLight()) {{ root.setAttribute('data-theme', 'light'); }}
    }}
  }}
  function currentTheme() {{
    var value = null;
    try {{ value = window.localStorage.getItem('lhc-theme'); }} catch (error) {{ value = null; }}
    return value === 'light' || value === 'dark' ? value : 'auto';
  }}
  applyTheme(currentTheme());
  var toggle = document.getElementById('theme-toggle');
  if (toggle) {{
    var order = ['auto', 'light', 'dark'];
    var names = {{ auto: 'Тема: как в системе', light: 'Тема: светлая', dark: 'Тема: тёмная' }};
    function label() {{ toggle.textContent = names[currentTheme()]; }}
    label();
    toggle.addEventListener('click', function () {{
      var next = order[(order.indexOf(currentTheme()) + 1) % order.length];
      applyTheme(next);
      try {{
        if (next === 'auto') {{ window.localStorage.removeItem('lhc-theme'); }}
        else {{ window.localStorage.setItem('lhc-theme', next); }}
      }} catch (error) {{ /* no storage */ }}
      label();
    }});
  }}
}})();
(function () {{
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('.table-leaves tbody tr'));
  var input = document.getElementById('search');
  var activeDetailsRow = null;
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
  // The task opens where the owner taps it. The card used to open in a host
  // below the whole table, which on a phone is thousands of pixels away from
  // the finger that asked for it.
  function closeDetails() {{
    if (!activeDetailsRow) {{ return; }}
    if (activeDetailsRow.previousElementSibling) {{
      var previousButton = activeDetailsRow.previousElementSibling.querySelector('.task-details-trigger');
      if (previousButton) {{ previousButton.setAttribute('aria-expanded', 'false'); }}
    }}
    activeDetailsRow.remove();
    activeDetailsRow = null;
  }}
  function openDetails(row, id) {{
    var template = document.getElementById('task-details-template-' + id);
    if (!template || !row) {{ return; }}
    closeDetails();
    var detailsRow = document.createElement('tr');
    detailsRow.className = 'task-details-row';
    var cell = document.createElement('td');
    cell.colSpan = 5;
    cell.appendChild(template.content.cloneNode(true));
    detailsRow.appendChild(cell);
    row.after(detailsRow);
    activeDetailsRow = detailsRow;
    var button = row.querySelector('.task-details-trigger');
    if (button) {{ button.setAttribute('aria-expanded', 'true'); }}
    var close = detailsRow.querySelector('.task-details-close');
    if (close) {{
      close.addEventListener('click', function () {{ closeDetails(); }});
      close.focus({{ preventScroll: true }});
    }}
    detailsRow.scrollIntoView({{ block: 'nearest' }});
  }}
  document.querySelectorAll('.task-details-trigger').forEach(function (button) {{
    button.addEventListener('click', function (event) {{
      event.stopPropagation();
      var row = button.closest('tr');
      openDetails(row, button.dataset.detailsId);
    }});
  }});
  rows.forEach(function (row) {{
    if (!row.dataset.detailsId) {{ return; }}
    row.addEventListener('click', function () {{
      openDetails(row, row.dataset.detailsId);
    }});
  }});
  // Every number of the page can be opened: the tile shows the tasks behind
  // it, and a task in that list opens its full card.
  var tileIndex = null;
  try {{
    var island = document.getElementById('lhc-tile-index');
    tileIndex = island ? JSON.parse(island.content.textContent) : null;
  }} catch (error) {{ tileIndex = null; }}
  var tileCard = document.getElementById('lhc-tile-card');
  var currentTile = null;
  function tileTitle(key) {{
    return (tileIndex && tileIndex.titles && tileIndex.titles[key]) || 'Задачи';
  }}
  function renderTileList(key) {{
    if (!tileIndex || !tileCard) {{ return; }}
    var ids = (tileIndex.tiles && tileIndex.tiles[key]) || [];
    var head = document.createElement('div');
    head.className = 'tile-card-head';
    var title = document.createElement('b');
    title.textContent = tileTitle(key) + ' · ' + ids.length;
    var close = document.createElement('button');
    close.type = 'button'; close.className = 'tile-card-close'; close.textContent = 'Закрыть';
    close.addEventListener('click', function () {{
      tileCard.hidden = true; tileCard.replaceChildren(); currentTile = null;
    }});
    head.appendChild(title); head.appendChild(close);
    var list = document.createElement('ul');
    list.className = 'tile-card-list';
    ids.forEach(function (id) {{
      var leaf = (tileIndex.leaves && tileIndex.leaves[id]) || {{}};
      var item = document.createElement('li');
      item.className = 'tile-card-item';
      var code = document.createElement('span'); code.className = 'row-id'; code.textContent = id;
      var name = document.createElement('span'); name.className = 'row-name';
      name.textContent = leaf.label || id;
      var meta = document.createElement('span'); meta.className = 'row-meta';
      meta.textContent = [leaf.status_label, leaf.owner, leaf.estimate].filter(Boolean).join(' · ');
      item.appendChild(code); item.appendChild(name); item.appendChild(meta);
      item.addEventListener('click', function () {{ openLeafInTile(id); }});
      list.appendChild(item);
    }});
    if (!ids.length) {{
      var empty = document.createElement('div');
      empty.className = 'empty'; empty.textContent = 'Задач нет.';
      list.appendChild(empty);
    }}
    tileCard.replaceChildren(head, list);
    tileCard.hidden = false;
  }}
  function openLeafInTile(id) {{
    if (!tileIndex || !tileCard) {{ return; }}
    var leaf = (tileIndex.leaves && tileIndex.leaves[id]) || {{}};
    var template = document.getElementById('task-details-template-' + leaf.template);
    if (!template) {{ return; }}
    var back = document.createElement('button');
    back.type = 'button'; back.className = 'tile-card-back'; back.textContent = '← ко всем задачам';
    back.addEventListener('click', function () {{ renderTileList(currentTile); }});
    var card = template.content.cloneNode(true);
    tileCard.replaceChildren(back, card);
    tileCard.hidden = false;
    var progressStrip = document.getElementById('lhc-progress-strip');
    var stickySpace = progressStrip ? progressStrip.getBoundingClientRect().height + 12 : 76;
    tileCard.style.scrollMarginTop = Math.max(76, Math.ceil(stickySpace)) + 'px';
    tileCard.scrollIntoView({{ block: 'start' }});
    var close = tileCard.querySelector('.task-details-close');
    if (close) {{
      close.addEventListener('click', function () {{ renderTileList(currentTile); }});
    }}
  }}
  document.querySelectorAll('[data-tile]').forEach(function (tile) {{
    tile.addEventListener('click', function () {{
      currentTile = tile.dataset.tile;
      renderTileList(currentTile);
    }});
    tile.addEventListener('keydown', function (event) {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        tile.click();
      }}
    }});
  }});
  apply();
}})();
{product_scripts}
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# text summary
# --------------------------------------------------------------------------


def wave_count(graph: Graph, metrics: dict[str, Any]) -> int:
    """Number of waves the schedule derives from the dependencies."""

    schedule = metrics.get("schedule")
    waves = getattr(schedule, "waves", None) or {}
    return max(waves.values()) + 1 if waves else 1


def render_leaf_lines(graph: Graph, metrics: dict[str, Any]) -> list[str]:
    """Render one readable line per leaf: id, status, estimate, fact, wave, links."""

    schedule = metrics.get("schedule")
    waves = getattr(schedule, "waves", None) or {}
    lines = [f"Листья плана ({len(graph.leaves)}):"]
    for leaf in graph.leaves:
        wave = leaf.wave if leaf.wave is not None else waves.get(leaf.id, 0) + 1
        actual = fmt_minutes(leaf.actual_minutes) if leaf.actual_minutes is not None else "не измерено"
        parts = [
            f"  - {leaf.id}",
            f"{STATUS_GLYPHS.get(leaf.status, '⋯')} {STATUS_LABELS.get(leaf.status, leaf.status)}",
        ]
        if leaf.label:
            parts.append(f"({leaf.label})")
        parts.append(f"оценка {leaf.duration_label}")
        parts.append(f"усилие {actual}")
        if leaf.actual_span_minutes is not None:
            parts.append(f"по часам {fmt_minutes(leaf.actual_span_minutes)}")
        # A deferred leaf is not scheduled: it has no wave, it is outside the
        # remainder of the delivery.
        parts.append("вне остатка" if leaf.status == STATUS_DEFERRED else f"волна {wave}")
        parts.append("зависит: " + (", ".join(leaf.depends_on) or "—"))
        if leaf.parallel_with:
            parts.append("параллельно: " + ", ".join(leaf.parallel_with))
        if leaf.blocker and leaf.status == STATUS_BLOCKED:
            parts.append(f"блокер: {leaf.blocker}")
        lines.append(" · ".join(parts))
        if leaf.description:
            lines.append(f"      Описание задачи: {leaf.description}")
        if leaf.acceptance:
            lines.append(f"      Приёмка: {leaf.acceptance}")
        if leaf.affected_files:
            lines.append("      Затрагиваемые файлы: " + ", ".join(f"`{path}`" for path in leaf.affected_files))
    return lines


def render_text(graph: Graph, metrics: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Граф задач: {graph.title}")
    lines.append(f"Ревизия плана: {graph_revision(graph)}")
    lines.append(SNAPSHOT_NOTE)
    if graph.goal:
        lines.append(f"Цель: {graph.goal}")
    for result in (graph.business_results or ([graph.business_result] if graph.business_result else [])):
        lines.append(f"Бизнес-результат: {result}")
    scope = "по журналу волны" if metrics["use_live"] else "по листьям графа"
    lines.append(
        "Прогресс ({scope}): {done}/{total} готово ({pct}%) · в работе {running} · "
        "заблокировано {blocked} · осталось {left}".format(
            scope=scope,
            done=metrics["done"], total=metrics["headline_total"], pct=metrics["progress_pct"],
            running=metrics["running"], blocked=metrics["blocked"],
            left=metrics["unfinished"],
        )
    )
    lines.append(
        "Листьев в графе: {total} · слотов: {slots} · волн: {waves}".format(
            total=metrics["total"], slots=metrics["slots"],
            waves=graph.declared_waves or wave_count(graph, metrics),
        )
    )
    lines.append(
        "Параллельность: сейчас {current} из {slots} слотов, {peak}".format(
            current=metrics["current_parallel"], slots=metrics["slots"],
            peak=(f"пик по плану {metrics['planned_peak_parallel']}"
                  if metrics["duration_known"] else "пик по плану неизвестен"),
        )
    )
    lines.append(
        "Прогноз: {work_label} {remaining} (от {minimum}), финиш {eta}. {anchor}{imprecise}".format(
            work_label=("известная активная часть" if metrics["unknown_estimate_pending"] or metrics["external_wait_unknown"] else "осталось"),
            remaining=fmt_minutes(metrics["remaining_minutes_max"]),
            minimum=fmt_minutes(metrics["remaining_minutes_min"]),
            eta=("неизвестен из-за внешнего ожидания" if metrics["external_wait_unknown"] else
                 f"неизвестен: {metrics['unknown_estimate_pending']} листьев без оценки"
                 if metrics["unknown_estimate_pending"] else _eta_range_text(metrics)),
            anchor=("отсчёт от последнего события " + metrics["eta_anchor_clock"]
                    + f" · простой {fmt_minutes(metrics['eta_anchor_idle_minutes'])}"
                    if metrics["eta_anchor_clock"] else "остаток стартует сейчас"),
                imprecise=(
                    " · неточно: " + "; ".join(
                        (
                            [f"Листьев без оценки — {metrics['unknown_estimate_pending']}"]
                            if metrics["unknown_estimate_pending"] else []
                        )
                        + (
                            ["срок внешнего ожидания не подтверждён"]
                            if metrics["external_wait_unknown"] or metrics["external_wait_declared"]
                            else []
                        )
                    )
                    if (
                        metrics["unknown_estimate_pending"]
                        or metrics["external_wait_unknown"]
                        or metrics["external_wait_declared"]
                    )
                    else ""
                ),
        )
    )
    if metrics["critical_path"] and metrics["critical_known"]:
        labels = {leaf.id: leaf.label or leaf.id for leaf in graph.leaves}
        lines.append("Критический путь: " + " → ".join(labels.get(item, item) for item in metrics["critical_path"]))
    elif not metrics["critical_known"]:
        lines.append("Критический путь: неизвестен — оценки длительности не заданы")
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
    lines.extend(render_leaf_lines(graph, metrics))
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
            # Only the bounds that are actually known are written: a null bound
            # would make the exported graph fail the offline checker.
            bounds: dict[str, Any] = {}
            if leaf.estimate_min is not None:
                bounds["minimum"] = leaf.estimate_min
            if leaf.estimate_max is not None:
                bounds["maximum"] = leaf.estimate_max
            task["estimate_minutes"] = bounds
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
        if leaf.model_class:
            task["model_class"] = leaf.model_class
        if leaf.blocker:
            task["blocker"] = leaf.blocker
        if leaf.acceptance:
            task["acceptance"] = leaf.acceptance
        if leaf.description:
            task["description"] = leaf.description
        if leaf.affected_files:
            task["affected_files"] = leaf.affected_files
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
        "business_results": list(graph.business_results),
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
# reconciliation: the report's tasks and the graph's leaves are one set
# --------------------------------------------------------------------------


@dataclass
class PlanSync:
    """The difference between the report's task list and the graph's leaves."""

    matched: list[tuple[Leaf, Leaf]] = field(default_factory=list)
    extra_in_report: list[Leaf] = field(default_factory=list)
    missing_in_report: list[Leaf] = field(default_factory=list)
    status_mismatch: list[tuple[Leaf, Leaf]] = field(default_factory=list)
    field_mismatch: list[tuple[Leaf, Leaf, str]] = field(default_factory=list)
    matched_by_label: int = 0

    @property
    def ok(self) -> bool:
        return not (self.extra_in_report or self.missing_in_report or self.status_mismatch or self.field_mismatch)


def _graph_leaf_for(leaf: Leaf, graph: Graph, taken: set[str]) -> tuple[Optional[Leaf], bool]:
    """Find the graph leaf that carries the same task as the report leaf.

    The id is the primary key. A report leaf carries a positional id, so a
    hand-written graph may name the same task differently; a unique label
    match is the only fallback, because a weak overlap is not evidence.
    """

    for candidate in graph.leaves:
        if candidate.id in taken:
            continue
        if candidate.id.strip().lower() == leaf.id.strip().lower():
            return candidate, False
    label = normalize(leaf.label).lower()
    if not label:
        return None, False
    matches = [
        candidate
        for candidate in graph.leaves
        if candidate.id not in taken and normalize(candidate.label).lower() == label
    ]
    return (matches[0], True) if len(matches) == 1 else (None, False)


def compare_plan_with_graph(report: Graph, graph: Graph) -> PlanSync:
    """Compare task identity/status and human details stated in the report."""

    result = PlanSync()
    taken: set[str] = set()
    for leaf in report.leaves:
        target, by_label = _graph_leaf_for(leaf, graph, taken)
        if target is None:
            result.extra_in_report.append(leaf)
            continue
        taken.add(target.id)
        result.matched.append((leaf, target))
        if by_label:
            result.matched_by_label += 1
        if leaf.status != target.status:
            result.status_mismatch.append((leaf, target))
        for field_name in ("description", "acceptance", "affected_files"):
            reported = getattr(leaf, field_name)
            if reported and reported != getattr(target, field_name):
                result.field_mismatch.append((leaf, target, field_name))
    for leaf in graph.leaves:
        if leaf.id not in taken:
            result.missing_in_report.append(leaf)
    return result


def load_plan_report(path: Path) -> Graph:
    """Load a canonical plan report; an unread report is an error."""

    text = path.read_text(encoding="utf-8", errors="replace")
    graph = parse_plan_report(text)
    if graph is None:
        raise ValueError(PLAN_REPORT_HINT)
    graph.source_path = str(path)
    graph.resolve_dependencies()
    return graph


def load_graph_document(path: Path) -> Graph:
    """Load a task graph JSON; a report or any other text is not a graph."""

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {error}") from error
    graph = parse_graph_json(document)
    graph.source_path = str(path)
    graph.resolve_dependencies()
    return graph


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
    render.add_argument(
        "--markdown",
        type=Path,
        help="write the Markdown summary of the same graph revision",
    )
    render.add_argument(
        "--out-dir",
        type=Path,
        help="write plan.html and plan.md of one graph revision into this directory",
    )
    render.add_argument(
        "--product",
        type=Path,
        help="delivery side of the plan as JSON; it is merged into the same page",
    )

    merged = sub.add_parser(
        "render-product",
        help="Build the merged page out of the delivery side alone",
    )
    merged.add_argument("input", type=Path, help="delivery side JSON")
    merged.add_argument("--out-dir", type=Path, required=True)
    merged.add_argument("--title", help="override the page title")

    status = sub.add_parser("status", help="Print a compact text summary")
    status.add_argument("input", type=Path)

    export = sub.add_parser("export", help="Convert a plan into the standard graph JSON")
    export.add_argument("input", type=Path)
    export.add_argument("-o", "--output", type=Path, required=True)
    export.add_argument(
        "--merge",
        type=Path,
        help="Carry the attribution of an earlier graph into the fresh export",
    )

    validate = sub.add_parser("validate", help="Check the graph structure")
    validate.add_argument("input", type=Path)

    check = sub.add_parser(
        "check-plan",
        help="Compare plan task identity, statuses and stated task details with the graph",
    )
    check.add_argument("report", type=Path, help="canonical plan report (markdown)")
    check.add_argument("graph", type=Path, help="plan.graph.json of the same objective")
    return parser


def load_product(path: Optional[Path]) -> Optional[dict[str, Any]]:
    """Read the delivery side of a plan."""
    if path is None:
        return None
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path}: ожидался объект JSON")
    return document


def command_render(args: argparse.Namespace) -> int:
    graph = require_leaves(discover_graph(args.input))
    if args.title:
        graph.title = args.title
    metrics = build_metrics(graph)
    html = render_html(graph, metrics, load_product(getattr(args, "product", None)))
    # The dashboard and the Markdown summary come from the same graph, so they
    # carry the same revision. Two artifacts of one plan are generated, never
    # kept in sync by hand.
    markdown_text = render_text(graph, metrics)
    output = args.output
    markdown = args.markdown
    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        output = args.out_dir / "plan.html"
        markdown = args.out_dir / "plan.md"
    if output is None:
        stem = Path(graph.source_path).stem if graph.source_path else "lhc-grid"
        output = Path.cwd() / f"{stem}.grid.html"
    output.write_text(html, encoding="utf-8")
    print(f"{output}")
    if markdown is not None:
        markdown.write_text(markdown_text, encoding="utf-8")
        print(f"{markdown}")
    if args.open:
        try:
            webbrowser.open(output.resolve().as_uri())
        except Exception:  # pragma: no cover - headless hosts have no browser
            print("browser not available", file=sys.stderr)
    return 0


def command_render_product(args: argparse.Namespace) -> int:
    """The merged page of a delivery side: the plan it carries and the plan itself."""
    import lhc_product

    product = load_product(args.input)
    leaves = lhc_product.product_leaves(product)
    if not leaves:
        raise ValueError(f"{args.input}: в delivery side нет работ")
    tasks = []
    for leaf in leaves:
        low = leaf.get("estimate_minutes")
        high = leaf.get("estimate_max_minutes")
        base = leaf.get("estimate_base_minutes")
        note = str(leaf.get("note") or "")
        if base is not None:
            note = f"{note} · рабочая оценка {fmt_minutes(base)}".strip(" ·")
        tasks.append({
            "id": leaf.get("id"),
            "label": leaf.get("label") or "",
            "status": leaf.get("status") or STATUS_QUEUED,
            "owner": leaf.get("owner") or "",
            "estimate_minutes": {"minimum": low, "maximum": high if high is not None else low},
            "depends_on": leaf.get("depends_on") or [],
            "note": note,
        })
    document = {
        "schema_version": 2,
        "title": args.title or str(product.get("title") or "План работ"),
        "goal": str(product.get("title") or ""),
        "business_result": str(product.get("coverageNote") or ""),
        "current_progress": str(product.get("method") or ""),
        "tasks": tasks,
    }
    graph = parse_graph_json(document)
    metrics = build_metrics(graph)
    html = render_html(graph, metrics, product)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.out_dir / "plan.html"
    output.write_text(html, encoding="utf-8")
    print(f"{output}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    graph = require_leaves(discover_graph(args.input))
    metrics = build_metrics(graph)
    print(render_text(graph, metrics))
    return 0


def merge_attribution(
    document: dict[str, Any], previous: dict[str, Any], report_title: str = ""
) -> None:
    """Carry the attribution of an earlier graph into a fresh export.

    The export writes what a plan report knows. The attribution of a leaf - the
    paths it owns, its role - is not in the report, so a refresh would drop it
    and force a manual edit of the JSON at every plan boundary. The earlier
    graph is read as raw JSON because the parser drops fields it does not model.
    """

    tasks = [item for item in previous.get("tasks", []) if isinstance(item, dict)]
    by_id = {item.get("id"): item for item in tasks if item.get("id")}
    by_label = {item.get("label"): item for item in tasks if item.get("label")}
    for task in document.get("tasks", []):
        if not isinstance(task, dict):
            continue
        source = by_id.get(task.get("id")) or by_label.get(task.get("label"))
        if not source:
            continue
        for field in ATTRIBUTION_FIELDS:
            if not task.get(field) and source.get(field) is not None:
                task[field] = source[field]
    for field in ("current_progress", "external_waits"):
        if not document.get(field) and previous.get(field):
            document[field] = previous[field]
    # The title of the plan is the first line of the report. A title that was
    # set in the graph by hand survives a refresh, a title that came from the
    # report does not survive it as a stale copy.
    previous_title = previous.get("title")
    if previous_title and previous_title != DEFAULT_GRAPH_TITLE:
        if not report_title or previous_title != report_title:
            document["title"] = previous_title
    elif previous_title and document.get("title") == DEFAULT_GRAPH_TITLE:
        document["title"] = previous_title


def command_export(args: argparse.Namespace) -> int:
    graph = require_leaves(discover_graph(args.input))
    document = export_graph(graph)
    if args.merge:
        previous = json.loads(args.merge.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ValueError("merged graph is not a JSON object")
        merge_attribution(document, previous, report_title=graph.title)
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


def command_check_plan(args: argparse.Namespace) -> int:
    """Reconcile the report's task list with the graph's leaves."""

    report = load_plan_report(args.report)
    graph = load_graph_document(args.graph)
    result = compare_plan_with_graph(report, graph)
    print(f"Отчёт: {args.report}")
    print(f"Граф:   {args.graph}")
    print(
        f"Задач в отчёте: {len(report.leaves)} · листьев в графе: {len(graph.leaves)}"
        + (f" · сопоставлено по названию: {result.matched_by_label}" if result.matched_by_label else "")
    )
    if result.ok:
        print("OK: задачи отчёта и листья графа совпадают — идентификаторы, статусы и указанные описания.")
        return 0
    print("РАСХОЖДЕНИЕ между отчётом и графом:")
    if result.extra_in_report:
        print("  задачи в отчёте без листа в графе:")
        for leaf in result.extra_in_report:
            print(f"    - {leaf.id} «{leaf.label}» — {STATUS_LABELS.get(leaf.status, leaf.status)}")
    if result.missing_in_report:
        print("  листья в графе без задачи в отчёте:")
        for leaf in result.missing_in_report:
            print(f"    - {leaf.id} «{leaf.label}» — {STATUS_LABELS.get(leaf.status, leaf.status)}")
    if result.status_mismatch:
        print("  разные статусы:")
        for leaf, target in result.status_mismatch:
            print(
                f"    - {leaf.id}: в отчёте «{STATUS_LABELS.get(leaf.status, leaf.status)}», "
                f"в графе «{STATUS_LABELS.get(target.status, target.status)}»"
            )
    if result.field_mismatch:
        print("  разные описания, приёмки или затрагиваемые файлы:")
        names = {"description": "описание задачи", "acceptance": "приёмка", "affected_files": "список файлов"}
        for leaf, _target, field_name in result.field_mismatch:
            print(f"    - {leaf.id} «{leaf.label}»: {names[field_name]} не совпадает")
    print("Приведите отчёт и граф в соответствие; расхождение — дефект, а не «примерно одинаково».")
    return 1


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "render": command_render,
        "render-product": command_render_product,
        "status": command_status,
        "export": command_export,
        "validate": command_validate,
        "check-plan": command_check_plan,
    }
    try:
        return handlers[args.command](args)
    except (OSError, ValueError) as error:
        print(f"lhc_grid: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
