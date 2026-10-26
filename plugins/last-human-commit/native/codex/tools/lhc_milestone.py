"""Durable native milestone debt. Observation only: no actions or scheduling.

Intent comes from human messages, change from Git, feedback from adapter-owned
raw transcripts exported by the existing Herder. Leader prose cannot accept work.

The module also exposes an explicit command line for the agent:

    lhc_milestone.py --cwd <root> --runtime <rt> --session-id <sid> observe --event <ev>
    lhc_milestone.py --cwd <root> --runtime <rt> --session-id <sid> gate
    lhc_milestone.py --cwd <root> --runtime <rt> --session-id <sid> status

These are agent-invoked commands, never hooks. A hook only tracks time; the
blocking acceptance check lives in ``gate`` so the agent asks for it explicitly.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
from time import monotonic

try:
    import lhc_git_facts as facts
except ImportError:
    # The published package may not ship the reader of the repository yet.
    # Git then answers every question, which is the answer it always gave.
    facts = None


def _load_git_layout():
    """Load the reader of the layout of a repository from next to this file.

    ``None`` means the reader is not there at all; every question about the
    layout is then answered by the git binary, the way it was answered
    before the reader existed.
    """

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


# The reader of the layout of a repository.  It is the one place of the canon
# that answers where a repository lives, so this module asks it instead of
# looking for the repository itself.
layout = _load_git_layout()

MAX_BYTES = 8 * 1024 * 1024
UI = re.compile(r"\.(?:html?|css|scss|sass|vue|svelte|jsx|tsx|qml|xaml|dart|swift|xml)$", re.I)
GENERATED_UI = re.compile(r"\.(?:[cm]?[jt]s|py|go|rb|php)$", re.I)
SURFACE = re.compile(r"\b(?:ui|ux|web|website|dashboard|frontend|interface|screen|page|portal|landing|app|visual|layout|responsive|form)\b|интерфейс|экран|страниц|кабинет|сайт|приложен|дашборд|лендинг|визуал|форм[ау]|дизайн", re.I)
BUILD = re.compile(r"\b(?:build|create|implement|redesign|rebuild|develop|complete|improve)\b|создай|сделай|реализуй|разработ|переделай|переработ|улучши", re.I)
SMALL = re.compile(r"\b(?:small|minor|tiny|typo|padding|spacing)\b|опечат|отступ|мелк|небольш", re.I)
# This suppresses whole-task milestone obligations, not tool permissions. A
# scoped or quoted "only check/review" clauses can restrict one surface while
# another stays actionable, so only direct task-wide wording at a line boundary
# belongs here. This never grants an operation or changes harness permission.
READ_ONLY = re.compile(r"^\s*(?:\b(?:read.only|review only|you are .{0,30}(?:tester|reviewer)|zero knowledge tester|do not (?:edit|modify) code|no code changes)\b|только (?:прочитай|ревью|review)\b|ты .{0,25}тестировщик|не (?:меняй|редактируй) код)", re.I | re.M)
ACCEPT = re.compile(r"(?:final|milestone|explicit|user) acceptance|(?:итогов|финальн|пользовательск).{0,20}при[её]мк|focus.groups|фокус.групп", re.I)
URL = re.compile(r"https?://[^\s<>\]\)\"']+", re.I)
POSITIVE = re.compile(r"\bpositive\b|\bliked\b|what helped|(?<!не )понрав|(?<!не )\bпомог|\bудобно\b", re.I)
NEGATIVE = re.compile(r"negative|disliked|confus|frustrat|не понрав|мешал|неудоб|затруд|недостат|критик|limitations|obstacles|defects|ошиб|ограничен|помех", re.I)
ACHIEVED = re.compile(r"(?:goal|task) (?:was )?(?:achieved|completed)|цель достигнута|задача выполнена|\bPASS\b", re.I)
CHANGES = re.compile(r"changes.required|goal (?:was )?not achieved|цель не достигнута|нужны исправления", re.I)
PARTIAL = re.compile(r"\bpartial\b|not.tested|never (?:attempted|tested)|did not (?:test|attempt|complete|import)|(?:required|assigned).{0,60}(?:failed|untested)|частичн|не (?:проверил|протестировал|пытался|импортировал)", re.I)

# ---------------------------------------------------------------------------
# The Git facts of a repository
#
# The observer asks one repository the same questions over and over: which
# files are tracked, which are untracked, which changed against the task
# HEAD, and what a remote points at.  Every answer is a fact about the
# working tree, so the layer below reads Git's own on-disk state - the
# index, HEAD, the config and the ignore rules - instead of starting a
# process for each question.
#
# Two rules keep the answers honest.
#
# * A reused answer comes with its invalidation.  The changed-paths answer
#   is reused only while the index, the HEAD reference and the stat of every
#   tracked file are bit for bit the ones it was computed for.  That is the
#   observable signal Git's own index uses, so a file that appeared, vanished
#   or changed, and a HEAD that moved, all end the reuse.  The tracked and
#   untracked lists are never reused at all: they are read from the index and
#   from a fresh walk of the working tree every time.
# * Anything unusual is answered by Git itself.  A linked worktree, a split
#   or sparse index, an unmerged path, an ignore file that a global config
#   points Git at: each of those falls back to a real `git` call, so the
#   answer stays the one Git would give.
#
# Nothing here writes, fetches or locks.  Every read is a plain file read of
# state Git already keeps on disk.
# ---------------------------------------------------------------------------


# The environment variables that move the state Git reads away from the
# working tree: the index, the objects and the configuration.  The facts of
# this module are read from the disk, so they are the facts of Git only while
# the environment keeps Git on the disk; otherwise the question is left to
# Git.
#
# The variables that move the *repository* away from the working tree are the
# business of the reader of the layout: it answers None for them, and Git
# answers instead.
_FACT_ENVIRONMENT_OVERRIDES = (
    "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM",
)

# Git's own bound on a single answer.  A repository larger than this is
# answered by Git, not by a partial read.
_SHA = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")

# The bounded caches below are keyed by repository, never by content, and
# hold at most a handful of repositories.  A cache entry is dropped as soon
# as the state it describes changes.
_CACHE_LIMIT = 16

_INDEXES = {}
_CHANGED = {}
_REMOTES = {}


def _stat(path):
    """The observable stamp of one path, or None when it is gone."""
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_size, info.st_ino)


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _read_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def _trim_cache(cache):
    while len(cache) > _CACHE_LIMIT:
        cache.pop(next(iter(cache)))


# ---------------------------------------------------------------------------
# The repository
#
# The canon answers the questions about the layout of a repository in one
# place: the reader of the layout.  This module asks it, so the repository
# the facts below are read from is the repository Git would name, found the
# way Git finds it and read at the moment of the question.  Nothing about the
# layout is remembered, so a repository that moved between two questions is
# never answered from the layout of an earlier one.  A layout the reader does
# not model answers None and Git is asked instead.
# ---------------------------------------------------------------------------


def discover(cwd):
    """The repository that holds ``cwd``, or None when Git has to answer."""

    return layout.discover(Path(cwd)) if layout is not None else None


def worktree_root(cwd):
    """The work tree that holds ``cwd``, or None when Git has to answer.

    The facts of this module are facts about a working tree.  A directory
    without one - a bare repository - has none, so its questions are left to
    Git.
    """

    return layout.worktree_root(Path(cwd)) if layout is not None else None


def _facts_are_on_disk():
    """Whether the facts of this module are the facts Git would read.

    Some environment variables move the index, the objects or the
    configuration of Git away from the working tree.  The facts below are
    read from the disk, so they are the facts of Git only while the
    environment keeps Git on the disk.
    """

    return not any(os.environ.get(name) for name in _FACT_ENVIRONMENT_OVERRIDES)


# ---------------------------------------------------------------------------
# HEAD
# ---------------------------------------------------------------------------


def _read_ref(repo, name):
    """The raw content of one reference, or None when it does not exist."""
    for base in (repo.gitdir, repo.common):
        text = _read_text(Path(base) / name)
        if text is not None:
            return text.strip()
    packed = _read_text(Path(repo.common) / "packed-refs")
    if packed is None:
        return None
    for line in packed.splitlines():
        if not line or line[0] in "#^":
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1].strip() == name:
            return parts[0].strip()
    return None


def _object_exists(repo, sha):
    """Whether the object of a commit is on disk.

    A loose object is a plain file; a packed one lives in a pack file.  When
    neither is there the commit cannot be read and Git would refuse it.
    """
    objects = Path(repo.common) / "objects"
    loose = objects / sha[:2] / sha[2:]
    if loose.exists():
        return True
    pack = objects / "pack"
    try:
        return any(pack.glob("*.pack"))
    except OSError:
        return False


def head_sha(repo):
    """The commit of HEAD.

    Returns the empty string when HEAD has no commit yet, which is what
    `git rev-parse --verify HEAD` reports for an unborn branch, and None
    when the answer is not certain and Git has to give it.
    """
    text = _read_text(Path(repo.gitdir) / "HEAD")
    if text is None:
        return None
    return _resolve_ref(repo, text.strip(), 0)


def _resolve_ref(repo, text, depth):
    if depth > 5:
        return None
    if text.startswith("ref:"):
        name = text[4:].strip()
        if not name.startswith("refs/"):
            return None
        value = _read_ref(repo, name)
        if value is None:
            # The branch has no commit yet: Git refuses HEAD the same way.
            return ""
        if not value:
            return None
        return _resolve_ref(repo, value, depth + 1)
    if not _SHA.match(text):
        return None
    if not _object_exists(repo, text):
        return None
    return text


def head_token(repo):
    """The observable stamp of HEAD and of the reference it points at."""
    tokens = [_stat(Path(repo.gitdir) / "HEAD")]
    text = _read_text(Path(repo.gitdir) / "HEAD") or ""
    if text.startswith("ref:"):
        name = text[4:].strip()
        tokens.append(_stat(Path(repo.gitdir) / name))
        tokens.append(_stat(Path(repo.common) / name))
    tokens.append(_stat(Path(repo.common) / "packed-refs"))
    return tuple(tokens)


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------


def _index_entries(repo):
    """The entries of the index of the repository.

    Every entry carries the mode and the object id of the file it names and
    the stat of that file when the index was written.  The paths keep the
    bytes of the index, so a path Git would spell in another encoding is
    still the path of the index.

    Returns None when the index is not a shape this module reads, so that
    Git answers instead.
    """
    key = repo.key
    stamp = _stat(Path(repo.gitdir) / "index")
    cached = _INDEXES.get(key)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    data = _read_bytes(Path(repo.gitdir) / "index")
    if data is None:
        # A repository without an index has no tracked file at all, which is
        # what `git ls-files` reports for it.
        if stamp is None:
            _INDEXES[key] = (stamp, {})
            return {}
        return None
    if len(data) < 12 or data[:4] != b"DIRC":
        return None
    version = int.from_bytes(data[4:8], "big")
    if version not in (2, 3):
        return None
    count = int.from_bytes(data[8:12], "big")
    offset = 12
    entries = {}
    for _ in range(count):
        start = offset
        if start + 62 > len(data):
            return None
        flags = int.from_bytes(data[start + 60:start + 62], "big")
        if (flags >> 12) & 0x3:
            return None  # an unmerged path: Git lists it once per stage
        if flags & 0x8000:
            return None  # an assumed unchanged path: Git does not read it
        base = 62
        if flags & 0x4000:
            if version < 3:
                return None
            base = 64
            if int.from_bytes(data[start + 62:start + 64], "big"):
                # Skip-worktree and intent-to-add change what Git compares.
                return None
        offset = start + base
        length = flags & 0xFFF
        if length < 0xFFF:
            end = offset + length
        else:
            end = data.find(b"\0", offset)
            if end < 0:
                return None
        if end >= len(data) or data[end:end + 1] != b"\0":
            return None
        name = data[offset:end]
        if not name or b"\0" in name or name.startswith(b"/"):
            return None
        mode = int.from_bytes(data[start + 24:start + 28], "big")
        if mode & 0o170000 == 0o160000:
            return None  # a submodule: its content is another repository
        entries[name] = (
            mode,
            data[start + 40:start + 60].hex(),
            (
                int.from_bytes(data[start + 8:start + 12], "big"),
                int.from_bytes(data[start + 12:start + 16], "big"),
                int.from_bytes(data[start + 0:start + 4], "big"),
                int.from_bytes(data[start + 4:start + 8], "big"),
                int.from_bytes(data[start + 20:start + 24], "big"),
                int.from_bytes(data[start + 28:start + 32], "big"),
                int.from_bytes(data[start + 32:start + 36], "big"),
                int.from_bytes(data[start + 36:start + 40], "big"),
            ),
        )
        # Every entry is padded with NULs to a multiple of eight bytes.
        offset = start + ((base + length + 8) & ~7)
    if len(entries) != count or list(entries) != sorted(entries):
        return None  # the entries did not add up: Git has to answer
    if _has_unsafe_extension(data, offset):
        return None
    _INDEXES[key] = (stamp, entries)
    _trim_cache(_INDEXES)
    return entries


def _index_paths(repo):
    """The tracked paths of the repository, root relative.

    Returns None when the index is not a shape this module reads, so that
    Git answers instead.
    """
    entries = _index_entries(repo)
    if entries is None:
        return None
    return [os.fsdecode(name) for name in entries]


def _has_unsafe_extension(data, offset):
    """Whether the index carries an extension this module cannot honour."""
    if offset + 4 > len(data) or data[offset:offset + 4] == b"\0\0\0\0":
        return False
    position = offset
    while position + 8 <= len(data):
        signature = data[position:position + 4]
        size = int.from_bytes(data[position + 4:position + 8], "big")
        if signature in (b"link", b"sdir"):
            return True
        position += 8 + size
    return False


def tracked_paths(repo, cwd):
    """The tracked files of the repository, relative to ``cwd``.

    `git ls-files` lists the files under the current directory and prints
    them relative to it; this is the same list.
    """
    paths = _index_paths(repo)
    if paths is None:
        return None
    prefix = _prefix(repo.root, cwd)
    if prefix is None:
        return None
    if not prefix:
        return list(paths)
    marker = prefix + "/"
    return [path[len(marker):] for path in paths if path.startswith(marker)]


def _prefix(root, cwd):
    """The path of ``cwd`` inside ``root``, or None when it is outside."""
    try:
        relative = Path(cwd).resolve().relative_to(root)
    except (OSError, ValueError):
        return None
    return "" if str(relative) == "." else relative.as_posix()


def _relative(root, path):
    """The path of ``path`` inside ``root``, without resolving symlinks."""
    try:
        return Path(path).relative_to(root).as_posix()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# The ignore rules
# ---------------------------------------------------------------------------


def _compile_pattern(line):
    """One gitignore pattern, or None when the line carries none."""
    if not line.strip():
        return None
    line = re.sub(r"(?<!\\)[ \t]+$", "", line)
    if not line or line.startswith("#"):
        return None
    negated = line.startswith("!")
    if negated:
        line = line[1:]
    directory_only = line.endswith("/")
    if directory_only:
        line = line[:-1]
    if not line:
        return None
    anchored = "/" in line
    if line.startswith("/"):
        line = line[1:]
        anchored = True
    if not line:
        return None
    return (_pattern_regex(line, anchored), negated, directory_only)


def _pattern_regex(pattern, anchored):
    """The regular expression one gitignore pattern stands for."""
    body = []
    index = 0
    length = len(pattern)
    while index < length:
        char = pattern[index]
        if char == "\\":
            # A backslash quotes the next character, a space at the end of
            # a pattern included.
            index += 1
            if index < length:
                body.append(re.escape(pattern[index]))
                index += 1
            continue
        if char == "*":
            if pattern[index:index + 3] == "**/":
                body.append("(?:.*/)?")
                index += 3
                continue
            if pattern[index:index + 2] == "**":
                body.append(".*")
                index += 2
                continue
            body.append("[^/]*")
            index += 1
            continue
        if char == "?":
            body.append("[^/]")
            index += 1
            continue
        if char == "[":
            end = index + 1
            if end < length and pattern[end] in "!^":
                end += 1
            if end < length and pattern[end] == "]":
                end += 1
            while end < length and pattern[end] != "]":
                end += 1
            if end >= length:
                body.append(re.escape("["))
                index += 1
                continue
            inner = pattern[index + 1:end]
            if inner.startswith("!"):
                inner = "^" + inner[1:]
            body.append("[" + inner.replace("\\", "\\\\") + "]")
            index = end + 1
            continue
        body.append(re.escape(char))
        index += 1
    prefix = "" if anchored else "(?:.*/)?"
    return re.compile("^" + prefix + "".join(body) + "$")


def _read_ignore_file(path, base=None):
    """The patterns of one ignore file, in file order, with their base.

    A pattern of a `.gitignore` file is relative to the directory that file
    sits in, so every rule carries that directory with it.  The patterns of
    the exclude files are relative to the root of the repository instead.
    """
    text = _read_text(path)
    if text is None:
        return []
    rules = []
    base = Path(base) if base is not None else Path(path).parent
    for line in text.splitlines():
        rule = _compile_pattern(line)
        if rule is not None:
            rules.append((base, rule[0], rule[1], rule[2]))
    return rules


def _config_values(path, section, key):
    """Every value of one key of one section of a Git config file."""
    text = _read_text(path)
    if text is None:
        return None
    found = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("["):
            end = line.find("]")
            if end < 0:
                current = None
                continue
            current = line[1:end].strip()
            continue
        if current != section:
            continue
        name, _, value = line.partition("=")
        if name.strip().lower() == key.lower():
            found.append(value.strip().strip('"'))
    return found


def _config_sections(path):
    """Every section name of a Git config file."""
    text = _read_text(path)
    if text is None:
        return []
    sections = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            sections.append(line[1:-1].strip())
    return sections


def _global_config_paths():
    """The config files Git reads outside the repository.

    In the order Git reads them: the later file has the stronger say.
    """
    home = Path.home()
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
    return [Path("/etc/gitconfig"), Path(xdg) / "git" / "config", home / ".gitconfig"]


def _repository_rules(repo):
    """The ignore rules that hold for the whole repository.

    The order is the order of precedence: a pattern that is read later wins.
    The per-directory `.gitignore` files are added while the tree is walked,
    because a deeper file has the stronger say.
    """
    paths = [repo.common / "config"]
    paths.extend(_global_config_paths())
    for path in paths:
        for section in _config_sections(path):
            if section == "include" or section.startswith("include "):
                return None  # an include may hide a rule this module cannot see
        values = _config_values(path, "core", "excludesfile")
        if values:
            return None  # Git reads an ignore file this module does not know
    rules = []
    excludes = os.environ.get("XDG_CONFIG_HOME")
    default = Path(excludes) / "git" / "ignore" if excludes else Path.home() / ".config" / "git" / "ignore"
    rules.extend(_read_ignore_file(default, repo.root))
    rules.extend(_read_ignore_file(Path(repo.common) / "info" / "exclude", repo.root))
    return rules


def _ignored(rules, path, is_directory):
    """Whether the last matching rule excludes the path.

    Every rule is matched against the path relative to the directory its
    own file sits in, which is how Git reads a pattern.
    """
    excluded = False
    for base, regex, negated, directory_only in rules:
        relative = _relative(base, path)
        if relative is None:
            continue
        if directory_only and not is_directory:
            continue
        if regex.match(relative):
            excluded = not negated
    return excluded


# ---------------------------------------------------------------------------
# The working tree
# ---------------------------------------------------------------------------


def _embedded_repository(path):
    """Whether a directory holds a repository of its own."""
    return (path / ".git").exists()


def untracked_paths(repo, cwd):
    """The untracked, non-ignored files under ``cwd``, relative to it.

    This is the list `git ls-files --others --exclude-standard` prints.
    """
    base_rules = _repository_rules(repo)
    if base_rules is None:
        return None
    tracked = _index_paths(repo)
    if tracked is None:
        return None
    tracked = set(tracked)
    try:
        start = Path(cwd).resolve()
    except OSError:
        return None
    if start != repo.root and repo.root not in start.parents:
        return None
    chain = []
    current = start
    while True:
        chain.append(current)
        if current == repo.root:
            break
        current = current.parent
    chain.reverse()
    rules = list(base_rules)
    for directory in chain:
        if directory != start and _ignored(rules, directory, True):
            # Git does not descend into an excluded directory.
            return []
        rules.extend(_read_ignore_file(directory / ".gitignore"))
        if directory == start:
            break
    found = []
    _walk(repo, start, rules, tracked, found)
    prefix = _prefix(repo.root, start)
    if prefix is None:
        return None
    if not prefix:
        return sorted(found)
    marker = prefix + "/"
    return sorted(path[len(marker):] for path in found if path.startswith(marker))


def _walk(repo, directory, rules, tracked, found):
    """Collect the untracked files of one directory and its subdirectories."""
    try:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
    except OSError:
        return
    for entry in entries:
        path = Path(entry.path)
        if directory == repo.root and entry.name == ".git":
            # The repository keeps its own bookkeeping out of the listing.
            continue
        relative = _relative(repo.root, path)
        if relative is None:
            continue
        try:
            is_directory = entry.is_dir(follow_symlinks=False)
        except OSError:
            continue
        if _ignored(rules, path, is_directory):
            continue
        if relative in tracked:
            continue
        if is_directory:
            if _embedded_repository(path):
                # An embedded repository is one entry, with its own slash.
                found.append(relative + "/")
                continue
            nested = list(rules)
            nested.extend(_read_ignore_file(path / ".gitignore"))
            _walk(repo, path, nested, tracked, found)
            continue
        found.append(relative)


# ---------------------------------------------------------------------------
# The changed paths
# ---------------------------------------------------------------------------


def _tracked_state(repo):
    """The stat of every tracked file, the signal Git's index relies on."""
    paths = _index_paths(repo)
    if paths is None:
        return None
    return tuple((path, _stat(Path(repo.root) / path)) for path in paths)


