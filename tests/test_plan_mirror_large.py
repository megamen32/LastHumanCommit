"""A plan whose snapshot outgrew the 8 MB wire cap stopped reaching its page.

agent-herder plan 20261107-herder-native-mcp-breaking, 386 leaves: the encoded snapshot
was 12 MB, the client raised «snapshot size limit exceeded», and the local state said only
«ValueError: синхронизация или источник недоступны». The page stayed at 06:31 UTC.
"""
import json
import sys
import threading
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_plan_mirror as mirror  # noqa: E402


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    plan = tmp_path / 'roots' / 'plan'
    write(plan / 'plan.json', {'title': 'Большой план', 'goal': 'Дойти до страницы', 'slots': 2})
    for index in range(40):
        write(plan / f'leaves/L{index:03}.json', {
            'id': f'L{index:03}', 'label': f'Лист {index}', 'status': 'queued', 'estimate_minutes': 10,
            'note': 'Длинная, но повторяющаяся заметка о ходе работы. ' * 60})
    token = tmp_path / 'token'
    token.write_text('a' * 32)
    token.chmod(0o600)
    key = tmp_path / 'dashboard-key'
    key.write_text('b' * 32)
    key.chmod(0o600)
    server_cfg = {'listen': '127.0.0.1', 'port': 0, 'data_dir': str(tmp_path / 'replica'),
                  'webroot': str(tmp_path / 'web'), 'base_url': 'https://lhc.example',
                  'token_file': str(token), 'dashboard_key_file': str(key)}
    server = mirror.make_server(server_cfg)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = tmp_path / 'client.json'
    write(client, {'mode': 'mirror', 'data_dir': str(tmp_path / 'client'), 'base_url': server_cfg['base_url'],
                   'endpoint': 'http://127.0.0.1:' + str(server.server_address[1]), 'token_file': str(token),
                   'roots': [str(plan.parent)], 'poll_seconds': .05, 'debounce_seconds': .08,
                   'timeout_seconds': 5})
    # The real plan was 12 MB against 8 MB; here the snapshot is ~1 MB against a 64 KB cap.
    monkeypatch.setattr(mirror, 'MAX_BYTES', 64 * 1024)
    yield plan, client, server_cfg
    server.shutdown()
    server.server_close()


def test_a_snapshot_over_the_wire_cap_still_reaches_the_page(setup):
    plan, client, server_cfg = setup
    mirror.register(plan, client)
    mirror.run_observer(client, once=True)
    state = mirror.read(mirror.directory(plan) / 'mirror-state.json')
    assert state['error'] is None, state['error']
    page = next(Path(server_cfg['webroot']).rglob('index.html')).read_text()
    assert 'Лист 39' in page


def test_a_snapshot_too_big_even_compressed_says_so(setup, monkeypatch):
    plan, client, _ = setup
    monkeypatch.setattr(mirror, 'MAX_SNAPSHOT_BYTES', 100 * 1024)
    mirror.register(plan, client)
    mirror.run_observer(client, once=True)
    error = mirror.read(mirror.directory(plan) / 'mirror-state.json')['error']
    assert 'snapshot size limit exceeded' in error, error
