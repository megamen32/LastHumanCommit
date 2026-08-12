#!/usr/bin/env python3
"""Print an OpenCode skills source for this plugin without changing user config."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def default_plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_config(root: Path, output_format: str) -> dict[str, object]:
    root = root.expanduser().resolve()
    skills = root / "skills"
    if not skills.is_dir():
        raise ValueError(f"plugin skills directory does not exist: {skills}")
    skills_value: object
    if output_format == "native":
        # The installed OpenCode 1.18.x config surface uses ConfigSkillsV1:
        # an object containing additional search paths and/or URLs.
        skills_value = {"paths": [os.fspath(skills)]}
    elif output_format == "v2":
        # OpenCode's current v2 documentation describes the compact array form.
        skills_value = [os.fspath(skills)]
    else:
        raise ValueError(f"unsupported output format: {output_format}")
    return {
        "$schema": "https://opencode.ai/config.json",
        "skills": skills_value,
        "plugin": [os.fspath(root / "opencode" / "lhc-time-guard.ts")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, default=default_plugin_root())
    parser.add_argument(
        "--format",
        choices=("native", "v2"),
        default="native",
        help="OpenCode config shape; native matches the installed v1 surface",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the JSON fragment to this explicit path; stdout is the default",
    )
    args = parser.parse_args()
    try:
        payload = json.dumps(build_config(args.plugin_root, args.format), indent=2) + "\n"
        if args.output:
            output = args.output.expanduser()
            if not output.parent.is_dir():
                raise ValueError(f"output parent does not exist: {output.parent}")
            output.write_text(payload, encoding="utf-8")
            print(f"wrote OpenCode config fragment to {output}")
        else:
            sys.stdout.write(payload)
        return 0
    except (OSError, ValueError) as exc:
        print(f"OpenCode config error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