def _changed_token(repo, head):
    """The observable stamp of everything a diff against ``head`` depends on.

    The index holds the staged state, HEAD holds the revision and the stat
    of every tracked file holds the working tree.  A change in any of them
    changes the answer, and each of them is visible without a process.
    """
    return (_stat(Path(repo.gitdir) / "index"), head_token(repo), _tracked_state(repo))


def changed_paths(repo, head):
    """The paths that differ between the working tree and ``head``.

    Returns the token the answer belongs to together with the answer, or
    None when the answer has to be computed by Git.  A cached answer is
    reused only while the token is the one it was computed for, so a moved
    HEAD, a staged change and a changed, added or removed file all end the
    reuse.
    """
    token = _changed_token(repo, head)
    if token is None:
        return None
    cached = _CHANGED.get((repo.key, head))
    if cached is not None and cached[0] == token:
        return token, cached[1]
    return token, None


# ---------------------------------------------------------------------------
# The comparison of the working tree
#
# Git answers "which paths differ" by comparing three states it keeps on
# disk: the tree of a revision, the index and the files of the working
# tree.  All three are read here, so the comparison starts no process.
#
# The answer is exact or it is not given at all.  A shape whose answer
# cannot be reproduced byte for byte - a submodule, a conversion of the
# content, a rename Git would pair, a revision this module cannot resolve
# - leaves the question to Git, so the answer stays the answer of Git.
# ---------------------------------------------------------------------------


