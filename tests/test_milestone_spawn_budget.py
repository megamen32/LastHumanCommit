"""The milestone observer must read the repository, not ask Git about it.

One observation used to spend several Git processes on the same repository:
the tracked list, the untracked list and HEAD, over and over for one render.
These cases hold two things at once:

* the **budget** - how many Git processes one observation may start, and
* the **answer** - a reused answer may never outlive the state it was
  computed for, so a file that appeared, vanished or changed, and a HEAD
  that moved, are all reported the moment they happen.
"""
import contextlib
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from _repos import head_of, prepared_repo


TOOLS = Path(__file__).resolve().parents[1] / "src" / "common" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import lhc_milestone as native  # noqa: E402  (the tools import each other by name)


GOAL = "Build a complete customer dashboard with search at https://demo.test/dashboard"

# The budget of one observation.  The repository facts the observer needs are
# facts about the working tree, and the observer reads them from the state
# Git already keeps on disk: the index, HEAD, the ignore rules and the
# config.  Nothing has to be started to learn them.
OBSERVATION_BUDGET = 0

# A repository with a commit has a HEAD to diff against, and that one answer
# is the only thing Git still has to say.
DIFF_BUDGET = 1


@contextlib.contextmanager
def git_processes():
    """Every Git process the code under test starts, in order."""
    started = []
    original = subprocess.run

    def counted(command, *args, **kwargs):
        if (isinstance(command, (list, tuple)) and command
                and os.path.basename(str(command[0])) == "git"):
            started.append([str(part) for part in command])
        return original(command, *args, **kwargs)

    subprocess.run = counted
    try:
        yield started
    finally:
        subprocess.run = original


def git(root, *args):
    """Git itself, for the answers the cases compare against."""
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    return result.stdout if result.returncode == 0 else b""


def repository(path, *, commit=False):
    """A Git checkout of its own, the way the observer meets one.

    The checkout is a copy of a prepared template: the same branch, the same
    identity and the same committed files a checkout built by hand would have
    had, without every case paying for the build again.
    """

    return prepared_repo(
        path,
        config=(("user.email", "observer@example.test"),
                ("user.name", "Observer")),
        files=(("page.html", "<main><button>Go</button></main>"),) if commit else (),
        message="first",
    )


def _unborn_repository(path):
    """A repository whose HEAD is unborn: no commit, so no revision.

    A special shape, used once per run: it is made the way ``git init``
    makes it, so the repository keeps the shape the cases expect of it.
    """

    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "observer@example.test")
    git(path, "config", "user.name", "Observer")
    return path


def observe(root, state, event, **fields):
    payload = {"cwd": str(root), "session_id": "observer", **fields}
    return native.observe(state, payload, event, root, "observer",
                          datetime.now().astimezone())


def _shapes(root):
    """Every shape of a repository the observer has to answer for."""

    main = repository(root / "main", commit=True)
    nested = main / "nested" / "deeper"
    nested.mkdir(parents=True)
    git(main, "worktree", "add", str(root / "linked"), "-b", "feature")
    git(main, "worktree", "add", "--detach", str(root / "detached"))
    separate = root / "separate"
    separate.mkdir()
    git(root, "init", "-q", "--separate-git-dir", str(root / "separate.git"), str(separate))
    bare = root / "bare.git"
    git(root, "init", "-q", "--bare", str(bare))
    unborn = _unborn_repository(root / "unborn")
    outside = root / "outside"
    outside.mkdir()
    return [("main", main), ("nested", nested), ("linked", root / "linked"),
            ("detached", root / "detached"), ("separate", separate), ("bare", bare),
            ("unborn", unborn), ("outside", outside)]


def _git_candidates(root):
    """The candidate paths Git lists for a directory."""

    paths = git(root, "ls-files", "-z").decode().split("\0")
    paths += git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    return sorted(path for path in paths if path)


def _candidates(answer):
    """The candidate paths of an answer of the observer."""

    return sorted(path for path in answer.decode().split("\0") if path)


