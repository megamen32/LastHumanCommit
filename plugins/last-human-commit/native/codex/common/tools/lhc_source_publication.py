"""Narrow source-only readiness and Git publication evidence adapter.

This adapter proves one exact candidate tree. It does not grant permission,
infer a destination, run product code, or treat remote existence as publication.
"""
import hashlib
import json
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            timeout=5)
    if result.returncode:
        raise ValueError("source-publication Git proof unavailable: " + " ".join(args[:2]))
    return result.stdout


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def historical_publication_commit_matches(metadata, root):
    """Check immutable local Git objects for the original published candidate."""
    try:
        root = Path(root).resolve(strict=True)
        base = str(metadata['base'])
        commit = str(metadata['published_commit'])
        _git(root, 'cat-file', '-e', base + '^{commit}')
        _git(root, 'cat-file', '-e', commit + '^{commit}')
        ancestry = _git(root, 'rev-list', '--parents', '-n', '1', commit).decode().strip().split()
        if ancestry != [commit, base]:
            return False
        paths = set(_git(root, 'diff', '--name-only', '--no-renames', base, commit).decode().splitlines())
        expected_files = metadata.get('owned_files') or {}
        if paths != set(expected_files):
            return False
        for name, expected_hash in expected_files.items():
            blob = _git(root, 'show', commit + ':' + name)
            if _sha(blob) != expected_hash:
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError):
        return False


def _output_exceeds_native_cap(encoded):
    # Text that resembles a persistence marker may be ordinary file content.
    # Below the native cap, exact candidate SHA is the completeness proof.
    return len(encoded) >= 65536


def _owned_file(root, name):
    root = root.resolve()
    raw = Path(name)
    raw = raw if raw.is_absolute() else root / raw
    current = raw
    while current != root and current != current.parent:
        if current.is_symlink():
            raise ValueError("source-publication owned paths cannot traverse symlinks")
        current = current.parent
    if current != root:
        raise ValueError("source-publication owned path escapes the product root")
    resolved = raw.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("source-publication owned path escapes the product root") from error
    return resolved


def _scope_permission(scope, root, paths, remote, branch):
    """Require one current, affirmative imperative bound to exact source/ref."""
    if not re.search(r"\bsource[- ]only\b", scope, re.I):
        return None
    clauses = re.split(r"(?<=[.!?;])\s+|\n", scope)
    ref = remote + "/" + branch
    root_token = re.compile(r"(?<![\w./-])" + re.escape(str(root)) + r"(?![\w./-])")
    if not root_token.search(scope):
        return None
    for path in paths:
        token = re.compile(r"(?<![\w./-])" + re.escape(path) + r"(?![\w./-])")
        if not token.search(scope):
            return None
    revocation = re.compile(
        r"\b(?:do\s+not|don't|never|no)\s+(?:publish|publishing|publication|push)\b|"
        r"\b(?:hold|pause|stop|cancel|revoke)\w*\b[^.!?\n]{0,80}\b(?:publish|publishing|publication|push)\b|"
        r"\b(?:publish|publishing|publication|push)\b[^.!?\n]{0,80}\b(?:on\s+hold|paused|cancelled|revoked)\b|"
        r"нельзя\b[^.!?\n]{0,80}(?:публиков|пуш)|не\s+(?:публикуй|пушь)", re.I)
    for index, clause in enumerate(clauses):
        candidate = clause.strip()
        if not candidate or candidate.startswith((">", "\"", "'", "`")):
            continue
        if not re.match(r"^(?:please\s+)?(?:publish|push)\b", candidate, re.I):
            continue
        if re.search(r"\b(?:no|not|never|don't|do not|without)\b|нельзя|не\s+(?:пуш|публику)", candidate, re.I):
            continue
        ref_text = candidate.rstrip(".!?;")
        if (root_token.search(candidate) and
                all(re.search(r"(?<![\w./-])" + re.escape(path) + r"(?![\w./-])", candidate)
                    for path in paths) and
                re.search(r"(?<![\w./-])" + re.escape(ref) + r"(?![\w./-])", ref_text, re.I)):
            if revocation.search(candidate) or any(revocation.search(later.strip()) for later in clauses[index + 1:]
                   if later.strip() and not later.strip().startswith((">", "\"", "'", "`"))):
                return None
            return candidate
    return None


