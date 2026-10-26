"""Acceptance contract: tangible result first, blind feedback at major outcomes."""
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def read(name):return " ".join((ROOT/name).read_text().split())


@pytest.mark.parametrize("name", ["src/common/agents/Tester.md", "src/common/skills/user-testing/SKILL.md", "src/common/skills/focus-groups/SKILL.md"])
def test_blind_testing_is_milestone_not_tool_or_hour(name):
    text=read(name)
    assert "milestone" in text
    assert "fresh" in text and "feedback" in text
    # Blind testing is a milestone-scale decision, not a per-hour ritual.
    assert "not every hour" in text \
        or "not a queue for every Full task, edit, hour or commit" in text \
        or "not a mandatory schedule" in text
    assert "Zero Knowledge" in text or "Independently attempt a user goal" in text


def test_personas_and_full_feedback_are_preserved_without_fake_customers():
    text=read("src/common/skills/focus-groups/SKILL.md")
    for phrase in ("age", "personality", "realistic goal", "random", "positive", "negative", "raw feedback", "not actual customers", "not a word quota"):
        assert phrase in text
    assert "stereotype" in text


def test_hourly_protocol_cannot_claim_milestone_acceptance():
    text=read("src/common/protocols/BUSINESS_CHECKPOINT.md")
    assert "Direction check is not acceptance" in text
    assert "--zk-session" not in text
    assert "--business-result" in text and "--source-ref" in text
    # The hourly control checks direction; the milestone scale is a separate,
    # explicitly chosen acceptance event.
    assert "do not launch a group every hour" in text
    assert "milestone_acceptance=not_evaluated" in text
    assert "not an elapsed-time gate" in text


def test_tester_sees_goal_not_desired_verdict_or_solution_recipe():
    text=read("src/common/skills/user-testing/SKILL.md")
    for phrase in ("no implementation history", "not the expected verdict", "public help", "before/after", "what helped", "what confused"):
        assert phrase in text
    assert "RED" in text and "GREEN" in text
