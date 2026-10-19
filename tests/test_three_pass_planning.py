"""User correction: design a solution, idealize it, then retain ~80% of value."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("path,stages", [
    ("AGENTS.md", ("Working solution", "Ideal version", "Minimum working version")),
    ("src/common/agents/Lead.md", ("one working solution", "an ideal", "minimum working implementation")),
    ("src/common/skills/architecture-design/SKILL.md", ("Working solution", "Ideal version", "80%-value MVP")),
    ("skills/planning/SKILL.md", ("working solution", "ideal version", "80%-value MVP")),
    ("src/common/profiles/Planning.md", ("working solution", "ideal version", "80%-value MVP")),
    ("templates/FULL_CYCLE.md", ("working solution", "ideal version", "80%-value MVP")),
])
def test_order_is_solution_then_ideal_then_value_cut(path, stages):
    text = " ".join((ROOT/path).read_text().split())
    positions = [text.index(stage) for stage in stages]
    assert positions == sorted(positions)
    assert "ideal/full -> normal -> YAGNI/Pareto MVP" not in text


def test_mvp_is_complete_value_not_partial_implementation():
    method = " ".join((ROOT/"src/common/skills/architecture-design/SKILL.md").read_text().split())
    assert "80% of the useful result, not 80% of the implementation" in method
    assert "orientation, not a measured guarantee" in method
    assert "Implement the third version" in method
    assert "not three separate builds or approval rounds" in method
    assert "already accepted mandatory outcomes" in method


def test_useful_method_does_not_restore_report_ritual():
    router = (ROOT/"AGENTS.md").read_text()
    assert "three passes over one solution" in router
    assert "not three reports" in router
    assert "three-line minimal path" not in router
    assert "small work uses one bounded Worker + Lead review" in router
    assert "An assigned no-delegation leaf" in router


def test_large_fullcycle_routes_research_before_plan_and_final_council_before_dispatch():
    for path in ('AGENTS.md', 'src/common/agents/Lead.md', 'src/common/skills/architecture-design/SKILL.md'):
        text = (ROOT/path).read_text()
        route = ['bounded independent research Workers', 'working→ideal→YAGNI', 'quota-aware frontier council', 'bounded dispatch']
        positions = [text.index(step) for step in route]
        assert positions == sorted(positions), path
        for invariant in ('alternatives', 'crosschallenge', 'business cost', 'dissent', 'Quickfix/testing/assigned leaf'):
            assert invariant in text, (path, invariant)