def capture_contract(outcome, source, root, paths, remote, branch, repository,
                     canary_target, target, expected, product_root_scope_allowed):
    """Snapshot a source-only candidate and its exact authorized publication ref."""
    if not source:
        raise ValueError("source-publication needs the exact current native source assignment")
    if not root.is_absolute() or not root.is_dir() or not paths:
        raise ValueError("source-publication needs an absolute product root and exact owned paths")
    scope = source.get("scope_prompt") or source.get("prompt") or ""
    permission = _scope_permission(scope, root, paths, remote, branch)
    if not permission:
        raise ValueError("source-publication needs a current source-only imperative publish/push assignment bound to root, owned paths, remote and branch")
    if not product_root_scope_allowed(outcome, source, root, paths):
        raise ValueError("source-publication root and every owned path need the exact current native assignment")
    if canary_target != "project:" + str(root.resolve()):
        raise ValueError("source-publication canary must bind the exact plain project root")
    expected_target = f"git ls-remote {remote} refs/heads/{branch}"
    if target != expected_target:
        raise ValueError("source-publication target must explicitly bind git ls-remote, remote and branch")
    if expected not in {"candidate", "candidate:auto"}:
        raise ValueError("source-publication expected value is derived from the immutable candidate; use candidate")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    base_lines = _git(root, "ls-remote", remote, "refs/heads/" + branch).decode().splitlines()
    base_rows = [line.split() for line in base_lines if len(line.split()) == 2]
    if len(base_rows) != 1 or base_rows[0][1] != "refs/heads/" + branch or not re.fullmatch(r"[0-9a-f]{40,64}", base_rows[0][0]):
        raise ValueError("source-publication base ref readback is missing or ambiguous")
    base = base_rows[0][0]
    _git(root, "cat-file", "-e", base + "^{commit}")
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head],
                      capture_output=True, timeout=5).returncode:
        raise ValueError("source-publication candidate is not fast-forward from the current remote base")
    files = {}
    for name in paths:
        file_path = _owned_file(root, name)
        if not file_path.is_file():
            raise ValueError("source-publication requires every owned candidate file to exist as a regular file")
        files[name] = _sha(file_path.read_bytes())
    body = {"root": str(root.resolve()), "repository": repository, "remote": remote,
            "branch": branch, "ref": "refs/heads/" + branch, "base": base,
            "candidate_head": head, "owned_files": files,
            "permission_source": source.get("source"), "permission_quote": permission}
    # Candidate identity is product content/root only. Remote, branch and
    # permission are separate publication gates and must not stale source reads.
    candidate = {key: body[key] for key in ("root", "candidate_head", "owned_files")}
    fingerprint = hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": "lhc-source-publication-v1", **body, "candidate_fingerprint": fingerprint}


def permission_unchanged(metadata, source, corrections=()):
    """Revalidate the original source-bound push clause and later revocations."""
    if not source or source.get("source") != metadata.get("permission_source"):
        return False
    root = Path(metadata["root"]).resolve()
    paths = list(metadata.get("owned_files", {}))
    scope = source.get("scope_prompt") or source.get("prompt") or ""
    quote = _scope_permission(scope, root, paths, metadata["remote"], metadata["branch"])
    if quote != metadata.get("permission_quote"):
        return False
    revocation = re.compile(r"\b(?:no|do not|don't|never|without)\b[^.!?\n]{0,120}\b(?:push|publish)\b|нельзя[^.!?\n]{0,120}(?:пуш|публику)", re.I)
    return not any(revocation.search(str(correction)) for correction in corrections)


