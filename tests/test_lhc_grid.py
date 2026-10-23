"""Tests for the LHC task-graph renderer."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'src' / 'common' / 'tools' / 'lhc_grid.py'
VALIDATOR = ROOT / 'scripts' / 'lhc_validate_graph.py'


def load_tool():
    spec = importlib.util.spec_from_file_location('lhc_grid', TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_validator():
    spec = importlib.util.spec_from_file_location('lhc_validate_graph', VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True,
    )


def run_validator(*args):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args], capture_output=True, text=True,
    )


lhc = load_tool()
validator = load_validator()


REPORT = """Цель: закрыть интеграцию источника
Бизнес-результат: сообщение превращается в карточку
Декомпозиция: 4 листа · 2 параллельно · 2 волны · слотов: 2

✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
✅ (поиск источника) начата 14:02 закончена 14:11, оценка 15 минут, факт 9 минут, ∥ параллельно с листом 1

🔄 работаем (приём в доске) начата 14:12, оценка 20 минут, прошло 22 минут, отстаём потому что: ждём ключ
⏳ (сборка и push) начнём после листа 3, потому что нужен принятый контракт, примерно в 14:30, оценка 10 минут, закончим в 14:40
"""


class PlanReportTests(unittest.TestCase):
    def setUp(self):
        self.graph = lhc.parse_plan_report(REPORT)
        self.assertIsNotNone(self.graph)

    def test_headers(self):
        self.assertEqual(self.graph.goal, 'закрыть интеграцию источника')
        self.assertEqual(self.graph.business_result, 'сообщение превращается в карточку')
        self.assertEqual(self.graph.declared_leaves, 4)
        self.assertEqual(self.graph.slots, 2)

    def test_leaf_states(self):
        statuses = [leaf.status for leaf in self.graph.leaves]
        self.assertEqual(statuses, ['done', 'done', 'running', 'queued'])

    def test_leaf_times_and_estimates(self):
        first, second, third, fourth = self.graph.leaves
        self.assertEqual(first.started_at, '14:02')
        self.assertEqual(first.finished_at, '14:09')
        self.assertEqual(first.actual_minutes, 7)
        self.assertEqual(first.estimate_max, 15)
        self.assertEqual(second.parallel_with, ['L01'])
        self.assertEqual(third.actual_minutes, 22)
        self.assertIn('ждём ключ', third.note)
        self.assertEqual(fourth.depends_on, ['L03'])
        self.assertEqual(fourth.estimate_max, 10)

    def test_live_items_mirror_leaves(self):
        self.assertEqual(len(self.graph.live_items), 4)
        self.assertEqual(self.graph.live_items[0]['leaf'], 'L01')


class LegacyPlanTests(unittest.TestCase):
    PLAN = """**Цель:** проверить разбор

**Бизнес-результат:** виден прогресс

Декомпозиция: 39 листьев · до 3 параллельно · 2 волны · слотов: 4.

## Текущая волна

- ✅ контракт источника проверен, оценка 20 мин, факт 18 мин
- 🔄 приём в доске, назначено 05:48, оценка 20 мин
- ⏳ независимый прогон, срок восстановления неизвестен

## Декомпозиция и срок

