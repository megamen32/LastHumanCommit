from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "last-human-commit"


def test_installed_skill_resolves_bundled_router_and_tools():
    skill = PLUGIN / "skills" / "last-human-commit" / "SKILL.md"
    text = skill.read_text()
    assert "../../AGENTS.md" in text
    assert (PLUGIN / "AGENTS.md").is_file()
    assert (PLUGIN / "common" / "agents" / "Worker.md").is_file()
    assert (PLUGIN / "common" / "tools" / "lhc_worktree.py").is_file()


def test_bundle_contains_no_python_cache_files():
    bundled = PLUGIN / "common"
    assert bundled.is_dir()
    assert not any(p.name == "__pycache__" or p.suffix == ".pyc" for p in bundled.rglob("*"))


def test_hermes_adapter_is_packaged():
    assert (PLUGIN / "com.nousresearch.hermes" / "plugin.yaml").is_file()
