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

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from _inprocess import load_module, run_cli


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"


def load_tool():
    return load_module(TOOL, name="lhc_grid_regressions")


lhc = load_tool()


def run_tool(*args: str):
    return run_cli(lhc, args)


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


def test_progress_strip_never_claims_unknown_estimates_and_waits_are_absent():
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "external_waits": "Подключение источников не подтверждено.",
        "tasks": [
            {"id": f"L{i:02d}", "label": f"Phase {i}", "status": "queued", "depends_on": []}
            for i in range(1, 7)
        ],
    })
    html = lhc.render_html(graph, lhc.build_metrics(graph))

    assert "Известная часть работы" in html
    assert "Листьев без оценки — 6" in html
    assert "срок внешнего ожидания не подтверждён" in html
    assert "без неизвестных оценок и ожиданий" not in html


def test_tile_detail_scrolls_back_control_below_the_sticky_progress_strip():
    html = lhc.render_html(graph_with_owner(), lhc.build_metrics(graph_with_owner()))
    function = re.search(
        r"function openLeafInTile\(id\) \{.*?\n  \}\n  document\.querySelectorAll",
        html,
        re.S,
    )
    assert function, "функция показа подробностей карточки не найдена"
    body = function.group(0)

    shown = body.index("tileCard.hidden = false;")
    scrolled = body.index("tileCard.scrollIntoView({ block: 'start' });")
    assert scrolled > shown, "карточку нужно показать до прокрутки к кнопке возврата"
    assert '[id^="lhc-"] { scroll-margin-top: 76px; }' in html


def test_lhc_grid_fix_is_present_in_every_installed_package_projection():
    source = TOOL.read_bytes()
    package = ROOT / "plugins/last-human-commit"
    projections = {
        "tools/lhc_grid.py": source,
        "common/tools/lhc_grid.py": source.replace(b"src/common/", b"common/"),
        "native/codex/tools/lhc_grid.py": source,
        "native/codex/common/tools/lhc_grid.py": source.replace(b"src/common/", b"common/"),
    }
    for relative, expected in projections.items():
        path = package / relative
        assert path.is_file(), f"missing generated renderer: {path}"
        assert path.read_bytes() == expected, f"generated renderer drift: {path}"


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


def test_completed_plan_does_not_render_an_overdue_forecast():
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "tasks": [{
            "id": "done", "label": "Закончено", "status": "done",
            "depends_on": [], "estimate_minutes": {"minimum": 7, "maximum": 7},
            "started_at": "04:00", "finished_at": "04:10",
        }],
    })
    with patch.object(lhc, "now_clock", return_value=4 * 60 + 17):
        metrics = lhc.build_metrics(graph)
    html = lhc.render_html(graph, metrics)
    assert metrics["unfinished"] == 0
    assert metrics["remaining_minutes_max"] == 0
    assert metrics["eta_overdue"] is False
    assert "срок прошёл, остаток не начался" not in html


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
    assert goal_at > 0 and result_at > 0
    # The progress comes first, the goal follows - and it is open, so the owner
    # reads it without a tap.
    assert body.find("progress-strip") < body.find("kpis") < goal_at
    assert "<details class=\"panel brief-details brief-why-details\" open>" in body


def test_confirmed_progress_is_visible_without_tap():
    """A non-empty progress value is visible without opening the panel."""

    graph = graph_with_brief()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    body = html[html.find("<body"):]
    folded = re.search(
        r'<details class="panel brief-details"( open)?>\s*<summary>([^<]*)</summary>', body
    )
    assert folded, "свёрнутый блок технической части не найден"
    assert folded.group(1), "непустой подтверждённый прогресс должен быть виден сразу"
    assert "Текущий факт" in folded.group(2)
    assert "Что уже сделано" in body
    assert "Контракт принят, приёмка в доске" in body
    assert body.find("Что уже сделано") > body.find("kpis"), (
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
        # the owner put the progress above the goal; the goal stays open
        "tasks": [{
            "id": "L01",
            "label": "Починить доступ",
            "status": "running",
            "owner": "mavis",
            "session": "mvs_92b7a29fcb6147ae848063c2e62bf864",
            "model": "MiniMax-M3.1-Flash",
            "harness": "minimax-code",
            "description": "Задача: после настройки интерпретатор 100 содержит пакет mcp, чтобы интеграция могла подключаться.",
            "acceptance": "Импортировать mcp в целевом интерпретаторе и успешно создать тестовое соединение.",
            "affected_files": ["src/integration.py", "tests/test_integration.py"],
            "note": "Локальная среда пока без пакета mcp.",
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
        "Задача: после настройки интерпретатор 100 содержит пакет mcp, чтобы интеграция могла подключаться.",
        "Ожидаемый результат",
        "Импортировать mcp в целевом интерпретаторе",
        "Затрагиваемые файлы",
        "src/integration.py",
        "Локальная среда пока без пакета mcp.",
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
    # A blocker, task description and technical note stay separate.
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


def test_unbounded_task_details_roundtrip_report_graph_html_markdown_and_merge(tmp_path):
    description = "Человек сохраняет настройки и после перезагрузки видит выбранный канал. " * 80
    acceptance = "Открыть настройки, выбрать канал, сохранить, перезагрузить и увидеть тот же канал. " * 45
    paths = ["src/settings/page.py", "src/settings/store.py", "tests/settings/test_page.py"]
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: Сделать настройки понятными\n"
        "Бизнес-результат: Пользователь видит сохранённый канал\n"
        "Декомпозиция: 1 лист · 1 параллельно · 1 волна · слотов: 1\n\n"
        "⏳ (сохранение канала) оценка 15 минут\n"
        f"  Описание задачи: {description}\n"
        f"  Приёмка: {acceptance}\n"
        "  Затрагиваемые файлы: " + ", ".join(f"`{path}`" for path in paths) + "\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    exported = run_tool("export", str(report), "-o", str(graph_path))
    assert exported.returncode == 0, exported.stderr
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["tasks"][0]["description"] == description.strip()
    assert graph["tasks"][0]["acceptance"] == acceptance.strip()
    assert graph["tasks"][0]["affected_files"] == paths

    rendered = run_tool("render", str(graph_path), "--out-dir", str(tmp_path / "rendered"))
    assert rendered.returncode == 0, rendered.stderr
    html = (tmp_path / "rendered/plan.html").read_text(encoding="utf-8")
    markdown = (tmp_path / "rendered/plan.md").read_text(encoding="utf-8")
    for value in (description.strip(), acceptance.strip(), *paths):
        assert value in html
        assert value in markdown
    checked = run_tool("check-plan", str(report), str(graph_path))
    assert checked.returncode == 0, checked.stdout + checked.stderr

    # A later concise status report has no task-detail lines. --merge must keep
    # the last accepted details from the graph instead of discarding them.
    plain_report = tmp_path / "plain-report.md"
    plain_report.write_text("\n".join(
        line for line in report.read_text(encoding="utf-8").splitlines()
        if not line.startswith(("  Описание задачи:", "  Приёмка:", "  Затрагиваемые файлы:"))
    ) + "\n", encoding="utf-8")
    merged_path = tmp_path / "merged.json"
    merged = run_tool("export", str(plain_report), "-o", str(merged_path), "--merge", str(graph_path))
    assert merged.returncode == 0, merged.stderr
    merged_graph = json.loads(merged_path.read_text(encoding="utf-8"))
    assert merged_graph["tasks"][0]["description"] == description.strip()
    assert merged_graph["tasks"][0]["acceptance"] == acceptance.strip()
    assert merged_graph["tasks"][0]["affected_files"] == paths
    merged_check = run_tool("check-plan", str(plain_report), str(merged_path))
    assert merged_check.returncode == 0, merged_check.stdout + merged_check.stderr
    merged_render = run_tool("render", str(merged_path), "--out-dir", str(tmp_path / "merged-render"))
    assert merged_render.returncode == 0, merged_render.stderr
    merged_html = (tmp_path / "merged-render/plan.html").read_text(encoding="utf-8")
    merged_markdown = (tmp_path / "merged-render/plan.md").read_text(encoding="utf-8")
    for value in (description.strip(), acceptance.strip(), *paths):
        assert value in merged_html
        assert value in merged_markdown


def test_check_plan_reports_different_task_description(tmp_path):
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: Проверить сохранение\nБизнес-результат: Настройка сохраняется\n"
        "Декомпозиция: 1 лист · 1 параллельно · 1 волна · слотов: 1\n\n"
        "⏳ (сохранение настройки) оценка 10 минут\n"
        "  Описание задачи: Форма сохраняет выбранный пользователем канал.\n",
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "schema_version": 2,
        "tasks": [{"id": "L01", "label": "сохранение настройки", "status": "queued",
                   "depends_on": [], "description": "Форма теряет выбранный пользователем канал."}],
    }, ensure_ascii=False), encoding="utf-8")
    checked = run_tool("check-plan", str(report), str(graph))
    assert checked.returncode == 1
    assert "описание задачи не совпадает" in checked.stdout


