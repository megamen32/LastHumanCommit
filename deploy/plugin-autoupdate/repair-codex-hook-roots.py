#!/usr/bin/env python3
"""Explicit compatibility routes for native hooks retaining old plugin roots.

This does not install old plugin versions. It creates only absent tools links;
existing package contents and links are never replaced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

REQUIRED = ('lhc_progress_review.py', 'lhc_time_guard.py', 'lhc_entry.py')
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?')


def validate_tools(tools: Path) -> Path:
    tools = tools.expanduser().resolve(strict=True)
    if not tools.is_dir() or not all((tools / name).is_file() for name in REQUIRED):
        raise ValueError('tools root lacks required LHC hook tools')
    manifests = [tools.parent / '.codex-plugin/plugin.json', tools.parent / 'plugin.json']
    identified = False
    for path in manifests:
        try:
            manifest = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict) and manifest.get('name') == 'last-human-commit':
            identified = True
    if not identified:
        raise ValueError('tools root is not an identified last-human-commit package')
    return tools


def existing_result(version: str, target: Path) -> dict:
    try:
        validate_tools(target)
        status = 'preserved'
    except (OSError, ValueError, TypeError):
        status = 'conflict'
    return {'version': version, 'path': str(target), 'status': status}


def repair(cache_root: Path, tools_root: Path, versions: list[str]) -> list[dict]:
    # Validate every argument before the first filesystem mutation.
    if not versions or any(not VERSION.fullmatch(value) for value in versions):
        raise ValueError('version must be an explicit semantic version without a path')
    source = validate_tools(tools_root)
    cache = cache_root.expanduser().resolve()
    if cache.name != 'last-human-commit':
        raise ValueError('cache root must name the last-human-commit package')
    cache.mkdir(parents=True, exist_ok=True)
    results = []
    for version in dict.fromkeys(versions):
        package = cache / version
        target = package / 'tools'
        if package.is_symlink() or (package.exists() and not package.is_dir()):
            results.append({'version': version, 'path': str(target), 'status': 'conflict'})
            continue
        if target.exists() or target.is_symlink():
            results.append(existing_result(version, target))
            continue
        package.mkdir(exist_ok=True)
        try:
            target.symlink_to(source, target_is_directory=True)
            results.append({'version': version, 'path': str(target), 'status': 'created',
                            'tools_root': str(source)})
        except FileExistsError:
            results.append(existing_result(version, target))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', type=Path, required=True)
    parser.add_argument('--tools-root', type=Path, required=True)
    parser.add_argument('--version', action='append', required=True)
    args = parser.parse_args(argv)
    try:
        results = repair(args.cache_root, args.tools_root, args.version)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f'LHC compatibility repair: {error}\n')
    print(json.dumps({'compatibility_only': True, 'versions': results}, ensure_ascii=False))
    return int(any(item['status'] == 'conflict' for item in results))


if __name__ == '__main__':
    raise SystemExit(main())