# The settings of the configuration this module reads for a repository.
_CONFIG_KEYS = (("core", "autocrlf"), ("core", "filemode"), ("core", "symlinks"),
                ("core", "attributesfile"), ("extensions", "objectformat"))


def _repository_config(repo):
    """The settings of the configuration Git reads for this repository.

    None when a configuration file includes another one: the included file
    may hold a setting this module cannot see, and then only Git knows it.
    """
    paths = [Path(repo.common) / "config", *_global_config_paths()]
    worktree = Path(repo.gitdir) / "config.worktree"
    try:
        if worktree.exists():
            paths.append(worktree)
    except OSError:
        pass
    values = {}
    for path in paths:
        sections = _config_sections(path)
        for name in sections:
            if name == "include" or name.startswith("include "):
                return None
        for section, key in _CONFIG_KEYS:
            found = _config_values(path, section, key)
            if found:
                values[(section, key)] = found[-1]
    return values


def _tree_entries(repo, commit):
    """The paths of one revision with their mode and their object id.

    None when the tree cannot be read, so that Git answers instead.
    """
    if facts is None or not _SHA.match(commit or ""):
        return None
    tree = facts.tree_entries(repo, commit)
    if tree is None:
        return None
    return {os.fsencode(path): (mode, sha) for path, (mode, sha) in tree.items()}


def _stat_matches(data, info):
    """Whether the file on disk is the file the index recorded.

    The same fields Git compares: the times of the file, its owner, its
    number and its size.
    """
    (mtime_sec, mtime_nsec, ctime_sec, ctime_nsec, ino, uid, gid, size) = data
    return (mtime_sec == info.st_mtime_ns // 1000000000
            and mtime_nsec == info.st_mtime_ns % 1000000000
            and ctime_sec == info.st_ctime_ns // 1000000000
            and ctime_nsec == info.st_ctime_ns % 1000000000
            and ino == info.st_ino
            and uid == info.st_uid
            and gid == info.st_gid
            and size == info.st_size)


def _is_racy(entry, index_stamp):
    """Whether the entry of the index may be older than the file it names.

    Git writes the index after the files it records.  An entry that is not
    older than the index itself may hide a change of the same second, so
    Git reads the content of such a file again instead of trusting the
    entry.
    """
    if index_stamp is None:
        return True
    index_sec = index_stamp[0] // 1000000000
    index_nsec = index_stamp[0] % 1000000000
    return entry[0] >= index_sec and entry[1] >= index_nsec


