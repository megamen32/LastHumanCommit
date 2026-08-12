#!/usr/bin/env python3
"""Semantic regressions for business-first, least-cost LHC routing."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    """Return one repository instruction file as UTF-8 text."""

    return (ROOT / relative).read_text(encoding="utf-8")


def compact(value: str) -> str:
    """Normalize whitespace so prose wrapping does not weaken the contract."""

    return " ".join(value.split())


def assert_order(value: str, first: str, second: str, source: str) -> None:
    """Require *first* to appear before *second* in one instruction surface."""

    normalized = compact(value)
    first_index = normalized.find(first)
    second_index = normalized.find(second)
    assert first_index >= 0, f"{source} lacks {first!r}"
    assert second_index >= 0, f"{source} lacks {second!r}"
    assert first_index < second_index, f"{source} routes process before business value"


def test_lead_routes_business_value_before_process() -> None:
    lead = read("src/common/agents/Lead.md")
    assert_order(
        lead,
        "Business value is the first routing input.",
        "Choose the least-cost sufficient execution mode",
        "Lead.md",
    )
    required = (
        "Trace the actual production consumer path before choosing an implementation surface.",
        "Lead may research and implement directly whenever delegation would cost more",
        "Proof strength matches the exact claim the user needs now.",
        "An accepted MVP or 80/20 definition remains the Definition of Done",
        "Gates are tools, not milestones.",
    )
    for phrase in required:
        assert phrase in compact(lead), phrase


def test_worker_twenty_minutes_is_a_management_checkpoint() -> None:
    aggregate = "\n".join(
        read(path)
        for path in (
            "AGENTS.md",
            "src/common/agents/Lead.md",
            "src/common/agents/Worker.md",
            "src/common/agents/Overseer.md",
            "src/common/profiles/Planning.md",
            "src/common/protocols/STOP_RETHINK.md",
        )
    )
    normalized = compact(aggregate)
    for phrase in (
        "Every 20 active minutes is a control checkpoint, not a Worker lifetime limit.",
        "The Worker reports progress, business delta, blocker, and the shortest next action",
        "Prefer redirecting or resuming the same Worker",
        "Cancellation is exceptional",
    ):
        assert phrase in normalized, phrase

    forbidden = (
        "maximum <=20 active minutes",
        "Reject any Worker assignment above 20 minutes",
        "proposed Worker assignment exceeds 20",
    )
    for phrase in forbidden:
        assert phrase not in normalized, phrase


def test_required_children_are_actually_joined() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    codex = compact(read("adapters/codex/templates/subagent.md"))
    for value, source in ((lead, "Lead.md"), (codex, "Codex template")):
        assert "Use the harness wait/join tool" in value, source
        assert (
            "Do not send the final answer while a required child result remains non-terminal."
            in value
        ), source


def test_governance_is_risk_triggered_instead_of_unconditional() -> None:
    sources = {
        path: compact(read(path))
        for path in (
            "AGENTS.md",
            "src/common/agents/Lead.md",
            "README.md",
            "docs/agent-authoring.md",
            "templates/FULL_CYCLE.md",
        )
    }
    required = (
        "Use no role or gate whose expected decision or risk-reduction value is lower than its cost.",
        "Overseer, Adviser, Critic, Reviewer, and Tester are risk-triggered",
    )
    for phrase in required:
        assert any(phrase in value for value in sources.values()), phrase

    forbidden = (
        "Overseer is mandatory for every task",
        "Draft exactly three Russian plans, always",
        "exactly two fresh Testers",
        "After each wave run focused checks, Reviewer",
        "L does not search the repository or write code",
        "For Short and Full work I do not search the repository or write code",
    )
    for path, value in sources.items():
        for phrase in forbidden:
            assert phrase not in value, f"{path}: {phrase}"


def test_persistence_and_proof_are_claim_calibrated() -> None:
    research = compact(read("src/common/protocols/WORKER_RESEARCH.md"))
    session = compact(read("docs/shared-session-abstraction.md"))
    delivery = compact(read("skills/business-delivery/SKILL.md"))

    assert (
        "Persist research when handoff, recovery, reuse, or the cost of rediscovery justifies it."
        in research
    )
    assert "No elapsed-time threshold by itself requires a file or Git commit." in session
    assert "Use the cheapest evidence sufficient for the exact business claim." in delivery

    for value in (research, session):
        assert "After 10 active minutes" not in value
        assert "must include a Git commit" not in value


def test_adapter_templates_preserve_checkpoint_semantics() -> None:
    for adapter in ("codex", "opencode", "claude-code", "hermes", "zcode"):
        value = compact(read(f"adapters/{adapter}/templates/subagent.md"))
        assert "20-minute reporting checkpoint" in value, adapter
        assert "expected total range may exceed 20 minutes" in value, adapter
        assert "lowest sufficient" in value, adapter
