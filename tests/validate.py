#!/usr/bin/env python3
"""Validate the LHC v2 contract: minimal path, time truth, real-surface tests, no secret theater."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("Lead", "Overseer", "Worker", "Tester", "Reviewer")
REMOVED_ROLES = ("Adviser", "Critic")
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
    "lhc-rollout",
    "lhc-update-agents",
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
tester = text("src/common/agents/Tester.md")
reviewer = text("src/common/agents/Reviewer.md")
planning = text("src/common/profiles/Planning.md")
code = text("src/common/profiles/Code.md")
test_profile = text("src/common/profiles/Test.md")
research = text("src/common/protocols/WORKER_RESEARCH.md")
implement = text("src/common/protocols/WORKER_IMPLEMENT.md")
control = text("src/common/protocols/STOP_RETHINK.md")
time_control = text("src/common/protocols/TIME_CONTROL.md")
self_improve = text("src/common/protocols/SELF_IMPROVE.md")
workspace = text("src/common/protocols/SHARED_WORKTREE.md")
shared_session = text("docs/shared-session-abstraction.md")
authoring = text("docs/agent-authoring.md")
task_template = text("src/common/templates/.agents/tasks/task_template.md")
full_cycle = text("templates/FULL_CYCLE.md")
release = text("templates/RELEASE_HANDOFF.md")

if router != claude:
    fail("AGENTS.md and CLAUDE.md must stay byte-identical marker routers")

## Role set: exactly the four v2 roles, removed roles stay gone.
for role in ROLES:
    text(f"src/common/agents/{role}.md")
    require(router, f"- {role}: `src/common/agents/{role}.md`", "AGENTS.md")
for role in REMOVED_ROLES:
    if (ROOT / "src/common/agents" / f"{role}.md").exists():
        fail(f"removed role file still present: src/common/agents/{role}.md")

## Secret-theater infrastructure stays deleted.
for removed in (
    "src/common/capabilities",
    "plugins/ask-secret",
    "src/common/tools/install_http_capabilities.py",
    "scripts/install_http_capabilities.py",
    "tests/test_install_http_capabilities.py",
):
    if (ROOT / removed).exists():
        fail(f"secret-theater path still present: {removed}")

## Business-first ordering in Lead.
require_before(
    lead,
    "Business value is the first routing input.",
    "Choose the least-cost sufficient execution mode",
    "Lead.md",
)
for phrase in (
    "Trace the actual production consumer path before choosing an implementation surface.",
    "Lead may research and implement directly whenever delegation would cost more",
    "Proof strength matches the exact claim the user needs now.",
    "An accepted MVP or 80/20 definition remains the Definition of Done",
    "Gates are tools, not milestones.",
):
    require(lead, phrase, "Lead.md")

## Minimal path is mandatory.
for source, value in (
    ("AGENTS.md", router),
    ("Lead.md", lead),
    ("docs/agent-authoring.md", authoring),
):
    require(value, "three-line minimal path", source)
require(router, "smallest YAGNI vertical slice", "AGENTS.md")
require(lead, "discard list", "Lead.md")

## Secrets are not work.
for source, value in (("AGENTS.md", router), ("Lead.md", lead)):
    require(value, "Secrets are not work", source)
    require(value, "environment variable", source)

## Gates v2: supreme Overseer plus mandatory real-surface Tester.
require(router, "Overseer is the supreme route controller", "AGENTS.md")
require(router, "Overseer, Tester, and Reviewer are the only gates", "AGENTS.md")
require(reviewer, "risk-triggered", "Reviewer.md")
require(reviewer, "APPROVE", "Reviewer.md")
require(overseer, "supreme route controller", "Overseer.md")
require(overseer, "Security theater is the canonical drift", "Overseer.md")
require(overseer, "Started at", "Overseer.md")
require(tester, "mandatory final gate for user-facing results", "Tester.md")
require(tester, "Use the real surface", "Tester.md")
require(tester, "never prove a user-facing result", "Tester.md")
require(lead, "Test files never substitute", "Lead.md")
skill_rut = text("skills/real-use-testing/SKILL.md")
for source, value in (("Tester.md", tester), ("real-use-testing", skill_rut)):
    for phrase in ("Accessibility tree", "browserclaw", "touchpoint", "agent-browser", "Playwright", "XY"):
        require(value, phrase, source)
require(lead + router, "/secret", "secret handoff contract")
require(router, "never echoes the value", "AGENTS.md")
require(router, "AskHuman", "AGENTS.md")
require(router, "Never routine confirmations", "AGENTS.md")
require(lead, "AskHuman", "Lead.md")

## Checkpoint, join, and worker-question semantics.
checkpoint_sources = {
    "AGENTS.md": router,
    "Lead.md": lead,
    "Worker.md": worker,
    "Overseer.md": overseer,
    "Planning.md": planning,
    "STOP_RETHINK.md": control,
}
aggregate = "\n".join(checkpoint_sources.values())
for phrase in (
    "Every 20 active minutes is a control checkpoint, not a Worker lifetime limit.",
    "Prefer redirecting or resuming the same Worker",
    "Cancellation is exceptional",
):
    require(aggregate, phrase, "checkpoint contract")
for phrase in (
    "ask L at every decision boundary",
    "recommendation and proposed default",
    "non-blocking parent transport",
    "continue safe independent work while waiting",
    "L owns the decision",
):
    require(lead + worker, phrase, "worker question contract")
require(lead, "Do not send the final answer while a required child result remains non-terminal", "Lead.md")

## Time truth: start anchor, estimates, hourly report.
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
for phrase in ("Start anchor", "Started at", "manual clock", "lhc_time_guard.py", "не контролировал"):
    require(time_control, phrase, "TIME_CONTROL.md")
for phrase in (
    "At every crossed wall-clock hour while the task remains active",
    "Какие реальные задачи закрыты",
    "Завершённые файлы",
    "Какие гейты или инструкции задерживают бизнес-результат",
):
    require(lead + time_control + task_template, phrase, "business time-control contract")

## Compaction continuity stays bounded.
for phrase in (
    "current-handoff.md",
    "not append-only",
    "last three marks",
    "Compaction count",
):
    require(lead + worker + time_control + task_template, phrase, "compaction continuity contract")

## Self-evolution loop: patch, canary, reviewed commit, bounded iterations.
for phrase in (
    "minimal proposed patch",
    "verification canary",
    "one reviewed commit",
    "three refinement iterations",
):
    require(self_improve, phrase, "SELF_IMPROVE.md")
require(lead, "Self-evolution", "Lead.md")

## Workspace boundaries remain intact.
## Unified history: review every path, repair blockers, end clean and pushed.
for phrase in (
    "current primary project checkout",
    "git worktree list --porcelain",
    "first user-visible update",
    "<primary-project-root>/.worktrees/<task-slug>",
    "Never create project worktrees in `/tmp`",
    "Unified history",
    "review every change",
    "fix every unsafe or unreviewable item",
    "clean repositories",
):
    require(workspace, phrase, "SHARED_WORKTREE.md")
require(router, "Commit task-owned files at every completed step", "AGENTS.md")
require(router, "fixes unsafe or unreviewable", "AGENTS.md")
require(router, "pushed, deployed where deployable", "AGENTS.md")
require(lead, "clean tree", "Lead.md")
require(task_template, "Pushed (Full cycle):", "task template")
require(task_template, "Tree clean (nothing uncommitted):", "task template")
require(full_cycle, "Tree clean / pushed / deployed", "FULL_CYCLE.md")
require(text(".gitignore"), ".worktrees/", ".gitignore")

## Temporary project material never escapes the project-local ignored root.
temporary_contract = router + "\n" + workspace + "\n" + code
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
    require(temporary_contract, phrase, "project-local temporary storage contract")
require(text(".gitignore"), ".tmp/", ".gitignore")
pytest_config = text("conftest.py")
for phrase in (
    'f"pytest-{os.getpid()}-{secrets.token_hex(8)}"',
    "must not be a symlink",
    "escapes project root",
    '"check-ignore", "--quiet", "--", ".tmp/"',
):
    require(pytest_config, phrase, "conftest.py")

## Secret theater and removed-role contracts may not re-enter any behavior surface.
behavior_paths = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/agent-authoring.md",
    "docs/shared-session-abstraction.md",
    "src/common/agents/Lead.md",
    "src/common/agents/Worker.md",
    "src/common/agents/Overseer.md",
    "src/common/agents/Tester.md",
    "src/common/profiles/Planning.md",
    "src/common/profiles/Code.md",
    "src/common/profiles/Test.md",
    "src/common/protocols/WORKER_RESEARCH.md",
    "src/common/protocols/WORKER_IMPLEMENT.md",
    "src/common/protocols/STOP_RETHINK.md",
    "src/common/protocols/TIME_CONTROL.md",
    "src/common/protocols/SELF_IMPROVE.md",
    "templates/FULL_CYCLE.md",
    "templates/RELEASE_HANDOFF.md",
    "src/common/templates/.agents/tasks/task_template.md",
] + [f"adapters/{adapter}/templates/subagent.md" for adapter in ADAPTERS] + [
    f"adapters/{adapter}/instructions.md" for adapter in ADAPTERS
] + ["adapters/README.md"]
obsolete = (
    # secret theater
    "AskSecret/SSS",
    "opaque registered-agent",
    "base64 fallback",
    "NoticePlace capability",
    "attested human-request capability",
    "ask_secret_transport",
    "human.ask_secret",
    "human.ask_user",
    "attested AskSecret",
    # forced-confirmation ceremony (AskHuman itself is sanctioned)
    "confirmation for every",
    # removed roles as required gates
    "Adviser, Critic",
    "Reviewer, Tester, Overseer, or Critic",
    # fragmented-history regressions
    "Stage and commit only task-owned paths",
    "Commit, only if requested",
    # old process rituals
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

## Adapter contracts stay complete, local, and secret-theater-free.
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
    require(adapter_instructions, "Secrets are not work", f"{adapter}/instructions.md")
    require(adapter_manifest, "nonblocking_parent_transport:", f"{adapter}/adapter.yaml")
    require(adapter_manifest, "lifecycle_time_guard_hook:", f"{adapter}/adapter.yaml")
    for key in ("role_source", "optional_instructions", "subagent_instructions_template"):
        match = re.search(rf"^{key}:\s*(.+)$", adapter_manifest, re.MULTILINE)
        if not match or not (base / match.group(1).strip()).exists():
            fail(f"{adapter} manifest has invalid {key}")

## Canonical skills stay identical to their generated plugin copies.
for skill in SKILLS:
    source = ROOT / "skills" / skill / "SKILL.md"
    generated = ROOT / "plugins" / "last-human-commit" / "skills" / skill / "SKILL.md"
    if not source.is_file() or not generated.is_file():
        fail(f"missing canonical/generated skill: {skill}")
    if source.read_bytes() != generated.read_bytes():
        fail(f"generated skill differs from source: {skill}")

rollout_source = ROOT / "skills/lhc-rollout/scripts/lhc_rollout.py"
rollout_generated = ROOT / "plugins/last-human-commit/skills/lhc-rollout/scripts/lhc_rollout.py"
if rollout_source.read_bytes() != rollout_generated.read_bytes():
    fail("generated lhc-rollout script differs from source")
for relative in (
    "assets/last-human-commit-fleet.json",
    "references/manifest.md",
):
    source = ROOT / "skills/lhc-rollout" / relative
    generated = ROOT / "plugins/last-human-commit/skills/lhc-rollout" / relative
    if source.read_bytes() != generated.read_bytes():
        fail(f"generated lhc-rollout {relative} differs from source")

fleet = json.loads(text("skills/lhc-rollout/assets/last-human-commit-fleet.json"))
for target in fleet.get("targets", []):
    if not isinstance(target.get("projectRoot"), str) or not target["projectRoot"].strip():
        fail(f"fleet target {target.get('name')} lacks projectRoot")
manifest_reference = text("skills/lhc-rollout/references/manifest.md")
for phrase in (
    '"projectRoot": "gptadmin"',
    "<home>/<projectRoot>/.tmp/lhc-rollout/incoming/",
    "must not be a symlink",
    "different Git top-level",
):
    require(manifest_reference, phrase, "lhc-rollout manifest reference")
rollout_text = rollout_source.read_text(encoding="utf-8")
for phrase in (
    "target.projectRoot",
    "check-ignore",
    'case "$tmp/" in "$project/"*',
    '[ ! -L "$tmp" ]',
):
    require(rollout_text, phrase, "lhc-rollout project-local staging")
forbid(rollout_text, ".agent-harness-sync", "lhc-rollout project-local staging")

## Run the narrow behavioral validators owned by this repository.
def run_quiet(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        print(completed.stdout[-4000:], file=sys.stderr)
        print(completed.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"FAIL: nested validator failed: {' '.join(command)}")

run_quiet([sys.executable, "-m", "pytest", "-q", "tests/test_business_first_contract.py"])
run_quiet([sys.executable, "-m", "pytest", "-q", "tests/test_time_guard.py"])
run_quiet([sys.executable, "-m", "py_compile", str(time_guard)])
run_quiet(["sh", str(ROOT / "tests/test_block_adapter.sh")])

print(
    f"PASS: minimal path, supreme Overseer, real-surface Tester, time anchors, "
    f"self-evolution loop, {len(ROLES)} roles, {len(ADAPTERS)} adapters, "
    f"zero secret theater"
)
