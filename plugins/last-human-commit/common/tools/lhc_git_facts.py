"""Git facts read from the repository on disk, without a Git process.

Every answer below is a fact Git keeps in the repository itself, read at the
moment of the call.  Nothing is cached, so a repository that changed between
two calls is never answered from a stale value: the answer is always the
state of the repository now.  A layout or a question this module does not
model answers None and the Git binary is asked instead, which keeps the
answer of the caller the one Git gives.

The facts are read from the directories the reader of the layout of a
repository names, so the canon keeps one answer about where a repository
lives.  This module adds the facts themselves: the objects, the references,
the configuration and the packs.
"""
import importlib.util
import os
import re
import sys
import zlib
from pathlib import Path


def _load_layout():
    """Load the reader of the layout of a repository from next to this file.

    The reader is a separate file, so a package that does not carry it yet
    cannot answer a fact either; the caller then asks the Git binary, which
    is the answer it always gave.
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
            raise ImportError(f"no reader of the layout next to this file: {path}")
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module
    except Exception as error:  # noqa: BLE001 - a missing reader means Git answers
        sys.modules.pop("lhc_gitlayout_sibling", None)
        raise ImportError(f"no reader of the layout next to this file: {path}") from error


layout = _load_layout()


# The repository of a directory, exactly as the reader of the layout names it.
Repository = layout.Repository


# Environment variables that change which configuration files Git reads in a
# way this module does not model.  The answer is left to the Git binary.
_UNMODELLED_CONFIG_ENVIRONMENT = (
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
)

_OBJECT_ID = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")

# The bound on how many commits one ancestry walk may visit.  A history
# deeper than this is answered by Git, which walks it faster.
_WALK_LIMIT = 20000


# ---------------------------------------------------------------------------
# The repository
# ---------------------------------------------------------------------------


def _read_text(path):
    """Read one text file, answering None when it cannot be read.

    The bytes of a name Git cannot decode are kept, the way the reader of the
    layout keeps them.
    """

    return layout.read_text(Path(path), errors="surrogateescape")


def discover(cwd):
    """The repository that owns a directory, or None when Git has to answer."""

    return layout.discover(Path(cwd))


def _replaced(repo):
    """Whether the repository replaces objects, which changes their meaning."""
    try:
        return (repo.common / "refs" / "replace").exists()
    except OSError:
        return True


# ---------------------------------------------------------------------------
# The objects
# ---------------------------------------------------------------------------


def _object(repo, sha):
    """The type and the payload of one object.

    None means the object cannot be read: it does not exist, or the layout
    is not one this module reads.  The caller then asks Git, which knows
    every layout.
    """
    if not sha or not _OBJECT_ID.match(sha):
        return None
    loose = _loose_object(repo, sha)
    if loose is not None:
        return loose
    return _packed_object(repo, sha)


def _loose_object(repo, sha):
    """The type and the payload of one loose object, or None."""
    path = repo.common / "objects" / sha[:2] / sha[2:]
    try:
        raw = zlib.decompress(path.read_bytes())
    except (OSError, ValueError, zlib.error):
        return None
    head, separator, body = raw.partition(b"\0")
    if not separator:
        return None
    kind, _, size = head.decode("ascii", "replace").partition(" ")
    try:
        length = int(size)
    except ValueError:
        return None
    if length != len(body):
        return None
    return kind, body


def _reference(repo, name):
    """The object id a reference points at, or None."""
    for base in (repo.gitdir, repo.common):
        text = _read_text(base / name)
        if text is None:
            continue
        value = text.strip()
        if value.startswith("ref:"):
            nested = value[len("ref:"):].strip()
            if not nested:
                return None
            return _reference(repo, nested)
        return value if _OBJECT_ID.match(value) else None
    packed = _read_text(repo.common / "packed-refs")
    if packed is None:
        return None
    for raw in packed.splitlines():
        line = raw.strip()
        if not line or line[0] in "#^":
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1] == name and _OBJECT_ID.match(parts[0]):
            return parts[0]
    return None


def head_sha(repo):
    """The commit of HEAD, or None when Git has to answer.

    The object id is read from the reference itself, the way ``git
    rev-parse HEAD`` reads it: a reference that names an object which is not
    on disk is still an answer Git prints.
    """
    text = _read_text(repo.gitdir / "HEAD")
    if text is None:
        return None
    value = text.strip()
    if value.startswith("ref:"):
        name = value[len("ref:"):].strip()
        if not name:
            return None
        return _reference(repo, name)
    return value if _OBJECT_ID.match(value) else None


def _commit(repo, sha):
    """The tree and the parents of one commit, or None."""
    found = _object(repo, sha)
    if found is None or found[0] != "commit":
        return None
    tree = None
    parents = []
    for raw in found[1].split(b"\n"):
        if not raw:
            break
        if raw.startswith(b"tree "):
            tree = raw[len(b"tree "):].decode("ascii", "replace").strip()
        elif raw.startswith(b"parent "):
            parents.append(raw[len(b"parent "):].decode("ascii", "replace").strip())
    if tree is None:
        return None
    return tree, parents


def _peel(repo, sha, depth=0):
    """The commit a revision peels to, or None."""
    if depth > 5:
        return None
    found = _object(repo, sha)
    if found is None:
        return None
    if found[0] == "commit":
        return sha
    if found[0] != "tag":
        return None
    target = None
    for raw in found[1].split(b"\n"):
        if not raw:
            break
        if raw.startswith(b"object "):
            target = raw[len(b"object "):].decode("ascii", "replace").strip()
    if not target or not _OBJECT_ID.match(target):
        return None
    return _peel(repo, target, depth + 1)


def _resolve(repo, revision):
    """The object id a revision names, or None."""
    if not revision:
        return None
    if _OBJECT_ID.match(revision):
        return revision
    if revision == "HEAD":
        return head_sha(repo)
    if revision.startswith("refs/"):
        return _reference(repo, revision)
    return None


def commit_exists(repo, revision):
    """Whether Git can peel one revision to a commit.

    This is the answer of ``git cat-file -e <revision>^{commit}``.  True
    means the revision names a commit.  None means the answer is not
    certain: the object is packed, it does not exist, or it is a revision
    this module does not resolve.  The Git binary has to answer then, so
    that a revision without a commit fails exactly the way it failed
    before.
    """
    if revision.endswith("^{commit}"):
        revision = revision[: -len("^{commit}")]
    sha = _resolve(repo, revision)
    if sha is None:
        return None
    if _peel(repo, sha) is not None:
        return True
    return None


def commit_parents(repo, sha):
    """The parents of one commit, or None when Git has to answer.

    This is the answer of ``git rev-list --parents -n 1 <commit>``.
    """
    if not sha:
        return None
    parsed = _commit(repo, sha)
    if parsed is None:
        return None
    return parsed[1]


def _tree(repo, sha):
    """The entries of one tree, or None."""
    found = _object(repo, sha)
    if found is None or found[0] != "tree":
        return None
    body = found[1]
    width = len(sha) // 2
    entries = []
    index = 0
    while index < len(body):
        space = body.find(b" ", index)
        if space < 0:
            return None
        mode = body[index:space].decode("ascii", "replace")
        nul = body.find(b"\0", space)
        if nul < 0:
            return None
        name = body[space + 1:nul]
        start = nul + 1
        end = start + width
        if end > len(body):
            return None
        entries.append((mode, name, body[start:end].hex()))
        index = end
    return entries


def _tree_paths(repo, tree, prefix=b""):
    """Every path of one tree with its mode and its object id."""
    entries = _tree(repo, tree)
    if entries is None:
        return None
    found = {}
    for mode, name, child in entries:
        path = prefix + b"/" + name if prefix else name
        if mode == "40000":
            deeper = _tree_paths(repo, child, path)
            if deeper is None:
                return None
            found.update(deeper)
        else:
            found[path] = (mode, child)
    return found


def _needs_quoting(raw):
    """Whether Git would quote one path in a name-only listing."""
    return any(byte < 0x20 or byte == 0x7F or byte in (0x22, 0x5C) or byte >= 0x80
               for byte in raw)


def changed_paths(repo, base, commit, *, no_renames=True):
    """The paths that differ between two commits, or None.

    This is the answer of ``git diff --name-only <base> <commit>``.  The
    paths are listed in the order Git lists them, and a path Git would
    quote is not answered here: the Git binary has to answer then, so the
    listing stays byte for byte the listing of Git.
    """
    if _replaced(repo):
        return None
    left = _commit(repo, base)
    right = _commit(repo, commit)
    if left is None or right is None:
        return None
    before = _tree_paths(repo, left[0])
    after = _tree_paths(repo, right[0])
    if before is None or after is None:
        return None
    changed = {path for path in set(before) | set(after)
               if before.get(path) != after.get(path)}
    deleted = {path for path in before if path not in after}
    added = {path for path in after if path not in before}
    if not no_renames:
        # Git detects a rename when the same content moved to another path.
        # Which of several candidates Git pairs is its own decision, so the
        # Git binary answers whenever a candidate exists at all.
        contents = {}
        for path in deleted:
            contents.setdefault(before[path][1], []).append(path)
        for path in added:
            if after[path][1] in contents:
                return None
    if any(_needs_quoting(path) for path in changed):
        return None
    ordered = sorted(changed)
    return [os.fsdecode(path) for path in ordered]


def tree_entries(repo, commit):
    """Every path of one commit with its mode and its object id, or None.

    This is the answer of ``git ls-tree -r <commit>``: the paths of the
    commit, each with the mode and the object id the tree holds for it.
    The mode is the number of the mode, the way the index holds it, and
    the paths keep the bytes of the tree, so a path Git would spell in
    another encoding is still the path of the tree.

    None means the tree cannot be read, so the Git binary has to answer.
    """
    if _replaced(repo):
        return None
    parsed = _commit(repo, commit)
    if parsed is None:
        return None
    entries = _tree_paths(repo, parsed[0])
    if entries is None:
        return None
    return {os.fsdecode(path): (int(mode, 8), sha)
            for path, (mode, sha) in entries.items()}


def blob_at(repo, commit, path):
    """The bytes of one file inside a commit, or None.

    This is the answer of ``git show <commit>:<path>`` for a file.  A path
    that names a tree is not answered here, because Git prints a listing
    for it rather than the bytes of a file.
    """
    if _replaced(repo):
        return None
    parsed = _commit(repo, commit)
    if parsed is None:
        return None
    parts = [part for part in os.fsencode(path).split(b"/") if part]
    if not parts:
        return None
    current = parsed[0]
    mode = ""
    for index, part in enumerate(parts):
        entries = _tree(repo, current)
        if entries is None:
            return None
        found = None
        for entry_mode, name, child in entries:
            if name == part:
                found = (entry_mode, child)
                break
        if found is None:
            return None
        mode, current = found
        if index < len(parts) - 1 and mode != "40000":
            return None
    if mode == "40000":
        return None
    found = _object(repo, current)
    if found is None or found[0] != "blob":
        return None
    return found[1]


def is_ancestor(repo, ancestor, descendant):
    """Whether one commit is an ancestor of another, or None.

    This is the answer of ``git merge-base --is-ancestor <a> <b>``.  A
    commit is an ancestor of itself, the way Git counts it.
    """
    if _replaced(repo):
        return None
    if _commit(repo, ancestor) is None or _commit(repo, descendant) is None:
        return None
    seen = set()
    frontier = [descendant]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if current == ancestor:
            return True
        parsed = _commit(repo, current)
        if parsed is None:
            return None
        frontier.extend(parsed[1])
        if len(seen) > _WALK_LIMIT:
            return None
    return False


# ---------------------------------------------------------------------------
# The packed objects
# ---------------------------------------------------------------------------


# The kinds of object a pack holds.
_PACK_KINDS = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}


def _hash_width(repo):
    """The length of an object id of this repository."""
    entries = _config_entries(repo.common / "config")
    if entries is None:
        return 20
    for section, _subsection, key, value in entries:
        if section == "extensions" and key == "objectformat" and value == "sha256":
            return 32
    return 20


def _pack_indexes(repo):
    """The index of every pack of a repository."""
    root = repo.common / "objects" / "pack"
    try:
        names = sorted(item for item in os.listdir(root) if item.endswith(".idx"))
    except OSError:
        return []
    return [root / name for name in names]


def _index_find(index_path, sha, width):
    """Where one object lives in the pack of an index, or None.

    None means the index does not hold the object, or the index is of a
    shape this module does not read.  Git answers then.
    """
    try:
        wanted = bytes.fromhex(sha)
    except ValueError:
        return None
    if len(wanted) != width:
        return None
    try:
        with index_path.open("rb") as stream:
            if stream.read(4) != b"\xfftOc":
                return None
            if stream.read(4) != b"\x00\x00\x00\x02":
                return None
            fanout = stream.read(1024)
            if len(fanout) != 1024:
                return None
            count = int.from_bytes(fanout[255 * 4:256 * 4], "big")
            if count == 0:
                return None
            first = wanted[0]
            low = int.from_bytes(fanout[(first - 1) * 4:first * 4], "big") if first else 0
            high = int.from_bytes(fanout[first * 4:(first + 1) * 4], "big")
            names_at = 8 + 1024
            offsets_at = names_at + count * width + count * 4
            large_at = offsets_at + count * 4
            while low < high:
                middle = (low + high) // 2
                stream.seek(names_at + middle * width)
                name = stream.read(width)
                if len(name) != width:
                    return None
                if name == wanted:
                    stream.seek(offsets_at + middle * 4)
                    raw = stream.read(4)
                    if len(raw) != 4:
                        return None
                    value = int.from_bytes(raw, "big")
                    if value & 0x80000000:
                        stream.seek(large_at + (value & 0x7FFFFFFF) * 8)
                        raw = stream.read(8)
                        if len(raw) != 8:
                            return None
                        value = int.from_bytes(raw, "big")
                    pack = index_path.with_suffix(".pack")
                    return value, pack
                if name < wanted:
                    low = middle + 1
                else:
                    high = middle
    except OSError:
        return None
    return None


def _inflate(stream, size):
    """The bytes of one packed object, or None."""
    decompressor = zlib.decompressobj()
    out = b""
    while len(out) < size:
        chunk = stream.read(65536)
        if not chunk:
            break
        out += decompressor.decompress(chunk)
    if len(out) != size:
        return None
    return out


def _apply_delta(base, delta):
    """The result of applying one delta to its base, or None."""
    index = 0

    def number():
        nonlocal index
        value = 0
        shift = 0
        while index < len(delta):
            byte = delta[index]
            index += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                return value
        return None

    source = number()
    target = number()
    if source is None or target is None or source != len(base):
        return None
    out = bytearray()
    while index < len(delta):
        instruction = delta[index]
        index += 1
        if instruction & 0x80:
            offset = 0
            size = 0
            for bit in range(4):
                if instruction & (1 << bit):
                    if index >= len(delta):
                        return None
                    offset |= delta[index] << (bit * 8)
                    index += 1
            for bit in range(3):
                if instruction & (1 << (4 + bit)):
                    if index >= len(delta):
                        return None
                    size |= delta[index] << (bit * 8)
                    index += 1
            if size == 0:
                size = 0x10000
            out += base[offset:offset + size]
        elif instruction:
            out += delta[index:index + instruction]
            index += instruction
        else:
            return None
    if len(out) != target:
        return None
    return bytes(out)


def _read_pack_object(repo, pack_path, offset, width, depth):
    """The type and the payload of the object at one offset of a pack, or None."""
    if depth > 50:
        return None
    try:
        with pack_path.open("rb") as stream:
            stream.seek(offset)
            header = stream.read(64)
            if not header:
                return None
            byte = header[0]
            kind = (byte >> 4) & 7
            size = byte & 0x0F
            shift = 4
            position = 1
            while byte & 0x80:
                if position >= len(header):
                    return None
                byte = header[position]
                position += 1
                size |= (byte & 0x7F) << shift
                shift += 7
            if kind in _PACK_KINDS:
                stream.seek(offset + position)
                payload = _inflate(stream, size)
                if payload is None:
                    return None
                return _PACK_KINDS[kind], payload
            base = None
            if kind == 6:
                # The base is another object of the same pack, at a distance.
                if position >= len(header):
                    return None
                byte = header[position]
                position += 1
                distance = byte & 0x7F
                while byte & 0x80:
                    if position >= len(header):
                        return None
                    byte = header[position]
                    position += 1
                    distance = ((distance + 1) << 7) | (byte & 0x7F)
                base = _read_pack_object(repo, pack_path, offset - distance, width, depth + 1)
            elif kind == 7:
                # The base is another object, named by its id.
                base_sha = header[position:position + width].hex()
                position += width
                base = _object(repo, base_sha)
            if base is None:
                return None
            stream.seek(offset + position)
            delta = _inflate(stream, size)
            if delta is None:
                return None
            payload = _apply_delta(base[1], delta)
            if payload is None:
                return None
            return base[0], payload
    except (OSError, ValueError, zlib.error):
        return None


def _packed_object(repo, sha, depth=0):
    """The type and the payload of one packed object, or None."""
    if depth > 50:
        return None
    width = _hash_width(repo)
    for index_path in _pack_indexes(repo):
        found = _index_find(index_path, sha, width)
        if found is None:
            continue
        offset, pack_path = found
        return _read_pack_object(repo, pack_path, offset, width, depth + 1)
    return None


# ---------------------------------------------------------------------------
# The configuration
# ---------------------------------------------------------------------------


def _config_header(header):
    """The section and the subsection of one configuration header."""
    if '"' in header:
        quote = header.find('"')
        section = header[:quote].strip()
        rest = header[quote + 1:]
        end = rest.find('"')
        if end < 0:
            return None
        subsection = rest[:end]
        if rest[end + 1:].strip():
            return None
    elif "." in header:
        section, _, subsection = header.partition(".")
        section = section.strip()
        subsection = subsection.strip()
    else:
        section, subsection = header, None
    if not section:
        return None
    return section.lower(), subsection


def _config_value(raw):
    """The value of one configuration entry, without its quotes."""
    value = raw.strip()
    if value.startswith('"'):
        return _quoted_value(value)
    for index, char in enumerate(value):
        if char in "#;" and index and value[index - 1].isspace():
            return value[:index].strip()
    return value


def _quoted_value(value):
    """The value of one quoted configuration entry."""
    out = []
    index = 1
    escapes = {"n": "\n", "t": "\t", "b": "\b", "\\": "\\", '"': '"'}
    while index < len(value):
        char = value[index]
        if char == '"':
            break
        if char == "\\" and index + 1 < len(value):
            index += 1
            out.append(escapes.get(value[index], value[index]))
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _config_entries(path):
    """Every entry of one configuration file.

    None means the file holds something this module does not model, such as
    an include of another file, so the Git binary has to answer.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
    except OSError:
        return []
    entries = []
    section = ""
    subsection = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line[0] == "[":
            end = line.find("]")
            if end < 0:
                return None
            parsed = _config_header(line[1:end].strip())
            if parsed is None:
                return None
            section, subsection = parsed
            if section in {"include", "includeif"}:
                return None
            continue
        name, separator, value = line.partition("=")
        if not separator:
            continue
        entries.append((section, subsection, name.strip().lower(), _config_value(value)))
    return entries


