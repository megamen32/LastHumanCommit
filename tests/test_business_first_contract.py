#!/usr/bin/env python3
"""Semantic regressions for the LHC v2 contract: minimal path, time truth, real tests, no secret theater."""

import ast
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

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


def test_factory_routes_decisions_and_preserves_independent_full_acceptance() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    tester = compact(read("src/common/agents/Tester.md"))
    full = compact(read("templates/FULL_CYCLE.md"))
    control = compact(read("src/common/protocols/STOP_RETHINK.md"))
    assert "strongest suitable available decision model" in lead
    assert "mandatory initial independent Overseer audit before implementation" in lead
    assert "../skills/decompose-and-dispatch/SKILL.md" in lead
    assert "../skills/model-routing/SKILL.md" in lead
    assert "Full requires a fresh independent Tester" in tester
    assert "mandatory fresh independent Tester" in full
    assert "REDECOMPOSE" in control and "CHANGE_MODEL" in control


def test_factory_learning_reaches_verified_reuse() -> None:
    protocol = compact(read("src/common/protocols/SELF_IMPROVE.md"))
    assert "../skills/improve-workflow/SKILL.md" in protocol
    assert "later applicable reuse" in protocol
    assert "without a new human coordination cycle" in protocol


def test_advice_is_an_optional_capability_not_an_extra_gate() -> None:
    router = compact(read("AGENTS.md"))
    assert "- Adviser: `src/common/agents/Adviser.md`" in router
    assert "- Critic: `src/common/agents/Critic.md`" in router
    assert "compatibility alias" in read("src/common/agents/Critic.md")
    assert "Overseer, Tester, and Reviewer are the only gates" in router


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
        "Overseer, Tester, and Reviewer are the only gates",
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
            "opaque registered-agent",
            "base64 fallback",
            "NoticePlace capability",
            "attested human-request capability",
        ):
            assert phrase not in value, f"{relative}: {phrase}"


def test_interaction_tool_ladder() -> None:
    tester = compact(read("src/common/agents/Tester.md"))
    skill = compact(read("skills/real-use-testing/SKILL.md"))

    for phrase in (
        "Accessibility tree",
        "browserclaw",
        "touchpoint",
        "agent-browser",
        "Playwright",
        "XY",
        "last resort",
    ):
        assert phrase in tester + " " + skill, phrase


def test_askhuman_is_the_important_info_channel() -> None:
    router = compact(read("AGENTS.md"))
    lead = compact(read("src/common/agents/Lead.md"))

    assert "AskHuman" in router + " " + lead
    for phrase in ("Never routine confirmations", "/secret"):
        assert phrase in router, phrase


def test_secret_command_is_the_only_phone_handoff() -> None:
    lead = compact(read("src/common/agents/Lead.md"))
    router = compact(read("AGENTS.md"))

    assert "/secret" in lead + " " + router
    assert "never echoes the value" in router
    assert "orchestrates the already-connected AskSecret/AskHuman MCPs" in router


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


def test_unified_history_is_mandatory() -> None:
    router = compact(read("AGENTS.md"))
    lead = compact(read("src/common/agents/Lead.md"))
    workspace = compact(read("src/common/protocols/SHARED_WORKTREE.md"))
    task = compact(read("src/common/templates/.agents/tasks/task_template.md"))

    aggregate = router + " " + lead + " " + workspace
    for phrase in (
        "Commit task-owned files at every completed step",
        "review every change",
        "fix every unsafe or unreviewable item",
        "pushed, deployed where deployable",
        "clean tree",
    ):
        assert phrase in aggregate, phrase
    for phrase in ("Pushed (Full cycle):", "Tree clean (nothing uncommitted):"):
        assert phrase in task, phrase
    assert "Stage and commit only task-owned paths" not in workspace


