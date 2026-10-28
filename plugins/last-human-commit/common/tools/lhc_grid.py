#!/usr/bin/env python3
"""Render an LHC task graph as one self-contained HTML dashboard.

The dashboard answers, in one screen: what is done, what runs now, what is
blocked, roughly when the work finishes and how much of it runs in parallel.

It also answers the question a plan could not answer before: what this leaf
costs in dollars. The money is computed here, from the leaf's declared model
alias or class and the live catalog snapshot that `lhc_models.py` caches under
the repository's `.tmp/` — no LLM is in that loop, and no price or model name
is written in this file. A leaf whose class is unknown prints «модель не
выбрана», a plan whose snapshot is missing or older than its TTL prints «цена
не получена», and neither ever prints `$0`, because a zero in a cost column
reads like a cheap leaf.

Inputs
------
* a task graph JSON (``schema_version`` 1 or 2);
* a canonical LHC plan report (``common/protocols/PLAN_REPORT.md``);
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
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

SCHEMA_VERSIONS = (1, 2)

# The cost vocabulary. The words are the collector's enums, repeated here only
# as the set the reader recognises; the single source of truth for what a leaf
# may declare stays in `lhc_plan_json.py`, and the grid never invents a value
# outside them.
TIER_WORDS = ("fast", "frontier")
PROVENANCE_WORDS = ("measured", "provisional")

# What the plan prints when it does not know. A missing price and a missing
# model are two different absences, and both are named instead of being drawn
# as `$0`: a zero in a cost column reads like a cheap leaf, and the owner
# dispatches on it.
PRICE_UNAVAILABLE = "цена не получена"
MODEL_UNSELECTED = "модель не выбрана"

# The snapshot the money comes from. Reading the cache is offline by design —
# the renderer must never reach the network — and an override exists so a test
# or an operator can point the kernel at one named snapshot file.
CATALOG_FILE_ENV = "LHC_CATALOG_FILE"
CATALOG_CACHE_DIR_ENV = "LHC_MODELS_CACHE_DIR"
# A snapshot older than its own TTL is not a price list, it is a photograph of
# one: the plan stops quoting it and names why.
SNAPSHOT_STALE_NOTE = "снимок каталога устарел"

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
# table, so they cannot disagree about what a marker means. `⋯` is the queued
# marker the projected summary of `render` emits; `⏳` is the queued marker of
# the hand-written report. Both mean one state, and the projection is a report
# the same parser must read back.
GLYPH_STATUS = {
    "✅": STATUS_DONE,
    "🔄": STATUS_RUNNING,
    "⌛": STATUS_WAITING,
    "⏸": STATUS_DEFERRED,
    "⏳": STATUS_QUEUED,
    "⋯": STATUS_QUEUED,
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
    # The cost vocabulary of a leaf. `tier` is the canonical class the plan
    # kernel prices (`fast` or `frontier`); `model_class` is the older field the
    # live plans already carry and is read as a tier only when it holds one of
    # those two words. `complexity` is the size of the job as the Lead saw it,
    # `token_estimate` and `cost_usd` are what the leaf itself declares, and
    # `cost_source` says whether those numbers were measured or provisional —
    # money without that label is a number nobody stands behind.
    tier: str = ""
    complexity: str = ""
    token_estimate: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_source: str = ""
    result: str = ""
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    estimate_min: Optional[float] = None
    estimate_max: Optional[float] = None
    estimate_unknown_reason: str = ""
    # A leaf longer than the cap of the format is a real situation - the cost
    # kernel itself is one - but it must never pass silently: the leaf names in
    # its own words why it is deliberately larger, and only that named reason
    # lets it through the check.
    estimate_over_limit_reason: str = ""
    # What a leaf in the queue owes the report: why it cannot start yet, and
    # the planned start and finish. The format promises these three, so the
    # projection has to carry them.
    wait_reason: str = ""
    planned_start: str = ""
    planned_finish: str = ""
    actual_minutes: Optional[float] = None
    started_at: str = ""
    created_at: str = ""
    finished_at: str = ""
    blocker: str = ""
    blocker_details: dict[str, str] = field(default_factory=dict)
    note: str = ""
    wave: Optional[int] = None
    order: int = 0
    origin: str = ""
    # True when the line of the report itself named the leaf (the projected
    # report carries "- L04 · …"). A named id anchors the reconciliation; a
    # positional id is only the row number of the report.
    id_explicit: bool = False

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
        if "T" in self.started_at or "T" in self.finished_at:
            try:
                start_iso = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
                end_iso = datetime.fromisoformat(self.finished_at.replace("Z", "+00:00"))
                if start_iso.tzinfo is None or end_iso.tzinfo is None or end_iso < start_iso:
                    return None
                return (end_iso - start_iso).total_seconds() / 60
            except ValueError:
                return None
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

    @property
    def price_tier(self) -> tuple[str, str]:
        """The class the kernel prices, and the field it was read from.

        `tier` is the canonical name. `model_class` is the field the plans
        written before the cost kernel already carry, and it is honoured only
        when it holds one of the two tier words — a leaf whose model_class is
        a model name is not a class the kernel can price, and guessing a class
        out of a name is exactly the invention this table exists to prevent.
        """
        value = normalize(self.tier).lower()
        if value in TIER_WORDS:
            return value, "tier"
        legacy = normalize(self.model_class).lower()
        if legacy in TIER_WORDS:
            return legacy, "model_class"
        return "", ""


DEFAULT_GRAPH_TITLE = "LHC · граф задач"
# The attribution a plan report has no place for. The export writes it when the
# source graph knows it, and a refresh keeps it from the earlier graph.
# The cap of the format: a leaf is about fifteen minutes, and a longer job is
# two leaves. The collector (`lhc_plan_json.py`) owns the same number, and a
# leaf that records why it is deliberately larger is not a breach.
LEAF_ESTIMATE_CAP_MINUTES = 15

# The fields a leaf carries for the report: why it waits, and when it starts
# and finishes. The format promises all three, so the renderer has to carry
# them and show them.
ATTRIBUTION_FIELDS = (
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
    "result",
    "role",
    "acceptance",
    "description",
    "affected_files",
    "note",
    "blocker",
    "blocker_details",
    "estimate_unknown_reason",
    "estimate_over_limit_reason",
    "wait_reason",
    "planned_start",
    "planned_finish",
    "read_paths",
    "write_paths",
    "paths",
)
# A declared amount is a declared amount: `0` in a money or token field is a
# value the leaf wrote, not an empty cell, so a refresh must not overwrite it
# with the amount an older graph happened to carry.
NUMERIC_ATTRIBUTION_FIELDS = ("token_estimate", "cost_usd")


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
    acceptance_scenarios: list[str] = field(default_factory=list)
    current_progress: str = ""
    external_waits: str = ""
    leaves: list[Leaf] = field(default_factory=list)
    slots: int = 1
    # The money ceiling the owner set for this plan, in USD. `None` means no
    # ceiling was declared — that is not the same as a ceiling of zero, and the
    # page says «бюджет не задан» instead of comparing with an invented limit.
    budget_usd: Optional[float] = None
    declared_parallel: Optional[int] = None
    declared_leaves: Optional[int] = None
    declared_waves: Optional[int] = None
    declared_slots: Optional[int] = None
    updated_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    # Render context only; never written back into historical source plans.
    snapshot_at: str = ""
    plan_origin: dict[str, Any] = field(default_factory=dict)
    time_live: bool = True
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


def _elapsed_since(started_at: str, build_minutes: Optional[int]) -> Optional[float]:
    """Minutes from a leaf's start to the moment the projection was built.

    The time is taken from the fact of the build, not invented: a leaf that
    started at 14:12 and whose page is built at 15:00 has been going for
    forty-eight minutes. Without a start time there is nothing to measure, and
    the number stays absent rather than becoming a guess.
    """

    if build_minutes is None:
        return None
    started = parse_clock(started_at)
    if started is None:
        return None
    return float((build_minutes - started) % (24 * 60))


def now_clock() -> int:
    return datetime.now().hour * 60 + datetime.now().minute


# --------------------------------------------------------------------------
# parsing: canonical plan report
# --------------------------------------------------------------------------


HEADER_RE = re.compile(r"^\s*(Цель|Бизнес-результат|Что будет работать|Как проверим|Декомпозиция)\s*:\s*(.+?)\s*$")
# A leaf id is the letter L, digits, and optionally a letter suffix of any
# length: one executor may hold an "a" and a "b" leaf of the same number at the
# same time ("L02b", "L05a"), and the file leaves/L02b.json is the leaf "L02b".
# The suffix belongs to the id in both alphabets, so one shared class keeps
# every place that reads an id out of a report in step with what the renderer
# wrote: a pattern without the suffix silently truncates "L02b" to "L02", and
# then the report the tool generated itself cannot be read back.
ID_SUFFIX = r"[A-Za-zА-Яа-яЁё]*"
# The markers of the states come from one table, so the report, the live log
# and the dashboard cannot drift apart. The optional variation selector lets a
# report carry "⏸️" as well as "⏸". The projected report leads a line with a
# bullet and the id of its leaf ("  - L04 · ⋯ В очереди …"), and the parser
# reads exactly what the renderer writes: the id of the line anchors the
# reconciliation, and the glyph may stand after the bullet, not only at line
# start. A human writes the same leaf the other way round — the glyph first,
# then the id ("✅ L01 · …", "L01 ✅") — so the id is accepted on either side of
# the glyph and binds the line to that leaf exactly like the generated
# projection does. Whichever side carried it, the id is explicit; a line with
# no id on either side stays positional, and `check-plan` says so out loud.
LEAF_LINE_RE = re.compile(
    rf"^\s*(?:[-*]\s*)?(?P<id>[Ll]\d+{ID_SUFFIX})?(?:\s*[·•]\s*|\s+)?"
    rf"(?P<glyph>[{''.join(GLYPH_STATUS)}])\ufe0f?"
    rf"(?:\s+(?P<id_post>[Ll]\d+{ID_SUFFIX})(?:\s*[·•])?)?"
    rf"\s*(?P<rest>.*)$"
)
LABEL_RE = re.compile(r"\(([^)]*)\)")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
ESTIMATE_RE = re.compile(r"оценка\s+([^,;.·•]+)", re.IGNORECASE)
ACTUAL_RE = re.compile(r"(?:факт|прошло)\s+([^,;.·•]+)", re.IGNORECASE)
PARALLEL_RE = re.compile(rf"параллельно с листом\s+(L?\d+{ID_SUFFIX})", re.IGNORECASE)
# A join names every predecessor it waits for: "после листа 1 и листа 2",
# "после листов 1-3", "after leaf 1 and leaf 2". Cutting the phrase after the
# first number would drop the second parent and reorder the real execution.
AFTER_LEAF_RE = re.compile(
    r"(?:после|after)\s+(?:лист(?:а|ов|ьев|ы)?|leaves|leaf)\s+", re.IGNORECASE
)
AFTER_REGION_STOP_RE = re.compile(
    r"(?:потому|примерно|оценк|факт|прошло|закончим|начата|начнем|начнём|блокер"
    r"|отстаём|параллельн|слот|волн|минут|\bмин\b|час|because|since|approx"
    r"|estimate|finish|started|slot|wave|minute|[;.]|\d{1,2}:\d{2})",
    re.IGNORECASE,
)
AFTER_TOKEN_RE = re.compile(
    rf"(L?[0-9]+{ID_SUFFIX})(?:\s*[–—-]\s*(L?[0-9]+{ID_SUFFIX}))?", re.IGNORECASE
)
OVERRUN_RE = re.compile(r"отстаём потому что\s*:\s*(.+)$", re.IGNORECASE)
BLOCK_RE = re.compile(r"блокер\s*:\s*(.+)$", re.IGNORECASE)
# A leaf in the queue owes the report three things: why it cannot start yet,
# when it is planned to start, and when it is planned to finish. The canonical
# line names them in words - «потому что <почему нельзя параллельно>, примерно
# в 14:30 … закончим в 14:40» - and those words are the leaf's own
# `wait_reason`, `planned_start` and `planned_finish`. Read as plain times they
# would be taken for a work window, and a leaf that has not started would be
# reported as if it had.
PLANNED_START_RE = re.compile(r"примерно в\s*(\d{1,2}:\d{2})", re.IGNORECASE)
PLANNED_FINISH_RE = re.compile(r"закончим в\s*(\d{1,2}:\d{2})", re.IGNORECASE)
# The reason of a queued leaf. «отстаём потому что» belongs to the running
# leaf and keeps its own meaning, so it is not read as a wait reason.
WAIT_REASON_RE = re.compile(r"(?<!отстаём )потому что\s*:?\s*([^,]+)", re.IGNORECASE)
WAITING_REASON_RE = re.compile(r"жд[её]м\s+([^,]+?)(?:,\s*оценка|$)", re.IGNORECASE)
# The projected summary states the relations of a leaf in its own words:
# "зависит: L01, L02" and "параллельно: L03". The report is a projection, so
# reading the projection back is not a favour to the renderer — it is the same
# plan in the same table.
DEP_CELL_RE = re.compile(r"зависит:\s*([^·]+)", re.IGNORECASE)
PARALLEL_CELL_RE = re.compile(r"параллельно:\s*([^·]+)", re.IGNORECASE)
ID_TOKEN_RE = re.compile(rf"[Ll]\d+{ID_SUFFIX}")

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
    pending_parallel: list[tuple[int, str]] = []
    pending_after: list[tuple[int, str]] = []
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
            elif key == "Как проверим":
                graph.acceptance_scenarios.append(value.strip())
            elif key in ("Бизнес-результат", "Что будет работать"):
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
                # The explicit slot count is the resource bound; a claimed
                # parallelism that exceeds it is a divergence to name, not a
                # number to adopt as the bound.
                explicit_slots = _int_or_none(DECOMP_SLOTS_RE.search(value))
                graph.declared_slots = explicit_slots
                graph.slots = explicit_slots or graph.declared_parallel or 1
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
        glyph, rest = match.group("glyph"), match.group("rest").strip()
        if not rest:
            continue
        seen_leaf = True
        index = len(leaves)
        status = GLYPH_STATUS.get(glyph, STATUS_QUEUED)
        if rest.startswith("работаем "):
            rest = rest[len("работаем "):]
        label_match = LABEL_RE.search(rest)
        label = normalize(label_match.group(1)) if label_match else normalize(rest.split(",")[0])
        # The line names its leaf either before the glyph (the projected report
        # writes "- L04 · ⋯ …") or after it (a human writes "✅ L01 · …" or
        # "L01 ✅"); that id, not the row number, is the key of the
        # reconciliation. A report line that names no leaf on either side keeps
        # the positional id of its row, and `check-plan` flags that match.
        named_id = _dep_token_to_id(match.group("id") or match.group("id_post") or "")
        leaf = Leaf(
            id=named_id or f"L{index + 1:02d}",
            label=label,
            status=status,
            origin="report",
            id_explicit=bool(named_id),
            # The row number of the report. A line that names no leaf keeps
            # only its position, and the reconciliation says so out loud
            # instead of pretending the row number was a named id.
            order=index,
        )

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
        # A leaf in the queue has not started yet: «примерно в 14:30» and
        # «закончим в 14:40» are its plan, not a work window. Reading them as
        # `started_at`/`finished_at` would tell the reader that a leaf nobody
        # began has already run for ten minutes.
        planned = PLANNED_START_RE.search(rest)
        if planned:
            leaf.planned_start = planned.group(1)
        planned_finish = PLANNED_FINISH_RE.search(rest)
        if planned_finish:
            leaf.planned_finish = planned_finish.group(1)
        if leaf.status in (STATUS_QUEUED, STATUS_WAITING):
            work_window = re.sub(
                r"(примерно в|закончим в)\s*\d{1,2}:\d{2}", " ", rest, flags=re.IGNORECASE
            )
            times = TIME_RE.findall(work_window)
            reason = WAIT_REASON_RE.search(work_window)
            if reason:
                leaf.wait_reason = normalize(reason.group(1))
            elif leaf.status == STATUS_WAITING:
                waiting_reason = WAITING_REASON_RE.search(work_window)
                if waiting_reason:
                    leaf.wait_reason = normalize(waiting_reason.group(1))
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
            peer = _dep_token_to_id(parallel.group(1))
            if peer:
                pending_parallel.append((index, peer))
        parallel_cell = PARALLEL_CELL_RE.search(rest)
        if parallel_cell:
            for token in ID_TOKEN_RE.findall(parallel_cell.group(1)):
                peer = _dep_token_to_id(token)
                if peer and peer != leaf.id:
                    pending_parallel.append((index, peer))
        for dep in parse_after_phrase(rest):
            pending_after.append((index, dep))
        dep_cell = DEP_CELL_RE.search(rest)
        if dep_cell:
            for token in ID_TOKEN_RE.findall(dep_cell.group(1)):
                dep = _dep_token_to_id(token)
                if dep and dep != leaf.id:
                    pending_after.append((index, dep))
        leaves.append(leaf)

    if not leaves:
        return None

    for index, peer in pending_parallel:
        if peer not in leaves[index].parallel_with:
            leaves[index].parallel_with.append(peer)
    for index, dep in pending_after:
        if dep not in leaves[index].depends_on:
            leaves[index].depends_on.append(dep)

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
DEP_TOKEN_RE = re.compile(rf"[0-9]+{ID_SUFFIX}")


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
    result = re.search(r"\*\*(?:Бизнес-результат|Что будет работать):?\*\*\s*(.+)", text)
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
            if not re.fullmatch(rf"[0-9]+{ID_SUFFIX}", number):
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


def _dep_token_to_id(token: str) -> str:
    """One predecessor token of a phrase ("2", "1а", "L02", "L02b") as a leaf id."""
    match = re.fullmatch(rf"([Ll]?)([0-9]+)({ID_SUFFIX})", token)
    if not match:
        return ""
    _prefix, number, suffix = match.groups()
    return f"L{int(number):02d}{suffix}"


def parse_after_phrase(text: str) -> list[str]:
    """Every predecessor named by a "после листа ..." / "after leaf ..." phrase.

    A join waits for all of its parents, so the extraction reads the whole
    phrase: repeated names ("листа 1 и листа 2"), ranges ("листов 1-3"), bare
    second numbers ("и 2") and the English connectives. The phrase ends at the
    first schedule word or time, so estimates and clocks never become
    dependencies. Order is preserved and duplicates collapse.
    """
    found: list[str] = []
    for start in AFTER_LEAF_RE.finditer(text):
        tail = text[start.end():]
        stop = AFTER_REGION_STOP_RE.search(tail)
        region = tail[: stop.start()] if stop else tail
        for token in AFTER_TOKEN_RE.finditer(region):
            low, high = token.group(1), token.group(2)
            if high is not None:
                body = low.lstrip("Ll")
                digits = re.sub(r"[^0-9]", "", body)
                suffix = re.sub(r"[0-9]", "", body)
                try:
                    numbers = range(int(digits), int(re.sub(r"[^0-9]", "", high)) + 1)
                except ValueError:
                    continue
                for number in numbers:
                    found.append(f"{number:0{len(digits)}d}{suffix}")
            else:
                found.append(low)
    unique: list[str] = []
    for token in found:
        leaf_id = _dep_token_to_id(token)
        if leaf_id and leaf_id not in unique:
            unique.append(leaf_id)
    return unique


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
        range_match = re.match(
            rf"^([0-9]+{ID_SUFFIX})\s*[–—-]\s*([0-9]+{ID_SUFFIX})$", chunk
        )
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
    explicit = re.search(rf"лист[а-я]*\s+([0-9]+{ID_SUFFIX})", body, re.IGNORECASE)
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
    scenarios = document.get("acceptance_scenarios", [])
    if not isinstance(scenarios, list) or not all(isinstance(item, str) for item in scenarios):
        raise ValueError("acceptance_scenarios должно быть списком строк")
    graph.acceptance_scenarios = list(scenarios)
    graph.current_progress = str(document.get("current_progress") or "")
    graph.external_waits = str(document.get("external_waits") or "")
    graph.updated_at = str(document.get("updated_at") or "")
    graph.started_at = str(document.get("started_at") or "")
    graph.plan_origin = document.get('plan_origin') or {}
    graph.finished_at = str(document.get("finished_at") or "")
    graph.slots = int(document.get("slots") or 1)
    graph.declared_parallel = document.get("parallel")
    graph.declared_leaves = document.get("leaf_count")
    graph.declared_waves = document.get("wave_count")
    # A declared ceiling of zero is an owner's statement, not an absent ceiling:
    # only a missing or negative amount means «бюджет не задан».
    budget = _number(document.get("budget_usd"))
    graph.budget_usd = budget if budget is not None and budget >= 0 else None

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
            # A tier is a closed vocabulary: a leaf that writes `tier: "cheap"`
            # is not asking for a class the kernel knows, so the value is kept
            # in `model_class` (free text) and the cost path treats the leaf as
            # unclassed instead of guessing a band from a made-up word.
            tier=(str(task.get("tier") or "").strip().lower()
                  if str(task.get("tier") or "").strip().lower() in TIER_WORDS else ""),
            complexity=(str(task.get("complexity") or "").strip().upper()
                        if str(task.get("complexity") or "").strip().upper() in ("S", "M", "L")
                        else ""),
            cost_source=(str(task.get("cost_source") or "").strip().lower()
                         if str(task.get("cost_source") or "").strip().lower() in PROVENANCE_WORDS
                         else ""),
            result=normalize(str(task.get("result") or "")),
            depends_on=[str(item) for item in (task.get("depends_on") or [])],
            parallel_with=[str(item) for item in (task.get("parallel_with") or [])],
            started_at=str(task.get("started_at") or ""),
            created_at=str(task.get("created_at") or ""),
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
        leaf.estimate_over_limit_reason = normalize(str(task.get("estimate_over_limit_reason") or ""))
        leaf.wait_reason = normalize(str(task.get("wait_reason") or ""))
        leaf.planned_start = str(task.get("planned_start") or "")
        leaf.planned_finish = str(task.get("planned_finish") or "")
        actual = task.get("actual_minutes")
        if actual is not None:
            leaf.actual_minutes = _number(actual)
        tokens = _number(task.get("token_estimate"))
        if tokens is not None and tokens >= 0:
            leaf.token_estimate = int(tokens)
        cost = _number(task.get("cost_usd"))
        if cost is not None and cost >= 0:
            leaf.cost_usd = cost
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


def owner_key(leaf: Leaf) -> str:
    """Which executor holds this leaf — one worker, not one row of the report.

    A plan is parallel when *people* run it in parallel. One owner holding two
    leaves is one pair of hands, so counting report lines makes a plan look
    twice as parallel as it is, and the owner then reads a slot overflow that
    does not exist. The key falls back to the session, then to the leaf id, so a
    graph that names no owners does not collapse its leaves into one worker.
    """

    return normalize(leaf.owner or leaf.session or leaf.id).lower()


def wait_reasons(graph: Graph) -> dict[str, list[str]]:
    """Why each open leaf is not running, split the way the owner asks.

    «ждёт листа» and «ждёт исполнителя» are different problems: the first is
    answered by reordering the graph, the second by adding or freeing a worker.
    A blocked leaf is a third thing — it waits outside the plan — and stays in
    its own count.
    """

    by_id = graph.by_id()
    busy = {
        owner_key(leaf)
        for leaf in graph.leaves
        if leaf.status == STATUS_RUNNING
    }
    waiting_for_leaf: list[str] = []
    waiting_for_owner: list[str] = []
    ready: list[str] = []
    for leaf in graph.leaves:
        if leaf.status not in (STATUS_QUEUED, STATUS_WAITING):
            continue
        unfinished = [
            dep for dep in leaf.depends_on
            if dep in by_id and by_id[dep].status not in (STATUS_DONE, STATUS_DEFERRED)
        ]
        if unfinished:
            waiting_for_leaf.append(leaf.id)
        elif owner_key(leaf) in busy and (leaf.owner or leaf.session):
            # The leaf could start: nothing in the graph holds it, and the one
            # executor named for it is already busy with another leaf.
            waiting_for_owner.append(leaf.id)
        else:
            ready.append(leaf.id)
    return {
        "waiting_for_leaf": waiting_for_leaf,
        "waiting_for_owner": waiting_for_owner,
        "ready": ready,
    }


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
    # Without a live source the peak is counted by the executors, not by the
    # rows: one executor holding two leaves occupies one slot.
    if not use_live:
        active = [leaf for leaf in graph.leaves if leaf.status == STATUS_RUNNING]
        current_peak = len({
            (leaf.harness, leaf.session) if leaf.session else ("unknown", leaf.id)
            for leaf in active
        })
    slot_limit = graph.slots or 1
    # The same moment read by hands instead of rows: how many distinct
    # executors actually hold work, and whether the plan is over-subscribed at
    # that level. `current_parallel` stays the leaf count it always was — the
    # report projects it and `check-plan` reads it — while the owner view is
    # named separately.
    busy_owners = sorted({owner_key(leaf) for leaf in graph.leaves if leaf.status == STATUS_RUNNING})
    waits = wait_reasons(graph)
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

    metrics = {
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
        "busy_owners": len(busy_owners),
        "busy_owner_keys": busy_owners,
        "owner_overload": len(busy_owners) > slot_limit,
        "waiting_for_leaf_ids": waits["waiting_for_leaf"],
        "waiting_for_owner_ids": waits["waiting_for_owner"],
        "ready_unstarted_ids": waits["ready"],
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
        # The moment this projection is built. A running leaf is weighed
        # against its estimate here: the time that has passed since it started
        # is a fact of the build, and the build says how long ago that was.
        "build_minutes": now,
        "eta_overdue": bool(
            unfinished > 0 and eta_known and eta_from + int(round(eta_max)) < now
        ),
        "unfinished": unfinished,
        "schedule": schedule_max,
        "schedule_min": schedule_min,
        "pending": pending_max,
    }
    metrics["time_frame"] = plan_time_frame(graph, metrics)
    frame = metrics["time_frame"]
    # Keep the forecast card on the same absolute anchor as the time rail.
    if frame["anchor"]:
        anchor_dt = absolute_time(frame["anchor"])
        reference = absolute_time(frame["reference"])
        metrics["eta_anchor_clock"] = anchor_dt.isoformat(timespec="minutes")
        metrics["eta_anchor_idle_minutes"] = max(0, (reference - anchor_dt).total_seconds() / 60)
        metrics["eta_clock_min"] = frame["end_min"]
        metrics["eta_clock_max"] = frame["end"]
        metrics["eta_overdue"] = bool(frame["end"] and not frame["completed"]
                                       and absolute_time(frame["end"]) < reference)
    return metrics


def absolute_time(value: str) -> Optional[datetime]:
    """Only an absolute, timezone-aware source timestamp is a time anchor."""
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def plan_time_frame(graph: Graph, metrics: dict[str, Any]) -> dict[str, Any]:
    reference = absolute_time(graph.snapshot_at) or datetime.now(timezone.utc)
    snapshot = absolute_time(graph.snapshot_at) or absolute_time(graph.updated_at) or reference
    active = [leaf for leaf in graph.leaves if leaf.status != STATUS_DEFERRED]
    completed = bool(active) and all(leaf.status == STATUS_DONE for leaf in active)
    starts = [absolute_time(leaf.started_at) for leaf in graph.leaves]
    starts = [stamp for stamp in starts if stamp and stamp <= reference]
    start = absolute_time(graph.started_at) if graph.started_at else min(starts, default=None)
    if start and start > reference:
        start = None
    origin = absolute_time(graph.plan_origin.get('at', ''))
    start_source = 'recorded_start' if start else ''
    if origin and origin <= reference:
        # Keep earlier known work even if an imported/replaced file was born later.
        earlier = min([s for s in [start, *starts] if s], default=None)
        if earlier and earlier < origin:
            start, start_source = earlier, 'recorded_start'
        else:
            start, start_source = origin, graph.plan_origin.get('source', '')
    legacy = graph.started_at if re.fullmatch(r"\d{1,2}:\d{2}", graph.started_at) else ""
    if not graph.started_at and not start:
        legacy_starts = [leaf.started_at for leaf in graph.leaves
                         if re.fullmatch(r"\d{1,2}:\d{2}", leaf.started_at)]
        legacy = min(legacy_starts, default="")
    events = [absolute_time(graph.updated_at), absolute_time(graph.started_at)]
    events += [absolute_time(value) for leaf in graph.leaves
               for value in (leaf.started_at, leaf.finished_at)]
    anchor = max((stamp for stamp in events if stamp and stamp <= reference), default=None)
    anchor_source = 'event' if anchor else ''
    if anchor is None and origin and origin <= reference:
        # A new plan may have estimates and a frozen source origin before its
        # first progress event. Reuse that origin, never the render/poll time.
        anchor, anchor_source = origin, 'plan_origin'
    finish = absolute_time(graph.finished_at)
    if completed and not finish:
        finishes = [absolute_time(leaf.finished_at) for leaf in active]
        if all(finishes):
            finish = max(finishes)
            if any(absolute_time(leaf.started_at) and end < absolute_time(leaf.started_at)
                   for leaf, end in zip(active, finishes)):
                finish = None
    if finish and (finish > reference or (start and finish < start)):
        finish = None
    end_min = end = None
    if completed:
        end_min = end = finish
    elif anchor and metrics["eta_exact"]:
        try:
            end_min = anchor + timedelta(minutes=metrics["remaining_minutes_min"])
            end = anchor + timedelta(minutes=metrics["remaining_minutes_max"])
        except (OverflowError, ValueError):
            pass
    if end and start and end <= start:
        end_min = end = None
    if completed:
        end_label = "Завершено" if finish else "Завершено; время не записано"
    elif metrics["external_wait_unknown"]:
        end_label = "Прогноз неизвестен: срок внешнего ожидания не подтверждён"
    elif metrics["unknown_estimate_pending"]:
        end_label = "Прогноз частичный: есть задачи без оценки"
    elif not end:
        end_label = "Прогноз неизвестен: не записана дата начала или обновления плана"
    else:
        end_label = "Прогноз ≈"
    iso = lambda stamp: stamp.isoformat() if stamp else ""
    return {"start": iso(start), "start_source": start_source, "legacy_start": legacy, "end_min": iso(end_min),
            "end": iso(end), "anchor": iso(anchor), "anchor_source": anchor_source, "reference": iso(reference),
            "snapshot": iso(snapshot), "completed": completed, "live": graph.time_live,
            "end_label": end_label}


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


# --------------------------------------------------------------------------
# what a leaf costs: the price table of the plan kernel itself
# --------------------------------------------------------------------------

# The money a plan spends is computed here, from the leaf's own declaration and
# the catalog snapshot `lhc_models.py` caches. No price and no model name is
# written in this file: a plan that quotes a literal dollar is a plan that goes
# stale the day the catalog changes, and the whole point of the table is that a
# human can read the cost of a leaf before dispatching it without a model
# guessing.
#
# Three absences are named, never drawn as zero:
#   * no snapshot, or a snapshot older than its own TTL -> «цена не получена»;
#   * a leaf with no resolvable model -> «модель не выбрана»;
#   * a leaf with neither tokens nor a duration -> «цена не получена», because
#     there is nothing to multiply.

_MODELS_UNSET = object()
_MODELS_MODULE: Any = _MODELS_UNSET
# The catalog parse and the resolver scan are the two expensive steps, and both
# answer the same question for every leaf of the same class: memoize per
# process, so rendering a twenty-leaf plan costs one parse, not twenty.
_PRICE_MEMO: dict[tuple, dict] = {}
_ROUTE_MEMO: dict[tuple, dict] = {}


def models_module() -> Optional[Any]:
    """The pricing sibling, loaded once per process; `None` when it is absent."""

    global _MODELS_MODULE
    if _MODELS_MODULE is _MODELS_UNSET:
        _MODELS_MODULE = _load_sibling("lhc_models")
    return _MODELS_MODULE


def _snapshot_stamp(models: Any, path: Optional[str], directory: Optional[str]) -> str:
    """What the memo key is built from: the file, or "missing" when there is none."""

    if path:
        target = Path(path)
    else:
        base = Path(directory) if directory else models.default_cache_dir()
        target = base / getattr(models, "CACHE_FILE_NAME", "api.json")
    try:
        return str(target.stat().st_mtime_ns)
    except OSError:
        return "missing"


def _load_price_snapshot(models: Any, *, path: Optional[str], directory: Optional[str]) -> dict:
    """Read the cached catalog offline; never reach the network from a page."""

    try:
        catalog = models.load_catalog(path=path, cache_dir=directory, offline=True)
    except Exception as error:  # CatalogUnavailable, and any broken cache
        return {
            "ok": False,
            "reason_code": "no_snapshot",
            "reason": f"{PRICE_UNAVAILABLE}: под каталог нет сохранённого снимка ({error})",
        }
    meta = catalog.meta()
    return {
        "ok": True,
        "catalog": catalog,
        "measured": models.load_measured_tpm(),
        "snapshot": {
            "sha256": str(meta.get("sha256") or ""),
            "retrieved_at": str(meta.get("retrieved_at") or ""),
            "source": str(meta.get("source") or ""),
            "ttl_seconds": int(meta.get("ttl_seconds") or 0),
        },
    }


def price_source(
    *,
    catalog_path: Optional[str] = None,
    cache_dir: Optional[str] = None,
    now: Optional[float] = None,
) -> dict:
    """The snapshot the money comes from, or the honest reason there is none.

    A snapshot past its own TTL is not quoted: an old price list is a
    photograph of one, and a plan that reads it as current lies about the cost
    in whichever direction the catalog moved since.
    """

    models = models_module()
    if models is None:
        return {
            "ok": False,
            "reason_code": "no_backend",
            "reason": (
                f"{PRICE_UNAVAILABLE}: рядом нет lhc_models.py, "
                "и цену взять неоткуда"
            ),
        }
    path = catalog_path or os.environ.get(CATALOG_FILE_ENV) or None
    directory = cache_dir or os.environ.get(CATALOG_CACHE_DIR_ENV) or None
    clock = datetime.now().timestamp() if now is None else float(now)
    key = (str(path or ""), str(directory or ""), _snapshot_stamp(models, path, directory))
    stored = _PRICE_MEMO.get(key)
    if stored is None:
        stored = _load_price_snapshot(models, path=path, directory=directory)
        _PRICE_MEMO[key] = stored
    snapshot = dict(stored)
    if not snapshot.get("ok"):
        return snapshot
    catalog = snapshot["catalog"]
    age_minutes = max(0.0, (clock - catalog.retrieved_at) / 60.0)
    ttl_minutes = (catalog.ttl_seconds / 60.0) if catalog.ttl_seconds > 0 else None
    snapshot["age_minutes"] = age_minutes
    snapshot["ttl_minutes"] = ttl_minutes
    stale = ttl_minutes is not None and age_minutes > ttl_minutes
    snapshot["stale"] = stale
    if stale:
        return {
            "ok": False,
            "reason_code": "stale_snapshot",
            "reason": (
                f"{PRICE_UNAVAILABLE}: {SNAPSHOT_STALE_NOTE} — ему {fmt_minutes(age_minutes)}, "
                f"а срок жизни {fmt_minutes(ttl_minutes)}; обнови снимок каталога"
            ),
            "snapshot": snapshot["snapshot"],
            "age_minutes": age_minutes,
        }
    return snapshot


def _leaf_route(models: Any, catalog: Any, measured: dict, *, alias: str, tier: str) -> dict:
    """The resolver's answer for one (alias, tier) pair, memoized per process."""

    # The measured token-burn table is part of the answer - it decides the
    # rate behind the tokens - so its shape belongs in the memo key: a table
    # that changed between two leaves must not be answered from the first
    # leaf's route.
    stamp = tuple(sorted((name, entry.get("tokens_per_minute"))
                         for name, entry in (measured or {}).items()))
    key = (catalog.sha256, alias, tier, stamp)
    route = _ROUTE_MEMO.get(key)
    if route is None:
        # `tokens=0` asks for the route only: the money is computed per leaf
        # below, so a plan of twenty leaves of one class resolves once.
        route = models.leaf_estimate(
            catalog,
            model=alias or None,
            tier=tier or None,
            tokens=0,
            measured=measured,
        )
        _ROUTE_MEMO[key] = route
    return route