def _conversions_may_apply(repo, name, config):
    """Whether Git may convert the content of one file before comparing it.

    Git converts the content of a file with the rules of the attribute
    files and of core.autocrlf before it compares the file with the blob
    of the tree.  Then the bytes of the file are not the bytes of the
    blob, and only Git can say what the comparison is.
    """
    if config.get(("core", "autocrlf"), "false").lower() == "true":
        # Git converts the line endings of the content before it compares it.
        return True
    if config.get(("core", "attributesfile")) is not None:
        return True
    if (Path(repo.common) / "info" / "attributes").exists():
        return True
    home = Path.home()
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
    if (Path(xdg) / "git" / "attributes").exists() or (home / ".gitattributes").exists():
        return True
    directory = repo.root
    for part in os.fsdecode(name).split("/")[:-1]:
        directory = directory / part
        if (directory / ".gitattributes").exists():
            return True
    return (repo.root / ".gitattributes").exists()


def _blob_id(data, width):
    """The object id Git gives to a content."""
    header = b"blob %d\0" % len(data)
    if width == 32:
        return hashlib.sha256(header + data).hexdigest()
    return hashlib.sha1(header + data).hexdigest()


def _worktree_state(repo, name, entry, racy, config):
    """The state of one file of the working tree.

    The state is the mode and the object id of the content of the file, the
    way the index records them.  None when the file cannot be read the way
    Git reads it, so that Git answers instead.
    """
    full = Path(repo.root) / os.fsdecode(name)
    try:
        info = os.lstat(full)
    except OSError:
        return False, 0, ""
    if stat.S_ISLNK(info.st_mode):
        try:
            target = os.readlink(full)
        except OSError:
            return None
        return True, 0o120000, _blob_id(os.fsencode(target), _object_width(config))
    if not stat.S_ISREG(info.st_mode):
        return None
    fresh = 0o100000 | (0o755 if info.st_mode & stat.S_IXUSR else 0o644)
    if entry is not None and not racy and _stat_matches(entry[2], info):
        # The file is the one the index recorded, so its content is the
        # blob the index names.
        return True, entry[0], entry[1]
    if _conversions_may_apply(repo, name, config):
        return None
    try:
        data = full.read_bytes()
    except OSError:
        return None
    if config.get(("core", "filemode"), "true").lower() == "false":
        # Git does not read the permission of a file when it is told not to.
        fresh = (fresh & 0o170000) | (entry[0] & 0o777) if entry else fresh
    return True, fresh, _blob_id(data, _object_width(config))


def _object_width(config):
    """The length of an object id of this repository."""
    return 32 if config.get(("extensions", "objectformat")) == "sha256" else 20


def _diff_against_tree(repo, tree, entries, config):
    """The paths that differ between a tree and the working tree.

    None when the answer is not certain, so that Git answers instead.
    """
    if config.get(("core", "symlinks"), "true").lower() == "false":
        return None  # Git reads a symlink as a file: only Git can say what it sees
    index_stamp = _stat(Path(repo.gitdir) / "index")
    changed = []
    deleted = []
    added = []
    for name in sorted(set(tree) | set(entries)):
        entry = entries.get(name)
        tree_entry = tree.get(name)
        if tree_entry is None:
            if entry is None:
                continue  # a path neither the tree nor the index names
            state = _worktree_state(repo, name, entry, _is_racy(entry[2], index_stamp), config)
            if state is None:
                return None
            if state[0]:
                changed.append(name)
                added.append(name)
            continue
        if entry is None:
            # The index does not name the path, so the file is gone from
            # the working tree as far as Git is concerned.
            changed.append(name)
            deleted.append(name)
            continue
        state = _worktree_state(repo, name, entry, _is_racy(entry[2], index_stamp), config)
        if state is None:
            return None
        exists, mode, sha = state
        if not exists:
            changed.append(name)
            deleted.append(name)
            continue
        if mode != tree_entry[0] or sha != tree_entry[1]:
            changed.append(name)
    if deleted and added:
        # Git pairs a deleted path with an added one when their content is
        # similar, and then the listing names the new path alone.  Which
        # pair Git picks is Git's own decision, so Git answers the question.
        return None
    return changed


def _diff_between_trees(before, after):
    """The paths that differ between two trees, or None.

    None when Git would pair a deleted path with an added one, because
    then the listing names the new path alone.
    """
    deleted = set(before) - set(after)
    added = set(after) - set(before)
    if deleted and added:
        return None
    return [name for name in sorted(set(before) | set(after))
            if before.get(name) != after.get(name)]


def _diff_against_index(tree, entries):
    """The paths that differ between a tree and the index, or None."""
    after = {name: (entry[0], entry[1]) for name, entry in entries.items()}
    return _diff_between_trees(tree, after)


def _diff_paths(repo, commit):
    """The paths that differ between the working tree and one revision.

    The answer is the one ``git diff --name-only -z <commit>`` gives.
    None when the answer is not certain, so that Git answers instead.
    """
    tree = _tree_entries(repo, commit)
    if tree is None:
        return None
    entries = _index_entries(repo)
    if entries is None:
        return None
    config = _repository_config(repo)
    if config is None:
        return None
    return _diff_against_tree(repo, tree, entries, config)


def _diff_index_paths(repo):
    """The paths that differ between the working tree and the index."""
    entries = _index_entries(repo)
    if entries is None:
        return None
    config = _repository_config(repo)
    if config is None:
        return None
    if config.get(("core", "symlinks"), "true").lower() == "false":
        return None
    index_stamp = _stat(Path(repo.gitdir) / "index")
    changed = []
    for name in sorted(entries):
        entry = entries[name]
        state = _worktree_state(repo, name, entry, _is_racy(entry[2], index_stamp), config)
        if state is None:
            return None
        exists, mode, sha = state
        if not exists or mode != entry[0] or sha != entry[1]:
            changed.append(name)
    return changed


def _diff_cached_paths(repo, commit):
    """The paths that differ between the index and one revision."""
    tree = _tree_entries(repo, commit)
    if tree is None:
        return None
    entries = _index_entries(repo)
    if entries is None:
        return None
    return _diff_against_index(tree, entries)


def _diff_revision_paths(repo, base, commit):
    """The paths that differ between two revisions."""
    before = _tree_entries(repo, base)
    if before is None:
        return None
    after = _tree_entries(repo, commit)
    if after is None:
        return None
    return _diff_between_trees(before, after)


# ---------------------------------------------------------------------------
# The remotes
# ---------------------------------------------------------------------------


def remote_url(repo, name):
    """The URL of one remote, or None when Git has to answer."""
    key = (repo.key, name)
    configs = [Path(repo.common) / "config", *_global_config_paths()]
    stamp = tuple(_stat(path) for path in configs)
    cached = _REMOTES.get(key)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    for path in configs:
        for section in _config_sections(path):
            if section.startswith("url ") and _config_values(path, section, "insteadof"):
                # Git rewrites the URL on the way out; Git has to answer.
                return None
    section = 'remote "%s"' % name
    values = _config_values(configs[0], section, "url")
    if values is None:
        return None
    if not values:
        # A remote may also be named in the config outside the repository.
        for path in configs[1:]:
            found = _config_values(path, section, "url")
            if found:
                values = found
    url = values[0] if values else ""
    _REMOTES[key] = (stamp, url)
    _trim_cache(_REMOTES)
    return url


# ---------------------------------------------------------------------------
# The answers the observer asks for
# ---------------------------------------------------------------------------


def _as_bytes(paths):
    return b"".join(path.encode("utf-8", errors="replace") + b"\0" for path in paths)


def _revision(repo, name):
    """The commit one revision names, or None when Git has to answer."""
    if _SHA.match(name or ""):
        return name
    if name == "HEAD":
        return head_sha(repo) or None
    return None


def _diff_answer(repo, args):
    """The answer of one question about the changed paths, or None.

    The question is the one ``git diff`` asks with ``--name-only``: which
    paths differ.  The revision, the index and the working tree are read
    from disk, so the answer starts no process.
    """
    if args[0] != "diff" or "--name-only" not in args:
        return None
    if "-z" not in args:
        # Without -z Git spells a path it cannot print as it is, so the
        # listing is not the listing of this module.
        return None
    cached = "--cached" in args
    rest = [item for item in args[1:] if item not in ("--name-only", "-z", "--cached")]
    if any(item.startswith("--") for item in rest):
        return None  # an option this module does not model
    if not rest:
        if cached:
            commit = _revision(repo, "HEAD")
            if commit is None:
                return None
            paths = _diff_cached_paths(repo, commit)
        else:
            paths = _diff_index_paths(repo)
    elif len(rest) == 1:
        commit = _revision(repo, rest[0])
        if commit is None:
            return None
        paths = _diff_cached_paths(repo, commit) if cached else _diff_paths(repo, commit)
    elif len(rest) == 2:
        base = _revision(repo, rest[0])
        commit = _revision(repo, rest[1])
        if base is None or commit is None:
            return None
        paths = _diff_revision_paths(repo, base, commit)
    else:
        return None
    if paths is None:
        return None
    return b"".join(path + b"\0" for path in paths)


