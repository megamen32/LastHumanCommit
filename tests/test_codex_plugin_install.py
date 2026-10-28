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
