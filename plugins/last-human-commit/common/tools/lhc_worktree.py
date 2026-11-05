#!/usr/bin/env python3
"""Plan or create one Git-native, canonical LHC worktree assignment."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
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


def configured_pr_stage() -> str:
    """Read existing user LHC config first, then built package, then PR-on.

    Existing LHC preferences are under ~/.config/lhc; PR-off on one user's
    installation should not change the default mode of all marketplace users.
    Both common/tools and tools facades support the same package layout.
    """
    parent = Path(__file__).resolve().parent.parent
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    user_config = config_home / "lhc/workflow.json"
    bases = (parent.parent, parent) if parent.name == "common" else (parent, parent / "common")
    for path in [user_config, *(base / "config/workflow.json" for base in bases)]:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("invalid workflow config") from exc
            stage = data.get("pr_stage", "on") if isinstance(data, dict) else None
            if stage not in ("on", "off"):
                raise ValueError("pr_stage must be on or off")
            return stage
    return "on"


def delivery(repo: Path, target: str, remote: str = "origin", *, pr_stage: str | None = None) -> dict:
    """Verify a task is committed, remotely published and (if configured) in a PR.

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
    published = git(repo, "ls-remote", "--exit-code", remote, "refs/heads/" + branch, check=False)
    if published.split() != [head, "refs/heads/" + branch]:
        raise ValueError("task HEAD is not published on the remote branch")
    repository = pr_repository(repo, remote)
    stage = pr_stage if pr_stage is not None else configured_pr_stage()
    if stage not in ("on", "off"):
        raise ValueError("pr_stage must be on or off")
    if stage == "off":
        # A PR-free publication is a handoff to review/integration, never a
        # bypass of host branch protection or permission to deploy.
        target_ref = "refs/heads/" + target
        remote_target = git(repo, "ls-remote", "--exit-code", remote, target_ref, check=False)
        if not remote_target or git(repo, "rev-parse", "HEAD") != head or git(repo, "status", "--porcelain"):
            raise ValueError("checkout or target changed while collecting publication evidence")
        return {"branch": branch, "head": head, "remote": remote,
                "repository": repository, "target": target,
                "pr_stage": "off", "pr_required": False,
                "status": "published_without_pr", "integration_required": True,
                "merge_authorized": False, "deployment_verified": False}
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
            "pr_stage": "on", "pr_required": True, "integration_required": True,
            "pr_url": pr["url"], "draft": pr.get("isDraft") is True,
            "status": "published_for_review", "pr_marked_ready": pr.get("isDraft") is False,
            "merge_authorized": False,
            "deployment_verified": False}


def inventory(repo: Path, target: str) -> dict:
    """Read-only Git facts; callers must establish session ownership separately."""
    target_head = git(repo, "rev-parse", "--verify", "--end-of-options", target + "^{commit}")
    entries = []
    for record in worktrees(repo):
        path = Path(record["worktree"])
        entry = {"path": str(path), "branch": record.get("branch"),
                 "head": record.get("HEAD"), "locked": "locked" in record,
                 "prunable": "prunable" in record, "activity": "unknown",
                 "cleanup_authorized": False}
        try:
            if "bare" in record or "prunable" in record or not path.exists():
                raise ValueError("worktree unavailable")
            head = git(path, "rev-parse", "HEAD")
            entry.update(head=head, primary=absolute_git_dir(path) == common_dir(repo),
                         dirty=bool(git(path, "status", "--porcelain")),
                         conflicted=bool(git(path, "ls-files", "--unmerged")))
            check = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                                    head, target_head], capture_output=True, text=True)
            if check.returncode not in (0, 1):
                raise ValueError(check.stderr.strip() or "ancestry check failed")
            entry["merged"] = check.returncode == 0
            entry["head_unchanged"] = git(path, "rev-parse", "HEAD") == head
        except (ValueError, OSError) as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return {"common_dir": str(common_dir(repo)), "target": target,
            "target_head": target_head, "worktrees": entries,
            "read_only": True, "cleanup_authorized": False}


GUARD_REF = "refs/lhc/release/"
GUARD_TTL = 15 * 60  # seconds a fallback lease lives without a renewal
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbbdb904"


def _sibling(name: str):
    """A neighbouring LHC tool, imported by name or loaded from next to this file."""
    try:
        return importlib.import_module(name)
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_sibling", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"{name} is not next to lhc_worktree.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _guard_ref(project: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project or ""):
        raise ValueError("release-guard needs --project made of letters, digits, '.', '_' or '-'")
    return GUARD_REF + project


def _guard_read(repo: Path, remote: str, ref: str) -> tuple[str, dict]:
    """The commit the lease ref points at on the remote, and the JSON it carries."""
    out = git(repo, "ls-remote", remote, ref)
    sha = out.split()[0] if out else ""
    if not sha:
        return "", {}
    git(repo, "fetch", "--quiet", remote, ref)
    try:
        data = json.loads(git(repo, "show", "-s", "--format=%B", sha))
    except ValueError:
        data = {}
    return sha, data if isinstance(data, dict) else {}


