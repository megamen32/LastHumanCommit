"""Quiet plans must not be reread, reregistered or resent every polling tick."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_plan_mirror as mirror


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize('edit,constant_stamp', [(False, False), (True, False), (True, True)])
def test_quiet_observer_reuses_file_bytes_registration_and_durable_ack(tmp_path, monkeypatch, edit, constant_stamp):
    plan = tmp_path / 'plan'
    write(plan / 'plan.json', {})
    write(plan / 'leaves/A.json', {'id': 'A', 'label': 'Work', 'status': 'queued'})
    dest = mirror.directory(plan)
    write(dest / 'state.json', {'identity': 'identity'})
    write(dest / 'mirror.json', {'owner': 'owner'})
    write(dest / 'mirror-state.json', {'seq': 1, 'pending': {'identity': 'identity'},
                                     'source_hash': mirror.fingerprint(plan),
                                     'server_receipt': {'seq': 1, 'identity': 'identity'}})
    config = tmp_path / 'config.json'
    write(config, {'data_dir': str(tmp_path / 'client'), 'plans': [str(plan)], 'poll_seconds': 1})
    counts = {'register': 0, 'source_read': 0, 'state_read': 0, 'sync': 0}
    delivered_at = []
    if constant_stamp:
        monkeypatch.setattr(mirror, 'source_stamp', lambda plan: ('unchanged-filesystem-stamp',))
    read_bytes, read = Path.read_bytes, mirror.read
    def counted_bytes(path):
        if path == plan / 'leaves/A.json':
            counts['source_read'] += 1
        return read_bytes(path)
    def counted_read(path, default=None):
        if Path(path) == dest / 'mirror-state.json':
            counts['state_read'] += 1
        return read(path, default)
    monkeypatch.setattr(Path, 'read_bytes', counted_bytes)
    monkeypatch.setattr(mirror, 'read', counted_read)
    def register(*args):
        counts['register'] += 1
    def sync(*args):
        counts['sync'] += 1
        delivered_at.append(tick[0])
        state = mirror.read(dest / 'mirror-state.json')
        state['server_receipt'] = {'seq': state['seq'], 'identity': 'identity'}
        write(dest / 'mirror-state.json', state)
    def capture(*args):
        state = mirror.read(dest / 'mirror-state.json')
        source_hash = mirror.fingerprint(plan)
        if state['source_hash'] != source_hash:
            state.update(seq=state['seq'] + 1, source_hash=source_hash)
            write(dest / 'mirror-state.json', state)
        return state
    monkeypatch.setattr(mirror, 'register', register)
    monkeypatch.setattr(mirror, 'sync', sync)
    monkeypatch.setattr(mirror, 'capture', capture)
    tick = [0]
    class Finished(Exception):
        pass
    def sleep(_):
        tick[0] += 3
        if edit and tick[0] == 9:
            write(plan / 'leaves/A.json', {'id': 'A', 'label': 'Edit', 'status': 'queued'})
        if tick[0] >= 75:
            raise Finished()
    monkeypatch.setattr(mirror.time, 'monotonic', lambda: tick[0])
    monkeypatch.setattr(mirror.time, 'sleep', sleep)
    with pytest.raises(Finished):
        mirror.run_observer(config)
    assert counts['register'] == 1, counts
    assert counts['source_read'] <= (8 if edit else 5), counts
    assert counts['state_read'] <= (7 if edit else 3), counts
    assert counts['sync'] == int(edit), counts
    if edit:
        assert 30 <= delivered_at[0] <= 36 if constant_stamp else delivered_at[0] < 30


def test_repeated_identical_error_does_not_rewrite_state(tmp_path, monkeypatch):
    writes = []
    atomic = mirror.pub.atomic
    def save(path, value):
        writes.append(path)
        return atomic(path, value)
    monkeypatch.setattr(mirror.pub, 'atomic', save)
    mirror.record_error(tmp_path, OSError('offline'))
    mirror.record_error(tmp_path, OSError('still offline'))
    assert len(writes) == 1