def _leaf_cost(leaf: Leaf, source: dict) -> dict[str, Any]:
    """What this leaf costs, with the label of every number behind it."""

    entry: dict[str, Any] = {
        "id": leaf.id,
        "state": "",
        "reason_code": "",
        "usd": None,
        "declared_usd": leaf.cost_usd,
        "declared_source": leaf.cost_source,
        "tokens": None,
        "tokens_source": "",
        "label": "",
        "tier": "",
        "tier_field": "",
        "model": "",
        "alias": leaf.model,
        "price_per_mtok": None,
        "tokens_per_minute": None,
        "tpm_label": "",
        "tpm_samples": 0,
        "match_note": "",
        "selection": "",
        "divergence_pct": None,
        "text": "",
    }
    if leaf.status == STATUS_DEFERRED:
        entry["state"] = "deferred"
        entry["text"] = "вне сметы · отложено владельцем"
        return entry
    if not source.get("ok"):
        entry["state"] = "catalog_unavailable"
        entry["reason_code"] = str(source.get("reason_code") or "no_snapshot")
        entry["text"] = PRICE_UNAVAILABLE
        return entry
    models = models_module()
    tier, tier_field = leaf.price_tier
    alias = (leaf.model or "").strip()
    entry["tier"] = tier
    entry["tier_field"] = tier_field
    if not alias and not tier:
        entry["state"] = "no_class"
        entry["reason_code"] = "no_model_declared"
        entry["text"] = f"{MODEL_UNSELECTED} · лист не назвал ни модель, ни класс"
        return entry
    route = _leaf_route(models, source["catalog"], source.get("measured") or {},
                        alias=alias, tier=tier)
    entry["selection"] = str(route.get("selection") or "")
    entry["match_note"] = str(route.get("match_note") or "")
    if not route.get("ok"):
        code = str(route.get("reason_code") or "model_not_resolved")
        entry["state"] = code
        entry["reason_code"] = code
        if code == "model_not_resolved":
            entry["text"] = (
                f"{MODEL_UNSELECTED} · объявленный алиас «{alias}» не найден в каталоге"
            )
        elif code == "price_unknown":
            entry["text"] = f"{PRICE_UNAVAILABLE} · каталог не несёт цены модели «{alias}»"
        elif code == "class_not_resolved":
            entry["text"] = f"{MODEL_UNSELECTED} · в каталоге нет прохода класса {tier}"
        else:
            entry["text"] = f"{MODEL_UNSELECTED} · класс {tier or alias} не разбирается"
        return entry
    price = route.get("price_per_mtok")
    entry["price_per_mtok"] = price
    entry["tokens_per_minute"] = route.get("tokens_per_minute")
    entry["tpm_label"] = str(route.get("tpm_label") or "")
    entry["tpm_samples"] = route.get("tpm_samples") or 0
    entry["model"] = f"{route.get('provider')}/{route.get('model_id')}"
    entry["tier"] = str(route.get("tier") or tier)
    tokens = leaf.token_estimate
    if tokens is not None:
        entry["tokens_source"] = "leaf-declared"
        # A token count the leaf declares is the worker's own measurement only
        # when the leaf says so; an unlabelled amount stays provisional, because
        # nobody stands behind it.
        entry["label"] = leaf.cost_source if leaf.cost_source in PROVENANCE_WORDS else "provisional"
    else:
        minutes = leaf.plan_minutes
        if minutes is None:
            entry["state"] = "no_duration"
            entry["reason_code"] = "no_duration"
            entry["text"] = (
                f"{PRICE_UNAVAILABLE} · нет ни объявленных токенов, ни оценки длительности"
            )
            return entry
        rate = route.get("tokens_per_minute") or 0
        tokens = int(round(float(minutes) * float(rate)))
        entry["tokens_source"] = "minutes-x-tpm"
        entry["label"] = entry["tpm_label"]
    entry["tokens"] = int(tokens)
    entry["usd"] = models.blend_usd(tokens, price)
    entry["state"] = "priced"
    return entry


