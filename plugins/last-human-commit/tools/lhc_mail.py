#!/usr/bin/env python3
"""File mail between sessions of one project: it keeps working when the harness messaging does not.

A message is one file in the primary checkout: .agents/mail/<to>/<time>-<from>-<kind>.md.
The sender writes it and goes on, it never waits. The reader takes the oldest file,
acts, then moves it to done/. Kinds: task | step | question | result | ping.

Commands: send --to ID --from ID --kind K TEXT | inbox --me ID | ack --me ID FILE
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

KINDS = ("task", "step", "question", "result", "ping")


def primary_root(cwd):
    """The checkout that holds .git, the same for every worktree of the project."""
    out = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    return Path(out).parent


def box(root, session):
    if not session or any(c in session for c in "/\\") or session in {".", ".."}:
        raise ValueError("bad session id")
    return Path(root) / ".agents" / "mail" / session


def send(root, to, sender, kind, text, now=None):
    if kind not in KINDS:
        raise ValueError("kind must be one of " + ", ".join(KINDS))
    now = now or datetime.now(timezone.utc)
    folder = box(root, to)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{now.strftime('%Y%m%dT%H%M%S%f')}-{sender}-{kind}.md"
    tmp = folder / (name + ".tmp")
    tmp.write_text(f"from: {sender}\nkind: {kind}\n\n{text.strip()}\n", encoding="utf-8")
    os.replace(tmp, folder / name)
    return folder / name


def inbox(root, me):
    folder = box(root, me)
    return sorted(p for p in folder.glob("*.md")) if folder.is_dir() else []


def ack(root, me, name):
    source = box(root, me) / Path(name).name
    done = source.parent / "done"
    done.mkdir(exist_ok=True)
    os.replace(source, done / source.name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("send")
    cmd.add_argument("--to", required=True)
    cmd.add_argument("--from", dest="sender", required=True)
    cmd.add_argument("--kind", default="step", choices=KINDS)
    cmd.add_argument("text")
    cmd = commands.add_parser("inbox")
    cmd.add_argument("--me", required=True)
    cmd = commands.add_parser("ack")
    cmd.add_argument("--me", required=True)
    cmd.add_argument("file")
    args = parser.parse_args(argv)
    try:
        root = primary_root(Path.cwd())
        if args.command == "send":
            print(send(root, args.to, args.sender, args.kind, args.text))
        elif args.command == "inbox":
            for path in inbox(root, args.me):
                print(f"== {path.name}\n{path.read_text(encoding='utf-8')}")
        else:
            ack(root, args.me, args.file)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"mail: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
