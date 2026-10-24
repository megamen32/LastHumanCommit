#!/usr/bin/env python3
"""Budget tests for the git process spawns of the persistent time guard.

The time guard resolves the owner of the learning state from the repository
layout.  That resolution used to start two git processes for every lookup,
which made the guard the largest source of git spawns under the test suite.
The answers are filesystem facts, so the guard reads them from disk.

These tests hold three properties of that change:

* the lookup starts no git process at all,
* the lookup answers exactly what git answers, for a plain repository and for
  a linked worktree, and
* the lookup never answers from a stale value: the answer follows the
  repository layout of the moment, not the layout of an earlier call.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_time_guard.py"
SPEC = importlib.util.spec_from_file_location("lhc_time_guard_spawn_budget", TOOL)
assert SPEC is not None and SPEC.loader is not None
TIME_GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TIME_GUARD)

# Measured after the change: one learning-state lookup starts no git process.
GIT_SPAWN_BUDGET = 0

# Measured after the change: the snapshot needs git for the head and for the
# changed paths, the work tree and the branch come from the disk.
GIT_SNAPSHOT_SPAWN_BUDGET = 2

RUNTIME = "codex"
SESSION_ID = "spawn-budget"


def _git(*arguments: str, cwd: Path | None = None) -> str:
    """Run one git command and return its output."""

    completed = subprocess.run(
        ["git", *arguments],
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _digest(runtime: str = RUNTIME, session_id: str = SESSION_ID) -> str:
    """Reproduce the digest the guard uses for the learning-state file name."""

    return hashlib.sha256(f"{runtime}\0{session_id}".encode()).hexdigest()


def _expected_learning_path(cwd: Path, runtime: str = RUNTIME,
                            session_id: str = SESSION_ID) -> Path:
    """Resolve the learning-state path the way git itself resolves it."""

    common = _git("-C", str(cwd), "rev-parse", "--path-format=absolute",
                  "--git-common-dir").strip()
    worktrees = _git("--git-dir", common, "worktree", "list", "--porcelain").splitlines()
    primary = next(line.removeprefix("worktree ") for line in worktrees
                   if line.startswith("worktree "))
    return Path(primary) / ".agents" / "shared-session" / "learning" / f"{_digest(runtime, session_id)}.json"


@pytest.fixture
def git_spawns(monkeypatch) -> list[list[str]]:
    """Record every git process the code under test starts."""

    started: list[list[str]] = []
    original = subprocess.run

    def counting_run(arguments, *positional, **keywords):
        if isinstance(arguments, (list, tuple)) and arguments:
            first = arguments[0]
            if isinstance(first, str) and Path(first).name == "git":
                started.append([str(value) for value in arguments])
        return original(arguments, *positional, **keywords)

    monkeypatch.setattr(subprocess, "run", counting_run)
    return started


def _repository(root: Path, name: str) -> Path:
    """Create one plain repository with a committed head."""

    repository = root / name
    repository.mkdir(parents=True)
    _git("init", "-q", str(repository))
    _git("-C", str(repository), "config", "user.name", "Fixture")
    _git("-C", str(repository), "config", "user.email", "fixture@example.test")
    (repository / "owned.py").write_text("value = 1\n", encoding="utf-8")
    _git("-C", str(repository), "add", "-A")
    _git("-C", str(repository), "commit", "-qm", "fixture")
    return repository


def _remove_git_directory(repository: Path) -> None:
    """Remove the git directory of a repository, file or directory alike."""

    git_directory = repository / ".git"
    if git_directory.is_dir():
        shutil.rmtree(git_directory)
    else:
        git_directory.unlink()


def test_learning_path_of_a_plain_repository_starts_no_git_process(tmp_path, git_spawns) -> None:
    repository = _repository(tmp_path, "repository")
    git_spawns.clear()

    path = TIME_GUARD.learning_path(repository, RUNTIME, SESSION_ID)

    assert path == repository / ".agents" / "shared-session" / "learning" / f"{_digest()}.json"
    assert len(git_spawns) <= GIT_SPAWN_BUDGET, (
        f"learning_path started {len(git_spawns)} git processes, budget is {GIT_SPAWN_BUDGET}: "
        f"{git_spawns}"
    )


def test_learning_path_of_a_linked_worktree_starts_no_git_process(tmp_path, git_spawns) -> None:
    main = _repository(tmp_path, "main")
    linked = tmp_path / "linked"
    _git("-C", str(main), "worktree", "add", "-q", str(linked), "-b", "feature")
    git_spawns.clear()

    path = TIME_GUARD.learning_path(linked, RUNTIME, SESSION_ID)

    assert path == main / ".agents" / "shared-session" / "learning" / f"{_digest()}.json"
    assert len(git_spawns) <= GIT_SPAWN_BUDGET, (
        f"learning_path started {len(git_spawns)} git processes, budget is {GIT_SPAWN_BUDGET}: "
        f"{git_spawns}"
    )


def test_learning_path_answers_what_git_answers(tmp_path) -> None:
    main = _repository(tmp_path, "main")
    linked = tmp_path / "linked"
    _git("-C", str(main), "worktree", "add", "-q", str(linked), "-b", "feature")
    detached = tmp_path / "detached"
    _git("-C", str(main), "worktree", "add", "-q", "--detach", str(detached))
    nested = main / "nested" / "deeper"
    nested.mkdir(parents=True)

    for cwd in (main, linked, detached, nested):
        assert TIME_GUARD.learning_path(cwd, RUNTIME, SESSION_ID) == _expected_learning_path(cwd)


def test_learning_path_follows_a_repointed_git_directory(tmp_path) -> None:
    """A lookup must never answer from the repository layout of an earlier call."""

    repository = _repository(tmp_path, "repository")
    other = _repository(tmp_path, "other")

    before = TIME_GUARD.learning_path(repository, RUNTIME, SESSION_ID)
    assert before == repository / ".agents" / "shared-session" / "learning" / f"{_digest()}.json"

    # The directory now points at the git directory of another repository.
    _remove_git_directory(repository)
    (repository / ".git").write_text(f"gitdir: {other / '.git'}\n", encoding="utf-8")

    after = TIME_GUARD.learning_path(repository, RUNTIME, SESSION_ID)
    assert after == other / ".agents" / "shared-session" / "learning" / f"{_digest()}.json"
    assert after == _expected_learning_path(repository)


def test_learning_path_follows_a_removed_git_directory(tmp_path) -> None:
    """A directory that stops being a repository must stop being read as one."""

    repository = _repository(tmp_path, "repository")
    before = TIME_GUARD.learning_path(repository, RUNTIME, SESSION_ID)
    assert before == repository / ".agents" / "shared-session" / "learning" / f"{_digest()}.json"

    _remove_git_directory(repository)

    after = TIME_GUARD.learning_path(repository, RUNTIME, SESSION_ID)
    assert after == _expected_learning_path(repository)
    assert after != before


def test_worktree_listing_matches_git_byte_for_byte(tmp_path) -> None:
    """The process-free listing has to be the output of git, byte for byte."""

    helper = TIME_GUARD
    main = _repository(tmp_path, "main")
    _git("-C", str(main), "worktree", "add", "-q", str(tmp_path / "zeta"), "-b", "zeta")
    _git("-C", str(main), "worktree", "add", "-q", str(tmp_path / "alpha"), "-b", "alpha")
    _git("-C", str(main), "worktree", "add", "-q", "--detach", str(tmp_path / "detached"))
    separate_work = tmp_path / "separate-work"
    separate_work.mkdir()
    _git("init", "-q", "--separate-git-dir", str(tmp_path / "separate.git"), str(separate_work))
    bare = tmp_path / "bare.git"
    _git("init", "-q", "--bare", str(bare))
    unborn = tmp_path / "unborn"
    _git("init", "-q", str(unborn))

    for directory in (main, tmp_path / "zeta", separate_work, bare, unborn):
        common = _git("-C", str(directory), "rev-parse", "--path-format=absolute",
                      "--git-common-dir").strip()
        expected = _git("--git-dir", common, "worktree", "list", "--porcelain")
        assert helper._git_worktree_list_porcelain(Path(common)) == expected


def test_snapshot_answers_match_git_for_every_repository_shape(tmp_path) -> None:
    """The work tree and the branch of the snapshot have to be git's answers."""

    main = _repository(tmp_path, "main")
    linked = tmp_path / "linked"
    _git("-C", str(main), "worktree", "add", "-q", str(linked), "-b", "feature")
    detached = tmp_path / "detached"
    _git("-C", str(main), "worktree", "add", "-q", "--detach", str(detached))
    nested = main / "nested" / "deeper"
    nested.mkdir(parents=True)
    unborn = tmp_path / "unborn"
    _git("init", "-q", str(unborn))
    bare = tmp_path / "bare.git"
    _git("init", "-q", "--bare", str(bare))
    separate_work = tmp_path / "separate-work"
    separate_work.mkdir()
    _git("init", "-q", "--separate-git-dir", str(tmp_path / "separate.git"), str(separate_work))
    outside = tmp_path / "outside"
    outside.mkdir()

    for directory in (main, nested, linked, detached, unborn, bare, separate_work, outside):
        assert _git_answer(directory, "rev-parse", "--show-toplevel") == \
            _effective(TIME_GUARD._git_worktree_root(directory))
        assert _git_answer(directory, "branch", "--show-current") == \
            _effective(TIME_GUARD._git_current_branch(directory))


