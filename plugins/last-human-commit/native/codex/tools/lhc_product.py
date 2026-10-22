#!/usr/bin/env python3
"""Render the delivery side of a plan from the audit-data shape.

The dashboard (:mod:`lhc_grid`) answers one question: what is the state of
the work right now. This module answers the other half of the same plan:
what was checked, what was concluded, what is left to do, and what exactly
goes to the executor.

It turns the ``audit-data`` island of a finished audit page into HTML
fragments that can be embedded into the dashboard page, so both halves read
as one product in light and dark.

Public API
----------
``product_leaves(data)``
    The tasks of the audit as dashboard leaves.
``render_product_sections(data, *, theme_palette=None, group="all")``
    The HTML of the delivery sections. The ``group`` splits them into the
    plan (the grid and the works) and the evidence behind it.
``product_styles()``
    The CSS of those sections.
``product_scripts()``
    The JavaScript of those sections.

Rules of the module
-------------------
* offline, standard library only, no build step;
* every value that comes from the data goes through :func:`escape`;
* the theme is the dashboard theme: the same custom property names, one
  palette, never a second one;
* the fragments carry no ``<html>``, ``<head>``, ``<body>`` or ``<style>`` of
  their own: the CSS and the JS are returned separately.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

# --------------------------------------------------------------------------
# theme
# --------------------------------------------------------------------------

# The names the dashboard already uses. The product does not add a palette of
# its own: it borrows the very same custom properties, so a merged page has
# one theme instead of two.
THEME_VARIABLE_NAMES = (
    "bg", "panel", "panel-2", "line", "text", "muted", "accent",
    "ok", "warn", "bad",
    "st-done", "st-running", "st-blocked", "st-waiting", "st-deferred", "st-queued",
)

_PALETTE_CACHE: Optional[dict[str, dict[str, str]]] = None


def dashboard_palette() -> dict[str, dict[str, str]]:
    """The one palette of the dashboard, read from the neighbouring module.

    The product never invents colors: when the dashboard module cannot be
    loaded the product simply inherits the custom properties of the page it
    is embedded in.
    """

    global _PALETTE_CACHE
    if _PALETTE_CACHE is not None:
        return _PALETTE_CACHE
    palette: dict[str, dict[str, str]] = {}
    name = "_lhc_grid_palette"
    try:
        path = Path(__file__).resolve().with_name("lhc_grid.py")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            # The dataclasses of the dashboard look their own module up in
            # sys.modules, so it has to be there before the code runs.
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
            finally:
                sys.modules.pop(name, None)
            found = getattr(module, "THEME_PALETTE", None)
            if isinstance(found, dict):
                palette = found
    except Exception:  # a missing neighbour must not take the page down
        palette = {}
    _PALETTE_CACHE = palette
    return palette


def _theme_vars(values: Optional[dict[str, str]], theme: str) -> str:
    """The custom properties of one theme, scoped to the product root.

    The values live in ``--lhc-<theme>-<name>`` so a caller-supplied palette
    can be inlined on the root element and still follow the light/dark
    attribute of the page.
    """

    if values:
        return "".join(
            f"--{name}:var(--lhc-{theme}-{name},{value});"
            for name, value in values.items()
            if re.fullmatch(r"[a-zA-Z0-9_-]+", str(name))
        )
    return "".join(f"--{name}:inherit;" for name in THEME_VARIABLE_NAMES)


def _palette_style(palette: Optional[dict[str, dict[str, str]]]) -> str:
    """The inline custom properties of a palette, for the product root."""

    if not palette:
        return ""
    parts = []
    for theme, values in palette.items():
        if not isinstance(values, dict) or not re.fullmatch(r"[a-zA-Z0-9_-]+", str(theme)):
            continue
        for name, value in values.items():
            if re.fullmatch(r"[a-zA-Z0-9_-]+", str(name)):
                parts.append(f"--lhc-{theme}-{name}:{escape(value)};")
    return " ".join(parts)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def escape(text: Any) -> str:
    """Escape a value for HTML, the way the dashboard escapes it."""

    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _number(value: Any) -> Optional[float]:
    """A finite number out of a value, or nothing."""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        match = re.search(r"\d+(?:[.,]\d+)?", value)
        if match:
            try:
                return float(match.group(0).replace(",", "."))
            except ValueError:
                return None
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: Any) -> str:
    """A safe token for a class name or an anchor."""

    token = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "")).strip("-").lower()
    return token or "x"


def _fmt_hours(value: Optional[float]) -> str:
    """An amount of hours, short and readable."""

    if value is None:
        return "—"
    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))
    return f"{value:,.1f}".replace(",", " ")


def _fmt_range(low: Optional[float], high: Optional[float]) -> str:
    if low is None and high is None:
        return "—"
    if low is None or high is None:
        return f"{_fmt_hours(low if low is not None else high)} ч"
    if abs((high or 0) - (low or 0)) < 0.01:
        return f"{_fmt_hours(low)} ч"
    return f"{_fmt_hours(low)}–{_fmt_hours(high)} ч"


def _safe_color(value: Any) -> str:
    """A color that may be inlined into a style attribute."""

    text = _text(value)
    if re.fullmatch(r"#[0-9a-fA-F]{3,8}", text) or re.fullmatch(r"(rgb|rgba|hsl|hsla)\([^()]*\)", text):
        return text
    return "var(--accent)"


def _safe_url(value: Any) -> str:
    """A link that may be followed; anything else is not a link at all."""

    text = _text(value)
    if re.match(r"^(https?:)?//", text, re.IGNORECASE):
        return text
    return ""


def _join(parts: Any) -> str:
    """The non-empty parts of a sequence, joined by a middle dot."""

    return " · ".join(str(part) for part in parts if part)


def _list(items: Any) -> str:
    """A list of strings, or nothing when the list is empty."""

    rows = "".join(f"<li>{escape(item)}</li>" for item in items or [])
    return f'<ul class="lhc-list">{rows}</ul>' if rows else ""


def _refs(ids: Any) -> str:
    """Source id chips that jump to the source card."""

    chips = [
        f'<a class="lhc-ref" href="#lhc-source-{escape(_text(i))}">{escape(_text(i))}</a>'
        for i in ids or [] if _text(i)
    ]
    return f'<div class="lhc-refs">{"".join(chips)}</div>' if chips else ""


def _task_refs(ids: Any) -> str:
    """Task id chips that jump to the work card of the task."""

    chips = [
        f'<a class="lhc-ref lhc-ref--task" href="#lhc-work-{escape(_text(i))}">{escape(_text(i))}</a>'
        for i in ids or [] if _text(i)
    ]
    return f'<div class="lhc-refs">{"".join(chips)}</div>' if chips else ""


REQUIREMENT_STATUS_LABELS = {
    "ready": "Реализовано",
    "partial": "Частично",
    "missing": "Не выполнено",
    "unverified": "Не проверено",
}

SUMMARY_STATUS_LABELS = {
    "ready": "Уже реализовано",
    "missing": "Подтверждённые разрывы",
    "unverified": "До готовности продукта",
}

LEAF_STATUSES = ("done", "running", "blocked", "waiting", "deferred", "queued")


def _status_chip(status: Any, label: Any = None) -> str:
    """The chip of a verdict."""

    kind = _slug(status)
    text = _text(label) or REQUIREMENT_STATUS_LABELS.get(kind, kind)
    return f'<span class="lhc-chip lhc-chip--{kind}"><i class="lhc-dot"></i>{escape(text)}</span>'


def _note_block(item: dict[str, Any]) -> str:
    """One note, with the styling its type asks for."""

    kind = _slug(item.get("type") or "normal")
    if kind not in ("blue", "red", "warn", "green", "normal"):
        kind = "normal"
    return (
        f'<div class="lhc-note lhc-note--{kind} lhc-note-block">'
        f'<strong class="lhc-note-title">{escape(item.get("title"))}</strong>'
        f'<p class="lhc-note-text">{escape(item.get("text"))}</p>'
        f"{_refs(item.get('sources'))}</div>"
    )


# --------------------------------------------------------------------------
# leaves
# --------------------------------------------------------------------------


def product_leaves(data: Any) -> list[dict[str, Any]]:
    """The tasks of an audit as leaves the dashboard table understands.

    A task carries no executed state in the audit data, so it stays
    ``queued``: the product never invents a finished step.
    """

    tasks = (data or {}).get("tasks") or []
    leaves: list[dict[str, Any]] = []
    for index, raw in enumerate(tasks):
        task = raw if isinstance(raw, dict) else {}
        ident = _text(task.get("id")) or f"W{index + 1:02d}"
        label = _text(task.get("title")) or _text(task.get("label")) or ident

        state = _text(task.get("status")) or _text(task.get("state"))
        status = state if state in LEAF_STATUSES else "queued"

        hours = task.get("hours") if isinstance(task.get("hours"), dict) else {}
        low = _number(hours.get("min"))
        high = _number(hours.get("max"))
        base = _number(hours.get("base"))
        if base is None and low is not None and high is not None:
            base = (low + high) / 2.0
        if base is None:
            base = low if low is not None else high

        locks = [_text(lock) for lock in (task.get("locks") or []) if _text(lock)]
        note = _join([
            f"приоритет {_text(task.get('priority'))}" if _text(task.get("priority")) else "",
            "блокировки: " + ", ".join(locks) if locks else "",
            f"репозиторий: {_text(task.get('repo'))}" if _text(task.get("repo")) else "",
        ])

        leaves.append({
            "id": ident,
            "label": label,
            "status": status,
            "owner": _text(task.get("owner")),
            # The flat names the plan dashboard uses, plus the base of the
            # estimate: the middle of the range is the working one.
            "estimate_minutes": low,
            "estimate_max_minutes": high,
            "estimate_base_minutes": base,
            # The same bounds under the field names of the dashboard leaf.
            "estimate_min": low,
            "estimate_max": high,
            "depends_on": [_text(dep) for dep in (task.get("deps") or [])],
            "note": note,
        })
    return leaves


# --------------------------------------------------------------------------
# schedule
# --------------------------------------------------------------------------

SLOT_HOURS = 4
SLOTS_PER_DAY = 2
DEFAULT_WORKERS = 2
DEFAULT_MODE = "base"
WEEKDAY_LABELS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _hours_of(task: dict[str, Any], mode: str) -> float:
    hours = task.get("hours") if isinstance(task.get("hours"), dict) else {}
    for key in (mode, "base", "min"):
        value = _number(hours.get(key))
        if value is not None:
            return value
    return 0.0


def compute_schedule(
    tasks: list[dict[str, Any]],
    *,
    workers: int = DEFAULT_WORKERS,
    mode: str = DEFAULT_MODE,
) -> list[dict[str, Any]]:
    """Place every task on a grid of half-day slots.

    Dependencies and repository locks push a task later; the workers pull
    it into the earliest free stream. The result is the schedule the
    finished audit page computed in the browser, computed here so the HTML
    is complete before any script runs.
    """

    workers = max(1, int(workers))
    placed: dict[str, dict[str, Any]] = {}
    free = [0.0] * workers
    lock_free: dict[str, float] = {}
    pending = [task for task in tasks if isinstance(task, dict)]

    while pending:
        best: Optional[tuple[float, int, int, int]] = None
        for index, task in enumerate(pending):
            deps = [_text(dep) for dep in (task.get("deps") or [])]
            if any(dep not in placed for dep in deps):
                continue
            dep_end = max([placed[dep]["end"] for dep in deps] + [0.0])
            locks = [_text(lock) for lock in (task.get("locks") or [])]
            lock_end = max([lock_free.get(lock, 0.0) for lock in locks] + [0.0])
            slots = max(1, math.ceil(_hours_of(task, mode) / SLOT_HOURS))
            for worker in range(workers):
                candidate = (max(dep_end, lock_end, free[worker]), index, worker, slots)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
        if best is None:
            # A dependency cycle has no schedule. The rest of the plan still
            # belongs on the page, so the loop stops instead of raising.
            break
        begin, index, worker, slots = best
        task = pending.pop(index)
        ident = _text(task.get("id"))
        placed[ident] = {"id": ident, "task": task, "start": begin,
                         "end": begin + slots, "slots": slots, "worker": worker}
        free[worker] = begin + slots
        for lock in task.get("locks") or []:
            lock_free[_text(lock)] = begin + slots

    return sorted(placed.values(), key=lambda item: (item["start"], item["id"]))


def _start_date(value: Any) -> date:
    try:
        return date.fromisoformat(_text(value))
    except ValueError:
        return date.today()


def _work_date(start: date, offset: int) -> date:
    """The working day number ``offset`` after ``start``; weekends are out."""

    current = start
    while current.weekday() >= 5:
        current += timedelta(days=1)
    counted = 0
    while counted < offset:
        current += timedelta(days=1)
        if current.weekday() < 5:
            counted += 1
    return current


def _fmt_date(value: date) -> str:
    return f"{value.day:02d}.{value.month:02d}.{value.year}"


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------


def _section(section_id: str, number: str, title: str, subtitle: str, body: str) -> str:
    return (
        f'<section id="{escape(section_id)}" class="lhc-section">'
        f'<div class="lhc-section-head">'
        f'<span class="lhc-section-number">{escape(number)}</span>'
        f'<h3 class="lhc-section-title">{escape(title)}</h3>'
        f'<p class="lhc-section-sub">{escape(subtitle)}</p></div>{body}</section>'
    )


def _hero(data: dict[str, Any], *, with_theme: bool = True) -> str:
    meta = _join([
        _text(data.get("reportId")),
        _text(data.get("auditDateLabel")),
        f"схема {data.get('schemaVersion')}" if data.get("schemaVersion") is not None else "",
        f"старт плана {_text(data.get('planStart'))}" if _text(data.get("planStart")) else "",
    ])
    return (
        '<div class="lhc-hero"><div class="lhc-hero-main">'
        '<p class="lhc-eyebrow">Аудит · план доработок</p>'
        f'<h2 class="lhc-title">{escape(data.get("title"))}</h2>'
        f'<p class="lhc-lead">{escape(data.get("lead"))}</p>'
        f'<p class="lhc-meta">{escape(meta)}</p></div>'
        '<div class="lhc-hero-side"><span class="lhc-label">Метод проверки</span>'
        f'<p class="lhc-method">{escape(data.get("method"))}</p>'
        '<div class="lhc-actions">'
        '<button type="button" class="lhc-btn" id="lhc-download-json">Скачать план JSON</button>'
        + (
            '<button type="button" class="lhc-btn" id="lhc-theme-toggle" aria-label="Переключить тему">'
            'Светлая / тёмная</button>'
            if with_theme
            else ''
        )
        + '</div></div></div>'
    )


NAV_ITEMS = (
    ("lhc-summary", "Выводы"),
    ("lhc-notes", "Замечания"),
    ("lhc-metrics", "Метрики"),
    ("lhc-requirements", "Требования"),
    ("lhc-health", "Сервисы"),
    ("lhc-gantt", "Гант"),
    ("lhc-work", "Работы"),
    ("lhc-rules", "Правила"),
    ("lhc-agent", "Задание"),
    ("lhc-sources", "Источники"),
    ("lhc-spec", "Спецификация"),
)


def _nav() -> str:
    links = "".join(
        f'<a class="lhc-nav-link" href="#{escape(anchor)}">{escape(label)}</a>'
        for anchor, label in NAV_ITEMS
    )
    return f'<nav class="lhc-nav" aria-label="Разделы">{links}</nav>'


def _summary_section(data: dict[str, Any]) -> str:
    cards = []
    for item in data.get("summary") or []:
        if not isinstance(item, dict):
            continue
        status = _slug(item.get("status"))
        label = _text(item.get("label")) or SUMMARY_STATUS_LABELS.get(status, status)
        cards.append(
            f'<article class="lhc-card lhc-card--{status}">{_status_chip(status, label)}'
            f'<h4 class="lhc-card-title">{escape(item.get("title"))}</h4>'
            f"{_list(item.get('items'))}{_refs(item.get('sources'))}</article>"
        )
    body = f'<div class="lhc-cards">{"".join(cards)}</div>' if cards else ""
    return _section(
        "lhc-summary", "01 / РЕЗУЛЬТАТ ПРОВЕРКИ", "На что уже можно опереться",
        "Выводы аудита: что реализовано, где подтверждённый разрыв и что ещё не проверено.",
        body,
    )


def _notes_section(data: dict[str, Any]) -> str:
    blocks = [_note_block(item) for item in data.get("notes") or [] if isinstance(item, dict)]
    body = f'<div class="lhc-notes">{"".join(blocks)}</div>' if blocks else ""
    return _section(
        "lhc-notes", "02 / ЗАМЕЧАНИЯ", "Что стоит знать до начала работ",
        "Уточнения, которые меняют способ реализации.", body,
    )


def _metrics_section(data: dict[str, Any]) -> str:
    requirements = [i for i in data.get("requirements") or [] if isinstance(i, dict)]
    total = len(requirements)
    tiles = []
    for status in ("ready", "partial", "missing", "unverified"):
        count = sum(1 for item in requirements if _slug(item.get("status")) == status)
        tiles.append(
            f'<div class="lhc-metric lhc-metric--{status}"><b>{count}</b>'
            f"<span>{escape(REQUIREMENT_STATUS_LABELS[status])} · из {total} требований</span></div>"
        )
    tiles.append(
        f'<div class="lhc-metric lhc-metric--total"><b>{total}</b>'
        "<span>Всего требований в матрице</span></div>"
    )
    body = (
        f'<div class="lhc-metrics">{"".join(tiles)}</div>'
        f'<p class="lhc-note lhc-note--plain">{escape(data.get("coverageNote"))}</p>'
    )
    return _section(
        "lhc-metrics", "03 / СЧЁТ", "Готовность по требованиям",
        "Процент готовности продукта не вычисляется: считаются подтверждённые требования.",
        body,
    )


def _requirements_section(data: dict[str, Any]) -> str:
    rows = []
    for item in data.get("requirements") or []:
        if not isinstance(item, dict):
            continue
        status = _slug(item.get("status"))
        searchable = " ".join(
            _text(item.get(key)) for key in ("id", "component", "title", "found", "remaining")
        ).lower()
        rows.append(
            f'<tr class="lhc-row" data-lhc-status="{escape(status)}" '
            f'data-lhc-text="{escape(searchable)}">'
            '<td data-label="Требование">'
            f'<span class="lhc-mono">{escape(_text(item.get("id")))} · '
            f'{escape(item.get("component"))}</span>'
            f'<strong class="lhc-cell-title">{escape(item.get("title"))}</strong></td>'
            '<td data-label="Вердикт">'
            f'{_status_chip(status)}<p class="lhc-caption">{escape(item.get("proof"))}</p></td>'
            '<td data-label="Что найдено">'
            f'<p class="lhc-cell-text">{escape(item.get("found"))}</p>'
            f"{_refs(item.get('sources'))}</td>"
            '<td data-label="Что осталось">'
            f'<p class="lhc-cell-text">{escape(item.get("remaining"))}</p>'
            f"{_task_refs(item.get('tasks'))}</td></tr>"
        )
    table = (
        '<div class="lhc-table-wrap"><table class="lhc-table lhc-req-table">'
        "<thead><tr><th>Требование</th><th>Вердикт</th>"
        "<th>Что найдено</th><th>Что осталось</th></tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )
    chips = ['<button type="button" class="lhc-chip lhc-chip--btn is-active" '
             'data-lhc-req-filter="all">Все</button>']
    for status in ("ready", "partial", "missing", "unverified"):
        chips.append(
            '<button type="button" class="lhc-chip lhc-chip--btn" '
            f'data-lhc-req-filter="{escape(status)}">'
            f"{escape(REQUIREMENT_STATUS_LABELS[status])}</button>"
        )
    toolbar = (
        '<div class="lhc-toolbar">'
        '<input class="lhc-input" type="search" id="lhc-req-search" '
        'placeholder="Поиск: приёмка, 30 минут, сообщения…" aria-label="Поиск по требованиям">'
        f'<div class="lhc-chips">{"".join(chips)}</div>'
        f'<span class="lhc-count" id="lhc-req-count">{len(rows)} из {len(rows)}</span></div>'
    )
    return _section(
        "lhc-requirements", "04 / СВЕРКА СО СПЕЦИФИКАЦИЕЙ", "Готовность по требованиям",
        "Для статуса «Реализовано» указан уровень доказательства: код или наблюдаемый runtime.",
        toolbar + table,
    )


def _health_section(data: dict[str, Any]) -> str:
    rows = []
    for item in data.get("health") or []:
        if not isinstance(item, dict):
            continue
        url = _safe_url(item.get("url"))
        link = (f'<p class="lhc-cell-text"><a class="lhc-link" href="{escape(url)}" '
                'target="_blank" rel="noopener">Открыть приложение</a></p>') if url else ""
        rows.append(
            '<tr class="lhc-row lhc-row--health">'
            '<td data-label="Компонент">'
            f'<strong class="lhc-cell-title">{escape(item.get("name"))}</strong>'
            f'<p class="lhc-caption lhc-mono">{escape(item.get("repo"))}</p></td>'
            '<td data-label="Исходный сервис и код">'
            f'<p class="lhc-cell-text">{escape(item.get("native"))}</p>'
            f"{_refs(item.get('sources'))}</td>"
            '<td data-label="Доступ через Airlock">'
            f'<p class="lhc-cell-text">{escape(item.get("app"))}</p>{link}</td>'
            '<td data-label="Вывод для плана">'
            f'<p class="lhc-cell-text">{escape(item.get("conclusion"))}</p></td></tr>'
        )
    table = (
        '<div class="lhc-table-wrap"><table class="lhc-table lhc-health-table">'
        "<thead><tr><th>Компонент</th><th>Исходный сервис и код</th>"
        "<th>Доступ через Airlock</th><th>Вывод для плана</th></tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )
    return _section(
        "lhc-health", "05 / ТЕКУЩЕЕ ОКРУЖЕНИЕ", "Сервисы и точки подключения",
        "Состояние исходного сервиса, его кода и приложения внутри Airlock учитывается раздельно.",
        table,
    )


# The geometry of the grid. The heights are the source of truth of the
# server-side arrow geometry; the script measures the rows and corrects the
# arrows when the scale changes.
GANTT_DAY_WIDTH = 64
GANTT_ROW_HEIGHT = 68
GANTT_BAND_HEIGHT = 48


def _task_index(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The tasks of the plan by their id."""

    index: dict[str, dict[str, Any]] = {}
    for task in tasks:
        ident = _text(task.get("id"))
        if ident:
            index[ident] = task
    return index


