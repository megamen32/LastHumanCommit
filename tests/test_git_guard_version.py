"""git stash ban, branch switching only in a worktree, and the one-counter version rule."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_git_guard as guard  # noqa: E402
import lhc_version as version  # noqa: E402


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run("git", "init", "-q", "-b", "main", cwd=repo)
    run("git", "config", "user.email", "t@example.com", cwd=repo)
    run("git", "config", "user.name", "t", cwd=repo)
    (repo / "a.txt").write_text("a")
    run("git", "add", "-A", cwd=repo)
    run("git", "commit", "-q", "-m", "first", cwd=repo)
    return repo


@pytest.mark.parametrize("command", [
    "git stash",
    "git stash push -m x",
    "git stash pop",
    "git -C /tmp/x stash",
    "git -c core.pager=cat stash list",
    "cd /tmp && git stash",
    "FOO=1 git stash apply",
    "sudo git stash",
    "echo ok && git stash drop",
    "sh -c 'git stash'",
    "bash -lc \"cd x && git stash\"",
    "git pull --autostash",
    "git rebase --autostash main",
    "git -c rebase.autoStash=true rebase main",
    "git -c merge.autostash=1 merge x",
    "/usr/bin/git stash",
])
def test_stash_is_banned_in_every_form(command, tmp_path):
    assert "banned" in guard.check(command, str(tmp_path))


@pytest.mark.parametrize("command", [
    "git status",
    "git commit -m 'do not git stash here'",
    "echo git stash",
    "git log --oneline",
    "git -c rebase.autoStash=false rebase main",
    "grep -r stash src",
    "git commit -am 'wip: parked'",
])
def test_other_commands_pass(command, tmp_path):
    assert guard.check(command, str(tmp_path)) is None


def test_the_primary_checkout_never_switches_branch(tmp_path):
    repo = make_repo(tmp_path)
    run("git", "branch", "other", cwd=repo)
    for command in ("git checkout other", "git checkout -b new", "git switch other", "git switch -c new",
                    "git checkout -B new main", "git -C " + str(repo) + " switch other"):
        assert "primary checkout" in guard.check(command, str(repo)), command
    assert "primary checkout" in guard.check("cd " + str(repo) + " && git switch other", str(tmp_path))
    # Not a branch switch: restoring a file, commits, status.
    for command in ("git checkout -- a.txt", "git checkout HEAD -- a.txt", "git status", "git commit -am x"):
        assert guard.check(command, str(repo)) is None, command


def test_a_linked_worktree_may_switch_branches(tmp_path):
    repo = make_repo(tmp_path)
    work = tmp_path / "wt"
    run("git", "worktree", "add", "-q", "-b", "task", str(work), cwd=repo)
    assert guard.is_primary_checkout(str(repo)) and not guard.is_primary_checkout(str(work))
    for command in ("git switch -c next main", "git checkout main", "git checkout -b more"):
        assert guard.check(command, str(work)) is None, command
    assert guard.check("git stash", str(work))  # the stash ban holds everywhere


def test_a_directory_that_is_not_a_repository_is_allowed():
    assert guard.check("git switch main", "/") is None


def entry(event, *extra):
    done = subprocess.run([sys.executable, str(ROOT / "src/common/tools/lhc_entry.py"), "--event", "PreToolUse",
                           "--git-guard", *extra], input=json.dumps(event), capture_output=True, text=True)
    return json.loads(done.stdout) if done.stdout.strip() else None


def test_the_entry_point_denies_in_the_native_hook_format(tmp_path):
    out = entry({"tool_name": "Bash", "tool_input": {"command": "git stash"}, "cwd": str(tmp_path)})
    assert out["decision"] == "block"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "banned" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert entry({"tool_name": "Read", "tool_input": {"command": "git stash"}, "cwd": str(tmp_path)}) is None
    assert entry({"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(tmp_path)}) is None
    assert entry({}) is None


@pytest.mark.parametrize("path", ["plugins/last-human-commit/hooks/hooks.json",
                                  "plugins/last-human-commit/hooks/zcode-hooks.json",
                                  "plugins/last-human-commit/com.openai/hooks/hooks.json",
                                  "plugins/last-human-commit/native/codex/hooks/hooks.json"])
def test_every_hook_file_runs_the_guard_on_bash(path):
    data = json.loads((ROOT / path).read_text())
    rows = data["hooks"]["PreToolUse"]
    assert rows[0]["matcher"] == "Bash"
    assert "--event PreToolUse --git-guard" in rows[0]["hooks"][0]["command"]


def test_the_opencode_plugin_blocks_through_the_same_guard():
    text = (ROOT / "plugins/last-human-commit/opencode/lhc-v2.ts").read_text()
    assert '"tool.execute.before"' in text and "--git-guard" in text and "throw new Error(reason)" in text


# ------------------------------------------------------------------ version counter


def make_remote(tmp_path, first="1.2.3"):
    remote = tmp_path / "remote.git"
    run("git", "init", "-q", "--bare", "-b", "main", str(remote), cwd=tmp_path)
    work = tmp_path / "work"
    run("git", "clone", "-q", str(remote), str(work), cwd=tmp_path)
    run("git", "config", "user.email", "t@example.com", cwd=work)
    run("git", "config", "user.name", "t", cwd=work)
    (work / "VERSION").write_text(first + "\n")
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-q", "-m", "v", cwd=work)
    run("git", "push", "-q", "origin", "main", cwd=work)
    return remote, work


def branch_with(work, name, text):
    run("git", "fetch", "-q", "origin", cwd=work)
    run("git", "checkout", "-q", "-B", name, "origin/main", cwd=work)
    (work / "VERSION").write_text(text + "\n")
    return version.check(work, "origin/main")


@pytest.mark.parametrize("new,ok", [("1.2.4", True), ("1.3.0", True), ("2.0.0", True),
                                    ("1.2.5", False), ("1.3.1", False), ("1.2.3", False), ("1.2", False)])
def test_version_must_be_exactly_one_step_above_the_target(tmp_path, new, ok):
    remote, work = make_remote(tmp_path)
    assert branch_with(work, "task", new)["ok"] is ok


def test_two_agents_bumping_from_the_same_base_cannot_both_land(tmp_path):
    remote, work = make_remote(tmp_path)
    assert branch_with(work, "first", "1.2.4")["ok"]
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-q", "-m", "first bump", cwd=work)
    run("git", "push", "-q", "origin", "first:main", cwd=work)       # the first agent lands
    second = branch_with(work, "second-old-base", "1.2.4")            # the second one bumped from the old base
    assert not second["ok"] and "rebase" in second["reason"]
    assert version.step(version.target_version(work, "origin/main"), "z") == (1, 2, 5)


def test_bump_writes_the_next_number_over_the_target(tmp_path):
    remote, work = make_remote(tmp_path)
    run("git", "checkout", "-q", "-b", "task", cwd=work)
    done = subprocess.run([sys.executable, str(ROOT / "src/common/tools/lhc_version.py"), "bump", "--level", "y",
                           "--repo", str(work)], capture_output=True, text=True)
    assert json.loads(done.stdout)["version"] == "1.3.0"
    assert (work / "VERSION").read_text().strip() == "1.3.0"
    assert version.check(work, "origin/main")["ok"]


def test_an_existing_tag_blocks_the_version(tmp_path):
    remote, work = make_remote(tmp_path)
    run("git", "tag", "v1.2.4", cwd=work)
    run("git", "push", "-q", "origin", "v1.2.4", cwd=work)
    assert "tag v1.2.4 already exists" in branch_with(work, "task", "1.2.4")["reason"]


def test_the_repeated_versions_agree_with_the_version_file():
    done = subprocess.run([sys.executable, str(ROOT / "scripts/sync_version.py"), "--check"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize("entry_path", ["plugins/last-human-commit/tools/lhc_entry.py",
                                        "plugins/last-human-commit/native/codex/tools/lhc_entry.py"])
def test_the_published_copies_refuse_stash_too(entry_path, tmp_path):
    """The guard fails open, so a copy that lacks the module would silently allow everything."""
    done = subprocess.run([sys.executable, str(ROOT / entry_path), "--event", "PreToolUse", "--git-guard"],
                          input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git stash"},
                                            "cwd": str(tmp_path)}), capture_output=True, text=True)
    assert json.loads(done.stdout)["decision"] == "block", done.stderr
    assert (ROOT / entry_path).with_name("lhc_git_guard.py").is_file()
