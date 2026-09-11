#!/usr/bin/env python3
"""Wire this portable Agent Plugin into OpenCode and/or ZCode."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"expected a JSON object: {path}")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def backup(path: Path, backup_root: Path, home: Path) -> str | None:
    if not path.exists():
        return None
    try:
        relative = path.relative_to(home)
    except ValueError:
        relative = Path(path.name)
    target = backup_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return str(target)


def configure_opencode(plugin_root: Path, home: Path) -> Path:
    path = home / ".config" / "opencode" / "opencode.json"
    data = load_json(path)
    shim = str(plugin_root / "opencode-plugin" / "index.js")
    plugins = list(data.get("plugin", []))
    if shim not in plugins:
        plugins.append(shim)
    data["plugin"] = plugins

    skills = data.get("skills", {})
    if not isinstance(skills, dict):
        raise SystemExit(f"expected skills to be a JSON object: {path}")
    skill_path = str(plugin_root / "skills")
    paths = list(skills.get("paths", []))
    if skill_path not in paths:
        paths.append(skill_path)
    skills["paths"] = paths
    data["skills"] = skills
    write_json(path, data)
    return path


def configure_zcode(plugin_root: Path, home: Path) -> Path:
    path = home / ".zcode" / "cli" / "config.json"
    data = load_json(path)
    plugins = data.get("plugins", {})
    if not isinstance(plugins, dict):
        raise SystemExit(f"expected plugins to be a JSON object: {path}")

    root = str(plugin_root)
    dirs = list(plugins.get("dirs", []))
    if root not in dirs:
        dirs.append(root)
    plugins["dirs"] = dirs

    enabled = plugins.get("enabledPlugins", {})
    if not isinstance(enabled, dict):
        raise SystemExit(f"expected enabledPlugins to be a JSON object: {path}")
    enabled["gsd@inline"] = True
    plugins["enabledPlugins"] = enabled
    data["plugins"] = plugins
    write_json(path, data)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Stable checkout path (defaults to this repository).",
    )
    parser.add_argument(
        "--runtime", choices=("opencode", "zcode", "all"), default="all"
    )
    parser.add_argument("--backup-root", type=Path)
    args = parser.parse_args()

    plugin_root = args.plugin_root.expanduser().resolve()
    if not (plugin_root / "plugin.json").is_file():
        raise SystemExit(f"invalid plugin root: {plugin_root}")
    if not (plugin_root / "skills").is_dir():
        raise SystemExit(f"missing skills directory: {plugin_root / 'skills'}")

    home = Path.home()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = (
        args.backup_root or home / ".local" / "state" / "gsd-agent-plugin" / stamp
    ).expanduser()
    selected = ["opencode", "zcode"] if args.runtime == "all" else [args.runtime]
    paths = {
        "opencode": home / ".config" / "opencode" / "opencode.json",
        "zcode": home / ".zcode" / "cli" / "config.json",
    }
    backups = {
        runtime: saved
        for runtime in selected
        if (saved := backup(paths[runtime], backup_root, home)) is not None
    }

    configured = []
    for runtime in selected:
        if runtime == "opencode":
            configure_opencode(plugin_root, home)
        else:
            configure_zcode(plugin_root, home)
        configured.append(runtime)

    print(
        json.dumps(
            {
                "pluginRoot": str(plugin_root),
                "configured": configured,
                "backups": backups,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