def test_the_observer_asks_the_canon_for_the_repository(tmp_path):
    """The repository of the observer is the repository of the canon.

    The canon answers where a repository lives in one place, the reader of
    the layout.  The observer asks it, so the repository it works on is the
    one of the canon and not a copy that answers the same questions on its
    own.
    """

    root = repository(tmp_path / "repo", commit=True)

    found = native.discover(root)

    assert found is not None
    assert isinstance(found, native.layout.Repository)
    assert found.gitdir == (root / ".git").resolve()
    assert found.root == root.resolve()


def test_the_observer_follows_a_repointed_git_directory(tmp_path):
    """A lookup must never answer from the layout of an earlier call.

    The observer keeps nothing about the layout of a repository, so a
    directory that starts to point at another git directory is answered from
    the layout of the moment.
    """

    root = repository(tmp_path / "repo", commit=True)
    other = repository(tmp_path / "other", commit=True)
    before = native.discover(root)
    assert before is not None
    assert before.gitdir == (root / ".git").resolve()

    shutil.rmtree(root / ".git")
    (root / ".git").write_text(f"gitdir: {other / '.git'}\n", encoding="utf-8")

    after = native.discover(root)
    assert after is not None
    assert after.gitdir == (other / ".git").resolve()
    assert after.gitdir != before.gitdir


def test_the_answers_of_the_observer_are_the_answers_of_git(tmp_path):
    """Every shape of a repository answers exactly what Git answers."""

    for name, root in _shapes(tmp_path):
        assert native.git(root, "rev-parse", "--verify", "HEAD") == \
            git(root, "rev-parse", "--verify", "HEAD"), name
        assert native.git(root, "rev-parse", "--show-toplevel") == \
            git(root, "rev-parse", "--show-toplevel"), name
        answer = native.candidate_paths(root, "")
        if name == "bare":
            # A bare repository has no working tree, so Git answers it.
            assert answer is None, name
        else:
            assert answer is not None, name
            assert _candidates(answer) == _git_candidates(root), name


def test_one_observation_starts_no_git_process(tmp_path):
    """The facts about a repository are read from the repository itself."""
    root = repository(tmp_path / "repo")
    state = {}
    with git_processes() as started:
        milestone = observe(root, state, "UserPromptSubmit", prompt=GOAL)
    assert milestone is not None
    assert milestone["goal"] == GOAL
    assert started == []


def test_a_committed_repository_spends_only_the_one_answer_git_has_to_give(tmp_path):
    """Only the diff against a revision still needs Git, and only once."""
    root = repository(tmp_path / "repo", commit=True)
    head = head_of(root)
    state = {}
    with git_processes() as started:
        observe(root, state, "UserPromptSubmit", prompt=GOAL)
        assert len(started) <= DIFF_BUDGET
        before = len(started)
        observe(root, state, "PostToolUse", tool_name="exec_command",
                tool_input={"cmd": "write page"}, tool_response={"exit_code": 0})
        assert len(started) == before


def test_the_candidate_list_is_the_one_git_prints(tmp_path):
    """The answer the observer uses is Git's answer, byte for byte."""
    root = repository(tmp_path / "repo", commit=True)
    (root / "extra.js").write_text("document.body.appendChild(1);")
    (root / "notes.md").write_text("notes")
    wanted = [path for path in
              git(root, "ls-files", "-z").decode().split("\0") if path]
    wanted += [path for path in
               git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
               if path]
    raw = native.candidate_paths(root, "")
    assert sorted(path for path in raw.decode().split("\0") if path) == sorted(wanted)


def test_a_file_that_appears_is_reported_at_once(tmp_path):
    """A reused answer may not hide a file that appeared."""
    root = repository(tmp_path / "repo")
    assert "late.html" not in native.candidates(root, "")
    (root / "late.html").write_text("<main>late</main>")
    assert "late.html" in native.candidates(root, "")


def test_a_changed_working_tree_is_not_served_from_the_cache(tmp_path):
    """The diff against a revision may not outlive the working tree."""
    root = repository(tmp_path / "repo", commit=True)
    head = head_of(root)
    assert native.candidates(root, head) == []
    (root / "page.html").write_text("<main><button>Changed</button></main>")
    assert "page.html" in native.candidates(root, head)


