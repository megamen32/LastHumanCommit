import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manifests_and_upstream_versions_match():
    versions = {
        json.loads((ROOT / "plugin.json").read_text())["version"],
        json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"],
        json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"],
        json.loads((ROOT / "UPSTREAM.json").read_text())["version"],
        (ROOT / "VERSION").read_text().strip(),
    }
    assert versions == {"1.42.3"}


def test_full_skill_surface_is_portable_and_complete():
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    assert len(skills) == 67
    assert (ROOT / "skills/gsd-help/SKILL.md").is_file()
    assert (ROOT / "skills/gsd-new-project/SKILL.md").is_file()
    for skill in skills:
        text = skill.read_text()
        assert "<gsd_agent_plugin_adapter>" in text
        assert "/tmp/gsd-" not in text
        for ref in re.findall(r"@\.\./\.\./((?:get-shit-done|agents|bin|sdk)/[^\s]+)", text):
            assert (ROOT / ref).exists(), f"broken reference in {skill}: {ref}"


def test_bundled_sdk_and_workflows_exist():
    assert (ROOT / "bin/gsd-sdk.js").is_file()
    assert (ROOT / "sdk/dist/cli.js").is_file()
    assert (ROOT / "sdk/shared/model-catalog.json").is_file()
    assert (ROOT / "node_modules/ws/package.json").is_file()
    assert (ROOT / "sdk/package.json").is_file()
    assert (ROOT / "node_modules/ws/package.json").is_file()
    assert (ROOT / "node_modules/@anthropic-ai/claude-agent-sdk/package.json").is_file()
    assert (ROOT / "get-shit-done/workflows/help.md").is_file()
    assert (ROOT / "agents/gsd-executor.md").is_file()
    result = subprocess.run(
        ["node", str(ROOT / "bin/gsd-sdk.js"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Usage: gsd-sdk" in result.stdout
