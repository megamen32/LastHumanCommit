"""Exercise the canonical CLI against real Git repositories."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "src/common/tools/lhc_worktree.py"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "primary"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / ".gitignore").write_text(".worktrees/\n")
    git(root, "add", ".gitignore")
    git(root, "commit", "-m", "base")
    return root


def run(repo, action="plan", task="lane-one", base=None, ok=True):
    args = [sys.executable, str(TOOL), action, "--repo", str(repo), "--task=" + task]
    if base is not None:
        args.extend(["--base", base])
    result = subprocess.run(args, capture_output=True, text=True)
    if ok:
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    assert result.returncode != 0
    return result.stderr


def test_plan_read_only_and_auxiliary_identity(repo):
    before = git(repo, "status", "--porcelain")
    plan = run(repo)
    assert plan["primary"] == str(repo)
    assert plan["path"] == str(repo / ".worktrees/lane-one")
    assert plan["branch"] == "lhc/lane-one"
    assert not (repo / ".worktrees").exists()
    aux = repo / ".worktrees/aux"
    git(repo, "worktree", "add", "-b", "aux", str(aux))
    git(aux, "commit", "--allow-empty", "-m", "auxiliary advances")
    assert run(aux) == plan
    assert git(repo, "status", "--porcelain") == before


def test_create_reuse_after_commits_preserves_dirty_primary(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "foreign.txt").write_text("unrelated")
    first = run(repo, "create", base=base)
    lane = Path(first["path"])
    (lane / "result.txt").write_text("result")
    git(lane, "add", "result.txt")
    git(lane, "commit", "-m", "lane result")
    second = run(lane, "create", base=base)
    assert first["action"] == "created"
    assert second["action"] == "reused"
    assert git(repo, "branch", "--show-current") == "main"
    assert git(repo, "rev-parse", "HEAD") == base
    assert (repo / "foreign.txt").read_text() == "unrelated"
    assert "different base" in run(repo, "create", base="lhc/lane-one", ok=False)


@pytest.mark.parametrize("task", ["../escape", "UPPER", "a/b", "a--b", "-bad", "bad-"])
def test_invalid_slug(repo, task):
    assert "slug" in run(repo, task=task, ok=False)


def test_conflicting_path_or_branch(repo):
    target = repo / ".worktrees/lane-one"
    target.mkdir(parents=True)
    assert "occupied" in run(repo, "create", base="HEAD", ok=False)
    target.rmdir()
    git(repo, "branch", "lhc/lane-one")
    assert "branch" in run(repo, "create", base="HEAD", ok=False)


def test_requires_base_and_ignore_and_rejects_symlink(repo, tmp_path):
    assert "--base" in run(repo, "create", ok=False)
    (repo / ".gitignore").write_text("")
    assert "ignore" in run(repo, "create", base="HEAD", ok=False)
    (repo / ".gitignore").write_text(".worktrees/\n")
    (repo / ".worktrees").symlink_to(tmp_path, target_is_directory=True)
    assert "symlink" in run(repo, "create", base="HEAD", ok=False)


def test_does_not_adopt_foreign_worktree(repo):
    git(repo, "worktree", "add", "-b", "lhc/lane-one", str(repo / ".worktrees/lane-one"))
    assert "assignment" in run(repo, "create", base="HEAD", ok=False)


def test_primary_path_with_spaces_and_unicode(repo):
    moved = repo.with_name("primary space русский")
    repo.rename(moved)
    result = run(moved, "create", base="HEAD")
    assert result["primary"] == str(moved)
    assert run(Path(result["path"]))["path"] == result["path"]
