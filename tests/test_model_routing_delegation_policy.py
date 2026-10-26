from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]




def test_final_writer_owns_clarity_but_internal_messages_may_be_compact():
    router = (ROOT / "AGENTS.md").read_text()
    umbrella = (ROOT / "src/common/skills/last-human-commit/SKILL.md").read_text()
    routing = (ROOT / "src/common/skills/model-routing/SKILL.md").read_text()
    lead = (ROOT / "src/common/agents/Lead.md").read_text()
    worker = (ROOT / "src/common/agents/Worker.md").read_text()
    for source in (router, umbrella, routing, lead, worker):
        flat = " ".join(source.split())
        assert "Internal" in flat and "any language" in flat
        assert "user-facing" in flat
        assert "Russian-speaking reader" in flat
        assert "Russian" in flat and "language" in flat
        assert "Use English for internal" not in flat
        assert "English operating records and coordination" not in flat


def test_fresh_blind_context_is_reserved_for_independent_acceptance_roles():
    routing = (ROOT / "src/common/skills/model-routing/SKILL.md").read_text()
    worker = (ROOT / "src/common/agents/Worker.md").read_text()
    lead = (ROOT / "src/common/agents/Lead.md").read_text()
    sources = " ".join("\n".join((routing, worker, lead)).lower().split())

    assert "fresh, blind context for an independent role" in sources
    assert "independence is part of" in sources
    assert "ordinary executors receive verified decisions and necessary context" in sources
    assert "Prefer zero-knowledge executors: a fresh context for each independent subtask" not in routing


def test_generated_native_package_matches_routing_policy_sources():
    expected_router = (ROOT / "AGENTS.md").read_bytes().replace(b"src/common/", b"common/")
    assert (ROOT / "plugins/last-human-commit/AGENTS.md").read_bytes() == expected_router
    for source, generated in (
        (
            "src/common/skills/last-human-commit/SKILL.md",
            "plugins/last-human-commit/skills/last-human-commit/SKILL.md",
        ),
        ("src/common/agents/Lead.md", "plugins/last-human-commit/common/agents/Lead.md"),
        ("src/common/agents/Worker.md", "plugins/last-human-commit/common/agents/Worker.md"),
        (
            "src/common/skills/model-routing/SKILL.md",
            "plugins/last-human-commit/skills/model-routing/SKILL.md",
        ),
        (
            "src/common/skills/plan-artifacts/SKILL.md",
            "plugins/last-human-commit/skills/plan-artifacts/SKILL.md",
        ),
    ):
        expected = (ROOT / source).read_bytes()
        if source.startswith("src/common/") and not source.endswith(
            ("last-human-commit/SKILL.md", "plan-artifacts/SKILL.md")
        ):
            expected = expected.replace(b"src/common/", b"common/")
        if source.endswith("model-routing/SKILL.md"):
            expected = expected.replace(
                b"../../config/model-routing.example.json",
                b"references/model-routing.example.json",
            )
        assert (ROOT / generated).read_bytes() == expected


def _assert_native_copy_matches(source: str, generated: str, replacements: tuple[tuple[bytes, bytes], ...] = ()):
    expected = (ROOT / source).read_bytes()
    for old, new in replacements:
        expected = expected.replace(old, new)
    _assert_native_bytes(expected, (ROOT / generated).read_bytes())


def _assert_native_bytes(expected: bytes, actual: bytes):
    assert actual == expected


def test_native_codex_copies_match_canonical_routing_policy_sources(tmp_path):
    common_rewrite = ((b"src/common/", b"common/"),)
    routing_rewrites = common_rewrite + (
        (b"../../config/model-routing.example.json", b"references/model-routing.example.json"),
    )
    copies = (
        ("AGENTS.md", "plugins/last-human-commit/native/codex/AGENTS.md", common_rewrite),
        (
            "src/common/skills/last-human-commit/SKILL.md",
            "plugins/last-human-commit/native/codex/skills/last-human-commit/SKILL.md",
            (),
        ),
        (
            "src/common/agents/Lead.md",
            "plugins/last-human-commit/native/codex/common/agents/Lead.md",
            common_rewrite,
        ),
        (
            "src/common/agents/Worker.md",
            "plugins/last-human-commit/native/codex/common/agents/Worker.md",
            common_rewrite,
        ),
        (
            "src/common/skills/model-routing/SKILL.md",
            "plugins/last-human-commit/native/codex/skills/model-routing/SKILL.md",
            routing_rewrites,
        ),
        (
            "src/common/skills/plan-artifacts/SKILL.md",
            "plugins/last-human-commit/native/codex/skills/plan-artifacts/SKILL.md",
            (),
        ),
    )

    # Demonstrate that the same check catches stale content without touching a generated copy.
    stale_copy = tmp_path / "stale-AGENTS.md"
    stale_copy.write_bytes(b"stale")
    expected_router = (ROOT / "AGENTS.md").read_bytes().replace(*common_rewrite[0])
    with pytest.raises(AssertionError):
        _assert_native_bytes(expected_router, stale_copy.read_bytes())

    for source, generated, replacements in copies:
        _assert_native_copy_matches(source, generated, replacements)