def _command(call):
    args = call.get("arguments") or call.get("input") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return [], None
    if not isinstance(args, dict):
        return [], None
    raw = str(args.get("cmd") or args.get("command") or "")
    try:
        words = shlex.split(raw)
    except ValueError:
        return [], None
    if not words:
        return [], None
    if Path(words[0]).name in {"bash", "sh", "zsh"}:
        if len(words) != 3 or words[1] not in {"-c", "-lc"}:
            return [], None
        try:
            words = shlex.split(words[2])
        except ValueError:
            return [], None
    if any(word in {";", "&&", "||", "|", ">", "<"} for word in words):
        return [], None
    return words, args


def _workdir(args, call, root):
    value = args.get("workdir") or args.get("cwd") or call.get("_native_cwd")
    if not value:
        return None
    uri = urlsplit(str(value))
    path = Path(unquote(uri.path)) if uri.scheme == "file" and uri.netloc in {"", "localhost"} else Path(str(value))
    return path.resolve() if path.is_absolute() else (Path(call.get("_native_cwd") or root) / path).resolve()


def source_readiness(metadata, observations, root, *, floor=None, before=None):
    """Require full-file reads and matching hashes for every owned candidate."""
    if not isinstance(metadata, dict) or metadata.get("schema") != "lhc-source-publication-v1":
        raise ValueError("source-publication candidate snapshot is missing")
    if Path(metadata.get("root", "/unknown")).resolve() != root.resolve():
        raise ValueError("source-publication product root changed")
    current = {}
    for name in metadata.get("owned_files", {}):
        file_path = _owned_file(root, name)
        if not file_path.is_file():
            raise ValueError("source-publication candidate file is missing or unsafe")
        current[name] = _sha(file_path.read_bytes())
    if current != metadata.get("owned_files"):
        raise ValueError("source-publication candidate bytes changed after contract")
    read_refs, hash_refs, chunk_reads, chunk_read_refs = {}, {}, {}, {}
    for call, output in observations:
        if floor or before is not None:
            try:
                stamp = datetime.fromisoformat(str(call.get("_source_time") or "").replace("Z", "+00:00"))
                if floor and stamp < datetime.fromisoformat(str(floor).replace("Z", "+00:00")):
                    continue
                if before is not None and call.get("_source_index") is not None and call["_source_index"] >= before:
                    continue
            except ValueError:
                continue
        words, args = _command(call)
        if not words or not args or _workdir(args, call, root) != root.resolve():
            continue
        path_args = []
        read_kind = None
        chunk_range = None
        if len(words) == 2 and Path(words[0]).name == "cat" and not words[1].startswith("-"):
            path_args, read_kind = [words[1]], "read"
        elif (len(words) == 4 and Path(words[0]).name == "sed" and words[1] == "-n"
              and not words[3].startswith("-")):
            match = re.fullmatch(r"([1-9][0-9]*),([1-9][0-9]*)p", words[2])
            if match:
                start, end = (int(value) for value in match.groups())
                if end >= start and end - start + 1 <= 300:
                    path_args, read_kind = [words[3]], "chunk"
                    chunk_range = (start, end)
        elif Path(words[0]).name == "sha256sum" and len(words) >= 2:
            path_args = words[1:] if words[1] != "--" else words[2:]
            read_kind = "hash"
        elif Path(words[0]).name == "shasum" and len(words) == 4 and words[1:3] == ["-a", "256"]:
            path_args, read_kind = [words[3]], "hash"
        if not path_args or len(set(path_args)) != len(path_args):
            continue
        targets = []
        for path_arg in path_args:
            target = Path(path_arg)
            target = (target if target.is_absolute() else root / target).resolve()
            try:
                relative = target.relative_to(root.resolve()).as_posix()
            except ValueError:
                targets = []
                break
            targets.append((relative, target))
        if (not targets or any(relative not in metadata["owned_files"] for relative, _ in targets)
                or call.get("_exit_code", 0) != 0):
            continue
        call_id = call.get("call_id")
        if not call_id:
            continue
        if read_kind == "read":
            relative, _ = targets[0]
            encoded = output.encode("utf-8")
            if (not _output_exceeds_native_cap(encoded)
                    and _sha(encoded) == metadata["owned_files"][relative]):
                read_refs.setdefault(relative, []).append(call_id)
        elif read_kind == "chunk":
            relative, _ = targets[0]
            encoded = output.encode("utf-8")
            start, end = chunk_range
            requested_lines = end - start + 1
            output_lines = len(output.splitlines())
            if (not _output_exceeds_native_cap(encoded)
                    and output_lines <= requested_lines):
                chunk_reads.setdefault(relative, []).append(
                    (start, end, encoded, output_lines, call_id))
        elif read_kind == "hash":
            rows = [line.split(maxsplit=1) for line in output.splitlines() if line.strip()]
            returned = {}
            for row in rows:
                if len(row) != 2 or not re.fullmatch(r"[0-9a-f]{64}", row[0]):
                    returned = {}
                    break
                returned_path = Path(row[1].lstrip("*"))
                returned_path = (returned_path if returned_path.is_absolute() else root / returned_path).resolve()
                try:
                    returned_name = returned_path.relative_to(root.resolve()).as_posix()
                except ValueError:
                    returned = {}
                    break
                returned[returned_name] = row[0]
            expected_names = {name for name, _ in targets}
            if set(returned) == expected_names and all(returned[name] == metadata["owned_files"][name] for name in expected_names):
                for name in expected_names:
                    hash_refs.setdefault(name, []).append(call_id)
    for name, chunks in chunk_reads.items():
        expected_start = 1
        assembled = bytearray()
        chunk_call_ids = []
        complete = False
        for start, end, content, line_count, call_id in chunks:
            requested_lines = end - start + 1
            if complete or start != expected_start:
                complete = False
                break
            chunk_call_ids.append(call_id)
            if line_count < requested_lines:
                assembled.extend(content)
                complete = True
            else:
                assembled.extend(content)
                expected_start = end + 1
        if complete and _sha(bytes(assembled)) == metadata["owned_files"].get(name):
            chunk_read_refs[name] = chunk_call_ids
    groups = {}
    for name, candidate_sha in metadata["owned_files"].items():
        groups.setdefault(candidate_sha, []).append(name)
    read_calls, read_aliases = {}, {}
    missing = [name for name in metadata["owned_files"] if not hash_refs.get(name)]
    for names in groups.values():
        representative = next((name for name in names if read_refs.get(name)), None)
        representative = representative or next((name for name in names if chunk_read_refs.get(name)), None)
        if representative is None:
            missing.extend(names)
            continue
        proof = (read_refs[representative][-1] if read_refs.get(representative)
                 else chunk_read_refs[representative])
        for name in names:
            read_calls[name] = proof
            read_aliases[name] = representative
    missing = list(dict.fromkeys(missing))
    if missing:
        raise ValueError("source readiness needs native full-file reads and matching hash evidence for every owned path: " + ", ".join(missing))
    return {"read_calls": read_calls,
            "read_aliases": read_aliases,
            "hash_calls": {name: hash_refs[name][-1] for name in metadata["owned_files"]}}


