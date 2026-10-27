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


def test_only_root_uses_sso_capability_and_machine_api_remain_independent(fixture):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    mirror.capture(plan)
    cfg['sso_enabled'] = True
    server = start(cfg)
    verified = {'X-LHC-SSO-Verified': '1'}
    auth = {'Authorization': 'Bearer ' + 'a' * 32}
    capability = '/dashboard/' + 'b' * 32 + '/'
    try:
        assert get(server, '/')[0] == 401
        assert get(server, '/', {'X-LHC-SSO-Verified': '0'})[0] == 401
        assert get(server, '/', auth)[0] == 401
        assert get(server, '/', verified)[0] == 200
        # Agent-readable capability pages do not inherit the home page SSO gate.
        assert get(server, capability)[0] == 200
        assert get(server, capability, {'X-LHC-SSO-Verified': '0'})[0] == 200
        assert get(server, capability, auth)[0] == 200
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


def test_all_projects_plans_listed_sorted_safe_and_no_task_dump(fixture, monkeypatch):
    replica = mirror.Replica(fixture[2])
    entries = catalog_entries(fixture)
    monkeypatch.setattr(replica, 'entries', lambda: entries)
    monkeypatch.setattr(replica, 'legacy', lambda: [])
    page = replica.dashboard()
    assert page.count('<article class="plan') == 36
    assert page.count('<option value="project-') == 12
    # Old source events: unfinished running plans are stalled, not "in progress".
    assert page.count('data-state="stalled"') == 12
    assert page.count('data-state="blocked"') == 12
    assert page.count('data-state="completed"') == 12
    for i in range(36):
        assert f'/project-{i // 3:02}/plan-{i:02}/' in page
    # Attention first: blocked before stalled before completed; newest first inside.
    assert page.index('data-state="blocked"') < page.index('data-state="stalled"') < page.index('data-state="completed"')
    assert page.index('/project-07/plan-22/') < page.index('/project-00/plan-01/')
    assert '&lt;img' in page and '<img' not in page
    assert 'PRIVATE-TASK-NOTE' not in page and 'javascript:' not in page


def test_catalog_browser_filters_refresh_auth_expiry_mobile(fixture, browser, tmp_path, monkeypatch):
    call, js, url = browser
    replica = mirror.Replica(fixture[2])
    monkeypatch.setattr(replica, 'entries', lambda: catalog_entries(fixture))
    monkeypatch.setattr(replica, 'legacy', lambda: [])
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
    js("const s=document.getElementById('search');s.value='project-00';s.dispatchEvent(new Event('input'));"
       "document.querySelector('[data-filter=\"blocked\"]').click()")
    assert js("document.querySelectorAll('article:not([hidden])').length") == 1
    js('refresh()')
    assert js("document.getElementById('search').value==='project-00'")
    assert js("document.querySelectorAll('article:not([hidden])').length") == 1
    for stub in ("new Response('',{status:401})", "new Response('',{status:403})",
                 "({status:0,type:'opaqueredirect'})", "new Response('<html>SSO login</html>')"):
        js(f"window.fetch=async()=>({stub});refresh()")
        assert js("!document.getElementById('signin').hidden")
        assert js("document.querySelectorAll('article').length") == 36


# Reuse the project's isolated Chrome fixture; opt in explicitly for this test.
from test_plan_dashboard_browser import browser
test_catalog_browser_filters_refresh_auth_expiry_mobile = pytest.mark.skipif(
    __import__('os').environ.get('LHC_UI_BROWSER_TESTS') != '1', reason='opt-in isolated Chrome'
)(test_catalog_browser_filters_refresh_auth_expiry_mobile)