def _round_money(models: Any, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if models is not None and hasattr(models, "round_money"):
        return float(models.round_money(value))
    return round(value, 2)


def fmt_usd(value: Optional[float]) -> str:
    """Dollars as a plan reads them: cents, or what is left of a cent."""

    if value is None:
        return "—"
    if value >= 0.01:
        return f"${value:.2f}"
    return f"${value:.4f}"


def compute_cost(graph: Graph, *, source: Optional[dict] = None) -> dict[str, Any]:
    """Per-leaf money, the plan total, and the frontier share of the dollars."""

    models = models_module()
    if source is None:
        # A plan whose leaves name neither a model nor a class has nothing to
        # price: reading a 5 MB catalog to conclude «модель не выбрана» twenty
        # times over would be a waste, and the conclusion is the same without it.
        wants_price = any(
            (leaf.model or "").strip() or leaf.price_tier[0] for leaf in graph.leaves
        )
        if wants_price:
            source = price_source()
        else:
            source = {"ok": True, "catalog": None, "measured": {}, "snapshot": {},
                      "age_minutes": None}
    entries: dict[str, dict[str, Any]] = {}
    for leaf in graph.leaves:
        entries[leaf.id] = _leaf_cost(leaf, source)
    priced = [entry for entry in entries.values() if entry.get("usd") is not None]
    unpriced = [
        leaf.id
        for leaf in graph.leaves
        if entries[leaf.id]["state"] not in ("priced", "deferred")
    ]
    total = _round_money(models, sum(entry["usd"] for entry in priced))
    frontier = _round_money(
        models, sum(entry["usd"] for entry in priced if entry.get("tier") == "frontier")
    )
    fast = _round_money(
        models, sum(entry["usd"] for entry in priced if entry.get("tier") == "fast")
    )
    unfinished_total = _round_money(
        models,
        sum(
            entries[leaf.id]["usd"]
            for leaf in graph.leaves
            if entries[leaf.id].get("usd") is not None
            and leaf.status not in (STATUS_DONE, STATUS_DEFERRED)
        ),
    )
    declared_values = [
        leaf.cost_usd for leaf in graph.leaves if leaf.cost_usd is not None
    ]
    declared_total = (
        _round_money(models, sum(declared_values)) if declared_values else None
    )
    # The label of every money the plan shows. A sum of dollars is as
    # trustworthy as its weakest part, so the plan-level number carries the
    # label of the leaves it was made of: `measured` when every leaf stands
    # on a measurement, `provisional` when none does, and the mix itself
    # when the leaves differ.
    labels = sorted({entry["label"] for entry in priced if entry.get("label")})
    tier_labels: dict[str, str] = {}
    for entry in priced:
        tier = str(entry.get("tier") or "")
        label = str(entry.get("label") or "")
        if not tier or not label:
            continue
        seen = tier_labels.get(tier)
        tier_labels[tier] = label if seen is None else (
            label if seen == label else f"{seen}+{label}")
    plan_label = "+".join(labels) if labels else ""
    share = None
    if total and frontier is not None:
        share = round(100.0 * frontier / total, 1)
    divergent: list[str] = []
    for leaf in graph.leaves:
        entry = entries[leaf.id]
        declared = entry.get("declared_usd")
        computed = entry.get("usd")
        if declared and computed is not None:
            drift = 100.0 * (computed - declared) / declared
            entry["divergence_pct"] = round(drift, 1)
            if abs(drift) > 20.0:
                divergent.append(leaf.id)
        elif declared == 0 and computed:
            entry["divergence_pct"] = None
            divergent.append(leaf.id)
    return {
        "available": bool(source.get("ok")),
        "reason_code": "" if source.get("ok") else str(source.get("reason_code") or ""),
        "reason": "" if source.get("ok") else str(source.get("reason") or ""),
        "snapshot": (source.get("snapshot") or {}) if isinstance(source, dict) else {},
        "age_minutes": source.get("age_minutes"),
        "leaves": entries,
        "priced_count": len(priced),
        "leaf_count": len(graph.leaves),
        "unpriced_ids": unpriced,
        # Which number the owner is reading: a leaf that names its model is
        # priced on that model, a leaf that names only its class is priced on
        # whatever route the class policy picks today. The second is a class
        # price, not the price of the executor, and the plan must say so.
        "declared_model_ids": [
            leaf.id for leaf in graph.leaves if entries[leaf.id].get("selection") == "declared-model"
        ],
        "class_priced_ids": [
            leaf.id for leaf in graph.leaves if entries[leaf.id].get("selection") == "tier-suggested"
        ],
        "tier_from_model_class_ids": [
            leaf.id for leaf in graph.leaves if entries[leaf.id].get("tier_field") == "model_class"
        ],
        "single_sample_tpm_ids": [
            leaf.id
            for leaf in graph.leaves
            if entries[leaf.id].get("state") == "priced"
            and entries[leaf.id].get("tpm_label") == "measured"
            and (entries[leaf.id].get("tpm_samples") or 0) <= 1
        ],
        "frontier_on_small_ids": [
            leaf.id
            for leaf in graph.leaves
            if leaf.price_tier[0] == "frontier" and leaf.complexity == "S"
        ],
        "unsource_money_ids": [
            leaf.id
            for leaf in graph.leaves
            if leaf.cost_usd is not None and not leaf.cost_source
        ],
        "total_usd": total,
        "unfinished_usd": unfinished_total,
        "frontier_usd": frontier,
        "fast_usd": fast,
        "frontier_share_pct": share,
        # The label of the plan-level money, and the label of each class's
        # money: a number without a label next to it is a number a human
        # reads as a fact.
        "label": plan_label,
        "labels": labels,
        "tier_labels": tier_labels,
        "frontier_label": tier_labels.get("frontier", plan_label),
        "fast_label": tier_labels.get("fast", plan_label),
        "frontier_count": sum(1 for entry in priced if entry.get("tier") == "frontier"),
        "fast_count": sum(1 for entry in priced if entry.get("tier") == "fast"),
        "budget_usd": graph.budget_usd,
        "over_budget": bool(graph.budget_usd is not None and (total or 0) > graph.budget_usd),
        "declared_total_usd": declared_total,
        "class_priced_usd": _round_money(
            models,
            sum(
                entry["usd"]
                for entry in priced
                if entry.get("selection") == "tier-suggested"
            ),
        ),
        "divergent_ids": divergent,
        "tpm_labels": {
            entry["tier"]: entry["label"]
            for entry in priced
            if entry.get("tier") and entry.get("tokens_source") == "minutes-x-tpm"
        },
        "tpm_rates": {
            entry["tier"]: entry["tokens_per_minute"]
            for entry in priced
            if entry.get("tier") and entry.get("tokens_per_minute")
        },
    }


def cost_lines(cost: dict[str, Any]) -> list[str]:
    """The plan-level money, in the words the report and the page both show."""

    if not cost.get("available"):
        return [str(cost.get("reason") or f"{PRICE_UNAVAILABLE}: смета не рассчитана")]
    priced = cost.get("priced_count") or 0
    if priced:
        parts = [
            f"Смета плана: {fmt_usd(cost['total_usd'])}"
            + (f" ({cost['label']})" if cost.get("label") else "")
            + f" за {priced} из {cost['leaf_count']} листьев"
        ]
    else:
        # No leaf could be priced: the plan does not cost zero dollars, it
        # costs an unknown number of dollars.
        parts = [
            f"Смета плана: нет посчитанных денег — {cost['leaf_count']} листьев без цены"
        ]
    share = cost.get("frontier_share_pct")
    if share is not None:
        frontier_label = cost.get("frontier_label") or cost.get("label") or ""
        parts.append(
            f"frontier {fmt_usd(cost['frontier_usd'])}"
            + (f" ({frontier_label})" if frontier_label else "")
            + f" — {share}% всех долларов плана"
        )
    else:
        parts.append("доля frontier не вычисляется: нет посчитанных денег")
    if priced:
        parts.append(
            f"остатку к запуску {fmt_usd(cost['unfinished_usd'])}"
            + (f" ({cost['label']})" if cost.get("label") else "")
        )
    else:
        parts.append("остатку к запуску: нет посчитанных денег")
    if cost.get("class_priced_ids"):
        parts.append(
            f"из них {fmt_usd(cost.get('class_priced_usd'))}"
            + (f" ({cost['label']})" if cost.get("label") else "")
            + f" — цена класса для {len(cost['class_priced_ids'])} листьев без объявленной модели"
        )
    if cost.get("budget_usd") is not None:
        parts.append(
            f"бюджет {fmt_usd(cost['budget_usd'])}"
            + (" — превышен" if cost.get("over_budget") else "")
        )
    else:
        parts.append("бюджет не задан")
    if cost.get("declared_total_usd") is not None:
        parts.append(f"листья объявили {fmt_usd(cost['declared_total_usd'])}")
    if cost.get("unpriced_ids"):
        parts.append(
            f"без цены {len(cost['unpriced_ids'])}: " + ", ".join(cost["unpriced_ids"])
        )
    snapshot = cost.get("snapshot") or {}
    age = cost.get("age_minutes")
    provenance = ", ".join(
        f"{tier} {label}" for tier, label in sorted((cost.get("tpm_labels") or {}).items())
    )
    tail = []
    if snapshot.get("sha256"):
        tail.append(f"снимок {str(snapshot['sha256'])[:12]} от {snapshot.get('retrieved_at')}")
    if age is not None:
        tail.append(f"возраст {fmt_minutes(age)}")
    if provenance:
        tail.append(f"скорость токенов: {provenance}")
    if tail:
        parts.append(" · ".join(tail))
    return parts


def cost_panel_html(cost: dict[str, Any]) -> str:
    """The plan's money as one screen block: total, class share, provenance."""

    if not cost.get("available"):
        return (
            '<div class="panel panel-cost" id="lhc-cost">'
            "<h2>Смета плана</h2>"
            '<ul class="facts">'
            f"<li><b>Цены</b>: {escape(str(cost.get('reason') or PRICE_UNAVAILABLE))}</li>"
            f"<li><b>Что делать</b>: получить снимок каталога через "
            f"<code>lhc_models.py snapshot</code>, затем перерисовать план</li>"
            "</ul></div>"
        )
    priced = cost.get("priced_count") or 0
    if priced:
        facts = [
            f"<li><b>Весь план</b>: {escape(fmt_usd(cost['total_usd']))}"
            + (f" <span class='cell-sub'>{escape(cost['label'])}</span>"
               if cost.get("label") else "")
            + f" · цена посчитана для {priced} из {cost['leaf_count']} листьев</li>"
        ]
        facts.append(
            f"<li><b>Остатку к запуску</b>: {escape(fmt_usd(cost['unfinished_usd']))}"
            + (f" <span class='cell-sub'>{escape(cost['label'])}</span>"
               if cost.get("label") else "")
            + " (завершённые и отложенные листья не в этой строке)</li>"
        )
    else:
        facts = [
            f"<li><b>Весь план</b>: нет посчитанных денег · цена посчитана для 0 "
            f"из {cost['leaf_count']} листьев</li>",
            "<li><b>Остатку к запуску</b>: нет посчитанных денег</li>",
        ]
    share = cost.get("frontier_share_pct")
    facts.append(
        f"<li><b>Класс frontier</b>: {escape(fmt_usd(cost['frontier_usd']))}"
        + (f" <span class='cell-sub'>{escape(cost.get('frontier_label') or '')}</span>"
           if cost.get("frontier_label") else "")
        + (f" — {share}% всех долларов плана" if share is not None else "")
        + f" · {cost['frontier_count']} листьев"
        + f" · fast {escape(fmt_usd(cost['fast_usd']))}"
        + (f" <span class='cell-sub'>{escape(cost.get('fast_label') or '')}</span>"
           if cost.get("fast_label") else "")
        + f" · {cost['fast_count']} листьев</li>"
    )
    if cost.get("class_priced_ids"):
        facts.append(
            f"<li><b>Цена класса против цены модели</b>: "
            f"{escape(fmt_usd(cost.get('class_priced_usd')))} из "
            f"{escape(fmt_usd(cost.get('total_usd')))} посчитано по самому дешёвому проходу "
            f"класса для {len(cost['class_priced_ids'])} листьев, которые не назвали свою "
            "модель; остальные посчитаны по объявленному алиасу</li>"
        )
    if cost.get("budget_usd") is not None:
        facts.append(
            f"<li><b>Бюджет плана</b>: {escape(fmt_usd(cost['budget_usd']))} · "
            + ("превышен" if cost.get("over_budget") else "в пределах")
            + "</li>"
        )
    else:
        facts.append("<li><b>Бюджет плана</b>: не задан</li>")
    if cost.get("divergent_ids"):
        facts.append(
            "<li><b>Листья спорят с каталогом</b>: "
            f"{escape(', '.join(cost['divergent_ids']))} — объявленная стоимость "
            "отличается от посчитанной больше чем на 20%</li>"
        )
    if cost.get("unpriced_ids"):
        missing = []
        for leaf_id in cost["unpriced_ids"]:
            entry = cost["leaves"].get(leaf_id, {})
            missing.append(f"{leaf_id} — {escape(str(entry.get('text') or PRICE_UNAVAILABLE))}")
        facts.append(
            "<li><b>Без цены</b>: " + "; ".join(missing) + "</li>"
        )
    snapshot = cost.get("snapshot") or {}
    provenance = []
    if snapshot.get("sha256"):
        provenance.append(
            f"снимок {escape(str(snapshot['sha256'])[:12])} от {escape(str(snapshot.get('retrieved_at')))}"
        )
    age = cost.get("age_minutes")
    if age is not None:
        provenance.append(f"возраст {escape(fmt_minutes(age))}")
    for tier in ("fast", "frontier"):
        rate = (cost.get("tpm_rates") or {}).get(tier)
        if rate:
            label = (cost.get("tpm_labels") or {}).get(tier) or "provisional"
            provenance.append(
                f"{tier}: {int(rate):,} ток/мин ({escape(label)})".replace(",", " ")
            )
    if provenance:
        facts.append("<li><b>Откуда числа</b>: " + " · ".join(provenance) + "</li>")
    return (
        '<div class="panel panel-cost" id="lhc-cost">'
        "<h2>Смета плана</h2>"
        '<ul class="facts">' + "".join(facts) + "</ul></div>"
    )


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
    if graph.started_at or graph.finished_at:
        payload.append(["plan_times", graph.started_at, graph.finished_at])
    if graph.plan_origin:
        payload.append(['plan_origin', graph.plan_origin])
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
    # The money of the plan, computed once for the whole page.
    cost = _cost_of(graph, metrics)

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
    remaining_label = "Известная часть работы" if partly_unknown else "Остаток по плану"
    remaining_value = (
        f"от {fmt_minutes(metrics['remaining_minutes_min'])} "
        f"до {fmt_minutes(metrics['remaining_minutes_max'])}"
    )
    if metrics['remaining_minutes_min'] == metrics['remaining_minutes_max']:
        remaining_value = fmt_minutes(metrics['remaining_minutes_max'])
    remaining_hint = "Оценка оставшихся работ"
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
    import lhc_plan_ui
    eta_range = _eta_range_text(metrics)
    frame = metrics["time_frame"]
    if not frame["end"]:
        eta_range = "Срок неизвестен"
        eta_hint = frame["end_label"]
    else:
        eta_range = ("Завершено: " if frame["completed"] else "≈ ") + lhc_plan_ui.display_time(frame["end"])
        if frame["end_min"] != frame["end"]:
            eta_range = "≈ " + lhc_plan_ui.display_time(frame["end_min"]) + " — " + lhc_plan_ui.display_time(frame["end"])
    if not frame["anchor"]:
        eta_hint = (("отсчёт от последнего события " + metrics["eta_anchor_clock"] + " · дата не записана; ")
                    if metrics["eta_anchor_clock"] else "") + frame["end_label"]
    elif not frame["completed"]:
        eta_hint = ("Отсчёт от начала плана " if frame.get('anchor_source') == 'plan_origin'
                    else "Оценка по состоянию на ") + lhc_plan_ui.display_time(frame["anchor"])
    if metrics['unfinished'] == 0:
        eta_range = "Работы по плану завершены"
        eta_hint = ("Фактический финиш: " + lhc_plan_ui.display_time(frame["end"])) if frame["end"] else "Фактический финиш не зафиксирован"
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
         f"{peak_hint} · занятых исполнителей {metrics['busy_owners']}"
         + (" — больше, чем слотов" if metrics["owner_overload"] else ""),
         STATUS_RUNNING, False, "parallel"),
        (remaining_label, remaining_value, remaining_hint, STATUS_WAITING, False, "remaining"),
        ("Прогноз финиша", eta_range or "Срок неизвестен",
         eta_hint, STATUS_DONE, False, "forecast"),
        ("Усилие", effort_value, effort_hint, STATUS_QUEUED, False, "effort"),
    ]
    priority = {key: n for n, key in enumerate(("remaining", "forecast", "parallel", "unfinished", "done", "running", "blocked", "queued", "deferred", "effort"))}
    cards.sort(key=lambda card: priority[card[-1]])
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
    # Keep the four decision cards on the first screen, on every viewport.
    secondary_at = card_html.index('<div class="kpi kpi-tile" data-tile="done"')
    secondary_cards = card_html[secondary_at:]
    card_html = card_html[:secondary_at]
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
        if count:
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
        f'<div class="progress-strip-bar" aria-label="Распределение задач по статусам">{"".join(segments)}</div>'
        f'<div class="legend">{legend}</div>'
        + lhc_plan_ui.time_rail(metrics["time_frame"])
        +
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
        # The time a running leaf has been going, measured at the moment this
        # page is built. It is a fact of the build, not a measured effort: the
        # leaf declares when it started and the build says how long ago that was.
        elapsed_at_build = (
            _elapsed_since(leaf.started_at, metrics.get("build_minutes"))
            if leaf.status == STATUS_RUNNING
            else None
        )
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
        # What the leaf costs, which model of the catalog that price belongs to,
        # and the label of the number. An absent price is named, never drawn as
        # a zero that reads like a cheap task.
        entry = cost["leaves"].get(leaf.id, {})
        if entry.get("state") == "priced":
            money_dd = (
                f"<dt>Стоимость</dt><dd>{escape(fmt_usd(entry['usd']))} "
                f"<span class='cell-sub'>{escape(entry['label'])}</span></dd>"
                f"<dt>Модель каталога</dt><dd>{escape(entry['model'])}"
                + (f" <span class='cell-sub'>класс {escape(entry['tier'])}"
                   + (f" из поля {escape(entry['tier_field'])}" if entry.get("tier_field") else "")
                   + "</span>" if entry.get("tier") else "")
                + "</dd>"
                f"<dt>Токены</dt><dd>{int(entry['tokens']):,} "
                f"<span class='cell-sub'>"
                f"{'объявлены листом' if entry['tokens_source'] == 'leaf-declared' else 'минуты × скорость токенов'}</span></dd>"
            ).replace(",", " ")
            if entry.get("match_note"):
                money_dd += f"<dt>Как каталог понял алиас</dt><dd>{escape(entry['match_note'])}</dd>"
            if entry.get("divergence_pct") is not None:
                money_dd += (
                    f"<dt>Объявлено листом</dt><dd>{escape(fmt_usd(entry['declared_usd']))}"
                    f" <span class='cell-sub'>расхождение {entry['divergence_pct']}%</span></dd>"
                )
        elif leaf.status == STATUS_DEFERRED:
            money_dd = "<dt>Стоимость</dt><dd>вне сметы · лист отложен владельцем</dd>"
        else:
            money_dd = (
                f"<dt>Стоимость</dt><dd class='plan-none'>"
                f"{escape(entry.get('text') or PRICE_UNAVAILABLE)}</dd>"
            )
            if leaf.cost_usd is not None:
                money_dd += (
                    f"<dt>Объявлено листом</dt><dd>{escape(fmt_usd(leaf.cost_usd))}"
                    + (f" <span class='cell-sub'>{escape(leaf.cost_source)}</span>"
                       if leaf.cost_source else "")
                    + "</dd>"
                )
        details = (
            f"<dl class='task-details'><dt>Код</dt><dd>{escape(leaf.id)}</dd>"
            + (f"<dt>Описание задачи</dt><dd>{escape(leaf.description)}</dd>" if leaf.description else "")
            + (f"<dt>Ожидаемый результат</dt><dd>{escape(leaf.acceptance)}</dd>" if leaf.acceptance else "")
            + (f"<dt>Затрагиваемые файлы</dt><dd>{escape(', '.join(leaf.affected_files))}</dd>" if leaf.affected_files else "")
            + (f"<dt>Примечание</dt><dd>{escape(leaf.note)}</dd>" if leaf.note else "")
            + (
                f"<dt>Результат исполнителя</dt><dd>{escape(leaf.result)}</dd>"
                if leaf.result else ""
            )
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
            + money_dd
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
            # A leaf in the queue owes the report three things: why it cannot
            # start yet, when it is planned to start and when it is planned to
            # finish. A queued leaf without a reason says so: the format does
            # not go silent about a wait nobody explained.
            + (
                f"<dt>Почему в очереди</dt><dd>"
                + escape(leaf.wait_reason or "причина не названа")
                + "</dd>"
                + (f"<dt>Начнём по плану</dt><dd>{escape(leaf.planned_start)}</dd>" if leaf.planned_start else "")
                + (f"<dt>Закончим по плану</dt><dd>{escape(leaf.planned_finish)}</dd>" if leaf.planned_finish else "")
                if leaf.status in (STATUS_QUEUED, STATUS_WAITING)
                else ""
            )
            # A running leaf is weighed against its estimate at the moment the
            # page is built: the time that has passed is a fact of the build,
            # not a measured effort.
            + (
                f"<dt>Прошло на момент сборки</dt><dd>{escape(fmt_minutes(elapsed_at_build))}"
                + (
                    f" <span class='cell-sub'>отстаём: оценка {escape(leaf.duration_label)}</span>"
                    if elapsed_at_build is not None
                    and leaf.estimate_max is not None
                    and elapsed_at_build > leaf.estimate_max + 0.01
                    else ""
                )
                + "</dd>"
                if elapsed_at_build is not None
                else ""
            )
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
        # The cost of one leaf belongs on the row: the owner decides to
        # dispatch from this line, not from a page they have to open first.
        entry = cost["leaves"].get(leaf.id, {})
        if entry.get("state") == "priced":
            meta_parts.append(
                f"стоимость: {fmt_usd(entry['usd'])} · {entry['tier']} · {entry['label']}"
            )
        elif leaf.status != STATUS_DEFERRED:
            meta_parts.append(f"стоимость: {entry.get('text') or PRICE_UNAVAILABLE}")
        # What a leaf in the queue waits for belongs on the row: the owner reads
        # the plan in the open, not in a dialog. A queued leaf without a reason
        # says so here rather than passing in silence.
        if leaf.status in (STATUS_QUEUED, STATUS_WAITING):
            meta_parts.append(f"ждёт: {leaf.wait_reason or 'причина не названа'}")
            if leaf.planned_start:
                meta_parts.append(f"начнём {leaf.planned_start}")
            if leaf.planned_finish:
                meta_parts.append(f"закончим {leaf.planned_finish}")
        if elapsed_at_build is not None:
            meta_parts.append(f"прошло {fmt_minutes(elapsed_at_build)} на момент сборки")
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

    # The cap of the format, named on the page itself: a leaf over fifteen
    # minutes is two leaves, and a plan that carries one says so instead of
    # looking like a plan whose leaves are all short.
    cap_html = ""
    cap_breaches = [item for item in estimate_cap_findings(graph) if item["breach"]]
    if cap_breaches:
        items = "".join(
            f"<li>{escape(item['id'])}: оценка {escape(fmt_minutes(item['minutes']))} "
            f"при пределе {item['cap']} мин — "
            "разбейте лист на два либо запишите в листе estimate_over_limit_reason"
            "</li>"
            for item in cap_breaches
        )
        cap_html = (
            "<div class='hint' id='lhc-estimate-cap'><b>Превышен предел оценки листа "
            f"({LEAF_ESTIMATE_CAP_MINUTES} мин)</b>: {len(cap_breaches)} листьев. "
            "Лист длиннее предела — это два листа. "
            "<ul>" + items + "</ul></div>"
        )

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
        heading = "Что будет работать" if index == 0 else f"Что будет работать · {index + 1}"
        why_cards.append(
            f'<article class="brief-card brief-result"><h2>{escape(heading)}</h2>'
            f"<p>{escape(result)}</p></article>"
        )
    if graph.current_progress:
        detail_cards.append(
            f'<article class="brief-card"><h2>Что уже сделано</h2>'
            f"<p>{escape(graph.current_progress)}</p></article>"
        )
    if graph.external_waits:
        detail_cards.append(
            f'<article class="brief-card brief-wait"><h2>Внешние ожидания</h2>'
            f"<p>{escape(graph.external_waits)}</p></article>"
        )
    why_html = f'<div class="brief brief-why">{"".join(why_cards)}</div>' if why_cards else ""
    scenarios = ''.join(f'<li>{escape(item)}</li>' for item in graph.acceptance_scenarios)
    why_html += '<article class="panel acceptance-scenarios"><h2>Как проверим</h2>' + (f'<ul>{scenarios}</ul>' if scenarios else '<p>Сценарии проверки ещё не описаны</p>') + '</article>'
    why_html += '<p class="hint">Это декларация плана. Статус задач сам по себе не подтверждает приёмку результата.</p>'
    brief_html = f'<div class="brief">{"".join(detail_cards)}</div>' if detail_cards else ""
    why_panel = ""
    if why_html:
        why_panel = (
            '<details class="panel brief-details brief-why-details" open>\n'
            "  <summary>Цель и результат</summary>\n"
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
            '<div class="sub">' + (f'План обновлён {escape(graph.updated_at.replace("T", " "))}'
                                  if graph.updated_at else 'Дата обновления не записана') + '</div>'
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
        secondary_cards=secondary_cards,
        legend=legend,
        brief=brief_html,
        brief_details_open=" open" if graph.current_progress else "",
        why_panel=why_panel,
        cost=cost_panel_html(cost),
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
        estimate_cap=cap_html,
        total=total,
    )

    # The page keeps itself in sync with the file it was built from: a plan
    # that changed a second ago is visible without a reload. The rendering
    # stays in Python; the page only swaps in what Python rendered.
    try:
        html = live_module().inject_live(html)
    except Exception:  # pragma: no cover - a page without the poller is still a page
        pass
    import lhc_plan_ui
    return lhc_plan_ui.decorate(html)


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
{header}
<!-- plan-revisions -->
<main id="plan-content">
<section id="dashboard" class="plan-section" aria-label="Дашборд">
{progress_strip}
<p class="hint acceptance-note">Прогресс задач не означает приёмку пользовательского результата.</p>
<div class="kpis" id="lhc-state">{cards}</div>
<section class="panel status-details"><h2>Статусы задач и усилие</h2><div class="kpis secondary-kpis">{secondary_cards}</div></section>

<div class="tile-card" id="lhc-tile-card" hidden></div>
{tile_island}

<div class="panel panel-now">
  {now}
</div>

<div class="panel panel-blocking" id="lhc-blocking">
  <h2>Что блокирует</h2>
  {blocking}
</div>
</section>
<section id="outcome" class="plan-section" aria-label="Цель и результат">
{why_panel}
<details class="panel brief-details"{brief_details_open}>
  <summary>Текущий факт и внешние ожидания</summary>
  {brief}
</details>

{evidence_fold}
{product_plan}
</section>
<section id="work-plan" class="plan-section" aria-label="План работ">
<div class="panel panel-gantt" id="lhc-plan-gantt"{plan_gantt_hidden}>
  <h2>Гант · листья и параллельные волны</h2>
  {gantt_note}
  <div class="gantt"><div class="gantt-inner">
    <div class="gantt-axis-row"><div class="gantt-axis-spacer"></div><div class="gantt-axis">{axis}</div></div>
    {gantt}
  </div></div>
</div>
</section>
<section id="comparison" class="plan-section" aria-label="План и факт">
<!-- plan-comparison -->
<p class="comparison-empty panel">Сравнение ревизий доступно в опубликованном плане. Этот файл содержит один снимок.</p>
{cost}
</section>
<section id="tasks" class="plan-section" aria-label="Задачи">
  <div class="panel panel-leaves" id="lhc-leaves">
    <h2>Задачи</h2>
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
</section>
<section id="history" class="plan-section" aria-label="История">
<!-- plan-publication -->
<p class="snapshot-note">{snapshot}</p>
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
      {estimate_cap}
    </div>
    <div class="panel journal-fold" id="lhc-journal">
      <details>
        <summary><h2>Журнал изменений</h2></summary>

      <h2>Журнал изменений</h2>
      {live}

      </details>
    </div>
  </div>
</section>
</main>
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
# the paper version of the plan
# --------------------------------------------------------------------------

# The paper version is its own document, not the dashboard with the clicks
# taken away: a dashboard is a working surface, and a sheet of paper is not.
# So the print sheet carries the same graph and the same numbers, laid out for
# A4 with a page break per wave, and it references nothing outside the file —
# a sheet that waits for a font server prints differently on the next machine.
PRINT_CSS = """\
@page { size: A4 portrait; margin: 14mm 12mm 16mm; }
@page :first { margin-top: 12mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 10pt;
  line-height: 1.35;
  color: #16181d;
  background: #fff;
}
h1 { font-size: 17pt; margin: 0 0 2mm; }
h2 { font-size: 13pt; margin: 0 0 2mm; }
p { margin: 0 0 2mm; }
ul { margin: 0 0 2mm; padding-left: 5mm; }
table { width: 100%; border-collapse: collapse; margin-bottom: 4mm; }
th, td { border: 1px solid #b9bec7; padding: 3px 5px; text-align: left; vertical-align: top; }
th { background: #eef1f5; font-weight: 600; }
tr { break-inside: avoid; page-break-inside: avoid; }
.cover { break-after: page; page-break-after: always; }
.wave { break-before: page; page-break-before: always; }
.wave.first { break-before: avoid; page-break-before: avoid; }
.kpis td { width: 25%; }
.muted { color: #4a4f58; }
.small { font-size: 9pt; }
"""


def _print_leaf_state(leaf: Leaf, metrics: dict[str, Any]) -> str:
    """What the paper says about the state of one leaf.

    The same truth the screen tells: a leaf in the queue owes the reader the
    reason it waits and the times it plans to start and finish, a leaf in
    work owes the time that has passed since it started, and a leaf that
    passed its own estimate says so.
    """

    bits: list[str] = []
    if leaf.status in (STATUS_QUEUED, STATUS_WAITING):
        bits.append(f"ждёт: {leaf.wait_reason or 'причина не названа'}")
        if leaf.planned_start:
            bits.append(f"начнём {leaf.planned_start}")
        if leaf.planned_finish:
            bits.append(f"закончим {leaf.planned_finish}")
    elif leaf.status == STATUS_RUNNING:
        if leaf.started_at:
            bits.append(f"начата {leaf.started_at}")
        passed = _elapsed_since(leaf.started_at, metrics.get("build_minutes"))
        if passed is not None:
            bits.append(f"прошло {fmt_minutes(passed)} на момент сборки")
            if leaf.estimate_max is not None and passed > leaf.estimate_max + 0.01:
                bits.append(
                    f"отстаём: прошло {fmt_minutes(passed)} при оценке "
                    f"{fmt_minutes(leaf.estimate_max)}"
                )
    elif leaf.status == STATUS_BLOCKED:
        bits.append(f"блокер: {leaf.blocker or 'не назван'}")
    if leaf.actual_minutes is not None:
        bits.append(f"факт {fmt_minutes(leaf.actual_minutes)}")
    return " · ".join(bits) if bits else "—"


def render_print_html(graph: Graph, metrics: dict[str, Any]) -> str:
    """The plan on paper: one wave per page, no clicks, no external resource.

    The dashboard is a working surface — it folds, it searches, it scrolls. A
    sheet of paper can do none of that, and a document that keeps the
    machinery of a screen prints badly and drags in resources the printer
    never sees. So the paper version is its own document: the same graph and
    the same numbers, laid out for A4 with a page break per wave, and not one
    reference to anything outside the file.
    """

    schedule: Schedule = metrics["schedule"]
    cost = _cost_of(graph, metrics)
    leaves = sorted(
        graph.leaves,
        key=lambda leaf: (schedule.waves.get(leaf.id, 0), leaf.order),
    )
    waves: dict[int, list[Leaf]] = {}
    unscheduled: list[Leaf] = []
    for leaf in leaves:
        wave = schedule.waves.get(leaf.id)
        if wave is None:
            # A leaf the scheduler does not place - a deferred one - is not a
            # wave of its own: it is outside the delivery, and the paper says
            # so instead of giving it a wave number it never had.
            unscheduled.append(leaf)
            continue
        waves.setdefault(wave, []).append(leaf)

    priced = cost.get("priced_count") or 0
    if priced:
        money = (
            f"{fmt_usd(cost['total_usd'])}"
            + (f" ({cost['label']})" if cost.get("label") else "")
            + f" за {priced} из {cost['leaf_count']} листьев"
        )
    else:
        money = f"нет посчитанных денег — {cost['leaf_count']} листьев без цены"

    kpi_rows = []
    for label, value in (
        ("Готово", f"{metrics['done']} / {metrics['headline_total']}"),
        ("В работе", str(metrics["running"])),
        ("В очереди", str(metrics["queued"])),
        ("Заблокировано", str(metrics["blocked"])),
        ("Отложено владельцем", str(metrics["deferred"])),
        ("Осталось", str(metrics["unfinished"])),
        ("Параллельность", f"{metrics['current_parallel']} / {metrics['slots']}"),
        (
            "Усилие",
            fmt_minutes(metrics["effort_minutes"])
            if metrics["effort_known"]
            else "неизвестно",
        ),
    ):
        kpi_rows.append(
            f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        )

    findings = estimate_cap_warnings(graph) + staffing_warnings(graph, cost)
    finding_html = ""
    if findings:
        finding_html = (
            "<h2>Что требует внимания</h2>\n<ul>\n"
            + "".join(f"<li>{escape(note)}</li>\n" for note in findings)
            + "</ul>\n"
        )

    business = ""
    if graph.business_result:
        business += (
            f"<p><b>Что будет работать:</b> {escape(graph.business_result)}</p>\n"
        )
    for item in graph.business_results:
        business += f"<p class='small muted'>{escape(item)}</p>\n"
    business += '<h2>Как проверим</h2>'
    business += ('<ul>' + ''.join(f'<li>{escape(item)}</li>' for item in graph.acceptance_scenarios) + '</ul>') if graph.acceptance_scenarios else '<p>Сценарии проверки ещё не описаны</p>'
    if graph.current_progress:
        business += f'<p><b>Что уже сделано:</b> {escape(graph.current_progress)}</p>'

    def row_html(leaf: Leaf) -> str:
        """One leaf as one row of the paper table."""

        entry = cost.get("leaves", {}).get(leaf.id, {})
        if entry.get("usd") is not None:
            leaf_money = fmt_usd(entry.get("usd"))
        else:
            leaf_money = entry.get("text") or PRICE_UNAVAILABLE
        estimate = leaf.duration_label
        if (
            leaf.estimate_max is not None
            and leaf.estimate_max > LEAF_ESTIMATE_CAP_MINUTES
        ):
            estimate += f" — выше предела {LEAF_ESTIMATE_CAP_MINUTES} мин"
            estimate += (
                f": {leaf.estimate_over_limit_reason}"
                if leaf.estimate_over_limit_reason
                else " (причина не названа)"
            )
        return (
            "<tr>"
            f"<td><b>{escape(leaf.id)}</b></td>"
            f"<td>{escape(STATUS_GLYPHS.get(leaf.status, '⋯'))} "
            f"{escape(STATUS_LABELS.get(leaf.status, leaf.status))}</td>"
            f"<td>{escape(leaf.label or leaf.id)}</td>"
            f"<td>{escape(estimate)}</td>"
            f"<td>{escape(_print_leaf_state(leaf, metrics))}</td>"
            f"<td>{escape(', '.join(leaf.depends_on) or '—')}</td>"
            f"<td>{escape(leaf.owner or '—')}</td>"
            f"<td>{escape(leaf_money)}</td>"
            "</tr>"
        )

    def table_html(members: list[Leaf]) -> str:
        return (
            "<table>\n<thead><tr>"
            "<th>Лист</th><th>Статус</th><th>Что делает</th><th>Оценка</th>"
            "<th>Состояние</th><th>Зависит</th><th>Кто</th><th>Стоимость</th>"
            "</tr></thead>\n<tbody>\n"
            + "\n".join(row_html(leaf) for leaf in members)
            + "\n</tbody>\n</table>\n"
        )

    sections: list[str] = []
    for index, wave in enumerate(sorted(waves)):
        members = waves[wave]
        head = (
            f"<h2>Волна {wave}</h2>\n"
            f"<p class='small muted'>{len(members)} "
            f"{'лист' if len(members) == 1 else 'листьев'}</p>\n"
        )
        klass = "wave first" if index == 0 else "wave"
        sections.append(
            f'<section class="{klass}">\n{head}{table_html(members)}</section>\n'
        )
    if unscheduled:
        sections.append(
            '<section class="wave">\n'
            "<h2>Вне расписания</h2>\n"
            "<p class='small muted'>отложено владельцем — вне поставки</p>\n"
            f"{table_html(unscheduled)}</section>\n"
        )

    goal = f"<p><b>Цель:</b> {escape(graph.goal)}</p>\n" if graph.goal else ""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{escape(graph.title)} — печатная версия</title>\n"
        f"<style>{PRINT_CSS}</style>\n"
        "</head>\n<body>\n"
        '<section class="cover">\n'
        f"<h1>{escape(graph.title)}</h1>\n"
        + goal
        + business
        + "<table class='kpis'>\n<tbody>\n"
        + "\n".join(kpi_rows)
        + "\n</tbody>\n</table>\n"
        + f"<p><b>Смета плана:</b> {escape(money)}</p>\n"
        + finding_html
        + "</section>\n"
        + "".join(sections)
        + "</body>\n</html>\n"
    )


