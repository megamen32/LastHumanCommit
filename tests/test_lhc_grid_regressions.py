"""Regressions of the dashboard defects, and of the fixes that followed.

Every test here protects a defect that was measured on a real plan:

* the counters came from another layer than the table, so "готово 4/18" stood
  above 24 rows and "осталось 7" hid 14 unfinished leaves;
* the forecast bounds were swapped, so the finish was earlier than its own
  "minimum";
* the search promised the owner and the row carried no owner, so a known
  session id was never found;
* the wave log repeated the task names instead of recording changes.

A fix without a test is a fix that comes back.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("lhc_grid_regressions", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lhc = load_tool()


def run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


REPORT = """Цель: закрыть интеграцию источника
Бизнес-результат: сообщение превращается в карточку
Декомпозиция: 4 листа · 2 параллельно · 2 волны · слотов: 2

✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
✅ (поиск источника) начата 14:02 закончена 14:11, оценка 15 минут, факт 9 минут, ∥ параллельно с листом 1

🔄 работаем (приём в доске) начата 14:12, оценка 20 минут, прошло 22 минут, отстаём потому что: ждём ключ
⏳ (сборка и push) начнём после листа 3, потому что нужен принятый контракт, примерно в 14:30, оценка 10 минут, закончим в 14:40
"""


def graph_with_owner(owner: str = "mvs_03faeb0f"):
    return lhc.parse_graph_json(
        {
            "schema_version": 2,
            "slots": 2,
            "tasks": [
                {
                    "id": "L01",
                    "label": "Поднять ноду",
                    "status": "done",
                    "depends_on": [],
                    "owner": owner,
                    "session": "ses_03faeb0f",
                    "estimate_minutes": {"minimum": 10, "maximum": 20},
                    "actual_minutes": 22,
                    "started_at": "11:15",
                    "finished_at": "11:26",
                },
                {
                    "id": "L02",
                    "label": "Проверить приёмку",
                    "status": "queued",
                    "depends_on": [],
                    "owner": "mvs_other",
                    "estimate_minutes": {"minimum": 5, "maximum": 15},
                },
            ],
        }
    )


def kpi_value(html: str, label: str) -> str:
    pattern = re.compile(
        r'<div class="kpi-label"[^>]*>[^<]*' + re.escape(label) + r'[^<]*</div>'
        r'<div class="kpi-value">([^<]*)</div>'
    )
    match = pattern.search(html)
    assert match, f"плитка {label!r} не найдена"
    return match.group(1)


# --------------------------------------------------------------------------
# the four defects of the previous release
# --------------------------------------------------------------------------


def test_forecast_bounds_are_ordered():
    """The earliest finish cannot be later than the latest one."""

    graph = lhc.parse_graph_json(
        {
            "schema_version": 2,
            "slots": 1,
            "tasks": [
                {
                    "id": "a",
                    "label": "a",
                    "status": "queued",
                    "depends_on": [],
                    "estimate_minutes": {"minimum": 5, "maximum": 45},
                }
            ],
        }
    )
    with patch.object(lhc, "now_clock", return_value=12 * 60):
        metrics = lhc.build_metrics(graph)
    early = lhc.parse_clock(metrics["eta_clock_min"])
    late = lhc.parse_clock(metrics["eta_clock_max"])
    assert early is not None and late is not None
    assert early <= late, "прогноз финиша должен идти от ранней границы к поздней"


def test_remaining_counter_and_done_share_one_layer():
    """«Осталось» and «Готово» answer the same question in the same layer."""

    graph = lhc.parse_plan_report(REPORT)
    metrics = lhc.build_metrics(graph)
    assert metrics["use_live"] is True
    assert metrics["unfinished"] == metrics["headline_total"] - metrics["done"]
    html = lhc.render_html(graph, metrics)
    assert kpi_value(html, "Осталось") == str(metrics["unfinished"])
    assert kpi_value(html, "Готово") == f"{metrics['done']} / {metrics['headline_total']}"


def test_owner_is_findable_in_the_search_data():
    """The search box promises the owner, so the row has to carry the owner."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "mvs_03faeb0f" in html
    row = re.search(r'<tr data-status="done" data-text="([^"]*)"[^>]*>', html)
    assert row, "строка листа не найдена"
    searchable = row.group(1)
    assert "mvs_03faeb0f" in searchable
    assert "ses_03faeb0f" in searchable


