#!/usr/bin/env python3
"""Validate the dependency-free Last Human Commit instruction contract."""

from __future__ import annotations

from pathlib import Path
import hashlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("Lead", "Overseer", "Adviser", "Critic", "Worker", "Reviewer", "Tester")
ADAPTERS = ("codex", "opencode", "claude-code", "hermes", "zcode")


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        fail(f"missing file: {path}")
    return target.read_text(encoding="utf-8")


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def require(value: str, phrase: str, source: str) -> None:
    if normalized(phrase) not in normalized(value):
        fail(f"{source} lacks: {phrase}")


def forbid(value: str, phrase: str, source: str) -> None:
    if normalized(phrase) in normalized(value):
        fail(f"{source} contains forbidden text: {phrase}")


def require_before(value: str, first: str, second: str, source: str) -> None:
    a = normalized(value).find(normalized(first))
    b = normalized(value).find(normalized(second))
    if a < 0 or b < 0 or a >= b:
        fail(f"{source} must place {first!r} before {second!r}")


router = text("AGENTS.md")
claude = text("CLAUDE.md")
lead = text("src/common/agents/Lead.md")
worker = text("src/common/agents/Worker.md")
oversee = text("src/common/agents/Overseer.md")
critic = text("src/common/agents/Critic.md")
reviewer = text("src/common/agents/Reviewer.md")
tester = text("src/common/agents/Tester.md")
adviser = text("src/common/agents/Adviser.md")
planning = text("src/common/profiles/Planning.md")
code = text("src/common/profiles/Code.md")
workspace = text("src/common/protocols/SHARED_WORKTREE.md")
stop = text("src/common/protocols/STOP_RETHINK.md")
research = text("src/common/protocols/WORKER_RESEARCH.md")
implement = text("src/common/protocols/WORKER_IMPLEMENT.md")
self_improve = text("src/common/protocols/SELF_IMPROVE.md")
task_template = text("src/common/templates/.agents/tasks/task_template.md")
full_cycle = text("templates/FULL_CYCLE.md")
release = text("templates/RELEASE_HANDOFF.md")
readme = text("README.md")
authoring = text("docs/agent-authoring.md")
adapters_readme = text("adapters/README.md")
roadmap = text("ROADMAP.md")

# Marker router and exact role boundary.
if router.encode() != claude.encode():
    fail("AGENTS.md and CLAUDE.md must be byte-identical")
for marker in ("<!-- last-human-commit:begin -->", "<!-- last-human-commit:end -->"):
    if router.splitlines().count(marker) != 1:
        fail(f"AGENTS.md needs exactly one {marker}")
for role in ROLES:
    require(router, f"{role}: `src/common/agents/{role}.md`", "AGENTS.md")
    if not (ROOT / f"src/common/agents/{role}.md").is_file():
        fail(f"missing role: src/common/agents/{role}.md")
if (ROOT / "src/common/agents/Explorer.md").exists():
    fail("Explorer.md must be replaced by Worker research mode")

for phrase in (
    "Routine work stays in the current primary checkout",
    "first user-visible update must warn the user",
    "<primary-project-root>/.worktrees/<task-slug>",
    "children append detailed evidence",
    "children never create a second task card",
    "minimum / maximum active minutes",
    "L is an orchestrator by default",
    "maximum five active minutes",
    "mode: research",
    "mode: implement",
    "maximum <=20 active minutes",
    "Full always uses three plans and two explicit human approvals",
    "Overseer is mandatory for every task",
    "Event-triggered audits cannot be suppressed by a 30-minute cooldown",
    "Silence never authorizes them",
):
    require(router, phrase, "AGENTS.md")

