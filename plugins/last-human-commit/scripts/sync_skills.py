#!/usr/bin/env python3
"""Synchronize the plugin's generated skills from the repository source tree."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_source_root() -> Path:
    return plugin_root().parent.parent / "skills"


def source_skill_dirs(source_root: Path) -> list[Path]:
    if not source_root.is_dir():
        raise ValueError(f"source skills directory does not exist: {source_root}")
    result = []
    for path in sorted(source_root.iterdir()):
        if not path.is_dir() or path.is_symlink():
            continue
        if not SKILL_NAME.fullmatch(path.name):
            raise ValueError(f"invalid skill directory name: {path.name}")
        source_file = path / "SKILL.md"
        if not source_file.is_file() or source_file.is_symlink():
            raise ValueError(f"missing regular SKILL.md: {source_file}")
        result.append(path)
    if not result:
        raise ValueError(f"no source skills found under {source_root}")
    return result


def compare(source_root: Path, output_root: Path) -> list[str]:
    source_dirs = source_skill_dirs(source_root)
    expected = {path.name for path in source_dirs}
    actual = {
        path.name
        for path in output_root.iterdir()
        if path.is_dir() and not path.is_symlink()
    } if output_root.is_dir() else set()
    errors: list[str] = []
    if expected != actual:
        errors.append(f"skill directories differ: expected {sorted(expected)}, got {sorted(actual)}")
    for source_dir in source_dirs:
        target_file = output_root / source_dir.name / "SKILL.md"
        source_file = source_dir / "SKILL.md"
        if not target_file.is_file() or target_file.is_symlink():
            errors.append(f"missing generated skill: {target_file}")
            continue
        if target_file.read_bytes() != source_file.read_bytes():
            errors.append(f"generated skill differs from source: {source_dir.name}")
        unexpected = [
            path.relative_to(target_file.parent).as_posix()
            for path in target_file.parent.rglob("*")
            if path.name != "SKILL.md"
        ]
        if unexpected:
            errors.append(f"unexpected generated files in {source_dir.name}: {unexpected}")
    return errors


def sync(source_root: Path, output_root: Path) -> int:
    source_dirs = source_skill_dirs(source_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for source_dir in source_dirs:
        target_dir = output_root / source_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_dir / "SKILL.md", target_dir / "SKILL.md", follow_symlinks=False)
    errors = compare(source_root, output_root)
    if errors:
        for error in errors:
            print(f"sync error: {error}", file=sys.stderr)
        return 1
    print(f"synced {len(source_dirs)} skills into {output_root}")
    return 0


def sync_tool(source: Path, output: Path, check: bool) -> list[str]:
    """Keep the package's executable guard identical to its canonical source."""

    if check:
        return [] if output.is_file() and output.read_bytes() == source.read_bytes() else [
            f"generated time guard differs from source: {output}"
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output, follow_symlinks=False)
    output.chmod(source.stat().st_mode)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=default_source_root())
    parser.add_argument("--output-root", type=Path, default=plugin_root() / "skills")
    parser.add_argument("--check", action="store_true", help="check parity without changing files")
    args = parser.parse_args()
    try:
        source_root = args.source_root.expanduser().resolve()
        output_root = args.output_root.expanduser().resolve()
        tool_errors = sync_tool(
            plugin_root().parent.parent / "src" / "common" / "tools" / "lhc_time_guard.py",
            plugin_root() / "tools" / "lhc_time_guard.py",
            args.check,
        )
        if tool_errors:
            for error in tool_errors:
                print(f"parity error: {error}", file=sys.stderr)
            return 1
        if args.check:
            errors = compare(source_root, output_root)
            if errors:
                for error in errors:
                    print(f"parity error: {error}", file=sys.stderr)
                return 1
            print(f"parity: PASS ({len(source_skill_dirs(source_root))} skills)")
            return 0
        return sync(source_root, output_root)
    except (OSError, ValueError) as exc:
        print(f"sync error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
