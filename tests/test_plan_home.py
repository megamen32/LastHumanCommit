"""Root catalog / proxy trust boundary; all fixtures are local and disposable."""
import copy
from email.message import Message
from types import SimpleNamespace
import urllib.error
import urllib.request

import pytest

from test_plan_mirror import fixture, start, stop, mirror, pending


def get(server, path='/', headers=None, data=None):
    req = urllib.request.Request('http://127.0.0.1:' + str(server.server_port) + path,
                                 headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def test_root_sso_and_capability_guard_machine_api_independent(fixture):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    mirror.capture(plan)
    cfg['sso_enabled'] = True
    server = start(cfg)
    verified = {'X-LHC-SSO-Verified': '1'}
    auth = {'Authorization': 'Bearer ' + 'a' * 32}
    capability = '/dashboard/' + 'b' * 32 + '/'
    try:
        for path in ('/', capability):
            assert get(server, path)[0] == 401
            assert get(server, path, {'X-LHC-SSO-Verified': '0'})[0] == 401
            assert get(server, path, auth)[0] == 401
            assert get(server, path, verified)[0] == 200
        # Forwarded IP does not influence the actual peer check.
        handler = server.RequestHandlerClass
        headers = Message()
        headers['X-LHC-SSO-Verified'] = '1'
        headers['X-Forwarded-For'] = '127.0.0.1'
        request = SimpleNamespace(client_address=('203.0.113.7', 1234), headers=headers)
        assert not handler.proxy_authorized(request)
        request.client_address = ('127.0.0.1', 1234)
        assert handler.proxy_authorized(request)
        headers['X-LHC-SSO-Verified'] = '1'
        assert not handler.proxy_authorized(request)  # ambiguous duplicate rejected
        request.client_address = ('::1', 1234)
        del headers['X-LHC-SSO-Verified']
        headers['X-LHC-SSO-Verified'] = '1'
        assert handler.proxy_authorized(request)
        assert get(server, '/v1/status', verified)[0] == 404
        assert get(server, '/v1/status', auth)[0] == 200
        assert get(server, '/v1/snapshots', verified, b'{}')[0] == 401
        assert get(server, '/v1/snapshots', auth, mirror.pub.encoded(pending(plan)).encode())[0] == 200
    finally:
        stop(server)


def test_no_sso_root_closed_legacy_capability_works_and_sso_key_optional(fixture):
    _, _, cfg = fixture
    server = start(cfg)
    try:
        assert get(server, headers={'X-LHC-SSO-Verified': '1'})[0] == 404
        status, page = get(server, '/dashboard/' + 'b' * 32 + '/')
        assert status == 200 and 'Пока нет синхронизированных планов' in page
    finally:
        stop(server)
    cfg['sso_enabled'] = True
    del cfg['dashboard_key_file']
    server = start(cfg)
    try:
        assert get(server)[0] == 401
        assert get(server, headers={'X-LHC-SSO-Verified': '1'})[0] == 200
    finally:
        stop(server)


def catalog_entries(fixture):
    plan, client, _ = fixture
    mirror.register(plan, client)
    mirror.capture(plan)
    original = pending(plan)
    entries = []
    for i in range(36):
        snap = copy.deepcopy(original)
        snap.update(project=f'project-{i // 3:02}', name=f'plan-{i:02}', identity=f'identity-{i}',
                    last_file_event=f'2026-10-{i % 25 + 1:02}T00:00:00Z')
        snap['document']['title'] = f'План {i:02} <img src=x onerror=alert(1)> " &'
        snap['document']['tasks'][0]['status'] = ['running', 'blocked', 'done'][i % 3]
        snap['document']['tasks'][0]['note'] = 'PRIVATE-TASK-NOTE'
        entries.append({'snapshot': snap, 'receipt': {'received_at': snap['last_file_event'],
                                                     'url': 'javascript:alert(1)'}})
    return entries


def test_all_projects_plans_grouped_sorted_safe_and_no_task_dump(fixture, monkeypatch):
    replica = mirror.Replica(fixture[2])
    entries = catalog_entries(fixture)
    monkeypatch.setattr(replica, 'entries', lambda: entries)
    page = replica.dashboard()
    assert page.count('<section class="project">') == 12
    assert page.count('<article ') == 36
    assert 'Проектов: <b>12</b>' in page and 'Планов: <b>36</b>' in page
    assert 'В работе: 12 · Заблокировано: 12 · Завершено: 12' in page
    for i in range(36):
        assert f'/project-{i // 3:02}/plan-{i:02}/' in page
    # Last source event is day 25, then 24. Group rows also retain event order.
    assert page.index('<h2>project-08') < page.index('<h2>project-07')
    assert page.index('/project-00/plan-02/') < page.index('/project-00/plan-01/')
    assert '&lt;img' in page and '<img' not in page
    assert 'PRIVATE-TASK-NOTE' not in page and 'javascript:' not in page
    assert 'view-r001.html' in page


def test_catalog_browser_filters_refresh_auth_expiry_mobile(fixture, browser, tmp_path, monkeypatch):
    call, js, url = browser
    replica = mirror.Replica(fixture[2])
    monkeypatch.setattr(replica, 'entries', lambda: catalog_entries(fixture))
    (tmp_path / 'plan.html').write_text(replica.dashboard())
    call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
    call('Page.navigate', {'url': url})
    import time
    for _ in range(100):
        if js("!!document.querySelector('main[data-lhc-catalog]')"):
            break
        time.sleep(.05)
    assert js("document.documentElement.scrollWidth <= innerWidth")
    assert js("document.querySelectorAll('article').length") == 36
    js("search.value='project-00';search.dispatchEvent(new Event('input'));scope.value='active';scope.dispatchEvent(new Event('change'))")
    assert js("document.querySelectorAll('article:not([hidden])').length") == 2
    assert js("document.querySelectorAll('.project:not([hidden])').length") == 1
    # Real fetch replaces data, controls retain values and filter still applies.
    js('refresh()')
    assert js("search.value==='project-00' && scope.value==='active'")
    assert js("document.querySelectorAll('article:not([hidden])').length") == 2
    for stub in ("new Response('',{status:401})", "new Response('',{status:403})",
                 "({status:0,type:'opaqueredirect'})", "new Response('<html>SSO login</html>')"):
        js(f"window.fetch=async()=>({stub});refresh()")
        assert js("!document.getElementById('signin').hidden")
        assert js("document.querySelectorAll('article').length") == 36
    js("search.value='неттакогоплана';filter()")
    assert js("!document.getElementById('no-matches').hidden")
    js("search.value='';scope.value='all';filter()")
    assert js("document.querySelectorAll('article:not([hidden])').length") == 36


# Reuse the project's isolated Chrome fixture; opt in explicitly for this test.
from test_plan_dashboard_browser import browser
test_catalog_browser_filters_refresh_auth_expiry_mobile = pytest.mark.skipif(
    __import__('os').environ.get('LHC_UI_BROWSER_TESTS') != '1', reason='opt-in isolated Chrome'
)(test_catalog_browser_filters_refresh_auth_expiry_mobile)
