#!/usr/bin/env python3
"""Replace LHC runtime wiring with one installed GSD Agent Plugin root."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


LHC_MARKER = re.compile(
    r"\n?<!-- last-human-commit:begin -->.*?<!-- last-human-commit:end -->\n?",
    re.DOTALL,
)


def backup(path: Path, root: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    target = root / path.relative_to(Path.home())
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir() and not path.is_symlink():
        shutil.copytree(path, target, dirs_exist_ok=True)
    elif path.is_symlink():
        target.write_text(f"SYMLINK -> {path.readlink()}\n")
    else:
        shutil.copy2(path, target)


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path)
    args = parser.parse_args()

    plugin_root = args.plugin_root.expanduser().resolve()
    if not (plugin_root / "plugin.json").is_file():
        raise SystemExit(f"invalid plugin root: {plugin_root}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = (args.backup_root or Path.home() / ".local/state/gsd-plugin-migration" / stamp).expanduser()
    backup_root.mkdir(parents=True, exist_ok=True)

    agent_files = [
        Path.home() / ".codex/AGENTS.md",
        Path.home() / ".zcode/AGENTS.md",
        Path.home() / ".config/opencode/AGENTS.md",
    ]
    opencode = Path.home() / ".config/opencode/opencode.json"
    zcode = Path.home() / ".zcode/cli/config.json"
    zcode_installed = Path.home() / ".zcode/cli/plugins/installed_plugins.json"
    launcher = Path.home() / ".local/bin/gsd-sdk"
    codex_config = Path.home() / ".codex/config.toml"
    codex_lhc_cache = Path.home() / ".codex/plugins/cache/megamen32-plugins/last-human-commit"
    candidates = agent_files + [
        codex_config,
        codex_lhc_cache,
        opencode,
        zcode,
        zcode_installed,
        launcher,
    ]
    for path in candidates:
        backup(path, backup_root)

    for path in agent_files:
        if path.exists():
            path.write_text(LHC_MARKER.sub("\n", path.read_text()).lstrip("\n"))

    if opencode.exists():
        data = json.loads(opencode.read_text())
        opencode_shim = str(plugin_root / "opencode-plugin/index.js")
        plugins = [
            x
            for x in data.get("plugin", [])
            if "last-human-commit" not in str(x)
            and "@megamen32/gsd-opencode-plugin" not in str(x)
            and not ("/gsd/" in str(x) and "opencode-plugin" in str(x))
        ]
        if opencode_shim not in plugins:
            plugins.append(opencode_shim)
        data["plugin"] = plugins
        skills = data.setdefault("skills", {})
        paths = [x for x in skills.get("paths", []) if "last-human-commit" not in str(x)]
        gsd_skills = str(plugin_root / "skills")
        if gsd_skills not in paths:
            paths.append(gsd_skills)
        skills["paths"] = paths
        write_json(opencode, data)

    if zcode.exists():
        data = json.loads(zcode.read_text())
        plugins = data.setdefault("plugins", {})
        dirs = [x for x in plugins.get("dirs", []) if "last-human-commit" not in str(x)]
        if str(plugin_root) not in dirs:
            dirs.append(str(plugin_root))
        plugins["dirs"] = dirs
        enabled = plugins.setdefault("enabledPlugins", {})
        for key in list(enabled):
            if "last-human-commit" in key:
                del enabled[key]
        enabled["gsd@inline"] = True
        write_json(zcode, data)

    stale_install_paths: list[Path] = []
    if zcode_installed.exists():
        data = json.loads(zcode_installed.read_text())
        kept = []
        for entry in data.get("plugins", []):
            if "last-human-commit" in str(entry.get("id", "")) or entry.get("name") == "last-human-commit":
                install_path = entry.get("installPath")
                if install_path:
                    stale_install_paths.append(Path(install_path))
                continue
            kept.append(entry)
        data["plugins"] = kept
        write_json(zcode_installed, data)

    stale_install_paths.extend([
        Path.home() / ".zcode/cli/plugins/data/last-human-commit@inline",
        Path.home() / ".zcode/cli/plugins/data/last-human-commit@last-human-commit",
    ])
    for path in stale_install_paths:
        if path.exists():
            backup(path, backup_root)
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    launcher.parent.mkdir(parents=True, exist_ok=True)
    if launcher.exists() or launcher.is_symlink():
        launcher.unlink()
    launcher.symlink_to(plugin_root / "bin/gsd-sdk.js")

    print(json.dumps({
        "pluginRoot": str(plugin_root),
        "backupRoot": str(backup_root),
        "opencodeConfigured": opencode.exists(),
        "zcodeConfigured": zcode.exists(),
        "launcher": str(launcher),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