def _config_paths(repo):
    """The configuration files Git reads, in the order Git reads them."""
    paths = []
    if not os.environ.get("GIT_CONFIG_NOSYSTEM"):
        system = os.environ.get("GIT_CONFIG_SYSTEM")
        paths.append(Path(system) if system else Path("/etc/gitconfig"))
    global_path = os.environ.get("GIT_CONFIG_GLOBAL")
    if global_path:
        paths.append(Path(global_path))
    else:
        home = Path.home()
        xdg = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
        paths.append(Path(xdg) / "git" / "config")
        paths.append(home / ".gitconfig")
    paths.append(repo.gitdir / "config")
    worktree = repo.gitdir / "config.worktree"
    try:
        if worktree.exists():
            paths.append(worktree)
    except OSError:
        pass
    return paths


def _expand_url(url, rules):
    """The URL Git reports after the insteadOf rules are applied.

    The longest matching prefix wins.  When two rules match equally long,
    the one Git reads first wins, which is the one in the configuration file
    Git reads first.
    """
    best = None
    for base, prefix in rules:
        if not prefix or not url.startswith(prefix):
            continue
        if best is None or len(prefix) > len(best[1]):
            best = (base, prefix)
    if best is None:
        return url
    base, prefix = best
    return base + url[len(prefix):]


