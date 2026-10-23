"""Git facts for the milestone observer, read without spawning `git`.

`lhc_milestone` asks one repository the same questions over and over: which
files are tracked, which are untracked, which changed against the task HEAD,
and what a remote points at.  Every answer is a fact about the working tree,
so this module reads Git's own on-disk state - the index, HEAD, the config
and the ignore rules - instead of starting a process for each question.

Two rules keep the answers honest.

* **A reused answer comes with its invalidation.**  The changed-paths answer
  is reused only while the index, the HEAD reference and the stat of every
  tracked file are bit for bit the ones it was computed for.  That is the
  observable signal Git's own index uses, so a file that appeared, vanished
  or changed, and a HEAD that moved, all end the reuse.  The tracked and
  untracked lists are never reused at all: they are read from the index and
  from a fresh walk of the working tree every time.
* **Anything unusual is answered by Git itself.**  A linked worktree, a
  split or sparse index, an unmerged path, an ignore file that a global
  config points Git at: each of those falls back to a real `git` call, so the
  answer stays the one Git would give.

Nothing here writes, fetches or locks.  Every read is a plain file read of
state Git already keeps on disk.
"""

import os
import re
import subprocess
from pathlib import Path


# The environment variables that move the repository away from the working
# tree.  When any of them is set this module does not guess where the
# repository is; it lets Git answer.
_ENVIRONMENT_OVERRIDES = (
    "GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM",
)

# Git's own bound on a single answer.  A repository larger than this is
# answered by Git, not by a partial read.
MAX_BYTES = 8 * 1024 * 1024

_SHA = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")

# The bounded caches below are keyed by repository, never by content, and
# hold at most a handful of repositories.  A cache entry is dropped as soon
# as the state it describes changes.
_CACHE_LIMIT = 16

_REPOSITORIES = {}
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


def _directory_stamp(path):
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_ino)


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
# ---------------------------------------------------------------------------


class Repository:
    """Where the repository lives and which files Git keeps for it."""

    def __init__(self, gitdir, root, common):
        self.gitdir = gitdir
        self.root = root
        self.common = common

    @property
    def key(self):
        return str(self.gitdir)


def _common_dir(gitdir):
    """The shared directory of a repository, the gitdir itself by default.

    A linked worktree keeps its own HEAD and index but shares the refs, the
    config and the objects with the main worktree; the `commondir` file
    says which directory that is.
    """
    text = _read_text(Path(gitdir) / "commondir")
    if not text:
        return Path(gitdir)
    target = Path(text.strip())
    if not target.is_absolute():
        target = Path(gitdir) / target
    return target


def _gitdir_from_file(path):
    """The gitdir a `.git` file points at, or None when it is not one."""
    text = _read_text(path)
    if not text or not text.startswith("gitdir:"):
        return None
    target = Path(text[len("gitdir:"):].strip())
    if not str(target):
        return None
    if not target.is_absolute():
        target = path.parent / target
    return target


def discover(cwd):
    """The repository that holds ``cwd``, or None when Git has to answer."""
    if any(os.environ.get(name) for name in _ENVIRONMENT_OVERRIDES):
        return None
    try:
        start = Path(cwd).resolve()
    except OSError:
        return None
    cached = _REPOSITORIES.get(str(start))
    if cached is not None:
        return cached
    found = None
    for candidate in (start, *start.parents):
        dotgit = candidate / ".git"
        if dotgit.is_dir():
            found = Repository(dotgit, candidate, _common_dir(dotgit))
            break
        if dotgit.is_file():
            target = _gitdir_from_file(dotgit)
            if target is None or not target.is_dir():
                break
            found = Repository(target, candidate, _common_dir(target))
            break
    if found is not None:
        # A path that is not a repository yet may become one, so only a
        # repository that was found is remembered.
        _REPOSITORIES[str(start)] = found
        _trim_cache(_REPOSITORIES)
    return found


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


def _index_paths(repo):
    """The tracked paths of the repository, root relative.

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
            _INDEXES[key] = (stamp, [])
            return []
        return None
    if len(data) < 12 or data[:4] != b"DIRC":
        return None
    version = int.from_bytes(data[4:8], "big")
    if version not in (2, 3):
        return None
    count = int.from_bytes(data[8:12], "big")
    offset = 12
    paths = []
    for _ in range(count):
        start = offset
        if start + 62 > len(data):
            return None
        flags = int.from_bytes(data[start + 60:start + 62], "big")
        if (flags >> 12) & 0x3:
            return None  # an unmerged path: Git lists it once per stage
        base = 62
        if flags & 0x4000:
            if version < 3:
                return None
            base = 64
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
        name = data[offset:end].decode("utf-8", errors="replace")
        if not name or "\0" in name or name.startswith("/"):
            return None
        paths.append(name)
        # Every entry is padded with NULs to a multiple of eight bytes.
        offset = start + ((base + length + 8) & ~7)
    if len(paths) != count or paths != sorted(paths) or len(set(paths)) != count:
        return None  # the entries did not add up: Git has to answer
    if _has_unsafe_extension(data, offset):
        return None
    _INDEXES[key] = (stamp, paths)
    _trim_cache(_INDEXES)
    return paths


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


def _git(cwd, *args):
    """The one Git call this module still makes, for what it cannot read."""
    try:
        result = subprocess.run(["git", "-C", str(cwd), *args],
                                capture_output=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return b""
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("Git surface exceeds bounded window")
    return result.stdout if result.returncode == 0 else b""


def _as_bytes(paths):
    return b"".join(path.encode("utf-8", errors="replace") + b"\0" for path in paths)


def answer(cwd, args):
    """The answer to one Git question, read from disk when it is safe.

    Returns None when the question is not one this module reads, so that
    the caller asks Git.
    """
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
        return str(repo.root).encode() + b"\n"
    if len(args) == 3 and args[:2] == ("remote", "get-url"):
        url = remote_url(repo, args[2])
        if url is None:
            return None
        return url.encode() + b"\n"
    return None


def candidate_paths(cwd, head):
    """The changed and untracked paths of ``cwd``, as Git would list them.

    Returns None when this module cannot answer, so that the caller asks
    Git the way it always did.
    """
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
            changed = [path for path in
                       _git(cwd, "diff", "--name-only", "-z", head).decode("utf-8", errors="replace").split("\0")
                       if path]
            _CHANGED[(repo.key, head)] = (token, changed)
            _trim_cache(_CHANGED)
        return _as_bytes(changed) + _as_bytes(untracked)
    return _as_bytes(tracked) + _as_bytes(untracked)
