#!/usr/bin/env python3
"""Run one read-only loader canary for Codex, Claude Code, or OpenCode."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from validate import (
    ValidationError,
    check_native_manifest,
    discover_skills,
    load_json,
)


def default_plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(runtime: str, root: Path) -> None:
    skills = discover_skills(root)
    if runtime == "codex":
        target = check_native_manifest(root, ".codex-plugin/plugin.json", "Codex")
        if target != root / "skills":
            raise ValidationError("Codex loader path is not the package skills directory")
    elif runtime == "claude":
        target = check_native_manifest(root, ".claude-plugin/plugin.json", "Claude Code")
        if target != root / "skills":
            raise ValidationError("Claude Code loader path is not the package skills directory")
    elif runtime == "opencode":
        helper = root / "scripts" / "opencode-config.py"
        completed = subprocess.run(
            [sys.executable, str(helper), "--plugin-root", str(root)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ValidationError(completed.stderr.strip() or "OpenCode helper failed")
        try:
            config = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"OpenCode helper did not return JSON: {exc}") from exc
        skills_config = config.get("skills")
        if not isinstance(skills_config, dict) or skills_config.get("paths") != [str(root / "skills")]:
            raise ValidationError("OpenCode native config does not point to the package skills directory")
        if not (root / "skills").is_dir():
            raise ValidationError("OpenCode skills source is missing")
    else:
        raise ValidationError(f"unknown runtime: {runtime}")
    print(f"{runtime} loader canary: PASS skills={len(skills)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", choices=("codex", "claude", "opencode"))
    parser.add_argument("--plugin-root", type=Path, default=default_plugin_root())
    args = parser.parse_args()
    try:
        run(args.runtime, args.plugin_root.expanduser().resolve())
        return 0
    except (OSError, ValidationError, ValueError) as exc:
        print(f"{args.runtime} loader canary: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
