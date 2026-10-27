"""Every runtime-facing manifest of the LHC package must report the same version.

A release that bumps only the JSON manifests leaves Hermes reporting the older
version, because Hermes reads the flat YAML manifest. The release gate covers
the JSON manifests; this test covers the runtimes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins" / "last-human-commit"

VERSION = re.compile(r"^version:\s*['\"]?([0-9]+\.[0-9]+\.[0-9]+)", re.MULTILINE)


def _json_version(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["version"])


def _yaml_version(path: Path) -> str:
    match = VERSION.search(path.read_text(encoding="utf-8"))
    assert match, f"no version field in {path}"
    return match.group(1)


def _release_version() -> str:
    return _json_version(PACKAGE / "plugin.json")


def test_every_runtime_manifest_reports_the_same_version():
    reported: dict[str, str] = {}

    for rel in (
        "plugin.json",
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".zcode-plugin/plugin.json",
    ):
        path = PACKAGE / rel
        if path.is_file():
            reported[rel] = _json_version(path)

    for path in sorted(PACKAGE.glob("native/*/.codex-plugin/plugin.json")):
        reported[str(path.relative_to(PACKAGE))] = _json_version(path)

    # Hermes reads the flat manifests, so they are the ones that drift silently.
    for rel in ("plugin.yaml", "com.nousresearch.hermes/plugin.yaml"):
        path = PACKAGE / rel
        if path.is_file():
            reported[rel] = _yaml_version(path)

    source = ROOT / "adapters" / "hermes" / "plugin" / "plugin.yaml"
    if source.is_file():
        reported[str(source.relative_to(ROOT))] = _yaml_version(source)

    assert len(reported) >= 6, f"expected every manifest to be checked, saw {sorted(reported)}"
    assert set(reported.values()) == {_release_version()}, f"manifest versions drifted: {reported}"


def test_hermes_flat_manifest_matches_the_json_manifest():
    release = _release_version()
    assert _yaml_version(PACKAGE / "plugin.yaml") == release
    assert _yaml_version(PACKAGE / "com.nousresearch.hermes" / "plugin.yaml") == release
    assert _yaml_version(ROOT / "adapters" / "hermes" / "plugin" / "plugin.yaml") == release




def test_repo_catalog_advertises_the_release_version():
    catalog = ROOT / ".claude-plugin" / "marketplace.json"
    if not catalog.is_file():
        return
    for entry in json.loads(catalog.read_text(encoding="utf-8")).get("plugins", []):
        if entry.get("name") == "last-human-commit":
            assert entry.get("version") == _release_version()
