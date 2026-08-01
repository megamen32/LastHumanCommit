#!/usr/bin/env python3
"""Validate the small, dependency-free YAGNI LHC text contract."""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

ROLES = (
    "Lead",
    "Overseer",
    "Adviser",
    "Critic",
    "Explorer",
    "Worker",
    "Reviewer",
)

ADAPTERS = ("codex", "opencode", "claude-code", "hermes")


def fail(message: str) -> None:
    """Exit with one readable contract failure."""
    raise SystemExit(f"FAIL: {message}")


def require_text(text: str, phrase: str, source: str) -> None:
    if " ".join(phrase.split()) not in " ".join(text.split()):
        fail(f"{source} lacks: {phrase}")


def require_absent(text: str, phrase: str, source: str) -> None:
    if " ".join(phrase.split()) in " ".join(text.split()):
        fail(f"{source} still contains forbidden text: {phrase}")


agents_path = ROOT / "AGENTS.md"
claude_path = ROOT / "CLAUDE.md"
lead_path = ROOT / "src/common/agents/Lead.md"
roadmap_path = ROOT / "ROADMAP.md"
release_path = ROOT / "templates/RELEASE_HANDOFF.md"
planning_path = ROOT / "src/common/profiles/Planning.md"
self_improve_path = ROOT / "src/common/protocols/SELF_IMPROVE.md"
shared_worktree_path = ROOT / "src/common/protocols/SHARED_WORKTREE.md"
adapter_path = ROOT / "scripts/lhc-block"
adapter_test_path = ROOT / "tests/test_block_adapter.sh"

for path in (
    agents_path,
    claude_path,
    lead_path,
    roadmap_path,
    release_path,
    planning_path,
    self_improve_path,
    shared_worktree_path,
    adapter_path,
    adapter_test_path,
):
    if not path.is_file():
        fail(f"missing text contract: {path.relative_to(ROOT)}")

for adapter in ADAPTERS:
    adapter_dir = ROOT / "adapters" / adapter
    for path in (adapter_dir / "adapter.yaml", adapter_dir / "instructions.md"):
        if not path.is_file():
            fail(f"missing harness adapter contract: {path.relative_to(ROOT)}")
    manifest = (adapter_dir / "adapter.yaml").read_text(encoding="utf-8")
    require_text(manifest, f"harness: {adapter}", str(adapter_dir / "adapter.yaml"))
    require_text(
        (adapter_dir / "instructions.md").read_text(encoding="utf-8"),
        "templates/subagent.md",
        f"{adapter} adapter instructions",
    )
    for key in (
        "role_source",
        "optional_instructions",
        "subagent_instructions_template",
    ):
        prefix = f"{key}:"
        value = next(
            (line.split(":", 1)[1].strip() for line in manifest.splitlines()
             if line.startswith(prefix)),
            "",
        )
        if not value or not (adapter_dir / value).exists():
            fail(f"{adapter} manifest has missing {key}: {value or '<empty>'}")
        if key == "subagent_instructions_template":
            template = (adapter_dir / value).read_text(encoding="utf-8")
            for phrase in (
                "lowest sufficient working model class",
                "Do not inherit L's model by default",
                "Task Card",
            ):
                require_text(template, phrase, f"{adapter} subagent template")
            if adapter == "codex":
                for phrase in (
                    "fork_context: false",
                    "Never fork the parent conversation history",
                    "pass required context explicitly",
                ):
                    require_text(template, phrase, "codex subagent template")
                require_absent(
                    template,
                    "fork_context: true",
                    "codex subagent template",
                )
    plugin_value = next(
        (line.split(":", 1)[1].strip() for line in manifest.splitlines()
         if line.startswith("plugin:")),
        "",
    )
    if plugin_value and not (adapter_dir / plugin_value).is_dir():
        fail(f"{adapter} manifest has missing plugin directory: {plugin_value}")
    verification_value = next(
        (line.split(":", 1)[1].strip() for line in manifest.splitlines()
         if line.startswith("verification:")),
        "",
    )
    if verification_value and not (adapter_dir / verification_value).is_file():
        fail(f"{adapter} manifest has missing verification file: {verification_value}")

manifest_path = ROOT / "adapters/manifest.yaml"
if not manifest_path.is_file():
    fail("missing adapters/manifest.yaml")
require_text(
    manifest_path.read_text(encoding="utf-8"),
    "schema_version: 1",
    "adapters/manifest.yaml",
)
manifest_text = manifest_path.read_text(encoding="utf-8")
for adapter in ADAPTERS:
    require_text(manifest_text, f"adapters/{adapter}/adapter.yaml", "adapters/manifest.yaml")