def answer(cwd, args):
    """The answer to one Git question, read from disk when it is safe.

    Returns None when the question is not one this module reads, so that
    the caller asks Git.
    """
    if not _facts_are_on_disk():
        return None
    repo = discover(cwd)
    if repo is None:
        return None
    if args[:3] == ("rev-parse", "--verify", "HEAD"):
        sha = head_sha(repo)
        if sha is None:
            return None
        # A repository without a commit has no revision, and Git refuses it
        # with no output at all.
        return (sha + "\n").encode() if sha else b""
    if args[:2] == ("rev-parse", "--show-toplevel"):
        root = worktree_root(cwd)
        if root is None:
            return None
        return str(root).encode() + b"\n"
    if len(args) == 3 and args[:2] == ("remote", "get-url"):
        url = remote_url(repo, args[2])
        if url is None:
            return None
        return url.encode() + b"\n"
    if args and args[0] == "diff":
        if worktree_root(cwd) is None:
            # A directory without a work tree has no diff to read.
            return None
        return _diff_answer(repo, args)
    return None


def candidate_paths(cwd, head):
    """The changed and untracked paths of ``cwd``, as Git would list them.

    Returns None when this module cannot answer, so that the caller asks
    Git the way it always did.
    """
    if not _facts_are_on_disk():
        return None
    if worktree_root(cwd) is None:
        # A directory without a work tree has no paths to list.
        return None
    repo = discover(cwd)
    if repo is None:
        return None
    tracked = tracked_paths(repo, cwd)
    if tracked is None:
        return None
    untracked = untracked_paths(repo, cwd)
    if untracked is None:
        return None
    if head:
        answer = changed_paths(repo, head)
        if answer is None:
            return None
        token, changed = answer
        if changed is None:
            paths = _diff_paths(repo, head)
            if paths is None:
                changed = [path for path in
                           git(cwd, "diff", "--name-only", "-z", head).decode("utf-8", errors="replace").split("\0")
                           if path]
            else:
                changed = [os.fsdecode(path) for path in paths]
            _CHANGED[(repo.key, head)] = (token, changed)
            _trim_cache(_CHANGED)
        return _as_bytes(changed) + _as_bytes(untracked)
    return _as_bytes(tracked) + _as_bytes(untracked)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

def minor(goal):
    return bool(SMALL.search(goal) and not re.search(r"\b(?:full|complete|major|entire)\b|полност|целиком|крупн", goal, re.I))

def task_flags(goal):
    # Intent must describe an action on a user surface in the same human
    # sentence. A quoted workflow requirement elsewhere is not a UI assignment.
    sentences = re.split(r"\n|(?<=\.)\s+", goal)
    expected = any(SURFACE.search(s) and BUILD.search(s) and not minor(s) for s in sentences)
    first = sentences[0] if sentences else ""
    explicit = bool(SURFACE.search(first) and ACCEPT.search(first))
    return bool(expected or explicit), explicit

def read(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("raw source exceeds bounded native window")
    return data

def git(cwd, *args):
    # The facts Git keeps on disk are read from disk; Git itself answers
    # everything this module cannot read exactly.
    value = answer(cwd, args)
    if value is not None:
        return value
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, timeout=2)
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("Git surface exceeds bounded window")
    return result.stdout if result.returncode == 0 else b""

def candidates(cwd, head):
    # The changed and the untracked paths are facts about the working tree.
    # They are read from the repository's own state; Git is asked only when
    # that state is not a shape the reader knows.
    paths = candidate_paths(cwd, head)
    if paths is None:
        paths = git(cwd, "diff", "--name-only", "-z", head) if head else git(cwd, "ls-files", "-z")
        paths += git(cwd, "ls-files", "--others", "--exclude-standard", "-z")
    result = []
    for raw in sorted(set(paths.split(b"\0"))):
        if not raw:
            continue
        p = raw.decode()
        if set(Path(p).parts) & {"tests", "test", "__tests__", ".tmp", ".agents", "node_modules"} or re.search(r"(?:^|/)(?:test_|.*\.test\.)", p):
            continue
        if UI.search(p):
            result.append(p)
        elif GENERATED_UI.search(p):
            path = (cwd / p).resolve()
            path.relative_to(cwd)
            data = read(path) if path.is_file() else git(cwd, "show", head + ":" + p)
            if re.search(rb"<(?:!doctype|html|main|body|form|button|input|div)\b|(?:React\.createElement|render_template)\(", data, re.I):
                result.append(p)
    if len(result) > 256:
        raise ValueError("more than 256 changed UI paths; narrow the milestone")
    return result

def file_hash(cwd, name):
    path = (cwd / name).resolve()
    path.relative_to(cwd)
    return digest(read(path)) if path.is_file() else "deleted"

def content(parts):
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        return "\n".join(str(x.get("text", "")) for x in parts if isinstance(x, dict))
    return ""

def native_transcript(data):
    """Codex native JSONL. Unknown/partial formats fail pending, never PASS."""
    rows = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    meta = next((r["payload"] for r in rows if r.get("type") == "session_meta"), {})
    messages, calls, observations = [], {}, []
    for row in rows:
        p = row.get("payload", {})
        if row.get("type") == "event_msg" and p.get("type") == "item_completed":
            item = p.get("item", {})
            if item.get("type") == "CommandExecution" and isinstance(item.get("exit_code"), int):
                command = item.get("command", [])
                if isinstance(command, list) and len(command) >= 3:
                    observations.append(({"name": "exec_command", "call_id": item.get("id"), "_exit_code": item['exit_code'], "arguments": json.dumps({"cmd": command[-1], "workdir": item.get("cwd")})},
                                         str(item.get("aggregated_output") or "")))
        if row.get("type") != "response_item":
            continue
        kind = p.get("type", "")
        if kind == "message" and p.get("role") in {"user", "assistant"}:
            text = content(p.get("content"))
            if not text.startswith(("# AGENTS.md instructions", "<environment_context>")):
                messages.append((p["role"], text, p.get("phase")))
        elif kind in {"function_call", "custom_tool_call"}:
            calls[p.get("call_id")] = p
        elif kind in {"function_call_output", "custom_tool_call_output"}:
            call = calls.get(p.get("call_id"), {})
            observations.append((call, content(p.get("output"))))
    return meta, messages, observations

def first_goal(event, state):
    business = state.get("business", {})
    goal = business.get("original_prompt") or event.get("prompt")
    latest = business.get("latest_prompt") or ""
    if latest and not latest.startswith("🤖") and task_flags(latest)[0]:
        goal = latest
    if not goal and event.get("transcript_path"):
        try:
            _, messages, _ = native_transcript(read(event["transcript_path"]))
            goal = next((text for role, text, _ in messages if role == "user"), "")
        except (OSError, ValueError, StopIteration):
            pass
    # OpenCode's canonical context hook can bootstrap an already open thread.
    if not goal:
        goal = next((content(m.get("content")) for m in event.get("messages", [])
                     if isinstance(m, dict) and m.get("role") == "user"), "")
    return goal if isinstance(goal, str) else ""