def publisher_push(outcome, metadata, floor):
    """Bind one successful native publisher push to the authorized exact ref."""
    location = Path(outcome.get("native_source") or "")
    try:
        raw = location.read_bytes()
    except OSError as error:
        raise ValueError("source-publication native publisher source is unavailable") from error
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("source-publication native publisher source exceeds bounded window")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    header = next((row.get("payload", {}) for row in rows if row.get("type") == "session_meta"), {})
    expected_session_root = Path(outcome.get("cwd") or metadata["root"]).resolve()
    if (header.get("id") != outcome.get("owner", {}).get("session_id") or
            Path(header.get("cwd", "/unknown")).resolve() != expected_session_root):
        raise ValueError("source-publication publisher native identity/root mismatch")
    for row in rows:
        payload = row.get("payload", {})
        item = payload.get("item") or {}
        if row.get("type") != "event_msg" or payload.get("type") != "item_completed" or item.get("type") != "CommandExecution":
            continue
        if item.get("exit_code") != 0 or not row.get("timestamp"):
            continue
        try:
            stamp = datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
            floor_time = datetime.fromisoformat(str(floor).replace("Z", "+00:00"))
        except ValueError:
            continue
        if stamp < floor_time:
            continue
        argv = item.get("command") or []
        if len(argv) == 3 and Path(argv[0]).name in {"bash", "sh", "zsh"} and argv[1] in {"-c", "-lc"}:
            try:
                words = shlex.split(argv[2])
            except ValueError:
                continue
        else:
            words = [str(value) for value in argv]
        if (len(words) != 4 or words[:2] != ["git", "push"] or words[2] != metadata["remote"] or
                words[3] not in {metadata["branch"], "HEAD:" + metadata["ref"], "HEAD:" + metadata["branch"]}):
            continue
        workdir = item.get("cwd") or ""
        uri = urlsplit(workdir)
        path = Path(unquote(uri.path)) if uri.scheme == "file" and uri.netloc in {"", "localhost"} else Path(workdir)
        if not path.is_absolute() or path.resolve() != Path(metadata["root"]).resolve():
            continue
        return {"call_id": str(item.get("id") or "native-push"), "at": stamp.isoformat()}
    raise ValueError("source-publication needs a successful current native git push to the exact authorized ref")


