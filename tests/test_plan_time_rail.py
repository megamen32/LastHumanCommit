"""Time is separate from task percentage; source-rendered proof, not deployment acceptance."""
import json
import os
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_grid as grid
import lhc_plan_json as collector
import lhc_plan_publish as pub
from test_plan_dashboard_browser import browser


def document(**fields):
    doc = {'schema_version': 2, 'updated_at': '2026-10-25T23:55:00+03:00',
           'tasks': [{'id': 'L01', 'label': 'Работа', 'status': 'running',
                      'estimate_minutes': 20, 'started_at': '2026-10-25T23:45:00+03:00'}]}
    doc.update(fields)
    return doc


def frame(doc):
    graph = grid.parse_graph_json(doc)
    graph.snapshot_at = '2026-10-26T00:05:00+03:00'
    return grid.build_metrics(graph)['time_frame']


def test_exact_start_precedence_and_deferred_history():
    doc = document(started_at='2026-10-25T23:40:00+03:00')
    assert frame(doc)['start'] == doc['started_at']
    del doc['started_at']
    doc['tasks'].append({'id': 'L00', 'label': 'Ранняя работа', 'status': 'deferred',
                         'started_at': '2026-10-25T23:30:00+03:00'})
    assert frame(doc)['start'] == doc['tasks'][1]['started_at']


def test_unknown_and_legacy_never_use_planned_start():
    doc = document(planned_start_at='2026-10-25T22:00:00+03:00')
    doc['tasks'][0].pop('started_at')
    assert frame(doc)['start'] == ''
    doc['tasks'][0]['started_at'] = '23:45'
    f = frame(doc)
    assert f['start'] == '' and f['legacy_start'] == '23:45'
    page = grid.render_html(grid.parse_graph_json(doc), grid.build_metrics(grid.parse_graph_json(doc)))
    assert 'дата не записана' in page


def test_forecast_is_fixed_full_datetime_across_midnight_and_timezones():
    graph = grid.parse_graph_json(document())
    graph.snapshot_at = '2026-10-26T00:05:00+03:00'
    first = grid.build_metrics(graph)
    graph.snapshot_at = '2026-10-26T01:05:00+03:00'
    later = grid.build_metrics(graph)
    assert first['time_frame']['end'] == later['time_frame']['end'] == '2026-10-26T00:15:00+03:00'
    assert later['eta_overdue']
    graph.updated_at = '2026-10-25T21:00:00Z'
    assert grid.build_metrics(graph)['time_frame']['end'] == '2026-10-25T21:20:00+00:00'


@pytest.mark.parametrize('start', ['2026-10-27T00:00:00Z', 'invalid'])
def test_bad_or_future_start_does_not_make_proportional_marker(start):
    assert frame(document(started_at=start))['start'] == ''


@pytest.mark.parametrize('status', ['blocked', 'waiting'])
def test_external_wait_has_no_finish(status):
    doc = document()
    doc['tasks'][0]['status'] = status
    f = frame(doc)
    assert not f['end'] and 'ожидания' in f['end_label']


def test_unknown_estimate_has_no_false_full_finish():
    doc = document()
    del doc['tasks'][0]['estimate_minutes']
    assert not frame(doc)['end'] and 'частичный' in frame(doc)['end_label']


def test_completed_requires_trustworthy_finish():
    doc = document()
    doc['tasks'][0]['status'] = 'done'
    assert frame(doc)['completed'] and frame(doc)['end'] == ''
    doc['tasks'][0]['finished_at'] = '2026-10-26T00:00:00+03:00'
    assert frame(doc)['end'] == doc['tasks'][0]['finished_at']
    doc['tasks'][0]['finished_at'] = '2026-10-25T23:00:00+03:00'
    assert frame(doc)['end'] == ''


def test_collector_and_public_projection_keep_optional_actual_times(tmp_path):
    (tmp_path / 'leaves').mkdir()
    (tmp_path / 'leaves/L01.json').write_text(json.dumps(document()['tasks'][0]))
    metadata = {'title': 'План', 'started_at': '2026-10-25T23:40:00+03:00',
                'finished_at': '2026-10-26T00:15:00+03:00'}
    (tmp_path / 'plan.json').write_text(json.dumps(metadata))
    built = collector.build_document(tmp_path)
    assert built['started_at'] == metadata['started_at']
    assert pub.public_document(built)['finished_at'] == metadata['finished_at']
    metadata['started_at'] = 'yesterday'
    (tmp_path / 'plan.json').write_text(json.dumps(metadata))
    with pytest.raises(collector.LeafError):
        collector.build_document(tmp_path)


