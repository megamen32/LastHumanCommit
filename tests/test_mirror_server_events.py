"""Linux events keep replica reads proportional to changed files, not history size."""
import copy
import json
from pathlib import Path
import sys
import subprocess

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_plan_mirror as mirror
from test_mirror_server_perf import entry


def indexed(tmp_path, count=100):
    data, web = tmp_path / 'data', tmp_path / 'web'
    data.mkdir()
    web.mkdir()
    for i in range(count):
        value = entry()
        value['snapshot'].update(identity=f'id{i}', name=f'plan{i}', owner='owner')
        (data / f'id{i}.json').write_text(json.dumps(value))
    return mirror.Replica({'data_dir': str(data), 'webroot': str(web), 'base_url': 'https://lhc.test'})


@pytest.mark.parametrize('count', [100, 1000])
def test_unchanged_index_has_no_per_history_stat_glob_or_read(tmp_path, monkeypatch, count):
    service = indexed(tmp_path, count)
    service.entries()
    original_stat, original_glob, original_read = Path.stat, Path.glob, mirror.read
    def stat(path, *args, **kwargs):
        assert path.parent != service.data
        return original_stat(path, *args, **kwargs)
    def glob(path, *args, **kwargs):
        assert path != service.data
        return original_glob(path, *args, **kwargs)
    def read(path, *args, **kwargs):
        assert Path(path).parent != service.data
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', stat)
    monkeypatch.setattr(Path, 'glob', glob)
    monkeypatch.setattr(mirror, 'read', read)
    for _ in range(3):
        assert len(service.entries()) == count
        service.dashboard()