# --------------------------------------------------------------------------
# text summary
# --------------------------------------------------------------------------


def wave_count(graph: Graph, metrics: dict[str, Any]) -> int:
    """Number of waves the schedule derives from the dependencies."""

    schedule = metrics.get("schedule")
    waves = getattr(schedule, "waves", None) or {}
    return max(waves.values()) + 1 if waves else 1


def count_russian(value: int, one: str, few: str, many: str) -> str:
    """A number with the right Russian form of its noun: 1 лист, 2 листа, 5 листьев."""

    if value % 10 == 1 and value % 100 != 11:
        return f"{value} {one}"
    if 2 <= value % 10 <= 4 and not 12 <= value % 100 <= 14:
        return f"{value} {few}"
    return f"{value} {many}"


def plan_shape(graph: Graph, metrics: dict[str, Any]) -> tuple[int, int, int]:
    """The shape of the work the graph itself proves: parallel, waves, slots.

    A header line is a claim; the dependencies are the evidence. The waves
    come from the dependency layers, and no layer ever runs wider than the
    slots the plan provides — that is the honest shape of the same work the
    report declares in words.
    """

    schedule = metrics.get("schedule")
    waves_map = getattr(schedule, "waves", None) or {}
    slots = metrics["slots"]
    computed_waves = wave_count(graph, metrics)
    if waves_map:
        sizes: dict[int, int] = {}
        for wave in waves_map.values():
            sizes[wave] = sizes.get(wave, 0) + 1
        parallel = min(max(sizes.values()), slots)
    else:
        parallel = 0
    return parallel, computed_waves, slots


