#!/usr/bin/env python3
"""Plan or create one Git-native, canonical LHC worktree assignment."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


_GIT_LAYOUT = None
_GIT_LAYOUT_LOADED = False


def git_layout():
    """The reader of the layout of a repository, loaded from next to this file.

    The tool is loaded by path in the tests and as a neighbour in the package,
    so the neighbour cannot be found by a plain import in every environment.
    ``None`` means the neighbour is not there at all; every question is then
    answered by the git binary, the way it was answered before the reader
    existed.
    """
    global _GIT_LAYOUT, _GIT_LAYOUT_LOADED
    if not _GIT_LAYOUT_LOADED:
        _GIT_LAYOUT = _load_git_layout()
        _GIT_LAYOUT_LOADED = True
    return _GIT_LAYOUT


def _load_git_layout():
    """Load the reader of the layout of a repository from next to this file."""

    try:
        import lhc_gitlayout

        return lhc_gitlayout
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name("lhc_gitlayout.py")
    try:
        spec = importlib.util.spec_from_file_location("lhc_gitlayout_sibling", path)
        if spec is None or spec.loader is None:
            return None
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - a missing reader is answered by git
        sys.modules.pop("lhc_gitlayout_sibling", None)
        return None


def common_dir(repo: Path) -> Path:
    """The shared git directory of the repository that owns a checkout.

    The answer is a fact about the directories on the disk, so it is read from
    there.  A layout the reader does not model is answered by the git binary,
    so an unusual repository keeps the answer it has today.
    """
    layout = git_layout()
    answer = layout.common_dir_of(repo) if layout is not None else None
    if answer is None:
        answer = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return answer.resolve()


def absolute_git_dir(candidate: Path) -> Path:
    """The git directory of one checkout, read from the disk.

    The git directory of a linked worktree is the one next to the shared one,
    not the shared one itself.
    """
    layout = git_layout()
    answer = layout.absolute_git_dir(candidate) if layout is not None else None
    if answer is None:
        answer = Path(git(candidate, "rev-parse", "--absolute-git-dir"))
    return answer.resolve()


def worktrees(repo: Path) -> list[dict[str, str]]:
    # The listing is read from the disk.  The git binary is asked only for a
    # layout the reader does not model; older supported Git versions lack
    # worktree list -z, and core.quotePath=false keeps ordinary Unicode
    # literal in that answer.
    listing = None
    layout = git_layout()
    if layout is not None:
        common = layout.common_dir_of(repo)
        if common is not None:
            listing = layout.worktree_list_porcelain(common)
    if listing is None:
        listing = git(repo, "-c", "core.quotePath=false", "worktree", "list", "--porcelain")
    records = []
    record = {}
    for field in (listing.strip() + "\n\n").splitlines():
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


def assignment(repo: Path, task: str, base_ref: str | None, create: bool) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", task):
        raise ValueError("task slug must contain lowercase letters/digits separated by single hyphens")
    common = common_dir(repo)
    records = worktrees(repo)
    primary = None
    for entry in records:
        candidate = Path(entry["worktree"])
        if "bare" in entry or "prunable" in entry or not candidate.exists():
            continue
        git_dir = absolute_git_dir(candidate)
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
    result = dict(primary=str(primary), common_dir=str(common), branch=branch,
                  path=str(target), base=base, action="plan")
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
    parent.mkdir(exist_ok=True)
    git(primary, "worktree", "add", "-b", branch, str(target), base)
    git(primary, "config", key, base)
    result["action"] = "created"
    return result


def pr_repository(repo: Path, remote: str) -> str:
    """Bind gh to the selected remote, not GH_REPO or an ambient default."""
    url = git(repo, "remote", "get-url", remote)
    if "://" not in url:
        match = re.fullmatch(r"(?:[^@/:]+@)?([^/:]+):([^?#]+)", url)
        if not match:
            raise ValueError("delivery requires a supported GitHub remote URL")
        host, path = match.groups()
    else:
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "ssh") or parsed.query or parsed.fragment:
            raise ValueError("delivery requires a supported GitHub remote URL")
        host, path = parsed.hostname or "", parsed.path.lstrip("/")
    path = path.removesuffix(".git").rstrip("/")
    if not host or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
        raise ValueError("delivery requires an owner/repository remote")
    return host + "/" + path


def delivery(repo: Path, target: str, remote: str = "origin") -> dict:
    """Verify a task is committed, remotely published and represented by a PR.

    Read-only. A green receipt is not merge/deploy authorization and does not
    replace the project release lease immediately before a runtime mutation.
    """
    branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not branch or branch == target:
        raise ValueError("delivery requires a task branch, not detached HEAD or the target branch")
    if absolute_git_dir(repo) == common_dir(repo):
        raise ValueError("delivery requires an isolated task worktree")
    if git(repo, "status", "--porcelain"):
        raise ValueError("commit scoped changes and preserve foreign work before delivery")
    head = git(repo, "rev-parse", "HEAD")
    # Query the remote itself: a local remote-tracking ref is not push evidence.
    published = git(repo, "ls-remote", "--exit-code", remote, "refs/heads/" + branch)
    if published.split() != [head, "refs/heads/" + branch]:
        raise ValueError("task HEAD is not published on the remote branch")
    repository = pr_repository(repo, remote)
    result = subprocess.run(
        ["gh", "pr", "view", branch, "--repo", repository, "--json",
         "headRefName,headRefOid,baseRefName,url,state,isDraft"],
        cwd=repo, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise ValueError("open a draft PR for the published task branch before delivery")
    try:
        pr = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid PR evidence") from exc
    if (not isinstance(pr, dict) or pr.get("headRefName") != branch
            or pr.get("headRefOid") != head or pr.get("baseRefName") != target
            or pr.get("state") != "OPEN" or not pr.get("url")):
        raise ValueError("PR must be open and match the exact task HEAD and target")
    if git(repo, "rev-parse", "HEAD") != head or git(repo, "status", "--porcelain"):
        raise ValueError("checkout changed while collecting publication evidence")
    return {"branch": branch, "head": head, "remote": remote,
            "repository": repository, "target": target,
            "pr_url": pr["url"], "draft": pr.get("isDraft") is True,
            "status": "published_for_review", "merge_authorized": False,
            "deployment_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "create", "delivery"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task")
    parser.add_argument("--target", default="main", help="PR integration target for delivery")
    parser.add_argument("--remote", default="origin", help="remote to verify for delivery")
    parser.add_argument("--base", help="resolve from primary checkout; required for create")
    args = parser.parse_args()
    try:
        if args.action == "delivery":
            result = delivery(args.repo, args.target, args.remote)
        else:
            if not args.task:
                raise ValueError("--task is required for plan/create")
            result = assignment(args.repo, args.task, args.base, args.action == "create")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
