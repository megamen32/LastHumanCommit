"""A fresh session that loads the umbrella skill must land on the LHC router.

The umbrella skill is the only LHC entry point in a harness that runs no plugin
hooks. If its pointer to the router is ambiguous, the session reads the
project's own `AGENTS.md`, never learns the Lead contract, and answers a
Russian user in English. These checks pin the pointer, the file it resolves to
and the no-hook fallback command.

The skill must also be self-sufficient for the first three decisions — who the
Lead is, which mode the accepted scope calls for, and which language the user
reads — because a session that picks a mode from a skill description before it
reads the router will run the wrong cycle.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/last-human-commit'
SKILL = PACKAGE / 'skills/last-human-commit/SKILL.md'
ROUTER = PACKAGE / 'AGENTS.md'


def flat(text: str) -> str:
    """Line wrapping must not change what the skill says."""
    return " ".join(text.split())


def test_umbrella_skill_points_at_the_package_router_not_the_project_file():
    skill = SKILL.read_text()
    assert "the LHC package's own `AGENTS.md`" in flat(skill)
    assert "not** the `AGENTS.md` of the project" in flat(skill)
    # The pointer must resolve inside the delivered package.
    assert (SKILL.parent / '../../AGENTS.md').resolve() == ROUTER.resolve()
    assert ROUTER.is_file()


def test_package_router_still_carries_the_lead_contract():
    router = ROUTER.read_text()
    assert 'Lead only orchestrates' in flat(router)
    assert 'Lead owns' in flat(router)
    assert '## Language policy' in flat(router)
    assert 'Russian-speaking user' in flat(router)


def test_a_harness_without_hooks_has_an_explicit_fallback_command():
    skill = SKILL.read_text()
    assert 'no plugin hooks' in flat(skill)
    assert 'lhc_entry.py" --session' in flat(skill)
    assert '--heartbeat-only' in flat(skill)
    assert 'session_id' in flat(skill)
    # The fallback must point at the package's own tool, not a global path.
    assert '"<tools>/lhc_entry.py"' in flat(skill)


def test_every_projected_skill_carries_the_same_umbrella_pointer():
    canon = (ROOT / 'src/common/skills/last-human-commit/SKILL.md').read_text()
    assert canon == SKILL.read_text()


def test_the_skill_alone_states_who_the_lead_is():
    skill = SKILL.read_text()
    # The catalog line is what the agent reads before it loads anything.
    front_matter = skill.split('---')[1]
    assert 'You are the Lead' in front_matter
    assert "never from a skill's description" in front_matter
    assert 'in their own language' in front_matter
    assert 'You are the Lead' in flat(skill)
    assert 'The Lead only orchestrates' in flat(skill)
    assert 'performed by a Worker' in flat(skill)
    assert 'Workers do not hire other agents' in flat(skill)
    # The full role description is reachable by a path, not by hope.
    assert 'common/agents/Lead.md' in flat(skill)


def test_the_skill_alone_carries_the_mode_table_and_its_rule():
    skill = SKILL.read_text()
    for mode in ('quickfix', 'fullcycle', 'testing', 'research', 'status', 'coordination'):
        assert mode in skill
    assert "never from a skill's description" in flat(skill)
    # Design work is Full, and the mini loop says so itself.
    assert 'that is Full' in flat(skill)
    assert 'working→ideal→YAGNI' in flat(skill)
    assert 'council' in flat(skill)


def test_the_skill_alone_states_the_language_rule():
    skill = SKILL.read_text()
    assert "the user's own language" in flat(skill)
    assert 'leaf labels' in flat(skill)
    assert 'Reason and coordinate in English' in flat(skill)


def test_the_mini_loop_refuses_design_work_in_its_catalog_description():
    skill = (PACKAGE / 'skills/mini-improvement-loop/SKILL.md').read_text()
    front_matter = skill.split('---')[1]
    # The catalog line is what the agent reads before it loads anything.
    assert 'that is Full, not this loop' in flat(front_matter)
    assert '## Scope check before the loop' in flat(skill)
    assert 'working→ideal→YAGNI' in flat(skill)


def test_the_package_language_policy_covers_every_user_facing_artifact():
    router = ROUTER.read_text()
    assert 'your answers, the task record, the plan report, the task graph' in flat(router)
    assert 'leaf labels and field wording included' in flat(router)
    report = (PACKAGE / 'common/protocols/PLAN_REPORT.md').read_text()
    assert 'the user reads the leaves, not the plan' in flat(report)