if (ROOT / "CANON.md").exists():
    fail("CANON.md must be absent; AGENTS.md is the portable router")

if agents_path.read_bytes() != claude_path.read_bytes():
    fail("AGENTS.md and CLAUDE.md must be byte-identical")


def require_one_marker_block(text: str, source: str) -> None:
    begin = "<!-- last-human-commit:begin -->"
    end = "<!-- last-human-commit:end -->"
    lines = text.splitlines()
    if lines.count(begin) != 1 or lines.count(end) != 1:
        fail(f"{source} needs exactly one marker pair")
    if lines.index(begin) >= lines.index(end):
        fail(f"{source} has reversed marker lines")

router = agents_path.read_text(encoding="utf-8")
lead = lead_path.read_text(encoding="utf-8")
roadmap = roadmap_path.read_text(encoding="utf-8")

require_one_marker_block(router, "AGENTS.md")
if not adapter_path.stat().st_mode & 0o111:
    fail("scripts/lhc-block must be executable")
for path in (
    ROOT / ".agents/kanban.md",
    ROOT / "src/common/templates/.agents/kanban.md",
    ROOT / "templates/.agents/kanban.md",
):
    if path.exists():
        fail(f"obsolete duplicate task index remains: {path.relative_to(ROOT)}")
if (ROOT / "src/common/templates/.agents/orchestrator.md").exists():
    fail("templates must not be split between src/common/templates and templates")
for path in (
    ROOT / "templates/.agents/orchestrator.md",
    ROOT / "templates/.agents/self-improve.md",
):
    if not path.is_file():
        fail(f"missing unified template: {path.relative_to(ROOT)}")

for role in ROLES:
    require_text(router, role, "AGENTS.md router")
    require_text(router, f"src/common/agents/{role}.md", "AGENTS.md router")
    role_path = ROOT / f"src/common/agents/{role}.md"
    if not role_path.is_file():
        fail(f"missing role contract: {role_path.relative_to(ROOT)}")

for phrase in (
    "If an enclosing instruction explicitly assigns one of these roles",
    "read only that role file",
    "If it says you are a subagent but does not assign a known role",
    "stop and ask L",
    "Otherwise, you are L",
    "ROADMAP.md",
    "Proposed",
    "Direct",
    "Short",
    "Full",
    "Emergency",
):
    require_text(router, phrase, "AGENTS.md router")

for role in ROLES[1:]:
    relative = f"src/common/agents/{role}.md"
    role_text = (ROOT / relative).read_text(encoding="utf-8")
    require_text(role_text.lower(), "subagent", relative)
    if "read lead.md" in role_text.lower():
        fail(f"{relative} must remain independently injectable")

for role in ROLES:
    relative = f"src/common/agents/{role}.md"
    role_text = (ROOT / relative).read_text(encoding="utf-8")
    for phrase in (
        "After at most 30 tool calls or shell commands",
        "30 elapsed minutes when measurable",
        "whichever comes first",
        "run `uptime`",
        "progress checkpoint",
    ):
        require_text(role_text, phrase, relative)

for path in sorted((ROOT / ".agents/tasks").glob("*.md")):
    task_text = path.read_text(encoding="utf-8")
    if not path.name.startswith(("work-", "done-")):
        fail(
            "task filename must start with work- or done-: "
            f"{path.relative_to(ROOT)}"
        )
    status_match = re.search(r"^Status:\s*(.+)$", task_text, re.MULTILINE)
    if not status_match:
        fail(f"task lacks Status: {path.relative_to(ROOT)}")
    status = status_match.group(1).strip().lower()
    if re.search(r"^State:\s*", task_text, re.MULTILINE):
        fail(f"task duplicates Status with legacy State: {path.relative_to(ROOT)}")
    if path.name.startswith("work-"):
        if status not in {"in progress", "blocked"}:
            fail(
                f"work task has invalid status {status!r}: "
                f"{path.relative_to(ROOT)}"
            )
    elif status != "complete":
        fail(f"done task has invalid status {status!r}: {path.relative_to(ROOT)}")

normative = {
    "AGENTS.md": router,
    "src/common/agents/Lead.md": lead,
    "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
    "docs/agent-authoring.md": (ROOT / "docs/agent-authoring.md").read_text(
        encoding="utf-8"
    ),
    "templates/RELEASE_HANDOFF.md": release_path.read_text(encoding="utf-8"),
}
for source, text in normative.items():
    for forbidden in (
        "CANON.md",
        "Web, credentials",
        "Agent Fleet",
        "external scheduler",
        "external adapter",
    ):
        if forbidden.lower() in text.lower():
            fail(f"{source} contains stale ownership or source: {forbidden}")