def _cost_of(graph: Graph, metrics: dict[str, Any]) -> dict[str, Any]:
    """The money of this plan, computed once and then read from the metrics.

    Every surface that shows dollars goes through here, so the report, the page
    and the validator cannot quote three different numbers for one plan; the
    catalog parse behind it is memoized per process, so a hook refresh does not
    re-read the snapshot.
    """

    cost = metrics.get("cost")
    if cost is None:
        cost = compute_cost(graph)
        metrics["cost"] = cost
    return cost


def leaf_cost_segment(entry: dict[str, Any]) -> str:
    """One leaf's money, in the words of the projected report.

    The segment is built to be read back by the report parser: no parentheses
    (the first pair on the line is the leaf's label), no ``HH:MM`` (that would
    become a start or a finish time), no «оценка», «факт», «зависит» or
    «блокер» — each of those words is a field the parser claims for its own.
    """

    if entry.get("state") == "priced":
        bits = [
            f"стоимость {fmt_usd(entry['usd'])}",
            f"модель {entry['model']}",
            f"класс {entry['tier']}",
            f"токенов {entry['tokens']:,}".replace(",", " "),
            f"цена {entry['label']}",
        ]
        if entry.get("tokens_source") == "minutes-x-tpm":
            rate = entry.get("tokens_per_minute")
            if rate:
                bits.append(f"скорость {int(rate):,} ток/мин {entry.get('tpm_label')}".replace(",", " "))
        if entry.get("selection") == "tier-suggested":
            # The number is the price of the class, not the price of the worker:
            # a leaf that never named its model cannot be quoted more exactly
            # than the catalog quotes its cheapest route of that class today.
            bits.append("цена класса, а не объявленной модели")
        if entry.get("match_note"):
            bits.append(f"каталог принял алиас так: {entry['match_note']}")
        if entry.get("divergence_pct") is not None:
            bits.append(
                f"лист объявил {fmt_usd(entry.get('declared_usd'))} · расхождение "
                f"{entry['divergence_pct']}%"
            )
        return " · ".join(bits)
    return f"стоимость — {entry.get('text') or PRICE_UNAVAILABLE}"


