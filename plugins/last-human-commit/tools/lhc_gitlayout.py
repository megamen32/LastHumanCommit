#!/usr/bin/env python3
"""Answers about the layout of a Git repository, read from the disk.

This module is the one place of the canon that answers the questions about
the layout of a repository: where its git directory is, where the shared git
directory is, which worktrees it has, which branch the work tree is on and
which configuration it keeps.  The worktree tool, the mailbox and the
persistent time guard ask it; the reader of the repository facts asks it for
the directories it reads the objects and the references from.

The answers are facts about the directories on the disk, so they are read
from the disk instead of paying for a git process on every question.

Every answer is read at the moment of the call and nothing is cached, so a
repository that changed between two calls is never answered from a stale
value.  A layout this module does not model answers None and the caller asks
the git binary instead, so an unusual repository keeps the answer it has
today.

The answers are the ones git gives, path for path:

* ``discover_git_dir`` answers the git directory that owns a directory,
* ``common_dir_of`` answers ``git rev-parse --path-format=absolute
  --git-common-dir``,
* ``absolute_git_dir`` answers ``git rev-parse --absolute-git-dir``,
* ``worktree_list_porcelain`` answers ``git worktree list --porcelain``,
* ``primary_worktree`` answers the first worktree of that listing,
* ``worktree_root`` answers ``git rev-parse --show-toplevel`` and
* ``current_branch`` answers ``git branch --show-current``.
"""
from __future__ import annotations

import os
from pathlib import Path


# Environment variables that change how git discovers the repository.  While
# any of them is set the discovery of git is not the plain directory walk this
# module models, so the answer is left to the git binary.
DISCOVERY_ENVIRONMENT = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_CEILING_DIRECTORIES",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
)

NULL_OBJECT_ID = "0" * 40
_OBJECT_ID_LENGTHS = (40, 64)
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class Repository:
    """Where the repository lives and which files Git keeps for it."""

    def __init__(self, gitdir: Path, root: Path, common: Path):
        self.gitdir = gitdir
        self.root = root
        self.common = common


def read_text(path: Path, *, errors: str = "replace") -> str | None:
    """Read one text file, answering None when it cannot be read.

    The reader of the repository facts keeps the bytes of a name it cannot
    decode, so it asks for ``surrogateescape``; the layout answers are read
    as ordinary text.
    """

    try:
        return path.read_text(encoding="utf-8", errors=errors)
    except OSError:
        return None


def is_git_directory(path: Path) -> bool:
    """Report whether a directory holds a git directory, as git decides it."""

    try:
        return (
            (path / "HEAD").is_file()
            and (path / "objects").is_dir()
            and (path / "refs").is_dir()
        )
    except OSError:
        return False


def is_linked_git_directory(path: Path) -> bool:
    """Report whether a directory holds the git directory of a linked worktree.

    A linked worktree keeps its own git directory next to the shared one.  It
    has no objects and no shared refs of its own, it names the shared git
    directory in a ``commondir`` file instead.
    """

    try:
        return (path / "HEAD").is_file() and (path / "commondir").is_file()
    except OSError:
        return False


def gitdir_pointer(path: Path) -> Path | None:
    """Read the target of a ``gitdir:`` pointer file such as ``.git``."""

    text = read_text(path)
    if text is None:
        return None
    text = text.strip()
    if not text.startswith("gitdir:"):
        return None
    target = text[len("gitdir:"):].strip()
    if not target:
        return None
    candidate = Path(target)
    if not candidate.is_absolute():
        candidate = path.parent / candidate
    return candidate


def common_dir_of_git_dir(git_dir: Path) -> Path:
    """Return the shared git directory of the repository that owns a git dir.

    A linked worktree keeps its own git directory and names the shared one in
    a ``commondir`` file next to it.
    """

    text = read_text(git_dir / "commondir")
    if text is None:
        return git_dir
    content = text.strip()
    if not content:
        return git_dir
    candidate = Path(content)
    if not candidate.is_absolute():
        candidate = git_dir / candidate
    return candidate


def _discover(cwd: Path) -> tuple[Path, Path] | None:
    """Find the directory that owns a repository and its git directory.

    The answer is the pair of the directory that holds the repository and the
    git directory of that repository, the way git discovers them.  ``None``
    means the repository is not discovered the way this module models it and
    the git binary has to answer.
    """

    for name in DISCOVERY_ENVIRONMENT:
        if os.environ.get(name):
            return None
    try:
        start = Path(os.path.realpath(str(cwd)))
    except OSError:
        return None
    try:
        if not start.is_dir():
            return None
    except OSError:
        return None
    for root in (start, *start.parents):
        try:
            # A bare repository is its own git directory.
            if is_git_directory(root):
                return root, root
            candidate = root / ".git"
            if candidate.is_dir():
                if is_git_directory(candidate):
                    return root, candidate
                continue
            if candidate.is_file():
                pointer = gitdir_pointer(candidate)
                if pointer is None:
                    continue
                if is_git_directory(pointer) or is_linked_git_directory(pointer):
                    return root, pointer
        except OSError:
            continue
    return None