def observe(state, event, name, cwd, session, now):
    milestone = state.get("milestone")
    goal = first_goal(event, state)
    human_prompt = str(event.get("prompt") or "") if name == "UserPromptSubmit" and not event.get("_lhc_control_prompt") else ""
    # A later human can start a UI outcome in an existing non-UI session. Status,
    # corrections and peer envelopes do not replace its accepted assignment.
    new_ui_task = bool(human_prompt and not human_prompt.startswith("🤖") and SURFACE.search(human_prompt)
                       and (BUILD.search(human_prompt) or re.search(r"\b(?:fix|adjust|change)\b|исправ|поправ", human_prompt, re.I) or ACCEPT.search(human_prompt))
                       and (not milestone or human_prompt != milestone["goal"]))
    if new_ui_task and milestone and milestone.get("hold") in {"Interrupt", "SessionEnd", "session.error"}:
        import lhc_outcome
        import lhc_time_guard
        business = state.get("business", {})
        active_prompts = [business.get("latest_prompt_full") or business.get("latest_prompt") or "",
                          business.get("original_prompt_full") or business.get("original_prompt") or "",
                          milestone.get("goal") or ""]
        if not lhc_time_guard.prompt_can_resume_hold(
                human_prompt, active_prompts, hold=milestone.get("hold"),
                origin=lhc_outcome.source_origin(human_prompt)):
            new_ui_task = False
    if new_ui_task and milestone:
        if pending(milestone):
            if human_prompt not in milestone["goal"]:
                milestone["goal"] = (milestone["goal"] + "\n" + human_prompt)[-8192:]
        else:
            milestone = None
            goal = human_prompt
    if not milestone and goal:
        head = git(cwd, "rev-parse", "--verify", "HEAD").decode().strip()
        baseline = {p: file_hash(cwd, p) for p in candidates(cwd, head)} if name == "UserPromptSubmit" else {}
        milestone = state["milestone"] = {
            "task": digest(session + "\n" + goal)[:20], "goal": goal[:4096],
            "started_at": now.isoformat(), "head": head, "baseline": baseline,
            "expected": task_flags(goal)[0], "explicit": task_flags(goal)[1],
            "read_only": bool(READ_ONLY.search(goal[:500])), "cwd": str(cwd),
            "status": "not-required", "surface": {}, "sources": [], "feedback": [],
        }
    if not milestone:
        return None
    if name == "PostToolUse":
        # export_transcript returns a navigation card, often outside product CWD:
        # Herder's MCP-process workspace owns the archive. Persist its exact path.
        for text in response_texts(event.get("tool_response")):
            for match in re.finditer(r"Lineage manifest:\s*([^\r\n]+\.manifest\.json)", text):
                path = match[1].strip()
                if Path(path).is_absolute() and path not in milestone["sources"]:
                    milestone["sources"] = (milestone["sources"] + [path])[-16:]
    if name in {"Interrupt", "SessionEnd", "PermissionRequest", "session.error", "ToolFailure"}:
        milestone["hold"] = name
    elif name == "UserPromptSubmit" and not event.get("_lhc_control_prompt") and milestone.get("hold") != "PermissionRequest":
        raw_prompt = str(event.get("prompt") or event.get("text") or "")
        import lhc_outcome
        import lhc_time_guard
        origin = lhc_outcome.source_origin(raw_prompt)
        business = state.get("business", {})
        active_prompts = event.get("_lhc_previous_active_prompts") or [
            business.get("latest_prompt_full") or business.get("latest_prompt") or "",
            business.get("original_prompt_full") or business.get("original_prompt") or "",
            milestone.get("goal") or "",
        ]
        if lhc_time_guard.prompt_can_resume_hold(raw_prompt, active_prompts,
                                                hold=milestone.get("hold"), origin=origin):
            milestone.pop("hold", None)
    elif name == "permission.replied" and milestone.get("hold") == "PermissionRequest":
        milestone.pop("hold", None)
    elif name == "PostToolUseFailure" or (name == "PostToolUse" and tool_failed(event)):
        scoped = scoped_surface_failure(event) if name == "PostToolUse" else None
        if not scoped:
            milestone["hold"] = "ToolFailure"
    elif name == "PostToolUse" and milestone.get("hold") in {"ToolFailure", "PermissionRequest"}:
        milestone.pop("hold", None)
    if milestone["read_only"]:
        return milestone
    # Deployment/start URL belongs to the current runnable task, not necessarily
    # the user's first sentence. Read this existing small project note only.
    urls = URL.findall(milestone["goal"])
    local_run = cwd / "LOCAL_RUN.md"
    if not urls and local_run.is_file() and not local_run.is_symlink():
        urls = URL.findall(read(local_run).decode())
    milestone["urls"] = urls
    # Reconcile observable repository changes, never keywords in tool stdout.
    surface = {}
    owned = set(state.get("business", {}).get("outcome", {}).get("owned_paths", []))
    changed = set(candidates(cwd, milestone["head"])) | set(milestone["surface"])
    for p in sorted(changed & owned if owned else changed):
        value = file_hash(cwd, p)
        original = milestone["baseline"].get(p)
        if original is None:
            old = git(cwd, "show", milestone["head"] + ":" + p) if milestone["head"] else b""
            original = digest(old)
        if value != original:
            surface[p] = value
    # A broad implementation with several UI components is also a milestone,
    # even when the human did not use the words UI or milestone.
    required = milestone["expected"] or (len(surface) >= 3 and bool(BUILD.search(milestone["goal"])) and not minor(milestone["goal"]))
    if not required or not (surface or milestone["explicit"] or milestone.get("surface_key")):
        return milestone
    key = digest(json.dumps(surface, sort_keys=True) + milestone["task"] + milestone["goal"])[:20]
    if milestone.get("surface_key") != key:
        milestone.update(surface=surface, surface_key=key, changed_at=now.isoformat(), status="pending", feedback=[])
        milestone.pop("blocker", None)
    if pending(milestone) and not milestone.get("hold") and (name in {"Stop", "PreCompact", "SessionStart", "UserPromptSubmit"} or event.get("model_boundary")):
        reconcile_feedback(milestone, cwd, session)
    # A leader's final prose is not native evidence that a surface is blocked.
    # Preserve any previously observed scoped evidence, but never let a claim
    # suppress the independent acceptance obligation for the whole task.
    return milestone

def tool_failed(event):
    response = event.get("tool_response")
    return bool(event.get("error") or (isinstance(response, dict) and
        (response.get("isError") or response.get("exit_code", 0) not in {0, None})))

def response_texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from response_texts(child)
    elif isinstance(value, dict):
        for key in ("content", "text", "output", "stdout", "result"):
            if key in value:
                yield from response_texts(value[key])

def scoped_surface_failure(event):
    """Recognize only structured HTTP failures explicitly scoped to a target."""
    response = event.get("tool_response")
    candidates = [response] if isinstance(response, dict) else []
    for text in response_texts(response):
        try:
            value = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            candidates.append(value)
    for value in candidates:
        try:
            status = int(value.get("http_status") or value.get("status_code") or 0)
        except (TypeError, ValueError):
            continue
        target = value.get("scoped_to") or value.get("target_scope")
        operation = value.get("command") or value.get("operation")
        if status >= 400 and isinstance(target, str) and target.strip() and isinstance(operation, str) and operation.strip():
            return {"target": target.strip()[:120], "operation": operation.strip()[:120],
                    "http_status": status, "source": "native-tool:" + str(
                        event.get("tool_call_id") or event.get("call_id") or event.get("tool_name") or "unknown")[:120]}
    return None

def archive_sources(cwd, milestone):
    # Herder owns these raw exports/manifests already; no new receipt store.
    local = (cwd / ".agent-herder/transcripts").glob("*/*.manifest.json")
    paths = {p for p in [*local, *(Path(p) for p in milestone["sources"])] if p.is_file()}
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:16]

def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("missing native timezone")
    return parsed

def browser_commands(command, depth=0):
    """Read native executed argv; unwrap bounded shells/SSH, never evaluate it."""
    if depth > 4 or not isinstance(command, str):
        return []
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments, current = [], []
    for token in tokens:
        if token in {";", "&&", "||", "|", "&"}:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    result = []
    for argv in segments:
        executable = Path(argv[0]).name
        if executable in {"agent-browser", "agent-device"}:
            result.append(argv)
        elif executable == "ssh":
            # The remote command is a shell string after SSH's host argument.
            # Only interpret its argv, not text printed by echo/printf/cat.
            i = 1
            while i < len(argv) and argv[i].startswith('-'):
                option = argv[i]
                i += 2 if option in {'-o', '-p', '-i', '-l', '-F', '-J', '-S'} else 1
            if i + 1 < len(argv):
                remote = argv[i+1] if len(argv[i+1:]) == 1 else shlex.join(argv[i+1:])
                result.extend(browser_commands(remote, depth+1))
        elif executable in {"bash", "sh", "zsh"}:
            index = next((i for i, x in enumerate(argv) if x in {'-c', '-lc'}), None)
            if index is not None and index+1 < len(argv):
                result.extend(browser_commands(argv[index+1], depth+1))
    return result