| № | Используемый результат листа | Оценка активной работы | Зависимость |
|---|---|---|---|
| 01 | Проверенный путь исходника к доске | 15 мин на проверку | нет, первая волна |
| 02 | Исходное сообщение связано с поручением | 15 мин, предварительно | 01 |
| 03 | Прогон и приёмка | 10 мин активных + 30 мин пассивного ожидания | 02 |
"""

    def setUp(self):
        self.graph = lhc.parse_legacy_plan(self.PLAN)
        self.assertIsNotNone(self.graph)

    def test_table_leaves(self):
        self.assertEqual([leaf.id for leaf in self.graph.leaves], ['01', '02', '03'])
        self.assertEqual(self.graph.leaves[0].estimate_max, 15)
        self.assertEqual(self.graph.leaves[1].depends_on, ['01'])
        self.assertEqual(self.graph.leaves[2].depends_on, ['02'])

    def test_external_wait_is_separate(self):
        leaf = self.graph.leaves[2]
        self.assertEqual(leaf.estimate_max, 10)
        self.assertIn('ожидание', leaf.note)

    def test_live_counts_come_from_the_wave_log(self):
        metrics = lhc.build_metrics(self.graph)
        self.assertEqual(metrics['live_total'], 3)
        self.assertEqual(metrics['done'], 1)
        self.assertEqual(metrics['running'], 1)
        self.assertEqual(metrics['total'], 3)
        self.assertEqual(metrics['slots'], 4)

    def test_dependency_cell(self):
        self.assertEqual(lhc.parse_dependency_cell('нет, первая волна'), [])
        self.assertEqual(lhc.parse_dependency_cell('03,04'), ['03', '04'])
        self.assertEqual(lhc.parse_dependency_cell('32–35'), ['32', '33', '34', '35'])
        self.assertEqual(lhc.parse_dependency_cell('22, доступ21'), ['22', '21'])


class GraphJsonTests(unittest.TestCase):
    def test_version_2_document(self):
        document = {
            'schema_version': 2,
            'title': 'demo',
            'goal': 'goal',
            'slots': 2,
            'tasks': [
                {'id': 'a', 'label': 'first', 'status': 'done', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 10}, 'actual_minutes': 7},
                {'id': 'b', 'label': 'second', 'status': 'queued', 'depends_on': ['a']},
            ],
        }
        graph = lhc.parse_graph_json(document)
        self.assertEqual(graph.title, 'demo')
        self.assertEqual(graph.slots, 2)
        self.assertEqual(graph.leaves[0].estimate_max, 10)
        self.assertEqual(graph.leaves[0].actual_minutes, 7)
        self.assertEqual(graph.leaves[1].depends_on, ['a'])

    def test_version_1_document_still_reads(self):
        document = {
            'schema_version': 1,
            'tasks': [
                {'id': 'a', 'role': 'Lead', 'model_class': 'frontier', 'depends_on': [],
                 'read_paths': [], 'write_paths': [], 'acceptance': 'ok'},
            ],
        }
        graph = lhc.parse_graph_json(document)
        self.assertEqual(len(graph.leaves), 1)

    def test_unsupported_version_is_rejected(self):
        with self.assertRaises(ValueError):
            lhc.parse_graph_json({'schema_version': 9, 'tasks': [{'id': 'a'}]})

    def test_unknown_estimate_reason_round_trips_without_zero_duration(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [
                {'id': 'done', 'label': 'Done', 'status': 'done', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'wait', 'label': 'External wait', 'status': 'blocked', 'depends_on': ['done'],
                 'estimate_unknown_reason': 'Owner has not confirmed access.'},
                {'id': 'known', 'label': 'Known next work', 'status': 'queued', 'depends_on': [],
                 'estimate_minutes': {'minimum': 10, 'maximum': 10}},
            ],
        })
        with patch.object(lhc, 'now_clock', return_value=17 * 60):
            metrics = lhc.build_metrics(graph)
        self.assertEqual(metrics['unknown_estimate_pending'], 1)
        self.assertEqual(metrics['eta_clock_max'], '')
        self.assertEqual(metrics['remaining_minutes_max'], 10)
        self.assertEqual(graph.leaves[1].duration_label, 'Срок неизвестен')
        self.assertEqual(lhc.parse_graph_json(lhc.export_graph(graph)).leaves[1].estimate_unknown_reason,
                         'Owner has not confirmed access.')
        html = lhc.render_html(graph, metrics)
        self.assertIn('Срок неизвестен', html)
        self.assertIn('Известная часть работы', html)
        self.assertIn('без неизвестных оценок и ожиданий', html)

    def test_forecast_counts_from_the_last_confirmed_event(self):
        """The forecast is anchored at the last confirmed event.

        An idle plan must not push its own finish away with every minute of
        silence. The anchor and the idle time are shown instead of being
        hidden inside the horizon, and a horizon that already passed is
        reported as passed.
        """
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [{'id': 'next', 'label': 'Next', 'status': 'queued', 'depends_on': [],
                       'estimate_minutes': {'minimum': 5, 'maximum': 5}, 'started_at': '15:19'}],
        })
        with patch.object(lhc, 'now_clock', return_value=17 * 60):
            metrics = lhc.build_metrics(graph)
        self.assertEqual(metrics['eta_clock_min'], '15:24')
        self.assertEqual(metrics['eta_clock_max'], '15:24')
        self.assertEqual(metrics['eta_anchor_clock'], '15:19')
        self.assertEqual(metrics['eta_anchor_idle_minutes'], 101)
        self.assertTrue(metrics['eta_overdue'])
        html = lhc.render_html(graph, metrics)
        self.assertIn('отсчёт от последнего события 15:19', html)
        self.assertIn('срок прошёл', html)

    def test_external_wait_withholds_clock_eta_and_round_trips(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'external_waits': 'Ждём подтверждения владельца; срок неизвестен.',
            'tasks': [{'id': 'next', 'label': 'Next', 'status': 'queued', 'depends_on': [],
                       'estimate_minutes': {'minimum': 5, 'maximum': 5}}],
        })
        with patch.object(lhc, 'now_clock', return_value=17 * 60):
            metrics = lhc.build_metrics(graph)
        self.assertEqual(metrics['eta_clock_max'], '')
        self.assertTrue(metrics['external_wait_unknown'])
        self.assertIn('неизвестен из-за внешнего ожидания', lhc.render_text(graph, metrics).lower())
        self.assertEqual(lhc.parse_graph_json(lhc.export_graph(graph)).external_waits,
                         'Ждём подтверждения владельца; срок неизвестен.')

    def test_declared_model_class_survives_the_round_trip(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [{'id': 'a', 'label': 'a', 'status': 'queued', 'depends_on': [],
                       'model': 'gpt-6-luna', 'model_class': 'gpt-6-luna'}],
        })
        exported = lhc.export_graph(graph)
        self.assertEqual(exported['tasks'][0]['model_class'], 'gpt-6-luna')
        self.assertEqual(lhc.parse_graph_json(exported).leaves[0].model_class, 'gpt-6-luna')


class ScheduleTests(unittest.TestCase):
    def _graph(self):
        return lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'tasks': [
                {'id': 'a', 'label': 'a', 'depends_on': [], 'estimate_minutes': {'minimum': 10, 'maximum': 10}},
                {'id': 'b', 'label': 'b', 'depends_on': [], 'estimate_minutes': {'minimum': 10, 'maximum': 10}},
                {'id': 'c', 'label': 'c', 'depends_on': [], 'estimate_minutes': {'minimum': 10, 'maximum': 10}},
                {'id': 'd', 'label': 'd', 'depends_on': ['a', 'b'], 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })

    def test_capacity_is_respected(self):
        schedule = lhc.schedule_graph(self._graph(), use_max=True)
        self.assertLessEqual(schedule.peak, 2)
        # a and b run first, then c and the join run together: 10 + 10.
        self.assertEqual(schedule.makespan, 20)
        self.assertEqual(schedule.starts['a'], 0)
        self.assertEqual(schedule.starts['b'], 0)
        self.assertEqual(schedule.starts['c'], 10)
        self.assertEqual(schedule.starts['d'], 10)

    def test_critical_path(self):
        schedule = lhc.schedule_graph(self._graph(), use_max=True)
        self.assertEqual(schedule.critical_path[-1], 'd')
        self.assertIn('a', schedule.critical_path)

    def test_metrics_report_remaining_work(self):
        graph = self._graph()
        graph.leaves[0].status = 'done'
        metrics = lhc.build_metrics(graph)
        self.assertEqual(metrics['done'], 1)
        self.assertLess(metrics['remaining_minutes_max'], metrics['effort_minutes'])


class RenderTests(unittest.TestCase):
    def test_html_contains_the_dashboard_parts(self):
        graph = lhc.parse_plan_report(REPORT)
        metrics = lhc.build_metrics(graph)
        html = lhc.render_html(graph, metrics)
        for needle in ('Готово', 'Гант', 'Что блокирует', 'Прогноз', 'Критический путь', 'L01'):
            self.assertIn(needle, html)
        self.assertNotIn('{cards}', html)
        self.assertNotIn('None', html.split('<footer>')[0].replace('Nonexistent', ''))

    def test_html_escapes_labels(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [{'id': 'a', 'label': '<script>alert(1)</script>', 'depends_on': []}],
        })
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_text_view_lists_the_leaves_and_the_waves(self):
        graph = lhc.parse_plan_report(REPORT)
        metrics = lhc.build_metrics(graph)
        text = lhc.render_text(graph, metrics)
        self.assertIn('Листья плана (4):', text)
        self.assertIn('волна 1', text)
        self.assertIn('волн:', text)
        self.assertIn('L01', text)

    def test_business_outcome_and_technical_details_have_separate_hierarchy(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'goal': 'Поручение запускается и завершается общим результатом',
            'business_result': 'Участники продолжают одну историю и принимают результат',
            'current_progress': 'Пока подтверждён только исследовательский canary',
            'tasks': [{
                'id': 'T1', 'label': 'Проверить исследовательский результат',
                'status': 'running', 'owner': 'Luna', 'session': 'opaque-session',
                'model': 'gpt-6-luna', 'depends_on': [],
            }],
        })
        self.assertEqual(
            lhc.parse_graph_json(lhc.export_graph(graph)).current_progress,
            graph.current_progress,
        )
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn('Ожидаемый бизнес-результат', html)
        self.assertIn('Подтверждённый прогресс', html)
        self.assertIn("class='task-details-trigger'", html)
        self.assertIn("id='task-details-host'", html)
        self.assertIn('<details class="technical">', html)
        self.assertIn('.table-scroll { max-width: 100%; overflow-x: auto;', html)
        self.assertIn('@media (max-width: 640px)', html)
        self.assertEqual(html.count('.grid { display: grid'), 1)
        self.assertIn('@media (max-width: 1000px) { .grid { grid-template-columns: minmax(0, 1fr); } }', html)
        # The one sticky layer is the progress strip; the goal block must not
        # be a second one.
        self.assertEqual(html.count('position: sticky; top: 0;'), 1)
        # The goal and the business result are the reason the work exists. The
        # owner put the progress above them, so they come after the state -
        # but they stay open, so nothing is hidden behind a tap.
        self.assertIn('<details class="panel brief-details brief-why-details" open>', html)
        self.assertLess(html.index('class="kpis"'), html.index('Цель'))
        self.assertLess(html.index('Цель'), html.index('Подтверждённый прогресс'))
        self.assertIn('<details class="panel brief-details">', html)

    def test_long_task_ids_do_not_compete_with_gantt_or_table_titles(self):
        long_id = 'integrator-source-subject-39e04120-97e5-4302-9756-5072de10c84c'
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [{
                'id': long_id,
                'label': 'Сверить официальный сайт и публичный деловой контакт',
                'status': 'running',
                'depends_on': [],
                'estimate_minutes': {'minimum': 5, 'maximum': 10},
            }],
        })
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn('class="gantt-axis-row"', html)
        self.assertIn('class="tick tick-0"', html)
        self.assertIn('class="tick tick-6"', html)
        self.assertIn('class="gantt-label"', html)
        self.assertIn('class="gantt-track"', html)
        self.assertIn("class='task-title'", html)
        self.assertIn(f'<dt>Код</dt><dd>{long_id}</dd>', html)
        self.assertIn("data-details-id='0'", html)
        self.assertIn("id='task-details-template-0'", html)
        self.assertIn("class='task-details-close'", html)
        self.assertIn("detailsRow.scrollIntoView({ block: 'nearest' });", html)
        self.assertNotIn('<th>ID</th>', html)
        self.assertIn('.gantt-row { display: grid; grid-template-columns: minmax(240px, 320px) minmax(360px, 1fr);', html)
        self.assertIn('.table-leaves { min-width: 920px; width: 100%; table-layout: fixed; }', html)
        self.assertIn('.table-leaves th:nth-child(5) { width: 120px; }', html)
        self.assertIn('.task-details-host { position: static; width: 100%; margin-top: 12px; }', html)
        self.assertIn('padding: 0 5px; min-width: 0; white-space: normal; overflow-wrap: anywhere; }', html)
        self.assertIn('.task-details { display: grid; grid-template-columns: minmax(110px, auto) minmax(0, 1fr);', html)
        self.assertIn('.task-details dd { margin: 0; min-width: 0; width: 100%; overflow-wrap: anywhere; word-break: break-word; }', html)
        self.assertIn('.status { color: var(--c); font-weight: 600; white-space: nowrap; }', html)

    def test_blocker_details_are_structured_and_dependencies_are_human_readable(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [
                {'id': 'qa_scope', 'label': 'Выдать доступ к тестовому проекту',
                 'status': 'blocked', 'depends_on': [],
                 'blocker': 'Текущий project grant отсутствует.',
                 'blocker_details': {
                     'reason': 'Для тестовой команды ещё не выдано разрешение на проект.',
                     'responsible': 'Владелец QA-проекта',
                     'next_action': 'Выдать доступ через штатный интерфейс проекта.',
                     'human_required': 'yes',
                     'human_action': 'Нужно подтвердить участника и проект.',
                 },
                 'acceptance': 'Тестовый участник видит точный проект.'},
                {'id': 'canary', 'label': 'Запустить проверку полного цикла',
                 'status': 'queued', 'depends_on': ['qa_scope'],
                 'acceptance': 'Поручение доходит до ручной приёмки.'},
            ],
        })
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        status_text = lhc.render_text(graph, lhc.build_metrics(graph))
        exported = lhc.export_graph(graph)
        self.assertIn('<b>Почему ждём:</b> Для тестовой команды ещё не выдано разрешение на проект.', html)
        self.assertIn('<b>Кто делает:</b> Владелец QA-проекта', html)
        self.assertIn('<b>Следующий шаг:</b> Выдать доступ через штатный интерфейс проекта.', html)
        self.assertIn('<b>Нужен ли человек:</b> Да. Нужно подтвердить участника и проект.', html)
        self.assertIn('<dt>Зависит от</dt><dd>Выдать доступ к тестовому проекту</dd>', html)
        self.assertIn('<dt>Ожидаемый результат</dt><dd>Поручение доходит до ручной приёмки.</dd>', html)
        self.assertNotIn('лист qa_scope', html)
        self.assertIn('Почему ждём: Для тестовой команды ещё не выдано разрешение на проект.', status_text)
        self.assertIn('Кто делает: Владелец QA-проекта', status_text)
        self.assertNotIn('qa_scope:', status_text)
        self.assertEqual(exported['tasks'][0]['blocker_details']['human_required'], 'yes')
        self.assertEqual(exported['tasks'][1]['acceptance'], 'Поручение доходит до ручной приёмки.')

    def test_legacy_graph_without_blocker_details_still_renders(self):
        graph = lhc.parse_graph_json({
            'schema_version': 1,
            'tasks': [{'id': 'legacy', 'label': 'Старый блокер', 'status': 'blocked',
                       'depends_on': [], 'blocker': 'Ждём прежний маршрут.'}],
        })
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn('Ждём прежний маршрут.', html)
        self.assertIn('<b>Нужен ли человек:</b> Пока неизвестно.', html)


class DashboardLayoutTests(unittest.TestCase):
    """The dashboard must stay readable: nothing may cover a block of it."""

    def _graph(self):
        return lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'goal': 'Довести поручение до результата.',
            'business_result': 'Участники принимают общий результат.',
            'tasks': [
                {'id': 'a', 'label': 'Готовая работа', 'status': 'done', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'b', 'label': 'Можно запускать', 'status': 'queued', 'depends_on': ['a'],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'c', 'label': 'Ждёт b', 'status': 'queued', 'depends_on': ['b'],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'd', 'label': 'Идёт сейчас', 'status': 'running', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'e', 'label': 'Ждёт внешнего хода', 'status': 'blocked', 'depends_on': [],
                 'blocker': 'Нужен доступ к стенду.',
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })

    def test_no_overlay_element_can_cover_a_block_of_the_dashboard(self):
        """A fixed or sticky opaque layer is what hid the KPI strip before.

        The dashboard paints its background on the canvas instead, so there is
        no element left that could cover the content while still occupying
        space.
        """

        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertNotIn('position: fixed', html)
        self.assertNotIn('body::before', html)
        self.assertNotIn('body::after', html)
        # The one sticky layer is the progress strip the owner asked for: it
        # sticks to the top of the window so the degree of the progress is
        # always in sight. Nothing else may stick, and an anchor jump must not
        # land a section under the strip.
        sticky = re.findall(r'([a-z-]+)\s*\{\s*position: sticky', html)
        self.assertEqual(sticky, ['progress-strip'])
        self.assertIn('scroll-margin-top', html)

    def test_kpi_strip_has_a_bounded_column_count(self):
        """An implicit auto-fit grid may silently collapse into one tall column."""

        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn(
            '.kpis { display: grid; gap: 10px; grid-template-columns: repeat(5, minmax(0, 1fr));',
            html,
        )
        for columns in ('repeat(5,', 'repeat(3,', 'repeat(2,'):
            self.assertIn(columns, html)

    def test_the_page_is_read_in_the_declared_order(self):
        """The progress, then the action, then what blocks, then the wording.

        The owner reads the page on a phone and named the order himself: the
        current progress has to be seen at once, then what to do now, then what
        blocks the work, and only then the wording of the plan.
        """
        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        markers = [
            'progress-strip',
            'class="kpis"',
            'Что делать сейчас',
            'Что блокирует',
            'Подтверждённый прогресс',
            'Гант · листья и параллельные волны',
            "table table-leaves",
        ]
        positions = [html.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_kpi_strip_carries_ten_metrics_with_a_big_number(self):
        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertEqual(html.count('class="kpi kpi-tile"'), 10)
        for label in ('Готово', 'В работе', 'Заблокировано', 'В очереди',
                      'Отложено владельцем', 'Осталось', 'Параллельность',
                      'Осталось по плану', 'Прогноз финиша', 'Усилие'):
            self.assertRegex(html, r'kpi-label"[^>]*>[^<]*' + re.escape(label))

    def test_status_is_never_carried_by_colour_alone(self):
        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        # every gantt row states its status in words, not only as a coloured bar
        self.assertEqual(html.count('class="gantt-status"'), len(graph.leaves))
        self.assertIn('class="legend"', html)
        self.assertIn('Готово', html)

    def test_now_panel_shows_running_ready_and_blocked_lines(self):
        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn('Что делать сейчас', html)
        self.assertIn('В работе', html)
        self.assertIn('Готовы к запуску', html)
        self.assertIn('Заблокированы', html)
        self.assertIn('Свободных слотов:', html)
        self.assertIn('Идёт сейчас', html)
        self.assertIn('Можно запускать', html)
        self.assertIn('Нужен доступ к стенду.', html)

    def test_now_panel_agrees_with_the_parallel_planner(self):
        graph = self._graph()
        plan = lhc.plan_now(graph)
        self.assertEqual(plan['slots'], 2)
        self.assertEqual(plan['free_slots'], 1)
        self.assertEqual([item['id'] for item in plan['running']], ['d'])
        self.assertEqual([item['id'] for item in plan['ready']], ['b'])
        self.assertEqual([item['id'] for item in plan['waiting']], ['c'])
        self.assertEqual([item['id'] for item in plan['blocked']], ['e'])

    def test_the_port_answers_exactly_like_the_planner_module(self):
        graph = self._graph()
        plan = lhc.plan_now(graph)
        port = lhc._plan_now_port(graph)
        for group in ('running', 'ready', 'deferred', 'blocked', 'waiting'):
            self.assertEqual(
                [item['id'] for item in plan[group]],
                [item['id'] for item in port[group]],
                group,
            )
        self.assertEqual(plan['free_slots'], port['free_slots'])

    def test_no_line_is_ready_when_every_slot_is_taken(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 1,
            'tasks': [
                {'id': 'busy', 'label': 'Занятый слот', 'status': 'running', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'next', 'label': 'Ждёт слот', 'status': 'queued', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })
        plan = lhc.plan_now(graph)
        self.assertEqual(plan['free_slots'], 0)
        self.assertEqual(plan['ready'], [])
        self.assertEqual([item['id'] for item in plan['deferred']], ['next'])

    def test_the_dashboard_is_one_self_contained_file(self):
        graph = self._graph()
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        head = html.split('</head>')[0]
        self.assertNotIn('http://', head)
        self.assertNotIn('https://', head)
        self.assertNotIn('//cdn', head)
        self.assertNotIn('<link', head)
        self.assertNotIn('<img', head)
        self.assertIn('<style>', html)
        self.assertIn('<script>', html)


class CanonicalContractTests(unittest.TestCase):
    """The renderer and the offline checker accept one contract: TASK_GRAPH.md."""

    @staticmethod
    def published_example():
        text = (ROOT / 'src/common/protocols/TASK_GRAPH.md').read_text(encoding='utf-8')
        return text.split('```json\n', 1)[1].split('\n```', 1)[0]

    def test_published_example_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / 'plan.graph.json'
            graph.write_text(self.published_example(), encoding='utf-8')
            result = run_validator(str(graph))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)['valid'])

    def test_exported_plan_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            plan = base / 'plan.md'
            plan.write_text(REPORT, encoding='utf-8')
            graph = base / 'plan.graph.json'
            exported = run_tool('export', str(plan), '-o', str(graph))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            result = run_validator(str(graph))
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)['valid'])

    def test_minimum_task_set_is_enough(self):
        document = {'schema_version': 2, 'tasks': [
            {'id': 'a', 'label': 'first', 'status': 'queued', 'depends_on': []},
        ]}
        result = validator.validate_graph(document)
        self.assertTrue(result['valid'], result['errors'])

    def test_canonical_required_fields_are_checked(self):
        for missing in ('label', 'status', 'depends_on'):
            task = {'id': 'a', 'label': 'first', 'status': 'queued', 'depends_on': []}
            task.pop(missing)
            result = validator.validate_graph({'schema_version': 2, 'tasks': [task]})
            self.assertFalse(result['valid'])
            self.assertIn(missing, ' '.join(result['errors']))

    def test_declared_paths_still_conflict(self):
        document = {'schema_version': 2, 'tasks': [
            {'id': 'a', 'label': 'a', 'status': 'queued', 'depends_on': [],
             'write_paths': ['src']},
            {'id': 'b', 'label': 'b', 'status': 'queued', 'depends_on': [],
             'read_paths': ['src/a']},
        ]}
        result = validator.validate_graph(document)
        self.assertFalse(result['valid'])
        self.assertIn('conflict', ' '.join(result['errors']))

    def test_model_class_is_checked_against_the_allowed_names(self):
        for name in ('glm-5.3-flash', 'minimax-3.1-flash', 'gpt-6-luna',
                     'glm-5.3', 'gpt-6.1-sol'):
            document = {'schema_version': 2, 'tasks': [
                {'id': 'a', 'label': 'a', 'status': 'queued', 'depends_on': [],
                 'model_class': name},
            ]}
            self.assertTrue(validator.validate_graph(document)['valid'], name)
        document = {'schema_version': 2, 'tasks': [
            {'id': 'a', 'label': 'a', 'status': 'queued', 'depends_on': [],
             'model_class': 'sonnet'},
        ]}
        self.assertFalse(validator.validate_graph(document)['valid'])

    def test_partial_estimates_do_not_fail(self):
        document = {'schema_version': 2, 'tasks': [
            {'id': 'a', 'label': 'a', 'status': 'done', 'depends_on': [],
             'estimate_minutes': {'minimum': 5, 'maximum': 10}},
            {'id': 'b', 'label': 'b', 'status': 'queued', 'depends_on': ['a']},
        ]}
        result = validator.validate_graph(document)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['estimate']['effort_minutes'], {'minimum': 5, 'maximum': 10})

    def test_declared_optional_fields_are_checked_when_present(self):
        document = {'schema_version': 2, 'tasks': [
            {'id': 'a', 'label': 'a', 'status': 'queued', 'depends_on': [],
             'acceptance': '   ',
             'blocker_details': {'human_required': 'maybe'}},
        ]}
        result = validator.validate_graph(document)
        self.assertFalse(result['valid'])
        joined = ' '.join(result['errors'])
        self.assertIn('acceptance', joined)
        self.assertIn('human_required', joined)


class PlanReconciliationTests(unittest.TestCase):
    """The report's tasks and the graph's leaves are one set."""

    def test_matching_report_and_graph_reconcile(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [
                {'id': 'L01', 'label': 'контракт источника', 'status': 'done', 'depends_on': []},
                {'id': 'L02', 'label': 'сборка и push', 'status': 'queued', 'depends_on': ['L01']},
            ],
        })
        report = lhc.parse_plan_report(
            'Цель: собрать\n'
            'Декомпозиция: 2 листа · 1 параллельно · 1 волны · слотов: 1\n'
            '\n'
            '✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут\n'
            '⏳ (сборка и push) начнём после листа 1, оценка 10 минут\n'
        )
        result = lhc.compare_plan_with_graph(report, graph)
        self.assertTrue(result.ok, result.extra_in_report or result.missing_in_report)
        self.assertEqual(len(result.matched), 2)

    def test_divergence_is_reported(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'tasks': [
                {'id': 'L01', 'label': 'контракт источника', 'status': 'done', 'depends_on': []},
                {'id': 'L09', 'label': 'лишний лист', 'status': 'queued', 'depends_on': []},
            ],
        })
        report = lhc.parse_plan_report(
            'Цель: собрать\n'
            'Декомпозиция: 2 листа · 1 параллельно · 1 волны · слотов: 1\n'
            '\n'
            '⏳ (контракт источника) начнём после листа 1, оценка 15 минут\n'
            '⏳ (сборка и push) начнём после листа 1, оценка 10 минут\n'
        )
        result = lhc.compare_plan_with_graph(report, graph)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.extra_in_report), 1)
        self.assertEqual(len(result.missing_in_report), 1)
        self.assertEqual(len(result.status_mismatch), 1)


class HonestLeafStatesTests(unittest.TestCase):
    """A leaf that waits and a leaf the owner deferred are two different things.

    The second one is not expected to move at all: no answer is waited for, it
    takes no slot, it is not a blocker and it is not part of the remainder of
    the delivery.
    """

    REPORT = (
        'Цель: довести интеграцию до результата\n'
        'Бизнес-результат: карточка принимается\n'
        'Декомпозиция: 4 листа · 2 параллельно · 2 волны · слотов: 2\n'
        '\n'
        '✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут\n'
        '⌛ (ответ поставщика) ждём ответа поставщика, оценка 20 минут\n'
        '⏸ (правка объявления) владелец отложил лист, оценка 30 минут\n'
        '⛔ (доступ к стенду) начата 14:05, оценка 20 минут, блокер: нет ключа\n'
    )

    def _report_graph(self):
        graph = lhc.parse_plan_report(self.REPORT)
        self.assertIsNotNone(graph)
        return graph

    def test_the_waiting_and_the_deferred_markers_are_read_as_their_states(self):
        graph = self._report_graph()
        self.assertEqual(
            [leaf.status for leaf in graph.leaves],
            ['done', 'waiting', 'deferred', 'blocked'],
        )

    def test_the_deferred_state_is_named_for_the_owner(self):
        self.assertEqual(lhc.STATUS_LABELS[lhc.STATUS_DEFERRED], 'Отложено владельцем')
        self.assertEqual(lhc.STATUS_GLYPHS[lhc.STATUS_DEFERRED], '⏸')
        self.assertEqual(lhc.STATUS_GLYPHS[lhc.STATUS_WAITING], '⌛')
        for alias in ('deferred', 'отложено', 'отложен', 'отложено владельцем'):
            self.assertEqual(lhc.normalize_status(alias), 'deferred', alias)

    def test_the_report_and_a_graph_with_the_same_states_reconcile(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            report = base / 'plan.report.md'
            report.write_text(self.REPORT, encoding='utf-8')
            graph = base / 'plan.graph.json'
            graph.write_text(json.dumps({
                'schema_version': 2,
                'slots': 2,
                'tasks': [
                    {'id': 'L01', 'label': 'контракт источника', 'status': 'done', 'depends_on': []},
                    {'id': 'L02', 'label': 'ответ поставщика', 'status': 'waiting', 'depends_on': []},
                    {'id': 'L03', 'label': 'правка объявления', 'status': 'deferred', 'depends_on': []},
                    {'id': 'L04', 'label': 'доступ к стенду', 'status': 'blocked',
                     'depends_on': [], 'blocker': 'нет ключа'},
                ],
            }, ensure_ascii=False), encoding='utf-8')
            checked = run_tool('check-plan', str(report), str(graph))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn('OK:', checked.stdout)

    def test_a_deferred_leaf_is_outside_the_remainder(self):
        """It takes no time, no slot and no place on the critical path."""

        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'tasks': [
                {'id': 'L01', 'label': 'готовая работа', 'status': 'done', 'depends_on': [],
                 'estimate_minutes': {'minimum': 10, 'maximum': 10}},
                {'id': 'L02', 'label': 'работа в очереди', 'status': 'queued', 'depends_on': [],
                 'estimate_minutes': {'minimum': 20, 'maximum': 20}},
                {'id': 'L03', 'label': 'отложено надолго', 'status': 'deferred', 'depends_on': [],
                 'estimate_minutes': {'minimum': 999, 'maximum': 999}},
                {'id': 'L04', 'label': 'отложено без оценки', 'status': 'deferred', 'depends_on': []},
            ],
        })
        metrics = lhc.build_metrics(graph)

        self.assertEqual(metrics['unfinished'], 1)
        self.assertEqual(metrics['remaining_minutes_min'], 20)
        self.assertEqual(metrics['remaining_minutes_max'], 20)
        self.assertNotIn('L03', metrics['critical_path'])
        self.assertNotIn('L04', metrics['critical_path'])
        # A deferred leaf without an estimate must not make the horizon unknown.
        self.assertEqual(metrics['unknown_estimate_pending'], 0)
        self.assertNotEqual(metrics['eta_clock_max'], '')

    def test_a_deferred_leaf_takes_no_slot_and_waits_for_nothing(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 1,
            'tasks': [
                {'id': 'L01', 'label': 'отложено владельцем', 'status': 'deferred', 'depends_on': []},
                {'id': 'L02', 'label': 'первая работа', 'status': 'queued', 'depends_on': []},
                {'id': 'L03', 'label': 'вторая работа', 'status': 'queued', 'depends_on': []},
            ],
        })
        plan = lhc.plan_now(graph)
        self.assertEqual([item['id'] for item in plan['ready']], ['L02'])
        self.assertEqual([item['id'] for item in plan['deferred']], ['L03'])
        self.assertEqual(plan['blocked'], [])
        self.assertEqual(plan['waiting'], [])

    def test_the_port_agrees_with_the_planner_about_a_deferred_leaf(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 1,
            'tasks': [
                {'id': 'L01', 'label': 'отложено владельцем', 'status': 'deferred', 'depends_on': []},
                {'id': 'L02', 'label': 'первая работа', 'status': 'queued', 'depends_on': []},
                {'id': 'L03', 'label': 'вторая работа', 'status': 'queued', 'depends_on': []},
            ],
        })
        plan = lhc.plan_now(graph)
        port = lhc._plan_now_port(graph)
        for group in ('running', 'ready', 'deferred', 'blocked', 'waiting'):
            self.assertEqual(
                [item['id'] for item in plan[group]],
                [item['id'] for item in port[group]],
                group,
            )
        self.assertEqual(plan['free_slots'], port['free_slots'])

    def test_only_a_blocked_leaf_is_counted_as_blocked(self):
        """One rule: the status says it, the text does not."""

        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'tasks': [
                {'id': 'L01', 'label': 'ждёт ответа', 'status': 'queued', 'depends_on': [],
                 'blocker': 'источник не ответил',
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'L02', 'label': 'настоящий блокер', 'status': 'blocked', 'depends_on': [],
                 'blocker': 'нет ключа',
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })
        metrics = lhc.build_metrics(graph)
        plan = lhc.plan_now(graph)
        html = lhc.render_html(graph, metrics)

        self.assertEqual(metrics['blocked'], 1)
        self.assertEqual([item['id'] for item in plan['blocked']], ['L02'])
        self.assertEqual(html.count('class="blocker"'), 1)
        self.assertEqual(self._kpi_value(html, 'Заблокировано'), '1')
        self.assertIn('Заблокированы', html)

    def test_the_blocker_text_is_printed_only_for_a_blocked_leaf(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'tasks': [
                {'id': 'L01', 'label': 'ждёт ответа', 'status': 'queued', 'depends_on': [],
                 'blocker': 'источник не ответил',
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })
        metrics = lhc.build_metrics(graph)
        self.assertNotIn('блокер:', lhc.render_html(graph, metrics))
        self.assertNotIn('блокер:', lhc.render_text(graph, metrics))

    def test_the_kpi_strip_carries_the_deferred_state(self):
        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 2,
            'tasks': [
                {'id': 'L01', 'label': 'отложено владельцем', 'status': 'deferred', 'depends_on': []},
            ],
        })
        metrics = lhc.build_metrics(graph)
        html = lhc.render_html(graph, metrics)
        self.assertEqual(self._kpi_value(html, 'Отложено владельцем'), '1')
        # The remainder says how many leaves are outside of it.
        hint = self._kpi_hint(html, 'Осталось')
        self.assertIn('1', hint)
        self.assertIn('отложено владельцем', hint)

    def test_the_load_group_is_not_called_deferred(self):
        """The group of the lines that wait for a free slot has its own name."""

        graph = lhc.parse_graph_json({
            'schema_version': 2,
            'slots': 1,
            'tasks': [
                {'id': 'L01', 'label': 'первая работа', 'status': 'queued', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
                {'id': 'L02', 'label': 'вторая работа', 'status': 'queued', 'depends_on': [],
                 'estimate_minutes': {'minimum': 5, 'maximum': 5}},
            ],
        })
        html = lhc.render_html(graph, lhc.build_metrics(graph))
        self.assertIn('Ждут свободного слота', html)
        self.assertNotIn('Отложено — свободных слотов нет', html)

    @staticmethod
    def _kpi_value(html, label):
        match = re.search(
            r'<div class="kpi-label"[^>]*>[^<]*' + re.escape(label) +
            r'</div>\s*<div class="kpi-value">([^<]*)</div>',
            html,
        )
        return match.group(1) if match else None

    @staticmethod
    def _kpi_hint(html, label):
        match = re.search(
            r'<div class="kpi-label"[^>]*>[^<]*' + re.escape(label) +
            r'</div>\s*<div class="kpi-value">[^<]*</div>\s*<div class="kpi-hint">([^<]*)</div>',
            html,
        )
        return match.group(1) if match else None


class UnrecognizedReportTests(unittest.TestCase):
    """An unread report is an error, never an empty dashboard."""

    @pytest.mark.nightly
    def test_commands_fail_with_a_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            plan = base / 'plan.md'
            plan.write_text('просто текст без структуры отчёта\n', encoding='utf-8')
            for command in ('render', 'status', 'export'):
                args = [command, str(plan)]
                if command == 'export':
                    args += ['-o', str(base / 'graph.json')]
                elif command == 'render':
                    args += ['-o', str(base / 'plan.html')]
                result = run_tool(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn('отчёт не распознан', result.stderr)
                self.assertIn('Цель:', result.stderr)
            self.assertFalse((base / 'graph.json').exists())
            self.assertFalse((base / 'plan.html').exists())


class CommandTests(unittest.TestCase):
    def _run(self, *args):
        return run_tool(*args)

    @pytest.mark.nightly
    def test_render_status_export_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            plan = base / 'plan.md'
            plan.write_text(REPORT, encoding='utf-8')
            out = base / 'plan.html'
            result = self._run('render', str(plan), '-o', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertIn('Готово', out.read_text(encoding='utf-8'))

            summary = self._run('status', str(plan))
            self.assertEqual(summary.returncode, 0, summary.stderr)
            self.assertIn('Прогресс', summary.stdout)

            graph_path = base / 'plan.graph.json'
            exported = self._run('export', str(plan), '-o', str(graph_path))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            document = json.loads(graph_path.read_text(encoding='utf-8'))
            self.assertEqual(document['schema_version'], 2)
            self.assertEqual(len(document['tasks']), 4)

            checked = self._run('validate', str(graph_path))
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)['valid'])

    def test_missing_input_fails_cleanly(self):
        result = self._run('status', '/a/nonexistent/plan.md')
        self.assertEqual(result.returncode, 2)
        self.assertIn('lhc_grid', result.stderr)

    @pytest.mark.nightly
    def test_check_plan_accepts_matching_files_and_reports_divergence(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            report = base / 'plan.report.md'
            report.write_text(REPORT, encoding='utf-8')
            graph = base / 'plan.graph.json'
            exported = self._run('export', str(report), '-o', str(graph))
            self.assertEqual(exported.returncode, 0, exported.stderr)

            matching = self._run('check-plan', str(report), str(graph))
            self.assertEqual(matching.returncode, 0, matching.stdout + matching.stderr)
            self.assertIn('OK:', matching.stdout)

            document = json.loads(graph.read_text(encoding='utf-8'))
            document['tasks'].append({
                'id': 'L05', 'label': 'лишний лист', 'status': 'queued', 'depends_on': [],
            })
            graph.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
            diverging = self._run('check-plan', str(report), str(graph))
            self.assertEqual(diverging.returncode, 1, diverging.stdout + diverging.stderr)
            self.assertIn('РАСХОЖДЕНИЕ', diverging.stdout)


if __name__ == '__main__':
    unittest.main()
