#!/usr/bin/env python3
"""Regression checks for the portable approval-policy boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_core_instructions_defer_approval_policy_to_active_harness() -> None:
    ownership = "The active harness owns approval policy."
    for relative_path in ("AGENTS.md", "CLAUDE.md", "src/common/agents/Lead.md"):
        assert ownership in read(relative_path), relative_path


def test_lhc_has_no_mandatory_human_approval_gates() -> None:
    sources = {
        "AGENTS.md": read("AGENTS.md"),
        "CLAUDE.md": read("CLAUDE.md"),
        "src/common/agents/Lead.md": read("src/common/agents/Lead.md"),
        "templates/FULL_CYCLE.md": read("templates/FULL_CYCLE.md"),
        "templates/RELEASE_HANDOFF.md": read("templates/RELEASE_HANDOFF.md"),
    }
    forbidden = (
        "two explicit human approvals",
        "second explicit approval",
        "Do not implement before explicit selection.",
        "Do not implement before the second approval.",
        "requires one direct question at the exact action",
        "Silence never authorizes them.",
        "Без явного `да` deploy не выполняется",
    )
    for relative_path, value in sources.items():
        for phrase in forbidden:
            assert phrase not in value, f"{relative_path} still requires: {phrase}"