def discover(cwd: Path) -> Repository | None:
    """The repository that owns a directory, or None when git has to answer."""

    found = _discover(cwd)
    if found is None:
        return None
    root, git_dir = found
    return Repository(git_dir, root, common_dir_of_git_dir(git_dir))


def discover_git_dir(cwd: Path) -> Path | None:
    """Find the git directory that owns a directory, the way git discovers it."""

    found = _discover(cwd)
    return None if found is None else found[1]


def common_dir_of(cwd: Path) -> Path | None:
    """Answer ``git rev-parse --path-format=absolute --git-common-dir``.

    ``None`` means the repository is not discovered the way this module models
    it and the git binary has to answer.
    """

    git_dir = discover_git_dir(cwd)
    if git_dir is None:
        return None
    shared = common_dir_of_git_dir(git_dir)
    try:
        return Path(os.path.realpath(str(shared)))
    except OSError:
        return None


def absolute_git_dir(cwd: Path) -> Path | None:
    """Answer ``git rev-parse --absolute-git-dir`` for a directory.

    The git directory of a linked worktree is the one next to the shared one,
    not the shared one itself.  ``None`` means the repository is not
    discovered the way this module models it and the git binary has to
    answer.
    """

    git_dir = discover_git_dir(cwd)
    if git_dir is None:
        return None
    return git_dir


def _config_value(config: Path, section: str, key: str) -> str | None:
    """Read one config value, answering None when the key is not set."""

    text = read_text(config)
    if text is None:
        return None
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().split(" ", 1)[0].casefold()
            continue
        name, separator, value = line.partition("=")
        if not separator:
            continue
        if current != section.casefold() or name.strip().casefold() != key.casefold():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return None


def _config_boolean(config: Path, section: str, key: str) -> bool | None:
    """Read a boolean config value, answering None when it is not a boolean."""

    value = _config_value(config, section, key)
    if value is None:
        return False
    if value.casefold() in {"true", "yes", "on", "1"}:
        return True
    if value.casefold() in {"false", "no", "off", "0", ""}:
        return False
    return None


def _looks_like_object_id(value: str) -> bool:
    """Report whether a string is a full hexadecimal object id."""

    return len(value) in _OBJECT_ID_LENGTHS and set(value) <= _HEX_DIGITS


def _resolve_ref(git_dir: Path, common: Path, refname: str) -> str | None:
    """Resolve one reference to the object id it points at."""

    for root in (git_dir, common):
        try:
            candidate = root / refname
            if not candidate.is_file():
                continue
        except OSError:
            return None
        value = (read_text(candidate) or "").strip()
        if value.startswith("ref:"):
            nested = value[len("ref:"):].strip()
            if not nested:
                return None
            return _resolve_ref(git_dir, common, nested)
        if _looks_like_object_id(value):
            return value
        return None
    packed = read_text(common / "packed-refs")
    if packed is None:
        return None
    for raw in packed.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        if parts[1].strip() == refname and _looks_like_object_id(parts[0].strip()):
            return parts[0].strip()
    return None


def _head_state(git_dir: Path, common: Path) -> tuple[str, str] | None:
    """Return the object id and the branch or detached state of one HEAD."""

    text = read_text(git_dir / "HEAD")
    if text is None:
        return None
    content = text.strip()
    if not content:
        return None
    if content.startswith("ref:"):
        refname = content[len("ref:"):].strip()
        if not refname:
            return None
        return _resolve_ref(git_dir, common, refname) or NULL_OBJECT_ID, f"branch {refname}"
    if _looks_like_object_id(content):
        return content, "detached"
    return None


def _linked_worktrees(common: Path) -> list[tuple[Path, Path]] | None:
    """List the linked worktrees of a repository, ordered by their path.

    ``None`` means the repository carries a worktree this module does not
    model, such as a locked or a prunable one.
    """

    root = common / "worktrees"
    try:
        names = sorted(os.listdir(root))
    except FileNotFoundError:
        return []
    except OSError:
        return None
    found: list[tuple[Path, Path]] = []
    for name in names:
        entry = root / name
        try:
            if not entry.is_dir():
                continue
            if (entry / "locked").exists():
                return None
        except OSError:
            return None
        pointer = read_text(entry / "gitdir")
        if pointer is None:
            return None
        target = pointer.strip()
        if not target:
            return None
        worktree = Path(target)
        if not worktree.is_absolute():
            worktree = entry / worktree
        worktree = worktree.parent
        try:
            if not worktree.is_dir():
                return None
        except OSError:
            return None
        found.append((entry, worktree))
    found.sort(key=lambda item: str(item[1]))
    return found