def _task_deps(task: dict[str, Any]) -> list[str]:
    """The ids the task waits for."""

    return [_text(dep) for dep in (task.get("deps") or []) if _text(dep)]


def _blocks_map(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """The tasks each task holds back: who waits for whom."""

    blocks: dict[str, list[str]] = {}
    for task in tasks:
        ident = _text(task.get("id"))
        for dep in _task_deps(task):
            blocks.setdefault(dep, []).append(ident)
    return blocks


def _gantt_flags(waits: list[str], held: list[str]) -> str:
    """The markers of a row: what it waits for and what it holds back."""

    chips = []
    if waits:
        chips.append(
            f'<span class="lhc-flag lhc-flag--wait">ждёт {escape(", ".join(waits))}</span>'
        )
    if held:
        chips.append(
            f'<span class="lhc-flag lhc-flag--block" data-lhc-count="{len(held)}">'
            f'блокирует {escape(", ".join(held))}</span>'
        )
    if not chips:
        return ""
    return f'<span class="lhc-gantt-flags">{"".join(chips)}</span>'


def _gantt_paths(
    tasks: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
    *,
    band_count: int = 0,
) -> str:
    """One arrow per dependency of the plan.

    The arrow leaves the end of the dependency and enters the start of the
    dependent task, so the owner sees what waits for what.
    """

    placed_by_id = {item["id"]: item for item in schedule}
    tasks_by_id = _task_index(tasks)
    order = [_text(task.get("id")) for task in tasks]
    row_of = {ident: index for index, ident in enumerate(order)}
    px_per_slot = GANTT_DAY_WIDTH / float(SLOTS_PER_DAY)
    top = band_count * GANTT_BAND_HEIGHT

    def centre(ident: str) -> float:
        return top + row_of[ident] * GANTT_ROW_HEIGHT + GANTT_ROW_HEIGHT / 2.0

    parts = []
    for ident in order:
        task = tasks_by_id.get(ident)
        target = placed_by_id.get(ident)
        if not task or not target:
            continue
        for dep in _task_deps(task):
            source = placed_by_id.get(dep)
            if not source or dep not in row_of:
                continue
            x1 = source["end"] * px_per_slot
            x2 = target["start"] * px_per_slot
            elbow = min(x1 + 12, max(x1 + 5, x2 - 7))
            parts.append(
                f'<path class="lhc-net-edge" data-lhc-from="{escape(dep)}" '
                f'data-lhc-to="{escape(ident)}" '
                f'd="M {x1:.1f} {centre(dep):.1f} H {elbow:.1f} V {centre(ident):.1f} H {x2:.1f}" '
                'marker-end="url(#lhc-gantt-arrow)"/>'
            )
    return "".join(parts)


def _task_detail(
    task: dict[str, Any],
    *,
    phase_name: str = "",
    tasks: Optional[dict[str, dict[str, Any]]] = None,
    held: Optional[list[str]] = None,
) -> str:
    """The card of one task: everything the plan knows about it.

    The same card is opened from the grid of the Gantt and from the work
    card, so there is one implementation and one content.
    """

    index = tasks or {}
    ident = _text(task.get("id"))
    priority = _text(task.get("priority"))
    owner = _text(task.get("owner"))
    repo = _text(task.get("repo"))
    hours = task.get("hours") if isinstance(task.get("hours"), dict) else {}
    low = _number(hours.get("min"))
    base = _number(hours.get("base"))
    high = _number(hours.get("max"))
    locks = [_text(lock) for lock in (task.get("locks") or []) if _text(lock)]

    def entry(other_id: str, planned: bool = False) -> str:
        """One dependency: its id, its title and the state the data knows."""

        other = index.get(other_id)
        title = _text(other.get("title")) if other else "работа вне плана"
        chip = ' <span class="lhc-chip lhc-chip--plan">план</span>' if planned else ""
        return (f'<li><span class="lhc-mono">{escape(other_id)}</span> · '
                f'{escape(title)}{chip}</li>')

    tags = [f'<span class="lhc-chip lhc-chip--id">{escape(ident)}</span>']
    if phase_name:
        tags.append(f'<span class="lhc-chip">{escape(phase_name)}</span>')
    if priority:
        tags.append(f'<span class="lhc-chip lhc-chip--priority">{escape(priority)}</span>')
    # The data has no executed state, so a task of the plan is a plan.
    tags.append('<span class="lhc-chip lhc-chip--plan">план</span>')

    waits = "".join(entry(dep, planned=True) for dep in _task_deps(task))
    waits_html = waits or "<li>Можно начинать сразу: предшественников нет.</li>"
    blocked = "".join(entry(other) for other in (held or []))
    blocked_html = blocked or "<li>Ничего не блокирует.</li>"

    head = (
        '<div class="lhc-detail-head">'
        f'<div class="lhc-detail-tags">{"".join(tags)}</div>'
        f'<h4 class="lhc-detail-title">{escape(task.get("title"))}</h4>'
        f'<p class="lhc-caption">Владелец: {escape(owner) or "—"} · '
        f'репозиторий: {escape(repo) or "—"}</p>'
        f'<p class="lhc-caption">Оценка: мин {_fmt_hours(low)} · база {_fmt_hours(base)} · '
        f'макс {_fmt_hours(high)} ч</p>'
        f'<p class="lhc-caption">Блокировки репозиториев: {escape(", ".join(locks)) or "нет"}</p>'
        '<p class="lhc-caption lhc-detail-state">Состояние выполнения в данных не задано: '
        "каждая работа — это план.</p>"
        '<button type="button" class="lhc-btn lhc-detail-gantt" '
        f'data-lhc-gantt-link="{escape(ident)}">Показать в сетке Ганта</button></div>'
    )
    cols = (
        '<div class="lhc-detail-cols">'
        '<div class="lhc-work-col"><h5 class="lhc-work-label">Изменить</h5>'
        f"{_list(task.get('scope'))}</div>"
        '<div class="lhc-work-col"><h5 class="lhc-work-label">Критерий приёмки</h5>'
        f"{_list(task.get('acceptance'))}</div>"
        '<div class="lhc-work-col"><h5 class="lhc-work-label">Уже есть и используется повторно</h5>'
        f'<p class="lhc-cell-text">{escape(task.get("reuse"))}</p>'
        f"{_refs(task.get('sources'))}</div>"
        '<div class="lhc-work-col"><h5 class="lhc-work-label">Зависимости и результат</h5>'
        f'<p class="lhc-cell-text">{escape(task.get("result"))}</p>'
        '<p class="lhc-work-label">Ждёт</p>'
        f'<ul class="lhc-list">{waits_html}</ul>'
        '<p class="lhc-work-label">Блокирует</p>'
        f'<ul class="lhc-list">{blocked_html}</ul></div>'
        "</div>"
    )
    return f'<div class="lhc-detail" data-lhc-detail="{escape(ident)}">{head}{cols}</div>'



def _gantt_section(data: dict[str, Any]) -> str:
    tasks = [task for task in data.get("tasks") or [] if isinstance(task, dict)]
    phases = [phase for phase in data.get("phases") or [] if isinstance(phase, dict)]
    phase_by_id = {_text(phase.get("id")): phase for phase in phases}
    tasks_by_id = _task_index(tasks)
    blocks = _blocks_map(tasks)

    schedule = compute_schedule(tasks)
    days = max(1, math.ceil(max((item["end"] for item in schedule), default=0) / SLOTS_PER_DAY))
    columns = max(days, 8)
    start = _start_date(data.get("planStart"))
    finish = _work_date(start, max(0, days - 1))
    low_days = max(1, math.ceil(max((i["end"] for i in compute_schedule(tasks, mode="min")), default=0) / SLOTS_PER_DAY))
    high_days = max(1, math.ceil(max((i["end"] for i in compute_schedule(tasks, mode="max")), default=0) / SLOTS_PER_DAY))
    effort = sum(_hours_of(task, DEFAULT_MODE) for task in tasks)

    meta = (
        '<div class="lhc-gantt-meta">'
        f'<div><span>Оценка завершения</span><b>{escape(_fmt_date(finish))}</b>'
        "<span>при выбранных допущениях</span></div>"
        f'<div><span>Длина плана</span><b>{days} раб. дн.</b>'
        f"<span>диапазон {low_days}–{high_days} рабочих дней</span></div>"
        f'<div><span>Трудоёмкость</span><b>{_fmt_hours(effort)} ч</b>'
        "<span>сумма работ, без ожидания внешних ответов</span></div>"
        f'<div><span>Исполнение</span><b>{DEFAULT_WORKERS} потока</b>'
        "<span>8 часов на рабочий день</span></div></div>"
    )

    day_cells = "".join(
        '<div class="lhc-gantt-day">'
        f"<span>Д{index + 1} · {WEEKDAY_LABELS[day.weekday()]}</span>"
        f"<strong>{day.day:02d}.{day.month:02d}</strong></div>"
        for index, day in enumerate(_work_date(start, index) for index in range(columns))
    )

    span = float(columns * SLOTS_PER_DAY)
    placed_by_id = {item["id"]: item for item in schedule}

    bands = []
    for phase in phases:
        ident = _text(phase.get("id"))
        color = _safe_color(phase.get("color"))
        members = [item for item in schedule if _text(item["task"].get("phase")) == ident]
        if not members:
            continue
        left = 100.0 * min(item["start"] for item in members) / span
        width = max(1.5, 100.0 * (max(item["end"] for item in members)
                                 - min(item["start"] for item in members)) / span)
        hours = sum(_hours_of(t, DEFAULT_MODE) for t in tasks if _text(t.get("phase")) == ident)
        bands.append(
            f'<div class="lhc-gantt-band" data-lhc-phase="{escape(ident)}">'
            '<div class="lhc-gantt-band-label">'
            '<span class="lhc-gantt-band-line">'
            f'<i class="lhc-swatch" style="background:{escape(color)}"></i>'
            f'<strong>{escape(phase.get("name"))}</strong></span>'
            f'<span class="lhc-band-meta">{len(members)} работ · {_fmt_hours(hours)} ч</span></div>'
            '<div class="lhc-gantt-track">'
            f'<span class="lhc-band" style="left:{left:.4f}%;width:{width:.4f}%;'
            f'background:{escape(color)}"></span></div></div>'
        )

    rows = []
    for task in tasks:
        ident = _text(task.get("id"))
        color = _safe_color(phase_by_id.get(_text(task.get("phase")), {}).get("color"))
        placed = placed_by_id.get(ident)
        hours = task.get("hours") if isinstance(task.get("hours"), dict) else {}
        meta_line = _join([
            _text(task.get("owner")),
            _fmt_range(_number(hours.get("min")), _number(hours.get("max"))),
            _text(task.get("priority")),
        ])
        waits = [dep for dep in _task_deps(task) if dep in tasks_by_id]
        held = blocks.get(ident, [])
        waits_text = ", ".join(waits)
        held_text = ", ".join(held)
        title = f"{ident} · {_text(task.get('title'))} · {_fmt_hours(_hours_of(task, DEFAULT_MODE))} ч"
        if placed:
            left = 100.0 * placed["start"] / span
            width = max(1.2, 100.0 * placed["slots"] / span)
            bar = (f'<button type="button" class="lhc-bar" data-lhc-task="{escape(ident)}" '
                   f'style="left:{left:.4f}%;width:{width:.4f}%;'
                   f'background:{escape(color)}" title="{escape(title)}" '
                   f'aria-label="{escape(title)}">'
                   f'<span class="lhc-bar-id">{escape(ident)}</span></button>')
        else:
            bar = '<span class="lhc-bar lhc-bar--free" title="Нет расписания"></span>'
        rows.append(
            f'<div class="lhc-gantt-row" data-lhc-task="{escape(ident)}"'
            f' data-lhc-waits="{escape(waits_text)}"'
            f' data-lhc-blocks="{escape(held_text)}">'
            '<button type="button" class="lhc-gantt-label">'
            f"<strong>{escape(ident)} · {escape(task.get('title'))}</strong>"
            f'<span class="lhc-gantt-row-meta">{escape(meta_line)}</span>'
            f"{_gantt_flags(waits, held)}</button>"
            f'<div class="lhc-gantt-track">{bar}</div></div>'
        )

    legend = "".join(
        f'<span><i class="lhc-swatch" style="background:'
        f'{escape(_safe_color(phase.get("color")))}"></i>{escape(phase.get("name"))}</span>'
        for phase in phases
    )
    net = (
        '<svg class="lhc-gantt-net" id="lhc-gantt-net" aria-hidden="true" focusable="false">'
        '<defs><marker id="lhc-gantt-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" '
        'orient="auto" markerUnits="userSpaceOnUse">'
        '<path class="lhc-net-arrow" d="M0,0 L8,4 L0,8 Z"/></marker></defs>'
        + _gantt_paths(tasks, schedule, band_count=len(bands)) + "</svg>"
    )
    gantt = (
        f'<div class="lhc-gantt" id="lhc-gantt-grid" style="--lhc-cols:{columns};'
        f'--lhc-day:{GANTT_DAY_WIDTH}px;--lhc-row-h:{GANTT_ROW_HEIGHT}px;'
        f'--lhc-band-h:{GANTT_BAND_HEIGHT}px" data-lhc-day-base="{GANTT_DAY_WIDTH}">'
        '<div class="lhc-gantt-head"><div class="lhc-gantt-corner">Работа / репозиторий</div>'
        f'<div class="lhc-gantt-days">{day_cells}</div></div>'
        f'<div class="lhc-gantt-body">{"".join(bands)}{"".join(rows)}{net}</div></div>'
    )
    toolbar = (
        '<div class="lhc-toolbar"><span class="lhc-toolbar-label">Масштаб шкалы</span>'
        '<button type="button" class="lhc-btn lhc-btn--icon" data-lhc-zoom="-1" '
        'aria-label="Уменьшить масштаб">−</button>'
        '<input class="lhc-range" type="range" id="lhc-gantt-zoom" min="0.6" max="2.4" step="0.1" '
        'value="1" aria-label="Масштаб шкалы времени">'
        '<button type="button" class="lhc-btn lhc-btn--icon" data-lhc-zoom="1" '
        'aria-label="Увеличить масштаб">+</button>'
        '<output class="lhc-count" id="lhc-gantt-zoom-value">100%</output>'
        '<label class="lhc-switch" for="lhc-gantt-deps">'
        '<input type="checkbox" id="lhc-gantt-deps" checked>'
        '<span>Связи работ</span></label></div>'
    )
    detail = (
        '<div class="lhc-gantt-detail" id="lhc-gantt-detail" hidden>'
        '<div class="lhc-gantt-detail-bar"><span class="lhc-gantt-detail-caption">Карточка работы</span>'
        '<button type="button" class="lhc-btn lhc-btn--icon" id="lhc-gantt-detail-close" '
        'aria-label="Закрыть карточку">×</button></div>'
        '<div class="lhc-gantt-detail-body" id="lhc-gantt-detail-body"></div></div>'
    )
    body = (
        toolbar
        + '<div class="lhc-gantt-shell">' + meta
        + f'<div class="lhc-gantt-scroll">{gantt}</div>'
        + detail
        + '<div class="lhc-gantt-foot">Шкала показывает рабочие дни, половина ячейки — 4 часа. '
        "Работы в одном изменяемом репозитории не накладываются, выходные пропущены. "
        "Нажмите на строку или на полосу работы, чтобы открыть карточку.</div></div>"
        + f'<div class="lhc-legend">{legend}</div>'
        + f'<p class="lhc-note lhc-note--plain">{escape(data.get("estimateNote"))}</p>'
    )
    return _section(
        "lhc-gantt", "06 / ПОСЛЕДОВАТЕЛЬНОСТЬ РАБОТ", "Сетка Ганта",
        "Расчёт учитывает зависимости, доступные потоки и пересечение репозиториев.",
        body,
    )


def _work_section(data: dict[str, Any]) -> str:
    tasks = [task for task in data.get("tasks") or [] if isinstance(task, dict)]
    phases = [phase for phase in data.get("phases") or [] if isinstance(phase, dict)]
    tasks_by_id = _task_index(tasks)
    held_by_id = _blocks_map(tasks)

    blocks = []
    for phase in phases:
        ident = _text(phase.get("id"))
        color = _safe_color(phase.get("color"))
        members = [task for task in tasks if _text(task.get("phase")) == ident]
        if not members:
            continue
        cards = []
        for task in members:
            task_id = _text(task.get("id"))
            hours = task.get("hours") if isinstance(task.get("hours"), dict) else {}
            detail = _task_detail(
                task,
                phase_name=_text(phase.get("name")),
                tasks=tasks_by_id,
                held=held_by_id.get(task_id, []),
            )
            cards.append(
                f'<article class="lhc-work" id="lhc-work-{escape(task_id)}" '
                f'style="--lhc-phase:{escape(color)}">'
                '<button type="button" class="lhc-work-head" aria-expanded="false" '
                f'data-lhc-task="{escape(task_id)}" '
                f'aria-controls="lhc-work-body-{escape(task_id)}">'
                f'<span class="lhc-work-id">{escape(task_id)}</span>'
                '<span class="lhc-work-main">'
                f'<strong class="lhc-work-title">{escape(task.get("title"))}</strong>'
                f'<span class="lhc-work-result">{escape(task.get("result"))}</span></span>'
                '<span class="lhc-work-side">'
                f'<span class="lhc-work-meta">{escape(_join([_text(task.get("owner")), _fmt_range(_number(hours.get("min")), _number(hours.get("max"))), _text(task.get("priority"))]))}</span>'
                '<span class="lhc-work-toggle">Показать</span></span></button>'
                f'<div class="lhc-work-body" id="lhc-work-body-{escape(task_id)}" hidden>'
                f"{detail}</div></article>"
            )
        blocks.append(
            '<div class="lhc-phase"><div class="lhc-phase-head">'
            f'<i class="lhc-swatch" style="background:{escape(color)}"></i>'
            f'<strong class="lhc-phase-name">{escape(phase.get("name"))}</strong>'
            '<span class="lhc-phase-line"></span>'
            f'<span class="lhc-phase-count">{len(members)} работ</span></div>'
            f'<div class="lhc-work-list">{"".join(cards)}</div></div>'
        )
    body = f'<div class="lhc-phases">{"".join(blocks)}</div>' if blocks else ""
    return _section(
        "lhc-work", "07 / ЗАДАНИЯ НА ДОРАБОТКУ", "Работы с проверяемым результатом",
        "Каждая работа привязана к выявленному разрыву. Нажмите на карточку, "
        "чтобы увидеть объём и критерий приёмки.", body,
    )


def _rules_section(data: dict[str, Any]) -> str:
    items = [f"<li>{escape(rule)}</li>" for rule in (data.get("rules") or []) if _text(rule)]
    body = f'<ol class="lhc-rules">{"".join(items)}</ol>' if items else ""
    return _section(
        "lhc-rules", "08 / ПРАВИЛА", "Согласованные правила продукта",
        "Правила, которые исполнение обязано соблюдать.", body,
    )


def _agent_section(data: dict[str, Any]) -> str:
    body = (
        '<div class="lhc-agent">'
        '<h4 class="lhc-card-title">Продолжить работу от проверенного состояния</h4>'
        '<p class="lhc-caption">В задании указаны порядок работ, действующие ограничения '
        "и критерии завершения.</p>"
        f'<pre class="lhc-agent-text" id="lhc-agent-text">{escape(data.get("agentPrompt"))}</pre>'
        '<div class="lhc-actions">'
        '<button type="button" class="lhc-btn lhc-btn--primary" id="lhc-copy-agent" '
        'data-lhc-copy-target="lhc-agent-text">Скопировать задание</button>'
        '<span class="lhc-status" id="lhc-copy-status" role="status" aria-live="polite"></span>'
        "</div></div>"
    )
    return _section(
        "lhc-agent", "09 / ПЕРЕДАЧА ИСПОЛНИТЕЛЮ", "Готовое задание агенту",
        "Задание копируется целиком и вставляется исполнителю без правок.", body,
    )


def _sources_section(data: dict[str, Any]) -> str:
    cards = []
    for item in data.get("sources") or []:
        if not isinstance(item, dict):
            continue
        ident = _text(item.get("id"))
        revision = _text(item.get("revision"))
        excerpt = _text(item.get("excerpt"))
        cards.append(
            f'<article class="lhc-source" id="lhc-source-{escape(ident)}">'
            f'<span class="lhc-mono">{escape(ident)} · {escape(item.get("kind"))} · '
            f'{escape(item.get("time") or data.get("auditDateLabel"))}</span>'
            f'<h4 class="lhc-card-title">{escape(item.get("title"))}</h4>'
            f'<div class="lhc-location">{escape(item.get("location"))}</div>'
            + (f'<div class="lhc-location">Версия: {escape(revision)}</div>' if revision else "")
            + f'<p class="lhc-cell-text">{escape(item.get("finding"))}</p>'
            + ('<details class="lhc-details"><summary>Показать подтверждение</summary>'
               f'<pre class="lhc-excerpt">{escape(excerpt)}</pre></details>' if excerpt else "")
            + "</article>"
        )
    body = f'<div class="lhc-sources">{"".join(cards)}</div>' if cards else ""
    return _section(
        "lhc-sources", "10 / ДОКАЗАТЕЛЬСТВА", "Что именно проверено",
        "Пути, версии, точки чтения и выдержки для повторной проверки.", body,
    )


def _spec_section(data: dict[str, Any]) -> str:
    url = _safe_url(data.get("specUrl"))
    link = (
        f'<a class="lhc-link" id="lhc-spec-link" href="{escape(url)}" target="_blank" '
        'rel="noopener">Открыть оригинал</a>'
        if url
        else f'<span id="lhc-spec-link" class="lhc-caption">{escape(_text(data.get("specUrl")))}</span>'
    )
    body = (
        '<details class="lhc-details lhc-details--flat"><summary>Исходная спецификация</summary>'
        f'<p class="lhc-cell-text">{link}</p>'
        f'<pre class="lhc-spec-text">{escape(data.get("specText"))}</pre></details>'
    )
    return _section(
        "lhc-spec", "11 / СПЕЦИФИКАЦИЯ", "Исходный текст спецификации",
        "Полный текст, по которому сделан этот план.", body,
    )


# --------------------------------------------------------------------------
# public rendering
# --------------------------------------------------------------------------


def product_hero(data: Any, *, with_theme: bool = True) -> str:
    """The headline of the delivery side, on its own.

    The merged page has one headline and one theme switch, so the hero can
    stand alone: the plan page keeps its own header and its own switch.
    """
    payload = data if isinstance(data, dict) else {}
    return _hero(payload, with_theme=with_theme)


def product_nav_items() -> tuple:
    """The anchors of the delivery sections, so the page can build one navigation."""
    return NAV_ITEMS


# The sections of the delivery side, in the order of the page. The groups
# are the two halves the page can place separately: the plan with its grid
# and the evidence behind it.
PRODUCT_SECTIONS: tuple[tuple[str, Any], ...] = (
    ("lhc-summary", _summary_section),
    ("lhc-notes", _notes_section),
    ("lhc-metrics", _metrics_section),
    ("lhc-requirements", _requirements_section),
    ("lhc-health", _health_section),
    ("lhc-gantt", _gantt_section),
    ("lhc-work", _work_section),
    ("lhc-rules", _rules_section),
    ("lhc-agent", _agent_section),
    ("lhc-sources", _sources_section),
    ("lhc-spec", _spec_section),
)

PLAN_SECTIONS = ("lhc-gantt", "lhc-work")

EVIDENCE_SECTIONS = tuple(
    section_id for section_id, _ in PRODUCT_SECTIONS if section_id not in PLAN_SECTIONS
)

PRODUCT_GROUPS = ("all", "plan", "evidence")


def render_product_sections(
    data: Any,
    *,
    theme_palette: Optional[dict] = None,
    group: str = "all",
    include_hero: Optional[bool] = None,
    include_nav: Optional[bool] = None,
) -> str:
    """The HTML of the delivery sections.

    The result is a fragment: it carries no page of its own, so it can be
    dropped into the dashboard page as it is.

    The ``group`` splits the sections into the two halves of the page:

    ``"plan"``
        the grid of the Gantt and the work cards, with the card of a task;
    ``"evidence"``
        the conclusions, the remarks, the metrics, the requirement matrix,
        the services, the rules, the agent task, the sources and the
        specification;
    ``"all"``
        everything, as one block (the default).

    The groups do not share an id, so both can stand on one page: the card
    of a task belongs to the plan group, and the evidence group refers to
    it by its id. The headline and the navigation belong to the plan group
    as well; ``include_hero`` and ``include_nav`` say otherwise.
    """

    key = str(group or "all").strip().lower()
    if key not in PRODUCT_GROUPS:
        raise ValueError(f"unknown product group: {group!r}")
    if include_hero is None:
        include_hero = key != "evidence"
    if include_nav is None:
        include_nav = key != "evidence"
    payload = data if isinstance(data, dict) else {}
    palette = theme_palette if isinstance(theme_palette, dict) else dashboard_palette()
    wanted = {
        "all": tuple(section_id for section_id, _ in PRODUCT_SECTIONS),
        "plan": PLAN_SECTIONS,
        "evidence": EVIDENCE_SECTIONS,
    }[key]

    parts = [
        f'<div class="lhc-product" id="lhc-product-{escape(key)}" '
        f'style="{escape(_palette_style(palette))}">',
        _hero(payload, with_theme=not include_hero) if include_hero else "",
        _nav() if include_nav else "",
    ]
    for section_id, builder in PRODUCT_SECTIONS:
        if section_id in wanted:
            parts.append(builder(payload))
    if key in ("all", "plan"):
        island = json.dumps(payload, ensure_ascii=False, indent=2, default=str).replace("<", "\\u003c")
        parts.append(f'<template id="lhc-plan-json">{island}</template>')
    parts.append("</div>")
    return "".join(parts)


# --------------------------------------------------------------------------
# styles
# --------------------------------------------------------------------------

_STYLES = """
/* ---- the delivery sections of a plan ---- */
.lhc-product{
  /*THEME-DARK*/
}
:root[data-theme="light"] .lhc-product{
  /*THEME-LIGHT*/
}
.lhc-product{color:var(--text);font-size:14px;line-height:1.55;overflow-wrap:anywhere}
.lhc-product *,.lhc-product *::before,.lhc-product *::after{box-sizing:border-box}
.lhc-product h2,.lhc-product h3,.lhc-product h4,.lhc-product h5{margin:0;letter-spacing:-.01em}
.lhc-product p{margin:0 0 10px}
.lhc-product ul,.lhc-product ol{margin:0;padding-left:20px}
.lhc-product li+li{margin-top:6px}
.lhc-product a{color:var(--accent);text-underline-offset:3px}
.lhc-product b{font-weight:650}
.lhc-product [hidden]{display:none!important}

/* ---- hero ---- */
.lhc-hero{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:20px;margin-bottom:14px}
.lhc-eyebrow{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:0 0 8px}
.lhc-title{font-size:26px;line-height:1.2;font-weight:700;margin:0 0 10px}
.lhc-lead{font-size:15px;color:var(--muted);margin:0 0 10px;max-width:900px}
.lhc-meta{font:11.5px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);margin:0}
.lhc-hero-side{background:var(--panel-2);border:1px solid var(--line);border-radius:12px;padding:14px}
.lhc-label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:6px}
.lhc-method{font-size:12.5px;color:var(--muted);margin:0 0 12px}
.lhc-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}

/* ---- buttons ---- */
.lhc-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:44px;min-width:44px;padding:8px 14px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--text);font:inherit;font-size:12.5px;font-weight:600;cursor:pointer}
.lhc-btn:hover{border-color:var(--accent);color:var(--accent)}
.lhc-btn--primary{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.lhc-btn--icon{padding:8px 12px;font-size:16px;line-height:1}
.lhc-btn:focus-visible,.lhc-chip:focus-visible,.lhc-nav-link:focus-visible,.lhc-work-head:focus-visible,.lhc-ref:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ---- navigation ---- */
.lhc-nav{display:flex;gap:6px;overflow-x:auto;white-space:nowrap;padding:8px 0;margin-bottom:14px;border-bottom:1px solid var(--line);scrollbar-width:thin}
.lhc-nav-link{display:inline-flex;align-items:center;min-height:44px;padding:6px 12px;border-radius:8px;color:var(--muted);font-size:12.5px;font-weight:600;text-decoration:none}
.lhc-nav-link:hover{background:var(--panel-2);color:var(--accent)}

/* ---- sections ---- */
.lhc-section{background:linear-gradient(180deg,var(--panel) 0%,var(--panel-2) 100%);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px;scroll-margin-top:72px;min-width:0}
.lhc-section-head{margin-bottom:12px}
.lhc-section-number{display:block;font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.08em;color:var(--accent);margin-bottom:4px}
.lhc-section-title{font-size:19px;font-weight:650;margin:0 0 4px}
.lhc-section-sub{font-size:12.5px;color:var(--muted);margin:0;max-width:900px}

/* ---- cards and chips ---- */
.lhc-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.lhc-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-width:0}
.lhc-card-title{font-size:15px;font-weight:650;margin:9px 0 8px}
.lhc-card .lhc-list{font-size:13px;color:var(--muted)}
.lhc-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:6px;border:1px solid var(--line);font-size:11px;font-weight:700;letter-spacing:.02em;white-space:nowrap;background:var(--panel-2);color:var(--muted)}
.lhc-chip--ready{color:var(--ok);border-color:var(--ok)}
.lhc-chip--partial{color:var(--warn);border-color:var(--warn)}
.lhc-chip--missing{color:var(--bad);border-color:var(--bad)}
.lhc-chip--btn{cursor:pointer;min-height:44px;min-width:44px;font-family:inherit;font-size:12.5px;padding:6px 14px;background:var(--panel);color:var(--muted)}
.lhc-chip--btn:hover{color:var(--text);border-color:var(--accent)}
.lhc-chip--btn.is-active{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.lhc-dot{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block;flex:none}
.lhc-refs{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.lhc-ref{display:inline-flex;align-items:center;justify-content:center;min-height:26px;padding:2px 8px;border-radius:5px;background:var(--panel-2);border:1px solid var(--line);color:var(--muted);font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;text-decoration:none}
.lhc-ref:hover{color:var(--accent);border-color:var(--accent)}
.lhc-ref--task{color:var(--accent)}
.lhc-link{display:inline-flex;align-items:center;min-height:44px;min-width:44px;padding:4px 12px;
  border:1px solid var(--line);border-radius:8px;background:var(--panel-2);color:var(--accent);
  font-size:12px;font-weight:600;text-decoration:none;margin-top:2px}
.lhc-link:hover{border-color:var(--accent)}

/* ---- notes ---- */
.lhc-note{border:1px solid var(--line);border-left:4px solid var(--muted);border-radius:10px;background:var(--panel);padding:12px 14px;font-size:13px;margin:12px 0 0}
.lhc-note--blue{border-left-color:var(--accent)}
.lhc-note--red{border-left-color:var(--bad)}
.lhc-note--warn{border-left-color:var(--warn)}
.lhc-note--green{border-left-color:var(--ok)}
.lhc-note--plain{border-left-color:var(--muted)}
.lhc-note-title{display:block;font-weight:650;margin-bottom:4px}
.lhc-note-text{margin:0;color:var(--muted)}
.lhc-note .lhc-refs{margin-top:8px}
.lhc-notes .lhc-note{margin:0 0 10px}
.lhc-notes .lhc-note:last-child{margin-bottom:0}

/* ---- metrics ---- */
.lhc-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:4px}
.lhc-metric{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.lhc-metric b{display:block;font-size:26px;line-height:1.1;font-variant-numeric:tabular-nums}
.lhc-metric span{display:block;font-size:11.5px;color:var(--muted);margin-top:4px}
.lhc-metric--ready b{color:var(--ok)}
.lhc-metric--partial b{color:var(--warn)}
.lhc-metric--missing b{color:var(--bad)}
.lhc-metric--total b{color:var(--accent)}

/* ---- toolbar ---- */
.lhc-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.lhc-toolbar-label{font-size:12px;color:var(--muted)}
.lhc-input{flex:1 1 220px;min-width:0;min-height:44px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--text);font:inherit;font-size:13px}
.lhc-chips{display:flex;flex-wrap:wrap;gap:6px}
.lhc-count{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.lhc-range{width:170px;min-height:44px;accent-color:var(--accent)}

/* ---- tables ---- */
.lhc-table-wrap{max-width:100%;overflow-x:auto}
.lhc-table{width:100%;border-collapse:collapse;font-size:13px}
.lhc-table th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:8px 10px;border-bottom:1px solid var(--line);background:var(--panel);white-space:nowrap}
.lhc-table td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.lhc-table tr:last-child td{border-bottom:0}
.lhc-cell-title{display:block;font-size:13.5px;font-weight:650}
.lhc-cell-text{margin:0 0 6px}
.lhc-caption{font-size:11.5px;color:var(--muted);margin:0}
.lhc-mono{font:11.5px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);display:block}
.lhc-req-table td:first-child{width:24%;min-width:200px}
.lhc-req-table td:nth-child(2){width:130px}
.lhc-health-table td:first-child{width:20%}

/* ---- gantt ---- */
.lhc-gantt-shell{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel)}
.lhc-gantt-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:14px 16px;border-bottom:1px solid var(--line)}
.lhc-gantt-meta span{display:block;font-size:11.5px;color:var(--muted)}
.lhc-gantt-meta b{display:block;font-size:19px;line-height:1.2;margin:4px 0}
.lhc-gantt-scroll{overflow:auto;max-height:620px}
.lhc-gantt{--lhc-day:64px;--lhc-cols:12;--lhc-label:280px;--lhc-row-h:68px;--lhc-band-h:48px;min-width:max-content}
.lhc-gantt-head{display:flex;position:sticky;top:0;z-index:5;background:var(--panel-2);border-bottom:1px solid var(--line)}
.lhc-gantt-corner{position:sticky;left:0;z-index:6;flex:none;width:var(--lhc-label);min-width:var(--lhc-label);padding:10px 12px;background:var(--panel-2);border-right:1px solid var(--line);font-size:11px;font-weight:700}
.lhc-gantt-days{display:flex}
.lhc-gantt-day{width:var(--lhc-day);flex:none;padding:8px 4px;text-align:center;border-right:1px solid var(--line);font-size:10px;color:var(--muted)}
.lhc-gantt-day strong{display:block;font-size:12px;color:var(--text)}
.lhc-gantt-body{position:relative;z-index:0}.lhc-gantt-row,.lhc-gantt-band{display:flex;border-bottom:1px solid var(--line)}
.lhc-gantt-row{height:var(--lhc-row-h);min-height:44px}
.lhc-gantt-band{height:var(--lhc-band-h);background:var(--panel-2)}
.lhc-gantt-label{position:sticky;left:0;z-index:4;flex:none;width:var(--lhc-label);min-width:var(--lhc-label);display:flex;flex-direction:column;justify-content:center;gap:2px;padding:7px 12px;background:var(--panel);border:0;border-right:1px solid var(--line);border-radius:0;overflow:hidden;text-align:left;font:inherit;color:inherit;cursor:pointer}
.lhc-gantt-label:hover{background:var(--panel-2)}.lhc-gantt-label strong{display:block;font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lhc-gantt-row-meta{display:block;font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lhc-gantt-flags{display:flex;gap:5px;white-space:nowrap;overflow:hidden}.lhc-flag{display:inline-block;flex:none;padding:1px 6px;border-radius:5px;border:1px solid var(--line);font-size:9.5px;font-weight:700;letter-spacing:.01em;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.lhc-flag--wait{color:var(--warn);border-color:var(--warn)}.lhc-flag--block{color:var(--accent);border-color:var(--accent);flex:0 1 auto;min-width:0}
.lhc-gantt-row[data-lhc-waits] .lhc-gantt-label::before,.lhc-gantt-row[data-lhc-blocks] .lhc-gantt-label::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px}
.lhc-gantt-row[data-lhc-waits] .lhc-gantt-label::before{background:var(--warn)}
.lhc-gantt-row[data-lhc-blocks] .lhc-gantt-label::before{background:var(--accent)}
.lhc-gantt-row[data-lhc-waits][data-lhc-blocks] .lhc-gantt-label::before{background:linear-gradient(var(--warn) 0 50%,var(--accent) 50% 100%)}
.lhc-gantt-band-label{position:sticky;left:0;z-index:4;flex:none;width:var(--lhc-label);min-width:var(--lhc-label);display:flex;flex-direction:column;justify-content:center;gap:2px;padding:7px 12px;background:var(--panel-2);border-right:1px solid var(--line);font-size:11.5px;overflow:hidden}
.lhc-gantt-band-line{display:flex;align-items:center;gap:6px;min-width:0}.lhc-gantt-band-label strong{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lhc-band-meta{font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lhc-gantt-track{position:relative;flex:none;width:calc(var(--lhc-cols) * var(--lhc-day));background:repeating-linear-gradient(to right,transparent 0,transparent calc(var(--lhc-day) - 1px),var(--line) calc(var(--lhc-day) - 1px),var(--line) var(--lhc-day))}
.lhc-bar{position:absolute;top:50%;transform:translateY(-50%);z-index:3;height:44px;min-width:44px;padding:0 6px;border:0;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,.25);cursor:pointer;overflow:hidden;white-space:nowrap;display:flex;align-items:center;justify-content:center;font:inherit;font-size:10.5px;font-weight:700;color:#fff;text-shadow:0 1px 1px rgba(0,0,0,.35)}
.lhc-bar:hover{filter:brightness(1.08)}.lhc-bar-id{overflow:hidden;text-overflow:ellipsis}
.lhc-bar--free{background:repeating-linear-gradient(45deg,var(--line) 0 4px,transparent 4px 8px);box-shadow:none;cursor:default}
.lhc-band{position:absolute;top:50%;transform:translateY(-50%);height:14px;border-radius:4px;opacity:.45;min-width:4px}
.lhc-swatch{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.lhc-gantt-row.is-selected .lhc-bar{outline:3px solid var(--text);outline-offset:2px}.lhc-gantt-row.is-selected .lhc-gantt-label{background:var(--panel-2)}
.lhc-gantt-net{position:absolute;left:var(--lhc-label);top:0;width:calc(var(--lhc-cols) * var(--lhc-day));height:100%;z-index:2;pointer-events:none;overflow:visible}
.lhc-net-edge{fill:none;stroke:var(--muted);stroke-width:1.3;opacity:.75}.lhc-net-edge.is-active{stroke:var(--accent);stroke-width:2;opacity:1}.lhc-net-arrow{fill:var(--muted);stroke:none}
.lhc-gantt--no-deps .lhc-gantt-net{display:none}
.lhc-gantt-foot{padding:10px 14px;background:var(--panel-2);border-top:1px solid var(--line);font-size:11.5px;color:var(--muted)}
.lhc-legend{display:flex;flex-wrap:wrap;gap:10px 16px;margin-top:12px}
.lhc-legend span{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}

/* ---- the card of a task: one card, opened from the grid and from the work ---- */
.lhc-gantt-detail{border-top:1px solid var(--line);background:var(--panel)}
.lhc-gantt-detail-bar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 12px;border-bottom:1px solid var(--line)}.lhc-gantt-detail-caption{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.lhc-gantt-detail-body{padding:14px}.lhc-detail-head{display:block;margin-bottom:12px}
.lhc-detail-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
.lhc-chip--id{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--accent)}.lhc-chip--priority{color:var(--warn);border-color:var(--warn)}.lhc-chip--plan{color:var(--muted)}
.lhc-detail-title{font-size:16px;font-weight:650;margin:0 0 6px}
.lhc-detail-state{margin-top:4px}.lhc-detail-cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.lhc-detail-gantt{margin-top:10px}.lhc-gantt-detail .lhc-detail-gantt{display:none}

/* ---- the switch of the arrows ---- */
.lhc-switch{display:inline-flex;align-items:center;gap:8px;min-height:44px;min-width:44px;padding:0 10px 0 0;font-size:12.5px;color:var(--muted);cursor:pointer;user-select:none}
.lhc-switch input{appearance:none;-webkit-appearance:none;width:44px;height:44px;margin:0;flex:none;border:1px solid var(--line);border-radius:10px;background:var(--panel) no-repeat center/18px 18px;cursor:pointer}
.lhc-switch input:checked{background-color:var(--accent);border-color:var(--accent);background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'><path d='M4 10.5l4 4 8-9' fill='none' stroke='%23ffffff' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></svg>")}

/* ---- work cards ---- */
.lhc-phase{margin-bottom:18px}
.lhc-phase:last-child{margin-bottom:0}
.lhc-phase-head{display:flex;align-items:center;gap:10px;margin-bottom:10px;font-size:13px}
.lhc-phase-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lhc-phase-line{height:1px;flex:1;background:var(--line)}
.lhc-phase-count{font-size:11.5px;color:var(--muted);white-space:nowrap}
.lhc-work{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--lhc-phase,var(--accent));border-radius:12px;margin-bottom:10px;overflow:hidden}
.lhc-work:last-child{margin-bottom:0}
.lhc-work-head{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:6px 12px;width:100%;min-height:44px;padding:12px 14px;border:0;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer;align-items:start}
.lhc-work-head:hover .lhc-work-title{color:var(--accent)}
.lhc-work-id{font:11.5px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--accent)}
.lhc-work-main{min-width:0}
.lhc-work-title{display:block;font-size:14px;font-weight:650}
.lhc-work-result{display:block;font-size:12px;color:var(--muted);margin-top:3px}
.lhc-work-side{display:flex;flex-direction:column;align-items:flex-end;gap:4px}
.lhc-work-meta{font-size:11.5px;color:var(--muted);text-align:right}
.lhc-work-toggle{font-size:11.5px;color:var(--accent);white-space:nowrap}
.lhc-work-body{padding:0 14px 14px}
.lhc-work-col{min-width:0}
.lhc-work-col--wide{grid-column:1/-1}
.lhc-work-label{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:6px}
.lhc-work-body .lhc-list{font-size:13px}
.lhc-work-body .lhc-cell-text{font-size:13px;color:var(--muted)}

/* ---- rules ---- */
.lhc-rules{columns:2;column-gap:32px;font-size:13.5px;padding-left:22px}
.lhc-rules li{break-inside:avoid;margin-bottom:8px}

/* ---- agent handoff ---- */
.lhc-agent{background:var(--panel-2);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.lhc-agent-text{font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0 12px;max-height:460px;overflow:auto}
.lhc-status{font-size:12px;color:var(--ok)}

/* ---- sources ---- */
.lhc-sources{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.lhc-source{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;scroll-margin-top:80px;min-width:0}
.lhc-source:target{border-color:var(--accent)}
.lhc-source .lhc-card-title{font-size:14px;margin:6px 0}
.lhc-location{font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);overflow-wrap:anywhere}
.lhc-source .lhc-cell-text{font-size:13px;margin-top:8px}
.lhc-details{margin-top:8px}
.lhc-details summary{cursor:pointer;font-size:12px;color:var(--accent);min-height:44px;display:flex;align-items:center}
.lhc-excerpt{font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--panel-2);padding:10px;border-radius:8px;margin:6px 0 0}
.lhc-details--flat{background:var(--panel-2);border:1px solid var(--line);border-radius:12px;padding:12px 16px}
.lhc-details--flat summary{font-weight:650}
.lhc-spec-text{font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);margin:10px 0 0}

/* ---- the phone layout comes last, so it wins ---- */
@media (max-width:1000px){
  .lhc-cards{grid-template-columns:minmax(0,1fr)}
  .lhc-sources{grid-template-columns:minmax(0,1fr)}
  .lhc-rules{columns:1}
  .lhc-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media (max-width:760px){
  .lhc-product{font-size:13.5px}
  .lhc-hero{grid-template-columns:minmax(0,1fr);gap:14px}
  .lhc-title{font-size:21px}
  .lhc-section{padding:12px 13px;border-radius:12px}
  .lhc-section-title{font-size:17px}
  .lhc-metrics{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .lhc-metric{padding:10px 12px}
  .lhc-metric b{font-size:22px}
  .lhc-detail-cols{grid-template-columns:minmax(0,1fr);gap:10px}
  .lhc-work-head{grid-template-columns:minmax(0,1fr);gap:4px}
  .lhc-work-side{flex-direction:row;align-items:center;justify-content:space-between;gap:10px}
  .lhc-work-meta{text-align:left}
  .lhc-gantt-meta{grid-template-columns:repeat(2,minmax(0,1fr));padding:12px}
  .lhc-gantt{--lhc-label:180px}
  /* The column is narrow: the flag says how many it holds back. */
  .lhc-flag--block{font-size:0}.lhc-flag--block::after{content:"блокирует " attr(data-lhc-count);font-size:9.5px}
  .lhc-toolbar{align-items:stretch}
  .lhc-toolbar-label{flex:1 0 100%}
  .lhc-input{flex:1 1 100%}
  .lhc-range{flex:1 1 120px;width:auto;min-width:120px}
  /* Every touch target is at least 44 CSS px. */
  .lhc-ref{min-height:44px;padding:6px 12px}
  .lhc-details summary{min-height:44px}
  /* The tables become one card per row instead of a wide table to scroll. */
  .lhc-table-wrap{overflow-x:visible}
  .lhc-table thead{display:none}
  .lhc-table tbody,.lhc-table tr{display:block}
  .lhc-table tr{padding:10px 0;border-bottom:1px solid var(--line)}
  .lhc-table tr:last-child{border-bottom:0}
  .lhc-table td{display:block;padding:4px 0;border:0}
  .lhc-table td::before{content:attr(data-label);display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:2px}
}
"""


def product_styles() -> str:
    """The CSS of the delivery sections.

    The theme variables are declared for both themes, taken from the palette
    of the dashboard so the merged page cannot drift into a second palette.
    """

    palette = dashboard_palette()
    dark = _theme_vars(palette.get("dark"), "dark")
    light = _theme_vars(palette.get("light"), "light")
    return _STYLES.replace("/*THEME-DARK*/", dark).replace("/*THEME-LIGHT*/", light)


# --------------------------------------------------------------------------
# scripts
# --------------------------------------------------------------------------

_SCRIPTS = """
(function () {
  "use strict";
  function all(node, selector) {
    return Array.prototype.slice.call(node.querySelectorAll(selector));
  }
  var products = all(document, ".lhc-product");
  if (!products.length) { return; }
  var root = document.documentElement;

  /* ---- theme: the choice of the reader, remembered between openings ---- */
  var stored = null;
  try { stored = window.localStorage.getItem("lhc-theme"); } catch (error) { stored = null; }
  if (stored === "light" || stored === "dark") {
    root.setAttribute("data-theme", stored);
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
    root.setAttribute("data-theme", "light");
  }
  var themeToggle = document.getElementById("lhc-theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      try { window.localStorage.setItem("lhc-theme", next); } catch (error) { /* no storage */ }
    });
  }

  /* ---- the agent task: copy and confirm ---- */
  var copyButton = document.getElementById("lhc-copy-agent");
  var copyStatus = document.getElementById("lhc-copy-status");
  function say(message) {
    if (!copyStatus) { return; }
    copyStatus.textContent = message;
    window.setTimeout(function () { if (copyStatus) { copyStatus.textContent = ""; } }, 3500);
  }
  function agentText() {
    var name = (copyButton && copyButton.getAttribute("data-lhc-copy-target")) || "lhc-agent-text";
    var target = document.getElementById(name);
    return target ? (target.textContent || "") : "";
  }
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "readonly");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    document.body.appendChild(area);
    area.select();
    var copied = false;
    try { copied = document.execCommand("copy"); } catch (error) { copied = false; }
    area.remove();
    say(copied ? "Задание скопировано" : "Текст выделен. Скопируйте его обычной командой.");
  }
  if (copyButton) {
    copyButton.addEventListener("click", function () {
      var text = agentText();
      if (!text) { say("Задание не найдено"); return; }
      var settled = false;
      var fallback = function () {
        if (settled) { return; }
        settled = true;
        fallbackCopy(text);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          if (settled) { return; }
          settled = true;
          say("Задание скопировано");
        }, fallback);
        /* A clipboard that never answers must not leave the reader without
           a confirmation: the selection path is the second way out. */
        window.setTimeout(fallback, 800);
      } else {
        fallbackCopy(text);
      }
    });
  }

  /* ---- the plan as a file ---- */
  var downloadButton = document.getElementById("lhc-download-json");
  if (downloadButton) {
    downloadButton.addEventListener("click", function () {
      var island = document.getElementById("lhc-plan-json");
      var raw = island ? (island.content ? island.content.textContent : island.textContent) : "";
      var payload = raw;
      try { payload = JSON.stringify(JSON.parse(raw), null, 2); } catch (error) { payload = raw; }
      var blob = new Blob([payload || "{}"], { type: "application/json;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      link.href = url;
      link.download = "lhc-plan.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });
  }

  /* ---- one block of the page: the grid, the requirements and the works ---- */
  function wireProduct(product) {
    var gantt = product.querySelector("#lhc-gantt-grid");
    var net = gantt ? gantt.querySelector(".lhc-gantt-net") : null;
    var area = product.querySelector("#lhc-gantt-detail");
    var detailBody = product.querySelector("#lhc-gantt-detail-body");
    var closeButton = product.querySelector("#lhc-gantt-detail-close");
    var zoom = product.querySelector("#lhc-gantt-zoom");
    var zoomValue = product.querySelector("#lhc-gantt-zoom-value");
    var depsToggle = product.querySelector("#lhc-gantt-deps");
    var rows = gantt ? all(gantt, ".lhc-gantt-row") : [];
    var paths = net ? all(net, "path[data-lhc-from]") : [];
    var bars = {};
    var baseDay = gantt ? (parseFloat(gantt.getAttribute("data-lhc-day-base")) || 64) : 64;
    rows.forEach(function (row) {
      var bar = row.querySelector(".lhc-bar");
      if (bar) { bars[row.getAttribute("data-lhc-task")] = bar; }
    });

    /* the arrows of the dependencies: measured, so they follow the scale */
    function layoutArrows() {
      if (!net || !gantt || gantt.classList.contains("lhc-gantt--no-deps")) { return; }
      var box = net.getBoundingClientRect();
      if (!box.width) { return; }
      paths.forEach(function (path) {
        var from = bars[path.getAttribute("data-lhc-from")];
        var to = bars[path.getAttribute("data-lhc-to")];
        if (!from || !to) { return; }
        var a = from.getBoundingClientRect();
        var b = to.getBoundingClientRect();
        var x1 = a.right - box.left - 2, y1 = a.top + a.height / 2 - box.top;
        var x2 = b.left - box.left + 3, y2 = b.top + b.height / 2 - box.top;
        var elbow = Math.min(x1 + 12, Math.max(x1 + 5, x2 - 7));
        path.setAttribute("d", "M " + x1.toFixed(1) + " " + y1.toFixed(1) + " H " +
          elbow.toFixed(1) + " V " + y2.toFixed(1) + " H " + x2.toFixed(1));
      });
    }

    /* the card of a task: the very card the work card opens */
    function openTask(taskId, scroll) {
      if (!taskId || !area || !detailBody) { return; }
      var source = document.getElementById("lhc-work-body-" + taskId);
      if (source) { detailBody.innerHTML = source.innerHTML; }
      area.hidden = false;
      rows.forEach(function (row) { row.classList.toggle("is-selected", row.getAttribute("data-lhc-task") === taskId); });
      paths.forEach(function (path) { path.classList.toggle("is-active", path.getAttribute("data-lhc-to") === taskId); });
      if (scroll) {
        try { area.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
        catch (error) { area.scrollIntoView(); }
      }
    }

    /* gantt: the scale of the time axis */
    function applyZoom(scale) {
      if (!gantt) { return; }
      var clamped = Math.min(2.4, Math.max(0.6, scale));
      gantt.style.setProperty("--lhc-day", (baseDay * clamped).toFixed(1) + "px");
      if (zoomValue) { zoomValue.textContent = Math.round(clamped * 100) + "%"; }
      if (zoom && parseFloat(zoom.value) !== clamped) { zoom.value = String(clamped); }
      layoutArrows();
    }
    if (zoom) { zoom.addEventListener("input", function () { applyZoom(parseFloat(zoom.value) || 1); }); }
    all(product, "[data-lhc-zoom]").forEach(function (button) {
      button.addEventListener("click", function () {
        var step = parseFloat(button.getAttribute("data-lhc-zoom")) || 1;
        applyZoom((zoom ? (parseFloat(zoom.value) || 1) : 1) + step * 0.2);
      });
    });
    applyZoom(1);

    /* gantt: the arrows of the dependencies can be switched off */
    if (depsToggle && gantt) {
      depsToggle.addEventListener("change", function () {
        gantt.classList.toggle("lhc-gantt--no-deps", !depsToggle.checked);
        layoutArrows();
      });
    }

    /* gantt: a click on the row, the label or the bar opens the card */
    if (gantt) {
      gantt.addEventListener("click", function (event) {
        var holder = event.target && event.target.closest ? event.target.closest("[data-lhc-task]") : null;
        if (!holder || !gantt.contains(holder)) { return; }
        openTask(holder.getAttribute("data-lhc-task"), true);
      });
    }

    /* gantt: the card can be closed, and the selection is dropped with it */
    if (closeButton && area && detailBody) {
      closeButton.addEventListener("click", function () {
        area.hidden = true;
        detailBody.innerHTML = "";
        rows.forEach(function (row) { row.classList.remove("is-selected"); });
        paths.forEach(function (path) { path.classList.remove("is-active"); });
      });
    }

    /* the card of a task is opened from the work card of the same page */
    product.addEventListener("click", function (event) {
      var link = event.target && event.target.closest ? event.target.closest("[data-lhc-gantt-link]") : null;
      if (!link) { return; }
      event.preventDefault();
      openTask(link.getAttribute("data-lhc-gantt-link"), true);
    });

    /* requirements: a filter by verdict and a search */
    var chips = all(product, "[data-lhc-req-filter]");
    var reqRows = all(product, ".lhc-req-table tbody tr");
    var search = product.querySelector("#lhc-req-search");
    var count = product.querySelector("#lhc-req-count");
    var filter = "all";
    function applyRequirements() {
      var query = ((search && search.value) || "").trim().toLowerCase();
      var shown = 0;
      reqRows.forEach(function (row) {
        var okStatus = filter === "all" || row.getAttribute("data-lhc-status") === filter;
        var okQuery = !query || (row.getAttribute("data-lhc-text") || "").indexOf(query) !== -1;
        row.hidden = !(okStatus && okQuery);
        if (!row.hidden) { shown += 1; }
      });
      if (count) { count.textContent = shown + " из " + reqRows.length; }
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        chips.forEach(function (other) { other.classList.remove("is-active"); });
        chip.classList.add("is-active");
        filter = chip.getAttribute("data-lhc-req-filter") || "all";
        applyRequirements();
      });
    });
    if (search) { search.addEventListener("input", applyRequirements); }
    applyRequirements();

    /* work cards: the card opens where the finger already is */
    all(product, ".lhc-work-head").forEach(function (head) {
      head.addEventListener("click", function () {
        var body = document.getElementById(head.getAttribute("aria-controls") || "");
        if (body) {
          var open = head.getAttribute("aria-expanded") === "true";
          head.setAttribute("aria-expanded", open ? "false" : "true");
          body.hidden = open;
              var toggle = head.querySelector(".lhc-work-toggle");
          if (toggle) { toggle.textContent = open ? "Показать" : "Скрыть"; }
        }
        openTask(head.getAttribute("data-lhc-task"), false);
      });
    });

    /* the arrows follow the scale of the time axis */
    if (paths.length) {
      window.addEventListener("load", layoutArrows);
      layoutArrows();
    }
  }

  products.forEach(function (product) { wireProduct(product); });
})();
"""


def product_scripts() -> str:
    """The JavaScript of the delivery sections.

    Plain inline JavaScript: the controls work without a framework and
    without a build step.
    """

    return _SCRIPTS
