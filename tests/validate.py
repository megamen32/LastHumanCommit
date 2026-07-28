#!/usr/bin/env python3
"""Validate the canonical agent store without third-party dependencies."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "AGENTS.md",
    "ROADMAP.md",
    "src/project/ROADMAP.md",
    "VERSION",
    "install.sh",
    "src/global/entry.md.in",
    "src/project/entry.md.in",
    "src/project/ROADMAP.md",
    "src/common/agents/Lead.md",
    "src/common/agents/Explorer.md",
    "src/common/agents/Worker.md",
    "src/common/agents/Reviewer.md",
    "src/common/agents/Overseer.md",
    "src/common/agents/Adviser.md",
    "src/common/agents/Critic.md",
    "src/common/protocols/STOP_RETHINK.md",
    "src/common/profiles/Code.md",
    "src/common/profiles/Infrastructure.md",
    "src/common/templates/.agents/orchestrator.md",
    "src/common/templates/.agents/bugs/bug_template.md",
    "src/common/templates/.agents/kanban.md",
    "src/common/templates/.agents/tasks/task_template.md",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


missing = sorted(path for path in REQUIRED if not (ROOT / path).is_file())
if missing:
    fail(f"missing files: {', '.join(missing)}")

core = (ROOT / "src/global/entry.md.in").read_text(encoding="utf-8")
if len(core) > 800:
    fail(f"src/global/entry.md.in is {len(core)} characters; budget is 800")

required_core = (
    "You are **L**",
    "Overseer every 30 minutes",
    "P0 CONFIRMED",
    "P0 NOT CONFIRMED",
    "ROADMAP.md",
)
for phrase in required_core:
    if phrase not in core:
        fail(f"src/global/entry.md.in lacks required phrase: {phrase}")

role_prompts = {
    "Lead.md": ("I am L", "workflow"),
    "Adviser.md": ("I am a subagent", "workflow"),
    "Critic.md": ("I am a subagent", "workflow"),
    "Explorer.md": ("I am a subagent", "workflow"),
    "Overseer.md": ("I am a subagent", "workflow"),
    "Reviewer.md": ("I am a subagent", "workflow"),
    "Worker.md": ("I am a subagent", "workflow"),
}
for name, phrases in role_prompts.items():
    prompt = (ROOT / "src/common/agents" / name).read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in prompt:
            fail(f"src/common/agents/{name} lacks required phrase: {phrase}")

subagent_names = ("Adviser.md", "Critic.md", "Explorer.md", "Overseer.md", "Reviewer.md", "Worker.md")
for name in subagent_names:
    prompt = (ROOT / "src/common/agents" / name).read_text(encoding="utf-8")
    for phrase in ("L (Lead)", "## Shared workflow", "do only my assigned role", "commit every task-file edit"):
        if phrase not in prompt:
            fail(f"src/common/agents/{name} lacks shared workflow phrase: {phrase}")

lead = (ROOT / "src/common/agents/Lead.md").read_text(encoding="utf-8")
for phrase in (
    "Immediately launch bounded Explorers",
    "vertical slice",
    "P0/P1 still fails",
    "STOP_RETHINK.md",
    "Critic before closing complex",
    "`.agents/bugs/<id>.md`",
    "todo-{id}.md`, `work-{id}.md`, and `done-{id}.md",
    "every task-file edit",
    "verified fix commit",
    "Never depend on a",
    "shortest useful",
    "TL;DR: status and task-file path",
    "Do not duplicate its detailed Result",
    "tag meaningful",
):
    if phrase not in lead:
        fail(f"src/common/agents/Lead.md lacks required workflow guarantee: {phrase}")

explorer = (ROOT / "src/common/agents/Explorer.md").read_text(encoding="utf-8")
for phrase in ("primary sources", "source and date", "what was checked and excluded"):
    if phrase not in explorer:
        fail(f"src/common/agents/Explorer.md lacks required research guarantee: {phrase}")

task_template = (ROOT / "src/common/templates/.agents/tasks/task_template.md").read_text(encoding="utf-8")
for phrase in (
    "on any edit this file then commit it",
    "## Before Start",
    "Description:",
    "Severity: P0_URGENT | CORE | BEST_EFFORT | OPT_IN",
    "workflow:",
    "estimated min-max complete time:",
    "Acceptance:",
    "DO `git mv todo-<id>.md work-<id>.md`",
    "started (UTC+3):",
    "Executor:",
    "PID:",
    "Harness:",
    "session identifier:",
    "Next action:",
    "# Message layer",
    "## Notes",
    "## Blocker",
    ".agents/bugs/<id>.md",
    "DO `git mv work-<id>.md done-<id>.md`",
    "full durable result",
    "does not depend on a delivered agent message",
):
    if phrase not in task_template:
        fail(f"task template lacks lifecycle contract: {phrase}")

for path in (
    ROOT / "src/common/templates/.agents/bugs.md",
    ROOT / "src/common/templates/.agents/subagents.jsonl",
):
    if path.exists():
        fail(f"obsolete shared registry still exists: {path.relative_to(ROOT)}")

for phrase in ("wip-<id>", "Transition:", "Harness and session ID (best effort)"):
    if phrase in task_template:
        fail(f"task template retains obsolete field: {phrase}")

checked_docs = list((ROOT / "src").rglob("*.md")) + [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "docs/agent-authoring.md",
]
for path in checked_docs:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.rstrip() != line:
            fail(f"trailing whitespace: {path.relative_to(ROOT)}:{number}")
        if any("\u0400" <= char <= "\u04ff" for char in line):
            fail(f"non-English text: {path.relative_to(ROOT)}:{number}")

print(f"PASS: {len(REQUIRED)} required files; global entry={len(core)} characters")
