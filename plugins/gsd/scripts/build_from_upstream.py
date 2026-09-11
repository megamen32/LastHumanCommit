#!/usr/bin/env python3
"""Build the portable GSD Agent Plugin from an isolated upstream install."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from emit_opencode import emit


ADAPTER = """<gsd_agent_plugin_adapter>
This GSD distribution is loaded from an Agent Plugin rather than a fixed runtime home.

- Resolve `GSD_PLUGIN_ROOT` as the absolute directory two levels above this `SKILL.md`.
- Resolve every `@../../...` execution-context reference relative to this skill directory.
- Before running a workflow shell command, replace `gsd-sdk` with
  `node \"$GSD_PLUGIN_ROOT/bin/gsd-sdk.js\"` and turn any `../../get-shit-done/...`
  command path into an absolute path below `$GSD_PLUGIN_ROOT`.
- Named GSD agent prompts live in `$GSD_PLUGIN_ROOT/agents/`. If the runtime has no
  matching registered agent type, spawn an available generic worker/default agent and
  include the corresponding `agents/<name>.md` prompt in its task message.
</gsd_agent_plugin_adapter>

"""


def replace_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-prefix", required=True)
    args = parser.parse_args()

    version_file = args.projection / "VERSION"
    if not version_file.exists():
        version_file = args.projection / "get-shit-done" / "VERSION"
    version = version_file.read_text().strip()
    package_meta = json.loads((args.package / "package.json").read_text())
    if package_meta.get("version") != version:
        raise SystemExit(f"version mismatch: projection={version} package={package_meta.get('version')}")

    for name in ("skills", "get-shit-done", "agents"):
        replace_tree(args.projection / name, args.output / name)
    replace_tree(args.package / "sdk" / "dist", args.output / "sdk" / "dist")
    replace_tree(args.package / "sdk" / "shared", args.output / "sdk" / "shared")
    replace_tree(args.package / "sdk" / "prompts", args.output / "sdk" / "prompts")
    replace_tree(args.package / "node_modules", args.output / "node_modules")
    shutil.copy2(args.package / "sdk" / "package.json", args.output / "sdk" / "package.json")
    shutil.copy2(args.package / "package-lock.json", args.output / "package-lock.upstream.json")
    (args.output / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.package / "bin" / "gsd-sdk.js", args.output / "bin" / "gsd-sdk.js")
    shutil.copy2(args.package / "LICENSE", args.output / "LICENSE.upstream")

    for skill_file in sorted((args.output / "skills").glob("*/SKILL.md")):
        text = skill_file.read_text()
        text = text.replace(args.source_prefix, "../..")
        marker = text.find("---", 4)
        if marker < 0:
            raise SystemExit(f"missing frontmatter terminator: {skill_file}")
        insert_at = marker + 3
        text = text[:insert_at] + "\n\n" + ADAPTER + text[insert_at:].lstrip("\n")
        skill_file.write_text(text)

    (args.output / "VERSION").write_text(version + "\n")
    emit(
        args.output,
        package_name="@megamen32/gsd-opencode-plugin",
        includes=[
            "agents",
            "bin",
            "get-shit-done",
            "sdk",
            "README.md",
            "UPSTREAM.json",
            "VERSION",
            "LICENSE.upstream",
        ],
        dependencies_from=args.package / "sdk/package.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
