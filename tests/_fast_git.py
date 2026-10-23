"""The git the suite starts, and the proof that it is the very same git.

On this machine ``/usr/bin/git`` is an ``xcrun`` stub: it spends about 21 ms
on every start to resolve the developer directory, while the git it forwards
to needs about 7 ms.  The tools under test start git thousands of times per
suite, so that difference is one of the largest remaining costs of a run.

The forwarded binary is accepted only when it is *provably* the same git:

* it reports exactly the same ``git --version``, and
* for every git command the tools under test use, it produces byte identical
  stdout, byte identical stderr and the same exit code.

The proof runs in a scratch repository of its own, so it cannot be influenced
by the repository a case works in.  When no such binary exists - or when the
proof fails - the suite simply keeps the git of the PATH and nothing changes.

The helpers here are private to the test suite.  No test file may depend on
them.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


#: The git commands the tools under test ask for.  The proof below runs each
#: of them against both binaries in the same repository and compares the bytes
#: they produce, so a binary that answers anything else is refused.
GIT_COMMANDS = (
    ("--version",),
    ("rev-parse", "--git-common-dir"),
    ("rev-parse", "--show-toplevel"),
    ("rev-parse", "--absolute-git-dir"),
    ("rev-parse", "--is-inside-work-tree"),
    ("rev-parse", "--show-prefix"),
    ("rev-parse", "--short=12", "HEAD"),
    ("status", "--short"),
    ("status", "--porcelain"),
    ("ls-files", "-z"),
    ("ls-files", "--others", "--exclude-standard", "-z"),
    ("diff", "--name-only", "-z", "HEAD"),
    ("diff", "--name-only", "-z"),
    ("log", "--oneline", "-1"),
    ("show", "--name-only", "--format=", "HEAD"),
    ("remote", "-v"),
    ("remote", "get-url", "origin"),
    ("worktree", "list"),
    ("config", "--get", "core.repositoryformatversion"),
    ("branch", "--show-current"),
)


_FAST_GIT_DIRECTORY: str | None = None
_FAST_GIT_RESOLVED = False


def _scratch_repository(root: Path) -> Path:
    """A small repository with one commit, used only by the proof."""

    repo = root / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)],
                   check=True, capture_output=True)
    for name, value in (("user.email", "proof@example.invalid"),
                        ("user.name", "Proof")):
        subprocess.run(["git", "-C", str(repo), "config", name, value],
                       check=True, capture_output=True)
    (repo / "proof.txt").write_text("proof\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "proof.txt"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "proof"],
                   check=True, capture_output=True)
    return repo


def _same_answers(current: str, forwarded: str, repo: Path) -> bool:
    """True when both binaries answer every command of the proof identically."""

    for command in GIT_COMMANDS:
        first = subprocess.run([current, "-C", str(repo), *command],
                               capture_output=True)
        second = subprocess.run([forwarded, "-C", str(repo), *command],
                                capture_output=True)
        if (first.returncode, first.stdout, first.stderr) != (
                second.returncode, second.stdout, second.stderr):
            return False
    return True


def fast_git_directory() -> str | None:
    """A directory whose only entry is a link to the git the system forwards to.

    The directory holds a link and nothing else, so the rest of the PATH - the
    ``python3`` of the fixture commands included - is untouched.  ``None`` means
    that no binary could be proven to be the same git, and the git of the PATH
    stays in use.
    """

    global _FAST_GIT_DIRECTORY, _FAST_GIT_RESOLVED
    if _FAST_GIT_RESOLVED:
        return _FAST_GIT_DIRECTORY
    _FAST_GIT_RESOLVED = True
    current = shutil.which("git")
    if current is None:
        return None
    try:
        version = subprocess.run([current, "--version"], capture_output=True,
                                 text=True, check=True).stdout.strip()
        forwarded = subprocess.run(["xcrun", "-f", "git"], capture_output=True,
                                   text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if not forwarded or forwarded == current:
        return None
    try:
        other = subprocess.run([forwarded, "--version"], capture_output=True,
                               text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if other != version:
        return None
    directory = Path(tempfile.mkdtemp(prefix="lhc-git-bin-"))
    atexit.register(shutil.rmtree, directory, True)
    try:
        proof = directory / "proof"
        proof.mkdir()
        repo = _scratch_repository(proof)
        if not _same_answers(current, forwarded, repo):
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    (directory / "git").symlink_to(forwarded)
    _FAST_GIT_DIRECTORY = str(directory)
    return _FAST_GIT_DIRECTORY


def git_environment() -> dict[str, str]:
    """The environment that makes a ``git`` call use the forwarded binary."""

    directory = fast_git_directory()
    if directory is None:
        return {}
    return {"PATH": directory + os.pathsep + os.environ.get("PATH", "")}


def use_fast_git() -> None:
    """Let every ``git`` of this process use the forwarded binary."""

    environment = git_environment()
    if environment:
        os.environ.update(environment)
