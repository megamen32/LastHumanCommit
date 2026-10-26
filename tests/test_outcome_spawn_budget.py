"""The outcome tools must read the repository, not ask Git about it.

One publication proof used to spend a Git process per fact: the object
existence, the parents, the changed paths, the blob of every owned file,
the remote ref and the ancestry check.  The repository already holds every
one of those facts, so they are read from disk.

These cases hold two things at once:

* the **budget** - how many Git processes one proof may start, and
* the **answer** - the answer is the answer of Git, byte for byte, and it
  is never served from a stale read.
"""
import atexit
import contextlib
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "src" / "common" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from _inprocess_lane import prepare_git_template  # noqa: E402  (the suite prepares its own checkouts)
from _repos import head_of, prepared_repo  # noqa: E402

import lhc_git_facts as facts  # noqa: E402  (the tools import each other by name)
import lhc_outcome as outcome  # noqa: E402
import lhc_source_publication as source_pub  # noqa: E402


# The budget of one publication proof.  Every fact the proof needs is a
# fact about the repository or about a remote that is a directory on this
# machine, and both are read from the state Git already keeps.  Nothing has
# to be started to learn them.
PROOF_BUDGET = 0


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


@pytest.fixture
def own_config(tmp_path, monkeypatch):
    """A configuration of this machine's own, so the answers are the ones of the case."""
    path = tmp_path / "global-config"
    path.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(path))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    return path


# The identity of every checkout of the fixture.
IDENTITY = (("user.email", "publisher@example.test"), ("user.name", "Publisher"))

# The files the base commit of the fixture holds.
BASE = (("owned.py", "print('base')\n"),)

# The candidate commit of the fixture: the files it holds and its message.
CANDIDATE = ((("owned.py", "print('candidate')\n"),), "candidate")

# The commit of many similar lines: the files it holds and its message.
LINES = (tuple(("line%d.txt" % index, "the same line over and over\n" * 40)
                for index in range(12)), "many similar lines")

# The two commits of the nested paths of the fixture.
NESTED_BASE = ((("sub/nested.py", "print('nested base')\n"),), "nested base")
NESTED_CANDIDATE = ((("sub/nested.py", "print('nested candidate')\n"),
                     ("owned.py", "print('candidate')\n")), "candidate")

# The prepared checkouts of this process, keyed by the history they hold.
_TEMPLATES: dict[str, Path] = {}

# The commits of the prepared checkouts, keyed by the name of the checkout.
_COMMITS: dict[str, list[str]] = {}

# The prepared bare remote of this process.
_BARE_TEMPLATE: Path | None = None


def _template(name: str) -> Path:
    """The directory of one prepared checkout of this process."""
    root = _TEMPLATES.get(name)
    if root is None:
        root = Path(tempfile.mkdtemp(prefix="lhc-outcome-budget-" + name + "-"))
        atexit.register(shutil.rmtree, root, True)
        _TEMPLATES[name] = root
    return root


def _prepared(name: str, *commits) -> list[str]:
    """The commits of one prepared checkout of this process, built once.

    The base commit of the fixture is the first of them.  Every other commit
    is a pair of the files it holds and the message it carries; its files are
    written over the files of the commit before it.
    """
    held = _COMMITS.get(name)
    if held is not None:
        return held
    root = _template(name)
    prepared_repo(root, config=IDENTITY, files=BASE, message="base")
    held = [head_of(root)]
    known = {path for path, _ in BASE}
    for files, message in commits:
        for path, text in files:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        if all(path in known for path, _ in files):
            # Every file of the step Git already knows: one commit is enough.
            git(root, "commit", "-aqm", message)
        else:
            git(root, "add", "-A")
            git(root, "commit", "-qm", message)
        known.update(path for path, _ in files)
        held.append(head_of(root))
    _COMMITS[name] = held
    return held


def _bare_template() -> Path:
    global _BARE_TEMPLATE
    if _BARE_TEMPLATE is None:
        root = Path(tempfile.mkdtemp(prefix="lhc-outcome-budget-bare-"))
        atexit.register(shutil.rmtree, root, True)
        subprocess.run(["git", "init", "--bare", "-q", str(root)], check=True)
        prepare_git_template(root)
        _BARE_TEMPLATE = root
    return _BARE_TEMPLATE


