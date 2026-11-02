#!/usr/bin/env python3
"""One version file, one counter, for every project the agents work on.

The project keeps its version in a root VERSION file: X.Y.Z.

* X changes when the contract breaks: a consumer of the old version stops working.
* Y changes when a compatible capability is added.
* Z changes for a fix, wording or documentation.

Every change that lands on the target branch raises the version by exactly one step
over the target's own VERSION. The number is not a lock by itself. What stops a
stale change from overwriting a newer one is that the check below fails as soon as the
target moved: the branch must be rebased, bumped again to the new next number and
re-tested. Take the bump last, right before the merge.

Commands (facts in, JSON out; exit status 1 on a failed check):

  next  --level x|y|z [--target origin/main]   print the next version over the target
  bump  --level x|y|z [--target origin/main]   fetch, then write VERSION = next
  check [--target origin/main]                 VERSION is exactly one step above the target
                                               and its tag is free
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def parse(text: str) -> tuple[int, int, int] | None:
    match = SEMVER.fullmatch(text.strip())
    return tuple(int(part) for part in match.groups()) if match else None


def step(old: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    if level == "x":
        return (old[0] + 1, 0, 0)
    if level == "y":
        return (old[0], old[1] + 1, 0)
    return (old[0], old[1], old[2] + 1)


def one_step_above(old: tuple[int, int, int], new: tuple[int, int, int]) -> str | None:
    """The level at which new follows old by exactly one step, or None."""
    for level in ("z", "y", "x"):
        if step(old, level) == new:
            return level
    return None


def git(repo: Path, *args: str) -> str | None:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def target_version(repo: Path, target: str) -> tuple[int, int, int] | None:
    """The target's VERSION; with none, the newest tag on it; with neither, 0.0.0."""
    text = git(repo, "show", f"{target}:VERSION")
    if text is not None:
        return parse(text)
    tag = git(repo, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", target)
    return (parse(tag.lstrip("v")) if tag else None) or (0, 0, 0)


def tag_taken(repo: Path, version: str, remote: str = "origin") -> bool | None:
    """True/False when known, None when the remote cannot be asked."""
    if git(repo, "tag", "--list", f"v{version}"):
        return True
    remote_tags = git(repo, "ls-remote", "--tags", remote, f"refs/tags/v{version}")
    return None if remote_tags is None else bool(remote_tags)


def check(repo: Path, target: str, remote: str = "origin") -> dict:
    path = repo / "VERSION"
    if not path.is_file():
        return {"ok": False, "reason": "no VERSION file in the repository root"}
    mine = parse(path.read_text(encoding="utf-8"))
    if mine is None:
        return {"ok": False, "reason": "VERSION must be X.Y.Z with plain numbers"}
    base = target_version(repo, target)
    if base is None:
        return {"ok": False, "reason": f"{target} has a VERSION that is not X.Y.Z"}
    shown = ".".join(map(str, mine))
    level = one_step_above(base, mine)
    if level is None:
        want = ", ".join(".".join(map(str, step(base, lv))) for lv in ("z", "y", "x"))
        return {"ok": False, "version": shown, "target_version": ".".join(map(str, base)),
                "reason": f"VERSION must be exactly one step above {target} ({want}). The target moved or "
                          "the bump is missing: rebase onto the target, bump again, re-run the tests."}
    taken = tag_taken(repo, shown, remote)
    if taken:
        return {"ok": False, "version": shown, "reason": f"tag v{shown} already exists"}
    return {"ok": True, "version": shown, "level": level, "target_version": ".".join(map(str, base)),
            "tag_free": None if taken is None else True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("next", "bump", "check"))
    parser.add_argument("--level", choices=("x", "y", "z"), default="z")
    parser.add_argument("--target", default="origin/main")
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--no-fetch", action="store_true", help="do not fetch the target first")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not args.no_fetch and "/" in args.target:
        remote, _, branch = args.target.partition("/")
        git(repo, "fetch", "--quiet", remote, branch)
    if args.command == "check":
        result = check(repo, args.target)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    base = target_version(repo, args.target)
    if base is None:
        print(json.dumps({"ok": False, "reason": f"{args.target} has a VERSION that is not X.Y.Z"}))
        return 1
    new = ".".join(map(str, step(base, args.level)))
    if args.command == "bump":
        (repo / "VERSION").write_text(new + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "version": new, "level": args.level, "target_version": ".".join(map(str, base))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
