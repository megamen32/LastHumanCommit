"""Contracts shared by standalone, publisher and derived mirror artifacts."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_grid as grid
import lhc_plan_json as leaves
import lhc_plan_publish as pub
import lhc_plan_mirror as mirror


def document():
    return {'schema_version': 2, 'title': 'План владельца', 'goal': 'Найти срок',
            'business_result': 'Владелец увидит срок и сравнит ревизии',
            'current_progress': 'Исходники изменены; приёмка ещё не проведена',
            'acceptance_scenarios': ['Владелец открывает план и видит срок на первом экране'],
            'slots': 2, 'tasks': [{'id': 'A', 'label': 'Работа', 'status': 'queued',
                                     'estimate_minutes': 10}]}


def test_standalone_default_order_and_sections():
    graph = grid.parse_graph_json(document())
    page = grid.render_html(graph, grid.build_metrics(graph))
    assert page.index('<header>') < page.index('class="revision-strip"') < page.index('id="dashboard"')
    assert page.index('id="lhc-progress-strip"') < page.index('id="lhc-state"') < page.index('id="outcome"')
    assert 'Прогресс задач не означает приёмку' in page[page.index('id="dashboard"'):page.index('id="outcome"')]
    for section in ('dashboard', 'outcome', 'work-plan', 'comparison', 'tasks', 'history'):
        assert f'href="#{section}"' in page
        assert f'id="{section}" class="plan-section"' in page
    assert 'Что будет работать' in page and 'Как проверим' in page
    assert 'Владелец открывает план и видит срок' in page
    assert 'Статус задач сам по себе не подтверждает приёмку' in page
    assert '.plan-section[hidden]{display:block!important}' in page
    assert 'lhc-before-swap' in page and 'ArrowRight' in page
    assert grid.export_graph(graph)['acceptance_scenarios'] == document()['acceptance_scenarios']


def test_optional_scenarios_roundtrip_and_validation(tmp_path):
    (tmp_path / 'leaves').mkdir()
    metadata = {k: v for k, v in document().items() if k not in ('schema_version', 'tasks')}
    (tmp_path / 'plan.json').write_text(json.dumps(metadata))
    (tmp_path / 'leaves/A.json').write_text(json.dumps(document()['tasks'][0]))
    collected = leaves.build_document(tmp_path)
    assert collected['acceptance_scenarios'] == document()['acceptance_scenarios']
    assert pub.public_document(collected)['acceptance_scenarios'] == document()['acceptance_scenarios']
    old = document(); old.pop('acceptance_scenarios')
    graph = grid.parse_graph_json(old)
    assert 'Сценарии проверки ещё не описаны' in grid.render_html(graph, grid.build_metrics(graph))
    (tmp_path / 'plan.json').write_text(json.dumps(dict(metadata, acceptance_scenarios='нет')))
    with pytest.raises(leaves.LeafError, match='acceptance_scenarios'):
        leaves.build_document(tmp_path)


def test_publication_keeps_comparison_out_of_first_view_and_revisions_static():
    doc = document()
    revisions = [{'id': 'r001', 'document': doc, 'reason': 'Начало', 'created_at': '2026-10-25T10:00:00Z'}]
    page = pub.page(doc, doc, doc, revisions, 'r001', revisions[0]['created_at'], True, 'version')
    assert page.index('id="dashboard"') < page.index('id="plan-comparison"')
    assert page.index('id="history"') < page.index('id="publication"')
    assert '<a href="./" aria-current="page">Текущий план</a>' in page
    assert '<a href="r001.html"' in page
    assert '<a href="view-r001.html"' in page
    frozen = pub.page(doc, doc, doc, revisions, 'r001', revisions[0]['created_at'], False)
    assert 'id="lhc-publication-live"' not in frozen
    assert 'id="lhc-live"' not in frozen


def test_future_intent_changes_need_revision_but_progress_does_not():
    doc = document()
    for key, value in [('business_result', 'Другая возможность'), ('business_results', ['Возможность']),
                       ('acceptance_scenarios', ['Другой сценарий'])]:
        assert pub.planning_facts(dict(doc, **{key: value})) != pub.planning_facts(doc)
    assert pub.planning_facts(dict(doc, current_progress='Другой факт')) == pub.planning_facts(doc)
    old = dict(doc); old.pop('acceptance_scenarios')
    assert pub.planning_facts(old) == pub.planning_facts(dict(old, acceptance_scenarios=[]))


def test_new_report_heading_and_scenarios_preserve_legacy_reports():
    doc = document()
    doc['tasks'][0]['id'] = 'L01'
    doc['tasks'] = [leaves.task_from_leaf(task, Path(task['id'] + '.json')) for task in doc['tasks']]
    report = leaves.report_block_of(doc)
    graph = grid.parse_plan_report(report.replace('Бизнес-результат:', 'Что будет работать:'))
    assert graph.business_result == document()['business_result']
    assert graph.acceptance_scenarios == document()['acceptance_scenarios']
    assert grid.export_graph(graph)['acceptance_scenarios'] == document()['acceptance_scenarios']
    assert grid.parse_plan_report(report).business_result == document()['business_result']


def test_completed_plan_does_not_forecast_an_unstarted_remainder():
    doc = document(); doc['tasks'][0]['status'] = 'done'
    graph = grid.parse_graph_json(doc)
    page = grid.render_html(graph, grid.build_metrics(graph))
    assert 'Работы по плану завершены' in page
    assert 'Фактический финиш не зафиксирован' in page
    assert 'остаток стартует сейчас' not in page
    assert page.index('data-tile="remaining"') < page.index('data-tile="forecast"') < page.index('data-tile="parallel"')
    assert page.index('data-tile="parallel"') < page.index('<summary>Статусы задач и усилие')


def test_historical_view_has_all_tabs_but_only_selected_revision_facts():
    import copy
    first = document(); later = copy.deepcopy(first)
    later['tasks'][0]['estimate_minutes'] = 999
    later['tasks'].append({'id': 'B', 'label': 'FUTURE_TASK_MUST_NOT_LEAK', 'status': 'done', 'estimate_minutes': 999, 'actual_minutes': 888})
    revisions = [{'id': 'r001', 'document': first, 'reason': 'Начало', 'created_at': '2026-10-25T10:00:00Z'},
                 {'id': 'r002', 'document': later, 'reason': 'Вторая ревизия', 'created_at': '2026-10-25T11:00:00Z',
                  'observed': {'B': {'task': later['tasks'][-1], 'completed': []}}}]
    frozen = pub.page(first, first, first, revisions, 'r001', revisions[0]['created_at'], False)
    expected_comparison = pub.comparison(first, first, first, revisions[:1], revisions[0]['created_at'])
    assert expected_comparison in frozen
    assert 'href="view-r001.html" aria-current="page"' in frozen
    assert 'href="view-r002.html"' in frozen
    assert 'class="plan-sidebar"' in frozen
    assert 'FUTURE_TASK_MUST_NOT_LEAK' not in frozen
    assert 'Есть изменения плана без новой ревизии' not in frozen


def test_renderer_only_update_preserves_receipt_sequence_and_archive(tmp_path):
    cfg = {'data_dir': str(tmp_path / 'data'), 'webroot': str(tmp_path / 'web'), 'base_url': 'https://example.test'}
    replica = mirror.Replica(cfg)
    entry = {'snapshot': {'identity': 'abc', 'project': 'project', 'name': 'plan',
                         'document': document(), 'observed': {}, 'last_file_event': '2026-10-25T10:00:00Z',
                         'revisions': [{'id': 'r001', 'document': document(), 'observed': {}, 'reason': 'Начало', 'created_at': '2026-10-25T10:00:00Z'}]},
             'receipt': {'seq': 7, 'received_at': '2026-10-25T10:00:01Z'}}
    replica.render(entry)
    target = Path(cfg['webroot']) / 'project/plan'
    # Historical output can predate this UI and carry CRLF: preserve its bytes.
    archive = b'<!doctype html>\r\n<p>original immutable archive</p>\r\n'
    (target / 'r001.html').write_bytes(archive)
    original = json.loads((target / 'version.json').read_text())
    replica.renderer = 'new presentation only'
    replica.render(entry)
    updated = json.loads((target / 'version.json').read_text())
    assert updated['version'] != original['version']
    assert updated['server_receipt'] == original['server_receipt'] == entry['receipt']
    assert (target / 'r001.html').read_bytes() == archive
    derived = (target / 'view-r001.html').read_text()
    assert 'class="plan-sidebar"' in derived
    assert '<a href="view-r001.html" aria-current="page"' in derived
    assert 'id="lhc-publication-live"' not in derived
    assert 'id="lhc-live"' not in derived