def test_collector_chooses_latest_absolute_event_and_export_preserves_it(tmp_path):
    (tmp_path / 'leaves').mkdir()
    task = document()['tasks'][0]
    task['updated_at'] = '2026-10-26T00:10:00+03:00'
    (tmp_path / 'leaves/L01.json').write_text(json.dumps(task))
    (tmp_path / 'plan.json').write_text(json.dumps({'updated_at': '2026-10-25T21:15:00Z'}))
    doc = collector.build_document(tmp_path)
    assert doc['updated_at'] == '2026-10-25T21:15:00Z'
    assert grid.export_graph(grid.parse_graph_json(doc))['updated_at'] == doc['updated_at']


@pytest.mark.skipif(os.environ.get('LHC_UI_BROWSER_TESTS') != '1', reason='opt-in isolated Chrome')
def test_browser_clock_marker_widths_and_archived_snapshot(browser, tmp_path):
    call, js, url = browser
    doc = document()
    doc['updated_at'] = '2026-10-25T16:55:00Z'
    doc['tasks'][0]['started_at'] = '2026-10-25T16:45:00Z'
    revs = [{'id': 'r001', 'reason': 'Начало', 'document': doc,
             'created_at': '2026-10-25T16:55:00Z'}]
    page = tmp_path / 'plan.html'
    page.write_text(pub.page(doc, doc, doc, revs, 'r001', revs[0]['created_at'], True))
    call('Page.enable')
    call('Page.addScriptToEvaluateOnNewDocument', {'source': '''
      window.testNow=Date.parse('2026-10-25T16:55:00Z');Date.now=()=>window.testNow;
      const realInterval=window.setInterval;window.clockTicks=[];
      window.setInterval=(fn,ms)=>{if(ms===15000)window.clockTicks.push(fn);return realInterval(fn,ms)};
    '''})
    call('Emulation.setTimezoneOverride', {'timezoneId': 'Europe/Berlin'})
    call('Page.navigate', {'url': url})
    for _ in range(100):
        if js('!!document.querySelector(".time-rail-marker") && !!window.__lhcUI'):
            break
        time.sleep(.03)
    assert 'Начало: 25.10.2026, 17:45' in js('document.querySelector(".time-rail-start").textContent')
    assert 'Europe/Berlin' in js('document.querySelector(".time-rail-note").textContent')
    end = js('document.querySelector(".time-rail-end").textContent')
    position = js('document.querySelector(".time-rail-dot").style.left')
    percent = js('document.querySelector(".progress-strip-percent").textContent')
    js('window.testNow+=5*60000;window.clockTicks.forEach(fn=>fn())')
    assert js('document.querySelector(".time-rail-dot").style.left') != position
    assert js('document.querySelector(".time-rail-end").textContent') == end
    assert js('document.querySelector(".progress-strip-percent").textContent') == percent
    js('window.testNow+=60*60000;window.clockTicks.forEach(fn=>fn())')
    assert 'срок прошёл' in js('document.querySelector(".time-rail-clock").textContent')
    for width in (320, 390, 1440):
        call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 900, 'deviceScaleFactor': 1, 'mobile': width < 650})
        js('window.dispatchEvent(new Event("resize"))')
        assert js('''(()=>{const r=document.querySelector('.time-rail').getBoundingClientRect();
          return ['.time-rail-start','.time-rail-end','.time-rail-marker','.time-rail-dot'].every(s=>{
            const b=document.querySelector(s).getBoundingClientRect();return b.left>=r.left-1&&b.right<=r.right+1&&b.width>0})})()''')
    page.write_text(pub.page(doc, doc, doc, revs, 'r001', revs[0]['created_at'], False))
    call('Page.navigate', {'url': url + '?snapshot'})
    for _ in range(100):
        if js('!!window.__lhcUI && document.querySelector(".time-rail-clock")?.textContent.startsWith("На момент снимка")'):
            break
        time.sleep(.03)
    frozen = js('document.querySelector(".time-rail-clock").textContent')
    js('window.testNow+=3600000;window.clockTicks.forEach(fn=>fn())')
    assert js('document.querySelector(".time-rail-clock").textContent') == frozen
    # A downloaded current page is a labelled snapshot even if its source was live.
    page.write_text(pub.page(doc, doc, doc, revs, 'r001', revs[0]['created_at'], True))
    call('Page.navigate', {'url': page.as_uri()})
    for _ in range(100):
        if js('location.protocol==="file:" && !!window.__lhcUI && document.querySelector(".time-rail-clock")?.textContent.startsWith("На момент снимка")'):
            break
        time.sleep(.03)
    frozen = js('document.querySelector(".time-rail-clock").textContent')
    js('window.testNow+=3600000;window.clockTicks.forEach(fn=>fn())')
    assert js('document.querySelector(".time-rail-clock").textContent') == frozen