def _guard_push(repo: Path, remote: str, ref: str, expected: str, source: str) -> str:
    """Atomic compare-and-swap of the lease ref; an empty expected value means 'must not exist'."""
    result = subprocess.run(
        ["git", "-C", str(repo), "push", "--quiet", f"--force-with-lease={ref}:{expected}", remote, f"{source}:{ref}"],
        capture_output=True, text=True)
    return "" if result.returncode == 0 else (result.stderr.strip() or "push refused")


def _expired(data: dict, now: float) -> bool:
    try:
        return float(data.get("expires", 0)) <= now
    except (TypeError, ValueError):
        return True


def guard_acquire(repo: Path, project: str, session: str, candidate: str, host: str = "",
                  remote: str = "origin", ttl: int = GUARD_TTL, now: float | None = None) -> dict:
    """Take or renew the fallback release lease (Herder unavailable): a git ref on the remote.

    A live lease of another session stops the caller; an expired one is taken by the same CAS.
    """
    import time
    now = time.time() if now is None else now
    ref = _guard_ref(project)
    if not session:
        raise ValueError("release-guard needs --session")
    sha, data = _guard_read(repo, remote, ref)
    if data.get("session") != session and sha and not _expired(data, now):
        return {"ok": False, "action": "acquire", "ref": ref, "reason": "foreign lease",
                "owner": data.get("session"), "remaining_seconds": int(float(data.get("expires", 0)) - now)}
    payload = {"session": session, "host": host, "candidate": candidate, "expires": int(now + ttl)}
    env = {**os.environ, "GIT_AUTHOR_NAME": "lhc", "GIT_AUTHOR_EMAIL": "lhc@localhost",
           "GIT_COMMITTER_NAME": "lhc", "GIT_COMMITTER_EMAIL": "lhc@localhost"}
    tree = subprocess.run(["git", "-C", str(repo), "mktree"], input="", capture_output=True, text=True).stdout.strip()
    made = subprocess.run(["git", "-C", str(repo), "commit-tree", tree or EMPTY_TREE, "-m", json.dumps(payload, sort_keys=True)],
                          capture_output=True, text=True, env=env)
    if made.returncode:
        raise ValueError(made.stderr.strip() or "cannot create the lease commit")
    commit = made.stdout.strip()
    error = _guard_push(repo, remote, ref, sha, commit)
    if error:
        return {"ok": False, "action": "acquire", "ref": ref, "reason": "lost the compare-and-swap: " + error}
    return {"ok": True, "action": "acquire", "ref": ref, "commit": commit, "expires": payload["expires"],
            "took_over_expired": bool(sha and data.get("session") != session)}


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """lhc_git_facts.is_ancestor; the git binary answers when the facts reader cannot."""
    try:
        facts = _sibling("lhc_git_facts")
        found = facts.discover(repo)
        answer = facts.is_ancestor(found, ancestor, descendant) if found is not None else None
    except Exception:  # noqa: BLE001 - the git binary is the fallback
        answer = None
    if answer is None:
        answer = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
                                capture_output=True).returncode == 0
    return answer is True


def _version(text: str) -> tuple:
    try:
        return tuple(int(part) for part in text.strip().split("."))
    except ValueError:
        return ()


def guard_check(repo: Path, project: str, session: str, candidate: str, live: str, expected: str = "",
                target: str = "main", remote: str = "origin", now: float | None = None) -> dict:
    """The checks made in code immediately before a release that runs under the fallback lease."""
    import time
    now = time.time() if now is None else now
    ref = _guard_ref(project)
    checks: dict[str, bool] = {}
    sha, data = _guard_read(repo, remote, ref)
    checks["own_unexpired_lease"] = bool(sha) and data.get("session") == session and not _expired(data, now) \
        and data.get("candidate") == candidate
    cand = git(repo, "rev-parse", "--verify", candidate + "^{commit}", check=False)
    live_sha = git(repo, "rev-parse", "--verify", live + "^{commit}", check=False) if live else ""
    git(repo, "fetch", "--quiet", remote, target, check=False)
    tip = git(repo, "rev-parse", "--verify", f"{remote}/{target}^{{commit}}", check=False)
    checks["candidate_in_origin_main"] = bool(cand and tip) and _is_ancestor(repo, cand, tip)
    checks["live_is_ancestor_of_candidate"] = bool(cand and live_sha) and _is_ancestor(repo, live_sha, cand)
    checks["expected_revision_matches_live"] = bool(live_sha) and bool(expected) \
        and git(repo, "rev-parse", "--verify", expected + "^{commit}", check=False) == live_sha
    new_v = _version(git(repo, "show", f"{cand}:VERSION", check=False)) if cand else ()
    old_v = _version(git(repo, "show", f"{live_sha}:VERSION", check=False)) if live_sha else ()
    checks["version_is_greater_than_live"] = bool(new_v and old_v) and new_v > old_v
    dirty = [line for line in git(repo, "status", "--porcelain", check=False).splitlines()
             if not line.startswith("?? .agents/mail")]
    checks["worktree_clean"] = not dirty
    return {"ok": all(checks.values()), "action": "check", "ref": ref, "checks": checks}


