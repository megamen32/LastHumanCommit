#!/usr/bin/env python3
"""Validate package manifests, skill discovery, and optional source parity."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from sync_skills import compare, default_source_root, source_skill_dirs


SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_SKILLS = {
    "bugfix-tdd",
    "business-delivery",
    "feature-implementation",
    "lhc-rollout",
    "lhc-update-agents",
    "planning",
    "real-use-testing",
    "release",
    "task-decomposition",
    "worker-bugfix",
    "worker-code",
    "worker-research",
}


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON object required at {path}")
    return value


def check_no_symlinks(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"symlink is not allowed in package: {path}")


def check_version_parity(root: Path) -> None:
    versions = {}
    for rel in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        path = root / rel
        if path.is_file():
            versions[rel] = str(load_json(path).get("version"))
    unique = set(versions.values())
    if len(unique) > 1:
        raise ValidationError(f"manifest versions drifted: {versions}")
    if len(versions) < 2:
        raise ValidationError("expected at least root and one projection manifest")


def check_root_manifest(root: Path) -> None:
    path = root / "plugin.json"
    manifest = load_json(path)
    allowed = {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
    unexpected = set(manifest) - allowed
    if unexpected:
        raise ValidationError(f"root manifest has unsupported fields: {sorted(unexpected)}")
    if manifest.get("$schema") != SCHEMA:
        raise ValidationError("root manifest has the wrong $schema")
    name = manifest.get("name")
    if not isinstance(name, str) or len(name) == 0 or len(name) > 64 or not NAME.fullmatch(name):
        raise ValidationError("root manifest has an invalid name")
    for field in ("version", "description", "homepage", "repository", "license"):
        if field in manifest and not isinstance(manifest[field], str):
            raise ValidationError(f"root manifest field {field!r} must be a string")
    if "keywords" in manifest and (
        not isinstance(manifest["keywords"], list)
        or not all(isinstance(item, str) for item in manifest["keywords"])
    ):
        raise ValidationError("root manifest keywords must be an array of strings")
    if "author" in manifest:
        author = manifest["author"]
        if not isinstance(author, dict) or set(author) - {"name", "email", "url"}:
            raise ValidationError("root manifest author must contain only name, email, and url")
        if not all(isinstance(value, str) for value in author.values()):
            raise ValidationError("root manifest author values must be strings")
    if "extensions" in manifest:
        extensions = manifest["extensions"]
        if not isinstance(extensions, dict) or not all(isinstance(value, dict) for value in extensions.values()):
            raise ValidationError("root manifest extensions must map names to objects")


def resolve_package_path(root: Path, raw: object, field: str) -> Path:
    if not isinstance(raw, str) or not raw.startswith("./"):
        raise ValidationError(f"{field} must be a ./ relative path")
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValidationError(f"{field} escapes the package root")
    if not candidate.is_dir():
        raise ValidationError(f"{field} does not point to a directory: {candidate}")
    return candidate


def check_native_manifest(root: Path, relative: str, label: str) -> Path:
    manifest = load_json(root / relative)
    if manifest.get("name") != "last-human-commit":
        raise ValidationError(f"{label} manifest has the wrong name")
    for field in ("version", "description"):
        if field in manifest and not isinstance(manifest[field], str):
            raise ValidationError(f"{label} manifest field {field!r} must be a string")
    return resolve_package_path(root, manifest.get("skills"), f"{label}.skills")


def parse_skill_name(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 5 or lines[0].strip() != "---":
        raise ValidationError(f"skill lacks frontmatter: {path}")
    frontmatter: dict[str, str] = {}
    for line in lines[1:30]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    if not frontmatter.get("name") or not frontmatter.get("description"):
        raise ValidationError(f"skill frontmatter needs name and description: {path}")
    return frontmatter["name"]


def discover_skills(root: Path) -> set[str]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        raise ValidationError(f"skills directory is missing: {skills_root}")
    discovered: set[str] = set()
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir() or child.is_symlink():
            continue
        if not SKILL_NAME.fullmatch(child.name):
            raise ValidationError(f"invalid skill directory name: {child.name}")
        skill_file = child / "SKILL.md"
        if not skill_file.is_file() or skill_file.is_symlink():
            raise ValidationError(f"skill directory lacks regular SKILL.md: {child}")
        if parse_skill_name(skill_file) != child.name:
            raise ValidationError(f"skill frontmatter name does not match directory: {child.name}")
        discovered.add(child.name)
    if discovered != EXPECTED_SKILLS:
        raise ValidationError(f"skills discovered: expected {sorted(EXPECTED_SKILLS)}, got {sorted(discovered)}")
    return discovered


def check_parity(root: Path, source_root: Path | None) -> str:
    if source_root is None or not source_root.is_dir():
        return "SKIP (source tree unavailable)"
    errors = compare(source_root, root / "skills")
    if errors:
        raise ValidationError("; ".join(errors))
    return f"PASS ({len(source_skill_dirs(source_root))} skills)"


def check_opencode_helper(root: Path) -> None:
    helper = root / "scripts" / "opencode-config.py"
    if not helper.is_file():
        raise ValidationError(f"OpenCode helper is missing: {helper}")
    for output_format, expected in (
        ("native", {"paths": [str(root / "skills")]}),
        ("v2", [str(root / "skills")]),
    ):
        completed = subprocess.run(
            [sys.executable, str(helper), "--plugin-root", str(root), "--format", output_format],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ValidationError(f"OpenCode helper failed in {output_format} format")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"OpenCode helper returned invalid JSON in {output_format} format") from exc
        if payload.get("skills") != expected:
            raise ValidationError(f"OpenCode helper returned the wrong skills shape in {output_format} format")
        if payload.get("plugin") != [str(root / "opencode" / "lhc-time-guard.ts")]:
            raise ValidationError("OpenCode helper does not point to the LHC time-guard adapter")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-root", type=Path, default=None)
    args = parser.parse_args()
    root = args.plugin_root.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve() if args.source_root else default_source_root()
    try:
        check_no_symlinks(root)
        check_version_parity(root)
        check_root_manifest(root)
        codex_skills = check_native_manifest(root, ".codex-plugin/plugin.json", "Codex")
        claude_skills = check_native_manifest(root, ".claude-plugin/plugin.json", "Claude Code")
        discovered = discover_skills(root)
        if codex_skills != root / "skills" or claude_skills != root / "skills":
            raise ValidationError("native manifests do not point to the package skills directory")
        parity = check_parity(root, source_root if source_root.is_dir() else None)
        check_opencode_helper(root)
        print(f"plugin validation: PASS skills={len(discovered)} parity={parity}")
        return 0
    except (OSError, ValidationError, ValueError) as exc:
        print(f"plugin validation: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