def test_every_navigation_fragment_has_a_rendered_target():
    nav = lhc.merged_navigation(())
    fragments = re.findall(r'href=["\']#([^"\']+)["\']', nav)
    targets = set(re.findall(r'\bid=["\']([^"\']+)["\']', lhc.HTML_TEMPLATE))
    assert fragments, "page should have in-page section links"
    assert set(fragments) <= targets


def test_current_blocker_and_resolved_historical_blocker_stay_separate():
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "tasks": [{"id": "L01", "label": "Сохранить выбор", "status": "blocked",
                   "depends_on": [], "blocker": "Сервис сейчас не отвечает."}],
    })
    graph.journal = [{"at": "09:20", "action": "Устранено старое препятствие",
                      "result": "Удалён прежний конфликт доступа.", "evidence": "receipt-1"}]
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    blocker_panel = html[html.index('id="lhc-blocking"'):html.index('id="lhc-plan-gantt"')]
    journal_panel = html[html.index('id="lhc-journal"'):]
    assert "Сервис сейчас не отвечает." in blocker_panel
    assert "Удалён прежний конфликт доступа." in journal_panel
    assert "Удалён прежний конфликт доступа." not in blocker_panel


def test_done_leaf_and_technical_progress_do_not_claim_user_acceptance():
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "goal": "Покупатель находит нужный товар и оформляет безопасный заказ.",
        "business_result": "Покупатель видит итоговую цену и может подтвердить заказ.",
        "current_progress": "Исходники опубликованы, сборка и модульные проверки прошли.",
        "tasks": [{"id": "L01", "label": "Сборка и модульные проверки завершены",
                   "status": "done", "depends_on": [], "acceptance": "Сборка завершается без ошибок."}],
    })
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "Что будет работать" in html
    assert "Покупатель видит итоговую цену и может подтвердить заказ." in html
    assert "Сборка и модульные проверки завершены" in html
    assert "Исходники опубликованы, сборка и модульные проверки прошли." in html
    assert "Покупатель принял результат" not in html
    assert "Пользователь уже может подтвердить заказ" not in html


def test_leaf_percent_and_plain_russian_do_not_mean_business_readiness():
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "goal": "Пользователь получает и настраивает подписку на интересующие товары.",
        "business_result": "Пользователь получает уведомление до изменения цены.",
        "current_progress": "Все два технических листа закрыты; приёмка пользовательского пути не проводилась.",
        "tasks": [
            {"id": "L01", "label": "Добавить опрос цен", "status": "done", "depends_on": []},
            {"id": "L02", "label": "Собрать русские подписи", "status": "done", "depends_on": []},
        ],
    })
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "2 / 2" in html
    assert "100.0% листьев" in html
    assert "Все два технических листа закрыты; приёмка пользовательского пути не проводилась." in html
    assert "Пользователь получает уведомление до изменения цены." in html
    assert "готовность продукта 100%" not in html.lower()


def test_dependency_map_lists_every_prerequisite_for_long_join():
    tasks = []
    for index in range(1, 9):
        tasks.append({
            "id": f"L{index:02d}",
            "label": f"Шаг {index}: проверить часть сценария",
            "status": "queued",
            "depends_on": [f"L{prior:02d}" for prior in range(1, index)],
        })
    graph = lhc.parse_graph_json({"schema_version": 2, "tasks": tasks})
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    last_card = html[html.index("<template id='task-details-template-7'"):]
    for index in range(1, 8):
        assert f"Шаг {index}: проверить часть сценария" in last_card
    gantt = html[html.index('id="lhc-plan-gantt"'):html.index('id="lhc-leaves"')]
    for index in range(1, 9):
        assert f"Шаг {index}: проверить часть сценария" in gantt


def test_leaf_cell_shows_effort_and_calendar_span():
    """The table cell carries both numbers, not one that means the other."""

    graph = graph_with_owner()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "по часам 11 мин" in html
    assert "Усилие" in html


# --------------------------------------------------------------------------
# an unknown estimate is not a zero estimate
# --------------------------------------------------------------------------


def all_unknown_graph(leaf_count: int = 16):
    """A plan where no leaf carries an estimate at all."""

    return lhc.parse_graph_json(
        {
            "schema_version": 2,
            "slots": 2,
            "tasks": [
                {
                    "id": f"L{index:02d}",
                    "label": f"Лист {index}",
                    "status": "queued",
                    "depends_on": [],
                }
                for index in range(1, leaf_count + 1)
            ],
        }
    )