def test_a_file_that_disappears_is_reported_at_once(tmp_path):
    """A file that vanished is gone from the listing, at once."""
    root = repository(tmp_path / "repo", commit=True)
    head = head_of(root)
    (root / "temp.html").write_text("<main>temporary</main>")
    assert "temp.html" in native.candidates(root, head)
    os.remove(root / "temp.html")
    assert "temp.html" not in native.candidates(root, head)


def test_a_deleted_tracked_file_is_a_change(tmp_path):
    """A tracked file that vanished shows up in the diff, at once."""
    root = repository(tmp_path / "repo", commit=True)
    head = head_of(root)
    assert native.candidates(root, head) == []
    os.remove(root / "page.html")
    assert "page.html" in native.candidates(root, head)


def test_a_moved_head_is_not_served_from_the_cache(tmp_path):
    """A HEAD that moved is a different revision, with a different answer."""
    root = repository(tmp_path / "repo", commit=True)
    old = head_of(root)
    (root / "second.html").write_text("<main>second</main>")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "second")
    new = head_of(root)
    assert native.candidates(root, old) != native.candidates(root, new)
    assert "second.html" in native.candidates(root, old)
    assert "second.html" not in native.candidates(root, new)


def test_the_head_of_the_repository_is_gits_own_answer(tmp_path):
    """The revision the observer records is the revision Git reports."""
    root = repository(tmp_path / "repo", commit=True)
    assert native.git(root, "rev-parse", "--verify", "HEAD").decode().strip() == head_of(root)


def test_an_unborn_head_is_gits_own_answer(tmp_path):
    """A repository without a commit has no revision, and Git says so."""
    root = repository(tmp_path / "repo")
    assert native.git(root, "rev-parse", "--verify", "HEAD") == b""
    assert native.git(root, "rev-parse", "--verify", "HEAD") == git(root, "rev-parse", "--verify", "HEAD")


def test_the_remote_url_is_gits_own_answer(tmp_path):
    """The remote the observer reads is the remote Git reports."""
    root = repository(tmp_path / "repo")
    git(root, "remote", "add", "origin", "git@github.com:owner/project.git")
    assert native.git(root, "remote", "get-url", "origin") == git(root, "remote", "get-url", "origin")
    assert native.git(root, "remote", "get-url", "origin").decode().strip() == "git@github.com:owner/project.git"


def test_a_changed_remote_url_is_not_served_from_the_cache(tmp_path):
    """A remote that moved has to be read again."""
    root = repository(tmp_path / "repo")
    git(root, "remote", "add", "origin", "git@github.com:owner/project.git")
    assert native.git(root, "remote", "get-url", "origin").decode().strip() == "git@github.com:owner/project.git"
    git(root, "remote", "set-url", "origin", "git@github.com:owner/other.git")
    assert native.git(root, "remote", "get-url", "origin").decode().strip() == "git@github.com:owner/other.git"


def test_a_repository_that_git_cannot_read_is_answered_by_git(tmp_path):
    """An unusual repository falls back to Git instead of guessing."""
    root = repository(tmp_path / "repo", commit=True)
    head = head_of(root)
    wanted = [path for path in git(root, "diff", "--name-only", "-z", head).decode().split("\0") if path]
    assert sorted(native.candidates(root, head)) == sorted(wanted)


def test_the_ignore_rules_are_read_the_way_git_reads_them(tmp_path):
    """A pattern of a subdirectory is relative to that subdirectory."""
    root = repository(tmp_path / "repo")
    (root / ".gitignore").write_text("*.log\n")
    (root / "sub").mkdir()
    (root / "sub" / ".gitignore").write_text("/anchored.txt\n!keep.txt\n")
    (root / "top.log").write_text("1")
    (root / "sub" / "anchored.txt").write_text("2")
    (root / "sub" / "keep.txt").write_text("3")
    (root / "sub" / "free.txt").write_text("4")
    wanted = [path for path in
              git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
              if path]
    raw = native.candidate_paths(root, "")
    assert sorted(path for path in raw.decode().split("\0") if path) == sorted(wanted)
