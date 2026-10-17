"""Acceptance contract: tangible result first, blind feedback at major outcomes."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def read(name):return " ".join((ROOT/name).read_text().split())

def test_tangible_outcome_precedes_design_and_code():
    router=read("AGENTS.md")
    assert router.index("Осязаемый результат до кода") < router.index("Трёхступенчатое проектирование")
    for phrase in ("кто", "раньше", "после", "TDD", "RED", "GREEN"):
        assert phrase in router
    assert "SHA" in router

@pytest.mark.parametrize("name", ["src/common/agents/Tester.md", "src/common/skills/user-testing/SKILL.md", "src/common/skills/focus-groups/SKILL.md"])
def test_blind_testing_is_milestone_not_tool_or_hour(name):
    text=read(name)
    assert "milestone" in text and "3 hours" in text
    assert "not every hour" in text
    assert "fresh" in text and "feedback" in text


def test_personas_and_full_feedback_are_preserved_without_fake_customers():
    text=read("src/common/skills/focus-groups/SKILL.md")
    for phrase in ("age", "personality", "realistic goal", "random", "positive", "negative", "raw feedback", "not actual customers", "not a word quota"):
        assert phrase in text
    assert "stereotype" in text


def test_hourly_protocol_cannot_claim_milestone_acceptance():
    text=read("src/common/protocols/BUSINESS_CHECKPOINT.md")
    assert "не приёмка milestone" in text
    assert "--zk-session" not in text
    assert "--business-result" in text and "--source-ref" in text
    assert "~3 часа" in text


def test_tester_sees_goal_not_desired_verdict_or_solution_recipe():
    text=read("src/common/skills/user-testing/SKILL.md")
    for phrase in ("no implementation history", "not the expected verdict", "public help", "before/after", "what helped", "what confused"):
        assert phrase in text
    assert "RED" in text and "GREEN" in text
