#!/usr/bin/env python3
"""Plan or create one Git-native, canonical LHC worktree assignment."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def worktrees(repo: Path) -> list[dict[str, str]]:
    # Older supported Git versions lack worktree list -z. Git C-quotes
    # unusual paths; core.quotePath=false keeps ordinary Unicode literal.
    records = []
    record = {}
    for field in (git(repo, "-c", "core.quotePath=false", "worktree", "list", "--porcelain") + "\n\n").splitlines():
        if not field:
            if record:
                records.append(record)
                record = {}
        else:
            key, _, value = field.partition(" ")
            if key == "worktree" and value.startswith('"'):
                value = ast.literal_eval(value)
            record[key] = value
    return records


def assignment(
    repo: Path,
    task: str,
    base_ref: str | None,
    create: bool,
    preserve_dirty_primary: bool = False,
    dirty_primary_reason: str | None = None,
) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", task):
        raise ValueError("task slug must contain lowercase letters/digits separated by single hyphens")
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    records = worktrees(repo)
    primary = None
    for entry in records:
        candidate = Path(entry["worktree"])
        if "bare" in entry or "prunable" in entry or not candidate.exists():
            continue
        git_dir = Path(git(candidate, "rev-parse", "--absolute-git-dir")).resolve()
        if git_dir == common:
            primary = candidate.resolve()
            break
    if primary is None:
        raise ValueError("no primary working checkout found in Git worktree metadata")
    if create and base_ref is None:
        raise ValueError("create requires --base (a commit or ref)")
    base = git(primary, "rev-parse", "--verify", "--end-of-options", (base_ref or "HEAD") + "^{commit}")
    branch = "lhc/" + task
    parent = primary / ".worktrees"
    target = parent / task
    if parent.is_symlink() or target.is_symlink() or target.resolve() != target:
        raise ValueError("canonical worktree path must not escape through a symlink")
    # Inspect both the index and working tree, including untracked WIP.
    # Git's ignored worktree directory is not foreign WIP.
    dirty_primary = bool(git(primary, "status", "--porcelain=v1", "--untracked-files=normal"))
    result = dict(primary=str(primary), common_dir=str(common), branch=branch,
                  path=str(target), base=base, action="plan", dirty_primary=dirty_primary)
    if not create:
        return result
    ignored = subprocess.run(
        ["git", "-C", str(primary), "check-ignore", "-q", "--", str(parent) + "/"],
        capture_output=True,
    )
    if ignored.returncode:
        raise ValueError("primary checkout must ignore .worktrees/ before create")
    existing = next((r for r in records if Path(r["worktree"]).resolve() == target), None)
    key = "branch." + branch + ".lhc-base"
    if existing is not None:
        if existing.get("branch") != "refs/heads/" + branch or "prunable" in existing:
            raise ValueError("canonical path is occupied by a different worktree")
        recorded = git(primary, "config", "--get", key, check=False)
        if not recorded:
            raise ValueError("existing worktree has no LHC assignment; refusing adoption")
        if recorded != base:
            raise ValueError("existing assignment has a different base")
        result["action"] = "reused"
        return result
    if target.exists():
        raise ValueError("canonical path is occupied; refusing adoption")
    if git(primary, "show-ref", "--verify", "refs/heads/" + branch, check=False):
        raise ValueError("branch already exists outside this assignment")
    if dirty_primary_reason and not preserve_dirty_primary:
        raise ValueError("dirty-primary override reason requires --preserve-dirty-primary")
    if dirty_primary:
        if not preserve_dirty_primary:
            raise ValueError(
                "dirty primary checkout: attribute and preserve existing WIP "
                "before creating a Full-cycle worktree; active foreign owners "
                "must remain untouched (use explicit preserve override with reason)"
            )
        if not dirty_primary_reason or len(dirty_primary_reason.strip()) < 12:
            raise ValueError(
                "dirty primary preserve override requires --dirty-primary-reason "
                "recording the independently verified WIP owner/condition"
            )
        # A reason is a caller assertion, not verified ownership. Never reset,
        # stash or modify the primary; the lead must preserve evidence separately.
        result["dirty_primary_preserved"] = True
        result["dirty_primary_reason"] = dirty_primary_reason.strip()
        result["ownership_verification"] = "caller_attested_not_verified"
    elif preserve_dirty_primary or dirty_primary_reason:
        raise ValueError("dirty-primary override is only valid for a dirty primary")
    parent.mkdir(exist_ok=True)
    git(primary, "worktree", "add", "-b", branch, str(target), base)
    git(primary, "config", key, base)
    result["action"] = "created"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "create"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--base", help="resolve from primary checkout; required for create")
    parser.add_argument(
        "--preserve-dirty-primary", action="store_true",
        help="explicit isolation of verified active/owned WIP; never cleans primary",
    )
    parser.add_argument(
        "--dirty-primary-reason",
        help="record separately verified owner/condition; not a proof of attribution",
    )
    args = parser.parse_args()
    try:
        result = assignment(
            args.repo, args.task, args.base, args.action == "create",
            args.preserve_dirty_primary, args.dirty_primary_reason,
        )
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
