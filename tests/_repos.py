"""Prepared Git repositories for the cases, and the facts about them.

A case that needs a Git checkout used to build one from nothing: ``git init``,
two ``git config`` calls, ``git add``, ``git commit``.  Every one of those is
a process start, and the suite pays for them hundreds of times - the whole
run started about a thousand processes, and about a third of its wall clock
went into waiting for them.

The repository of a case does not have to be built to be believed in.  What
the cases read from a repository is what the repository *is*: a branch, an
identity, a set of committed files.  A prepared template holds exactly that,
and a case receives its own checkout by copying it.  The copy is a real Git
repository - the same layout, the same history, the same answers to every
Git question - so every assertion that compares a tool with Git keeps
comparing the tool with Git.

What this module does not do is answer a Git question.  The truth about Git
still comes from the Git binary; this module only stops the suite from
building the same repository over and over.

The helpers here are private to the test suite.  No test file may depend on
them.
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

#: The prepared templates of this process, keyed by what they contain.
_TEMPLATES: dict[tuple, Path] = {}

#: The directory the prepared templates of this process live in.
_TEMPLATE_ROOT: Path | None = None


def _template_root() -> Path:
    """The directory the prepared templates of this process live in.

    The name carries the process id: two pytest runs may share the
    project-local temporary root and must not share a template.
    """

    global _TEMPLATE_ROOT
    if _TEMPLATE_ROOT is None:
        root = REPO_ROOT / ".tmp" / f"lhc-prepared-repos-{os.getpid()}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        atexit.register(shutil.rmtree, root, True)
        _TEMPLATE_ROOT = root
    return _TEMPLATE_ROOT


def _git(repo: Path, *args: str) -> None:
    """Run one Git command in a repository that is being prepared."""

    subprocess.run(["git", "-C", str(repo), *args],
                   check=True, capture_output=True)


def _drop_hook_samples(repo: Path) -> None:
    """Drop the inert hook samples ``git init`` writes.

    ``git init`` writes fourteen sample hooks that no case ever runs.  They
    are four times heavier than the rest of the repository, and every copy
    would carry them; the default ignore rules in ``info/exclude`` stay
    untouched, so the checkout behaves exactly as before.
    """

    hooks = repo / ".git" / "hooks"
    if hooks.is_dir():
        for sample in hooks.glob("*.sample"):
            sample.unlink()


def _build_template(branch, config, files, message) -> Path:
    """Build one prepared repository and return it."""

    root = _template_root()
    template = root / ("repo-" + str(len(_TEMPLATES)))
    template.mkdir()
    command = ["git", "init", "-q"]
    if branch is not None:
        command += ["-b", branch]
    command.append(str(template))
    subprocess.run(command, check=True, capture_output=True)
    for name, value in config:
        _git(template, "config", name, value)
    for name, text in files:
        path = template / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if files:
        _git(template, "add", "-A")
        _git(template, "commit", "-qm", message)
    _drop_hook_samples(template)
    return template


def prepared_repo(path, *, branch=None, config=(), files=(), message="fixture") -> Path:
    """Give the case its own Git checkout, copied from a prepared template.

    ``files`` are the paths and the contents the checkout holds, relative to
    its root; they are committed under ``message``.  ``config`` is the
    sequence of ``(name, value)`` pairs the checkout carries.

    The copy is a Git repository of its own: the branch, the identity, the
    committed files and the answers of every Git command are the ones the
    checkout would have had if it had been built by hand.
    """

    target = Path(path)
    key = (branch, tuple(config), tuple(files), message)
    template = _TEMPLATES.get(key)
    if template is None:
        template = _build_template(branch, config, files, message)
        _TEMPLATES[key] = template
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, target, dirs_exist_ok=True)
    return target


def head_of(root) -> str:
    """The commit of HEAD, read from the repository itself.

    The repository keeps its own answer: ``HEAD`` names a reference, and the
    reference is either the loose file of that name or the line of
    ``packed-refs`` that carries it.
    """

    gitdir = Path(root) / ".git"
    head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head
    name = head[4:].strip()
    loose = gitdir / name
    if loose.is_file():
        return loose.read_text(encoding="utf-8").strip()
    packed = gitdir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == name:
                return parts[0]
    raise AssertionError("HEAD names no commit: " + name)
