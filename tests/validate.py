#!/usr/bin/env python3
"""Validate the small, dependency-free YAGNI text canon."""

from pathlib import Path
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
    for key in ("role_source", "optional_instructions"):
        prefix = f"{key}:"
        value = next(
            (line.split(":", 1)[1].strip() for line in manifest.splitlines()
             if line.startswith(prefix)),
            "",
        )
        if not value or not (adapter_dir / value).exists():
            fail(f"{adapter} manifest has missing {key}: {value or '<empty>'}")
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
    ROOT / "src/common/templates/.agents/kanban.md",
    ROOT / "src/common/templates/.agents/orchestrator.md",
):
    if path.exists():
        fail("templates must not be split between src/common/templates and templates")
for path in (
    ROOT / "templates/.agents/kanban.md",
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

for phrase in (
    "Ultimate perfect totally ideal",
    "Normal",
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
    "Review the whole repository",
    "Reviewer",
    "Critic once",
    "For Full work, load `../profiles/Planning.md` relative to this role file before presenting plans.",
    "Direct, Short, and Emergency work stay proportional; they do not gain planning ceremony unless",
    "Mandatory self-improve",
    "../protocols/SELF_IMPROVE.md",
    "Shared worktree",
    "five minutes",
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
for text, source in ((worker, "Worker.md"), (reviewer, "Reviewer.md")):
    require_text(text, "shared worktree", source)
    require_text(text, "five minutes", source)

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
    "Do not silently rewrite the canon",
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
    "Use this profile for Full work",
    "optimistic / likely / pessimistic",
    "relative cost",
    "more than 20 likely active minutes",
    "Every fresh child receives a Task Card",
    "NEEDS_REDECOMPOSITION",
    "Use a no-history child only when the harness demonstrably supports it",
    "do not claim model-routing or fresh-context proof",
):
    require_text(planning, phrase, "src/common/profiles/Planning.md")

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