def _git_answer(directory: Path, *arguments: str) -> str:
    """Answer one git question, reporting a failed question as unavailable."""

    completed = subprocess.run(
        ["git", *arguments], cwd=str(directory), capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip()


def _effective(answer: str | Path | None) -> str:
    """Report a refused answer the way the guard reports it."""

    if answer is None:
        return "unavailable"
    return str(answer)


def test_git_snapshot_starts_only_the_two_git_processes_it_needs(tmp_path, git_spawns) -> None:
    """The work tree and the branch come from the disk, the rest needs git."""

    repository = _repository(tmp_path, "repository")
    git_spawns.clear()

    snapshot = TIME_GUARD.git_snapshot(repository)

    assert len(git_spawns) <= GIT_SNAPSHOT_SPAWN_BUDGET, (
        f"git_snapshot started {len(git_spawns)} git processes, budget is "
        f"{GIT_SNAPSHOT_SPAWN_BUDGET}: {git_spawns}"
    )
    assert f"Repository:\n{os.path.realpath(repository)}" in snapshot
    # The branch is whatever this machine's git calls the first branch: the
    # snapshot must name the branch of the repository, not a name from here.
    head = (repository / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    branch = head.rsplit("/", 1)[-1] if head.startswith("ref:") else head
    assert f"Branch:\n{branch}" in snapshot


def _load_reader():
    """The reader of the layout of a repository, loaded from the canon."""

    path = ROOT / "src/common/tools/lhc_gitlayout.py"
    spec = importlib.util.spec_from_file_location("lhc_gitlayout_reader", path)
    assert spec is not None and spec.loader is not None
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def test_the_guard_asks_the_one_reader_of_the_layout(tmp_path) -> None:
    """The guard has no layout of its own: it asks the reader of the canon.

    The reader owns the answers about the layout of a repository.  A second
    implementation inside the guard would drift from the answers of git, so
    the answers of the guard are compared with the answers of git and with
    the answers of the reader, for every shape of a repository.
    """

    reader = _load_reader()
    main = _repository(tmp_path, "main")
    linked = tmp_path / "linked"
    _git("-C", str(main), "worktree", "add", "-q", str(linked), "-b", "feature")
    detached = tmp_path / "detached"
    _git("-C", str(main), "worktree", "add", "-q", "--detach", str(detached))
    bare = tmp_path / "bare.git"
    _git("init", "-q", "--bare", str(bare))

    for directory in (main, linked, detached, bare):
        assert TIME_GUARD._git_worktree_root(directory) == reader.worktree_root(directory)
        assert TIME_GUARD._git_current_branch(directory) == reader.current_branch(directory)
        assert TIME_GUARD._git_primary_worktree(directory) == reader.primary_worktree(directory)
        common = reader.common_dir_of(directory)
        assert (TIME_GUARD._git_worktree_list_porcelain(common)
                == reader.worktree_list_porcelain(common))
        assert _git_answer(directory, "rev-parse", "--show-toplevel") == \
            _effective(TIME_GUARD._git_worktree_root(directory))
        assert _git_answer(directory, "branch", "--show-current") == \
            _effective(TIME_GUARD._git_current_branch(directory))
