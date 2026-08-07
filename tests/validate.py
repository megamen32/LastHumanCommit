#!/usr/bin/env python3
"""Validate the dependency-free Last Human Commit text contract."""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("Lead", "Overseer", "Adviser", "Critic", "Worker", "Reviewer")
ADAPTERS = ("codex", "opencode", "claude-code", "hermes")


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        fail(f"missing file: {path}")
    return target.read_text(encoding="utf-8")


def normalized(value: str) -> str:
    return " ".join(value.split())


def require(value: str, phrase: str, source: str) -> None:
    if normalized(phrase) not in normalized(value):
        fail(f"{source} lacks: {phrase}")


def forbid(value: str, phrase: str, source: str) -> None:
    if normalized(phrase) in normalized(value):
        fail(f"{source} contains forbidden text: {phrase}")


router = text("AGENTS.md")
claude = text("CLAUDE.md")
lead = text("src/common/agents/Lead.md")
worker = text("src/common/agents/Worker.md")
oversee = text("src/common/agents/Overseer.md")
critic = text("src/common/agents/Critic.md")
reviewer = text("src/common/agents/Reviewer.md")
planning = text("src/common/profiles/Planning.md")
code = text("src/common/profiles/Code.md")
workspace = text("src/common/protocols/SHARED_WORKTREE.md")
stop = text("src/common/protocols/STOP_RETHINK.md")
research = text("src/common/protocols/WORKER_RESEARCH.md")
implement = text("src/common/protocols/WORKER_IMPLEMENT.md")
task_template = text("src/common/templates/.agents/tasks/task_template.md")
full_cycle = text("templates/FULL_CYCLE.md")
release = text("templates/RELEASE_HANDOFF.md")
readme = text("README.md")
authoring = text("docs/agent-authoring.md")

# Marker router and role boundary.
if router.encode() != claude.encode():
    fail("AGENTS.md and CLAUDE.md must be byte-identical")
for marker in ("<!-- last-human-commit:begin -->", "<!-- last-human-commit:end -->"):
    if router.splitlines().count(marker) != 1:
        fail(f"AGENTS.md needs exactly one {marker}")
for role in ROLES:
    require(router, f"{role}: `src/common/agents/{role}.md`", "AGENTS.md")
    role_path = ROOT / f"src/common/agents/{role}.md"
    if not role_path.is_file():
        fail(f"missing role: {role_path.relative_to(ROOT)}")
if (ROOT / "src/common/agents/Explorer.md").exists():
    fail("Explorer.md must be replaced by Worker research mode")

for phrase in (
    "first user-visible update must warn the user",
    "<primary-project-root>/.worktrees/<task-slug>",
    "one Markdown file under `.agents/tasks/`",
    "Never create a second ledger, kanban, specification, or recovery file",
    "minimum / maximum active minutes",
    "L is an orchestrator by default",
    "mode: research",
    "mode: implement",
    "maximum <=20 active minutes",
    "Overseer is mandatory for every task",
    "Silence never authorizes them",
):
    require(router, phrase, "AGENTS.md")

# Lead keeps orchestration cheap while preserving the Full human layer.
for phrase in (
    "I am an orchestrator by default",
    "For Short and Full work I do not search the repository",
    "maximum five active minutes",
    "Worker research confirms both development over 30 active minutes",
    "maximum <=20 active minutes",
    "A whole plan may exceed one hour only as an explicit graph",
    "There is no separate Explorer role",
    "every invocation is a new no-history child",
    "after every implementation wave",
    "Максимально идеальный",
    "Нормальный",
    "YAGNI MVP",
    "call-stack tree",
    "file-tree diff",
    "key types and method signatures",
    "pseudocode",
    "migration description",
    "execution graph",
    "second explicit approval",
    "YAGNI -> Normal -> Ultimate",
    "silence means pending",
):
    require(lead, phrase, "Lead.md")