# Lead is an orchestrator while Full preserves the expensive human layer.
for phrase in (
    "For Short and Full work I do not search the repository or write code",
    "maximum five active minutes",
    "Worker research confirms both development over 30 active minutes",
    "maximum <=20 active minutes",
    "one unresolved block above one hour requires more research",
    "There is no separate Explorer role",
    "root task path",
    "after the first concrete Worker result",
    "after research and before the three plans",
    "after every implementation wave or selected delivery stage",
    "Thirty minutes is an extra trigger, never a cooldown",
    "Present exactly three Russian plans, always",
    "Максимально идеальный",
    "Нормальный",
    "YAGNI 80/20",
    "call-stack tree",
    "file-tree diff",
    "key types and method signatures",
    "pseudocode",
    "migration description",
    "execution graph",
    "second explicit approval",
    "not three branches, worktrees, specifications, or throwaway rewrites",
    "fresh Tester",
    "invoke fresh Critic once",
    "never silently include foreign edits",
    "AskSecret/SSS",
    "silence means pending",
    "only when its trigger occurred",
):
    require(lead, phrase, "Lead.md")
require_before(lead, "invoke a fresh Tester", "invoke fresh Critic once", "Lead.md")
for bad in (
    "optimistic / likely / pessimistic",
    "Later audits are allowed only after 30 minutes",
    "Before every final answer",
    "creates the cheapest sufficient Worker package, normally on",
):
    forbid(lead, bad, "Lead.md")

# Worker modes and strict bounded ownership.
for phrase in (
    "`mode: research` or `mode: implement`",
    "maximum <=20",
    "assigned task-file contract",
    "append detailed evidence",
    "NEEDS_REDECOMPOSITION",
    "NEEDS_RETHINK",
    "Do not silently extend the estimate",
    "Do not report a SHA unless a commit was actually requested and created",
):
    require(worker, phrase, "Worker.md")
for phrase in (
    "read-only",
    "execution graph of independent slices",
    "maximum <=20",
    "NEEDS_MORE_RESEARCH",
    "Do not write code",
):
    require(research, phrase, "WORKER_RESEARCH.md")
for phrase in (
    "Bugfix / TDD",
    "Feature",
    "Reproduce the real reported symptom",
    "thinnest working vertical slice",
    "Never write a test merely to satisfy ceremony",
    "stop and return to research",
):
    require(implement, phrase, "WORKER_IMPLEMENT.md")

# Fresh oversight, review, real-user test, and release gate.
for phrase in (
    "fresh, independent route auditor",
    "never resumed",
    "raw user request",
    "Reject any Worker assignment above 20 minutes",
    "current maximum is exceeded",
    "default to `RETHINK`",
    "never a cooldown",
    "VERDICT: CONTINUE | RETHINK | ASK_USER | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT",
):
    require(oversee, phrase, "Overseer.md")
for phrase in (
    "fresh no-history child",
    "Raw user context is passed explicitly",
    "PASS",
    "STOP_MISSING_CONTEXT",
):
    require(critic, phrase, "Critic.md")
for phrase in (
    "task-owned diff",
    "Never touch, stage, or propose silently including foreign edits",
    "smallest bounded fix",
    "<=20-minute Worker slice",
    "append detailed review evidence",
):
    require(reviewer, phrase, "Reviewer.md")
for phrase in (
    "actual user-facing surface",
    "before the final Critic release gate",
    "`only-new` is mandatory",
    "append detailed real-use evidence",
    "Return only TL;DR",
    "STOP_MISSING_REAL_SURFACE",
):
    require(tester, phrase, "Tester.md")
require(adviser, "maximum 20 active minutes", "Adviser.md")

# Estimates and decomposition are two-value control limits, not output ceremony.
for phrase in (
    "minimum / maximum active minutes",
    "Do not add optimistic/likely/pessimistic variants",
    "fresh Overseer verdict",
    "Every Worker assignment has one mode, one acceptance gate, and maximum <=20",
    "whole plan may exceed 60 minutes only as a known graph",
    "single unresolved block above 60 minutes",
    "does not create a second task file",
    "Resume the same Worker",
):
    require(planning, phrase, "Planning.md")