def test_project_local_tmp_is_mandatory_and_self_enforced() -> None:
    router = compact(read("AGENTS.md"))
    workspace = compact(read("src/common/protocols/SHARED_WORKTREE.md"))
    code = compact(read("src/common/profiles/Code.md"))
    aggregate = " ".join((router, workspace, code))

    for phrase in (
        "<project-root>/.tmp/",
        "source code",
        "repository clones",
        "build trees and caches",
        "binaries",
        "packages",
        "APK/DMG",
        "archives",
        "checksums",
        "release artifacts",
        "even when they exist only briefly",
        "system `/tmp`",
        "`$TMPDIR`",
        "default temp directory",
        "tiny non-code OS primitives",
        "never for project data or deliverables",
    ):
        assert phrase in aggregate, phrase

    assert ".tmp/" in read(".gitignore").splitlines()
    pytest_config = read("conftest.py")
    for phrase in (
        'f"pytest-{os.getpid()}-{secrets.token_hex(8)}"',
        "must not be a symlink",
        "escapes project root",
        '"check-ignore", "--quiet", "--", ".tmp/"',
    ):
        assert phrase in pytest_config, phrase

    for relative in (
        "tests/test_block_adapter.sh",
        "tests/test_task_resume_snapshots.sh",
    ):
        shell = read(relative)
        assert "${TMPDIR" not in shell, relative
        assert "${TMPDIR:-/tmp}" not in shell, relative
        assert "/.tmp/" in shell, relative

    canonical = ROOT / "skills/lhc-rollout/scripts/lhc_rollout.py"
    generated = ROOT / "plugins/last-human-commit/skills/lhc-rollout/scripts/lhc_rollout.py"
    assert canonical.read_bytes() == generated.read_bytes()

    tree = ast.parse(canonical.read_text(encoding="utf-8"))
    creators = {"TemporaryDirectory", "NamedTemporaryFile", "mkdtemp", "mkstemp"}
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        function = call.func
        if not (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "tempfile"
            and function.attr in creators
        ):
            continue
        assert any(keyword.arg == "dir" for keyword in call.keywords), (
            f"tempfile.{function.attr} must use an explicit project-local or "
            "same-directory dir"
        )


def test_rollout_rejects_symlink_tmp_escape(tmp_path: Path) -> None:
    canonical = ROOT / "skills/lhc-rollout/scripts/lhc_rollout.py"
    spec = importlib.util.spec_from_file_location("lhc_rollout_escape_test", canonical)
    assert spec is not None and spec.loader is not None
    rollout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rollout)

    repo = tmp_path / "source-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text(".tmp/\n", encoding="utf-8")
    outside = tmp_path / "escaped"
    outside.mkdir()
    (repo / ".tmp").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RuntimeError, match="must not be a symlink"):
        rollout._project_tmp(repo)


def test_pytest_basetemp_is_unique_and_project_local() -> None:
    spec = importlib.util.spec_from_file_location("lhc_pytest_config_test", ROOT / "conftest.py")
    assert spec is not None and spec.loader is not None
    pytest_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pytest_config)

    first = pytest_config._new_pytest_basetemp()
    second = pytest_config._new_pytest_basetemp()
    expected_parent = (ROOT / ".tmp").resolve(strict=True)
    assert first != second
    assert first.parent == expected_parent
    assert second.parent == expected_parent
    assert first.name.startswith(f"pytest-{pytest_config.os.getpid()}-")
    assert second.name.startswith(f"pytest-{pytest_config.os.getpid()}-")


def test_ssh_rollout_stages_only_in_target_project_tmp(tmp_path: Path, monkeypatch) -> None:
    canonical = ROOT / "skills/lhc-rollout/scripts/lhc_rollout.py"
    spec = importlib.util.spec_from_file_location("lhc_rollout_ssh_test", canonical)
    assert spec is not None and spec.loader is not None
    rollout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rollout)

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "identity.json").write_text(
        json.dumps({"version": "abc1234"}) + "\n", encoding="utf-8"
    )
    (bundle / "payload").write_text("fixture\n", encoding="utf-8")
    remote = "/srv/operator/project/.tmp/lhc-rollout/incoming/abc1234-123"
    calls: list[list[str]] = []

    def fake_run(command, *, input_text=None, timeout=300):
        del input_text, timeout
        value = list(command)
        calls.append(value)
        if value[0] == "scp":
            return subprocess.CompletedProcess(value, 0, "", "")
        remote_command = value[-1]
        if "sh -c" in remote_command:
            return subprocess.CompletedProcess(value, 0, remote + "\n", "")
        if "remote-preview" in remote_command:
            report = rollout.REPORT_PREFIX + json.dumps({"name": "fake"}) + "\n"
            return subprocess.CompletedProcess(value, 0, report, "")
        return subprocess.CompletedProcess(value, 0, "", "")

    monkeypatch.setattr(rollout, "_run", fake_run)
    result = rollout._remote_call(
        "preview",
        {
            "name": "fake",
            "transport": "ssh",
            "sshTarget": "fake-host",
            "home": "/srv/operator",
            "projectRoot": "project",
            "python": "python3",
        },
        bundle,
        {},
    )

    assert result == {"name": "fake"}
    rendered = "\n".join(" ".join(call) for call in calls)
    assert ".agent-harness-sync" not in rendered
    assert "/.tmp/lhc-rollout/incoming/" in rendered
    assert "check-ignore --quiet -- .tmp/" in rendered
    assert '[ ! -L "$tmp" ]' in rendered
    scp = next(call for call in calls if call[0] == "scp")
    assert scp[-1] == f"fake-host:{remote}/"


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