def test_graph_journal_renders_as_a_change_log():
    """A graph may carry its own change log; the leaf list is not one."""

    graph = lhc.parse_graph_json(
        {
            "schema_version": 2,
            "journal": [
                {
                    "at": "13:27",
                    "action": "собрана и запущена 1.5.30",
                    "result": "дефекты дашборда исправлены",
                    "evidence": "e9838c6",
                }
            ],
            "tasks": [
                {"id": "L01", "label": "Что-то", "status": "done", "depends_on": [],
                 "estimate_minutes": {"minimum": 5, "maximum": 5}},
            ],
        }
    )
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "13:27" in html
    assert "собрана и запущена 1.5.30" in html
    assert "дефекты дашборда исправлены" in html
    assert "e9838c6" in html
    assert "Журнал изменений" in html


# --------------------------------------------------------------------------
# the work that followed
# --------------------------------------------------------------------------


def test_calendar_span_and_summed_effort_are_separate():
    """22 minutes of effort inside an 11 minute window are two numbers."""

    graph = graph_with_owner()
    leaf = graph.leaves[0]
    assert leaf.actual_minutes == 22
    assert leaf.actual_span_minutes == 11
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "Усилие (суммарно)" in html
    assert "Длительность по часам" in html
    text = lhc.render_text(graph, lhc.build_metrics(graph))
    assert "усилие 22 мин" in text
    assert "по часам 11 мин" in text


def test_forecast_is_anchored_at_the_last_confirmed_event():
    """An idle plan must not push its own finish away with silence."""

    graph = lhc.parse_graph_json(
        {
            "schema_version": 2,
            "tasks": [
                {"id": "next", "label": "Next", "status": "queued", "depends_on": [],
                 "estimate_minutes": {"minimum": 5, "maximum": 5}, "started_at": "15:19"},
            ],
        }
    )
    with patch.object(lhc, "now_clock", return_value=17 * 60):
        metrics = lhc.build_metrics(graph)
    assert metrics["eta_anchor_clock"] == "15:19"
    assert metrics["eta_anchor_idle_minutes"] == 101
    assert metrics["eta_overdue"] is True
    html = lhc.render_html(graph, metrics)
    assert "отсчёт от последнего события 15:19" in html
    assert "срок прошёл" in html


