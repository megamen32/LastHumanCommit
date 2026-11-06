#!/usr/bin/env python3
"""Install LHC once through native Codex and preserve old hook tool routes."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

spec = importlib.util.spec_from_file_location('lhc_hook_root_repair', Path(__file__).with_name('repair-codex-hook-roots.py'))
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


def version_order(value: str) -> tuple:
    core, _, prerelease = value.split('+', 1)[0].partition('-')
    identifiers = tuple((0, int(part)) if part.isdigit() else (1, part)
                        for part in prerelease.split('.')) if prerelease else ()
    return (*map(int, core.split('.')), not bool(prerelease), identifiers)


def load_record(record) -> list[str]:
    """Every LHC version this host had in the Codex cache; open chats may still use them."""
    try:
        data = json.loads(Path(record).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return []
    return [str(item) for item in data if isinstance(item, str) and compat.VERSION.fullmatch(item)] \
        if isinstance(data, list) else []


def save_record(record, versions) -> None:
    path = Path(record)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(sorted(set(versions), key=version_order), indent=1) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    except OSError as error:
        print(f'LHC: could not save the list of installed versions: {error}', file=sys.stderr)


def install(codex_bin: str, cache_root: Path, tools_root: Path, *,
            upgrade_marketplace: bool = False, record=None) -> int:
    tools = compat.validate_tools(tools_root)
    cache = cache_root.expanduser().resolve()
    if cache.name != 'last-human-commit':
        raise ValueError('cache root must name the last-human-commit package')
    if cache == tools or cache in tools.parents:
        raise ValueError('tools root must be outside the native cache pruned by upgrades')
    # A retained older tools alias may target a newer version's pruned root.
    versions = sorted((path.name for path in cache.iterdir()
                       if compat.VERSION.fullmatch(path.name) and path.is_dir()),
                      key=version_order, reverse=True) if cache.exists() else []
    # `codex plugin marketplace upgrade` (also Codex's own auto-upgrade) installs the new version
    # and prunes the old ones before this script runs, so the cache alone forgets them: the
    # record keeps every version seen here, and all of them get their hook route back.
    if record is not None:
        versions = sorted(set(versions) | set(load_record(record)), key=version_order, reverse=True)
    status = 1
    # The marketplace upgrade replaces its checkout. Codex run from inside it (the updater
    # cds there) then has no working directory and fails «failed to load configuration».
    home = str(Path.home())
    try:
        if upgrade_marketplace:
            refreshed = subprocess.run([codex_bin, 'plugin', 'marketplace', 'upgrade', 'megamen32-plugins'],
                                       check=False, cwd=home).returncode
            if refreshed != 0:
                print(f'LHC: marketplace upgrade exited {refreshed}; installing from the current checkout',
                      file=sys.stderr)
        # Native manager remains the installer; no retry after any result.
        status = subprocess.run([codex_bin, 'plugin', 'add',
                                 'last-human-commit@megamen32-plugins', '--json'], check=False, cwd=home).returncode
    except OSError as error:
        print(f'LHC native install unavailable: {error}', file=sys.stderr)
        status = 127
    finally:
        try:
            results = compat.repair(cache, tools, versions) if versions else []
            print(json.dumps({'compatibility_only': True, 'versions': results}, ensure_ascii=False), file=sys.stderr)
            if any(item['status'] == 'conflict' for item in results) and status == 0:
                status = 1
        except (OSError, ValueError, TypeError) as error:
            print(f'LHC hook compatibility repair failed: {error}', file=sys.stderr)
            if status == 0:
                status = 1
        if record is not None and cache.exists():
            save_record(record, [*versions, *(path.name for path in cache.iterdir()
                                              if compat.VERSION.fullmatch(path.name) and path.is_dir())])
    return status


def main(argv=None):
    codex_home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-bin', default='codex')
    parser.add_argument('--cache-root', type=Path,
                        default=codex_home / 'plugins/cache/megamen32-plugins/last-human-commit')
    parser.add_argument('--tools-root', type=Path,
                        default=codex_home / '.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/tools')
    parser.add_argument('--upgrade-marketplace', action='store_true',
                        help='refresh the megamen32-plugins marketplace first (it prunes old versions; their routes come back)')
    parser.add_argument('--record', type=Path,
                        default=Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')
                        / 'lhc/codex-plugin-versions.json')
    args = parser.parse_args(argv)
    try:
        return install(args.codex_bin, args.cache_root, args.tools_root,
                       upgrade_marketplace=args.upgrade_marketplace, record=args.record)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f'LHC native install preflight: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
