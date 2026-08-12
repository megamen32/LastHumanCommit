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
CANONICAL_SKILL_OWNERS = {
    "planning": "Lead",
    "bugfix-tdd": "Worker",
    "feature-implementation": "Worker",
    "real-use-testing": "Tester",
    "business-delivery": "Lead",
    "release": "Lead",
}


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


def canonical_skill_contract(manifest_value: str) -> tuple[str, dict[str, str]]:
    skills_root_match = re.search(r"^  skills:\s*(\S+)\s*$", manifest_value, re.MULTILINE)
    if not skills_root_match:
        fail("adapters/manifest.yaml lacks core.skills")
    skills_root = skills_root_match.group(1)
    skills_root_path = Path(skills_root)
    if skills_root_path.is_absolute() or ".." in skills_root_path.parts:
        fail("adapters/manifest.yaml core.skills must stay inside the repository")

    lines = manifest_value.splitlines()
    try:
        start = lines.index("canonical_skills:") + 1
    except ValueError:
        fail("adapters/manifest.yaml lacks canonical_skills")

    owners: dict[str, str] = {}
    index = start
    while index < len(lines) and (not lines[index].strip() or lines[index].startswith("  ")):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        name_match = re.fullmatch(r"  - name: ([a-z0-9]+(?:-[a-z0-9]+)*)", line)
        if not name_match or index + 1 >= len(lines):
            fail("adapters/manifest.yaml has malformed canonical_skills entry")
        name = name_match.group(1)
        owner_match = re.fullmatch(r"    owner: ([A-Za-z]+)", lines[index + 1])
        if not owner_match or name in owners:
            fail(f"adapters/manifest.yaml has malformed or duplicate skill: {name}")
        owners[name] = owner_match.group(1)
        index += 2

    if set(owners) != set(CANONICAL_SKILL_OWNERS) or len(owners) != 6:
        fail("adapters/manifest.yaml must declare exactly the six canonical skills")
    for name, expected_owner in CANONICAL_SKILL_OWNERS.items():
        if owners[name] != expected_owner:
            fail(f"canonical skill {name} owner mismatch: expected {expected_owner}, got {owners[name]}")

    for name, owner in owners.items():
        skill_path = (ROOT / skills_root_path / name / "SKILL.md").resolve()
        try:
            skill_path.relative_to(ROOT.resolve())
        except ValueError:
            fail(f"canonical skill path escapes repository: {name}")
        if not skill_path.is_file():
            fail(f"missing canonical skill: {skill_path.relative_to(ROOT)}")
        skill_lines = skill_path.read_text(encoding="utf-8").splitlines()
        if not skill_lines or skill_lines[0] != "---":
            fail(f"{skill_path.relative_to(ROOT)} lacks YAML frontmatter")
        try:
            end = skill_lines.index("---", 1)
        except ValueError:
            fail(f"{skill_path.relative_to(ROOT)} has unterminated YAML frontmatter")
        fields: dict[str, str] = {}
        for field in skill_lines[1:end]:
            match = re.fullmatch(r"([a-z][a-z0-9_-]*):\s*(.+\S)", field)
            if not match or match.group(1) in fields:
                fail(f"{skill_path.relative_to(ROOT)} has invalid frontmatter")
            fields[match.group(1)] = match.group(2)
        if set(fields) != {"name", "description"}:
            fail(f"{skill_path.relative_to(ROOT)} frontmatter must contain name and description")
        if fields["name"] != name or not fields["description"].strip():
            fail(f"{skill_path.relative_to(ROOT)} frontmatter does not match manifest name")
        role_value = text(f"src/common/agents/{owner}.md")
        require(role_value, f"`{name}`", f"{owner}.md")

    return skills_root, owners


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
shared_session = text("docs/shared-session-abstraction.md")
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
    "Full always uses three plans; the active harness governs any approval flow",
    "Overseer is mandatory for every task",
    "Event-triggered audits cannot be suppressed by a 30-minute cooldown",
    "The active harness owns approval policy",
    "Use one project-local state root",
    "never create a separate `.at/` or `.lhc/`",
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
    "Draft exactly three Russian plans, always",
    "Максимально идеальный",
    "Нормальный",
    "YAGNI 80/20",
    "call-stack tree",
    "file-tree diff",
    "key types and method signatures",
    "pseudocode",
    "migration description",
    "execution graph",
    "select the route under active-harness policy",
    "not three branches, worktrees, specifications, or throwaway rewrites",
    "exactly two fresh Testers",
    "invoke fresh Critic once",
    "never silently include foreign edits",
    "AskSecret/SSS",
    "The active harness owns approval policy",
    "only when its trigger occurred",
):
    require(lead, phrase, "Lead.md")
