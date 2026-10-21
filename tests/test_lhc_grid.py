"""Tests for the LHC task-graph renderer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'src' / 'common' / 'tools' / 'lhc_grid.py'


def load_tool():
    spec = importlib.util.spec_from_file_location('lhc_grid', TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lhc = load_tool()


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
        for needle in ('Готово', 'Гант', 'Блокеры', 'Прогноз', 'Критический путь', 'L01'):
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
        self.assertNotIn('position: sticky; top: 0;', html)
        self.assertLess(html.index('Цель'), html.index('class="progress"'))

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
        self.assertIn("detailsHost.scrollIntoView({ block: 'nearest' });", html)
        self.assertNotIn('<th>ID</th>', html)
        self.assertIn('.gantt-row { display: grid; grid-template-columns: minmax(240px, 320px) minmax(360px, 1fr);', html)
        self.assertIn('.table-leaves { min-width: 920px; width: 100%; table-layout: fixed; }', html)
        self.assertIn('.table-leaves th:nth-child(5) { width: 120px; }', html)
        self.assertIn('.task-details-host { position: static; width: 100%; margin-top: 12px; }', html)
        self.assertIn('.task-details { display: grid; grid-template-columns: minmax(110px, auto) minmax(0, 1fr);', html)
        self.assertIn('.task-details dd { margin: 0; min-width: 0; width: 100%; overflow-wrap: anywhere; word-break: break-word; }', html)
        self.assertIn('.status { color: var(--c); font-weight: 600; white-space: nowrap; }', html)


class CommandTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *args], capture_output=True, text=True,
        )

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


if __name__ == '__main__':
    unittest.main()
