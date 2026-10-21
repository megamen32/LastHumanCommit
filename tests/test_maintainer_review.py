#!/usr/bin/env python3
"""A PR into a repository we do not own passes the owner's own review first."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def compact(value: str) -> str:
    return " ".join(value.split())


def test_the_skill_exists_in_the_factory_and_the_authored_set():
    factory = ROOT / "src/common/skills/maintainer-review/SKILL.md"
    authored = ROOT / "skills/maintainer-review/SKILL.md"
    assert factory.is_file()
    assert authored.is_file()
    assert factory.read_bytes() == authored.read_bytes()


def test_the_skill_describes_the_gate_in_full():
    skill = read("src/common/skills/maintainer-review/SKILL.md")
    for phrase in (
        "repositories we do not own",
        "before the PR is opened",
        "maintainer: a senior engineer",
        "The project, before the diff",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CODEOWNERS",
        "CI workflow files",
        "A mountain of specific, actionable findings",
        "Do not invent findings to look thorough",
        "CLEAN",
        "the review is redone, not assumed",
    ):
        assert phrase in skill, phrase


def test_the_role_is_the_projects_own_strict_maintainer():
    role = read("src/common/agents/Maintainer.md")
    assert "strict senior engineer of the target project" in role
    assert "I read the project first, then the diff" in role
    assert "I am read-only about the target project" in role
    assert "maintainer-review/SKILL.md" in role
    assert "never a rubber stamp" in role


def test_the_delivery_protocol_makes_it_a_gate_before_the_pr():
    protocol = compact(read("src/common/protocols/REVIEW_TO_DELIVERY.md"))
    assert "Before a PR into a project you do not own" in protocol
    assert "before the PR is opened" in protocol
    assert "maintainer-review/SKILL.md" in protocol
    assert "Only a clean or explicitly answered review lets the PR be opened" in protocol


def test_the_lead_owns_running_it():
    lead = compact(read("src/common/agents/Lead.md"))
    assert "Before opening a PR into a repository you do not own" in lead
    assert "maintainer-review/SKILL.md" in lead
    assert "Our own repositories do not need it" in lead


def test_the_router_carries_the_rule_and_stays_english():
    router = read("AGENTS.md")
    assert "a fresh strong session plays that project's" in router
    assert "Only a clean or explicitly answered review lets the PR open" in router
    assert not re.search("[А-Яа-яЁё]", router)
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8") == router


def test_the_skill_is_registered_everywhere_it_must_be():
    validate = read("plugins/last-human-commit/scripts/validate.py")
    assert '"maintainer-review"' in validate
    manifest = read("adapters/manifest.yaml")
    assert "name: maintainer-review" in manifest
    assert "owner: Maintainer" in manifest
    catalog = read("src/common/skills/README.md")
    assert "maintainer-review" in catalog
    roles = read("tests/validate.py")
    assert '"Maintainer"' in roles


def test_the_package_ships_the_skill_and_the_role():
    package = ROOT / "plugins/last-human-commit"
    assert (package / "skills/maintainer-review/SKILL.md").is_file()
    assert (package / "common/skills/maintainer-review/SKILL.md").is_file()
    assert (package / "common/agents/Maintainer.md").is_file()


def test_the_philosophy_records_the_rule():
    philosophy = read("PRODUCT-PHILOSOPHY.md")
    assert "12a. Если проект не наш — сначала хозяин" in philosophy
    assert "Грязный PR, дошедший до хозяина, дороже позднего" in philosophy
    assert "maintainer-review" in philosophy
