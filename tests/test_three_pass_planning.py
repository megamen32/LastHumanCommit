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
    # Small work keeps the broad council route short, while authorized code work
    # still gets the minimal Lead-owned plan before implementation.
    assert "Every authorized development task has a user-readable Lead-owned plan" in router
    assert "Quickfix still requires a proportional independent tester" in router
    assert "An assigned no-delegation leaf" in router


# The large fullcycle route is stated in the router and the Lead role; the
# architecture-design skill carries the same order with its own softened
# adviser-challenge wording. Each document is checked against its own text.
FULL_CYCLE_ROUTE = {
    'AGENTS.md': (
        ['bounded independent research Workers', 'working→ideal→YAGNI',
         'quota-aware frontier council', 'bounded dispatch'],
        ('alternatives', 'crosschallenge', 'business cost', 'dissent',
         'Every authorized development task has a user-readable Lead-owned plan'),
    ),
    'src/common/agents/Lead.md': (
        ['bounded independent research Workers', 'working→ideal→YAGNI',
         'quota-aware frontier council', 'bounded dispatch'],
        ('alternatives', 'crosschallenge', 'business cost', 'dissent',
         'Quickfix/testing/assigned leaf tasks may skip the broad research/council'),
    ),
    'src/common/skills/architecture-design/SKILL.md': (
        ['bounded independent research Workers', 'working→ideal→YAGNI',
         'before dispatch', 'allowed-model adviser challenge',
         'Quickfix/testing/assigned leaf'],
        ('alternatives', 'do not start this research/council loop',
         'not a mandatory review queue or release gate'),
    ),
}


def test_large_fullcycle_routes_research_before_plan_and_final_council_before_dispatch():
    for path, (route, invariants) in FULL_CYCLE_ROUTE.items():
        text = " ".join((ROOT/path).read_text().split())
        positions = [text.index(step) for step in route]
        assert positions == sorted(positions), path
        for invariant in invariants:
            assert invariant in text, (path, invariant)


def test_native_context_points_at_the_canonical_router_instead_of_copying_it():
    import sys
    sys.path.insert(0, str(ROOT/'src/common/tools'))
    from lhc_entry import context_for
    context = context_for({}, ROOT)
    # The native context is a pointer to the canonical English router, so the
    # harness always reads the live policy instead of a copied instruction blob.
    assert context == f"LHC: read {(ROOT/'AGENTS.md').resolve()} for current instructions."
    assert len(context) < 2200
    # The router keeps the planning-only bounds: a small or read-only answer
    # never starts development, and the Lead never executes the work itself.
    router = (ROOT/'AGENTS.md').read_text()
    assert "Simple questions, translations and status requests do not start development" in router
    assert "Lead only orchestrates: decompose the objective" in router
    assert "Every inspection, edit, check, deployment, commit, push or install is performed by a Worker" in router
    assert "Never bypass HumanStop or required permission" in router
    assert "Choose the shortest working route and check the real scenario" in router