require_before(lead, "invoke exactly two fresh Testers", "invoke fresh Critic once", "Lead.md")
for bad in (
    "optimistic / likely / pessimistic",
    "Later audits are allowed only after 30 minutes",
    "Before every final answer",
    "creates the cheapest sufficient Worker package, normally on",
):
    forbid(lead, bad, "Lead.md")

# Codex wait joins are observation points, never lifecycle decisions. Keep the
# mechanics fail-closed across the aggregate contract while requiring only the
# policy/surface markers that belong in each individual file.
codex_instructions = text("adapters/codex/instructions.md")
codex_template = text("adapters/codex/templates/subagent.md")
wait_contract_aggregate = "\n".join((router, claude, lead, codex_instructions, codex_template))
for phrase in (
    "deadline = monotonicNow() + 1800000 ms",
    "on every mailbox wake or `timed_out` result, re-check the target child status",
    "if non-terminal, compute `remainingMs = deadline - monotonicNow()`",
    "wait only with `remainingMs`",
    "never reset/restart the full 1800000 after a wake or timeout",
    "remainingMs <= 0",
    "return `join-deadline-expired`",
    "child preserved",
    "Codex V1 target-specific wait",
    "Codex V2 mailbox wake",
    "same absolute deadline",
):
    require(wait_contract_aggregate, phrase, "Codex wait-agent contract aggregate")
for source, value in (("AGENTS.md", router), ("CLAUDE.md", claude)):
    for phrase in (
        "wait timeout is observational only",
        "missing completion signal alone is not evidence of dead or unknown",
        "authoritative terminal status",
        "explicit cancellation",
    ):
        require(value, phrase, source)
for source, value in (
    ("Lead.md", lead),
    ("adapters/codex/instructions.md", codex_instructions),
    ("adapters/codex/templates/subagent.md", codex_template),
):
    require(value, "fixed absolute 30-minute join deadline", source)
    require(value, "timeout_ms: 1800000", source)
    require(value, "never call `close_agent` on timeout", source)
    require(value, "never create a replacement on timeout", source)
for source, value, phrase in (
    ("Lead.md", lead, "deadline = monotonicNow() + 1800000 ms"),
    ("adapters/codex/instructions.md", codex_instructions, "Codex V1 target-specific wait"),
    ("adapters/codex/templates/subagent.md", codex_template, "Codex V2 mailbox wake"),
):
    require(value, phrase, source)
for bad in (
    "if PID is dead or no completion signal exists, report the task as dead or unknown",
    "timeout authorizes `close_agent`",
    "timeout authorizes replacement",
):
    forbid(wait_contract_aggregate, bad, "Codex wait-agent contract aggregate")

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
    "search-<task-slug>.md",
    "result-<result-slug>.md",
    "After 10 active minutes",
    "Git commit",
    ".agents/at/",
    "/tmp",
    ".tmpbin/",
):
    require(research, phrase, "WORKER_RESEARCH.md durable research contract")
for phrase in (
    "search-<task-slug>.md",
    "result-<result-slug>.md",
    "physically Git-ignored",
    "must include a Git commit",
    "One-off scripts are forbidden",
    "<working-directory>/.agents/at/",
):
    require(shared_session, phrase, "shared-session abstraction")
for phrase in (
    "Bugfix / TDD",
    "Feature",
    "Reproduce the real reported symptom",
    "thinnest working vertical slice",
    "Never write a test merely to satisfy ceremony",
    "stop and return to research",
):
    require(implement, phrase, "WORKER_IMPLEMENT.md")

