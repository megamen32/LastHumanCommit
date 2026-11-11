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


def test_router_is_outcome_first_and_keeps_only_effect_guards():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Default mode: outcome first" in text
    assert "one real canary or readback" in text
    assert "missing telemetry never blocks ordinary work" in text
    assert "do not expose secrets" in text
    assert "do not repeat an external mutation" in text
    assert "preserve an explicit human STOP" in text
    for retired in (
        "Subagents are on by default",
        "Every discovered bug must close before Done",
        "at least two in a fullcycle",
    ):
        assert retired not in text


def test_plan_is_optional_and_small():
    text = flat("src/common/skills/plan/SKILL.md")
    assert "Planning is a tool, not a gate" in text
    assert "at most three stages" in text
    assert "Recon facts" in text and "optional telemetry" in text
    assert "Do not create a plan merely because a change may take more than fifteen minutes" in text


def test_real_use_testing_is_proportional():
    text = flat("src/common/skills/real-use-testing/SKILL.md")
    assert "does not require a fresh independent Tester" in text
    assert "explicit release/high" in text
    assert "Do not launch tester sessions merely to satisfy" in text


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
