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
import lhc_plan_publish as pub

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

        call('Page.bringToFront')

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
        if js('!!document.getElementById("plan-app") && !!window.__lhcUI && !!document.querySelector(".plan-sidebar [aria-current]")'):
            break
        time.sleep(.05)
    assert js('document.querySelector(".plan-sidebar [aria-current]")?.hash') == '#dashboard', js('({url:location.href,text:document.body.innerText.slice(0,300),sections:[...document.querySelectorAll(".plan-section")].map(s=>s.id),ready:document.readyState,app:!!window.__lhcUI})')
    assert js('document.getElementById("lhc-state").getBoundingClientRect().top < 500')
    visible = '[...document.querySelectorAll(".plan-section")].filter(s=>!s.hidden && getComputedStyle(s).display!=="none").length'
    assert js(visible) == 6
    assert js('!document.querySelector(".status-details").closest("details") && !!document.querySelector(".panel-blocking .empty") && getComputedStyle(document.querySelector(".panel-blocking")).display!=="none"')
    call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    js('document.querySelector("a[href$=outcome]").click()')
    time.sleep(.1)
    assert js(visible) == 6
    assert js('Math.abs(document.getElementById("outcome").getBoundingClientRect().top-24)<3')
    assert js('document.querySelector(".brief-goal details")!==null')
    old_history = js('history.length')
    js('document.getElementById("work-plan").scrollIntoView()')
    time.sleep(.1)
    assert js('document.querySelector(".plan-sidebar [aria-current=location]").hash') == '#work-plan'
    assert js('history.length') == old_history
    assert js('location.hash') == '#outcome'
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
    js('window.scrollBy(0,130)')
    position = js('scrollY')
    doc['title'] = 'Обновлённый план после обычного сохранения'
    graph = grid.parse_graph_json(doc)
    page.write_text(grid.render_html(graph, grid.build_metrics(graph)))
    for _ in range(80):
        if js('document.title.startsWith("Обновлённый план")'):
            break
        time.sleep(.05)
    assert js('document.title.startsWith("Обновлённый план") && !document.getElementById("tasks").hidden && document.getElementById("search").value==="L001"')
    assert abs(js('scrollY') - position) < 3
    assert js(visible) == 6
    assert js('document.querySelector("[data-filter=running]").classList.contains("active")')
    for width in (390, 320):
        call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        for section in ('dashboard', 'outcome', 'work-plan', 'comparison', 'tasks', 'history'):
            js(f'document.querySelector("a[href$={section}]").click()')
            time.sleep(.1)
            assert js(visible) == 6
            assert js('document.documentElement.scrollWidth <= innerWidth'), (width, section)
            assert js(f'document.getElementById("{section}").getBoundingClientRect().top >= document.querySelector(".plan-sidebar").getBoundingClientRect().bottom-2'), (width, section)
        assert js('document.querySelector("a[href$=history]").getBoundingClientRect().height>=44')
        js('document.querySelector("a[href$=dashboard]").focus(); document.querySelector("a[href$=dashboard]").dispatchEvent(new KeyboardEvent("keydown",{key:"End",bubbles:true}))')
        assert js('location.hash') == '#history'
        assert js('document.querySelector("a[href$=history]").getBoundingClientRect().right <= innerWidth')
    call('Emulation.setEmulatedMedia', {'media': 'print'})
    assert js('[...document.querySelectorAll(".plan-section")].every(s=>getComputedStyle(s).display!=="none")')
    js('window.dispatchEvent(new Event("beforeprint"))')
    assert js('[...document.querySelectorAll("details")].every(d=>d.open)')


def test_publication_reload_restores_position_but_deliberate_hash_wins(browser, tmp_path):
    call, js, url = browser
    doc = {'schema_version': 2, 'title': 'Зеркало плана', 'slots': 1,
           'tasks': [{'id': f'A{i:02}', 'label': 'Работа ' * 10, 'status': 'queued',
                      'estimate_minutes': 10} for i in range(20)]}
    revisions = [{'id': 'r001', 'document': doc, 'reason': 'Начало', 'created_at': '2026-10-25T10:00:00Z'}]
    def write(version):
        (tmp_path / 'plan.html').write_text(pub.page(doc, doc, doc, revisions, 'r001', revisions[0]['created_at'], True, version))
        (tmp_path / 'version.json').write_text(json.dumps({'version': version}))
    write('one')
    call('Page.enable')
    call('Page.navigate', {'url': url})
    for _ in range(100):
        if js('!!document.querySelector(".plan-sidebar [aria-current]")'):
            break
        time.sleep(.05)
    call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    js('document.querySelector("a[href$=tasks]").click(); const s=document.getElementById("search"); s.value="A06"; s.dispatchEvent(new Event("input")); document.querySelector("[data-filter=queued]").click()')
    time.sleep(.1)
    js('scrollTo({top:scrollY-350,behavior:"instant"})')
    position = js('scrollY')
    assert js('Math.abs(document.getElementById("tasks").getBoundingClientRect().top-24)>100')
    write('two')
    for _ in range(300):
        if js('document.getElementById("lhc-publication-live")?.textContent.includes("version=\'two\'") && !!document.querySelector(".plan-sidebar [aria-current]")'):
            break
        time.sleep(.05)
    assert js('document.getElementById("lhc-publication-live").textContent.includes("version=\'two\'")')
    time.sleep(.1)
    assert abs(js('scrollY') - position) < 3
    assert js('document.getElementById("search").value') == 'A06'
    assert js('document.querySelector("[data-filter=queued]").classList.contains("active")')
    call('Page.navigate', {'url': url + '#outcome'})
    time.sleep(.2)
    assert js('Math.abs(document.getElementById("outcome").getBoundingClientRect().top-24)<3')