def repository(path, name="base", *commits):
    """The checkout of one case: a copy of a prepared checkout and its commits.

    The history and the identity of the fixture are fixed, so `git init`,
    both `git config` calls, `git add` and `git commit` all become a copy;
    only the real publication work stays a real Git call.
    """
    held = _prepared(name, *commits)
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_template(name), root, dirs_exist_ok=True)
    return root, held


def bare_remote(path):
    """A bare remote on this machine, the way a publication target is."""
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_bare_template(), root, dirs_exist_ok=True)
    return root


def commit_of(root, message, content):
    """One commit with the given content of the owned file.

    The owned file is the only file the commit changes, so the commit takes
    the change of the working tree as it is.
    """
    (root / "owned.py").write_text(content)
    git(root, "commit", "-aqm", message)
    return head_of(root)


def metadata_for(base, commit, root):
    """The published metadata of one candidate commit."""
    blob = git(root, "show", f"{commit}:owned.py")
    return {"base": base, "published_commit": commit,
            "owned_files": {"owned.py": hashlib.sha256(blob).hexdigest()}}


def test_the_historical_publication_proof_starts_no_git_process(tmp_path, own_config):
    """Every fact of the proof is a fact the repository already holds."""
    root, (base, commit) = repository(tmp_path / "product", "candidate", CANDIDATE)
    metadata = metadata_for(base, commit, root)

    with git_processes() as started:
        proof = source_pub.historical_publication_commit_matches(metadata, root)
    assert proof is True
    assert len(started) <= PROOF_BUDGET, started


def test_the_source_publication_contract_starts_no_git_process(tmp_path, own_config):
    """The contract reads the head, the remote and the ancestry from disk."""
    root, _ = repository(tmp_path / "product")
    remote = bare_remote(tmp_path / "remote.git")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "-u", "origin", "HEAD:main")
    (root / "owned.py").write_text("print('candidate')\n")
    source = {"source": "native-user-prompt:publisher:source-1",
              "scope_prompt": "Source-only task. Publish owned.py from " + str(root) +
                              " to origin/main."}

    with git_processes() as started:
        metadata = source_pub.capture_contract(
            {"owner": {"session_id": "publisher"}}, source, root, ["owned.py"],
            "origin", "main", None, "project:" + str(root),
            "git ls-remote origin refs/heads/main", "candidate", lambda *_: True)
    assert metadata["base"] == git(root, "rev-parse", "HEAD").decode().strip()
    assert len(started) <= PROOF_BUDGET, started


def test_the_remote_binding_starts_no_git_process(tmp_path, own_config):
    """The repository of a remote is read from the configuration, not from Git."""
    root, _ = repository(tmp_path / "product")
    git(root, "remote", "add", "origin", "https://github.com/owned/project.git")

    with git_processes() as started:
        binding = outcome.remote_binding(root, "origin")
    assert binding == "owned/project"
    assert len(started) <= PROOF_BUDGET, started


def test_the_remote_url_is_the_one_git_reports_after_the_insteadof_rule(tmp_path, own_config):
    """Git rewrites the URL of a remote while it reads it; the raw value is not the answer."""
    root, _ = repository(tmp_path / "product")
    git(root, "remote", "add", "origin", "https://github.com/owned/project.git")
    own_config.write_text('[url "ssh://git@example.com/"]\n\tinsteadOf = https://github.com/\n')

    assert facts.remote_url(root, "origin") == "ssh://git@example.com/owned/project.git"
    assert facts.remote_url(root, "origin") == git(root, "remote", "get-url", "origin").decode().strip()


def test_the_answers_are_the_answers_of_git(tmp_path, own_config):
    """Every fact read from the disk is the fact Git prints."""
    root, (base, commit) = repository(tmp_path / "product", "candidate", CANDIDATE)
    repo = facts.discover(root)

    assert facts.head_sha(repo) == git(root, "rev-parse", "HEAD").decode().strip()
    assert facts.commit_exists(repo, f"{commit}^{{commit}}") is True
    assert " ".join([commit, *facts.commit_parents(repo, commit)]) == \
        git(root, "rev-list", "--parents", "-n", "1", commit).decode().strip()
    assert facts.changed_paths(repo, base, commit, no_renames=True) == \
        git(root, "diff", "--name-only", "--no-renames", base, commit).decode().splitlines()
    assert facts.changed_paths(repo, base, commit, no_renames=False) == \
        git(root, "diff", "--name-only", base, commit).decode().splitlines()
    assert facts.blob_at(repo, commit, "owned.py") == git(root, "show", f"{commit}:owned.py")
    assert facts.is_ancestor(repo, base, commit) is True
    assert facts.is_ancestor(repo, commit, base) is False