def remote_url(cwd, name):
    """The URL Git reports for one remote, or None when Git has to answer.

    This is the answer of ``git remote get-url <name>``.  Git rewrites the
    URL with the ``url.<base>.insteadOf`` rules while it reads it, so the
    raw value of the configuration is not the answer.

    None means the answer is not the one this module can give with
    certainty: the remote is not one of this repository, the configuration
    is not one this module reads, or two configuration files name different
    URLs for the remote and Git itself has to say which one it uses.
    """
    if any(os.environ.get(name) for name in _UNMODELLED_CONFIG_ENVIRONMENT):
        return None
    repo = discover(cwd)
    if repo is None:
        return None
    entries = []
    for path in _config_paths(repo):
        found = _config_entries(path)
        if found is None:
            return None
        entries.extend(found)
    local = _config_entries(repo.gitdir / "config")
    if local is None:
        return None
    section = 'remote "%s"' % name
    if not any(item[0] == "remote" and item[1] == name for item in local):
        # A remote that only the global configuration names is not a remote
        # of this repository, and Git does not know it.
        return None
    url = None
    for item_section, item_subsection, key, value in entries:
        if item_section == "remote" and item_subsection == name and key == "url":
            url = value
            break
    local_url = None
    for item_section, item_subsection, key, value in local:
        if item_section == "remote" and item_subsection == name and key == "url":
            local_url = value
            break
    if local_url is not None and url is not None and local_url != url:
        # Git reads the configuration files in order and takes the first
        # URL it finds.  Two files that disagree are a question only Git
        # answers.
        return None
    if url is None:
        # Git reports the name of a remote that has no URL at all.
        return name
    rules = []
    for item_section, item_subsection, key, value in entries:
        if item_section == "url" and key == "insteadof":
            rules.append((item_subsection, value))
    return _expand_url(url, rules)


