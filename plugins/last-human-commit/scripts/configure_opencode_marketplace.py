#!/usr/bin/env python3
"""Point OpenCode at the stable native LHC marketplace checkout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile


class InstallationError(RuntimeError):
    pass


def _json_file(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallationError(f"Cannot safely update OpenCode config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InstallationError(f"OpenCode config must be a JSON object: {path}")
    return value


def _is_lhc_fleet_pointer(value: object, tail: str) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.replace("\\", "/")
    return "/agent-harness-fleet/plugin-rollout/" in normalized and normalized.endswith("/" + tail)


def _backup(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = backup_dir / f"{stamp}-{path.name}"
    shutil.copy2(path, target, follow_symlinks=True)
    return target


def _atomic_text(path: Path, payload: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _atomic_json(path: Path, value: dict, mode: int = 0o600) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", mode)


def configure(home: Path, package_root: Path) -> dict:
    home = home.expanduser().resolve()
    package_root = package_root.expanduser().resolve()
    manifest_path = package_root / "plugin.json"
    agents_path = package_root / "AGENTS.md"
    skills_path = package_root / "skills"
    plugin_source = package_root / "opencode/lhc-v2.ts"
    for required in (manifest_path, agents_path, skills_path / "last-human-commit/SKILL.md", plugin_source):
        if not required.is_file():
            raise InstallationError(f"Marketplace LHC package is incomplete: {required}")
    try:
        version = str(json.loads(manifest_path.read_text(encoding="utf-8"))["version"])
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise InstallationError(f"Cannot read the LHC package version: {manifest_path}") from exc

    config_path = home / ".config/opencode/opencode.json"
    config = _json_file(config_path)
    updated = dict(config)

    instructions = updated.get("instructions", [])
    if isinstance(instructions, str):
        instructions = [instructions]
    if not isinstance(instructions, list) or any(not isinstance(item, str) for item in instructions):
        raise InstallationError("OpenCode instructions must be a list of paths")
    next_instructions = [item for item in instructions if not _is_lhc_fleet_pointer(item, "AGENTS.md")]
    agents_text = str(agents_path)
    if agents_text not in next_instructions:
        next_instructions.append(agents_text)
    updated["instructions"] = next_instructions

    skills = updated.get("skills", {"paths": []})
    if isinstance(skills, dict):
        skill_paths = skills.get("paths", [])
        if not isinstance(skill_paths, list) or any(not isinstance(item, str) for item in skill_paths):
            raise InstallationError("OpenCode skills.paths must be a list of paths")
        next_skill_paths = [item for item in skill_paths if not _is_lhc_fleet_pointer(item, "skills")]
        skills_text = str(skills_path)
        if skills_text not in next_skill_paths:
            next_skill_paths.append(skills_text)
        next_skills = dict(skills)
        next_skills["paths"] = next_skill_paths
    elif isinstance(skills, list) and all(isinstance(item, str) for item in skills):
        next_skills = [item for item in skills if not _is_lhc_fleet_pointer(item, "skills")]
        skills_text = str(skills_path)
        if skills_text not in next_skills:
            next_skills.append(skills_text)
    else:
        raise InstallationError("OpenCode skills must be an array or an object with paths")
    updated["skills"] = next_skills

    plugin_dirs = (home / ".config/opencode/plugins", home / ".config/opencode/plugin")
    old_plugins: list[Path] = []
    for directory in plugin_dirs:
        candidate = directory / "last-human-commit.ts"
        if candidate.exists() or candidate.is_symlink():
            try:
                body = candidate.read_text(encoding="utf-8")
                resolved = str(candidate.resolve())
            except (OSError, UnicodeError) as exc:
                raise InstallationError(f"Cannot inspect existing LHC plugin {candidate}: {exc}") from exc
            known_fleet_link = (
                candidate.is_symlink()
                and "/agent-harness-fleet/plugin-rollout/" in resolved.replace("\\", "/")
                and resolved.endswith("/opencode/lhc-v2.ts")
            )
            known_lhc_copy = body == plugin_source.read_text(encoding="utf-8")
            known_fleet_wrapper = (
                "lhc-v2.ts" in body
                and "agent-harness-fleet/plugin-rollout/" in body.replace("\\", "/")
            )
            if not (known_fleet_link or known_lhc_copy or known_fleet_wrapper or resolved == str(plugin_source)):
                raise InstallationError(f"Refusing to replace an unrecognized plugin file: {candidate}")
            if resolved != str(plugin_source):
                old_plugins.append(candidate)

    plugin_dir = home / ".config/opencode/plugins"
    target_plugin = plugin_dir / "last-human-commit.ts"
    if target_plugin.is_symlink() and target_plugin.resolve() == plugin_source:
        replace_plugin = False
    else:
        if target_plugin.exists() and target_plugin not in old_plugins:
            raise InstallationError(f"Refusing to replace an unrecognized plugin file: {target_plugin}")
        replace_plugin = True

    state_path = home / ".local/state/last-human-commit/opencode.json"
    state = {}
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InstallationError(f"Cannot safely update LHC OpenCode state {state_path}: {exc}") from exc
        if not isinstance(state, dict):
            raise InstallationError(f"LHC OpenCode state must be a JSON object: {state_path}")
    new_state = dict(state)
    new_state.update({
        "packageRoot": str(package_root),
        "pluginDir": str(plugin_dir),
        "pluginFiles": {"lhc-v2.ts": str(target_plugin)},
    })

    backup_dir = home / ".local/state/last-human-commit/backups"
    backups = []
    changed = updated != config or new_state != state or replace_plugin or bool(old_plugins)
    if not changed:
        return {"version": version, "changed": False, "packageRoot": str(package_root)}

    if new_state != state:
        new_state["registeredAt"] = state.get("registeredAt") or datetime.now(timezone.utc).isoformat()

    if updated != config and config_path.exists():
        backups.append(str(_backup(config_path, backup_dir)))
    if state_path.is_file() and new_state != state:
        backups.append(str(_backup(state_path, backup_dir)))
    for old in old_plugins:
        backups.append(str(_backup(old, backup_dir)))

    if updated != config:
        mode = config_path.stat().st_mode & 0o777 if config_path.exists() else 0o600
        _atomic_json(config_path, updated, mode)

    plugin_dir.mkdir(parents=True, exist_ok=True)
    if replace_plugin:
        target_plugin.unlink(missing_ok=True)
        target_plugin.symlink_to(plugin_source)
    for old in old_plugins:
        if old != target_plugin:
            old.unlink(missing_ok=True)

    _atomic_json(state_path, new_state)
    return {
        "version": version,
        "changed": True,
        "packageRoot": str(package_root),
        "plugin": str(target_plugin),
        "instructions": str(agents_path),
        "skills": str(skills_path),
        "backups": backups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    try:
        print(json.dumps(configure(args.home, args.package_root), ensure_ascii=False))
        return 0
    except (OSError, InstallationError, ValueError) as exc:
        print(f"OpenCode LHC marketplace setup failed: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
