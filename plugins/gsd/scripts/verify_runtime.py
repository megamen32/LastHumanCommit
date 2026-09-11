#!/usr/bin/env python3
"""Verify GSD replacement across Codex, OpenCode, and optional ZCode."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, timeout=45)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.plugin_root.expanduser().resolve()
    home = Path.home()
    report: dict[str, object] = {"pluginRoot": str(root)}
    failures: list[str] = []

    codex = run("codex", "plugin", "list")
    gsd_line = next((x for x in codex.stdout.splitlines() if x.startswith("gsd@megamen32-plugins")), "")
    lhc_line = next((x for x in codex.stdout.splitlines() if x.startswith("last-human-commit@megamen32-plugins")), "")
    report["codex"] = {"gsd": gsd_line, "lhc": lhc_line}
    if "installed, enabled" not in gsd_line or "not installed" not in lhc_line:
        failures.append("codex registration")
    if len(list((root / "skills").glob("*/SKILL.md"))) != 67:
        failures.append("plugin skill count")
    if run("node", str(root / "bin/gsd-sdk.js"), "--help").returncode:
        failures.append("bundled SDK")

    opencode_cfg = home / ".config/opencode/opencode.json"
    if opencode_cfg.exists():
        cfg_text = opencode_cfg.read_text()
        cfg = json.loads(cfg_text)
        paths = cfg.get("skills", {}).get("paths", [])
        plugins = cfg.get("plugin", [])
        config_ok = (
            str(root / "skills") in paths
            and str(root / "opencode-plugin/index.js") in plugins
            and "last-human-commit" not in cfg_text
        )
        try:
            with tempfile.TemporaryFile(mode="w+") as output:
                skill_result = subprocess.run(
                    ["opencode", "debug", "skill"],
                    stdout=output,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=45,
                )
                output.seek(0)
                skill_data = json.load(output)
            if skill_result.returncode:
                raise RuntimeError(skill_result.stderr)
            gsd_count = sum(str(item.get("name", "")).startswith("gsd-") for item in skill_data)
        except Exception:
            gsd_count = -1
        report["opencode"] = {"configured": config_ok, "gsdSkills": gsd_count}
        if not config_ok or gsd_count != 67:
            failures.append("opencode loader")
    else:
        report["opencode"] = {"configured": False}
        failures.append("opencode config missing")

    zcode_cfg = home / ".zcode/cli/config.json"
    zcode_cli = shutil.which("zcode")
    zcode_report: dict[str, object] = {"cli": zcode_cli or "absent", "configured": False}
    if zcode_cfg.exists():
        cfg_text = zcode_cfg.read_text()
        cfg = json.loads(cfg_text)
        dirs = cfg.get("plugins", {}).get("dirs", [])
        zcode_report["configured"] = str(root) in dirs and "last-human-commit" not in cfg_text
        if not zcode_report["configured"]:
            failures.append("zcode config")
    if zcode_cli:
        listing = run(zcode_cli, "plugins", "list").stdout
        zcode_report["loader"] = "gsd@inline" in listing and "last-human-commit@" not in listing
        if not zcode_report["loader"]:
            failures.append("zcode loader")
    report["zcode"] = zcode_report

    marker_files = [home / ".codex/AGENTS.md", home / ".zcode/AGENTS.md", home / ".config/opencode/AGENTS.md"]
    report["lhcMarkersRemaining"] = [str(p) for p in marker_files if p.exists() and "last-human-commit" in p.read_text()]
    if report["lhcMarkersRemaining"]:
        failures.append("LHC AGENTS markers")
    report["lhcCodexCacheExists"] = (home / ".codex/plugins/cache/megamen32-plugins/last-human-commit").exists()
    if report["lhcCodexCacheExists"]:
        failures.append("LHC Codex cache")
    report["failures"] = failures
    print(json.dumps(report, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