# Persistent oversight, plus independent review, real-user test, and release gate.
for phrase in (
    "continuing route auditor",
    "persistent shared-session",
    "full conversation",
    "fresh context only",
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
    "plan-review",
    "long-term rewrite traps",
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
    "Exactly two fresh",
    "blast-radius",
    "zero-knowledge",
    "only blind",
    "mandatory screenshot/video",
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
    "Overseer verdict",
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
    "continued Overseer audit",
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
expected_code_sha256 = "971a8342a45b38a3a7fdd3b24c272fc12707e2d3ae3919370819e393ac15d4df"
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
    "Active-harness policy evidence",
    "Children append their detailed evidence and result to that file",
    "Overseer:",
    "Reviewer:",
    "Tester:",
    "Critic:",
    "Commit (only if created):",
    "Lifecycle snapshot: todo | work | done",
    "Supersedes: <previous lifecycle snapshot path or none>",
    "Snapshot commit: <commit or pending>",
    "Result file:",
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
    "Выбранный маршрут / evidence active harness",
    "not create three branches, worktrees, specifications",
    "exactly two fresh Testers",
    "Only the second pass is blind",
    "run Critic once",
):
    require(full_cycle, phrase, "FULL_CYCLE.md")
if full_cycle.count("### 1. Максимально идеальный") != 1 or full_cycle.count("### 2. Нормальный") != 1 or full_cycle.count("### 3. YAGNI 80/20") != 1:
    fail("FULL_CYCLE.md must contain exactly three plan headings")
require_before(full_cycle, "exactly two fresh Testers", "run Critic once", "FULL_CYCLE.md")

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

# Release approval policy belongs to the active harness.
require(release, "approval policy активного harness", "RELEASE_HANDOFF.md")
require(release, "Apply the active harness approval-policy state machine.", "RELEASE_HANDOFF.md")

# Public docs describe the same product rather than the reverted merge policy.
for source, value in (("README.md", readme), ("docs/agent-authoring.md", authoring)):
    for phrase in (
        "one Markdown",
        "orchestrator",
        "<=20",
        "Overseer",
        "three",
        "active harness",
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

# Adapter manifests and child templates preserve one root file, continuity, and independent gates.
manifest_text = text("adapters/manifest.yaml")
require(manifest_text, "schema_version: 1", "adapters/manifest.yaml")
canonical_skill_contract(manifest_text)
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
        "Overseer continues the persistent shared-session context",
        "Critic is a",
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

# Every todo/work card must retain enough lifecycle identity to distinguish a
# live task from a stale file. Legacy cards may say unknown, but may not omit
# the fields or present filesystem mtime as a fabricated start time.
task_template = text("src/common/templates/.agents/tasks/task_template.md")
for phrase in (
    "Harness:", "PID:", "Agent session:", "PID status:",
    "Last PID signal", "Last task-file transition", "Started at (UTC+3):",
    "Lifecycle provenance:", "Last task-file mtime observed (UTC+3):",
):
    require(task_template, phrase, "task template lifecycle identity")

for path in sorted((ROOT / ".agents/tasks").glob("*.md")):
    value = path.read_text(encoding="utf-8")
    if not path.name.startswith(("todo-", "work-", "done-")):
        fail(f"task filename must start with todo-, work-, or done-: {path.relative_to(ROOT)}")
    match = re.search(r"^Status:\s*(.+)$", value, re.MULTILINE)
    if not match:
        fail(f"task lacks Status: {path.relative_to(ROOT)}")
    status = match.group(1).strip().lower()
    if path.name.startswith("todo-") and status not in {"todo", "blocked", "work", "in progress"}:
        fail(f"todo task has invalid status {status!r}: {path.relative_to(ROOT)}")
    if path.name.startswith("work-") and status not in {"in progress", "blocked"}:
        fail(f"work task has invalid status {status!r}: {path.relative_to(ROOT)}")
    if path.name.startswith("done-") and status != "complete":
        fail(f"done task has invalid status {status!r}: {path.relative_to(ROOT)}")
    if path.name.startswith(("todo-", "work-")):
        lifecycle_fields = (
            "Harness", "PID", "Agent session", "PID status",
            "Last PID signal", "Last task-file transition",
            "Started at (UTC+3)", "Lifecycle provenance",
            "Last task-file mtime observed (UTC+3)",
        )
        for field in lifecycle_fields:
            field_pattern = re.escape(field)
            if field in {"Last PID signal", "Last task-file transition"}:
                field_pattern += r"(?: \(UTC\+3\))?"
            field_match = re.search(rf"^{field_pattern}:[ \t]*(.*)$", value, re.MULTILINE)
            if not field_match:
                fail(f"{path.name.split('-', 1)[0]} task lacks lifecycle field {field!r}: {path.relative_to(ROOT)}")
            if not field_match.group(1).strip():
                fail(f"{path.name.split('-', 1)[0]} task has empty lifecycle field {field!r}: {path.relative_to(ROOT)}")

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
