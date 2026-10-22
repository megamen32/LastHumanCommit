"""A fresh session that loads the umbrella skill must land on the LHC router.

The umbrella skill is the only LHC entry point in a harness that runs no plugin
hooks. If its pointer to the router is ambiguous, the session reads the
project's own `AGENTS.md`, never learns the Lead contract, and answers a
Russian user in English. These checks pin the pointer, the file it resolves to
and the no-hook fallback command.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/last-human-commit'
SKILL = PACKAGE / 'skills/last-human-commit/SKILL.md'
ROUTER = PACKAGE / 'AGENTS.md'


def test_umbrella_skill_points_at_the_package_router_not_the_project_file():
    skill = SKILL.read_text()
    assert "the LHC package's own `AGENTS.md`" in skill
    assert "not** the `AGENTS.md` of the project" in skill
    # The pointer must resolve inside the delivered package.
    assert (SKILL.parent / '../../AGENTS.md').resolve() == ROUTER.resolve()
    assert ROUTER.is_file()


def test_package_router_still_carries_the_lead_contract():
    router = ROUTER.read_text()
    assert 'Lead only orchestrates' in router
    assert 'Lead owns' in router
    assert '## Language policy' in router
    assert 'Russian-speaking user' in router


def test_a_harness_without_hooks_has_an_explicit_fallback_command():
    skill = SKILL.read_text()
    assert 'no plugin hooks' in skill
    assert 'lhc_entry.py" --session' in skill
    assert '--heartbeat-only' in skill
    assert 'session_id' in skill
    # The fallback must point at the package's own tool, not a global path.
    assert '"<package root>/tools/lhc_entry.py"' in skill


def test_every_projected_skill_carries_the_same_umbrella_pointer():
    canon = (ROOT / 'src/common/skills/last-human-commit/SKILL.md').read_text()
    assert canon == SKILL.read_text()