def gantt_section(html: str) -> str:
    start = html.index('class="panel panel-gantt"')
    end = html.index('id="lhc-leaves"')
    return html[start:end]


def test_the_gantt_draws_no_numeric_scale_when_no_duration_is_known():
    """F1: sixteen leaves without an estimate are not a one-minute plan."""

    graph = all_unknown_graph()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    panel = gantt_section(html)

    assert 'class="tick' not in panel, "шкала времени нарисована без единой известной оценки"
    assert "мин" not in panel, "панель Ганта обещает длительность, которой нет"
    assert "Шкала времени недоступна" in panel
    # the rows keep their state, the plan stays readable
    assert panel.count('class="gantt-status"') == 16
    assert "Ни один лист не имеет оценки длительности" in panel


def test_unknown_effort_is_not_reported_as_zero_minutes():
    """F2: unknown effort, critical path and remainder are named as unknown."""

    graph = all_unknown_graph()
    html = lhc.render_html(graph, lhc.build_metrics(graph))

    assert kpi_value(html, "Усилие") == "неизвестно"
    assert "критический путь неизвестен" in html
    # the known subtotal is kept and the unknown count is named
    assert "16 оценок неизвестны" in html
    # the remaining work is not claimed to be zero
    assert "Осталось</b> (без завершённых): неизвестно" in html
    assert "Осталось</b> (без завершённых): 0 мин" not in html
    # the counts that are really known stay exact
    assert kpi_value(html, "Осталось") == "16"
    assert kpi_value(html, "Готово") == "0 / 16"
    assert kpi_value(html, "Прогноз финиша") == "Срок неизвестен"


def test_a_partly_known_plan_keeps_the_known_subtotal_and_names_the_unknown():
    """A plan with one known estimate keeps its real numbers and says what is missing."""

    graph = lhc.parse_graph_json(
        {
            "schema_version": 2,
            "slots": 2,
            "tasks": [
                {
                    "id": "L01",
                    "label": "Известный лист",
                    "status": "queued",
                    "depends_on": [],
                    "estimate_minutes": {"minimum": 30, "maximum": 45},
                },
                {
                    "id": "L02",
                    "label": "Лист без оценки",
                    "status": "queued",
                    "depends_on": [],
                },
                {
                    "id": "L03",
                    "label": "Заблокированный лист без оценки",
                    "status": "blocked",
                    "depends_on": [],
                    "blocker": "ждём внешний ответ",
                },
            ],
        }
    )
    metrics = lhc.build_metrics(graph)
    html = lhc.render_html(graph, metrics)

    # the total is unknown, the known part is not lost
    assert kpi_value(html, "Усилие") == "неизвестно"
    assert "известная часть 45 мин" in html
    assert "2 оценок неизвестны" in html
    # the real timeline of the known leaf is still drawn
    assert 'class="tick' in gantt_section(html)
    # the leaf without an estimate gets no false bar
    assert 'class="gantt-noduration"' in html
    assert "Листьев без оценки длительности: 2" in html
    # blocked work without an estimate is not "0 мин"
    assert "Заблокировано</b> работы: неизвестно" in html
    # a blocked leaf is still counted as blocked
    assert kpi_value(html, "Заблокировано") == "1"
    # the remainder of a plan with unknown leaves is unknown, not zero
    assert "Осталось</b> (без завершённых): неизвестно" in html


def test_a_fully_known_plan_still_shows_its_numbers():
    """The honest state of a measured plan keeps every number as it was."""

    graph = lhc.parse_graph_json(
        {
            "schema_version": 2,
            "slots": 2,
            "tasks": [
                {
                    "id": "L01",
                    "label": "Первый",
                    "status": "queued",
                    "depends_on": [],
                    "estimate_minutes": {"minimum": 30, "maximum": 45},
                },
                {
                    "id": "L02",
                    "label": "Второй",
                    "status": "blocked",
                    "depends_on": [],
                    "estimate_minutes": {"minimum": 10, "maximum": 20},
                    "blocker": "ждём внешний ответ",
                },
            ],
        }
    )
    metrics = lhc.build_metrics(graph)
    html = lhc.render_html(graph, metrics)

    assert metrics["effort_known"] is True
    assert metrics["critical_known"] is True
    assert metrics["remaining_known"] is True
    assert kpi_value(html, "Усилие") == "1 ч 05 мин"
    assert "критический путь 45 мин" in html
    assert "Осталось</b> (без завершённых): 45 мин" in html
    assert "Заблокировано</b> работы: 20 мин" in html
    assert "Пик параллельности</b> по плану: 2 из 2 слотов" in html
    assert 'class="tick' in gantt_section(html)
    assert 'class="gantt-noduration"' not in html


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


# --------------------------------------------------------------------------
# the two-parent join: a lost second predecessor reorders real execution
# --------------------------------------------------------------------------

TWO_PARENT_REPORT = """Цель: проверить сохранение двух обязательных зависимостей
Бизнес-результат: сборка начинается только после готовности обоих предшественников
Декомпозиция: 3 листа · 2 параллельно · 2 волны · слотов: 2

🔄 работаем (подготовить интерфейс) начата 10:00, оценка 10 минут, прошло 2 минуты
🔄 работаем (подготовить обработчик) начата 10:00, оценка 15 минут, прошло 2 минуты, ∥ параллельно с листом 1
⏳ (соединить интерфейс и обработчик) начнём после листа 1 и листа 2, потому что нужны оба результата, примерно в 10:15, оценка 10 минут, закончим в 10:25
"""


def _join_report(phrase: str) -> str:
    lines = [
        "Цель: проверить разбор фразы зависимости",
        "Бизнес-результат: порядок запуска верен",
        "Декомпозиция: 5 листов · 1 параллельно · 1 волна · слотов: 1",
        "",
    ]
    lines += [f"✅ (подготовка {index}) оценка 5 минут" for index in range(1, 5)]
    lines.append(f"⏳ (сборка) {phrase}")
    return "\n".join(lines) + "\n"


def _join_deps(phrase: str) -> list:
    graph = lhc.parse_plan_report(_join_report(phrase))
    return graph.leaves[-1].depends_on


def test_two_parent_join_keeps_both_dependencies():
    """The defect: "после листа 1 и листа 2" exported only L01 and check-plan said OK."""

    graph = lhc.parse_plan_report(TWO_PARENT_REPORT)
    assert graph.leaves[2].depends_on == ["L01", "L02"]