lhc_naming_surfaces = {
    relative: (ROOT / relative).read_text(encoding="utf-8")
    for relative in (
        "README.md",
        "adapters/README.md",
        "adapters/hermes/instructions.md",
        "adapters/hermes/plugin/README.md",
        "adapters/hermes/plugin/instructions.md",
        "adapters/hermes/plugin/plugin.yaml",
        "adapters/hermes/plugin/__init__.py",
        "docs/agent-authoring.md",
        "scripts/lhc-block",
        "src/common/agents/Lead.md",
        "src/common/protocols/SELF_IMPROVE.md",
        "templates/.agents/self-improve.md",
    )
}
for source, text in lhc_naming_surfaces.items():
    normalized_text = " ".join(text.split())
    for deprecated in (
        "LastHuman" + "Commit",
        "the " + "canon",
        "portable " + "canon",
        "rewrite the " + "canon",
        "mutate the " + "canon",
        "applying the " + "canon",
    ):
        if re.search(rf"\b{re.escape(deprecated)}\b", normalized_text, re.IGNORECASE):
            fail(f"{source} uses deprecated LHC product wording: {deprecated}")

for phrase in (
    "Максимально идеальный",
    "Нормальный",
    "YAGNI MVP",
    "explicit human selection",
    "30 minutes",
):
    require_text(lead, phrase, "src/common/agents/Lead.md")

for alias in (
    "glm5.2",
    "kimi k3",
    "deepseek-v4-pro",
    "MinimaxM3",
    "Deepseek v4 flash",
    "mimo",
    "glm-4.7",
):
    require_text(lead, alias, "src/common/agents/Lead.md")

for phrase in (
    "I do not load specialist prompts into my own context",
    "Reviewer",
    "Critic once",
    "For Full work, load `../profiles/Planning.md` relative to this role file before presenting plans.",
    "Direct, Short, and Emergency work stay proportional; they do not gain planning ceremony unless",
    "Mandatory self-improve",
    "../protocols/SELF_IMPROVE.md",
    "Shared worktree",
    "five minutes",
    "Overseer and Critic are exceptions to bounded child assignments",
    "full raw user conversation",
    "must not give them a desired verdict",
    "Session ownership never overrides user priority",
    "project-wide ordered task list",
):
    require_text(lead, phrase, "src/common/agents/Lead.md")

shared_worktree = shared_worktree_path.read_text(encoding="utf-8")
for phrase in (
    "assume I am not working alone",
    "git stash",
    "git reset",
    "git clean",
    "git restore",
    "git revert",
    "five minutes",
    "currently being edited",
    "final review",
    "include it in L's commit",
):
    require_text(shared_worktree, phrase, "src/common/protocols/SHARED_WORKTREE.md")

worker = (ROOT / "src/common/agents/Worker.md").read_text(encoding="utf-8")
reviewer = (ROOT / "src/common/agents/Reviewer.md").read_text(encoding="utf-8")
overseer = (ROOT / "src/common/agents/Overseer.md").read_text(encoding="utf-8")
critic = (ROOT / "src/common/agents/Critic.md").read_text(encoding="utf-8")
for text, source in ((worker, "Worker.md"), (reviewer, "Reviewer.md")):
    require_text(text, "shared worktree", source)
    require_text(text, "five minutes", source)

workflow_contracts = {
    "AGENTS.md router": (
        router,
        (
            "create or update one Markdown task file under",
            ".agents/tasks/",
            "initial active-minute estimate",
            "Overseer is mandatory for every task",
            "Initial plans are written in Russian",
            "implementation progress is written in English",
            "final answer is written in Russian",
        ),
    ),
    "src/common/agents/Lead.md": (
        lead,
        (
            "original user request",
            ".agents/tasks/",
            "confirmed scope",
            "YAGNI -> Normal -> Ultimate",
            "Overseer is mandatory",
            "subagent_instructions_template",
            "lowest sufficient working model class",
            "Do not inherit L's model by default",
            "Escalate only after",
            "STOP_SCOPE_DRIFT",
            "Initial plans are in Russian",
            "execution updates are in English",
            "final answer is in Russian",
        ),
    ),
    "src/common/agents/Overseer.md": (
        overseer,
        (
            "latest raw user request",
            "project-wide P0",
            "my only authority",
            "L's delegation prompt",
            "claims to audit",
            "completely and unchanged",
            "STOP_MISSING_CONTEXT",
            "BUSINESS_DELTA",
            "P0_DISTANCE",
            "QUESTIONS_FOR_L",
            "RETHINK",
            "STOP_SCOPE_DRIFT",
            "unsolicited security",
        ),
    ),
    "src/common/agents/Critic.md": (
        critic,
        (
            "latest raw user request",
            "project-wide P0",
            "my only authority",
            "L's delegation prompt",
            "claims to audit",
            "completely and unchanged",
            "STOP_MISSING_CONTEXT",
            "BUSINESS_DELTA",
            "P0_DISTANCE",
            "QUESTIONS_FOR_L",
            "PASS",
            "RETHINK",
            "STOP",
            "STOP_SCOPE_DRIFT",
        ),
    ),
    "src/common/agents/Worker.md": (
        worker,
        (
            "task record",
            "confirmed scope",
            "I do not add helpful extras",
        ),
    ),
    "src/common/agents/Reviewer.md": (
        reviewer,
        (
            "business canary succeeds",
            "direct regressions",
            "outside-scope fixes",
        ),
    ),
}
for source, (text, phrases) in workflow_contracts.items():
    for phrase in phrases:
        require_text(text, phrase, source)

