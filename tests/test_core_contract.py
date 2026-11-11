import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location("lhc_test_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def flat(rel):
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def test_router_keeps_effect_boundaries_and_the_user_required_audits():
    text = flat("AGENTS.md")
    assert "## Default mode: outcome first" in text
    assert "A bounded task can be done directly" in text
    assert "actual consumer" in text
    assert "secrets and private data" in text
    assert "before retrying" in text
    assert "human STOP" in text
    assert "Boss audits are mandatory" in text
    assert "optional checks do not disable Boss" in text
    for retired in ("Every discovered bug must close before Done", "at least two in a fullcycle"):
        assert retired not in text


def test_fullcycle_choice_precedes_decomposition_and_execution():
    for path in ("AGENTS.md", "src/common/skills/plan/SKILL.md"):
        text = flat(path)
        assert "exactly three short plan summaries" in text
        assert "wait for the user's explicit choice" in text
        assert "After the user chooses" in text
        assert "full decomposition, dependencies and parallel allocation" in text
        assert "recommendation, silence" in text
        assert "A bounded quickfix stays direct" in text
    assert "decomposition: complete" in flat("src/common/skills/plan/SKILL.md")
    assert "before dispatch" in flat("src/common/skills/plan/SKILL.md")
    context = load("src/common/tools/lhc_entry.py").context_for({}, ROOT)
    assert "three short plan summaries" in context
    assert "wait for the user's explicit choice" in context
    assert "only then do full decomposition" in context
    assert "Boss audits are mandatory" in context


def test_real_use_testing_remains_proportional():
    text = flat("src/common/skills/real-use-testing/SKILL.md")
    assert "actual consumer" in text
    assert "a bounded direct client check may be enough" in text
    assert "when independent usability or coverage is part of the claim" in text
    assert "does not require trying every tool in order" in text


def test_outcome_fullcycle_does_not_invent_release_stages():
    outcome = load("src/common/tools/lhc_outcome.py")
    stages = outcome.applicable("fullcycle", "Implement a new feature.")
    assert [name for name, row in stages.items() if row["status"] == "pending"] == ["technical", "consumer"]


def test_milestone_gate_is_advisory():
    milestone = load("src/common/tools/lhc_milestone.py")
    result = milestone.acceptance_gate({"milestone": {"status": "pending", "hold": None}, "native_entry": {}})
    assert result["decision"] == "allow"
    assert result.get("advisory") is True


def test_default_hooks_do_not_run_accounting_or_stop_blocks():
    for rel in ("plugins/last-human-commit/hooks/hooks.json",
                "plugins/last-human-commit/hooks/zcode-hooks.json"):
        hooks = json.loads((ROOT / rel).read_text(encoding="utf-8"))["hooks"]
        assert set(hooks) == {"SessionStart", "PostCompact"}
    assert (ROOT / "plugins/last-human-commit/opencode/lhc-boss-v2.ts").is_file()