def _worktree_block(path: Path, common: Path, git_dir: Path, bare: bool) -> str | None:
    """Render one worktree of the porcelain listing."""

    lines = [f"worktree {path}"]
    if bare:
        lines.append("bare")
    else:
        head = _head_state(git_dir, common)
        if head is None:
            return None
        lines.append(f"HEAD {head[0]}")
        lines.append(head[1])
    lines.append("")
    return "\n".join(lines) + "\n"


def _default_worktree(git_dir: Path) -> Path | None:
    """Return the worktree a git directory belongs to.

    Git derives the worktree of a repository from the location of its git
    directory: a git directory called ``.git`` sits inside the worktree, any
    other name is its own worktree.  ``None`` means the layout is too short to
    decide and the git binary has to answer.
    """

    text = str(git_dir)
    if not text.endswith("/.git"):
        return git_dir
    stripped = text[: -len("/.git")]
    if not stripped:
        return None
    return Path(stripped)


def worktree_list_porcelain(common_dir: Path) -> str | None:
    """Answer ``git worktree list --porcelain`` for a shared git directory.

    The output is byte for byte the output of git for the layouts this module
    models.  ``None`` means the layout is not modelled and the git binary has
    to answer.
    """

    try:
        common = Path(os.path.realpath(str(common_dir)))
    except OSError:
        return None
    if not is_git_directory(common):
        return None
    bare = _config_boolean(common / "config", "core", "bare")
    if bare is None:
        return None
    main = _default_worktree(common)
    if main is None:
        return None
    first = _worktree_block(main, common, common, bare)
    if first is None:
        return None
    linked = _linked_worktrees(common)
    if linked is None:
        return None
    blocks = [first]
    for git_dir, worktree in linked:
        block = _worktree_block(worktree, common, git_dir, False)
        if block is None:
            return None
        blocks.append(block)
    return "".join(blocks)


def primary_worktree(cwd: Path) -> Path | None:
    """Return the primary worktree of the repository that owns a directory.

    The answer is read from the repository layout at the moment of the call.
    ``None`` means the layout is not modelled and the git binary has to answer.
    """

    common = common_dir_of(cwd)
    if common is None:
        return None
    listing = worktree_list_porcelain(common)
    if listing is None:
        return None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree "))
    return None


def worktree_root(cwd: Path) -> Path | None:
    """Answer ``git rev-parse --show-toplevel`` for a directory.

    The work tree of a repository is the directory that holds its git
    directory.  ``None`` means the directory is not inside a work tree, or the
    layout is not one this code models, and the git binary has to answer.
    """

    if any(os.environ.get(name) for name in DISCOVERY_ENVIRONMENT):
        return None
    try:
        start = Path(os.path.realpath(str(cwd)))
    except OSError:
        return None
    try:
        if not start.is_dir():
            return None
    except OSError:
        return None
    for root in (start, *start.parents):
        try:
            if is_git_directory(root):
                # A git directory is not a work tree of its own.
                return None
            candidate = root / ".git"
            if not candidate.exists():
                continue
            git_dir = candidate if candidate.is_dir() else gitdir_pointer(candidate)
            if git_dir is None:
                return None
            if _config_value(git_dir / "config", "core", "worktree") is not None:
                # The work tree is named in the config, not derived from the place.
                return None
            return root
        except OSError:
            return None
    return None


def current_branch(cwd: Path) -> str | None:
    """Answer ``git branch --show-current`` for a directory.

    The current branch is the branch the HEAD of the work tree points at.  An
    empty answer is a detached HEAD, which git reports as an empty branch.
    ``None`` means the directory is not in a repository, the HEAD points
    outside ``refs/heads``, or the layout is not one this code models.
    """

    git_dir = discover_git_dir(cwd)
    if git_dir is None:
        return None
    text = read_text(git_dir / "HEAD")
    if text is None:
        return None
    content = text.strip()
    if content.startswith("ref:"):
        refname = content[len("ref:"):].strip()
        if not refname.startswith("refs/heads/"):
            return None
        return refname[len("refs/heads/"):]
    if _looks_like_object_id(content):
        return ""
    return None
