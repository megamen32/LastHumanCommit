#!/usr/bin/env python3
"""Validate the small, text-only LastHumanCommit contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "CANON.md",
    "README.md",
    "ROADMAP.md",
    "src/common/agents/Lead.md",
    "src/common/agents/Adviser.md",
    "src/common/templates/.agents/kanban.md",
    "src/common/templates/.agents/tasks/task_template.md",
    "templates/FULL_CYCLE.md",
    "templates/RELEASE_HANDOFF.md",
)

RETIRED = (
    "install.sh",
    "VERSION",
    "tests/test_installer.py",
    "src/global/entry.md.in",
    "src/project/entry.md.in",
)


def fail(message: str) -> None:
    """Exit with one readable contract failure."""
    raise SystemExit(f"FAIL: {message}")


for relative in REQUIRED:
    if not (ROOT / relative).is_file():
        fail(f"missing text contract: {relative}")

for relative in RETIRED:
    if (ROOT / relative).exists():
        fail(f"retired runtime surface still exists: {relative}")

runtime_files = sorted(
    path.relative_to(ROOT)
    for suffix in ("*.sh", "*.service", "*.timer")
    for path in ROOT.rglob(suffix)
    if ".git" not in path.parts
)
if runtime_files:
    fail(f"runtime files are outside this text canon: {', '.join(map(str, runtime_files))}")

canon = (ROOT / "CANON.md").read_text(encoding="utf-8")
ordered = (
    "Ultimate perfect totally ideal",
    "Normal",
    "YAGNI MVP",
)
positions = [canon.find(phrase) for phrase in ordered]
if any(position < 0 for position in positions) or positions != sorted(positions):
    fail("CANON.md must contain the three plans in the required order")

for phrase in (
    "Research the request and repository",
    "bounded subagents",
    "Wait for explicit human selection",
    "Do not implement before the human selects one plan.",
    "Call-stack tree",
    "File-tree diff",
    "Key types and method signatures",
    "fable | sol",
    "opus | terra",
    "sonnet | luna",
    "haiku | 5.4mini",
    "Russian mobile review",
    "external deploy handoff",
    "30 minutes",
    "Stop after the handoff.",
    "open every named site in a real browser",
    "approved credential retrieval reference",
):
    if phrase not in canon:
        fail(f"CANON.md lacks: {phrase}")

contract_checks = {
    "src/common/agents/Lead.md": (
        "Research first",
        "Ultimate perfect totally ideal, Normal, YAGNI MVP",
        "explicit human selection",
        "external deploy handoff",
    ),
    "src/common/agents/Adviser.md": ordered,
    "templates/FULL_CYCLE.md": (
        "## Research",
        "### 1. Ultimate perfect totally ideal",
        "### 2. Normal",
        "### 3. YAGNI MVP",
        "Human selection",
        "## Selected-plan WSFF",
    ),
    "templates/RELEASE_HANDOFF.md": (
        "## Russian mobile review",
        "Eligibility is not deployment",
        "A new commit",
        "failed tests",
        "changed target",
        "owner:",
        "target:",
        "commit_or_artifact:",
        "acceptance_proof:",
        "rollback_reference:",
        "review_sent_at:",
        "eligible_not_before:",
        "veto_state:",
    ),
}
for relative, phrases in contract_checks.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            fail(f"{relative} lacks: {phrase}")

task_state = "todo -> work -> done"
for relative in (
    "README.md",
    "src/common/agents/Lead.md",
    "src/common/templates/.agents/kanban.md",
    "src/common/templates/.agents/tasks/task_template.md",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    if task_state not in text:
        fail(f"{relative} lacks the shared task state: {task_state}")

for relative in REQUIRED:
    text = (ROOT / relative).read_text(encoding="utf-8")
    if "@CANON_ROOT@" in text:
        fail(f"{relative} contains installer placeholder @CANON_ROOT@")

print(f"PASS: {len(REQUIRED)} text contracts; no shell/service runtime surface")
