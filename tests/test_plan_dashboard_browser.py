"""Opt-in Chrome checks of source-rendered offline plans, without shared profiles.

Run: LHC_UI_BROWSER_TESTS=1 python3 -m pytest -q tests/test_plan_dashboard_browser.py
Installed/public consumer acceptance remains a separate Lead check.
"""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import threading
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_grid as grid

pytestmark = pytest.mark.skipif(os.environ.get('LHC_UI_BROWSER_TESTS') != '1', reason='opt-in isolated Chrome')


@pytest.fixture
def browser(tmp_path):
    websocket = pytest.importorskip('websocket')
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome unavailable')
    profile = tmp_path / 'chrome'
    process = subprocess.Popen([chrome, '--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
                                '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
                                '--user-data-dir=' + str(profile), 'about:blank'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    socket = None
    try:
        for _ in range(100):
            if (profile / 'DevToolsActivePort').exists():
                break
            if process.poll() is not None:
                pytest.fail('isolated Chrome exited')
            time.sleep(.05)
        port = (profile / 'DevToolsActivePort').read_text().splitlines()[0]
        request = urllib.request.Request('http://127.0.0.1:' + port + '/json/new?about:blank', method='PUT')
        with urllib.request.urlopen(request) as response:
            target = json.load(response)
        socket = websocket.create_connection(target['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
        serial = 0

        def call(method, params=None):
            nonlocal serial
            serial += 1
            socket.send(json.dumps({'id': serial, 'method': method, 'params': params or {}}))
            while True:
                answer = json.loads(socket.recv())
                if answer.get('id') == serial:
                    assert 'error' not in answer, answer
                    return answer.get('result', {})

        def evaluate(expression):
            result = call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
            assert 'exceptionDetails' not in result, result
            return result.get('result', {}).get('value')

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(tmp_path), **kwargs)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield call, evaluate, 'http://127.0.0.1:' + str(server.server_port) + '/plan.html'
        finally:
            server.shutdown(); server.server_close()
    finally:
        if socket:
            socket.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()


def test_navigation_filters_refresh_mobile_print_and_task_details(browser, tmp_path):
    call, js, url = browser
    doc = {'schema_version': 2, 'title': 'План с длинным названием ' * 4, 'slots': 3,
           'goal': 'Цель ' * 300, 'business_result': 'Владелец сможет проверить план',
           'acceptance_scenarios': ['Открыть план и найти срок'],
           'tasks': [{'id': f'L{i:03}', 'label': f'Работа {i} ' + 'длиннаязаметка' * 10,
                      'status': 'running' if i == 1 else 'queued', 'estimate_minutes': 10,
                      'note': 'Примечание ' * 100} for i in range(110)]}
    graph = grid.parse_graph_json(doc)
    page = tmp_path / 'plan.html'
    page.write_text(grid.render_html(graph, grid.build_metrics(graph)))
    call('Page.enable')
    navigation = call('Page.navigate', {'url': url})
    assert 'errorText' not in navigation, navigation
    for _ in range(100):
        if js('!!document.getElementById("plan-app") && !!window.__lhcUI'):
            break
        time.sleep(.05)
    assert js('document.querySelector(".plan-sidebar [aria-current]")?.hash') == '#dashboard', js('({url:location.href,text:document.body.innerText.slice(0,300),sections:[...document.querySelectorAll(".plan-section")].map(s=>s.id),ready:document.readyState,app:!!window.__lhcUI})')
    assert js('document.getElementById("lhc-state").getBoundingClientRect().top < 500')
    assert js('[...document.querySelectorAll(".plan-section")].filter(s=>!s.hidden).length') == 1
    js('document.querySelector("a[href$=outcome]").click()')
    assert js('!document.getElementById("outcome").hidden')
    assert js('document.querySelector(".brief-goal details")!==null')
    js('document.querySelector("a[href$=tasks]").click(); const s=document.getElementById("search"); s.value="L001"; s.dispatchEvent(new Event("input")); document.querySelector("[data-filter=running]").click()')
    assert js('[...document.querySelectorAll(".table-leaves tbody tr")].filter(r=>r.style.display!=="none").length') == 1
    js('document.querySelector(".table-leaves tbody tr:not([style*=none]) .task-details-trigger").click()')
    assert js('!!document.querySelector(".task-details-row")')
    js('window.dispatchEvent(new Event("lhc-before-swap"))')
    call('Page.reload')
    for _ in range(100):
        if js('!!document.getElementById("search") && document.getElementById("search").value==="L001"'):
            break
        time.sleep(.05)
    assert js('!document.getElementById("tasks").hidden && document.querySelector("[data-filter=running]").classList.contains("active")')
    # Exercise the actual standalone HTTP poller and body/script replacement.
    doc['title'] = 'Обновлённый план после обычного сохранения'
    graph = grid.parse_graph_json(doc)
    page.write_text(grid.render_html(graph, grid.build_metrics(graph)))
    for _ in range(80):
        if js('document.title.startsWith("Обновлённый план")'):
            break
        time.sleep(.05)
    assert js('document.title.startsWith("Обновлённый план") && !document.getElementById("tasks").hidden && document.getElementById("search").value==="L001"')
    assert js('document.querySelector("[data-filter=running]").classList.contains("active")')
    for width in (390, 320):
        call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        for section in ('dashboard', 'outcome', 'work-plan', 'comparison', 'tasks', 'history'):
            js(f'document.querySelector("a[href$={section}]").click()')
            assert js('document.documentElement.scrollWidth <= innerWidth'), (width, section)
        assert js('document.querySelector("a[href$=history]").getBoundingClientRect().height>=44')
    call('Emulation.setEmulatedMedia', {'media': 'print'})
    assert js('[...document.querySelectorAll(".plan-section")].every(s=>getComputedStyle(s).display!=="none")')
    js('window.dispatchEvent(new Event("beforeprint"))')
    assert js('[...document.querySelectorAll("details")].every(d=>d.open)')
