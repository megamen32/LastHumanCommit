"""Source-local creation provenance; replicas never recover filesystem dates."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_plan_json as leaves
import lhc_plan_publish as pub
import lhc_plan_mirror as mirror
import lhc_grid as grid


def plan(tmp_path):
    (tmp_path / 'leaves').mkdir()
    (tmp_path / 'plan.json').write_text(json.dumps({'title': 'План'}))
    return tmp_path


def raw(root, name='A', **fields):
    path = root / 'leaves' / (name + '.json')
    path.write_text(json.dumps({'id': name, 'label': name, **fields}))
    return path


def test_native_creation_is_automatic_and_immutable(tmp_path):
    root = plan(tmp_path)
    leaves.update_leaf(root, 'A', {'label': 'Первый'}, create=True)
    first = json.loads((root / 'leaves/A.json').read_text())['created_at']
    assert leaves.origin_time(first) is not None
    origin = leaves.build_document(root)['plan_origin']
    leaves.update_leaf(root, 'A', {'note': 'Правка'})
    assert json.loads((root / 'leaves/A.json').read_text())['created_at'] == first
    before = (root / 'leaves/A.json').read_bytes()
    with pytest.raises(leaves.LeafError):
        leaves.update_leaf(root, 'A', {'created_at': '2099-01-01T00:00:00Z'})
    assert (root / 'leaves/A.json').read_bytes() == before
    assert leaves.build_document(root)['plan_origin'] == origin


def test_raw_discovery_freezes_source_birth_before_deletion(tmp_path, monkeypatch):
    root = plan(tmp_path)
    raw(root)
    monkeypatch.setattr(leaves, 'file_birthtime', lambda p: '2026-10-25T11:23:00+00:00')
    assert not (root / '.lhc-publication').exists()
    leaves.build_document(root)  # read/check is not a write
    assert not (root / '.lhc-publication').exists()
    leaves.build_graph(root)
    original = leaves.build_document(root)['plan_origin']
    assert original['at'] == '2026-10-25T11:23:00+00:00'
    assert original['source'] == 'file_birthtime'
    (root / 'leaves/A.json').unlink()
    raw(root, 'B', created_at='2026-10-26T11:23:00Z')
    leaves.build_graph(root)
    assert leaves.build_document(root)['plan_origin'] == original


def test_offsets_and_earlier_work_win_over_replaced_file_birth(tmp_path, monkeypatch):
    root = plan(tmp_path)
    raw(root, started_at='2026-10-25T19:54:52+03:00')
    monkeypatch.setattr(leaves, 'file_birthtime', lambda p: '2026-10-25T19:55:45+03:00')
    origin = leaves.ensure_plan_origin(root)
    assert origin['at'] == '2026-10-25T19:54:52+03:00'
    assert origin['source'] == 'recorded_start'


def test_no_birth_means_unknown_never_mtime_or_ctime(tmp_path, monkeypatch):
    root = plan(tmp_path)
    raw(root)
    monkeypatch.setattr(leaves, 'file_birthtime', lambda p: '')
    assert leaves.ensure_plan_origin(root)['source'] == 'unknown'
    assert leaves.build_document(root)['plan_origin']['at'] == ''


def test_graph_public_mirror_roundtrip_and_no_replica_recovery(tmp_path, monkeypatch):
    root = plan(tmp_path)
    raw(root, created_at='2026-10-25T14:23:00+03:00')
    raw(root, 'B', created_at='2026-10-25T11:24:00Z')
    leaves.ensure_plan_origin(root)
    doc = leaves.build_document(root)
    assert doc['plan_origin']['leaf_id'] == 'A'
    monkeypatch.setattr(leaves, 'file_birthtime', lambda p: pytest.fail('replica stat'))
    clean = mirror.valid_document(pub.public_document(doc))
    assert clean['tasks'][0]['created_at'] == '2026-10-25T14:23:00+03:00'
    graph = grid.parse_graph_json(clean)
    assert grid.export_graph(graph)['plan_origin'] == doc['plan_origin']
    f = grid.build_metrics(graph)['time_frame']
    assert f['start'] == doc['plan_origin']['at']
    assert f['start_source'] == 'leaf_created_at'
    assert grid.export_graph(graph)['tasks'][0]['created_at'] == clean['tasks'][0]['created_at']


def test_imported_graph_keeps_origin_after_source_copy(tmp_path, monkeypatch):
    root = plan(tmp_path)
    raw(root)
    origin = {'at': '2026-10-25T11:23:00Z', 'source': 'file_birthtime',
              'leaf_id': 'OLD', 'recorded_at': '2026-10-25T12:00:00Z'}
    (root / 'plan.graph.json').write_text(json.dumps({'plan_origin': origin}))
    monkeypatch.setattr(leaves, 'file_birthtime', lambda p: pytest.fail('copied birth'))
    leaves.build_graph(root)
    assert leaves.read_plan_origin(root) == origin
    assert json.loads((root / '.lhc-publication/plan-origin.json').read_text()) == origin


def test_real_source_birth_is_not_render_or_observer_receipt(tmp_path):
    root = plan(tmp_path)
    path = raw(root)
    birth = leaves.file_birthtime(path)
    if not birth:
        pytest.skip('filesystem has no birthtime')
    origin = leaves.ensure_plan_origin(root)
    assert origin['at'] == birth
    assert leaves.origin_time(origin['at']) <= leaves.origin_time(origin['recorded_at'])


def test_migration_unchanged_source_preserves_old_revision_and_r002(tmp_path):
    from test_plan_mirror import fixture, pending
    # Reuse the same local/offline fixture; no production runtime or token.
    root, client, _ = fixture.__wrapped__(tmp_path)
    mirror.register(root, client)
    old_doc = pub.public_document(leaves.build_document(root))
    pub.freeze(mirror.directory(root), old_doc, 'Исходный план')
    archive = mirror.directory(root) / 'revisions/r001.json'
    original = archive.read_bytes()
    sources = {p: p.read_bytes() for p in [root / 'plan.json', root / 'leaves/A.json']}
    # Model an older observer's unchanged source snapshot before this upgrade.
    pub.atomic(mirror.directory(root) / 'mirror-state.json',
               {'source_hash': 'legacy-hash', 'seq': 4})
    state = mirror.capture(root)
    origin = state['pending']['document']['plan_origin']
    assert state['seq'] == 5
    assert origin['source'] == 'file_birthtime'
    assert all(p.read_bytes() == content for p, content in sources.items())
    assert archive.read_bytes() == original
    mirror.capture(root, reason='Новая ревизия')
    assert pending(root)['revisions'][1]['document']['plan_origin'] == origin
    assert archive.read_bytes() == original


def test_mcp_native_create_has_same_automatic_creation(tmp_path):
    import lhc_plan_mcp as mcp
    root = plan(tmp_path)
    response = mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                          'params': {'name': 'create_leaf', 'arguments': {
                              'plan_dir': str(root), 'leaf': {'id': 'A', 'label': 'Через MCP'}}}})
    assert 'error' not in response, response
    assert not response['result']['isError'], response
    native = json.loads((root / 'leaves/A.json').read_text())
    assert leaves.origin_time(native['created_at']) is not None
    assert leaves.build_document(root)['plan_origin']['at'] == native['created_at']