for category in (
    "security",
    "secrets",
    "PII",
    "permissions",
    "ACL",
    "database",
    "schema",
    "Grafana",
    "dashboard",
    "observability",
    "log",
    "provider",
):
    require_text(overseer, category, "src/common/agents/Overseer.md")
for phrase in (
    "maximum-severity unauthorized drift",
    "user-confirmed scope",
    "minimal prerequisite for safely running the confirmed canary",
):
    require_text(overseer, phrase, "src/common/agents/Overseer.md")

require_absent(lead, "Review the whole repository", "src/common/agents/Lead.md")
if lead.index("Overseer is mandatory") > lead.index("Implement the selected plan"):
    fail("Lead.md invokes mandatory Overseer after implementation starts")

if "git stash" in (ROOT / "src/common/profiles/Test.md").read_text(encoding="utf-8"):
    fail("Test.md must not instruct agents to use git stash")

self_improve = self_improve_path.read_text(encoding="utf-8")
for phrase in (
    "all non-Hermes harnesses",
    ".agents/last-human-commit/self-improve.md",
    "What slowed or confused L?",
    "Which instruction should change?",
    "Which skill, MCP, or tool is missing?",
    "What operation or error repeated?",
    "same fingerprint",
    "Do not silently rewrite LHC",
):
    require_text(self_improve, phrase, "src/common/protocols/SELF_IMPROVE.md")

for adapter in ("codex", "opencode", "claude-code"):
    adapter_text = (ROOT / "adapters" / adapter / "adapter.yaml").read_text(
        encoding="utf-8"
    )
    require_text(adapter_text, "self_improve: required-core-protocol", f"{adapter} adapter")

hermes_adapter = (ROOT / "adapters/hermes/adapter.yaml").read_text(encoding="utf-8")
require_text(hermes_adapter, "self_improve: hermes-native", "hermes adapter")

planning = planning_path.read_text(encoding="utf-8")
for phrase in (
    "Use this profile for every task",
    "Every task record has an initial estimate",
    "optimistic / likely / pessimistic",
    "relative cost",
    "more than 20 likely active minutes",
    "Every fresh child receives a Task Card",
    "lowest sufficient working model class",
    "Do not inherit L's model by default",
    "Escalate only after",
    "NEEDS_REDECOMPOSITION",
    "Use a no-history child only when the harness demonstrably supports it",
    "do not claim model-routing or fresh-context proof",
):
    require_text(planning, phrase, "src/common/profiles/Planning.md")

full_cycle = (ROOT / "templates/FULL_CYCLE.md").read_text(encoding="utf-8")
task_template = (
    ROOT / "src/common/templates/.agents/tasks/task_template.md"
).read_text(encoding="utf-8")
stop_rethink = (
    ROOT / "src/common/protocols/STOP_RETHINK.md"
).read_text(encoding="utf-8")
for phrase in (
    "Планы - только на русском",
    "### 1. Максимально идеальный",
    "### 2. Нормальный",
    "### 3. YAGNI MVP",
    "Execution updates - English only",
    "YAGNI -> Normal -> Ultimate",
    "Финальный ответ - только на русском",
    "Failed canary + unrelated secondary work -> STOP_SCOPE_DRIFT",
    "Green canary + direct regression -> review the direct regression",
    "User-confirmed secondary objective -> in scope",
    "Mandatory Critic release decision",
    "Current user P0 reconstructed by Overseer",
    "Current user P0 reconstructed by Critic",
    "L cannot prescribe, narrow, rewrite, or override either gate",
    "After at most 30 tool calls or shell commands",
    "30 elapsed minutes when measurable",
    "whichever comes first",
    "runs `uptime`",
):
    require_text(full_cycle, phrase, "templates/FULL_CYCLE.md")
