"""Compatibility repair preserves real packages and foreign paths."""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/plugin-autoupdate/repair-codex-hook-roots.py'
spec = importlib.util.spec_from_file_location('hook_root_repair', SCRIPT)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


@pytest.fixture
def roots(tmp_path):
    cache = tmp_path / 'cache/last-human-commit'
    source = tmp_path / 'official-marketplace/plugins/last-human-commit/tools'
    source.mkdir(parents=True)
    for name in repair.REQUIRED:
        (source / name).write_text('# canonical tool\n')
    (source.parent / 'plugin.json').write_text(json.dumps({'name': 'last-human-commit'}))
    return cache, source


def test_missing_root_is_compatibility_link_and_idempotent(roots):
    cache, source = roots
    result = repair.repair(cache, source, ['1.6.2'])
    assert result[0]['status'] == 'created'
    target = cache / '1.6.2/tools'
    assert target.is_symlink() and target.resolve() == source
    assert not (target.parent / 'plugin.json').exists()
    before = target.lstat().st_mtime_ns
    assert repair.repair(cache, source, ['1.6.2'])[0]['status'] == 'preserved'
    assert target.lstat().st_mtime_ns == before


@pytest.mark.parametrize('kind', ['directory', 'symlink', 'file'])
def test_foreign_existing_path_is_preserved_and_reported_conflict(roots, tmp_path, kind):
    cache, source = roots
    target = cache / '1.6.2/tools'
    target.parent.mkdir(parents=True)
    if kind == 'directory':
        target.mkdir()
        (target / 'foreign').write_text('preserve')
    elif kind == 'symlink':
        target.symlink_to(tmp_path / 'foreign-missing')
    else:
        target.write_text('preserve')
    before = target.lstat()
    assert repair.repair(cache, source, ['1.6.2'])[0]['status'] == 'conflict'
    assert target.lstat() == before


@pytest.mark.parametrize('version', ['../escape', '/absolute', '1.6.2/../../escape', '', '1.6'])
def test_invalid_version_never_mutates_cache(roots, version):
    cache, source = roots
    with pytest.raises(ValueError):
        repair.repair(cache, source, [version])
    assert not cache.exists()


def test_unidentified_source_and_version_symlink_are_rejected(roots, tmp_path):
    cache, source = roots
    manifest = source.parent / 'plugin.json'
    manifest.write_text('{"name":"other"}')
    with pytest.raises(ValueError):
        repair.repair(cache, source, ['1.6.2'])
    assert not cache.exists()
    manifest.write_text('{"name":"last-human-commit"}')
    cache.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (cache / '1.6.2').symlink_to(outside)
    assert repair.repair(cache, source, ['1.6.2'])[0]['status'] == 'conflict'
    assert not (outside / 'tools').exists()
