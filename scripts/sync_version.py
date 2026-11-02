#!/usr/bin/env python3
"""Write the root VERSION into every file of this repository that repeats it.

VERSION is the only place a release number is typed. The manifests, the plan MCP
server and the README repeat it; this script rewrites them, and --check fails when
one disagrees (CI runs it). Generated copies under plugins/ come from
scripts/publish_package.py, run it afterwards.

    python3 scripts/sync_version.py            # rewrite
    python3 scripts/sync_version.py --check    # report drift, exit 1
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "plugins/last-human-commit"
JSON_MANIFESTS = (
    f"{PLUGIN}/plugin.json",
    f"{PLUGIN}/.codex-plugin/plugin.json",
    f"{PLUGIN}/.claude-plugin/plugin.json",
    f"{PLUGIN}/native/codex/.codex-plugin/plugin.json",
    f"{PLUGIN}/.zcode-plugin/plugin.json",
)
YAML_MANIFESTS = (
    f"{PLUGIN}/plugin.yaml",
    f"{PLUGIN}/com.nousresearch.hermes/plugin.yaml",
    "adapters/hermes/plugin/plugin.yaml",
)
SERVER = "src/common/tools/lhc_plan_mcp.py"
README = "README.md"
SEMVER = r"\d+\.\d+\.\d+"


def rules(version: str):
    """(path, pattern, replacement) triples; each pattern must match exactly once."""
    out = []
    for path in JSON_MANIFESTS:
        out.append((path, rf'("version"\s*:\s*")({SEMVER})(")', rf"\g<1>{version}\g<3>"))
    for path in YAML_MANIFESTS:
        out.append((path, rf"(?m)^(version:\s*)({SEMVER})(\s*)$", rf"\g<1>{version}\g<3>"))
    out.append((SERVER, rf'(SERVER_VERSION\s*=\s*")({SEMVER})(")', rf"\g<1>{version}\g<3>"))
    out.append((README, rf"(## File-backed bug register \()({SEMVER})(\))", rf"\g<1>{version}\g<3>"))
    out.append((README, rf"(`{PLUGIN}`, version )({SEMVER})(,)", rf"\g<1>{version}\g<3>"))
    return out


def marketplace(version: str, write: bool) -> list[str]:
    """The last-human-commit entry of the marketplace file (other plugins keep their own versions)."""
    path = ROOT / ".claude-plugin/marketplace.json"
    text = path.read_text(encoding="utf-8")
    pattern = rf'("name"\s*:\s*"last-human-commit"[^{{}}]*?"version"\s*:\s*")({SEMVER})(")'
    found = re.findall(pattern, text, flags=re.S)
    if len(found) != 1:
        return [f".claude-plugin/marketplace.json: expected one last-human-commit entry, found {len(found)}"]
    if found[0][1] == version:
        return []
    if write:
        path.write_text(re.sub(pattern, rf"\g<1>{version}\g<3>", text, flags=re.S), encoding="utf-8")
    return [f".claude-plugin/marketplace.json: {found[0][1]} != {version}"]


def main() -> int:
    check = "--check" in sys.argv[1:]
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(SEMVER, version):
        print(f"VERSION must be X.Y.Z, got {version!r}")
        return 1
    drift = []
    for path, pattern, replacement in rules(version):
        file = ROOT / path
        if not file.is_file():
            drift.append(f"{path}: missing")
            continue
        text = file.read_text(encoding="utf-8")
        found = re.findall(pattern, text)
        if len(found) != 1:
            drift.append(f"{path}: expected one version, found {len(found)}")
            continue
        if found[0][1] != version:
            drift.append(f"{path}: {found[0][1]} != {version}")
            if not check:
                file.write_text(re.sub(pattern, replacement, text), encoding="utf-8")
    drift += marketplace(version, write=not check)
    for line in drift:
        print(line)
    if check and drift:
        print("run: python3 scripts/sync_version.py && python3 scripts/publish_package.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
