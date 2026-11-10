#!/usr/bin/env python3
"""Whether this task may use subagents (Workers, Testers, Advisers, councils): on unless refused.

Priority, highest first:
  1. an explicit word of the owner in the task text (воркеры, субагенты, параллельно, council, ...);
  2. the field  subagents: on|off  in <primary checkout>/.agents/PROJECT.md;
  3. ~/.config/lhc/workflow.json  {"subagents": "on|off"};
  4. the package config/workflow.json, then the built-in default: on.

    python3 lhc_subagents.py [--repo DIR] [--task TEXT]     prints {"subagents": "on|off", "source": ...}
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

VALUES = ("on", "off")
ASK = re.compile(r"воркер|субагент|параллельн|council|совет\s+моделей|subagent|in parallel", re.I)
REFUSE = re.compile(r"(?:\bбез|\bне\s+нужн\w*|\bне\s+используй\w*|\bне\s+запускай\w*|\bno|\bwithout|\bdon'?t\s+use|\bnot)\s+"
                    r"(?:использовани\w+\s+)?(?:воркер|субагент|агент|subagent|agent|worker|council|параллельн)", re.I)


def from_task(task):
    task = task or ""
    if REFUSE.search(task):
        return "off"
    return "on" if ASK.search(task) else None


def primary_root(repo):
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, timeout=5, check=True).stdout.strip()
        return Path(out).parent
    except (OSError, subprocess.SubprocessError):
        return Path(repo)


def from_project(repo):
    try:
        text = (primary_root(repo) / ".agents" / "PROJECT.md").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^subagents:\s*(on|off)\s*$", text, re.I | re.M)
    return match.group(1).lower() if match else None


def from_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = data.get("subagents") if isinstance(data, dict) else None
    return value if value in VALUES else None


def resolve(repo=None, task="", config_home=None, package=None):
    """The effective mode and the layer that decided it."""
    repo = repo or Path.cwd()
    value = from_task(task)
    if value:
        return {"subagents": value, "source": "task"}
    value = from_project(repo)
    if value:
        return {"subagents": value, "source": ".agents/PROJECT.md"}
    home = Path(config_home or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    value = from_json(home / "lhc" / "workflow.json")
    if value:
        return {"subagents": value, "source": "~/.config/lhc/workflow.json"}
    here = Path(__file__).resolve().parent
    for base in ([Path(package)] if package else [here.parent, here, here.parent / "common"]):
        value = from_json(base / "config" / "workflow.json")
        if value:
            return {"subagents": value, "source": "package config"}
    return {"subagents": "on", "source": "default"}


def enabled(repo=None, task=""):
    return resolve(repo, task)["subagents"] == "on"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--task", default="")
    args = parser.parse_args(argv)
    print(json.dumps(resolve(args.repo, args.task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

