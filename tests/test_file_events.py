"""Real kernel events for plan edits, including atomic and same-mtime saves."""
import fcntl
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_file_events as events


@pytest.fixture
def watcher():
    with events.FileEvents() as source:
        if not source.available:
            pytest.skip('inotify unavailable on this platform')
        yield source


def test_same_size_same_mtime_and_atomic_save(watcher, tmp_path):
    target = tmp_path / 'plan.json'
    target.write_text('old')
    stamp = target.stat().st_mtime_ns
    assert watcher.add(tmp_path)
    target.write_text('new')
    os.utime(target, ns=(stamp, stamp))
    assert target in watcher.poll(0.2).paths
    staged = tmp_path / 'plan.tmp'
    staged.write_text('end')
    staged.replace(target)
    changes = watcher.poll(0.2)
    assert {staged, target} <= changes.paths
    assert not changes.overflow
    assert not watcher.poll().paths


def test_reading_is_quiet_and_watch_is_deduplicated(watcher, tmp_path):
    target = tmp_path / 'plan.json'
    target.write_text('data')
    assert watcher.add(tmp_path)
    assert watcher.add(tmp_path / '.')
    assert len(watcher._dirs) == 1
    assert target.read_text() == 'data'
    assert not watcher.poll().paths


def test_directory_create_rename_delete_and_self_removal(watcher, tmp_path):
    assert watcher.add(tmp_path)
    child = tmp_path / 'leaves'
    child.mkdir()
    assert child in watcher.poll(0.2).paths
    assert watcher.add(child)
    moved = tmp_path / 'renamed'
    child.rename(moved)
    assert {child, moved} <= watcher.poll(0.2).paths
    moved.rmdir()
    changes = watcher.poll(0.2)
    assert moved in changes.paths
    assert child not in watcher._paths  # IN_IGNORED clears the self watch.


def test_fd_flags_and_context_cleanup():
    with events.FileEvents() as watcher:
        if not watcher.available:
            pytest.skip('inotify unavailable')
        fd = watcher._fd
        assert fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_NONBLOCK
        assert fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
    with pytest.raises(OSError):
        os.fstat(fd)
    watcher.close()


def test_missing_directory_and_file_disable_coverage(tmp_path):
    for path in (tmp_path / 'missing', tmp_path / 'file'):
        if path.name == 'file':
            path.write_text('data')
        with events.FileEvents() as watcher:
            assert not watcher.add(path)
            assert not watcher.available
            assert watcher.poll().overflow


def test_overflow_reported_without_synthetic_path(watcher, monkeypatch):
    packet = events._HEADER.pack(-1, events._IN_Q_OVERFLOW, 0, 0)
    chunks = iter([packet])
    monkeypatch.setattr(events.select, 'select', lambda *args: ([watcher._fd], [], []))
    def read(*args):
        try:
            return next(chunks)
        except StopIteration:
            raise BlockingIOError()
    monkeypatch.setattr(events.os, 'read', read)
    changes = watcher.poll()
    assert changes.overflow
    assert not changes.paths


def test_nonlinux_uses_explicit_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(events.sys, 'platform', 'darwin')
    with events.FileEvents() as watcher:
        assert not watcher.available
        assert not watcher.add(tmp_path)
        assert watcher.poll().overflow


def test_watch_limit_failure_closes_fd_and_requires_fallback(watcher, tmp_path):
    fd = watcher._fd
    # The native call returns -1 for ENOSPC (and other add failures).
    watcher._libc = SimpleNamespace(inotify_add_watch=lambda *args: -1)
    assert not watcher.add(tmp_path)
    assert not watcher.available
    assert watcher.poll().overflow
    with pytest.raises(OSError):
        os.fstat(fd)