for source, value in (
    ("Planning.md", planning),
    ("AGENTS.md", router),
    ("Lead.md", lead),
    ("FULL_CYCLE.md", full_cycle),
):
    forbid(value, "optimistic / likely / pessimistic", source)
for phrase in (
    "current minimum/maximum estimate is exceeded",
    "proposed Worker assignment exceeds 20",
    "one unresolved block is estimated above 60",
    "fresh Overseer audit",
    "Worker(mode=research)",
    "There is no Explorer role",
):
    require(stop, phrase, "STOP_RETHINK.md")

# Project-local workspace, immediate disclosure, and task-owned commits only.
for phrase in (
    "current primary project checkout",
    "git worktree list --porcelain",
    "first user-visible update",
    "<primary-project-root>/.worktrees/<task-slug>",
    "Never create project worktrees in `/tmp`",
    "git stash",
    "git reset",
    "git clean",
    "within five minutes",
    "Stage and commit only reviewed task-owned paths",
    "Never stage or commit foreign edits",
):
    require(workspace, phrase, "SHARED_WORKTREE.md")
for bad in (
    "may include it in the same commit",
    "older ones get final review and, when safe, are committed",
    "L assumes a shared worktree",
):
    forbid(workspace + readme + authoring, bad, "workspace policy")
require(text(".gitignore"), ".worktrees/", ".gitignore")

# Protect the user's deliberately strict Code profile byte-for-byte.
expected_code_sha256 = "ad84a4730acc89b720afaff0e0d5bf3b72457d51769e74af29bc1e6449682ecc"
actual_code_sha256 = hashlib.sha256((ROOT / "src/common/profiles/Code.md").read_bytes()).hexdigest()
if actual_code_sha256 != expected_code_sha256:
    fail(f"Code.md changed: expected {expected_code_sha256}, got {actual_code_sha256}")
for phrase in (
    "Prefer structured logs and rotate them",
    "Split code files over 800 lines",
    "Document every function, including private ones: inputs, outputs, errors",
    "Check cross-OS behavior before claiming portability",
    "Mark legacy or deprecated code explicitly as `LEGACY` or `DEPRECATED`, with a date and end-of-support target",
):
    require(code, phrase, "Code.md")

# One task file contains the full human layer and compact execution history.
for phrase in (
    "Initial estimate (minimum / maximum active minutes):",
    "Three plans — Full only",
    "Call-stack tree:",
    "File-tree diff:",
    "Key types and method signatures:",
    "Pseudocode:",
    "Migration description:",
    "Execution graph (each node: owner, paths, acceptance, dependencies, max <=20):",
    "Second explicit human approval",
    "Children append their detailed evidence and result to that file",
    "Overseer:",
    "Reviewer:",
    "Tester:",
    "Critic:",
    "Commit (only if created):",
):
    require(task_template, phrase, "task_template.md")
for phrase in (
    "development over 30 active minutes",
    "material product, architecture, migration, or expensive-wrong",
    "maximum <=20 active minutes",
    "Планы — всегда ровно три",
    "### 1. Максимально идеальный",
    "### 2. Нормальный",
    "### 3. YAGNI 80/20",
    "Call-stack tree:",
    "File-tree diff:",
    "Key types and method signatures:",
    "Pseudocode:",
    "Migration description:",
    "Second explicit approval",
    "not create three branches, worktrees, specifications",
    "run fresh Tester",
    "run Critic once",
):
    require(full_cycle, phrase, "FULL_CYCLE.md")
if full_cycle.count("### 1. Максимально идеальный") != 1 or full_cycle.count("### 2. Нормальный") != 1 or full_cycle.count("### 3. YAGNI 80/20") != 1:
    fail("FULL_CYCLE.md must contain exactly three plan headings")
require_before(full_cycle, "run fresh Tester", "run Critic once", "FULL_CYCLE.md")

