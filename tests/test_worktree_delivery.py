"""Regression: a local commit/worktree is not a published, reviewable task."""
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("delivery_worktree", ROOT / "src/common/tools/lhc_worktree.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.fixture
def task(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    main = tmp_path / "main"
    work = tmp_path / "task"
    def run(*args):
        subprocess.run(args, check=True, capture_output=True)
    run("git", "init", "--bare", str(origin))
    run("git", "init", "-b", "main", str(main))
    run("git", "-C", str(main), "config", "user.email", "test@example.invalid")
    run("git", "-C", str(main), "config", "user.name", "Test")
    (main / "one").write_text("one")
    run("git", "-C", str(main), "add", "one")
    run("git", "-C", str(main), "commit", "-m", "initial")
    run("git", "-C", str(main), "remote", "add", "origin", str(origin))
    run("git", "-C", str(main), "push", "origin", "main")
    run("git", "-C", str(main), "worktree", "add", "-b", "task/test", str(work))
    head = mod.git(work, "rev-parse", "HEAD")
    pr = {"headRefName": "task/test", "headRefOid": head, "baseRefName": "main",
          "url": "https://example.invalid/pull/1", "state": "OPEN", "isDraft": True}
    actual_run = subprocess.run
    real_git = mod.git
    def remote_git(repo, *args, **kwargs):
        if args == ("remote", "get-url", "origin"):
            return "git@github.com:example/project.git"
        return real_git(repo, *args, **kwargs)
    monkeypatch.setattr(mod, "git", remote_git)
    def mocked_run(argv, **kwargs):
        if argv[0] == "gh":
            assert argv[argv.index("--repo") + 1] == "github.com/example/project"
            return SimpleNamespace(returncode=0, stdout=json.dumps(pr), stderr="")
        return actual_run(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", mocked_run)
    return main, work, pr


def publish(work):
    mod.git(work, "push", "origin", "HEAD")


def test_unpushed_task_is_not_delivery(task):
    _, work, _ = task
    with pytest.raises(ValueError):
        mod.delivery(work, "main")


def test_target_branch_is_rejected(task):
    main, _, _ = task
    with pytest.raises(ValueError, match="task branch"):
        mod.delivery(main, "main")


def test_shared_primary_feature_branch_is_rejected(task):
    main, _, _ = task
    mod.git(main, "checkout", "-b", "feature/primary")
    with pytest.raises(ValueError, match="isolated"):
        mod.delivery(main, "main")


def test_dirty_task_is_not_delivery(task):
    _, work, _ = task
    publish(work)
    (work / "uncommitted").write_text("do not lose this")
    with pytest.raises(ValueError, match="commit"):
        mod.delivery(work, "main")
    assert (work / "uncommitted").read_text() == "do not lose this"


@pytest.mark.parametrize("key,value", [
    ("headRefOid", "0" * 40), ("headRefName", "other"),
    ("baseRefName", "other"), ("state", "CLOSED"), ("url", "")
])
def test_mismatched_pr_is_rejected(task, key, value):
    _, work, pr = task
    publish(work)
    pr[key] = value
    with pytest.raises(ValueError, match="PR must"):
        mod.delivery(work, "main")


def test_local_remote_tracking_ref_does_not_prove_push(task):
    _, work, _ = task
    publish(work)
    (work / "one").write_text("two")
    mod.git(work, "commit", "-am", "next")
    head = mod.git(work, "rev-parse", "HEAD")
    mod.git(work, "update-ref", "refs/remotes/origin/task/test", head)
    with pytest.raises(ValueError, match="not published"):
        mod.delivery(work, "main")


def test_exact_published_draft_is_review_not_merge_or_deploy(task):
    _, work, _ = task
    publish(work)
    result = mod.delivery(work, "main")
    assert result["status"] == "published_for_review"
    assert result["draft"] is True
    assert result["merge_authorized"] is False
    assert result["deployment_verified"] is False


def test_detached_head_is_rejected(task):
    _, work, _ = task
    mod.git(work, "checkout", "--detach")
    with pytest.raises(ValueError, match="task branch"):
        mod.delivery(work, "main")


def test_pushed_branch_without_pr_is_not_delivery(task, monkeypatch):
    _, work, _ = task
    publish(work)
    previous = mod.subprocess.run
    def missing_pr(argv, **kwargs):
        if argv[0] == "gh":
            return SimpleNamespace(returncode=1, stdout="", stderr="no pull requests found")
        return previous(argv, **kwargs)
    monkeypatch.setattr(mod.subprocess, "run", missing_pr)
    with pytest.raises(ValueError, match="draft PR"):
        mod.delivery(work, "main")


def test_ambient_gh_repo_cannot_redirect_pr_lookup(task, monkeypatch):
    _, work, _ = task
    publish(work)
    monkeypatch.setenv("GH_REPO", "unrelated/wrong-repo")
    assert mod.delivery(work, "main")["repository"] == "github.com/example/project"


def test_checkout_change_during_pr_lookup_is_rejected(task, monkeypatch):
    _, work, _ = task
    publish(work)
    previous = mod.subprocess.run
    def racing_run(argv, **kwargs):
        result = previous(argv, **kwargs)
        if argv[0] == "gh":
            (work / "concurrent").write_text("another writer")
        return result
    monkeypatch.setattr(mod.subprocess, "run", racing_run)
    with pytest.raises(ValueError, match="checkout changed"):
        mod.delivery(work, "main")