def test_the_changed_paths_are_the_paths_git_prints(tmp_path, own_config):
    """The paths of a difference are the paths Git lists, nested ones included."""
    root, (_, base, commit) = repository(tmp_path / "product", "nested",
                                         NESTED_BASE, NESTED_CANDIDATE)
    repo = facts.discover(root)

    assert facts.changed_paths(repo, base, commit, no_renames=True) == \
        git(root, "diff", "--name-only", "--no-renames", base, commit).decode().splitlines()
    assert "sub/nested.py" in facts.changed_paths(repo, base, commit, no_renames=True)


def test_a_moved_head_is_not_served_from_a_stale_read(tmp_path, own_config):
    """A HEAD that moved is a different revision, with a different answer."""
    root, (base,) = repository(tmp_path / "product")
    repo = facts.discover(root)
    assert facts.head_sha(repo) == base

    commit = commit_of(root, "candidate", "print('candidate')\n")
    assert facts.head_sha(facts.discover(root)) == commit


def test_a_candidate_that_changed_is_not_served_from_a_stale_read(tmp_path, own_config):
    """The blob of the published commit is read now, not from an earlier read."""
    root, (base, commit) = repository(tmp_path / "product", "candidate", CANDIDATE)
    metadata = metadata_for(base, commit, root)
    assert source_pub.historical_publication_commit_matches(metadata, root) is True

    # The candidate the metadata names is not the candidate anymore, and the
    # proof has to fail at once instead of serving the earlier answer.
    changed = dict(metadata, owned_files={"owned.py": "0" * 64})
    assert source_pub.historical_publication_commit_matches(changed, root) is False


def test_a_packed_repository_is_answered_the_same_way(tmp_path, own_config):
    """A repository whose objects are packed holds the same facts on disk."""
    root, (_, base) = repository(tmp_path / "product", "lines", LINES)
    commit = commit_of(root, "candidate", "print('candidate')\n")
    metadata = metadata_for(base, commit, root)
    git(root, "gc", "-q")
    packed = facts.discover(root)

    # The objects are packed now, and the pack still holds every fact.
    assert facts.commit_exists(packed, f"{commit}^{{commit}}") is True
    assert facts.blob_at(packed, commit, "owned.py") == git(root, "show", f"{commit}:owned.py")
    assert facts.changed_paths(packed, base, commit, no_renames=True) == \
        git(root, "diff", "--name-only", "--no-renames", base, commit).decode().splitlines()
    # The proof holds, and it holds without starting a Git process.
    with git_processes() as started:
        proof = source_pub.historical_publication_commit_matches(metadata, root)
    assert proof is True
    assert len(started) <= PROOF_BUDGET, started


def test_the_repository_the_facts_read_is_the_repository_git_names(tmp_path, own_config):
    """The facts are read from the directories Git names.

    The canon keeps one answer about where a repository lives, so the reader
    of the facts has to name the same directories Git names, for every shape
    of a repository.
    """
    root, _ = repository(tmp_path / "product")
    linked = tmp_path / "linked"
    git(root, "worktree", "add", "-q", str(linked), "-b", "feature")
    bare = bare_remote(tmp_path / "bare.git")

    for directory in (root, linked, bare):
        repo = facts.discover(directory)
        assert repo is not None, directory
        expected_common = git(directory, "rev-parse", "--path-format=absolute",
                              "--git-common-dir").decode().strip()
        expected_absolute = git(directory, "rev-parse", "--absolute-git-dir").decode().strip()
        # The names are compared as the directories they are: a linked
        # worktree names the shared git directory relatively.
        assert Path(repo.common).resolve() == Path(expected_common).resolve(), directory
        assert Path(repo.gitdir).resolve() == Path(expected_absolute).resolve(), directory