# Worker modes and hard stop discipline.
for phrase in (
    "`mode: research` or `mode: implement`",
    "maximum <=20",
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

# Fresh oversight and overrun control.
for phrase in (
    "fresh, independent route auditor",
    "never resumed",
    "raw user request",
    "Reject any Worker assignment above 20 minutes",
    "current maximum is exceeded",
    "default to `RETHINK`",
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
    "one coherent selected diff",
    "smallest bounded fix",
    "<=20-minute Worker slice",
):
    require(reviewer, phrase, "Reviewer.md")

# Estimate/decomposition policy.
for phrase in (
    "minimum / maximum active minutes",
    "immutable initial",
    "fresh Overseer verdict",
    "Use for every non-Direct task",
    "maximum <=20 active minutes",
    "whole plan may exceed 60 minutes only as a known graph",
    "single unresolved block above 60 minutes",
    "Resume the same Worker",
    "Overseer and Critic are the opposite",
):
    require(planning, phrase, "Planning.md")
for phrase in (
    "current minimum/maximum estimate is exceeded",
    "proposed Worker assignment exceeds 20",
    "one unresolved block is estimated above 60",
    "fresh Overseer audit",
    "Worker(mode=research)",
    "There is no Explorer role",
):
    require(stop, phrase, "STOP_RETHINK.md")

# Project-local workspace and immediate disclosure.
for phrase in (
    "current primary checkout",
    "git worktree list --porcelain",
    "first user-visible update",
    "<primary-project-root>/.worktrees/<task-slug>",
    "Never create project worktrees in `/tmp`",
    "git stash",
    "git reset",
    "git clean",
    "five minutes",
):
    require(workspace, phrase, "SHARED_WORKTREE.md")
require(text(".gitignore"), ".worktrees/", ".gitignore")

# Protect the deliberately strict Code profile.
for phrase in (
    "Prefer structured logs and rotate them",
    "Split code files over 800 lines",
    "Document every function, including private ones: inputs, outputs, errors",
    "Check cross-OS behavior before claiming portability",
    "Mark legacy or deprecated code explicitly as `LEGACY` or `DEPRECATED`, with a date and end-of-support target",
):
    require(code, phrase, "Code.md")

# One task file contains the full human layer and execution history.
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
    "Execution — append-only",
    "Overseer receipts — append-only",
    "Critic decisions — append-only",
):
    require(task_template, phrase, "task_template.md")
for phrase in (
    "development over 30 active minutes",
    "material product, architecture, migration, or expensive-wrong-path choice",
    "maximum <=20 active minutes",
    "### 1. Максимально идеальный",
    "### 2. Нормальный",
    "### 3. YAGNI MVP",
    "Call-stack tree:",
    "File-tree diff:",
    "Key types and method signatures:",
    "Pseudocode:",
    "Migration description:",
    "Second explicit approval",
    "YAGNI -> Normal -> Ultimate",
):
    require(full_cycle, phrase, "FULL_CYCLE.md")

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

# Public docs describe the same product.
for source, value in (("README.md", readme), ("docs/agent-authoring.md", authoring)):
    for phrase in (
        "one Markdown",
        "orchestrator",
        "<=20",
        "Overseer",
        "three",
        "second explicit approval",
        ".worktrees/",
    ):
        require(value, phrase, source)

# No uptime-as-task-clock remains in runtime contract files.
for relative in (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/agent-authoring.md",
    "src/common/agents/Lead.md",
    "src/common/agents/Worker.md",
    "src/common/agents/Overseer.md",
    "src/common/agents/Reviewer.md",
    "src/common/agents/Critic.md",
    "src/common/agents/Adviser.md",
    "src/common/profiles/Planning.md",
    "src/common/protocols/STOP_RETHINK.md",
    "templates/FULL_CYCLE.md",
):
    forbid(text(relative), "uptime", relative)

# Adapter contracts preserve Worker continuity and fresh gates.
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
        "lowest sufficient working model class",
        "maximum <=20",
        "same Worker",
        "Overseer and Critic are always",
    ):
        require(template, phrase, f"{adapter}/templates/subagent.md")
    for key in ("role_source", "optional_instructions", "subagent_instructions_template"):
        match = re.search(rf"^{key}:\s*(.+)$", manifest, re.MULTILINE)
        if not match or not (base / match.group(1).strip()).exists():
            fail(f"{adapter} manifest has invalid {key}")
if "fork_context: true" in text("adapters/codex/templates/subagent.md"):
    fail("Codex template must never fork parent history")
require(text("adapters/codex/templates/subagent.md"), "fork_context: false", "Codex template")
plugin_source = text("adapters/hermes/plugin/__init__.py")
forbid(plugin_source, '"explorer": "Explorer"', "Hermes plugin")

# Existing task files retain the one-file status matrix.
for path in sorted((ROOT / ".agents/tasks").glob("*.md")):
    value = path.read_text(encoding="utf-8")
    if not path.name.startswith(("work-", "done-")):
        fail(f"task filename must start with work- or done-: {path.relative_to(ROOT)}")
    match = re.search(r"^Status:\s*(.+)$", value, re.MULTILINE)
    if not match:
        fail(f"task lacks Status: {path.relative_to(ROOT)}")
    status = match.group(1).strip().lower()
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

adapter_script = ROOT / "scripts/lhc-block"
if not adapter_script.is_file() or not adapter_script.stat().st_mode & 0o111:
    fail("scripts/lhc-block must exist and be executable")
subprocess.run(["sh", str(ROOT / "tests/test_block_adapter.sh")], check=True)

print(f"PASS: {len(ROLES)} roles, Worker modes, human gates, and workspace contract")
