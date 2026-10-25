"""Guard the documented expected-result/current-fact distinction."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PlanOutcomeSemanticsTests(unittest.TestCase):
    def test_plan_instructions_do_not_require_an_achieved_result(self):
        forbidden = (
            "что пользователь может использовать уже сейчас",
            "what the person can already use **now**",
            "what the person can already use now",
            "`business_result` is the achieved fact",
            "the business result the user can already use",
            "business result delivered now;",
        )
        for name in (
            "src/common/protocols/PLAN_REPORT.md",
            "src/common/protocols/TASK_GRAPH.md",
            "src/common/skills/plan-artifacts/SKILL.md",
            "AGENTS.md",
            "templates/FULL_CYCLE.md",
        ):
            text = (ROOT / name).read_text().lower()
            for phrase in forbidden:
                with self.subTest(file=name, phrase=phrase):
                    self.assertFalse(phrase.lower() in text, f"{name}: {phrase}")


if __name__ == "__main__":
    unittest.main()