# ---------------------------------------------------------------------------
# The remotes
# ---------------------------------------------------------------------------


def _local_path(url):
    """The local directory a remote URL names, or None."""
    if not url:
        return None
    if url.startswith("file://"):
        url = url[len("file://"):]
        if url.startswith("localhost/"):
            url = url[len("localhost"):]
    elif "://" in url or "@" in url and ":" in url.split("@", 1)[1]:
        return None
    if url.startswith("~"):
        return None
    try:
        candidate = Path(url)
    except (OSError, ValueError):
        return None
    if not candidate.is_absolute():
        return None
    return candidate


def _remote_refs(path):
    """Every reference of a local repository, or None."""
    refs = {}
    root = path / "refs"
    try:
        for base, _directories, files in os.walk(root):
            for name in files:
                full = Path(base) / name
                text = _read_text(full)
                if text is None:
                    continue
                value = text.strip()
                if not _OBJECT_ID.match(value):
                    continue
                refs[str(full.relative_to(path)).replace(os.sep, "/")] = value
    except OSError:
        return None
    packed = _read_text(path / "packed-refs")
    if packed is not None:
        for raw in packed.splitlines():
            line = raw.strip()
            if not line or line[0] in "#^":
                continue
            parts = line.split()
            if len(parts) == 2 and _OBJECT_ID.match(parts[0]):
                refs.setdefault(parts[1], parts[0])
    return refs


def remote_ref(cwd, remote, pattern):
    """The object id one remote branch points at, or None.

    This is the answer of ``git ls-remote <remote> <pattern>`` for a remote
    that is a directory on this machine.  A remote that lives somewhere
    else is asked over the network, so the Git binary has to answer.
    """
    repo = discover(cwd)
    if repo is None:
        return None
    if not pattern or "/" not in pattern:
        # A pattern without a slash matches the tail of a reference name, so
        # it can match more than one reference.
        return None
    url = remote
    entries = []
    for path in _config_paths(repo):
        found = _config_entries(path)
        if found is None:
            return None
        entries.extend(found)
    if not url.startswith("/") and not url.startswith(".") and "://" not in url:
        for item_section, item_subsection, key, value in entries:
            if item_section == "remote" and item_subsection == url and key == "url":
                url = value
                break
    path = _local_path(url)
    if path is None or not path.is_dir():
        return None
    refs = _remote_refs(path)
    if refs is None:
        return None
    value = refs.get(pattern)
    if value is None:
        return ""
    return value
