"""A native upgrade may prune old roots while running chats retain their hooks."""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/plugin-autoupdate/install-codex-plugin.py'
spec = importlib.util.spec_from_file_location('lhc_native_install', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@pytest.fixture
def roots(tmp_path):
    cache = tmp_path / 'cache/last-human-commit'
    for version in ('1.6.2', '1.6.3', '1.6.4'):
        (cache / version / 'tools').mkdir(parents=True)
    source = tmp_path / 'official/plugins/last-human-commit/tools'
    source.mkdir(parents=True)
    for name in installer.compat.REQUIRED:
        (source / name).write_text('# canonical hook\n')
    (source.parent / 'plugin.json').write_text(json.dumps({'name': 'last-human-commit'}))
    return cache, source


@pytest.mark.parametrize('native_status', [0, 9])
def test_native_pruning_restores_old_hooks_even_on_failure(roots, tmp_path, native_status):
    cache, source = roots
    log = tmp_path / 'native-calls.jsonl'
    native = tmp_path / 'fake-codex'
    native.write_text('#!/usr/bin/env python3\nimport json, pathlib, shutil, sys\n'
                      f'cache=pathlib.Path({str(cache)!r})\n'
                      f'with open({str(log)!r}, "a") as log: log.write(json.dumps(sys.argv[1:])+"\\n")\n'
                      'shutil.rmtree(cache)\n(cache / "1.6.5/tools").mkdir(parents=True)\n'
                      f'raise SystemExit({native_status})\n')
    native.chmod(0o700)
    assert installer.install(str(native), cache, source) == native_status
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        ['plugin', 'add', 'last-human-commit@megamen32-plugins', '--json']]
    for version in ('1.6.2', '1.6.3', '1.6.4'):
        assert (cache / version / 'tools/lhc_progress_review.py').read_text() == '# canonical hook\n'
        assert (cache / version / 'tools').is_symlink()
    assert (cache / '1.6.5/tools').is_dir() and not (cache / '1.6.5/tools').is_symlink()


def test_invalid_source_never_invokes_native_manager(roots, tmp_path):
    cache, source = roots
    (source / 'lhc_entry.py').unlink()
    with pytest.raises(ValueError):
        installer.install(str(tmp_path / 'must-not-run'), cache, source)
    assert not (cache / '1.6.2/tools').is_symlink()


def test_source_inside_prunable_cache_is_not_a_stable_repair_target(roots, tmp_path):
    cache, source = roots
    import shutil
    unstable = cache / '1.6.5/tools'
    shutil.copytree(source.parent, unstable.parent)
    with pytest.raises(ValueError, match='outside the native cache'):
        installer.install(str(tmp_path / 'must-not-run'), cache, unstable)


def test_partial_pruning_restores_newer_target_before_preserved_alias(roots, tmp_path):
    import shutil
    cache, source = roots
    for version in ('1.6.2', '1.6.4'):
        shutil.copytree(source.parent, cache / version, dirs_exist_ok=True)
    alias = cache / '1.6.3/tools'
    alias.rmdir()
    alias.symlink_to(cache / '1.6.4/tools')
    native = tmp_path / 'partially-pruning-codex'
    native.write_text('#!/usr/bin/env python3\nimport pathlib, shutil\n'
                      f'cache=pathlib.Path({str(cache)!r})\n'
                      'shutil.rmtree(cache / "1.6.4")\n'
                      '(cache / "1.6.5/tools").mkdir(parents=True)\n')
    native.chmod(0o700)
    assert installer.install(str(native), cache, source) == 0
    assert alias.is_symlink() and alias.readlink() == cache / '1.6.4/tools'
    assert (alias / 'lhc_progress_review.py').read_text() == '# canonical hook\n'


def test_versions_pruned_before_the_installer_ran_come_back_from_the_record(roots, tmp_path):
    import shutil
    cache, source = roots
    shutil.rmtree(cache)                      # the marketplace upgrade already pruned 1.6.2-1.6.4
    shutil.copytree(source.parent, cache / '1.6.5')
    record = tmp_path / 'state/lhc/codex-plugin-versions.json'
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps(['1.6.2', '1.6.3', '1.6.4']))
    log = tmp_path / 'calls.jsonl'
    native = tmp_path / 'fake-codex'
    native.write_text('#!/usr/bin/env python3\nimport json, sys\n'
                      f'open({str(log)!r}, "a").write(json.dumps(sys.argv[1:])+"\\n")\n')
    native.chmod(0o700)
    assert installer.install(str(native), cache, source, upgrade_marketplace=True, record=record) == 0
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        ['plugin', 'marketplace', 'upgrade', 'megamen32-plugins'],
        ['plugin', 'add', 'last-human-commit@megamen32-plugins', '--json']]
    for version in ('1.6.2', '1.6.3', '1.6.4'):
        assert (cache / version / 'tools/lhc_entry.py').read_text() == '# canonical hook\n'
    assert json.loads(record.read_text()) == ['1.6.2', '1.6.3', '1.6.4', '1.6.5']


def test_a_broken_record_is_ignored_not_fatal(roots, tmp_path):
    import shutil
    cache, source = roots
    for version in ('1.6.2', '1.6.3', '1.6.4'):
        shutil.copytree(source.parent, cache / version, dirs_exist_ok=True)
    record = tmp_path / 'record.json'
    record.write_text('{not json')
    native = tmp_path / 'noop-codex'
    native.write_text('#!/bin/sh\nexit 0\n')
    native.chmod(0o700)
    assert installer.install(str(native), cache, source, record=record) == 0
    assert json.loads(record.read_text()) == ['1.6.2', '1.6.3', '1.6.4']