def browser_attempt(observations, urls):
    navigated, interacted, saw_result = False, False, False
    before = ""
    for call, output in observations:
        name = call.get("name", "").lower().split(".")[-1].rsplit("__", 1)[-1]
        args = str(call.get("arguments") or call.get("input") or "")
        actions = [name] if "browser" in name or "agent-device" in name else []
        if name in {"exec_command", "shell_command", "exec", "bash"}:
            try:
                payload = json.loads(args)
                command = payload.get("cmd") or payload.get("command") or ""
            except (ValueError, TypeError):
                command = ""
            actions = []
            for argv in browser_commands(command):
                action = next((x for x in argv[1:] if x in {"open", "snapshot", "click", "fill", "type", "press", "select", "screenshot", "get"}), "")
                if action == 'get':
                    action = 'get-url' if 'url' in argv[argv.index('get')+1:] else 'get'
                actions.append(action)
        if not actions or not output or re.search(r"(?:isError|exit_code)\W*[:=]\W*(?:true|[1-9])", output, re.I):
            continue
        if any(url.rstrip("/") in args or url.rstrip("/") in output for url in urls) and any(re.search(r"open|navigate|get-url", action) for action in actions):
            navigated = True
        if navigated and any(re.search(r"click|fill|type|press|select", action) for action in actions):
            interacted = True
        if navigated and re.search(r"button|textbox|heading|link|кнопк|поле", output, re.I):
            if re.search(r"(?:heading|title).*?(?:log.in|sign.in|вход|авторизац)", output, re.I):
                continue
            if interacted and before and output.strip() != before:
                saw_result = True
            elif not interacted:
                before = output.strip()
    return navigated and interacted and saw_result

def native_surface_evidence(observations, urls):
    """Extract target-specific login evidence only from native browser output."""
    active, blocked, navigated = None, [], []
    for call, output in observations:
        name = call.get("name", "").lower().split(".")[-1].rsplit("__", 1)[-1]
        args = str(call.get("arguments") or call.get("input") or "")
        actions = [name] if "browser" in name or "agent-device" in name else []
        if name in {"exec_command", "shell_command", "exec", "bash"}:
            try:
                payload = json.loads(args)
                command = payload.get("cmd") or payload.get("command") or ""
            except (ValueError, TypeError):
                command = ""
            actions = []
            for argv in browser_commands(command):
                actions.append(next((x for x in argv[1:] if x in {
                    "open", "navigate", "snapshot", "click", "fill", "type", "press", "select", "get"}), ""))
        matched = next((url for url in urls if url.rstrip("/") in args or url.rstrip("/") in str(output)), None)
        if matched and any(re.search(r"open|navigate|get-url", action) for action in actions):
            parsed = urlparse(matched)
            host = parsed.hostname or "unknown"
            if parsed.port:
                host += f":{parsed.port}"
            active = f"{parsed.scheme}://{host}{parsed.path}".rstrip("/")
            if active not in navigated:
                navigated.append(active)
        snapshot = any(re.search(r"snapshot|browser", action) for action in actions) or "snapshot" in name
        access_error = bool(re.search(r"(?:isError|exit_code)\W*[:=]\W*(?:true|[1-9])", str(output), re.I))
        visible_login = snapshot and re.search(r"(?:heading|title).*?(?:log.in|sign.in|вход|авторизац)", str(output), re.I)
        denied = access_error and re.search(r"permission.{0,20}denied|access.{0,20}denied|нет.{0,20}доступ", str(output), re.I)
        if active and (visible_login or denied):
            blocked.append({"target": active, "operation": "login-or-access-required"})
    return {"blocked": blocked, "targets": navigated}


def goal_report(final, goal):
    # A mechanical floor, not an LLM semantic grader. Require the actual goal,
    # attempted steps and an observed result, retaining all raw criticism.
    stop = {"build", "create", "complete", "implement", "with", "that", "this", "then", "from", "goal", "task", "acceptance", "user", "final", "surface", "please", "should", "must", "сделай", "создай", "чтобы", "нужно", "должен"}
    terms = {w.casefold() for w in re.findall(r"[^\W\d_]{4,}", goal)} - stop
    shared = sum(bool(re.search(re.escape(word), final, re.I)) for word in terms)
    steps = re.search(r"\b(?:clicked|typed|entered|selected|opened|imported|searched|submitted|pressed|filled)\b|нажал|вв[её]л|импортировал|открыл|выбрал|отправил", final, re.I)
    result = re.search(r"\b(?:saw|found|displayed|appeared|showed|downloaded|observed)\b|увидел|показ|появ|наш[её]л|скачал|результат", final, re.I)
    return shared >= min(2, len(terms)) and bool(terms and steps and result)

def feedback_from(path, milestone, session):
    manifest = json.loads(read(path))
    if manifest.get("format") != "agent-herder-transcript-manifest-v1":
        return None
    target = manifest["target"]
    raw = read(target["path"])
    # Read adapter-owned native source, not a leader-authored summary. A live
    # source may have appended after the export; the exported prefix stays valid.
    if target.get("harness") == "codex" and target.get("complete"):
        location = Path(target["source"]["location"]).resolve()
        native_root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions"
        location.relative_to(native_root.resolve())
        if target["source"].get("kind") != "native-file" or location.suffix != ".jsonl":
            return None
        native = read(location)
        if not native.startswith(raw):
            return None
        meta, messages, observations = native_transcript(raw)
    elif target.get("harness") == "opencode":
        meta, messages, observations = opencode_transcript(target, raw)
    else:
        return None
    sid = meta.get("id") or meta.get("session_id")
    if not sid or sid == session or sid != target.get("sessionId"):
        return None
    if Path(meta.get("cwd", "/unknown")).resolve() != Path(milestone["cwd"]).resolve():
        return None
    if timestamp(meta["timestamp"]) < timestamp(milestone["changed_at"]):
        return None
    prompt = next((text for role, text, _ in messages if role == "user"), "")
    # Ordinary tester assignment carries the unchanged goal and changed surface
    # reference from current task context. These are correlation, not signatures.
    correlated = milestone["task"] in prompt and milestone["surface_key"] in prompt
    # Existing normal task assignments can carry the literal goal instead of
    # internal references. No leader-written acceptance certificate is needed.
    if not correlated and milestone["goal"] not in prompt:
        return None
    # Prefer the explicit persona, not a substring such as the ending of
    # Russian "аккаунты" in a common coordination/infrastructure preamble.
    persona = re.search(r"^\s*(?:persona|персона)\s*:\s*([^\n]+)", prompt, re.I | re.M)
    if persona is None:
        persona = re.search(r"(?:\byou are\b|(?<!\w)ты)\s+([^\n]+)", prompt, re.I)
    persona_text = next((p.strip() for p in persona.groups() if p), "") if persona else ""
    if len(persona_text) < 15:
        return None
    final = next((text for role, text, phase in reversed(messages) if role == "assistant" and phase != "commentary"), "")
    # Candid task-relevant observations need no praise/complaint keywords or
    # word quota. Actual actions, goal/result and native provenance remain below.
    if not final.strip():
        return None
    # The fresh native assignment may explicitly name a managed tunnel/staging
    # address for the same correlated task. It need not equal the public URL.
    urls = list(dict.fromkeys([*(milestone.get("urls") or []), *URL.findall(prompt)]))
    if not urls:
        return None
    surface = native_surface_evidence(observations, urls)
    status = "pending"
    if surface["blocked"]:
        status = "blocked"
    elif browser_attempt(observations, urls):
        if CHANGES.search(final):
            status = "changes-required"
        elif ACHIEVED.search(final) and not PARTIAL.search(final) and goal_report(final, milestone["goal"]):
            status = "accepted"
    return {"session": sid, "persona": persona_text, "status": status,
            "scope": surface["blocked"][0] if status == "blocked" else {"target": surface["targets"], "operation": "consumer-acceptance"},
            "targets": surface["targets"], "source": str(path), "raw_feedback": final,
            "surface": milestone["surface_key"], "started_at": meta["timestamp"]}

def reconcile_feedback(milestone, cwd, session):
    feedback, sessions, personas = [], set(), set()
    started = monotonic()
    for path in archive_sources(cwd, milestone):
        if monotonic() - started > 2:
            break  # Leave unobserved acceptance pending; native hook is bounded.
        try:
            result = feedback_from(path, milestone, session)
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            continue
        if result and result["session"] not in sessions:
            sessions.add(result["session"])
            feedback.append(result)
            personas.add(result["persona"].casefold())
    milestone["feedback"] = feedback
    milestone["scoped_blockers"] = [
        {"target": row["scope"].get("target"), "operation": row["scope"].get("operation"),
         "source": row["source"], "session": row["session"],
         "observed_at": row["started_at"]}
        for row in feedback if row["status"] == "blocked"
    ]
    failures = [r for r in feedback if r["status"] != "accepted"]
    latest_failure = max((timestamp(r["started_at"]) for r in failures), default=None)
    successful = [r for r in feedback if r["status"] == "accepted" and
                  (latest_failure is None or timestamp(r["started_at"]) > latest_failure)]
    unresolved = []
    for blocker in milestone["scoped_blockers"]:
        target = blocker.get("target")
        later = [r for r in successful if target and target in r.get("targets", [])
                 and timestamp(r["started_at"]) > timestamp(blocker["observed_at"])]
        if len({r["persona"].casefold() for r in later}) < 2:
            unresolved.append(blocker)
    if (len(successful) >= 2 and len({r["persona"].casefold() for r in successful}) >= 2
            and not unresolved):
        milestone["status"] = "accepted"
        milestone["scoped_blockers"] = []
    else:
        milestone["status"] = "changes-required" if any(r["status"] == "changes-required" for r in feedback) else "pending"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def native_get(url):
    # Only the existing local native OpenCode read API, no credentials, writes,
    # implicit login, remote hosts or redirects. Failure leaves evidence pending.
    with build_opener(ProxyHandler({}), NoRedirect).open(url, timeout=0.3) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("native API exceeds bounded window")
    result = json.loads(data)
    return result.get("data", result) if isinstance(result, dict) else result

