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


def test_the_skill_describes_the_full_maintainer_contract():
    skill = compact(read("src/common/skills/maintainer-review/SKILL.md"))
    for phrase in (
        "Before a PR into a repository you do not own",
        "let that project's strict maintainer read the project and the diff",
        "maintainer: a senior engineer",
        "The project, before the diff",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CODEOWNERS",
        "CI workflow files",
        "Specific, actionable findings",
        "Do not invent findings to look thorough",
        "CLEAN",
        "the maintainer's own reaction to a foreign PR",
    ):
        assert phrase in skill, phrase
    # The current contract: the review is conditional on policy or real risk,
    # and it never turns into an automatic LHC gate or an invented clean claim.
    assert "Ownership alone does not create an LHC gate" in skill
    assert "Do not invent `CLEAN` or `PASS` claims" in skill
    assert "A reviewer response, LHC receipt or non-blocking preference is not a release veto" in skill
    assert "Preserve unresolved material defects as blockers" in skill


def test_the_role_is_the_projects_own_strict_maintainer():
    role = read("src/common/agents/Maintainer.md")
    assert "strict senior engineer of the target project" in role
    assert "I read the project first, then the diff" in role
    assert "I am read-only about the target project" in role
    assert "maintainer-review/SKILL.md" in role
    assert "never a rubber stamp" in role


def test_the_delivery_protocol_binds_external_review_to_the_target_policy():
    protocol = compact(read("src/common/protocols/REVIEW_TO_DELIVERY.md"))
    assert "## Review for external repositories" in protocol
    assert "Follow the target repository's actual contribution policy" in protocol
    assert "assign a Reviewer from the allowed model families" in protocol
    assert "Fix concrete defects that affect the accepted claim or required policy" in protocol
    assert "never claim a clean result without evidence" in protocol
    assert "Preferences and LHC ledger, manifest or identity-registration state are not delivery vetoes" in protocol
    assert "Preserve actual negative findings and required project checks" in protocol


def test_the_lead_owns_the_external_repository_review():
    lead = compact(read("src/common/agents/Lead.md"))
    assert "Before a PR into another repository, follow that repository's actual contribution policy" in lead
    assert "Use an allowed-model Reviewer when it can identify concrete defects or material risk" in lead
    assert "Fix findings that affect the accepted claim or required policy" in lead
    assert "preferences and LHC bookkeeping alone are not delivery vetoes" in lead


def test_the_router_carries_the_rule_and_stays_english():
    router = read("AGENTS.md")
    assert "a fresh Reviewer from an allowed model tier plays that project's maintainer" in router
    assert "An LHC receipt or bookkeeping status alone is not a release veto" in router
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
