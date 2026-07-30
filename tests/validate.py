#!/usr/bin/env python3
"""Validate the small, dependency-free YAGNI text canon."""

from pathlib import Path

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

for path in (
    agents_path,
    claude_path,
    lead_path,
    roadmap_path,
    release_path,
    planning_path,
):
    if not path.is_file():
        fail(f"missing text contract: {path.relative_to(ROOT)}")

if (ROOT / "CANON.md").exists():
    fail("CANON.md must be absent; AGENTS.md is the portable router")

if agents_path.read_bytes() != claude_path.read_bytes():
    fail("AGENTS.md and CLAUDE.md must be byte-identical")

router = agents_path.read_text(encoding="utf-8")
lead = lead_path.read_text(encoding="utf-8")
roadmap = roadmap_path.read_text(encoding="utf-8")

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
    "For Full work, load `src/common/profiles/Planning.md` before presenting plans.",
    "Direct, Short, and Emergency work stay proportional; they do not gain planning ceremony unless",
):
    require_text(lead, phrase, "src/common/agents/Lead.md")

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

if "agent_resume" not in lead and "available harness cron" not in lead:
    fail("src/common/agents/Lead.md must self-resume via agent_resume or available harness cron")

require_text(roadmap, "## Proposed", "ROADMAP.md")
require_text(roadmap, "Agents Capable Start", "ROADMAP.md")
require_text(roadmap, "Agents Capable End", "ROADMAP.md")

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

print(f"PASS: {len(ROLES)} router roles and YAGNI text contracts")