def render_leaf_lines(graph: Graph, metrics: dict[str, Any]) -> list[str]:
    """Render one readable line per leaf: id, status, estimate, fact, wave, links."""

    schedule = metrics.get("schedule")
    waves = getattr(schedule, "waves", None) or {}
    cost = _cost_of(graph, metrics)
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
        # A leaf in the queue owes the report three things: why it cannot start
        # yet, when it is planned to start and when it is planned to finish. A
        # queued leaf without a reason is not silent either - the report says the
        # reason is missing, so nobody reads an unexplained wait as a plan.
        if leaf.status in (STATUS_QUEUED, STATUS_WAITING):
            parts.append(f"ждёт: {leaf.wait_reason}" if leaf.wait_reason else "ждёт: причина не названа")
            if leaf.planned_start:
                parts.append(f"начнём {leaf.planned_start}")
            if leaf.planned_finish:
                parts.append(f"закончим {leaf.planned_finish}")
        # A running leaf is measured against its estimate: the time that has
        # passed since it started is what the owner weighs, so the projection
        # shows it and names the delay when it passes the estimate.
        if leaf.status == STATUS_RUNNING and leaf.started_at:
            passed = _elapsed_since(leaf.started_at, metrics.get("build_minutes"))
            if passed is not None:
                parts.append(f"прошло {fmt_minutes(passed)} на момент сборки")
                if leaf.estimate_max is not None and passed > leaf.estimate_max + 0.01:
                    parts.append(f"отстаём: прошло {fmt_minutes(passed)} при оценке {leaf.duration_label}")
        # A deferred leaf is not scheduled: it has no wave, it is outside the
        # remainder of the delivery.
        parts.append("вне остатка" if leaf.status == STATUS_DEFERRED else f"волна {wave}")
        parts.append("зависит: " + (", ".join(leaf.depends_on) or "—"))
        if leaf.parallel_with:
            parts.append("параллельно: " + ", ".join(leaf.parallel_with))
        parts.append(leaf_cost_segment(cost["leaves"].get(leaf.id, {})))
        if leaf.blocker and leaf.status == STATUS_BLOCKED:
            parts.append(f"блокер: {leaf.blocker}")
        lines.append(" · ".join(parts))
        if leaf.description:
            lines.append(f"      Описание задачи: {leaf.description}")
        if leaf.acceptance:
            lines.append(f"      Приёмка: {leaf.acceptance}")
        if leaf.affected_files:
            lines.append("      Затрагиваемые файлы: " + ", ".join(f"`{path}`" for path in leaf.affected_files))
        # What the finished leaf actually delivered, in the worker's own words.
        # The report has no place for it until now, so the result of a closed
        # leaf was readable only inside the leaf file.
        if leaf.result:
            lines.append(f"      Результат: {leaf.result}")
    return lines


def _count_with_ids(ids: list[str]) -> str:
    """A count the reader can act on: how many, and which ones."""

    if not ids:
        return "0"
    if len(ids) <= 4:
        return f"{len(ids)} ({', '.join(ids)})"
    return f"{len(ids)} ({', '.join(ids[:4])}, …)"


