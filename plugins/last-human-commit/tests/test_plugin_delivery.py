from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "last-human-commit"


def test_installed_skill_resolves_bundled_router_and_tools():
    """The installed skill must point the agent at the package's own router.

    The skill says where the router is in words, because a skill may only
    link files that sit inside the skill directory: a `../` link would not
    resolve in a projection of the skills alone, and the factory test holds
    that rule. So the check is that the skill names the router and says
    where it is, and that the bundled files it names are really there.
    """
    skill = PLUGIN / "skills" / "last-human-commit" / "SKILL.md"
    text = skill.read_text()
    assert "`AGENTS.md`" in text
    assert "two directories above this `SKILL.md`" in text
    assert (PLUGIN / "AGENTS.md").is_file()
    assert (PLUGIN / "common" / "agents" / "Worker.md").is_file()
    assert (PLUGIN / "common" / "tools" / "lhc_worktree.py").is_file()
    # A skill links only files that travel with it.
    assert "../" not in text


def test_bundle_contains_no_python_cache_files():
    bundled = PLUGIN / "common"
    assert bundled.is_dir()
    assert not any(p.name == "__pycache__" or p.suffix == ".pyc" for p in bundled.rglob("*"))


def test_hermes_adapter_is_packaged():
    assert (PLUGIN / "com.nousresearch.hermes" / "plugin.yaml").is_file()