def opencode_transcript(target, raw):
    """Herder exports the message API with partial coverage. Verify freshness
    against native session metadata and archived messages against the same API;
    unknown pagination never becomes evidence of a fresh independent session.
    """
    source = target["source"]
    parsed = urlparse(source["location"])
    sid = target["sessionId"]
    if (source.get("kind") != "native-api" or parsed.scheme != "http" or
            parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or
            not re.fullmatch(r"/(?:api/)?session/" + re.escape(sid) + r"/message", parsed.path)):
        raise ValueError("not the local native session message source")
    archived = json.loads(raw)
    live = native_get(source["location"])
    info = native_get(parsed._replace(path=parsed.path.removesuffix("/message"), query="").geturl())
    if info.get("id") != sid or not isinstance(archived, list) or not isinstance(live, list):
        raise ValueError("native session identity unavailable")
    by_id = {(m.get("info") or m).get("id"): m for m in live}
    if any(not (m.get("info") or m).get("id") or by_id.get((m.get("info") or m).get("id")) != m for m in archived):
        raise ValueError("export does not match native messages")
    return opencode_messages(info, archived)


def opencode_messages(info, archived):
    """Parse already source-verified native messages; do not infer provenance."""
    sid = info['id']
    created = info["time"]["created"] / 1000
    meta = {"id": sid, "timestamp": datetime.fromtimestamp(created).astimezone().isoformat(),
            "cwd": (info.get("location") or {}).get("directory") or info.get("directory"),
            "model": info.get("model")}
    messages, observations = [], []
    for message in archived:
        header = message.get("info") or message
        if header.get("sessionID", sid) != sid:
            raise ValueError("mixed native sessions")
        role = header.get("role") or header.get("type")
        parts = message.get("parts") or message.get("content") or []
        text = content(parts) or message.get("text", "")
        if role in {"user", "assistant"}:
            # Tool-bearing assistant messages are working observations, not the
            # final raw feedback; a later plain assistant answer must conclude.
            has_tools = isinstance(parts, list) and any(p.get("type") == "tool" for p in parts)
            messages.append((role, text, "commentary" if has_tools else None))
        if isinstance(parts, list):
            for part in parts:
                state = part.get("state") or {}
                if part.get("type") == "tool" and state.get("status") == "completed":
                    observations.append(({"name": part.get("tool") or part.get("name") or "", "call_id": part.get("callID") or part.get("id"), "arguments": json.dumps(state.get("input", {}))}, content(state.get("output"))))
    return meta, messages, observations

def pending(milestone):
    return bool(milestone and milestone["status"] in {"pending", "changes-required", "blocked"})

def reminder(milestone):
    return ("LHC: milestone user acceptance remains incomplete (" + milestone["status"] +
        "). Do not declare UI ready from own tests, child-session launch or a login page. Prepare permitted "
        "sandbox/test identity before attempts; never extract secrets or bypass permissions. Existing Herder "
        "must provide at least two fresh independent Zero Knowledge attempts with varied realistic personas "
        "and full raw feedback: what helped/was liked, obstacles/dislikes, observed actions and goal achieved. "
        "Use existing model-routing. Include Persona: <age, experience, goal, conditions>, original goal/URL "
        "and current task/surface refs in the ordinary tester assignment: " + milestone["task"] + " / " + milestone["surface_key"] + ". "
        "Read original answers through native Herder export_transcript; the hook retains the returned Lineage "
        "manifest at its actual path without manual file copying. Never invent PASS or create a new report form. "
        "Findings require repairs and fresh attempts; login-only means blocked/not-tested. If access is truly "
        "blocked, finish with its exact reason and incomplete acceptance; no repeated automatic launches. "
        "Continue independent permitted work. Changed surface: " + ", ".join(milestone["surface"]) + ".")


# ---------------------------------------------------------------------------
# Explicit command line. The agent calls these; a hook never does.
# ---------------------------------------------------------------------------

RUNTIMES = ("codex", "opencode", "zcode", "claude", "hermes")


def acceptance_gate(state):
    """Decide the milestone user-acceptance gate for an observed session.

    This is the blocking check that used to live inside the native hook. It is
    an explicit command now: the hook stays time-only and never blocks.
    """
    milestone = state.get("milestone") or {}
    if not isinstance(milestone, dict):
        milestone = {}
    delivery = state.get("native_entry") or {}
    if not isinstance(delivery, dict):
        delivery = {}
    if delivery.get("finish_hold") or milestone.get("hold"):
        return {"decision": "allow",
                "reason": "LHC: milestone acceptance is held for this session "
                          "(recorded hold, not a verdict)."}
    if pending(milestone) and milestone.get("status") != "accepted":
        return {"decision": "block", "reason": reminder(milestone)}
    return {"decision": "allow",
            "reason": "LHC: no pending milestone user acceptance. This gate never accepts "
                      "work by itself; it only reports an outstanding acceptance debt."}


def _state_path(cwd, runtime, session_id):
    import lhc_time_guard as guard
    return guard.learning_path(cwd, runtime, session_id)


def _load_state(path, runtime, session_id, cwd):
    import lhc_time_guard as guard
    state = guard.load_state(path)
    if state is None:
        raise SystemExit(
            f"LHC milestone: no session state for {runtime}/{session_id} from session root "
            f"{cwd}; observe the session first")
    return state


def _observe(cwd, runtime, session_id, name, payload):
    import lhc_time_guard as guard
    path = _state_path(cwd, runtime, session_id)
    state = _load_state(path, runtime, session_id, cwd)
    event = dict(payload)
    business = state.get("business", {})
    prior_milestone = state.get("milestone", {})
    event.setdefault("_lhc_previous_active_prompts", [
        business.get("latest_prompt_full") or business.get("latest_prompt") or "",
        business.get("original_prompt_full") or business.get("original_prompt") or "",
        prior_milestone.get("goal") or "",
    ])
    now = datetime.now().astimezone()
    with path.with_suffix(".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path) or state
        milestone = observe(state, event, name, cwd, session_id, now)
        guard.write_state(path, state)
    return milestone


def _gate(cwd, runtime, session_id):
    path = _state_path(cwd, runtime, session_id)
    state = _load_state(path, runtime, session_id, cwd)
    return acceptance_gate(state)


def _status(cwd, runtime, session_id):
    path = _state_path(cwd, runtime, session_id)
    state = _load_state(path, runtime, session_id, cwd)
    milestone = state.get("milestone") or {}
    if not isinstance(milestone, dict):
        milestone = {}
    return {
        "session": session_id,
        "runtime": runtime,
        "state": str(path),
        "status": milestone.get("status", "not-observed"),
        "task": milestone.get("task"),
        "surface_key": milestone.get("surface_key"),
        "read_only": milestone.get("read_only"),
        "hold": milestone.get("hold"),
        "pending": pending(milestone),
        "feedback_count": len(milestone.get("feedback") or []),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--runtime", choices=RUNTIMES, required=True)
    parser.add_argument("--session-id", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    observe_parser = sub.add_parser("observe", help="observe one native event into the milestone state")
    observe_parser.add_argument("--event", required=True)
    sub.add_parser("gate", help="report the milestone user-acceptance gate for this session")
    sub.add_parser("status", help="report the observed milestone state")
    args = parser.parse_args()
    cwd = args.cwd.resolve()
    if args.command == "observe":
        raw = sys.stdin.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise SystemExit("LHC milestone: event payload exceeds the bounded native window")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            raise SystemExit("LHC milestone: event payload must be a JSON object")
        milestone = _observe(cwd, args.runtime, args.session_id, args.event, payload)
        result = {"milestone": milestone}
    elif args.command == "gate":
        result = _gate(cwd, args.runtime, args.session_id)
    else:
        result = _status(cwd, args.runtime, args.session_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
