import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/last-human-commit/scripts/configure_opencode_marketplace.py"
spec = importlib.util.spec_from_file_location("configure_opencode_marketplace", SCRIPT)
installer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(installer)


def package(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "plugin.json").write_text(json.dumps({"version": "1.5.65"}))
    (root / "AGENTS.md").write_text("current LHC router\n")
    (root / "opencode").mkdir()
    (root / "opencode/lhc-v2.ts").write_text("export default async function LHC() { return {} }\n")
    (root / "skills/last-human-commit").mkdir(parents=True)
    (root / "skills/last-human-commit/SKILL.md").write_text("---\nname: last-human-commit\ndescription: LHC\n---\n")
    return root


def test_configure_opencode_tracks_stable_marketplace_and_retires_only_lhc_copy(tmp_path):
    home = tmp_path / "home"
    root = package(tmp_path / "marketplace/plugins/last-human-commit")
    config_path = home / ".config/opencode/opencode.json"
    config_path.parent.mkdir(parents=True)
    fleet = str(home / ".local/share/agent-harness-fleet/plugin-rollout/sha256-old")
    config = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": [f"{fleet}/AGENTS.md", "/opt/operator/notes.md"],
        "skills": {"paths": [f"{fleet}/skills", "/opt/team/skills"]},
        "plugin": ["opencode-existing"],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    plugin_dir = home / ".config/opencode/plugins"
    plugin_dir.mkdir()
    old_plugin = plugin_dir / "last-human-commit.ts"
    old_plugin.write_text(f'export {{ default }} from "{fleet}/opencode/lhc-v2.ts";\n')

    result = installer.configure(home=home, package_root=root)

    updated = json.loads(config_path.read_text())
    assert updated["instructions"] == ["/opt/operator/notes.md", str(root / "AGENTS.md")]
    assert updated["skills"]["paths"] == ["/opt/team/skills", str(root / "skills")]
    assert updated["plugin"] == ["opencode-existing"]
    assert old_plugin.is_symlink()
    assert old_plugin.resolve() == root / "opencode/lhc-v2.ts"
    state = json.loads((home / ".local/state/last-human-commit/opencode.json").read_text())
    assert state["packageRoot"] == str(root)
    assert result["version"] == "1.5.65"
    assert len(list((home / ".local/state/last-human-commit/backups").glob("*"))) == 2


def test_configure_opencode_is_idempotent(tmp_path):
    home = tmp_path / "home"
    root = package(tmp_path / "marketplace/plugins/last-human-commit")
    (home / ".config/opencode").mkdir(parents=True)
    (home / ".config/opencode/opencode.json").write_text("{}\n")

    first = installer.configure(home=home, package_root=root)
    backup_count = len(list((home / ".local/state/last-human-commit/backups").glob("*")))
    second = installer.configure(home=home, package_root=root)

    assert first["changed"] is True
    assert second["changed"] is False
    assert len(list((home / ".local/state/last-human-commit/backups").glob("*"))) == backup_count


def test_configure_opencode_fails_closed_on_unrecognized_plugin_file(tmp_path):
    home = tmp_path / "home"
    root = package(tmp_path / "marketplace/plugins/last-human-commit")
    config_path = home / ".config/opencode/opencode.json"
    config_path.parent.mkdir(parents=True)
    original = '{"instructions":["keep-me"]}\n'
    config_path.write_text(original)
    plugin_dir = home / ".config/opencode/plugins"
    plugin_dir.mkdir()
    plugin = plugin_dir / "last-human-commit.ts"
    plugin.write_text("export default function unrelatedUserPlugin() {}\n")

    with pytest.raises(installer.InstallationError):
        installer.configure(home=home, package_root=root)

    assert config_path.read_text() == original
    assert plugin.read_text() == "export default function unrelatedUserPlugin() {}\n"
