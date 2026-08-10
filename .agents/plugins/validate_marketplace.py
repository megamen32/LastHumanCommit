#!/usr/bin/env python3
"""Validate the repository marketplace and its local plugin entries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
INSTALLATION_POLICIES = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
AUTH_POLICIES = {"ON_INSTALL", "ON_USE"}


class ValidationError(ValueError):
    pass


def read_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON object required at {path}")
    return value


def package_path(repo_root: Path, source_path: object, plugin_name: str) -> Path:
    if not isinstance(source_path, str) or not source_path.startswith("./"):
        raise ValidationError(f"{plugin_name}: source.path must start with ./")
    candidate = (repo_root / source_path).resolve()
    root = repo_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValidationError(f"{plugin_name}: source.path escapes the repository")
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValidationError(f"{plugin_name}: source directory is missing or symlinked")
    return candidate


def validate_marketplace(repo_root: Path, marketplace_path: Path) -> int:
    marketplace = read_object(marketplace_path)
    if set(marketplace) - {"name", "interface", "plugins"}:
        raise ValidationError("marketplace contains unsupported top-level fields")
    name = marketplace.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValidationError("marketplace name must be lowercase kebab-case")
    interface = marketplace.get("interface")
    if not isinstance(interface, dict) or not isinstance(interface.get("displayName"), str):
        raise ValidationError("marketplace.interface.displayName is required")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("marketplace.plugins must be a non-empty array")

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValidationError(f"plugins[{index}] must be an object")
        plugin_name = entry.get("name")
        if not isinstance(plugin_name, str) or not NAME.fullmatch(plugin_name):
            raise ValidationError(f"plugins[{index}].name is invalid")
        if plugin_name in seen:
            raise ValidationError(f"duplicate plugin entry: {plugin_name}")
        seen.add(plugin_name)

        source = entry.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            raise ValidationError(f"{plugin_name}: only local source entries are supported in this catalog")
        package = package_path(repo_root, source.get("path"), plugin_name)
        manifest_path = package / ".codex-plugin" / "plugin.json"
        manifest = read_object(manifest_path)
        if manifest.get("name") != plugin_name:
            raise ValidationError(f"{plugin_name}: package manifest name does not match marketplace entry")

        policy = entry.get("policy")
        if not isinstance(policy, dict):
            raise ValidationError(f"{plugin_name}: policy is required")
        if policy.get("installation") not in INSTALLATION_POLICIES:
            raise ValidationError(f"{plugin_name}: invalid installation policy")
        if policy.get("authentication") not in AUTH_POLICIES:
            raise ValidationError(f"{plugin_name}: invalid authentication policy")
        if not isinstance(entry.get("category"), str) or not entry["category"]:
            raise ValidationError(f"{plugin_name}: category is required")

    print(f"marketplace validation: PASS entries={len(seen)} name={name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=Path(__file__).resolve().parent / "marketplace.json",
    )
    args = parser.parse_args()
    try:
        return validate_marketplace(args.repo_root.expanduser().resolve(), args.marketplace.expanduser().resolve())
    except (OSError, ValidationError, ValueError) as exc:
        print(f"marketplace validation: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
