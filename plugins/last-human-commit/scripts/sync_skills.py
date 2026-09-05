#!/usr/bin/env python3
"""Project common factory skills into native skills, then synchronize the plugin."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXCLUDED_PARTS = {"__pycache__"}


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def package_files(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not (set(path.relative_to(root).parts) & EXCLUDED_PARTS)
        and path.suffix != ".pyc"
    }


def sync_tree(source: Path, target: Path, check: bool, replacements: dict[bytes, bytes] | None = None) -> list[str]:
    replacements = replacements or {}
    if source.is_file():
        expected = {Path(source.name): source.read_bytes()}
    else:
        expected = package_files(source)
    actual = package_files(target) if target.is_dir() else {}
    errors: list[str] = []
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"unexpected bundled file: {target.name}/{relative}")
    for relative, content in expected.items():
        for old, new in replacements.items():
            content = content.replace(old, new)
        output = target if source.is_file() else target / relative
        if check:
            if output.is_symlink() or not output.is_file() or output.read_bytes() != content:
                errors.append(f"bundled file differs: {target.name}/{relative}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
    return errors


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


def project_common_skills(common_root: Path, native_root: Path, check: bool) -> list[str]:
    """Make factory skills self-contained without changing existing native skills.

    Canonical factory content lives in common/skills. Native packages carry the
    routing example beside its skill, since they have no surrounding common tree.
    """
    errors: list[str] = []
    for source_dir in source_skill_dirs(common_root / "skills"):
        files = {
            path.relative_to(source_dir): path.read_bytes()
            for path in source_dir.rglob("*") if path.is_file()
        }
        if source_dir.name == "model-routing":
            files[Path("SKILL.md")] = files[Path("SKILL.md")].replace(
                b"../../config/model-routing.example.json",
                b"references/model-routing.example.json",
            )
            files[Path("references/model-routing.example.json")] = (
                common_root / "config/model-routing.example.json"
            ).read_bytes()
        target = native_root / source_dir.name
        actual = {path.relative_to(target) for path in target.rglob("*") if path.is_file()}
        for relative in sorted(actual - set(files)):
            errors.append(f"unexpected native factory file: {source_dir.name}/{relative}")
        for relative, content in files.items():
            output = target / relative
            if check:
                if output.is_symlink() or not output.is_file() or output.read_bytes() != content:
                    errors.append(f"native factory skill differs: {source_dir.name}/{relative}")
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(content)
    return errors


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
        target_dir = output_root / source_dir.name
        source_files = {
            path.relative_to(source_dir).as_posix(): path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
        }
        target_files = {
            path.relative_to(target_dir).as_posix(): path
            for path in target_dir.rglob("*")
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
        } if target_dir.is_dir() else {}
        missing = sorted(set(source_files) - set(target_files))
        unexpected = sorted(set(target_files) - set(source_files))
        for relative in missing:
            errors.append(f"missing generated skill file: {source_dir.name}/{relative}")
        for relative in sorted(set(source_files) & set(target_files)):
            if target_files[relative].is_symlink() or (
                target_files[relative].read_bytes() != source_files[relative].read_bytes()
            ):
                errors.append(f"generated skill differs from source: {source_dir.name}/{relative}")
        if unexpected:
            errors.append(f"unexpected generated files in {source_dir.name}: {unexpected}")
    return errors


def sync(source_root: Path, output_root: Path) -> int:
    source_dirs = source_skill_dirs(source_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for source_dir in source_dirs:
        target_dir = output_root / source_dir.name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
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
        if source_root == default_source_root().resolve():
            projection_errors = project_common_skills(
                plugin_root().parent.parent / "src/common", source_root, args.check,
            )
            if projection_errors:
                for error in projection_errors:
                    print(f"projection error: {error}", file=sys.stderr)
                return 1
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
        common_root = plugin_root().parent.parent / "src" / "common"
        bundle_errors = sync_tree(common_root, plugin_root() / "common", args.check,
                                  {b"src/common/": b"common/"})
        bundle_errors += sync_tree(plugin_root().parent.parent / "AGENTS.md", plugin_root() / "AGENTS.md", args.check,
                                   {b"src/common/": b"common/"})
        bundle_errors += sync_tree(plugin_root().parent.parent / "adapters" / "hermes" / "plugin",
                                   plugin_root() / "com.nousresearch.hermes", args.check)
        if bundle_errors:
            for error in bundle_errors:
                print(f"bundle error: {error}", file=sys.stderr)
            return 1
        if args.check:
            print(f"parity: PASS ({len(source_skill_dirs(source_root))} skills)")
            return 0
        return sync(source_root, output_root)
    except (OSError, ValueError) as exc:
        print(f"sync error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