def test_join_phrase_keeps_order_and_deduplicates():
    assert _join_deps("начнём после листа 3 и листа 1 и листа 3, оценка 10 минут") == ["L03", "L01"]


def test_join_phrase_expands_ranges():
    assert _join_deps("начнём после листов 1-3, оценка 10 минут") == ["L01", "L02", "L03"]
    assert _join_deps("начнём после листов 1–3 и листа 5, оценка 10 минут") == ["L01", "L02", "L03", "L05"]


def test_join_phrase_reads_russian_and_english_connectives():
    assert _join_deps("начнём после листа 1, а также листа 2, оценка 10 минут") == ["L01", "L02"]
    assert _join_deps("начнём после листа 1 и 2, оценка 10 минут") == ["L01", "L02"]
    assert _join_deps("start after leaf 1 and leaf 2, estimate 10 minutes") == ["L01", "L02"]
    assert _join_deps("start after leaves 1-2 plus leaf 4, estimate 10 minutes") == ["L01", "L02", "L04"]


def test_join_phrase_stops_before_schedule_numbers():
    """Times, estimates and slot arithmetic are not predecessors."""

    assert _join_deps(
        "начнём после листа 2, потому что нужен результат, примерно в 10:15, "
        "оценка 10 минут, закончим в 10:25"
    ) == ["L02"]
    assert _join_deps("начнём после листа 2; блокер: нет ключа") == ["L02"]


