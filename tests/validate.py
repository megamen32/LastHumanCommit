#!/usr/bin/env python3
"""Validate the business-first, least-cost Last Human Commit contract."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("Lead", "Overseer", "Adviser", "Critic", "Worker", "Reviewer", "Tester")
ADAPTERS = ("codex", "opencode", "claude-code", "hermes", "zcode")
SKILLS = (
    "planning",
    "bugfix-tdd",
    "feature-implementation",
    "real-use-testing",
    "business-delivery",
    "release",
    "task-decomposition",
    "worker-research",
    "worker-code",
    "worker-bugfix",
)


def fail(message: str) -> None:
    """Exit with one concise validation failure."""

    raise SystemExit(f"FAIL: {message}")


def text(relative: str) -> str:
    """Read one required repository file."""

    path = ROOT / relative
    if not path.is_file():
        fail(f"missing file: {relative}")
    return path.read_text(encoding="utf-8")


def compact(value: str) -> str:
    """Normalize prose wrapping for semantic phrase checks."""

    return " ".join(value.split())


def require(value: str, phrase: str, source: str) -> None:
    """Require one semantic phrase after whitespace normalization."""

    if compact(phrase).casefold() not in compact(value).casefold():
        fail(f"{source} lacks: {phrase}")


def forbid(value: str, phrase: str, source: str) -> None:
    """Reject one obsolete semantic phrase after whitespace normalization."""

    if compact(phrase).casefold() in compact(value).casefold():
        fail(f"{source} contains obsolete contract: {phrase}")


def require_before(value: str, first: str, second: str, source: str) -> None:
    """Require business ordering rather than mere phrase presence."""

    normalized = compact(value).casefold()
    first_index = normalized.find(compact(first).casefold())
    second_index = normalized.find(compact(second).casefold())
    if first_index < 0 or second_index < 0 or first_index >= second_index:
        fail(f"{source} must place {first!r} before {second!r}")


router = text("AGENTS.md")
claude = text("CLAUDE.md")
lead = text("src/common/agents/Lead.md")
worker = text("src/common/agents/Worker.md")
overseer = text("src/common/agents/Overseer.md")
reviewer = text("src/common/agents/Reviewer.md")
tester = text("src/common/agents/Tester.md")
critic = text("src/common/agents/Critic.md")
adviser = text("src/common/agents/Adviser.md")
planning = text("src/common/profiles/Planning.md")
code = text("src/common/profiles/Code.md")
test_profile = text("src/common/profiles/Test.md")
research = text("src/common/protocols/WORKER_RESEARCH.md")
implement = text("src/common/protocols/WORKER_IMPLEMENT.md")
control = text("src/common/protocols/STOP_RETHINK.md")
time_control = text("src/common/protocols/TIME_CONTROL.md")
workspace = text("src/common/protocols/SHARED_WORKTREE.md")
shared_session = text("docs/shared-session-abstraction.md")
task_template = text("src/common/templates/.agents/tasks/task_template.md")
full_cycle = text("templates/FULL_CYCLE.md")
release = text("templates/RELEASE_HANDOFF.md")
readme = text("README.md")
authoring = text("docs/agent-authoring.md")
audit = text("docs/business-first-error-audit.md")

# Portable router and role ownership.
if router.encode() != claude.encode():
    fail("AGENTS.md and CLAUDE.md must be byte-identical")
for marker in ("<!-- last-human-commit:begin -->", "<!-- last-human-commit:end -->"):
    if router.splitlines().count(marker) != 1:
        fail(f"router needs exactly one {marker}")
for role in ROLES:
    require(router, f"{role}: `src/common/agents/{role}.md`", "AGENTS.md")
    text(f"src/common/agents/{role}.md")

# Business logic must precede execution/process routing.
require_before(
    lead,
    "Business value is the first routing input.",
    "Choose the least-cost sufficient execution mode",
    "Lead.md",
)
for source, value in (("AGENTS.md", router), ("Lead.md", lead)):
    for phrase in (
        "Business value is the first routing input",
        "actual production consumer path",
        "least-cost sufficient execution mode",
        "accepted MVP",
        "Gates are tools, not milestones",
    ):
        require(value, phrase, source)
require(lead, "Lead may research and implement directly whenever delegation would cost more", "Lead.md")
require(lead, "Proof strength matches the exact claim the user needs now", "Lead.md")
require(code, "Trace the real production consumer", "Code.md")
require(test_profile, "Choose the cheapest evidence sufficient for the exact claim", "Test.md")
require(implement, "smallest coherent vertical change on the real path", "WORKER_IMPLEMENT.md")
require(research, "Trace the actual production consumer path", "WORKER_RESEARCH.md")

# Twenty minutes is management, not process death.
checkpoint_sources = {
    "AGENTS.md": router,
    "Lead.md": lead,
    "Worker.md": worker,
    "Overseer.md": overseer,
    "Planning.md": planning,
    "STOP_RETHINK.md": control,
    "FULL_CYCLE.md": full_cycle,
}
for source, value in checkpoint_sources.items():
    require(value, "20 active minutes", source)
require(router, "Every 20 active minutes is a control checkpoint, not a Worker lifetime limit", "AGENTS.md")
require(worker, "The expected total range may exceed 20 minutes", "Worker.md")
require(planning, "The expected total range may exceed 20 minutes", "Planning.md")
require(overseer, "Prefer redirecting or resuming the same Worker", "Overseer.md")
require(control, "Cancellation is exceptional", "STOP_RETHINK.md")

# Worker asks Lead without blocking independent progress.
for phrase in (
    "Ask L at every decision boundary",
    "recommendation and proposed default",
    "non-blocking parent transport",
    "continue safe independent work while waiting",
    "L owns the decision",
):
    require(worker + lead, phrase, "Lead/Worker decision feedback contract")
forbid(worker, "stop all work until L answers", "Worker.md")

# Required children are really joined and managed.
codex_instructions = text("adapters/codex/instructions.md")
codex_template = text("adapters/codex/templates/subagent.md")
for source, value in (("Lead.md", lead), ("Codex template", codex_template)):
    require(value, "Use the harness wait/join tool", source)
    require(value, "Do not send the final answer while a required child result remains non-terminal", source)
for phrase in (
    "deadline = monotonicNow() + 1800000 ms",
    "remainingMs = deadline - monotonicNow()",
    "preserve the child",
    "start another join window",
    "Never call `close_agent`",
):
    require(lead + codex_template + codex_instructions, phrase, "Codex join contract")

# Governance is selected by risk/value rather than route classification.
for source, value in (
    ("Lead.md", lead),
    ("Overseer.md", overseer),
    ("Reviewer.md", reviewer),
    ("Tester.md", tester),
    ("Critic.md", critic),
    ("Adviser.md", adviser),
):
    require(value, "optional" if source != "Lead.md" else "risk-triggered", source)
require(router, "Overseer, Adviser, Critic, Reviewer, and Tester are risk-triggered", "AGENTS.md")
require(reviewer, "accepted business claim", "Reviewer.md")
require(tester, "Match evidence to the claim", "Tester.md")
require(critic, "accepted Definition of Done", "Critic.md")
require(adviser, "do not manufacture a third plan", "Adviser.md")

# Persistence is cost-triggered and compact.
require(research, "Persist research when handoff, recovery, reuse, or the cost of rediscovery justifies it", "WORKER_RESEARCH.md")
require(shared_session, "No elapsed-time threshold by itself requires a file or Git commit", "shared-session abstraction")
require(task_template, "Accepted business outcome / Definition of Done", "task template")
require(task_template, "Why this is least-cost", "task template")
require(full_cycle, "Record exactly two genuinely different approaches", "FULL_CYCLE.md")
require(planning, "exactly two genuinely different approaches", "Planning.md")
require(planning, "ideal/full -> normal -> YAGNI/Pareto MVP", "Planning.md")
decomposition = text("skills/task-decomposition/SKILL.md")
for phrase in (
    "smallest independent, parallel, business-verifiable slices",
    "one owner, one output or business proof",
    "5–20 active minutes per leaf",
    "non-blocking parent transport",
):
    require(decomposition, phrase, "task-decomposition skill")

# Every declared cycle is estimated and time-controlled.
time_guard = ROOT / "src/common/tools/lhc_time_guard.py"
if not time_guard.is_file() or not time_guard.stat().st_mode & 0o111:
    fail("src/common/tools/lhc_time_guard.py must exist and be executable")
for source, value in (
    ("Lead.md", lead),
    ("Planning.md", planning),
    ("TIME_CONTROL.md", time_control),
    ("task template", task_template),
):
    require(value, "Every declared work cycle", source)
    require(value, "minimum / maximum", source)
for phrase in (
    "At every crossed wall-clock hour while the task remains active",
    "Какие реальные задачи закрыты",
    "Завершённые файлы",
    "Какие гейты или инструкции задерживают бизнес-результат",
    "lhc_time_guard.py",
):
    require(lead + time_control + task_template, phrase, "business time-control contract")
for phrase in (
    "current-handoff.md",
    "not append-only",
    "last three marks",
    "Compaction count",
):
    require(lead + worker + time_control + task_template, phrase, "compaction continuity contract")

# Old executable process contracts may not re-enter any behavior surface.
behavior_paths = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/agent-authoring.md",
    "docs/shared-session-abstraction.md",
    "src/common/agents/Lead.md",
    "src/common/agents/Worker.md",
    "src/common/agents/Overseer.md",
    "src/common/agents/Reviewer.md",
    "src/common/agents/Tester.md",
    "src/common/agents/Critic.md",
    "src/common/agents/Adviser.md",
    "src/common/profiles/Planning.md",
    "src/common/protocols/WORKER_RESEARCH.md",
    "src/common/protocols/WORKER_IMPLEMENT.md",
    "src/common/protocols/STOP_RETHINK.md",
    "src/common/protocols/TIME_CONTROL.md",
    "templates/FULL_CYCLE.md",
    "src/common/templates/.agents/tasks/task_template.md",
] + [f"adapters/{adapter}/templates/subagent.md" for adapter in ADAPTERS] + [
    f"adapters/{adapter}/instructions.md" for adapter in ADAPTERS
] + ["adapters/README.md"]
obsolete = (
    "Overseer is mandatory for every task",
    "For Short and Full work I do not search the repository or write code",
    "L does not search the repository or write code",
    "maximum five active minutes",
    "maximum <=20 active minutes",
    "Reject any Worker assignment above 20 minutes",
    "proposed Worker assignment exceeds 20",
    "Draft exactly three Russian plans, always",
    "Планы — всегда ровно три",
    "invoke exactly two fresh Testers",
    "run exactly two fresh Testers",
    "After 10 active minutes",
    "must include a Git commit",
    "After 3 active minutes of research orientation",
    "after the first concrete Worker result",
    "After each wave run focused checks, Reviewer",
)
for relative in behavior_paths:
    value = text(relative)
    for phrase in obsolete:
        forbid(value, phrase, relative)

# Adapter contracts and generated skill source are complete and local.
manifest = text("adapters/manifest.yaml")
require(manifest, "tools: src/common/tools", "adapters/manifest.yaml")
for adapter in ADAPTERS:
    base = ROOT / "adapters" / adapter
    adapter_manifest = text(f"adapters/{adapter}/adapter.yaml")
    adapter_instructions = text(f"adapters/{adapter}/instructions.md")
    template = text(f"adapters/{adapter}/templates/subagent.md")
    require(manifest, f"adapters/{adapter}/adapter.yaml", "adapters/manifest.yaml")
    require(adapter_manifest, f"harness: {adapter}", f"{adapter}/adapter.yaml")
    require(adapter_instructions, "templates/subagent.md", f"{adapter}/instructions.md")
    require(template, "lowest sufficient", f"{adapter}/templates/subagent.md")
    require(template, "expected total range may exceed 20 minutes", f"{adapter}/templates/subagent.md")
    require(template, "20-minute reporting checkpoint", f"{adapter}/templates/subagent.md")
    require(template, "non-blocking parent transport", f"{adapter}/templates/subagent.md")
    require(template, "lhc_time_guard.py", f"{adapter}/templates/subagent.md")
    require(template, "не контролировал", f"{adapter}/templates/subagent.md")
    require(template, "current-handoff.md", f"{adapter}/templates/subagent.md")
    require(adapter_manifest, "nonblocking_parent_transport:", f"{adapter}/adapter.yaml")
    require(adapter_manifest, "lifecycle_time_guard_hook:", f"{adapter}/adapter.yaml")
    for key in ("role_source", "optional_instructions", "subagent_instructions_template"):
        match = re.search(rf"^{key}:\s*(.+)$", adapter_manifest, re.MULTILINE)
        if not match or not (base / match.group(1).strip()).exists():
            fail(f"{adapter} manifest has invalid {key}")

for skill in SKILLS:
    source = ROOT / "skills" / skill / "SKILL.md"
    generated = ROOT / "plugins" / "last-human-commit" / "skills" / skill / "SKILL.md"
    if not source.is_file() or not generated.is_file():
        fail(f"missing canonical/generated skill: {skill}")
    if source.read_bytes() != generated.read_bytes():
        fail(f"generated skill differs from source: {skill}")

# Existing safety boundaries remain independent of optional governance.
for phrase in (
    "current primary project checkout",
    "git worktree list --porcelain",
    "first user-visible update",
    "<primary-project-root>/.worktrees/<task-slug>",
    "Never create project worktrees in `/tmp`",
    "Never stage or commit foreign edits",
):
    require(workspace, phrase, "SHARED_WORKTREE.md")
require(text(".gitignore"), ".worktrees/", ".gitignore")
ask_secret = text("src/common/capabilities/human.ask_secret.v1.yaml")
for phrase in (
    "registered-agent SSS handoff",
    "Opaque handle is never secret plaintext",
    "Plaintext and base64 fallback delivery are rejected",
):
    require(ask_secret, phrase, "human.ask_secret.v1.yaml")
for phrase in ("state: available", "provider: AskSecret", "transport: streamable_http", "ask_secret_run"):
    require(ask_secret, phrase, "human.ask_secret.v1.yaml")
ask_human = text("src/common/capabilities/human.ask_user.v1.yaml")
for phrase in ("state: available", "provider: AskHuman", "transport: streamable_http", "ask_human"):
    require(ask_human, phrase, "human.ask_user.v1.yaml")
installer = ROOT / "src/common/tools/install_http_capabilities.py"
if not installer.is_file():
    fail("src/common/tools/install_http_capabilities.py must exist")
for adapter in ADAPTERS:
    instructions = text(f"adapters/{adapter}/instructions.md")
    for phrase in ("AskHuman", "AskSecret/SSS", "opaque registered-agent", "plaintext", "base64 fallback"):
        require(instructions, phrase, f"{adapter}/instructions.md")

# The requested analysis remains a substantial, explicit causal audit.
if len(re.findall(r"^\d+\.", audit, re.MULTILINE)) < 200:
    fail("business-first error audit must retain at least 200 numbered errors")
require(audit, "Общий диагноз", "business-first error audit")
require(audit, "Новый обязательный порядок", "business-first error audit")

# Run the narrow behavioral validators owned by this repository.
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_business_first_contract.py"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_time_guard.py"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "-m", "py_compile", str(time_guard)], cwd=ROOT, check=True)
subprocess.run(["sh", str(ROOT / "tests/test_block_adapter.sh")], cwd=ROOT, check=True)

print(
    f"PASS: business-first order, least-cost routing, checkpoint/join semantics, "
    f"{len(ROLES)} optional roles, {len(ADAPTERS)} adapters, and safety boundaries"
)
