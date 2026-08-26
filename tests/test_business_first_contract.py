#!/usr/bin/env python3
"""Semantic regressions for the LHC v2 contract: minimal path, time truth, real tests, no secret theater."""

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
    assert (
        "Do not send the final answer while a required child result remains non-terminal"
        in lead
    )


def test_worker_questions_lead_without_blocking_safe_parallel_work() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    worker = compact(read("src/common/agents/Worker.md"))
    aggregate = lead + " " + worker

    for phrase in (
        "ask L at every decision boundary",
        "recommendation and proposed default",
        "non-blocking parent transport",
        "continue safe independent work while waiting",
        "L owns the decision",
    ):
        assert phrase in aggregate, phrase


def test_minimal_path_is_mandatory() -> None:
    router = compact(read("AGENTS.md"))
    lead = compact(read("src/common/agents/Lead.md"))

    for phrase in (
        "three-line minimal path",
        "smallest YAGNI vertical slice",
    ):
        assert phrase in router + " " + lead, phrase
    assert "discard list" in lead


def test_governance_is_supreme_overseer_plus_real_tester() -> None:
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
        "Overseer is the supreme route controller",
        "Overseer and Tester are the only gates",
    )
    for phrase in required:
        assert any(phrase in value for value in sources.values()), phrase

    assert "Security theater is the canonical drift" in compact(
        read("src/common/agents/Overseer.md")
    )


def test_secret_paranoia_is_forbidden() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    router = compact(read("AGENTS.md"))

    for phrase in ("Secrets are not work", "environment variable"):
        assert phrase in lead + " " + router, phrase

    for relative in ("AGENTS.md", "CLAUDE.md", "src/common/agents/Lead.md", "README.md"):
        value = compact(read(relative))
        for phrase in (
            "AskSecret/SSS",
            "Use AskHuman",
            "opaque registered-agent",
            "base64 fallback",
            "NoticePlace capability",
            "attested human-request capability",
        ):
            assert phrase not in value, f"{relative}: {phrase}"


def test_real_surface_testing_is_the_final_gate() -> None:
    tester = compact(read("src/common/agents/Tester.md"))
    lead = compact(read("src/common/agents/Lead.md"))

    for phrase in (
        "mandatory final gate for user-facing results",
        "Use the real surface",
        "never prove a user-facing result",
    ):
        assert phrase in tester, phrase
    assert "Test files never substitute" in lead


def test_overseer_time_truth_requires_start_anchor() -> None:
    overseer = compact(read("src/common/agents/Overseer.md"))
    time_control = compact(read("src/common/protocols/TIME_CONTROL.md"))

    for phrase in ("supreme route controller", "Started at"):
        assert phrase in overseer, phrase
    for phrase in ("Start anchor", "manual clock", "не контролировал"):
        assert phrase in time_control, phrase


def test_self_improve_is_an_evolution_loop() -> None:
    protocol = compact(read("src/common/protocols/SELF_IMPROVE.md"))
    lead = compact(read("src/common/agents/Lead.md"))

    for phrase in (
        "minimal proposed patch",
        "verification canary",
        "one reviewed commit",
        "three refinement iterations",
    ):
        assert phrase in protocol, phrase
    assert "Self-evolution" in lead


def test_hourly_business_report_and_cycle_estimates_are_required() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    planning = compact(read("src/common/profiles/Planning.md"))
    task = compact(read("src/common/templates/.agents/tasks/task_template.md"))

    for phrase in (
        "At every crossed wall-clock hour while the task remains active",
        "Какие реальные задачи закрыты",
        "Every declared work cycle has its own immutable minimum / maximum estimate",
    ):
        assert phrase in lead + " " + planning + " " + task, phrase

    assert "lhc_time_guard.py" in lead + " " + planning + " " + task


def test_planning_has_two_compressed_approaches_and_decomposition_skill() -> None:
    planning = compact(read("src/common/profiles/Planning.md"))
    lead = compact(read("src/common/agents/Lead.md"))
    decomposition = compact(read("skills/task-decomposition/SKILL.md"))

    for phrase in (
        "exactly two genuinely different approaches",
        "ideal/full -> normal -> YAGNI/Pareto MVP",
        "Recommend the least-cost YAGNI",
    ):
        assert phrase in planning + " " + lead, phrase
    assert decomposition


def test_adapter_templates_preserve_checkpoint_semantics() -> None:
    for adapter in ("codex", "opencode", "claude-code", "hermes", "zcode"):
        value = compact(read(f"adapters/{adapter}/templates/subagent.md"))
        for phrase in (
            "lowest sufficient",
            "expected total range may exceed 20 minutes",
            "20-minute reporting checkpoint",
            "non-blocking parent transport",
            "не контролировал",
        ):
            assert phrase in value, adapter


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


def test_compaction_handoff_is_bounded_not_append_only() -> None:
    aggregate = "\n".join(
        read(path)
        for path in (
            "src/common/agents/Lead.md",
            "src/common/agents/Worker.md",
            "src/common/protocols/TIME_CONTROL.md",
            "src/common/templates/.agents/tasks/task_template.md",
        )
    )
    for phrase in (
        "current-handoff.md",
        "not append-only",
        "last three marks",
        "Compaction count",
    ):
        assert phrase in aggregate, phrase


def test_worker_research_preserves_bugfix_chain_and_outcome_metrics() -> None:
    research = compact(read("skills/worker-research/SKILL.md"))

    assert (
        "telemetry -> reproduction -> smallest failing test -> root cause -> patch -> regression"
        in research
    )
    for phrase in (
        "do not infer the fix from a stack trace",
        "real consumer path",
        "lead_time",
        "rework",
        "effective_cost",
        "P50/P95/P99",
        "quality floor",
        "non-inferiority margin",
        "Write `unknown` when a value was not measured",
        "do not turn the reusable map into an append-only metrics log",
    ):
        assert phrase in research, phrase


def test_obsolete_process_rituals_stay_gone() -> None:
    sources = {
        path: compact(read(path))
        for path in (
            "AGENTS.md",
            "src/common/agents/Lead.md",
            "src/common/agents/Worker.md",
            "docs/agent-authoring.md",
            "templates/FULL_CYCLE.md",
        )
    }
    forbidden = (
        "Draft exactly three Russian plans, always",
        "Планы — всегда ровно три",
        "exactly two fresh Testers",
        "After each wave run focused checks, Reviewer",
        "L does not search the repository or write code",
        "For Short and Full work I do not search the repository or write code",
    )
    for path, value in sources.items():
        for phrase in forbidden:
            assert phrase not in value, f"{path}: {phrase}"