# Self-improve is event-triggered, not a tax on every completion.
for phrase in (
    "triggered only when at least one concrete event occurred",
    "Ordinary successful tasks add nothing",
    "route materially failed, exceeded its maximum, or required RETHINK",
    "Hermes is excluded",
):
    require(self_improve, phrase, "SELF_IMPROVE.md")
for bad in (
    "mandatory for L after every",
    "Before every final answer",
):
    forbid(self_improve + lead, bad, "self-improve policy")

# Explicit deploy authorization only.
for phrase in (
    "Без явного `да` deploy не выполняется",
    "молчание не является разрешением",
    "pending + explicit да + current + single_serialized_L",
    "pending + due + unanswered",
    "pending (revalidate and remind only; never deploy)",
):
    require(release, phrase, "RELEASE_HANDOFF.md")
forbid(release, "pending + due + unanswered + current + single_serialized_L -> deploying", "RELEASE_HANDOFF.md")

# Public docs describe the same product rather than the reverted merge policy.
for source, value in (("README.md", readme), ("docs/agent-authoring.md", authoring)):
    for phrase in (
        "one Markdown",
        "orchestrator",
        "<=20",
        "Overseer",
        "three",
        "second explicit approval",
        ".worktrees/",
        "Tester",
        "ZCode",
    ):
        require(value, phrase, source)
for bad in (
    "later audits are no more frequent than every 30 minutes",
    "mandatory once for every task after the contract and selected plan",
    "L assumes a shared worktree",
    "older ones get final review and, when safe, are committed",
):
    forbid(readme + authoring, bad, "public docs")

# Human request contracts survive the merge and remain fail-closed.
ask_secret = text("src/common/capabilities/human.ask_secret.v1.yaml")
for phrase in (
    "requirement: required",
    "registered-agent SSS handoff",
    "Opaque handle is never secret plaintext",
    "Plaintext and base64 fallback delivery are rejected",
    "Render only when an exact Fleet or harness attestation is proven",
):
    require(ask_secret, phrase, "human.ask_secret.v1.yaml")
for adapter in ADAPTERS:
    instructions = text(f"adapters/{adapter}/instructions.md")
    for phrase in ("AskHuman", "AskSecret/SSS", "opaque registered-agent", "plaintext", "base64 fallback"):
        require(instructions, phrase, f"{adapter}/instructions.md")

# Adapter manifests and child templates preserve one root file, continuity, and fresh gates.
manifest_text = text("adapters/manifest.yaml")
require(manifest_text, "schema_version: 1", "adapters/manifest.yaml")
for adapter in ADAPTERS:
    base = ROOT / "adapters" / adapter
    manifest = text(f"adapters/{adapter}/adapter.yaml")
    instructions = text(f"adapters/{adapter}/instructions.md")
    template = text(f"adapters/{adapter}/templates/subagent.md")
    require(manifest, f"harness: {adapter}", f"{adapter}/adapter.yaml")
    require(manifest_text, f"adapters/{adapter}/adapter.yaml", "adapters/manifest.yaml")
    require(instructions, "templates/subagent.md", f"{adapter}/instructions.md")
    for phrase in (
        "lowest sufficient",
        "maximum <=20",
        "root task path",
        "child reads only the assigned task file",
        "appends detailed evidence",
        "same Worker",
        "Overseer and Critic are always",
        "Reviewer and Tester are fresh independent gates",
    ):
        require(template, phrase, f"{adapter}/templates/subagent.md")
    for old in (
        "Write one compact `todo-*.md`",
        "only L writes the root task file",
    ):
        forbid(template, old, f"{adapter}/templates/subagent.md")
    for key in ("role_source", "optional_instructions", "subagent_instructions_template"):
        match = re.search(rf"^{key}:\s*(.+)$", manifest, re.MULTILINE)
        if not match or not (base / match.group(1).strip()).exists():
            fail(f"{adapter} manifest has invalid {key}")
    if adapter != "hermes":
        require(manifest, "self_improve: event-triggered-core-protocol", f"{adapter}/adapter.yaml")