def test_one_changed_history_reads_only_that_file_and_inplace_is_immediate(tmp_path, monkeypatch):
    service = indexed(tmp_path)
    service.entries()
    original, calls = mirror.read, []
    def read(path, *args, **kwargs):
        calls.append(Path(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', read)
    path = service.data / 'id7.json'
    value = original(path)
    value['snapshot']['document']['title'] = 'Next'
    path.write_text(json.dumps(value))
    values = service.entries()
    assert next(e for e in values if e['snapshot']['identity'] == 'id7')['snapshot']['document']['title'] == 'Next'
    assert calls == [path]


def test_new_project_legacy_and_atomic_replacement(tmp_path):
    service = indexed(tmp_path, 1)
    assert service.legacy() == []
    page = Path(service.cfg['webroot']) / 'new-project' / 'old-plan' / 'index.html'
    page.parent.mkdir(parents=True)
    page.write_text('<title>Old</title>')
    assert service.legacy() == [('new-project', 'old-plan', 'Old')]
    replacement = page.with_name('replacement')
    replacement.write_text('<title>New</title>')
    replacement.replace(page)
    assert service.legacy() == [('new-project', 'old-plan', 'New')]


def test_second_replica_cannot_claim_existing_url(tmp_path, monkeypatch):
    first = indexed(tmp_path, 0)
    second = mirror.Replica(first.cfg)
    monkeypatch.setattr(mirror, 'validate_snapshot', lambda value: value)
    monkeypatch.setattr(mirror.Replica, 'render', lambda self, entry: None)
    value = entry()['snapshot']
    value.update(owner='one', seq=1, observed={})
    first.ingest(copy.deepcopy(value))
    value.update(identity='another', owner='two')
    with pytest.raises(mirror.Conflict):
        second.ingest(value)


def test_ingest_checks_one_identity_instead_of_reading_all_histories(tmp_path, monkeypatch):
    service = indexed(tmp_path)
    monkeypatch.setattr(mirror, 'validate_snapshot', lambda value: value)
    monkeypatch.setattr(mirror.Replica, 'render', lambda self, entry: None)
    original, calls = mirror.read, []
    def counted(path, *args, **kwargs):
        calls.append(Path(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', counted)
    value = entry()['snapshot']
    value.update(identity='incoming', name='incoming', owner='owner', seq=1, observed={})
    service.ingest(value)
    assert calls == [service.data / 'incoming.json']


def test_cross_process_atomic_owner_update_invalidates_route_index(tmp_path, monkeypatch):
    service = indexed(tmp_path, 0)
    value = entry()
    value['snapshot'].update(owner='outside', seq=1, observed={})
    subprocess.run([sys.executable, '-c',
                    'import sys; from pathlib import Path; Path(sys.argv[1]).write_text(sys.argv[2])',
                    str(service.data / 'identity.json'), json.dumps(value)], check=True)
    monkeypatch.setattr(mirror, 'validate_snapshot', lambda value: value)
    monkeypatch.setattr(mirror.Replica, 'render', lambda self, entry: None)
    incoming = copy.deepcopy(value['snapshot'])
    incoming.update(identity='intruder', owner='different')
    with pytest.raises(mirror.Conflict):
        service.ingest(incoming)


def test_active_summaries_refresh_each_minute_inactive_only_on_source_event(tmp_path, monkeypatch):
    service = indexed(tmp_path, 2)
    path = service.data / 'id0.json'
    value = mirror.read(path)
    value['snapshot']['document']['tasks'][0]['status'] = 'done'
    path.write_text(json.dumps(value))
    tick, calls = [0.0], []
    original = mirror.catalog.summarize
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    def summarize(entry, now):
        calls.append(entry['snapshot']['identity'])
        return original(entry, now)
    monkeypatch.setattr(mirror.catalog, 'summarize', summarize)
    first = service.dashboard()
    assert calls.count('id0') == calls.count('id1') == 1
    tick[0] = 59.9
    assert service.dashboard() == first
    assert len(calls) == 2
    tick[0] = 60.0
    service.dashboard()
    assert calls.count('id0') == 1
    assert calls.count('id1') == 2
    value['snapshot']['document']['title'] = 'Changed completed plan'
    path.write_text(json.dumps(value))
    assert 'Changed completed plan' in service.dashboard()
    assert calls.count('id0') == 2


def test_overflow_reconciles_once_then_unchanged_reads_stay_in_memory(tmp_path, monkeypatch):
    from lhc_file_events import FileChanges
    service = indexed(tmp_path)
    original, calls = mirror.read, []
    def counted(path, *args, **kwargs):
        calls.append(Path(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(mirror, 'read', counted)
    monkeypatch.setattr(service.events, 'poll', lambda timeout=0: FileChanges(set(), True))
    assert len(service.entries()) == 100
    assert len(calls) == 100
    service.entries()
    assert len(calls) == 100


def test_legacy_symlink_inplace_atomic_file_and_target_replacement(tmp_path):
    service = indexed(tmp_path, 0)
    project = service.webroot / 'legacy'
    bundle = project / '.old.bundle'
    bundle.mkdir(parents=True)
    page = bundle / 'index.html'
    page.write_text('<title>First</title>')
    logical = project / 'plan'
    logical.symlink_to(bundle, target_is_directory=True)
    assert service.legacy() == [('legacy', 'plan', 'First')]
    page.write_text('<title>In place</title>')
    assert service.legacy() == [('legacy', 'plan', 'In place')]
    replacement = bundle / 'replacement'
    replacement.write_text('<title>Atomic file</title>')
    replacement.replace(page)
    assert service.legacy() == [('legacy', 'plan', 'Atomic file')]
    other = project / '.new.bundle'
    other.mkdir()
    (other / 'index.html').write_text('<title>Retarget</title>')
    temporary = project / '.new-link'
    temporary.symlink_to(other, target_is_directory=True)
    temporary.replace(logical)
    assert service.legacy() == [('legacy', 'plan', 'Retarget')]
    (other / 'index.html').write_text('<title>Retarget edit</title>')
    assert service.legacy() == [('legacy', 'plan', 'Retarget edit')]


@pytest.mark.parametrize('root_name', ['data', 'webroot'])
def test_root_move_preserves_last_good_and_rearms_after_bounded_recovery(tmp_path, monkeypatch, root_name):
    service = indexed(tmp_path, 1)
    page = service.webroot / 'legacy' / 'plan' / 'index.html'
    page.parent.mkdir(parents=True)
    page.write_text('<title>Before</title>')
    assert len(service.entries()) == 1
    assert service.legacy() == [('legacy', 'plan', 'Before')]
    root = getattr(service, root_name)
    moved = root.with_name(root.name + '-moved')
    root.rename(moved)
    # Missing roots are temporary coverage failures, not deletion of all plans.
    assert len(service.entries()) == 1
    assert service.legacy() == [('legacy', 'plan', 'Before')]
    now = service.last_reconcile
    def no_scan(*args, **kwargs):
        raise AssertionError('missing roots must not trigger a scan on every GET')
    with monkeypatch.context() as bounded:
        bounded.setattr(Path, 'glob', no_scan)
        bounded.setattr(Path, 'iterdir', no_scan)
        for _ in range(3):
            assert len(service.entries()) == 1
            service.dashboard()
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: now + 31)
    moved.rename(root)
    service.entries()
    assert service.events.available
    if root_name == 'data':
        path = service.data / 'id0.json'
        value = mirror.read(path)
        value['snapshot']['document']['title'] = 'After recovery'
        path.write_text(json.dumps(value))
        assert service.entries()[0]['snapshot']['document']['title'] == 'After recovery'
    else:
        page.write_text('<title>After recovery</title>')
        assert service.legacy() == [('legacy', 'plan', 'After recovery')]


@pytest.mark.parametrize('root_name', ['data', 'webroot'])
def test_root_replaced_before_poll_rearms_new_directory(tmp_path, root_name):
    service = indexed(tmp_path, 0)
    root = getattr(service, root_name)
    root.rename(root.with_name(root.name + '-old'))
    root.mkdir()
    service.entries()
    assert service.events.available
    if root_name == 'data':
        value = entry()
        (root / 'identity.json').write_text(json.dumps(value))
        assert len(service.entries()) == 1
    else:
        page = root / 'legacy' / 'plan' / 'index.html'
        page.parent.mkdir(parents=True)
        page.write_text('<title>Recreated</title>')
        assert service.legacy() == [('legacy', 'plan', 'Recreated')]