def test_one_graph_produces_one_revision_for_both_artifacts(tmp_path):
    """The dashboard and the summary are generated, never kept in sync."""

    report = tmp_path / "plan.report.md"
    report.write_text(REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    assert run_tool("export", str(report), "-o", str(graph_path)).returncode == 0

    out = tmp_path / "out"
    result = run_tool("render", str(graph_path), "--out-dir", str(out))
    assert result.returncode == 0, result.stderr
    html = (out / "plan.html").read_text(encoding="utf-8")
    markdown = (out / "plan.md").read_text(encoding="utf-8")

    html_revision = re.search(r"ревизия ([0-9a-f]{12})", html)
    markdown_revision = re.search(r"Ревизия плана: ([0-9a-f]{12})", markdown)
    assert html_revision and markdown_revision
    assert html_revision.group(1) == markdown_revision.group(1)

    # The same graph produces the same bytes: no hand-edited copy can drift.
    second = tmp_path / "out2"
    assert run_tool("render", str(graph_path), "--out-dir", str(second)).returncode == 0
    assert (second / "plan.md").read_bytes() == (out / "plan.md").read_bytes()


def test_check_plan_passes_on_the_same_chain(tmp_path):
    """The report, the graph and the dashboard are checked as one chain."""

    report = tmp_path / "plan.report.md"
    report.write_text(REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    assert run_tool("export", str(report), "-o", str(graph_path)).returncode == 0
    check = run_tool("check-plan", str(report), str(graph_path))
    assert check.returncode == 0, check.stdout + check.stderr

    out = tmp_path / "out"
    assert run_tool("render", str(graph_path), "--out-dir", str(out)).returncode == 0
    html = (out / "plan.html").read_text(encoding="utf-8")
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    for task in document["tasks"]:
        assert task["id"] in html


def test_snapshot_note_is_visible_in_both_artifacts():
    """The dashboard is a snapshot of the plan, not a control panel."""

    graph = graph_with_owner()
    metrics = lhc.build_metrics(graph)
    assert lhc.SNAPSHOT_NOTE in lhc.render_html(graph, metrics)
    assert lhc.SNAPSHOT_NOTE in lhc.render_text(graph, metrics)


REPORT_WITH_JOURNAL = """Цель: закрыть интеграцию источника
Бизнес-результат: сообщение превращается в карточку
Декомпозиция: 2 листа · 1 параллельно · 1 волна · слотов: 1

✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут

🔄 работаем (приём в доске) начата 11:15, оценка 20 минут, прошло 22 минут

## Журнал изменений

- 13:27 · L01 · выпущен 1.5.31 · результат: дефекты дашборда исправлены · подтверждение: e9838c6
- 13:40 · результат: план пересобран из одной ревизии · подтверждение: check-plan
"""


def test_report_journal_section_is_parsed():
    """The change log of the report is a history, not a second table."""

    graph = lhc.parse_plan_report(REPORT_WITH_JOURNAL)
    assert graph is not None
    assert len(graph.journal) == 2
    first = graph.journal[0]
    assert first["at"] == "13:27"
    assert first["leaf"] == "L01"
    assert first["action"] == "выпущен 1.5.31"
    assert first["result"] == "дефекты дашборда исправлены"
    assert first["evidence"] == "e9838c6"
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    for probe in ("13:27", "выпущен 1.5.31", "13:40", "check-plan"):
        assert probe in html


def graph_with_brief():
    """A plan that says why the work exists, and what progress is confirmed."""
    graph = graph_with_owner()
    graph.goal = "Закрыть интеграцию источника"
    graph.business_result = "Сообщение превращается в карточку у владельца"
    graph.current_progress = "Контракт принят, приёмка в доске"
    graph.external_waits = "Ждём ключ владельца"
    return graph


def test_first_screen_shows_state_and_action_before_the_technical_brief():
    """The state and the action come before the technical wording."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    body = html[html.find("<body"):]
    assert body.find("kpis") < body.find("panel-now")
    # The technical confirmation is collapsed, not the first thing to read.
    assert "<details class=\"panel brief-details\">" in html


def test_business_goal_is_visible_without_interaction():
    """The owner asked for the business goal: it is on the first screen.

    It used to live in a folded brief, so opening the dashboard on a phone
    showed the counters and the action but never the reason the work exists.
    """

    graph = graph_with_brief()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    body = html[html.find("<body"):]
    why = re.search(
        r'<details class="panel brief-details brief-why-details"( open)?>', body
    )
    assert why, "блок цели и бизнес-результата не найден"
    assert why.group(1), "блок цели должен быть открыт по умолчанию"
    goal_at = body.find("Закрыть интеграцию источника")
    result_at = body.find("Сообщение превращается в карточку у владельца")
    assert 0 < goal_at < body.find("kpis"), "цель должна быть до плиток состояния"
    assert 0 < result_at < body.find("kpis"), "бизнес-результат должен быть до плиток состояния"


def test_technical_brief_stays_folded():
    """The confirmed progress and the external waits are the folded part."""

    graph = graph_with_brief()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    body = html[html.find("<body"):]
    folded = re.search(
        r'<details class="panel brief-details">\s*<summary>([^<]*)</summary>', body
    )
    assert folded, "свёрнутый блок технической части не найден"
    assert "Подтверждённый прогресс" in folded.group(1)
    assert "Подтверждённый прогресс" in body
    assert body.find("Подтверждённый прогресс") > body.find("kpis"), (
        "техническая часть остаётся ниже состояния"
    )


def test_the_task_opens_where_the_owner_taps_it():
    """The row is the control, and the card opens under the row.

    The owner taps a task on a phone. The card used to open in a host below
    the whole table, thousands of pixels away from the finger that asked for
    it, and the only control was a button at the far end of the row.
    """

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    # Every row knows which task it is.
    assert "data-details-id='0' class='leaf-row'" in html
    # The row itself is bound to the open action.
    assert "rows.forEach(function (row)" in html
    assert "openDetails(row, row.dataset.detailsId)" in html
    # The card is placed under the row that was tapped, not in a host.
    assert "row.after(detailsRow)" in html
    assert "detailsHost.replaceChildren" not in html
    assert "document.getElementById('task-details-host')" not in html


def test_the_opened_task_carries_the_whole_of_it():
    """A task that opens must show everything the owner needs to read it.

    The description, the session and the model were not in the card: the
    description was shown only when there was no blocker, and the model was
    nowhere at all.
    """

    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "goal": "Проверить доступ",
        "business_result": "Доступ работает",
        "tasks": [{
            "id": "L01",
            "label": "Починить доступ",
            "status": "running",
            "owner": "mavis",
            "session": "mvs_92b7a29fcb6147ae848063c2e62bf864",
            "model": "MiniMax-M3.1-Flash",
            "harness": "minimax-code",
            "note": "Интерпретатор 100 не содержит пакета mcp.",
            "blocker": "venv без пакета mcp",
            "blocker_details": {
                "next_action": "Поставить пакет в venv и перезапустить проверку.",
                "human_required": "no",
                "human_action": "",
            },
            "depends_on": [],
            "estimate_minutes": {"minimum": 20, "maximum": 40},
        }],
    })
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    for probe in (
        "Описание задачи",
        "Интерпретатор 100 не содержит пакета mcp.",
        "Блокер",
        "venv без пакета mcp",
        "Следующий шаг",
        "Поставить пакет в venv",
        "Сессия",
        "mvs_92b7a29fcb6147ae848063c2e62bf864",
        "Модель",
        "MiniMax-M3.1-Flash",
        "Рантайм",
        "minimax-code",
    ):
        assert probe in html, f"в карточке задачи нет: {probe}"
    # A blocker and a description are two different things; neither eats the other.
    assert "Блокер / примечание" not in html
    # The row names the executor, so the owner sees it without opening anything.
    assert "row-meta" in html
    assert "mvs_92b7a29fcb6147ae848063c2e62bf864" in html


def test_the_task_details_stay_reachable_on_a_phone():
    """The opened card is a block under its own row on a narrow screen."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert ".table-leaves tr.task-details-row { display: block;" in html
    assert ".table-leaves tr.task-details-row > td { display: block;" in html
    assert ".leaf-row { cursor: pointer; }" in html


def test_leaf_cell_shows_effort_and_calendar_span():
    """The table cell carries both numbers, not one that means the other."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "по часам 11 мин" in html
    assert "Усилие" in html


# --------------------------------------------------------------------------
# the palette and the phone layout
# --------------------------------------------------------------------------


def _relative_luminance(color: str) -> float:
    value = color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def channel(part: float) -> float:
        return part / 12.92 if part <= 0.03928 else ((part + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(part) for part in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    one = _relative_luminance(first)
    two = _relative_luminance(second)
    high, low = max(one, two), min(one, two)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_palette_contrast_in_both_themes(theme):
    """Text and status colors stay readable on every surface of a theme."""

    values = lhc.THEME_PALETTE[theme]
    for foreground in ("text", "muted", "accent", "st-done", "st-running",
                       "st-blocked", "st-waiting", "st-queued"):
        for surface in ("panel", "bg"):
            ratio = _contrast(values[foreground], values[surface])
            assert ratio >= 4.5, (
                f"{theme}: {foreground} на {surface} даёт контраст {ratio:.2f}"
            )


def test_status_colors_are_theme_variables():
    """A status color is a variable, so one theme can change it."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "var(--st-done)" in html
    assert 'data-theme="light"' in html
    assert "--st-done:" in html


def test_phone_layout_keeps_touch_targets_and_compact_rows():
    """On a phone the cards become compact rows and the targets are 44 px."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "@media (max-width: 640px)" in html
    assert "min-height: 44px" in html
    assert ".kpis { grid-template-columns: minmax(0, 1fr); gap: 6px; }" in html
    assert ".table-leaves tr { display: block;" in html