if "fork_context: true" in text("adapters/codex/templates/subagent.md"):
    fail("Codex template must never fork parent history")
require(text("adapters/codex/templates/subagent.md"), "fork_context: false", "Codex template")
require(text("adapters/codex/adapter.yaml"), "ask_secret_transport: sss-opaque-registered-agent", "Codex adapter")

plugin_source = text("adapters/hermes/plugin/__init__.py")
require(plugin_source, '"tester": "Tester"', "Hermes plugin")
forbid(plugin_source, '"explorer": "Explorer"', "Hermes plugin")
for profile_path in (
    "adapters/hermes/profile/README.md",
    "adapters/hermes/profile/LHC.md",
    "adapters/hermes/profile/LHC.v1.md",
):
    text(profile_path)
profile = text("adapters/hermes/profile/LHC.v1.md")
for phrase in ("native `clarify` tool is disabled", "Use AskHuman", "through AskSecret/SSS", "opaque handling only"):
    require(profile, phrase, "Hermes LHC profile")

# No uptime ritual or old per-child Task Card workflow remains in runtime policy.
runtime_paths = [
    "AGENTS.md", "CLAUDE.md", "README.md", "docs/agent-authoring.md",
    "src/common/agents/Lead.md", "src/common/agents/Worker.md",
    "src/common/agents/Overseer.md", "src/common/agents/Reviewer.md",
    "src/common/agents/Tester.md", "src/common/agents/Critic.md",
    "src/common/agents/Adviser.md", "src/common/profiles/Planning.md",
    "src/common/protocols/STOP_RETHINK.md", "templates/FULL_CYCLE.md",
]
for relative in runtime_paths:
    forbid(text(relative), "uptime", relative)

# Existing task files retain the one-file status matrix; minimal todo records are
# allowed for unselected defects and do not require a full status contract.
for path in sorted((ROOT / ".agents/tasks").glob("*.md")):
    value = path.read_text(encoding="utf-8")
    if not path.name.startswith(("todo-", "work-", "done-")):
        fail(f"task filename must start with todo-, work-, or done-: {path.relative_to(ROOT)}")
    match = re.search(r"^Status:\s*(.+)$", value, re.MULTILINE)
    if not match:
        if path.name.startswith("todo-"):
            continue
        fail(f"task lacks Status: {path.relative_to(ROOT)}")
    status = match.group(1).strip().lower()
    if path.name.startswith("todo-") and status not in {"todo", "blocked", "work", "in progress"}:
        fail(f"todo task has invalid status {status!r}: {path.relative_to(ROOT)}")
    if path.name.startswith("work-") and status not in {"in progress", "blocked"}:
        fail(f"work task has invalid status {status!r}: {path.relative_to(ROOT)}")
    if path.name.startswith("done-") and status != "complete":
        fail(f"done task has invalid status {status!r}: {path.relative_to(ROOT)}")

for obsolete in (
    ROOT / ".agents/kanban.md",
    ROOT / "src/common/templates/.agents/kanban.md",
    ROOT / "templates/.agents/kanban.md",
):
    if obsolete.exists():
        fail(f"duplicate task index remains: {obsolete.relative_to(ROOT)}")

# Roadmap no longer advertises the reverted merge policies.
for phrase in (
    "M5.9 Add the ZCode adapter without per-child task files",
    "never silently include them in the current task commit",
    "material route failure",
):
    require(roadmap, phrase, "ROADMAP.md")
forbid(roadmap, "mandatory, bounded self-improve record for every non-Hermes", "ROADMAP.md")

adapter_script = ROOT / "scripts/lhc-block"
if not adapter_script.is_file() or not adapter_script.stat().st_mode & 0o111:
    fail("scripts/lhc-block must exist and be executable")
subprocess.run(["sh", str(ROOT / "tests/test_block_adapter.sh")], check=True)

print(f"PASS: {len(ROLES)} roles, {len(ADAPTERS)} adapters, human gates, one-task contract, and workspace policy")
