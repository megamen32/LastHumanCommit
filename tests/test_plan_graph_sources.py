"""Explicit legacy graphs use the same durable observer, without source rewrites."""
import json
from pathlib import Path
import subprocess

import pytest

from test_plan_mirror import fixture, mirror, write, start, stop, connect


def graph_fixture(fixture):
    native, client, cfg = fixture
    repo = native.parent.parent / 'LegacyProject'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    source = repo / '.agents/tasks/old/plan.graph.json'
    doc = {'schema_version': 2, 'title': 'Старый граф', 'slots': 2,
           'updated_at': '2026-01-01T00:00:00Z',
           'tasks': [{'id': 'A', 'label': 'Исходная работа', 'status': 'running',
                      'started_at': '2026-01-01T00:00:00Z', 'estimate_minutes': 10}]}
    write(source, doc)
    settings = mirror.config(client)
    settings.update(roots=[], graph_sources=[str(source), str(source.parent / '..' / 'old' / source.name)])
    write(client, settings)
    return source, doc, client, cfg


def test_graph_offline_restart_raw_changes_bad_source_preserves_good(fixture):
    source, doc, client, cfg = graph_fixture(fixture)
    raw = source.read_bytes()
    assert mirror.discover(mirror.config(client)) == [str(source)]
    mirror.run_observer(client, once=True)  # endpoint offline
    sidecar = mirror.directory(source)
    state = mirror.read(sidecar / 'mirror-state.json')
    assert state['error'] and state['pending']['document']['updated_at'] == doc['updated_at']
    assert state['pending']['document']['tasks'][0]['started_at'] == doc['tasks'][0]['started_at']
    assert 'actual_minutes' not in state['pending']['document']['tasks'][0]
    assert 'plan_origin' not in state['pending']['document']
    assert state['pending']['project'] == 'legacyproject'
    assert source.read_bytes() == raw
    assert not (source.parent / 'leaves').exists()
    server = start(cfg)
    try:
        connect(client, server)
        mirror.run_observer(client, once=True)
        state = mirror.read(sidecar / 'mirror-state.json')
        url = state['server_receipt']['url']
        target = Path(cfg['webroot']) / state['pending']['project'] / state['pending']['name']
        baseline = (target / 'r001.html').read_bytes()
        assert state['error'] is None
        doc['tasks'][0].update(label='Граф изменён без CLI', status='done')
        write(source, doc)
        updated = source.read_bytes()
        mirror.run_observer(client, once=True)
        current = (target / 'index.html').read_bytes()
        assert 'Граф изменён без CLI' in current.decode()
        assert source.read_bytes() == updated
        assert mirror.read(sidecar / 'mirror-state.json')['server_receipt']['url'] == url
        assert (target / 'r001.html').read_bytes() == baseline
        source.write_text('{')
        mirror.run_observer(client, once=True)
        assert mirror.read(sidecar / 'mirror-state.json')['error']
        assert (target / 'index.html').read_bytes() == current
        source.unlink()
        mirror.run_observer(client, once=True)
        assert (target / 'index.html').read_bytes() == current
        write(source, doc)
        mirror.run_observer(client, once=True)
        assert mirror.read(sidecar / 'mirror-state.json')['error'] is None
        assert (target / 'r001.html').read_bytes() == baseline
    finally:
        stop(server)


@pytest.mark.parametrize('path', ['relative/plan.graph.json', '/tmp/other.json'])
def test_graph_sources_explicit_absolute_only(fixture, path):
    cfg = mirror.config(fixture[1])
    cfg['graph_sources'] = [path]
    with pytest.raises(ValueError, match='absolute plan.graph.json'):
        mirror.discover(cfg)
