"""Local authority, raw-file consumers, restart/replay and replica boundaries."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_plan_json as leaves
import lhc_plan_publish as pub
import lhc_plan_mirror as mirror
import lhc_plan_mcp as mcp


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


@pytest.fixture
def fixture(tmp_path):
    plan = tmp_path / 'roots' / 'plan'
    write(plan / 'plan.json', {'title': 'Локальный план', 'goal': 'Читать обычные сохранения', 'slots': 2})
    write(plan / 'leaves/A.json', {'id': 'A', 'label': 'Первая работа', 'status': 'queued', 'estimate_minutes': 10})
    token = tmp_path / 'token'
    token.write_text('a' * 32)
    token.chmod(0o600)
    key = tmp_path / 'dashboard-key'
    key.write_text('b' * 32)
    key.chmod(0o600)
    server = {'listen': '127.0.0.1', 'port': 0, 'data_dir': str(tmp_path / 'replica'),
              'webroot': str(tmp_path / 'web'), 'base_url': 'https://lhc.example',
              'token_file': str(token), 'dashboard_key_file': str(key)}
    client = tmp_path / 'client.json'
    write(client, {'mode': 'mirror', 'data_dir': str(tmp_path / 'client'), 'base_url': server['base_url'],
                   'endpoint': 'http://127.0.0.1:1', 'token_file': str(token), 'roots': [str(plan.parent)],
                   'poll_seconds': .05, 'debounce_seconds': .08, 'timeout_seconds': .15})
    return plan, client, server


def start(cfg):
    server = mirror.make_server(cfg)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def stop(server):
    server.shutdown()
    server.server_close()


def connect(client, server):
    cfg = mirror.config(client)
    cfg['endpoint'] = 'http://127.0.0.1:' + str(server.server_address[1])
    write(client, cfg)


def dest(plan, cfg):
    state = mirror.read(mirror.directory(plan) / 'state.json')
    return Path(cfg['webroot']) / state['project'] / state['name']


def pending(plan):
    return mirror.read(mirror.directory(plan) / 'mirror-state.json')['pending']


def test_raw_save_offline_history_rebuild_and_url_migration(fixture):
    plan, client, cfg = fixture
    # Existing explicit publication retains URL and immutable original HTML.
    legacy = plan.parent.parent / 'publish.json'
    write(legacy, {k: cfg[k] for k in ('webroot', 'base_url')})
    original_url = pub.publish(plan, legacy, autopublish=True)['url']
    target = dest(plan, cfg)
    original = (target / 'r001.html').read_bytes()
    mirror.register(plan, client)
    assert mirror.read(mirror.directory(plan) / 'state.json')['autopublish'] is False
    frozen = (mirror.directory(plan) / 'revisions/r001.json').read_bytes()
    mirror.run_observer(client, once=True)  # unavailable server, durable snapshot
    # Plain save, no publication/build commands.
    write(plan / 'leaves/A.json', {'id': 'A', 'label': 'Обычное сохранение офлайн', 'status': 'done', 'estimate_minutes': 10, 'actual_minutes': 7})
    pub.publish(plan, reason='Локальная ревизия без сети')
    assert len(pending(plan)['revisions']) == 2
    assert (mirror.directory(plan) / 'revisions/r001.json').read_bytes() == frozen
    # Restart the observer after edits, restore server, no user publish retry.
    server = start(cfg)
    try:
        connect(client, server)
        mirror.run_observer(client, once=True)
        assert 'Обычное сохранение офлайн' in (target / 'index.html').read_text()
        assert (target / 'r001.html').read_bytes() == original
        assert mirror.read(mirror.directory(plan) / 'mirror-state.json')['server_receipt']['url'] == original_url
        # Partial save cannot delete remote/local facts.
        (plan / 'leaves/A.json').write_text('{')
        mirror.run_observer(client, once=True)
        assert 'Обычное сохранение офлайн' in (target / 'index.html').read_text()
        assert pending(plan)['observed']['A']['completed'] == [{'actual_minutes': 7}]
    finally:
        stop(server)
    # Rebuild with empty replica state, source and local histories remain.
    shutil.rmtree(cfg['data_dir'])
    server = start(cfg)
    try:
        connect(client, server)
        mirror.sync(plan, mirror.config(client))
        assert (target / 'r002.html').exists()
        assert (target / 'r001.html').read_bytes() == original
    finally:
        stop(server)


def test_cli_and_mcp_bound_edit_revise_never_network(fixture, monkeypatch):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    def forbidden(*a, **kw):
        pytest.fail('local operation attempted network/SSH transport')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(pub.transport, 'deploy', forbidden)
    before = time.monotonic()
    leaves.update_leaf(plan, 'A', {'note': 'Локальный API'})
    leaves.build_graph(plan)
    pub.publish(plan, reason='Офлайн')
    assert time.monotonic() - before < 3
    # MCP subprocess shares the bound local files, no env setup/config per edit.
    result = mcp.call('update_leaf', {'plan_dir': str(plan), 'leaf_id': 'A', 'fields': {'note': 'MCP офлайн'}})
    assert not result['isError'], result
    result = mcp.call('revise_plan', {'plan_dir': str(plan), 'reason': 'MCP ревизия офлайн'})
    assert not result['isError'], result
    assert json.loads((plan / 'leaves/A.json').read_text())['note'] == 'MCP офлайн'
    assert pending(plan)['revisions'][-1]['reason'] == 'MCP ревизия офлайн'

    # Native packaged LhcPlan entrypoint, retained from 1.5.52, also edits
    # these same leaves offline (observer detects its plain atomic writes).
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
        'name': 'update_leaf', 'arguments': {'plan_dir': str(plan), 'leaf_id': 'A',
                                          'fields': {'note': 'Native MCP офлайн'}}}}
    entry = TOOLS.parents[2] / 'plugins/last-human-commit/scripts/plan_mcp.py'
    response = subprocess.run([sys.executable, str(entry)], input=json.dumps(request) + '\n',
                              text=True, capture_output=True, timeout=5)
    reply = json.loads(response.stdout)
    assert not reply['result']['isError'], reply
    assert json.loads((plan / 'leaves/A.json').read_text())['note'] == 'Native MCP офлайн'


def test_saved_leaf_success_when_mirror_bookkeeping_is_broken(fixture, monkeypatch):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    client.write_text('{')
    # Existing binding makes bookkeeping purely local; unavailable/corrupt
    # config or dirty writes cannot report the successful leaf write as failed.
    monkeypatch.setattr(mirror, 'mark', lambda *a, **k: (_ for _ in ()).throw(PermissionError()))
    result = leaves.update_leaf(plan, 'A', {'note': 'Успешно сохранён'})
    assert result['sha256']
    assert json.loads((plan / 'leaves/A.json').read_text())['note'] == 'Успешно сохранён'
    monkeypatch.setattr(mirror, 'binding', lambda *a, **k: (_ for _ in ()).throw(ValueError()))
    assert leaves.update_leaf(plan, 'A', {'note': 'Сохранён повторно'})['sha256']


def test_registration_no_rewrites_and_same_seq_no_render(fixture, monkeypatch):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    files = [mirror.directory(plan) / 'state.json', mirror.directory(plan) / 'mirror.json', Path(mirror.config(client)['data_dir']) / 'registry.json']
    stamps = [p.stat().st_mtime_ns for p in files]
    mirror.register(plan, client)
    assert stamps == [p.stat().st_mtime_ns for p in files]
    mirror.capture(plan)
    replica = mirror.Replica(cfg)
    replica.ingest(copy.deepcopy(pending(plan)))
    original_render = replica.render
    calls = []
    monkeypatch.setattr(replica, 'render', lambda entry: calls.append(entry))
    replica.ingest(copy.deepcopy(pending(plan)))
    assert not calls
    target = dest(plan, cfg)
    (target / 'index.html').unlink()
    monkeypatch.setattr(replica, 'render', original_render)
    replica.ingest(copy.deepcopy(pending(plan)))
    assert (target / 'index.html').is_file()


def test_watch_retries_transient_capture_without_another_edit(fixture, monkeypatch):
    plan, client, cfg = fixture
    tick, calls = [0.0], []
    original = mirror.capture
    class Finished(Exception):
        pass
    def capture(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise ValueError('files changed during capture')
        return original(*args, **kwargs)
    def sleep(_):
        tick[0] += 2
        if tick[0] >= 10:
            raise Finished()
    monkeypatch.setattr(mirror, 'capture', capture)
    monkeypatch.setattr(mirror, 'sync', lambda *a: None)
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.time, 'sleep', sleep)
    with pytest.raises(Finished):
        mirror.run_observer(client)
    assert len(calls) == 2
    assert pending(plan)['document']['tasks'][0]['label'] == 'Первая работа'


def test_replica_sequence_survives_interrupted_render(fixture, monkeypatch):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    mirror.capture(plan)
    original = copy.deepcopy(pending(plan))
    replica = mirror.Replica(cfg)
    replica.ingest(copy.deepcopy(original))
    leaves.update_leaf(plan, 'A', {'note': 'После восстановления renderer'})
    mirror.capture(plan)
    latest = copy.deepcopy(pending(plan))
    render = replica.render
    monkeypatch.setattr(replica, 'render', lambda *_: (_ for _ in ()).throw(OSError('interrupted')))
    with pytest.raises(OSError):
        replica.ingest(copy.deepcopy(latest))
    with pytest.raises(mirror.Conflict, match='stale'):
        mirror.Replica(cfg).ingest(original)
    monkeypatch.setattr(replica, 'render', render)
    replica.ingest(latest)
    assert 'После восстановления renderer' in (dest(plan, cfg) / 'index.html').read_text()


def test_replay_owner_conflicts_history_and_path_validation(fixture):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    mirror.capture(plan)
    replica = mirror.Replica(cfg)
    first = pending(plan)
    receipt = replica.ingest(copy.deepcopy(first))
    assert replica.ingest(copy.deepcopy(first)) == receipt
    for key, value in [('owner', 'another-owner'), ('project', '../escape'), ('identity', '../bad')]:
        bad = copy.deepcopy(first)
        bad[key] = value
        with pytest.raises(ValueError):
            replica.ingest(bad)
    leaves.update_leaf(plan, 'A', {'status': 'done', 'actual_minutes': 7})
    mirror.capture(plan)
    latest = pending(plan)
    replica.ingest(copy.deepcopy(latest))
    with pytest.raises(mirror.Conflict, match='stale'):
        replica.ingest(first)
    bad = copy.deepcopy(latest)
    bad['seq'] += 1
    bad['revisions'][0]['reason'] = 'rewrite'
    with pytest.raises(mirror.Conflict, match='immutable'):
        replica.ingest(bad)
    bad = copy.deepcopy(latest)
    bad['seq'] += 1
    bad['observed'] = {}
    with pytest.raises(mirror.Conflict, match='observed'):
        replica.ingest(bad)
    # New client/owner must not silently reuse a copied bound plan.
    copied = plan.parent / 'copied'
    shutil.copytree(plan, copied)
    with pytest.raises(ValueError, match='owner conflict'):
        mirror.register(copied, client)


def test_http_auth_limits_dashboard_and_unknown_liveness(fixture):
    plan, client, cfg = fixture
    mirror.register(plan, client)
    leaves.update_leaf(plan, 'A', {'status': 'running'})
    mirror.capture(plan)
    server = start(cfg)
    try:
        connect(client, server)
        mirror.sync(plan, mirror.config(client))
        endpoint = mirror.config(client)['endpoint']
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(endpoint + '/v1/snapshots', data=b'{}'))
        assert error.value.code == 401
        auth = {'Authorization': 'Bearer ' + 'a' * 32}
        bad_path = copy.deepcopy(pending(plan))
        bad_path['project'] = '../outside'
        bad_tasks = copy.deepcopy(pending(plan))
        bad_tasks['document']['tasks'] = [None]
        for payload in (b'{', b'{}', json.dumps(bad_path).encode(), json.dumps(bad_tasks).encode()):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(endpoint + '/v1/snapshots', data=payload, headers=auth))
            assert error.value.code == 400
        for url in ('/', '/dashboard/', '/v1/status'):
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(endpoint + url)
        with urllib.request.urlopen(endpoint + '/dashboard/' + 'b' * 32 + '/') as response:
            page = response.read().decode()
        assert 'В плане: в работе' in page and 'Живость агента: неизвестна' in page
        assert 'Событие файла' in page and 'Приём сервером' in page
        old = pending(plan)
        old['last_file_event'] = '2020-01-01T00:00:00Z'
        replica = mirror.Replica(cfg)
        old['seq'] += 1
        replica.ingest(old)
        assert 'данные устарели' in replica.dashboard()
    finally:
        stop(server)


def test_watch_process_plain_save_debounce_restart(fixture):
    plan, client, cfg = fixture
    server = start(cfg)
    connect(client, server)
    proc = subprocess.Popen([sys.executable, str(TOOLS / 'lhc_plan_mirror.py'), 'watch', '--config', str(client)])
    def wait_for(predicate, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.05)
        pytest.fail('watch consumer did not converge')
    try:
        target = None
        wait_for(lambda: (mirror.directory(plan) / 'mirror-state.json').exists())
        target = dest(plan, cfg)
        wait_for(lambda: (target / 'index.html').exists())
        # Dependent saves across a temporarily invalid intermediate state.
        write(plan / 'leaves/B.json', {'id': 'B', 'label': 'Зависимая работа', 'status': 'queued', 'estimate_minutes': 5, 'depends_on': ['C']})
        time.sleep(.15)
        write(plan / 'leaves/C.json', {'id': 'C', 'label': 'Основа', 'status': 'queued', 'estimate_minutes': 5})
        write(plan / 'leaves/A.json', {'id': 'A', 'label': 'Файл изменён напрямую', 'status': 'queued', 'estimate_minutes': 10})
        wait_for(lambda: 'Файл изменён напрямую' in (target / 'index.html').read_text())
        assert 'Зависимая работа' in (target / 'index.html').read_text()
        state = mirror.read(mirror.directory(plan) / 'mirror-state.json')
        event = state['last_file_event']
        mirror.sync(plan, mirror.config(client))
        assert mirror.read(mirror.directory(plan) / 'mirror-state.json')['last_file_event'] == event
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        stop(server)
