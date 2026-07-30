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
    if phrase not in text:
        fail(f"{source} lacks: {phrase}")


agents_path = ROOT / "AGENTS.md"
claude_path = ROOT / "CLAUDE.md"
lead_path = ROOT / "src/common/agents/Lead.md"
roadmap_path = ROOT / "ROADMAP.md"

for path in (agents_path, claude_path, lead_path, roadmap_path):
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

for forbidden in ("Web", "credential", "Agent Fleet", "external scheduler"):
    if forbidden.lower() in router.lower() or forbidden.lower() in lead.lower():
        fail(f"router and Lead must not own a {forbidden} rule")

for phrase in (
    "Ultimate perfect totally ideal",
    "Normal",
    "YAGNI MVP",
    "explicit human selection",
    "GLM",
    "DeepSeek",
    "MiniMax",
    "Kimi",
    "Mimo",
    "30 minutes",
):
    require_text(lead, phrase, "src/common/agents/Lead.md")

if "agent_resume" not in lead and "available harness cron" not in lead:
    fail("src/common/agents/Lead.md must self-resume via agent_resume or available harness cron")

require_text(roadmap, "## Proposed", "ROADMAP.md")

print(f"PASS: {len(ROLES)} router roles and YAGNI text contracts")