def render_text(graph: Graph, metrics: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Граф задач: {graph.title}")
    lines.append(f"Ревизия плана: {graph_revision(graph)}")
    lines.append(SNAPSHOT_NOTE)
    if graph.goal:
        lines.append(f"Цель: {graph.goal}")
    for result in (graph.business_results or ([graph.business_result] if graph.business_result else [])):
        lines.append(f"Бизнес-результат: {result}")
    for scenario in graph.acceptance_scenarios:
        lines.append(f"Как проверим: {scenario}")
    # The shape of the work is part of the report, so the projection carries
    # it too — computed from this graph, never copied from an older claim.
    shape_parallel, shape_waves, shape_slots = plan_shape(graph, metrics)
    lines.append(
        "Декомпозиция: {leaves} · {parallel} параллельно · {waves} · слотов: {slots}".format(
            leaves=count_russian(metrics["total"], "лист", "листа", "листьев"),
            parallel=shape_parallel,
            waves=count_russian(shape_waves, "волна", "волны", "волн"),
            slots=shape_slots,
        )
    )
    scope = "по журналу волны" if metrics["use_live"] else "по листьям графа"
    # The counter of the progress row keeps its old meaning - «заблокировано»
    # counts the leaves whose status says blocked, and nothing else. The two
    # waits are named next to it because a leaf queued behind an unfinished
    # predecessor cannot start either, and a reader who sees only «заблокировано
    # 0» reads that as «nothing is in the way».
    lines.append(
        "Прогресс ({scope}): {done}/{total} готово ({pct}%) · в работе {running} · "
        "заблокировано {blocked} · ждёт листа {leaf_wait} · ждёт исполнителя {owner_wait} · "
        "осталось {left}".format(
            scope=scope,
            done=metrics["done"], total=metrics["headline_total"], pct=metrics["progress_pct"],
            running=metrics["running"], blocked=metrics["blocked"],
            leaf_wait=len(metrics["waiting_for_leaf_ids"]),
            owner_wait=len(metrics["waiting_for_owner_ids"]),
            left=metrics["unfinished"],
        )
    )
    # The money of the plan, next to its shape: what one leaf costs, what the
    # whole plan costs, and how much of the dollars go to the frontier class.
    lines.extend(cost_lines(_cost_of(graph, metrics)))
    # The cap of the format, said out loud where the plan is read: a leaf over
    # fifteen minutes is two leaves, and only a leaf that says why it is
    # deliberately larger is allowed past it. The plan that carries such a leaf
    # is named here rather than rendered as if it were ordinary.
    lines.extend(estimate_cap_warnings(graph))
    # The waves are counted from the dependencies, never copied from the
    # header: a hand-written number is a claim, the graph is the evidence.
    computed_waves = wave_count(graph, metrics)
    waves_note = (
        f" · заявлено волн: {graph.declared_waves} — расхождение с расчётным числом"
        if graph.declared_waves and graph.declared_waves != computed_waves
        else ""
    )
    lines.append(
        "Листьев в графе: {total} · слотов: {slots} · волн: {waves}{waves_note}".format(
            total=metrics["total"], slots=metrics["slots"],
            waves=computed_waves, waves_note=waves_note,
        )
    )
    parallel_note = (
        f" · заявлено {graph.declared_parallel} параллельно при {metrics['slots']} слотах — расхождение"
        if graph.declared_parallel and graph.declared_parallel > metrics["slots"]
        else ""
    )
    lines.append(
        "Параллельность: сейчас {current} из {slots} слотов, {peak}{parallel_note}".format(
            current=metrics["current_parallel"], slots=metrics["slots"],
            peak=(f"пик по плану {metrics['planned_peak_parallel']}"
                  if metrics["duration_known"] else "пик по плану неизвестен"),
            parallel_note=parallel_note,
        )
    )
    # The same moment counted by hands. Two rows in the report can be one
    # executor, and that is the difference between a full plan and a plan with
    # a free slot nobody noticed.
    overload = " — исполнителей больше, чем слотов" if metrics["owner_overload"] else ""
    lines.append(
        "Исполнители: занято {busy} из {slots} слотов{overload} · "
        "ждёт листа: {leaf_wait} · ждёт исполнителя: {owner_wait} · готово к запуску: {ready}".format(
            busy=metrics["busy_owners"], slots=metrics["slots"], overload=overload,
            leaf_wait=_count_with_ids(metrics["waiting_for_leaf_ids"]),
            owner_wait=_count_with_ids(metrics["waiting_for_owner_ids"]),
            ready=_count_with_ids(metrics["ready_unstarted_ids"]),
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
        if leaf.estimate_over_limit_reason:
            task["estimate_over_limit_reason"] = leaf.estimate_over_limit_reason
        if leaf.wait_reason:
            task["wait_reason"] = leaf.wait_reason
        if leaf.planned_start:
            task["planned_start"] = leaf.planned_start
        if leaf.planned_finish:
            task["planned_finish"] = leaf.planned_finish
        if leaf.actual_minutes is not None:
            task["actual_minutes"] = leaf.actual_minutes
        if leaf.started_at:
            task["started_at"] = leaf.started_at
        if leaf.created_at:
            task['created_at'] = leaf.created_at
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
        if leaf.tier:
            task["tier"] = leaf.tier
        if leaf.complexity:
            task["complexity"] = leaf.complexity
        if leaf.token_estimate is not None:
            task["token_estimate"] = leaf.token_estimate
        if leaf.cost_usd is not None:
            task["cost_usd"] = leaf.cost_usd
        if leaf.cost_source:
            task["cost_source"] = leaf.cost_source
        if leaf.result:
            task["result"] = leaf.result
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
        "acceptance_scenarios": list(graph.acceptance_scenarios),
        "current_progress": graph.current_progress,
        "external_waits": graph.external_waits,
        "slots": graph.slots,
        "updated_at": graph.updated_at,
        "tasks": tasks,
    }
    if graph.budget_usd is not None:
        document["budget_usd"] = graph.budget_usd
    if graph.plan_origin:
        document['plan_origin'] = graph.plan_origin
    for field in ("started_at", "finished_at"):
        if getattr(graph, field):
            document[field] = getattr(graph, field)
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
    # (report leaf, graph leaf, edges lost by the graph, edges the report does not name)
    dependency_mismatch: list[tuple[Leaf, Leaf, list[str], list[str]]] = field(default_factory=list)
    field_mismatch: list[tuple[Leaf, Leaf, str]] = field(default_factory=list)
    matched_by_label: int = 0
    # Report rows that named no leaf and were paired by their row number. The
    # pairing is a guess, and `check-plan` says so out loud instead of
    # presenting it as an id match.
    matched_by_position: int = 0
    # (report row, leaf it was paired with, leaf the row really names)
    position_mismatch: list[tuple[Leaf, Leaf, Leaf]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (
            self.extra_in_report
            or self.missing_in_report
            or self.status_mismatch
            or self.dependency_mismatch
            or self.field_mismatch
            or self.position_mismatch
        )


def _graph_leaf_for(leaf: Leaf, graph: Graph, taken: set[str]) -> tuple[Optional[Leaf], str]:
    """Find the graph leaf that carries the same task as the report leaf.

    The second value says how the pair was made, and that is the whole point
    of this function: «id», «position» or «label». A report line that names its
    leaf («  - L04 · ✅ …») is anchored by that id, and a line whose id the
    graph does not have is a divergence, never a line to be shifted onto a
    neighbour. A line that names no leaf at all has only its row number, so it
    is matched by that number and the match is declared positional - a row
    number is not an identifier, and pretending otherwise is how a report
    without ids silently reorders a plan.
    """

    if leaf.id_explicit:
        for candidate in graph.leaves:
            if candidate.id in taken:
                continue
            if candidate.id.strip().lower() == leaf.id.strip().lower():
                return candidate, "id"
        return None, ""

    for candidate in graph.leaves:
        if candidate.id in taken:
            continue
        if candidate.id.strip().lower() == leaf.id.strip().lower():
            return candidate, "position"
    label = normalize(leaf.label).lower()
    if not label:
        return None, ""
    matches = [
        candidate
        for candidate in graph.leaves
        if candidate.id not in taken and normalize(candidate.label).lower() == label
    ]
    return (matches[0], "label") if len(matches) == 1 else (None, "")


def _positional_order_mismatch(
    leaf: Leaf, target: Leaf, graph: Graph, taken: set[str]
) -> Optional[Leaf]:
    """The leaf a nameless row really names, when that leaf is another one.

    A report row without an id is paired by its number, which is a guess. The
    guess is honest only while the row's own name agrees with it. When the row
    names a leaf that sits elsewhere in the graph, the rows of the report and
    the leaves of the graph are in a different order - and that is a
    divergence to name, not a detail to smooth over.
    """

    label = normalize(leaf.label).lower()
    if not label or label == normalize(target.label).lower():
        return None
    matches = [
        candidate
        for candidate in graph.leaves
        if candidate.id not in taken
        and candidate.id != target.id
        and normalize(candidate.label).lower() == label
    ]
    return matches[0] if len(matches) == 1 else None


def compare_plan_with_graph(report: Graph, graph: Graph) -> PlanSync:
    """Compare task identity/status and human details stated in the report."""

    result = PlanSync()
    taken: set[str] = set()
    for leaf in report.leaves:
        target, how = _graph_leaf_for(leaf, graph, taken)
        if target is None:
            result.extra_in_report.append(leaf)
            continue
        taken.add(target.id)
        result.matched.append((leaf, target))
        if how == "label":
            result.matched_by_label += 1
        elif how == "position":
            result.matched_by_position += 1
            elsewhere = _positional_order_mismatch(leaf, target, graph, taken)
            if elsewhere is not None:
                result.position_mismatch.append((leaf, target, elsewhere))
        if leaf.status != target.status:
            result.status_mismatch.append((leaf, target))
        # Dependencies decide the real launch order, so a lost or invented edge
        # is a divergence even when every other field agrees. Ids are only
        # comparable when both sides name the leaf by the same id.
        if how != "label":
            # A leaf never waits for itself: a positional self-reference in an
            # unparsed report is noise, not an edge.
            reported_deps = [dep for dep in leaf.depends_on if dep != leaf.id]
            graph_deps = [dep for dep in target.depends_on if dep != target.id]
            missing_in_graph = [dep for dep in reported_deps if dep not in graph_deps]
            unmentioned = [dep for dep in graph_deps if dep not in reported_deps]
            if missing_in_graph or unmentioned:
                result.dependency_mismatch.append((leaf, target, missing_in_graph, unmentioned))
        for field_name in ("description", "acceptance", "affected_files"):
            reported = getattr(leaf, field_name)
            if reported and reported != getattr(target, field_name):
                result.field_mismatch.append((leaf, target, field_name))
    for leaf in graph.leaves:
        if leaf.id not in taken:
            result.missing_in_report.append(leaf)
    return result


def check_plan_shape(report: Graph, graph: Graph) -> list[str]:
    """The declared shape of the header against the shape the graph proves.

    «до 9 параллельно · 7 волн · слотов: 9» is a claim about the plan; the
    dependencies and the slots are the evidence. A header that contradicts
    its own graph is a divergence and is named with both numbers — the one
    the report declared and the one the graph computes.
    """

    metrics = build_metrics(graph)
    parallel, waves, slots = plan_shape(graph, metrics)
    notes: list[str] = []
    if report.declared_leaves is not None and report.declared_leaves != len(graph.leaves):
        notes.append(
            f"заявлено {count_russian(report.declared_leaves, 'лист', 'листа', 'листьев')}, "
            f"в графе {count_russian(len(graph.leaves), 'лист', 'листа', 'листьев')}"
        )
    if report.declared_parallel is not None and report.declared_parallel != parallel:
        notes.append(
            f"заявлено {report.declared_parallel} параллельно · по графу {parallel} "
            f"(самый широкий слой зависимостей при {slots} слотах)"
        )
    if report.declared_waves is not None and report.declared_waves != waves:
        notes.append(
            f"заявлено {count_russian(report.declared_waves, 'волна', 'волны', 'волн')}, "
            f"по графу {count_russian(waves, 'волна', 'волны', 'волн')}"
        )
    if report.declared_slots is not None and report.declared_slots != slots:
        notes.append(f"заявлено слотов: {report.declared_slots}, в графе слотов: {slots}")
    return notes


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
    render.add_argument(
        "--print",
        dest="print_mode",
        action="store_true",
        help="also write the paper version of the same graph (plan.print.html)",
    )

    pdf = sub.add_parser(
        "pdf",
        help="Print the plan on paper through a headless renderer",
    )
    pdf.add_argument("input", type=Path, help="plan record, plan report or graph JSON")
    pdf.add_argument("-o", "--output", type=Path, help="output PDF path")
    pdf.add_argument("--title", help="override the plan title")
    pdf.add_argument(
        "--print-html",
        type=Path,
        help="print this prepared sheet instead of building one from the graph",
    )
    pdf.add_argument(
        "--renderer",
        help="the renderer to use: a name on the PATH or a path to the binary",
    )
    pdf.add_argument(
        "--timeout",
        type=int,
        default=PDF_RENDERER_TIMEOUT,
        help=f"seconds the renderer may take (default {PDF_RENDERER_TIMEOUT})",
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
    if getattr(args, "print_mode", False):
        # The paper version of the same graph: one wave per page, nothing to
        # click, nothing to fetch. It is written next to the other artifacts of
        # this revision, so the plan on paper and the plan on screen are the
        # same plan.
        if args.out_dir is not None:
            print_output = args.out_dir / "plan.print.html"
        elif args.output is not None:
            print_output = args.output.with_name(f"{args.output.stem}.print.html")
        else:
            stem = Path(graph.source_path).stem if graph.source_path else "lhc-grid"
            print_output = Path.cwd() / f"{stem}.print.html"
        print_output.write_text(render_print_html(graph, metrics), encoding="utf-8")
        print(f"{print_output}")
    if args.open:
        try:
            webbrowser.open(output.resolve().as_uri())
        except Exception:  # pragma: no cover - headless hosts have no browser
            print("browser not available", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------
# PDF: the honest command
# --------------------------------------------------------------------------

# The headless renderers a machine may have. Each one prints a PDF out of a
# local HTML file, and none of them needs the network — the sheet is a local
# file with no reference outside itself. The list is also the honest answer to
# the question "which renderer do I need", so the error names it instead of
# shrugging.
PDF_RENDERERS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "google-chrome",
        (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
        ),
        "chrome",
    ),
    ("chromium", (), "chrome"),
    ("chromium-browser", (), "chrome"),
    ("wkhtmltopdf", (), "wkhtmltopdf"),
    ("weasyprint", (), "weasyprint"),
)
# The list may be narrowed by the environment, so an operator can name the
# renderer this machine is allowed to use.
PDF_RENDERER_ENV = "LHC_PDF_RENDERERS"
PDF_RENDERER_TIMEOUT = 120


def _pdf_renderer_kind(name: str) -> str:
    """How a renderer is called, judged by its own name."""

    lowered = name.lower()
    if "chrome" in lowered or "chromium" in lowered:
        return "chrome"
    if "wkhtmltopdf" in lowered:
        return "wkhtmltopdf"
    if "weasyprint" in lowered:
        return "weasyprint"
    return "generic"


def find_pdf_renderer(
    requested: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], list[str]]:
    """Find the renderer that prints the sheet.

    Returns the executable, the way it is called and the names it looked for.
    The names are the point: a machine without a renderer has to be told
    which one is missing, not merely that something went wrong.
    """

    tried: list[str] = []
    if requested:
        candidates = [requested]
    else:
        override = os.environ.get(PDF_RENDERER_ENV, "")
        if override.strip():
            candidates = [item for item in override.split(os.pathsep) if item]
        else:
            candidates = [name for name, _paths, _kind in PDF_RENDERERS]
    for candidate in candidates:
        tried.append(candidate)
        # A known renderer also lives in places the PATH does not name.
        for name, paths, kind in PDF_RENDERERS:
            if name != candidate:
                continue
            for path in paths:
                if path and os.path.exists(path):
                    return path, kind, tried
        found = shutil.which(candidate)
        if found:
            return found, _pdf_renderer_kind(candidate), tried
        if os.path.sep in candidate and os.path.exists(candidate):
            return candidate, _pdf_renderer_kind(candidate), tried
    return None, None, tried


def _pdf_commands(
    executable: str,
    kind: str,
    source: Path,
    target: Path,
    profile: Optional[Path] = None,
) -> list[list[str]]:
    """The command lines that print the sheet, best first."""

    url = source.resolve().as_uri()
    if kind == "chrome":
        shared = [
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            # The sheet references nothing outside itself, so the renderer has
            # no reason to reach the network either.
            "--host-resolver-rules=MAP * ~NOTFOUND",
        ]
        if profile is not None:
            shared.append(f"--user-data-dir={profile}")
        return [
            [executable, "--headless=new", *shared, "--no-pdf-header-footer",
             f"--print-to-pdf={target}", url],
            [executable, "--headless", *shared, "--print-to-pdf-no-header",
             f"--print-to-pdf={target}", url],
        ]
    if kind == "wkhtmltopdf":
        return [
            [executable, "--enable-local-file-access", "--quiet", str(source), str(target)]
        ]
    return [[executable, str(source), str(target)]]


def _looks_like_pdf(path: Path) -> bool:
    """A PDF starts with its own name; a file that does not is not one."""

    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def command_pdf(args: argparse.Namespace) -> int:
    """Print the plan on paper, or name the renderer that is missing.

    There is no PDF encoder written here on purpose: a file a hand-rolled
    writer produced would be a different document from the one a browser
    prints, with its own bugs. So the sheet goes to a headless renderer that
    is installed on this machine, and when none is, the command says which
    one it looked for and exits with code 2 — a named absence, not a silent
    empty file.
    """

    graph = require_leaves(discover_graph(args.input))
    if args.title:
        graph.title = args.title
    metrics = build_metrics(graph)

    workdir: Optional[Path] = None
    if args.print_html:
        source = Path(args.print_html)
        if not source.exists():
            print(f"файл печатной версии не найден: {source}", file=sys.stderr)
            return 2
    else:
        workdir = Path(tempfile.mkdtemp(prefix="lhc-print-"))
        source = workdir / "plan.print.html"
        source.write_text(render_print_html(graph, metrics), encoding="utf-8")

    try:
        if args.output:
            target = Path(args.output)
        else:
            stem = Path(graph.source_path).stem if graph.source_path else "lhc-plan"
            target = Path.cwd() / f"{stem}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)

        executable, kind, tried = find_pdf_renderer(args.renderer)
        if executable is None:
            names = ", ".join(tried) if tried else "ни одного известного"
            print(
                "PDF не собран: рендерер не найден. Проверены: "
                f"{names}. Установите один из них "
                "(например: brew install --cask google-chrome) и повторите: "
                "python3 common/tools/lhc_grid.py pdf <план> -o plan.pdf",
                file=sys.stderr,
            )
            return 2

        profile = workdir / "chrome-profile" if workdir is not None else None
        if profile is not None:
            profile.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        for command in _pdf_commands(executable, kind or "generic", source, target, profile):
            try:
                finished = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                failures.append(f"{command[0]}: не ответил за {args.timeout} с")
                continue
            except OSError as error:
                failures.append(f"{command[0]}: не запустился ({error})")
                continue
            if finished.returncode != 0:
                tail = (finished.stderr or finished.stdout or "").strip().splitlines()
                failures.append(
                    f"{command[0]}: код {finished.returncode}"
                    + (f" — {tail[-1]}" if tail else "")
                )
                continue
            if not target.exists() or target.stat().st_size == 0:
                failures.append(f"{command[0]}: файл PDF не создан")
                continue
            if not _looks_like_pdf(target):
                failures.append(f"{command[0]}: созданный файл не похож на PDF")
                continue
            print(f"{target}")
            return 0
        print(
            f"PDF не собран: {executable} не напечатал файл. "
            + "; ".join(failures),
            file=sys.stderr,
        )
        return 2
    finally:
        if workdir is not None:
            shutil.rmtree(workdir, ignore_errors=True)


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
            # An amount of zero is an amount: the money and token fields are
            # carried only when the fresh export does not have them at all,
            # while a text field still counts an empty string as missing.
            missing = (
                task.get(field) is None
                if field in NUMERIC_ATTRIBUTION_FIELDS
                else not task.get(field)
            )
            if missing and source.get(field) is not None:
                task[field] = source[field]
    for field in ("current_progress", "external_waits", "acceptance_scenarios", "started_at", "finished_at", "updated_at", "plan_origin"):
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


def estimate_cap_findings(graph: Graph) -> list[dict[str, Any]]:
    """The leaves whose estimate passes the cap of the format.

    The format says a leaf is about fifteen minutes and a longer job is two
    leaves. That cap lived only in the prose, so a thirty-to-fifty minute leaf
    passed every gate and was printed as «оценка 30 мин–50 мин» without a word.
    A leaf that records, in its own words, why it is deliberately larger is not
    a breach: the reason is the signpost, and only the reason lets it through.
    """

    cap = LEAF_ESTIMATE_CAP_MINUTES
    findings: list[dict[str, Any]] = []
    for leaf in graph.leaves:
        high = leaf.estimate_max
        if high is None or high <= cap:
            continue
        reason = leaf.estimate_over_limit_reason
        findings.append(
            {
                "id": leaf.id,
                "minutes": high,
                "cap": cap,
                "reason": reason,
                "breach": not reason,
            }
        )
    return findings


def estimate_cap_warnings(graph: Graph) -> list[str]:
    """The cap of the format, said out loud by the renderer as well."""

    breaches = [item for item in estimate_cap_findings(graph) if item["breach"]]
    if not breaches:
        return []
    notes = [
        f"ПРЕВЫШЕН ПРЕДЕЛ ОЦЕНКИ ЛИСТА ({LEAF_ESTIMATE_CAP_MINUTES} мин) — "
        "длинную работу надо разбить на два листа, либо записать в листе "
        "estimate_over_limit_reason, почему он сознательно больше:"
    ]
    for item in breaches:
        notes.append(
            f"  - лист {item['id']}: оценка {fmt_minutes(item['minutes'])} "
            f"при пределе {item['cap']} мин — "
            "чего не хватает: разбиения или причины превышения"
        )
    return notes


def staffing_warnings(graph: Graph, cost: dict[str, Any]) -> list[str]:
    """Where the plan waits for hands rather than for leaves.

    The count of running rows says nothing about capacity: one executor holding
    two leaves is one pair of hands. A plan can look saturated and be idle, or
    look idle and be over-subscribed, and the owner decides with the wrong
    number either way.
    """

    metrics = build_metrics(graph)
    notes: list[str] = []
    if metrics["owner_overload"]:
        notes.append(
            "исполнителей в работе больше, чем слотов: "
            f"{metrics['busy_owners']} при {metrics['slots']} — "
            f"заняты {', '.join(metrics['busy_owner_keys'])}"
        )
    if metrics["waiting_for_owner_ids"]:
        notes.append(
            f"ждут исполнителя, а не листа: {', '.join(metrics['waiting_for_owner_ids'])} — "
            f"их владелец уже занят; зависимости этих листьев закрыты"
        )
    if metrics["ready_unstarted_ids"]:
        detail = ", ".join(
            f"{leaf_id} {fmt_usd(cost['leaves'].get(leaf_id, {}).get('usd'))}"
            + (f" ({cost['leaves'].get(leaf_id, {}).get('label')})"
               if cost["leaves"].get(leaf_id, {}).get("label") else "")
            if cost["leaves"].get(leaf_id, {}).get("usd") is not None
            else f"{leaf_id} — {cost['leaves'].get(leaf_id, {}).get('text') or PRICE_UNAVAILABLE}"
            for leaf_id in metrics["ready_unstarted_ids"]
        )
        notes.append(f"готовы к запуску и ничего не ждут: {detail}")
    return notes


def cost_warnings(graph: Graph, cost: dict[str, Any]) -> list[str]:
    """What the money of this plan tells the owner, without vetoing anything.

    These are findings, not errors: a plan whose snapshot is stale is still a
    plan, and `validate` must keep exiting 0 for a graph that merely costs more
    than expected. One finding per kind, with the leaves named inside it — a
    wall of twenty near-identical lines teaches the owner to skip the list.
    """

    notes: list[str] = []
    if not cost.get("available"):
        notes.append(f"{PRICE_UNAVAILABLE}: {cost.get('reason') or 'смета не рассчитана'}")
    if graph.budget_usd is not None and cost.get("over_budget"):
        notes.append(
            f"план стоит {fmt_usd(cost.get('total_usd'))} при бюджете "
            f"{fmt_usd(graph.budget_usd)}"
        )
    if cost.get("tier_from_model_class_ids"):
        notes.append(
            f"{len(cost['tier_from_model_class_ids'])} листьев объявляют класс в model_class, "
            "а не в tier: " + ", ".join(cost["tier_from_model_class_ids"])
            + " — поле tier каноническое, model_class читается как класс только по словам "
            "fast/frontier"
        )
    if cost.get("class_priced_ids"):
        notes.append(
            f"{len(cost['class_priced_ids'])} листьев посчитаны по классу, а не по модели "
            f"исполнителя ({fmt_usd(cost.get('class_priced_usd'))}"
            + (f" ({cost['label']})" if cost.get("label") else "")
            + f" из {fmt_usd(cost.get('total_usd'))}"
            + (f" ({cost['label']})" if cost.get("label") else "")
            + "): " + ", ".join(cost["class_priced_ids"])
            + " — это цена самого дешёвого прохода класса в сегодняшнем каталоге; объявите "
            "в листе поле model, и смета станет ценой конкретной модели"
        )
    if cost.get("unsource_money_ids"):
        notes.append(
            "cost_usd без cost_source у листьев: "
            + ", ".join(cost["unsource_money_ids"])
            + " — у денег нет метки measured или provisional"
        )
    # A leaf that declares no cost of its own is priced by the kernel, and the
    # owner has to be told where that number came from: the catalog snapshot
    # and the label of the rate behind the tokens. Dropping the field from a
    # leaf cannot be silent.
    undeclared = [
        leaf.id
        for leaf in graph.leaves
        if leaf.cost_usd is None
        and leaf.status != STATUS_DEFERRED
        and cost["leaves"].get(leaf.id, {}).get("state") == "priced"
    ]
    if undeclared:
        snapshot = cost.get("snapshot") or {}
        source = (
            f"снимку каталога {str(snapshot.get('sha256'))[:12]}"
            if snapshot.get("sha256") else "каталогу"
        )
        classes = ", ".join(
            f"{tier} {label}"
            for tier, label in sorted((cost.get("tier_labels") or {}).items())
        )
        notes.append(
            "листья не объявили свою стоимость: " + ", ".join(undeclared)
            + f" — цифры посчитаны ядром по {source}"
            + (f" ({classes})" if classes else "")
            + "; объявьте cost_usd + cost_source, если у листа есть своя цифра"
        )
    if cost.get("frontier_on_small_ids"):
        detail = ", ".join(
            f"{leaf_id} {fmt_usd(cost['leaves'].get(leaf_id, {}).get('usd'))}"
            for leaf_id in cost["frontier_on_small_ids"]
        )
        notes.append(
            "дорогой класс на простой работе: " + detail
            + " — лист сам объявил complexity S и одновременно класс frontier"
        )
    if cost.get("single_sample_tpm_ids"):
        notes.append(
            f"скорость токенов measured по одному замеру у листьев: "
            + ", ".join(cost["single_sample_tpm_ids"])
            + " — одна проба это порядок величины, а не ряд"
        )
    for leaf in graph.leaves:
        entry = cost["leaves"].get(leaf.id, {})
        state = entry.get("state")
        if state in ("no_class", "model_not_resolved", "class_not_resolved", "no_duration"):
            notes.append(f"{leaf.id}: {entry.get('text')}")
        elif state == "priced" and entry.get("divergence_pct") is not None:
            notes.append(
                f"{leaf.id}: лист объявил {fmt_usd(entry.get('declared_usd'))}, "
                f"каталог считает {fmt_usd(entry.get('usd'))} — расхождение "
                f"{entry['divergence_pct']}%"
            )
        elif state == "priced" and entry.get("declared_usd") == 0:
            notes.append(
                f"{leaf.id}: лист объявил нулевую стоимость, каталог считает "
                f"{fmt_usd(entry.get('usd'))}"
            )
    return notes


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
    # The money and the staffing are read out loud here, but they are never an
    # error: a stale snapshot or a frontier leaf on a simple job is a finding a
    # human weighs, not a reason for the tool to refuse a plan.
    cost = _cost_of(graph, build_metrics(graph))
    warnings = cost_warnings(graph, cost) + staffing_warnings(graph, cost)
    # The cap of the format is not a taste but a norm: a leaf over it is two
    # leaves, and only a leaf that says why it is deliberately larger passes.
    # The gate that refuses the plan lives with the leaf files
    # (`lhc_plan_json.py check`); here the breach is named, so a plan that
    # carries one is never rendered as if it were ordinary.
    warnings.extend(estimate_cap_warnings(graph))
    payload = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "leaves": len(graph.leaves),
        "slots": graph.slots,
        "source": graph.source_path,
        "cost": {
            "available": cost["available"],
            "total_usd": cost["total_usd"],
            "frontier_usd": cost["frontier_usd"],
            "frontier_share_pct": cost["frontier_share_pct"],
            "budget_usd": cost["budget_usd"],
            "priced_count": cost["priced_count"],
            "leaf_count": cost["leaf_count"],
            "unpriced_ids": cost["unpriced_ids"],
            "frontier_count": cost["frontier_count"],
            "fast_count": cost["fast_count"],
            # The label of the money: the JSON a machine reads carries the
            # same source label the page shows next to the figure.
            "label": cost["label"],
            "tier_labels": cost["tier_labels"],
            "busy_owners": len(
                {owner_key(leaf) for leaf in graph.leaves if leaf.status == STATUS_RUNNING}
            ),
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def command_check_plan(args: argparse.Namespace) -> int:
    """Reconcile the report's task list with the graph's leaves."""

    report = load_plan_report(args.report)
    graph = load_graph_document(args.graph)
    result = compare_plan_with_graph(report, graph)
    shape_notes = check_plan_shape(report, graph)
    print(f"Отчёт: {args.report}")
    print(f"Граф:   {args.graph}")
    print(
        f"Задач в отчёте: {len(report.leaves)} · листьев в графе: {len(graph.leaves)}"
        + (f" · сопоставлено по названию: {result.matched_by_label}" if result.matched_by_label else "")
        + (
            f" · сопоставлено по позиции, а не по id: {result.matched_by_position}"
            if result.matched_by_position
            else ""
        )
    )
    if result.ok and not shape_notes:
        print("OK: задачи отчёта и листья графа совпадают — идентификаторы, статусы, зависимости и указанные описания.")
        if result.matched_by_position:
            # The match was honest, but it was a guess: the report named no
            # leaf, so the rows were paired by their number. The reader has to
            # know that the agreement is positional.
            print(
                f"ВНИМАНИЕ: {result.matched_by_position} задач сопоставлено по позиции, а не по id — "
                "строки отчёта не называют свой лист. Напишите id листа в строке отчёта, "
                "чтобы сверка опиралась на идентификатор, а не на порядок строк."
            )
        return 0
    print("РАСХОЖДЕНИЕ между отчётом и графом:")
    if result.position_mismatch:
        print("  порядок строк отчёта не совпадает с порядком листьев графа:")
        for leaf, target, elsewhere in result.position_mismatch:
            print(
                f"    - строка «{leaf.label}» стоит на месте {target.id} «{target.label}», "
                f"а по названию это {elsewhere.id} «{elsewhere.label}» — "
                "строка отчёта не называет свой лист, поэтому порядок строк и есть расхождение"
            )
    if shape_notes:
        print("  форма плана в шапке отчёта не совпадает с графом:")
        for note in shape_notes:
            print(f"    - {note}")
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
    if result.dependency_mismatch:
        print("  разные зависимости:")
        for leaf, _target, lost_in_graph, unmentioned in result.dependency_mismatch:
            parts = []
            if lost_in_graph:
                parts.append("в графе потеряны зависимости: " + ", ".join(lost_in_graph))
            if unmentioned:
                parts.append("в отчёте не упомянуты зависимости: " + ", ".join(unmentioned))
            print(f"    - {leaf.id} «{leaf.label}»: " + "; ".join(parts))
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
        "pdf": command_pdf,
    }
    try:
        return handlers[args.command](args)
    except (OSError, ValueError) as error:
        print(f"lhc_grid: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
