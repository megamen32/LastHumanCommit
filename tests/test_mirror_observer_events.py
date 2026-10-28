"""Native events leave quiet archives untouched and reconcile changed sources."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_plan_mirror as mirror
import lhc_file_events as events


@pytest.mark.parametrize('change', ['quiet', 'edit', 'new', 'overflow'])
def test_event_observer_processes_only_affected_plans(tmp_path, monkeypatch, change):
    root = tmp_path / 'plans'
    plans = []
    def create(name):
        plan = root / name
        (plan / 'leaves').mkdir(parents=True)
        (plan / 'plan.json').write_text('{}')
        (plan / 'leaves/A.json').write_text('{"id":"A","label":"Done","status":"done"}')
        dest = mirror.directory(plan)
        dest.mkdir()
        (dest / 'mirror-state.json').write_text(json.dumps({'seq': 1, 'pending': {'identity': name, 'document': {'tasks': [{'status': 'done'}]}}, 'server_receipt': {'seq': 1, 'identity': name}}))
        return str(plan)
    for index in range(105):
        plans.append(create(str(index)))
    cfg = tmp_path / 'client.json'
    cfg.write_text(json.dumps({'data_dir': str(tmp_path / 'client'), 'roots': [str(root)], 'poll_seconds': .1, 'debounce_seconds': .05}))
    tick = [0]
    captures, registrations, stamps = [], [], []
    stamp = mirror.file_stamp
    def counted_stamp(path):
        stamps.append((tick[0], Path(path)))
        return stamp(path)
    monkeypatch.setattr(mirror, 'file_stamp', counted_stamp)
    monkeypatch.setattr(mirror, 'register', lambda plan, cfg: registrations.append(plan))
    monkeypatch.setattr(mirror, 'capture', lambda plan: captures.append(plan))
    monkeypatch.setattr(mirror, 'sync', lambda *args: pytest.fail('durable acknowledged snapshot must not be resent'))
    class FakeEvents:
        available = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add(self, path): return True
        def poll(self, timeout=0):
            paths, overflow = set(), False
            if tick[0] == 3:
                if change == 'edit': paths = {Path(plans[0]) / 'leaves/A.json'}
                elif change == 'new': paths = {Path(create('new-plan'))}
                elif change == 'overflow': overflow = True
            return SimpleNamespace(paths=paths, overflow=overflow)
    monkeypatch.setattr(events, 'FileEvents', FakeEvents)
    class Finished(Exception): pass
    def sleep(_):
        tick[0] += 1
        if tick[0] >= 8: raise Finished()
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.time, 'sleep', sleep)
    with pytest.raises(Finished): mirror.run_observer(cfg)
    if change == 'quiet':
        assert len(captures) == len(plans)
        assert not [path for at, path in stamps if at >= 2]
    elif change == 'edit':
        assert captures.count(plans[0]) == 2
        assert all(captures.count(plan) == 1 for plan in plans[1:])
    elif change == 'new':
        assert len(captures) == 106 and str(root / 'new-plan') in captures
    else:
        assert all(captures.count(plan) == 2 for plan in plans)
    assert len(registrations) == 106 if change == 'new' else len(registrations) in (105, 210)


@pytest.mark.parametrize('status,interval', [('queued', 60), ('done', 300)])
def test_unavailable_events_use_deadlines_without_reconciling_every_tick(tmp_path, monkeypatch, status, interval):
    plan = tmp_path / 'plan'
    (plan / 'leaves').mkdir(parents=True)
    (plan / 'plan.json').write_text('{}')
    (plan / 'leaves/A.json').write_text('{"status":"done"}')
    dest = mirror.directory(plan)
    dest.mkdir()
    (dest / 'mirror-state.json').write_text(json.dumps({'seq': 1, 'pending': {
        'identity': 'done', 'document': {'tasks': [{'status': status}]}},
        'server_receipt': {'seq': 1, 'identity': 'done'}}))
    cfg = tmp_path / 'client.json'
    cfg.write_text(json.dumps({'data_dir': str(tmp_path / 'client'), 'plans': [str(plan)],
                               'poll_seconds': 1, 'debounce_seconds': .05}))
    tick, discoveries, captures, signatures = [0], [], [], []
    discover = mirror.discover
    monkeypatch.setattr(mirror, 'discover', lambda cfg: (discoveries.append(tick[0]) or discover(cfg)))
    monkeypatch.setattr(mirror, 'capture', lambda plan: captures.append(tick[0]))
    monkeypatch.setattr(mirror, 'register', lambda *args: None)
    monkeypatch.setattr(mirror, 'source_stamp', lambda plan: (signatures.append(tick[0]) or ('same',)))
    class Unavailable:
        available = False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add(self, path): return False
        def poll(self, timeout=0): return SimpleNamespace(paths=set(), overflow=True)
    monkeypatch.setattr(events, 'FileEvents', Unavailable)
    class Finished(Exception): pass
    def sleep(_):
        tick[0] += 1
        if tick[0] >= 310: raise Finished()
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.time, 'sleep', sleep)
    with pytest.raises(Finished): mirror.run_observer(cfg)
    assert len(captures) == 1
    assert len(discoveries) <= 7
    assert signatures == list(range(1, 310, interval)), 'source checks respect active/archive deadlines'


def test_recreated_leaves_directory_is_watched_again(tmp_path, monkeypatch):
    plan = tmp_path / 'plan'
    leaves = plan / 'leaves'
    leaves.mkdir(parents=True)
    (plan / 'plan.json').write_text('{}')
    leaf = leaves / 'A.json'
    leaf.write_text('{"status":"done"}')
    cfg = tmp_path / 'client.json'
    cfg.write_text(json.dumps({'data_dir': str(tmp_path / 'client'), 'plans': [str(plan)],
                               'poll_seconds': 1, 'debounce_seconds': .05}))
    tick, captures, covered = [0], [], set()
    monkeypatch.setattr(mirror, 'register', lambda *args: None)
    monkeypatch.setattr(mirror, 'capture', lambda plan: captures.append(tick[0]))
    class ReplacedDirectory:
        available = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add(self, path):
            covered.add(Path(path))
            return True
        def poll(self, timeout=0):
            if tick[0] == 3:
                leaf.unlink()
                leaves.rmdir()
                covered.discard(leaves)  # IN_IGNORED removes the old inode watch.
                return SimpleNamespace(paths={leaves}, overflow=False)
            if tick[0] == 5:
                leaves.mkdir()
                leaf.write_text('{"status":"done"}')
                return SimpleNamespace(paths={leaves}, overflow=False)
            if tick[0] == 8:
                leaf.write_text('{"status":"queued"}')
                return SimpleNamespace(paths={leaf} if leaves in covered else set(), overflow=False)
            return SimpleNamespace(paths=set(), overflow=False)
    monkeypatch.setattr(events, 'FileEvents', ReplacedDirectory)
    class Finished(Exception): pass
    def sleep(_):
        tick[0] += 1
        if tick[0] >= 11: raise Finished()
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.time, 'sleep', sleep)
    with pytest.raises(Finished): mirror.run_observer(cfg)
    assert leaves in covered
    assert 9 in captures, 'later edits in the replacement directory must arrive'