def guard_release(repo: Path, project: str, session: str, remote: str = "origin") -> dict:
    """Free the fallback lease: delete the ref by CAS, and only when this session holds it."""
    ref = _guard_ref(project)
    sha, data = _guard_read(repo, remote, ref)
    if not sha:
        return {"ok": True, "action": "release", "ref": ref, "released": False, "note": "no lease"}
    if data.get("session") != session:
        return {"ok": False, "action": "release", "ref": ref, "reason": "foreign lease", "owner": data.get("session")}
    error = _guard_push(repo, remote, ref, sha, "")
    return ({"ok": False, "action": "release", "ref": ref, "reason": error} if error
            else {"ok": True, "action": "release", "ref": ref, "released": True})


def guard_journal(repo: Path, plan: Path | None, session: str, result: dict, project: str) -> None:
    """Leave the herder-bypass trace: a revisions entry in the plan and a result mail to the DISPATCHER."""
    from datetime import datetime, timezone
    text = f"herder-bypass: release-guard {result.get('action')} project={project} ok={result.get('ok')} ref={result.get('ref')}"
    try:
        if plan is not None and (plan / "plan.json").is_file():
            data = json.loads((plan / "plan.json").read_text(encoding="utf-8"))
            data.setdefault("revisions", []).append(
                {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reason": "herder-bypass", "summary": text})
            tmp = plan / "plan.json.tmp"
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, plan / "plan.json")
    except (OSError, ValueError):
        pass
    try:
        mail = _sibling("lhc_mail")
        mail.send(mail.primary_root(repo), "DISPATCHER", session or "release-guard", "result", text)
    except Exception:  # noqa: BLE001 - the journal never blocks a release decision
        pass


def release_guard_cli(args) -> dict:
    import socket
    repo = args.repo
    project = args.project or Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent.name
    candidate = args.candidate or git(repo, "rev-parse", "HEAD")
    if args.guard_action == "acquire":
        result = guard_acquire(repo, project, args.session, candidate, args.host or socket.gethostname(), args.remote, args.ttl)
    elif args.guard_action == "check":
        result = guard_check(repo, project, args.session, candidate, args.live_rev or "", args.expected_rev or "",
                             args.target, args.remote)
    elif args.guard_action == "release":
        result = guard_release(repo, project, args.session, args.remote)
    else:
        raise ValueError("release-guard needs acquire, check or release")
    if result.get("ok"):
        guard_journal(repo, args.plan, args.session, result, project)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "create", "delivery", "inventory", "release-guard"))
    parser.add_argument("guard_action", nargs="?", choices=("acquire", "check", "release"),
                        help="release-guard: the fallback release lease (a git ref) used when Herder is unavailable")
    parser.add_argument("--project", help="release-guard: project name of the lease ref (default: primary checkout name)")
    parser.add_argument("--session", default="", help="release-guard: this session's id")
    parser.add_argument("--host", default="")
    parser.add_argument("--candidate", help="release-guard: candidate commit (default HEAD)")
    parser.add_argument("--live-rev", help="release-guard check: the live revision just re-read")
    parser.add_argument("--expected-rev", help="release-guard check: the revision the release entrypoint expects")
    parser.add_argument("--ttl", type=int, default=GUARD_TTL)
    parser.add_argument("--plan", type=Path, help="release-guard: plan directory that gets the herder-bypass revision")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task")
    parser.add_argument("--target", default="main", help="PR integration target for delivery")
    parser.add_argument("--remote", default="origin", help="remote to verify for delivery")
    parser.add_argument("--pr-stage", choices=("on", "off"), help="override the built package PR stage for this check")
    parser.add_argument("--base", help="resolve from primary checkout; required for create")
    args = parser.parse_args()
    try:
        if args.action == "release-guard":
            result = release_guard_cli(args)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            raise SystemExit(0 if result.get("ok") else 1)
        if args.action == "inventory":
            result = inventory(args.repo, args.target)
        elif args.action == "delivery":
            result = delivery(args.repo, args.target, args.remote, pr_stage=args.pr_stage)
        else:
            if not args.task:
                raise ValueError("--task is required for plan/create")
            result = assignment(args.repo, args.task, args.base, args.action == "create")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