for phrase in (
    "Original user request:",
    "Confirmed scope:",
    "Explicit exclusions:",
    "Initial estimate (optimistic / likely / pessimistic active minutes):",
    "Current stage: YAGNI | Normal | Ultimate",
    "Overseer decision history (append-only)",
    "Critic decision history (append-only)",
    "Timestamp:",
    "Stage:",
    "Evidence:",
    "Current user P0:",
    "Business delta:",
    "P0 distance: CLOSER | SAME | FARTHER",
    "Questions for L:",
    "Decision: APPROVE | RETHINK | STOP | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT",
    "Decision: PASS | RETHINK | STOP | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT",
):
    require_text(task_template, phrase, "task_template.md")
for phrase in (
    "unauthorized scope expansion",
    "STOP_SCOPE_DRIFT",
    "original user request",
    "is terminal",
    "Preserve the evidence",
    "Report the exact mismatch",
    "Update the task record",
    "After plan selection, write in English",
    "Do not launch Explorer",
    "Do not generate alternatives",
    "explicit human scope confirmation",
    "Architectural STOP/RETHINK",
    "bounded Explorer",
    "Before plan selection, write in Russian",
    "30 tool calls or shell commands",
    "run `uptime`",
    "gate decision is binding on L",
    "L cannot override",
    "unanswered questions",
    "user is the only authority",
    "complete report unchanged",
):
    require_text(stop_rethink, phrase, "src/common/protocols/STOP_RETHINK.md")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
authoring = (ROOT / "docs/agent-authoring.md").read_text(encoding="utf-8")
for text, source in (
    (readme, "README.md"),
    (authoring, "docs/agent-authoring.md"),
):
    for phrase in (
        "one Markdown task file",
        ".agents/tasks/",
        "There is no duplicate kanban" if source == "README.md" else "Never maintain a duplicate kanban",
        "Overseer is mandatory",
        "Critic gates release",
        "raw user context",
        "obey only the user" if source == "docs/agent-authoring.md" else "obey the user rather than L",
        "at most 30",
        "30 elapsed minutes when measurable",
        "whichever comes first",
        "uptime",
        "YAGNI -> Normal -> Ultimate",
        "initial plans in Russian",
        "execution updates in English",
        "final answer in Russian",
    ):
        require_text(text, phrase, source)
    require_absent(text, "whole-repository review", source)

for phrase in (
    "Максимально идеальный",
    "Нормальный",
    "YAGNI MVP",
):
    require_text(lead, phrase, "src/common/agents/Lead.md")

release_text = release_path.read_text(encoding="utf-8")
require_text(
    release_text,
    "Финальный ответ - только на русском",
    "templates/RELEASE_HANDOFF.md",
)
require_absent(roadmap, "whole-repository review", "ROADMAP.md")
require_absent(
    roadmap,
    ".agents/tasks/work-20260801-outcome-first-lhc.md",
    "ROADMAP.md",
)

require_text(roadmap, "Codex custom-agent routing", "ROADMAP.md")
require_text(roadmap, "actual model", "ROADMAP.md")

require_text(lead, "selected harness adapter to arm one wake", "src/common/agents/Lead.md")

require_text(roadmap, "## Proposed", "ROADMAP.md")
require_text(roadmap, "adapter overlays additive", "ROADMAP.md")

release = release_path.read_text(encoding="utf-8")
for phrase in (
    "status: pending | answered | vetoed | invalidated | deploying | deployed | deploy_failed",
    "review_sent_at:",
    "eligible_not_before:",
    "wake_transport:",
    "execution_guard: single_serialized_L | unverified",
    "commit_or_artifact:",
    "tests:",
    "target:",
    "rollback_reference:",
    "last_human_reply_at_or_id:",
    "pending + да + current + single_serialized_L",
    "pending + due + unanswered + current + single_serialized_L",
    "pending + нет | стоп -> vetoed",
    "pending + other human reply -> answered",
    "pending + stale | unprovable | unverified serialization -> invalidated",
    "non-pending + any event -> no-op",
    "still-`pending` handoff to `deploying`",
    "repeated wake must be a no-op",
):
    require_text(release, phrase, "templates/RELEASE_HANDOFF.md")

try:
    subprocess.run(["sh", str(adapter_test_path)], check=True)
except subprocess.CalledProcessError as error:
    fail(f"block adapter tests failed: exit {error.returncode}")

print(f"PASS: {len(ROLES)} router roles and marker-block contracts")
