"""Repeated catalog/status reads do not reparse unchanged replica histories."""
import copy
import json
from pathlib import Path
import sys
import threading
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_plan_mirror as mirror


def replica(tmp_path):
    return mirror.Replica({'data_dir': str(tmp_path / 'data'),
                          'webroot': str(tmp_path / 'web'), 'base_url': 'https://lhc.test'})


def entry():
    doc = {'title': 'Plan', 'tasks': [{'id': 'A', 'label': 'Work', 'status': 'queued',
                                    'estimate_minutes': 10}]}
    return {'snapshot': {'identity': 'identity', 'project': 'project', 'name': 'plan',
                         'last_file_event': '2026-10-28T00:00:00Z', 'document': doc,
                         'revisions': [{'id': 'r001', 'created_at': '2026-10-28T00:00:00Z',
                                        'document': copy.deepcopy(doc)}]}, 'receipt': {}}


def test_unchanged_dashboard_and_status_read_each_replica_once(tmp_path, monkeypatch):
    service = replica(tmp_path)
    path = service.data / 'identity.json'
    path.write_text(json.dumps(entry()))
    original, calls = mirror.read, []
    def counted(path, *args, **kwargs):
        calls.append(Path(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', counted)
    service.dashboard()
    service.entries()
    service.dashboard()
    assert calls.count(path) == 1


def test_repeated_authenticated_http_root_does_not_reread_histories(tmp_path, monkeypatch):
    service = replica(tmp_path)
    (service.data / 'identity.json').write_text(json.dumps(entry()))
    token = tmp_path / 'token'
    token.write_text('a' * 32)
    token.chmod(0o600)
    cfg = dict(service.cfg, port=0, token_file=str(token), sso_enabled=True)
    monkeypatch.setattr(mirror.Replica, 'render', lambda self, entry: None)
    server = mirror.make_server(cfg)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    original, calls = mirror.read, []
    def counted(path, *args, **kwargs):
        calls.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', counted)
    try:
        url = 'http://127.0.0.1:' + str(server.server_address[1]) + '/'
        for _ in range(3):
            request = urllib.request.Request(url, headers={'X-LHC-SSO-Verified': '1'})
            with urllib.request.urlopen(request) as response:
                assert response.status == 200
                assert 'Plan' in response.read().decode()
        assert not calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join(2)


def test_cache_observes_replace_add_and_delete(tmp_path):
    service = replica(tmp_path)
    path = service.data / 'identity.json'
    first = entry()
    path.write_text(json.dumps(first))
    assert service.entries()[0]['snapshot']['document']['title'] == 'Plan'
    changed = copy.deepcopy(first)
    changed['snapshot']['document']['title'] = 'Next'
    replacement = service.data / 'replacement.tmp'
    replacement.write_text(json.dumps(changed))
    replacement.replace(path)
    assert service.entries()[0]['snapshot']['document']['title'] == 'Next'
    added = service.data / 'another.json'
    added.write_text(json.dumps(first))
    assert len(service.entries()) == 2
    path.unlink()
    assert len(service.entries()) == 1


def test_public_entries_do_not_expose_mutable_cache_and_ingest_can_read_fresh(tmp_path, monkeypatch):
    service = replica(tmp_path)
    path = service.data / 'identity.json'
    path.write_text(json.dumps(entry()))
    value = service.entries()
    value[0]['snapshot']['document']['title'] = 'Accidental mutation'
    assert service.entries()[0]['snapshot']['document']['title'] == 'Plan'
    original, calls = mirror.read, []
    def counted(path, *args, **kwargs):
        calls.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', counted)
    service.entries(fresh=True)
    service.entries(fresh=True)
    assert not calls  # Fresh ownership is event-drained, not a full archive read.


def test_dashboard_recomputes_active_time_at_most_once_per_minute(tmp_path, monkeypatch):
    service = replica(tmp_path)
    (service.data / 'identity.json').write_text(json.dumps(entry()))
    calls = []
    tick = [0.0]
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.catalog, 'render_items', lambda items, now: calls.append(items) or str(len(calls)))
    assert service.dashboard() == '1'
    tick[0] = 59.9
    assert service.dashboard() == '1'
    tick[0] = 60.0
    assert service.dashboard() == '2'


def test_cached_legacy_title_is_invalidated_on_change(tmp_path, monkeypatch):
    service = replica(tmp_path)
    page = Path(service.cfg['webroot']) / 'legacy' / 'old' / 'index.html'
    page.parent.mkdir(parents=True)
    page.write_text('<title>Old</title>')
    original, calls = Path.open, []
    def counted(path, *args, **kwargs):
        if path == page:
            calls.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', counted)
    assert service.legacy()[0][2] == 'Old'
    assert service.legacy()[0][2] == 'Old'
    assert len(calls) == 1
    page.write_text('<title>New title</title>')
    assert service.legacy()[0][2] == 'New title'


def test_same_tick_inplace_updates_are_revalidated_immediately_by_event(tmp_path, monkeypatch):
    service = replica(tmp_path)
    path = service.data / 'identity.json'
    value = entry()
    path.write_text(json.dumps(value))
    page = Path(service.cfg['webroot']) / 'legacy' / 'old' / 'index.html'
    page.parent.mkdir(parents=True)
    page.write_text('<title>Old</title>')
    tick = [0.0]
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    assert service.entries()[0]['snapshot']['document']['title'] == 'Plan'
    assert service.legacy()[0][2] == 'Old'
    value['snapshot']['document']['title'] = 'Next'
    path.write_text(json.dumps(value))
    page.write_text('<title>New</title>')
    assert service.entries()[0]['snapshot']['document']['title'] == 'Next'
    assert service.legacy()[0][2] == 'New'
