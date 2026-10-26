#!/usr/bin/env python3
"""Republish the generated package copies from the canonical sources.

The package under `plugins/last-human-commit/` is a projection of `src/common/`
and of the repository root files. A change in the canon that is not republished
leaves the package stale, and the projection gate turns red - which is how a
one-line edit of an instruction used to cost a release.

The entry router is a projection too. `AGENTS.md` is the only authored text;
`CLAUDE.md` exists because some harnesses read that filename instead of
`AGENTS.md`, and it carries exactly the same bytes. It is written here, so a
human never maintains two versions of the router.

This script makes the projection a command instead of a ritual:

    python3 scripts/publish_package.py            # republish what changed
    python3 scripts/publish_package.py --check    # report what is stale
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins" / "last-human-commit"
NATIVE = PACKAGE / "native" / "codex"

COMMON = ((b"src/common/", b"common/"),)
ROUTING = COMMON + (
    (b"../../config/model-routing.example.json", b"references/model-routing.example.json"),
)

# (source, generated, replacements)
# `AGENTS.md` is the single authored router: the root `CLAUDE.md` and both
# package router copies are projections of its bytes, never hand-edited files.
COPIES: tuple[tuple[str, str, tuple[tuple[bytes, bytes], ...]], ...] = (
    ("AGENTS.md", "CLAUDE.md", ()),
    # The native Codex package is the root the fleet installs for Codex, so the
    # facade and its MCP declaration travel with it as copies of the bytes.
    (
        "plugins/last-human-commit/scripts/plan_mcp.py",
        "plugins/last-human-commit/native/codex/scripts/plan_mcp.py",
        (),
    ),
    (
        "plugins/last-human-commit/.mcp.json",
        "plugins/last-human-commit/native/codex/.mcp.json",
        (),
    ),
    ("AGENTS.md", "plugins/last-human-commit/AGENTS.md", COMMON),
    ("AGENTS.md", "plugins/last-human-commit/CLAUDE.md", COMMON),
    ("AGENTS.md", "plugins/last-human-commit/native/codex/AGENTS.md", COMMON),
    ("AGENTS.md", "plugins/last-human-commit/native/codex/CLAUDE.md", COMMON),
    ("src/common/agents/Lead.md", "plugins/last-human-commit/common/agents/Lead.md", COMMON),
    ("src/common/agents/Worker.md", "plugins/last-human-commit/common/agents/Worker.md", COMMON),
    ("src/common/agents/Overseer.md", "plugins/last-human-commit/common/agents/Overseer.md", COMMON),
    ("src/common/agents/Overseer.md", "plugins/last-human-commit/native/codex/common/agents/Overseer.md", COMMON),
    (
        "src/common/agents/Lead.md",
        "plugins/last-human-commit/native/codex/common/agents/Lead.md",
        COMMON,
    ),
    (
        "src/common/agents/Worker.md",
        "plugins/last-human-commit/native/codex/common/agents/Worker.md",
        COMMON,
    ),
    (
        "src/common/skills/last-human-commit/SKILL.md",
        "skills/last-human-commit/SKILL.md",
        (),
    ),
    (
        "src/common/skills/last-human-commit/SKILL.md",
        "plugins/last-human-commit/skills/last-human-commit/SKILL.md",
        (),
    ),
    (
        "src/common/skills/last-human-commit/SKILL.md",
        "plugins/last-human-commit/native/codex/skills/last-human-commit/SKILL.md",
        (),
    ),
    (
        "src/common/skills/model-routing/SKILL.md",
        "plugins/last-human-commit/skills/model-routing/SKILL.md",
        ROUTING,
    ),
    (
        "src/common/skills/model-routing/SKILL.md",
        "plugins/last-human-commit/native/codex/skills/model-routing/SKILL.md",
        ROUTING,
    ),
    (
        "src/common/skills/plan-artifacts/SKILL.md",
        "plugins/last-human-commit/skills/plan-artifacts/SKILL.md",
        (),
    ),
    (
        "src/common/skills/plan-artifacts/SKILL.md",
        "plugins/last-human-commit/native/codex/skills/plan-artifacts/SKILL.md",
        (),
    ),
)

# The protocol, the template and the tool copies are projected the same way:
# the source text with the path of the package.
TOOL_COPIES = (
    "lhc_grid.py",
    "lhc_product.py",
    "lhc_entry.py",
    "lhc_parallel.py",
    "lhc_outcome.py",
    "lhc_outcome_review.py",
    "lhc_milestone.py",
    "lhc_time_guard.py",
    "lhc_progress_review.py",
    "lhc_active_time.py",
    "lhc_native_identity.py",
    "lhc_source_publication.py",
    "lhc_task_budget.py",
    "lhc_testing_reuse.py",
    "lhc_worktree.py",
    "lhc_chat.py",
    "lhc_plan_json.py",
    "lhc_plan_publish.py",
    "lhc_plan_transport.py",
    "lhc_plan_mirror.py",
    "lhc_plan_mcp.py",
    "lhc_plan_ui.py",
    "lhc_live.py",
    "lhc_git_facts.py",
    "lhc_gitlayout.py",
    "lhc_models.py",
)

TREE_FOLDERS = (
    "protocols",
    "templates",
)

def project(data: bytes, replacements: tuple[tuple[bytes, bytes], ...]) -> bytes:
    for old, new in replacements:
        data = data.replace(old, new)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="только показать расхождения")
    args = parser.parse_args()

    stale: list[str] = []
    published = 0

    def write(target: Path, data: bytes) -> None:
        nonlocal published
        if target.is_file() and target.read_bytes() == data:
            return
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            published += 1
        stale.append(str(target.relative_to(ROOT)))

    # The tool copies: byte for byte under tools/, and with the path of the
    # package under common/tools/.
    for name in TOOL_COPIES:
        source = ROOT / "src" / "common" / "tools" / name
        if not source.is_file():
            continue
        data = source.read_bytes()
        write(ROOT / "plugins" / "last-human-commit" / "tools" / name, data)
        write(ROOT / "plugins" / "last-human-commit" / "native" / "codex" / "tools" / name, data)
        # The same rewrite the bundle check applies, so the copy in the
        # package and the copy the check expects are the same bytes.
        rewritten = data
        for old_path, new_path in COMMON:
            rewritten = rewritten.replace(old_path, new_path)
        write(ROOT / "plugins" / "last-human-commit" / "common" / "tools" / name, rewritten)
        write(
            ROOT / "plugins" / "last-human-commit" / "native" / "codex" / "common" / "tools" / name,
            rewritten,
        )

    for source, generated, replacements in COPIES:
        source_path = ROOT / source
        if not source_path.is_file():
            print(f"нет источника: {source}", file=sys.stderr)
            continue
        write(ROOT / generated, project(source_path.read_bytes(), replacements))

    # Native Codex extension: preserve the portable/time-only bundle for other
    # clients and add only the explicitly supported async adapter here.
    codex_hooks = json.loads((ROOT / "adapters/codex/hooks/hooks.json").read_text())
    portable_hooks = json.loads((PACKAGE / "hooks/hooks.json").read_text())
    for event, registrations in portable_hooks["hooks"].items():
        codex_hooks["hooks"].setdefault(event, [])[:0] = registrations
    hook_data = (json.dumps(codex_hooks, ensure_ascii=False, indent=2) + "\n").encode()
    for prefix in (PACKAGE, NATIVE):
        write(prefix / "com.openai/hooks/hooks.json", hook_data)

    # A projected tool without a source is a leftover of a module that was
    # merged into another one. It ships as dead weight and it breaks the
    # bundle check, so it is reported instead of quietly staying.
    orphans = []
    for prefix in (
        "plugins/last-human-commit/tools",
        "plugins/last-human-commit/common/tools",
        "plugins/last-human-commit/native/codex/tools",
        "plugins/last-human-commit/native/codex/common/tools",
    ):
        directory = ROOT / prefix
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            if not (ROOT / "src" / "common" / "tools" / path.name).is_file():
                orphans.append(f"{prefix}/{path.name}")
    if orphans:
        print("осиротевшие проекции (нет источника в src/common/tools):", file=sys.stderr)
        for orphan in orphans:
            print(f"  {orphan}", file=sys.stderr)
        raise SystemExit(1)

    # The rest of the projected tree is republished only where the package
    # already has the file: the package is curated, not a mirror, and this
    # script must never grow it.
    for folder in TREE_FOLDERS:
        base = ROOT / "src" / "common" / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(base)
            for prefix in ("plugins/last-human-commit/common", "plugins/last-human-commit/native/codex/common"):
                target = ROOT / prefix / folder / relative
                if not target.is_file():
                    continue
                write(target, project(path.read_bytes(), COMMON))

    if stale:
        print("расхождений:", len(stale))
        for item in stale:
            print("  ", item)
        if not args.check:
            print("опубликовано:", published)
    else:
        print("проекции совпадают с каноном")
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