def test_export_and_check_plan_keep_the_two_parent_join(tmp_path):
    report = tmp_path / "plan.report.md"
    report.write_text(TWO_PARENT_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    exported = run_tool("export", str(report), "-o", str(graph_path))
    assert exported.returncode == 0, exported.stderr
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    join = [task for task in document["tasks"] if task["id"] == "L03"][0]
    assert join["depends_on"] == ["L01", "L02"]
    checked = run_tool("check-plan", str(report), str(graph_path))
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_check_plan_fails_when_the_graph_lost_a_dependency(tmp_path):
    """A stale or hand-edited graph must not reconcile green over a lost edge."""

    report = tmp_path / "plan.report.md"
    report.write_text(TWO_PARENT_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    assert run_tool("export", str(report), "-o", str(graph_path)).returncode == 0
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    for task in document["tasks"]:
        if task["id"] == "L03":
            task["depends_on"] = ["L01"]
    graph_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    checked = run_tool("check-plan", str(report), str(graph_path))
    assert checked.returncode == 1
    assert "РАСХОЖДЕНИЕ" in checked.stdout
    assert "зависим" in checked.stdout
    assert "L03" in checked.stdout
    assert "L02" in checked.stdout


def test_check_plan_fails_when_the_graph_added_a_dependency(tmp_path):
    report = tmp_path / "plan.report.md"
    report.write_text(TWO_PARENT_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    assert run_tool("export", str(report), "-o", str(graph_path)).returncode == 0
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    for task in document["tasks"]:
        if task["id"] == "L02":
            task["depends_on"] = ["L01"]
    graph_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    checked = run_tool("check-plan", str(report), str(graph_path))
    assert checked.returncode == 1
    assert "L02" in checked.stdout
    assert "L01" in checked.stdout


# --------------------------------------------------------------------------
# the declared schedule arithmetic is checked, not trusted
# --------------------------------------------------------------------------


def test_status_uses_computed_waves_and_names_the_declaration_divergence():
    report = (
        "Цель: проверить расчёт волн\n"
        "Бизнес-результат: волны посчитаны из графа\n"
        "Декомпозиция: 3 листа · 1 параллельно · 1 волна · слотов: 1\n\n"
        "✅ (первый шаг) оценка 5 минут\n"
        "⏳ (второй шаг) начнём после листа 1, оценка 5 минут\n"
        "⏳ (третий шаг) начнём после листа 2, оценка 5 минут\n"
    )
    graph = lhc.parse_plan_report(report)
    text = lhc.render_text(graph, lhc.build_metrics(graph))
    assert "волн: 3" in text
    assert "заявлено волн: 1" in text
    assert "расхождение" in text


def test_status_prefers_explicit_slots_and_names_the_parallel_claim():
    report = (
        "Цель: проверить слоты\n"
        "Бизнес-результат: ограничение ресурсов честное\n"
        "Декомпозиция: 1 лист · 3 параллельно · 1 волна · слотов: 2\n\n"
        "✅ (шаг) оценка 5 минут\n"
    )
    graph = lhc.parse_plan_report(report)
    metrics = lhc.build_metrics(graph)
    assert metrics["slots"] == 2
    text = lhc.render_text(graph, metrics)
    assert "заявлено 3 параллельно при 2 слотах" in text
    assert "расхождение" in text


def test_agreeing_declaration_is_not_flagged():
    graph = lhc.parse_plan_report(TWO_PARENT_REPORT)
    text = lhc.render_text(graph, lhc.build_metrics(graph))
    assert "волн: 2" in text
    assert "расхождение" not in text


# --------------------------------------------------------------------------
# DEFECT 1 (L05a): the projected report must be a valid report
#
# `render` writes plan.md, and `check-plan` rejected that very file with exit 2
# ("отчёт не распознан"). The summary lines carry the status glyph after a
# bullet and an id (`  - L01 · ✅ …`) and use `⋯` for a queued leaf, while the
# parser accepted a glyph only at line start and knew only `⏳`. The claim that
# "nobody writes them by hand" is false while the projection it rebuilds is not
# readable back. The full loop must close: leaves → build → render → check-plan
# exits 0.
# --------------------------------------------------------------------------


def write_leaves(plan_dir, leaves):
    """Write the source-of-truth leaf files of one plan and its plan.json."""

    leaves_dir = plan_dir / "leaves"
    leaves_dir.mkdir(parents=True, exist_ok=True)
    for payload in leaves:
        path = leaves_dir / f"{payload['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    plan_dir.joinpath("plan.json").write_text(
        json.dumps(
            {"title": "Проекция отчёта", "goal": "Закрыть интеграцию источника",
             "business_result": "Отчёт проходит check-plan", "slots": 2},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return plan_dir


def _build_grid_tool():
    from _inprocess import load_module

    return load_module(TOOL, name="lhc_grid_proj")


def _build_plan_json_tool():
    from _inprocess import load_module

    return load_module(ROOT / "src" / "common" / "tools" / "lhc_plan_json.py",
                       name="lhc_plan_json_proj")


def test_projected_report_is_a_valid_report(tmp_path):
    """leaves → build → render → check-plan on the generated plan.md exits 0."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    plan_json = _build_plan_json_tool()
    write_leaves(tmp_path, [
        {"id": "L01", "label": "контракт источника", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15},
         "started_at": "14:02", "finished_at": "14:09", "actual_minutes": 7},
        {"id": "L02", "label": "приём в доске", "status": "running", "depends_on": ["L01"],
         "estimate_minutes": {"minimum": 15, "maximum": 15}, "started_at": "14:12"},
        {"id": "L03", "label": "сборка и push", "status": "queued", "depends_on": ["L02"],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
    ])

    built = run_cli(plan_json, ["build", str(tmp_path)])
    assert built.returncode == 0, built.stderr
    graph_path = tmp_path / "plan.graph.json"
    assert graph_path.is_file()

    rendered = run_cli(grid, ["render", str(graph_path), "--out-dir", str(tmp_path)])
    assert rendered.returncode == 0, rendered.stderr
    report_path = tmp_path / "plan.md"
    assert report_path.is_file()

    # The projection must be readable back as a report at all.
    parsed = grid.load_plan_report(report_path)
    assert parsed is not None and len(parsed.leaves) == len(
        json.loads(graph_path.read_text(encoding="utf-8"))["tasks"]
    )

    checked = run_cli(grid, ["check-plan", str(report_path), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_parser_reads_the_glyph_and_position_variants_the_renderer_emits():
    """The parser accepts `- L01 · ✅ …` and the queued `⋯`, not only line-start glyphs."""

    grid = _build_grid_tool()
    text = (
        "Цель: закрыть интеграцию\n"
        "Бизнес-результат: отчёт читается обратно\n"
        "Декомпозиция: 2 листа · 1 параллельно · 2 волны · слотов: 1\n\n"
        "  - L01 · ✅ Готово · (контракт источника) · оценка 15 мин · усилие 7 мин · "
        "волна 1 · зависит: —\n"
        "  - L02 · ⋯ В очереди · (сборка) · оценка 10 мин · усилие не измерено · "
        "волна 2 · зависит: L01\n"
    )
    graph = grid.parse_plan_report(text)
    assert graph is not None
    assert len(graph.leaves) == 2
    first, second = graph.leaves
    assert first.status == "done"
    assert second.status == "queued"
    # The id is anchored from the line, not renumbered by position.
    assert first.id == "L01"
    assert second.id == "L02"
    # The `зависит:` variant is read back as a real dependency.
    assert second.depends_on == ["L01"]


# --------------------------------------------------------------------------
# DEFECT 2 (L05b): reconciliation is anchored by the leaf id, not by position
#
# The leaf collector sorts tasks by the dependency layer, so the graph order is
# L01, L02, L04, L03 — deliberately not the id order. compare_plan_with_graph
# paired the report lines with the graph leaves positionally, and an honest
# report written in the graph order produced six false divergences (the text
# of L04 was compared with L03). A report line whose id matches no leaf is a
# divergence, not a line to be silently shifted.
# --------------------------------------------------------------------------


ORDERED_GRAPH = {
    "schema_version": 2,
    "slots": 3,
    "tasks": [
        {"id": "L01", "label": "первый шаг", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
        {"id": "L02", "label": "второй шаг", "status": "running", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
        {"id": "L04", "label": "четвёртый шаг", "status": "queued", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
        {"id": "L03", "label": "третий шаг", "status": "queued", "depends_on": ["L02"],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
    ],
}

GRAPH_ORDER_REPORT = (
    "Цель: проверить сопоставление по идентификаторам\n"
    "Бизнес-результат: честный отчёт в порядке графа не даёт ложных расхождений\n"
    "  - L01 · ✅ Готово · (первый шаг) · оценка 10 мин · волна 1 · зависит: —\n"
    "  - L02 · 🔄 В работе · (второй шаг) · оценка 15 мин · волна 1 · зависит: —\n"
    "  - L04 · ⋯ В очереди · (четвёртый шаг) · оценка 15 мин · волна 1 · зависит: —\n"
    "  - L03 · ⋯ В очереди · (третий шаг) · оценка 10 мин · волна 2 · зависит: L02\n"
)


def test_reconciliation_is_anchored_by_id_not_by_position(tmp_path):
    """The measured defect: an honest report in the graph order gave 6 divergences."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(GRAPH_ORDER_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(ORDERED_GRAPH, ensure_ascii=False), encoding="utf-8")

    parsed = grid.parse_plan_report(report.read_text(encoding="utf-8"))
    assert parsed is not None
    graph = grid.parse_graph_json(ORDERED_GRAPH)
    result = grid.compare_plan_with_graph(parsed, graph)
    assert result.ok, (
        [leaf.id for leaf in result.extra_in_report],
        [leaf.id for leaf in result.missing_in_report],
        [(leaf.id, target.id) for leaf, target in result.status_mismatch],
    )

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_report_line_with_an_unknown_id_is_a_divergence_not_a_shift(tmp_path):
    """A line that names a leaf the graph does not have is named, not re-paired."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        GRAPH_ORDER_REPORT
        + "  - L07 · ✅ Готово · (несуществующий шаг) · оценка 5 мин · волна 1 · зависит: —\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(ORDERED_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 1
    assert "РАСХОЖДЕНИЕ" in checked.stdout
    assert "L07" in checked.stdout


def test_full_loop_with_the_out_of_order_graph(tmp_path):
    """leaves → build → render → check-plan exits 0 even when the layers reorder."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    plan_json = _build_plan_json_tool()
    write_leaves(tmp_path, [
        {"id": "L01", "label": "первый шаг", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
        {"id": "L02", "label": "второй шаг", "status": "running", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
        {"id": "L03", "label": "третий шаг", "status": "queued", "depends_on": ["L02"],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
        {"id": "L04", "label": "четвёртый шаг", "status": "queued", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
    ])
    plan_dir = tmp_path
    plan_dir.joinpath("plan.json").write_text(
        json.dumps({"title": "Порядок слоёв", "goal": "Проекция читается обратно",
                    "business_result": "check-plan принимает проекцию", "slots": 3},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    assert run_cli(plan_json, ["build", str(plan_dir)]).returncode == 0
    graph_path = plan_dir / "plan.graph.json"
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    assert [task["id"] for task in document["tasks"]] == ["L01", "L02", "L04", "L03"]

    assert run_cli(grid, ["render", str(graph_path), "--out-dir", str(plan_dir)]).returncode == 0
    checked = run_cli(grid, ["check-plan", str(plan_dir / "plan.md"), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr


# --------------------------------------------------------------------------
# DEFECT 2b: a fabricated shape line is a divergence, not a free claim
#
# «до 9 параллельно · 7 волн · слотов: 9» passed check-plan with exit 0 against
# a graph whose real figures are 3/2/3. The shape is computed from the graph;
# a declaration that contradicts it is named and exits non-zero.
# --------------------------------------------------------------------------


FABRICATED_SHAPE_REPORT = """Цель: проверить расхождение шапки
Бизнес-результат: выдуманная форма плана не проходит проверку
Декомпозиция: 4 листа · 9 параллельно · 7 волн · слотов: 9

✅ (первый шаг) оценка 10 минут
🔄 работаем (второй шаг) оценка 15 минут
⏳ (третий шаг) начнём после листа 2, оценка 10 минут
⏳ (четвёртый шаг) оценка 15 минут
"""


def test_fabricated_shape_line_exits_nonzero(tmp_path):
    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.report.md"
    report.write_text(FABRICATED_SHAPE_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(ORDERED_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 1
    assert "РАСХОЖДЕНИЕ" in checked.stdout
    assert "заявлено" in checked.stdout
    assert "9 параллельно" in checked.stdout or "параллельно: 9" in checked.stdout
    assert "7" in checked.stdout and "2" in checked.stdout


def test_honest_shape_line_passes(tmp_path):
    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.report.md"
    report.write_text(
        """Цель: проверить честную шапку
Бизнес-результат: заявленная форма совпадает с расчётной
Декомпозиция: 4 листа · 3 параллельно · 2 волны · слотов: 3

✅ (первый шаг) оценка 10 минут
🔄 работаем (второй шаг) оценка 15 минут
⏳ (третий шаг) начнём после листа 2, оценка 10 минут
⏳ (четвёртый шаг) оценка 15 минут
""",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(ORDERED_GRAPH, ensure_ascii=False), encoding="utf-8")
    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr


# --------------------------------------------------------------------------
# DEFECT 3 (L05c): an id with a letter suffix must be readable back
#
# The projected report of the live plan carried fifteen leaf lines and check-plan
# counted eight tasks. Every line whose id ended with a letter («  - L02b · 🔄
# В работе …») stopped being a leaf line at all, so those leaves were reported as
# missing from the report; and the dependency cell «зависит: L02, L02b» lost its
# second parent, because the id pattern knew only digits after the letter L. A
# letter suffix is a normal name in this scheme — one executor holds the «a»
# leaf and the «b» leaf of the same number at the same time — so the tool could
# not read the report it had written minutes before.
# --------------------------------------------------------------------------


SUFFIX_REPORT = (
    "Цель: проверить id листа с буквенным суффиксом\n"
    "Бизнес-результат: проекция с листьями L02b и L05a читается обратно\n"
    "  - L01 · ✅ Готово · (запись задачи) · оценка 15 мин · волна 1 · зависит: —\n"
    "  - L02 · ✅ Готово · (каталог моделей) · оценка 25 мин · волна 1 · зависит: —\n"
    "  - L02b · 🔄 В работе · (резолвер алиасов) · оценка 10 мин · волна 1 · зависит: —\n"
    "  - L05a · ⋯ В очереди · (отчёт из листьев) · оценка 15 мин · волна 2 · "
    "зависит: L01, L02b\n"
    "  - L05b · ⋯ В очереди · (привязка по id) · оценка 15 мин · начнём после листа 2b · "
    "волна 2\n"
    "  - L07aa · ⋯ В очереди · (карточки ролей) · оценка 15 мин · волна 2 · зависит: L05a · "
    "∥ параллельно с листом 2b\n"
)

SUFFIX_GRAPH = {
    "schema_version": 2,
    "slots": 2,
    "tasks": [
        {"id": "L01", "label": "запись задачи", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
        {"id": "L02", "label": "каталог моделей", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 25, "maximum": 25}},
        {"id": "L02b", "label": "резолвер алиасов", "status": "running", "depends_on": [],
         "estimate_minutes": {"minimum": 10, "maximum": 10}},
        {"id": "L05a", "label": "отчёт из листьев", "status": "queued",
         "depends_on": ["L01", "L02b"],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
    ],
}

SUFFIX_MATCHING_REPORT = (
    "Цель: проверить сверку с буквенными id\n"
    "Бизнес-результат: отчёт с листьями L02b и L05a сходится с графиком\n"
    "  - L01 · ✅ Готово · (запись задачи) · оценка 15 мин · волна 1 · зависит: —\n"
    "  - L02 · ✅ Готово · (каталог моделей) · оценка 25 мин · волна 1 · зависит: —\n"
    "  - L02b · 🔄 В работе · (резолвер алиасов) · оценка 10 мин · волна 1 · зависит: —\n"
    "  - L05a · ⋯ В очереди · (отчёт из листьев) · оценка 15 мин · волна 2 · "
    "зависит: L01, L02b\n"
)


def test_parser_reads_a_suffixed_id_in_the_line_the_cell_the_phrase_and_parallel():
    """L02b is one id: the line anchor, «зависит:», «после листа», «с листом»."""

    grid = _build_grid_tool()
    graph = grid.parse_plan_report(SUFFIX_REPORT)
    assert graph is not None
    assert [leaf.id for leaf in graph.leaves] == ["L01", "L02", "L02b", "L05a", "L05b", "L07aa"]
    by_id = {leaf.id: leaf for leaf in graph.leaves}
    # The dependency cell keeps both parents, the second one with its letter.
    assert by_id["L05a"].depends_on == ["L01", "L02b"]
    # The Russian join phrase reads a suffixed leaf too.
    assert by_id["L05b"].depends_on == ["L02b"]
    # So does the parallel marker, and a suffix of arbitrary length stays one id.
    assert by_id["L07aa"].depends_on == ["L05a"]
    assert by_id["L07aa"].parallel_with == ["L02b"]


def test_check_plan_accepts_a_report_whose_ids_carry_letters(tmp_path):
    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(SUFFIX_MATCHING_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(SUFFIX_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "4 · листьев в графе: 4" in checked.stdout


def test_full_loop_with_letter_suffixed_leaf_ids(tmp_path):
    """leaves/L02b.json → build → render → check-plan exits 0 with no hand edit."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    plan_json = _build_plan_json_tool()
    write_leaves(tmp_path, [
        {"id": "L01", "label": "запись задачи", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 15, "maximum": 15},
         "started_at": "14:02", "finished_at": "14:09", "actual_minutes": 7},
        {"id": "L02", "label": "каталог моделей", "status": "done", "depends_on": [],
         "estimate_minutes": {"minimum": 25, "maximum": 25},
         "started_at": "14:02", "finished_at": "14:22", "actual_minutes": 20},
        {"id": "L02b", "label": "резолвер алиасов", "status": "running", "depends_on": [],
         "estimate_minutes": {"minimum": 10, "maximum": 15}, "started_at": "14:31"},
        {"id": "L05a", "label": "отчёт из листьев", "status": "queued",
         "depends_on": ["L01", "L02b"],
         "estimate_minutes": {"minimum": 15, "maximum": 15}},
    ])

    assert run_cli(plan_json, ["build", str(tmp_path)]).returncode == 0
    graph_path = tmp_path / "plan.graph.json"
    assert run_cli(grid, ["render", str(graph_path), "--out-dir", str(tmp_path)]).returncode == 0

    report_text = (tmp_path / "plan.md").read_text(encoding="utf-8")
    assert "- L02b ·" in report_text
    assert "зависит: L01, L02b" in report_text

    checked = run_cli(grid, ["check-plan", str(tmp_path / "plan.md"), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_unknown_suffixed_id_is_named_not_dropped(tmp_path):
    """A line naming L99z is a divergence that names L99z, never a missing leaf."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        SUFFIX_MATCHING_REPORT
        + "  - L99z · ✅ Готово · (придуманный лист) · оценка 5 мин · волна 1 · зависит: —\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(SUFFIX_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 1
    assert "РАСХОЖДЕНИЕ" in checked.stdout
    assert "L99z" in checked.stdout


# --------------------------------------------------------------------------
# DEFECT 3 (L16): the report line names its leaf, and the parser reads that id
# from either side of the glyph
#
# A human writes "✅ L01 · …", the projected report writes "  - L01 · ✅ …",
# and the two forms say the same thing. The parser that only saw the id before
# the glyph turned the id of a human line into part of its caption, so the
# reconciliation fell back to the row number and invented ids for leaves the
# report never mentioned.
# --------------------------------------------------------------------------

BOTH_FORMS_REPORT = (
    "Цель: закрыть интеграцию источника\n"
    "Бизнес-результат: строка отчёта называет свой лист\n"
    "Декомпозиция: 4 листа · 2 параллельно · 2 волны · слотов: 2\n\n"
    "  - L01 · ✅ Готово · (контракт источника) · оценка 15 мин · волна 1 · зависит: —\n"
    "✅ L02 · (поиск источника) · оценка 15 мин · волна 1 · зависит: —\n"
    "✅ L02b · (резолвер алиасов) · оценка 10 мин · волна 2 · зависит: L01\n"
    "  - L05a · ✅ Готово · (отчёт из листьев) · оценка 15 мин · волна 2 · зависит: L02\n"
)

BOTH_FORMS_GRAPH = {
    "schema_version": 2,
    "slots": 2,
    "tasks": [
        {"id": "L01", "label": "контракт источника", "status": "done", "depends_on": []},
        {"id": "L02", "label": "поиск источника", "status": "done", "depends_on": []},
        {"id": "L02b", "label": "резолвер алиасов", "status": "done", "depends_on": ["L01"]},
        {"id": "L05a", "label": "отчёт из листьев", "status": "done", "depends_on": ["L02"]},
    ],
}


def test_the_parser_reads_the_leaf_id_on_either_side_of_the_glyph():
    """«✅ L01 · …» and «  - L01 · ✅ …» name the same leaf, suffixes included."""

    grid = _build_grid_tool()
    graph = grid.parse_plan_report(BOTH_FORMS_REPORT)
    assert graph is not None
    assert [leaf.id for leaf in graph.leaves] == ["L01", "L02", "L02b", "L05a"]
    # The id is named by the line, so the reconciliation may rely on it.
    assert all(leaf.id_explicit for leaf in graph.leaves)
    # The id is not part of the caption: the caption is the leaf's own name.
    assert [leaf.label for leaf in graph.leaves] == [
        "контракт источника",
        "поиск источника",
        "резолвер алиасов",
        "отчёт из листьев",
    ]


def test_check_plan_accepts_both_forms_of_the_same_report(tmp_path):
    """A report written in either form reconciles by id, with no invented leaf."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(BOTH_FORMS_REPORT, encoding="utf-8")
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(BOTH_FORMS_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr
    # Every leaf was matched by its id, so no row was fitted by its number.
    assert "сопоставлено по позиции" not in checked.stdout
    assert "без листа в графе" not in checked.stdout


def test_a_row_without_an_id_says_it_was_matched_by_position(tmp_path):
    """A row that names no leaf is paired by its number, and that is said out loud."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: закрыть интеграцию источника\n"
        "Бизнес-результат: строки отчёта не называют свой лист\n"
        "Декомпозиция: 2 листа · 1 параллельно · 1 волна · слотов: 1\n\n"
        "✅ (контракт источника) начата 14:02 закончена 14:09\n"
        "✅ (поиск источника) начата 14:02 закончена 14:11\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps({
        "schema_version": 2,
        "slots": 1,
        "tasks": [
            {"id": "L01", "label": "контракт источника", "status": "done", "depends_on": []},
            {"id": "L02", "label": "поиск источника", "status": "done", "depends_on": []},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 0, checked.stdout + checked.stderr
    # The match is honest, but it is a guess, and the reader is told so.
    assert "сопоставлено по позиции, а не по id: 2" in checked.stdout
    assert "не называют свой лист" in checked.stdout


def test_a_row_without_an_id_in_the_wrong_order_is_a_divergence(tmp_path):
    """The rows and the leaves are in a different order: that is named, not smoothed."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: закрыть интеграцию источника\n"
        "Бизнес-результат: порядок строк отчёта не совпадает с порядком листьев\n"
        "Декомпозиция: 2 листа · 1 параллельно · 1 волна · слотов: 1\n\n"
        "✅ (поиск источника) начата 14:02 закончена 14:11\n"
        "✅ (контракт источника) начата 14:02 закончена 14:09\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps({
        "schema_version": 2,
        "slots": 1,
        "tasks": [
            {"id": "L01", "label": "контракт источника", "status": "done", "depends_on": []},
            {"id": "L02", "label": "поиск источника", "status": "done", "depends_on": []},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["check-plan", str(report), str(graph_path)])
    assert checked.returncode == 1, checked.stdout + checked.stderr
    assert "РАСХОЖДЕНИЕ" in checked.stdout
    assert "порядок строк отчёта не совпадает" in checked.stdout
    # The names on both sides are named, so the reader sees which leaf is meant.
    assert "L01" in checked.stdout
    assert "L02" in checked.stdout


# --------------------------------------------------------------------------
# DEFECT 4 (L17): the kernel accepts an over-long leaf silently, and the queue
# cannot say what it waits for
#
# The format promises a leaf of about fifteen minutes, and a leaf in the queue
# owes the report three things: why it cannot start yet, when it is planned to
# start and when it is planned to finish.
# --------------------------------------------------------------------------

OVER_CAP_GRAPH = {
    "schema_version": 2,
    "slots": 1,
    "tasks": [
        {
            "id": "L01",
            "label": "Долгий расчёт",
            "status": "queued",
            "depends_on": [],
            "estimate_minutes": {"minimum": 30, "maximum": 50},
        }
    ],
}


def test_an_over_long_leaf_is_named_by_the_kernel(tmp_path):
    """A 30–50 minute leaf is named, not printed as an ordinary estimate."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(OVER_CAP_GRAPH, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["validate", str(graph_path)])
    payload = json.loads(checked.stdout)
    # The breach is named with the leaf, its estimate and the cap.
    cap_warnings = [w for w in payload["warnings"] if "ПРЕДЕЛ ОЦЕНКИ ЛИСТА" in w or "при пределе" in w]
    assert cap_warnings, payload["warnings"]
    assert "L01" in " ".join(cap_warnings)
    assert "50 мин" in " ".join(cap_warnings)
    assert "15 мин" in " ".join(cap_warnings)

    # The same breach is named where the plan is read: the summary and the page.
    summary = run_cli(grid, ["status", str(graph_path)])
    assert "ПРЕДЕЛ ОЦЕНКИ ЛИСТА" in summary.stdout


def test_a_leaf_that_says_why_it_is_longer_is_not_a_breach(tmp_path):
    """The same leaf with the reason recorded passes the cap."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    allowed = json.loads(json.dumps(OVER_CAP_GRAPH))
    allowed["tasks"][0]["estimate_over_limit_reason"] = "расчёт стоимости сам по себе"
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps(allowed, ensure_ascii=False), encoding="utf-8")

    checked = run_cli(grid, ["validate", str(graph_path)])
    payload = json.loads(checked.stdout)
    assert not [w for w in payload["warnings"] if "ПРЕДЕЛ ОЦЕНКИ ЛИСТА" in w]
    assert checked.returncode == 0


def test_the_queue_names_its_reason_and_its_planned_times(tmp_path):
    """A leaf in the queue shows all three things it owes the report."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: t\n"
        "Бизнес-результат: t\n"
        "Декомпозиция: 1 лист · 1 параллельно · 1 волна · слотов: 1\n\n"
        "⏳ (сборка и push) начнём после листа 3, потому что нужен принятый контракт, "
        "примерно в 14:30, оценка 10 минут, закончим в 14:40\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    assert run_cli(grid, ["export", str(report), "-o", str(graph_path)]).returncode == 0

    # The reason and the two planned times are read out of the line.
    graph = grid.parse_graph_json(json.loads(graph_path.read_text(encoding="utf-8")))
    leaf = graph.by_id()["L01"]
    assert leaf.wait_reason == "нужен принятый контракт"
    assert leaf.planned_start == "14:30"
    assert leaf.planned_finish == "14:40"
    # A leaf that has not started owns no work window.
    assert leaf.started_at == ""
    assert leaf.finished_at == ""

    # The summary (and so plan.md) names all three.
    summary = run_cli(grid, ["status", str(graph_path)])
    assert "ждёт: нужен принятый контракт" in summary.stdout
    assert "начнём 14:30" in summary.stdout
    assert "закончим 14:40" in summary.stdout

    # The page names them too.
    html = run_cli(grid, ["render", str(graph_path), "-o", str(tmp_path / "plan.html")])
    assert html.returncode == 0
    page = (tmp_path / "plan.html").read_text(encoding="utf-8")
    assert "ждёт: нужен принятый контракт" in page
    assert "начнём 14:30" in page
    assert "закончим 14:40" in page


def test_a_queued_leaf_without_a_reason_does_not_pass_in_silence(tmp_path):
    """A leaf in the queue without a reason says that the reason is missing."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    report = tmp_path / "plan.md"
    report.write_text(
        "Цель: t\n"
        "Бизнес-результат: t\n"
        "Декомпозиция: 1 лист · 1 параллельно · 1 волна · слотов: 1\n\n"
        "⏳ (сборка и push) исполнитель ещё не назначен, примерно в 14:30, "
        "оценка 10 минут, закончим в 14:40\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "plan.graph.json"
    assert run_cli(grid, ["export", str(report), "-o", str(graph_path)]).returncode == 0

    summary = run_cli(grid, ["status", str(graph_path)])
    assert "ждёт: причина не названа" in summary.stdout


def test_a_running_leaf_shows_the_time_passed_at_the_moment_of_the_build(tmp_path):
    """A running leaf is weighed against its estimate at the moment of the build."""

    from _inprocess import run_cli

    grid = _build_grid_tool()
    graph_path = tmp_path / "plan.graph.json"
    graph_path.write_text(json.dumps({
        "schema_version": 2,
        "slots": 1,
        "tasks": [
            {
                "id": "L01",
                "label": "Идущий лист",
                "status": "running",
                "depends_on": [],
                "estimate_minutes": {"minimum": 15, "maximum": 15},
                "started_at": "14:12",
            }
        ],
    }, ensure_ascii=False), encoding="utf-8")

    summary = run_cli(grid, ["status", str(graph_path)])
    # The time that has passed is a fact of the build, and it is named as such.
    assert "на момент сборки" in summary.stdout
    # The leaf overran its estimate, and the delay is named.
    assert "отстаём" in summary.stdout


def test_the_collector_refuses_an_over_long_leaf_and_accepts_a_named_one(tmp_path):
    """The gate that decides: a 30–50 minute leaf is refused, a named one passes."""

    from _inprocess import run_cli

    collector = _build_plan_json_tool()
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)

    def leaf(**extra):
        payload = {
            "id": "L01",
            "label": "Долгий расчёт",
            "status": "queued",
            "depends_on": [],
            "estimate_minutes": {"minimum": 30, "maximum": 50},
        }
        payload.update(extra)
        return payload

    (plan_dir / "leaves" / "L01.json").write_text(
        json.dumps(leaf(), ensure_ascii=False), encoding="utf-8"
    )
    (plan_dir / "plan.json").write_text(
        json.dumps({"title": "t", "goal": "g", "business_result": "b", "slots": 1}),
        encoding="utf-8",
    )

    checked = run_cli(collector, ["check", str(plan_dir)])
    assert checked.returncode == 1, checked.stdout + checked.stderr
    # The breach is named with the leaf and the cap.
    assert "ПРЕДЕЛ ОЦЕНКИ ЛИСТА" in checked.stderr
    assert "L01" in checked.stderr
    assert "15 мин" in checked.stderr

    # The same leaf, with the reason recorded, passes.
    (plan_dir / "leaves" / "L01.json").write_text(
        json.dumps(
            leaf(estimate_over_limit_reason="расчёт стоимости сам по себе"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    allowed = run_cli(collector, ["check", str(plan_dir)])
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
