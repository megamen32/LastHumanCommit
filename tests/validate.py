#!/usr/bin/env python3
"""Validate the canonical agent store without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "AGENTS.md",
    "agents/Lead.md",
    "agents/Explorer.md",
    "agents/Worker.md",
    "agents/Reviewer.md",
    "agents/Overseer.md",
    "agents/Adviser.md",
    "agents/Critic.md",
    "protocols/STOP_RETHINK.md",
    "profiles/Code.md",
    "profiles/Infrastructure.md",
    "templates/.agents/orchestrator.md",
    "templates/.agents/kanban.md",
    "templates/.agents/bugs.md",
    "templates/.agents/worklog.jsonl",
    "templates/.agents/subagents.jsonl",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


missing = sorted(path for path in REQUIRED if not (ROOT / path).is_file())
if missing:
    fail(f"missing files: {', '.join(missing)}")

core = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
if len(core) > 800:
    fail(f"AGENTS.md is {len(core)} characters; budget is 800")

required_core = (
    "You are **L**",
    "Overseer every 30 minutes",
    "P0 ПОДТВЕРЖДЁН",
    "P0 НЕ ПОДТВЕРЖДЁН",
)
for phrase in required_core:
    if phrase not in core:
        fail(f"AGENTS.md lacks required phrase: {phrase}")

for path in ROOT.rglob("*.md"):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.rstrip() != line:
            fail(f"trailing whitespace: {path.relative_to(ROOT)}:{number}")

for name in ("worklog.jsonl", "subagents.jsonl"):
    path = ROOT / "templates/.agents" / name
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid JSONL: {path.relative_to(ROOT)}:{number}: {exc}")

print(f"PASS: {len(REQUIRED)} required files; AGENTS.md={len(core)} characters")