def publication_readback(metadata, observations, root, outcome, floor, *, before=None):
    """Verify current remote ref, native push, fast-forward tree and exact blobs."""
    publisher = publisher_push(outcome, metadata, floor)
    matches = []
    command = ["git", "ls-remote", metadata["remote"], metadata["ref"]]
    for call, output in observations:
        words, args = _command(call)
        if before is not None and call.get("_source_index") is not None and call["_source_index"] >= before:
            continue
        try:
            stamp = datetime.fromisoformat(str(call.get("_source_time") or "").replace("Z", "+00:00"))
            if stamp < datetime.fromisoformat(str(floor).replace("Z", "+00:00")):
                continue
        except ValueError:
            continue
        if (words == command and args and _workdir(args, call, root) == root.resolve() and
                call.get("_exit_code", 0) == 0):
            try:
                readback_at = datetime.fromisoformat(str(call.get("_source_time") or "").replace("Z", "+00:00"))
                if readback_at < datetime.fromisoformat(publisher["at"].replace("Z", "+00:00")):
                    continue
            except ValueError:
                continue
            rows = [line.split() for line in output.splitlines() if len(line.split()) == 2]
            if len(rows) == 1 and rows[0][1] == metadata["ref"] and re.fullmatch(r"[0-9a-f]{40,64}", rows[0][0]):
                matches.append((call.get("call_id"), rows[0][0]))
    if len(matches) != 1:
        raise ValueError("source-publication needs one exact current remote branch readback after the native push")
    readback_call, commit = matches[0]
    from lhc_outcome import remote_binding
    if remote_binding(root, metadata["remote"]) != metadata.get("repository"):
        raise ValueError("source-publication repository identity changed after contract")
    current_rows = _git(root, "ls-remote", metadata["remote"], metadata["ref"]).decode().splitlines()
    if current_rows != [commit + "\t" + metadata["ref"]]:
        raise ValueError("source-publication remote ref changed after the native readback")
    base = metadata["base"]
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, commit],
                      capture_output=True, timeout=5).returncode:
        raise ValueError("published source commit is not fast-forward from the bound current remote base")
    changed = set(_git(root, "diff", "--name-only", base, commit).decode().splitlines())
    if changed != set(metadata["owned_files"]):
        raise ValueError("published source commit changed paths outside or missing from the exact owned set")
    for name, expected in metadata["owned_files"].items():
        committed = _git(root, "show", commit + ":" + name)
        if _sha(committed) != expected:
            raise ValueError("published source commit blob differs from the immutable candidate: " + name)
    return {"publisher_call": publisher["call_id"], "publisher_at": publisher["at"],
            "readback_call": readback_call, "commit": commit, "base": base, "ref": metadata["ref"]}
