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
    assert "Подтверждённый прогресс" in folded.group(2)
    assert "Подтверждённый прогресс" in body
    assert "Контракт принят, приёмка в доске" in body
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
    assert "Ожидаемый бизнес-результат" in html
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
