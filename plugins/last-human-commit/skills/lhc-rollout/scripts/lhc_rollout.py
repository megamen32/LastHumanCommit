#!/usr/bin/env python3
"""Manifest-driven, rollback-safe rollout of one committed LHC tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Mapping, Sequence


CONFIRM_PREFIX = "sha256:"
REPORT_PREFIX = "__LHC_ROLLOUT_REPORT__="


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _relative(value: object, field: str) -> Path:
    path = Path(_text(value, field))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a safe relative path")
    return path


def _inside(root: Path, relative: object, field: str) -> Path:
    path = (root / _relative(relative, field)).resolve(strict=False)
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{field} escapes its declared root") from error
    return path


def _run(command: Sequence[str], *, input_text: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=timeout,
    )


def _git(repo: Path, *arguments: str) -> str:
    completed = _run(["git", "-C", str(repo), *arguments])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def _source_repo(manifest: Mapping[str, Any]) -> Path:
    source = manifest.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("source must be an object")
    return Path(_text(source.get("repo"), "source.repo")).expanduser().resolve(strict=True)


def _project_tmp(repo: Path) -> Path:
    resolved_repo = repo.resolve(strict=True)
    root = resolved_repo / ".tmp"
    if root.is_symlink():
        raise RuntimeError(f"{root} must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    try:
        resolved_root.relative_to(resolved_repo)
    except ValueError as error:
        raise RuntimeError(f"{root} escapes project root {resolved_repo}") from error
    ignored = _run(
        ["git", "-C", str(resolved_repo), "check-ignore", "--quiet", "--", ".tmp/"]
    )
    if ignored.returncode != 0:
        raise RuntimeError(f"{resolved_repo} must ignore .tmp/ before rollout staging")
    return resolved_root


def tree_digest(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
        count += 1
    return CONFIRM_PREFIX + digest.hexdigest(), count


def _export_git_tree(repo: Path, commit: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.NamedTemporaryFile(
        prefix="lhc-rollout-", suffix=".tar", dir=destination.parent
    ) as archive_file:
        completed = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", commit],
            check=False,
            stdout=archive_file,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode(errors="replace").strip() or "git archive failed")
        archive_file.flush()
        with tarfile.open(archive_file.name, "r:") as archive:
            root = destination.resolve()
            for member in archive.getmembers():
                path = (destination / member.name).resolve(strict=False)
                try:
                    path.relative_to(root)
                except ValueError as error:
                    raise RuntimeError(f"unsafe Git archive member: {member.name}") from error
                if member.issym() or member.islnk() or member.isdev():
                    raise RuntimeError(f"unsupported Git archive member: {member.name}")
            archive.extractall(destination)


def _copy_committed(source_root: Path, relative: object, destination: Path, field: str) -> None:
    source = _inside(source_root, relative, field)
    if source.is_dir():
        shutil.copytree(source, destination)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    else:
        raise ValueError(f"{field} does not exist in the committed revision")


def build_bundle(manifest: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    source = manifest.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("source must be an object")
    repo = _source_repo(manifest)
    revision = _text(source.get("revision", "HEAD"), "source.revision")
    commit = _git(repo, "rev-parse", f"{revision}^{{commit}}")
    version_length = int(source.get("versionLength", 7))
    if version_length < 7 or version_length > 40:
        raise ValueError("source.versionLength must be between 7 and 40")
    version = commit[:version_length]

    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(
        prefix="lhc-rollout-source-", dir=_project_tmp(repo)
    ) as temporary:
        checkout = Path(temporary) / "checkout"
        _export_git_tree(repo, commit, checkout)
        version_root = destination / "version"
        version_root.mkdir()
        entries = source.get("version")
        if not isinstance(entries, list) or not entries:
            raise ValueError("source.version must be a non-empty array")
        for index, raw in enumerate(entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"source.version[{index}] must be an object")
            target = _inside(version_root, raw.get("destination"), f"source.version[{index}].destination")
            _copy_committed(checkout, raw.get("source"), target, f"source.version[{index}].source")
        (version_root / "VERSION").write_text(version + "\n", encoding="utf-8")

        routers = source.get("routers", {})
        if not isinstance(routers, Mapping):
            raise ValueError("source.routers must be an object")
        router_root = destination / "routers"
        router_root.mkdir()
        for name, relative in sorted(routers.items()):
            safe_name = _relative(name, f"source.routers.{name}")
            _copy_committed(checkout, relative, router_root / safe_name, f"source.routers.{name}")

        copies = source.get("copies", {})
        if not isinstance(copies, Mapping):
            raise ValueError("source.copies must be an object")
        copy_root = destination / "copies"
        copy_root.mkdir()
        for name, relative in sorted(copies.items()):
            safe_name = _relative(name, f"source.copies.{name}")
            _copy_committed(checkout, relative, copy_root / safe_name, f"source.copies.{name}")

    digest, files = tree_digest(destination / "version")
    identity = {
        "commit": commit,
        "version": version,
        "digest": digest,
        "files": files,
        "routers": sorted(str(item) for item in routers),
        "copies": sorted(str(item) for item in copies),
    }
    (destination / "identity.json").write_text(json.dumps(identity, sort_keys=True) + "\n", encoding="utf-8")
    return identity


def _marker_parts(text: str, begin: str, end: str) -> tuple[str, str, str]:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError("router must contain exactly one managed marker block")
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    return text[:start], text[start:finish], text[finish:]


def _source_block(path: Path, begin: str, end: str) -> str:
    _, block, _ = _marker_parts(path.read_text(encoding="utf-8"), begin, end)
    return block


def _outside_digest(text: str, begin: str, end: str) -> str:
    before, _, after = _marker_parts(text, begin, end)
    return hashlib.sha256((before + after).encode("utf-8")).hexdigest()


def _validate_incoming_role_references(
    block: str,
    router_path: Path,
    bundle: Path,
    variables: Mapping[str, str],
) -> int:
    references = sorted(set(re.findall(r"`([^`]*common/agents/[^`]+\.md)`", block)))
    if not references:
        raise ValueError(f"router has no role references: {router_path}")
    current = Path(variables["current"])
    runtime = Path(variables["runtime"]) if "runtime" in variables else None
    for value in references:
        path = Path(value)
        candidate: Path
        if path.is_absolute():
            try:
                relative = path.relative_to(current)
            except ValueError:
                candidate = path
            else:
                candidate = bundle / "version" / relative
        elif runtime is not None and path.parts and path.parts[0] == runtime.name:
            candidate = bundle / "version" / Path(*path.parts[1:])
        else:
            candidate = router_path.parent / path
        if not candidate.is_file():
            raise ValueError(f"incoming router role reference is missing: {value}")
    return len(references)


def _atomic_write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.lhc-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _newest_age(path: Path) -> int | None:
    if not path.exists():
        return None
    mtimes = [item.lstat().st_mtime for item in path.rglob("*")]
    mtimes.append(path.lstat().st_mtime)
    return int(time.time() - max(mtimes))


def _install(manifest: Mapping[str, Any]) -> dict[str, Any]:
    install = manifest.get("install")
    if not isinstance(install, Mapping):
        raise ValueError("install must be an object")
    begin = _text(install.get("markerBegin"), "install.markerBegin")
    end = _text(install.get("markerEnd"), "install.markerEnd")
    if begin == end:
        raise ValueError("marker boundaries must differ")
    fresh = int(install.get("freshSeconds", 300))
    if fresh < 0:
        raise ValueError("install.freshSeconds must not be negative")
    raw_runtime = install.get("projectRuntime", ".last-human-commit")
    if raw_runtime is None:
        project_runtime = None
        project_replace = _replacement_map(
            install.get("projectReplace", install.get("globalReplace", {})),
            "install.projectReplace",
        )
    else:
        project_runtime = _relative(raw_runtime, "install.projectRuntime")
        project_replace = _replacement_map(install.get("projectReplace", {}), "install.projectReplace")
    return {
        "store": _relative(install.get("store"), "install.store"),
        "projectRuntime": project_runtime,
        "rollback": _relative(
            install.get("rollback", "rollbacks/{version}-lhc-rollout"),
            "install.rollback",
        ),
        "markerBegin": begin,
        "markerEnd": end,
        "freshSeconds": fresh,
        "globalReplace": _replacement_map(install.get("globalReplace", {}), "install.globalReplace"),
        "projectReplace": project_replace,
    }


def _replacement_map(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return {_text(key, f"{field}.key"): _text(item, f"{field}.{key}") for key, item in value.items()}


def _target_home(target: Mapping[str, Any]) -> Path:
    return Path(_text(target.get("home"), "target.home")).expanduser().resolve()


def _select_rollback_root(
    store: Path,
    install: Mapping[str, Any],
    version: str,
) -> tuple[Path, str | None]:
    base = _inside(
        store,
        str(install["rollback"]).format(version=version),
        "install.rollback",
    )
    for attempt in range(100):
        candidate = base if attempt == 0 else base.with_name(f"{base.name}-retry-{attempt}")
        if not candidate.exists():
            return candidate, None
        receipt_path = candidate / "rollout.json"
        if not receipt_path.is_file():
            raise ValueError(f"rollback receipt is missing: {receipt_path}")
        status = _read_json(receipt_path).get("status")
        if status == "complete":
            return candidate, "complete"
        if status != "rolled_back":
            raise ValueError(f"rollback receipt has invalid status: {receipt_path}")
    raise ValueError(f"too many rolled-back retries for version {version}")


def _router_plan(
    *,
    root: Path,
    entries: object,
    bundle: Path,
    replacements: Mapping[str, str],
    variables: Mapping[str, str],
    install: Mapping[str, Any],
    field: str,
) -> list[dict[str, Any]]:
    if not isinstance(entries, list):
        raise ValueError(f"{field} must be an array")
    plans = []
    for index, raw in enumerate(entries):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        path = _inside(root, raw.get("path"), f"{field}[{index}].path")
        template_relative = _relative(raw.get("template"), f"{field}[{index}].template")
        template = _inside(bundle / "routers", str(template_relative), f"{field}[{index}].template")
        block = _source_block(template, install["markerBegin"], install["markerEnd"])
        for old, replacement in replacements.items():
            block = block.replace(old, replacement.format(**variables))
        role_references = _validate_incoming_role_references(
            block, path, bundle, variables
        )
        outside = None
        mode = 0o644
        age = None
        action = "create"
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"router is not a regular file: {path}")
            text = path.read_text(encoding="utf-8")
            _, observed_block, _ = _marker_parts(
                text, install["markerBegin"], install["markerEnd"]
            )
            outside = _outside_digest(text, install["markerBegin"], install["markerEnd"])
            mode = stat.S_IMODE(path.stat().st_mode)
            age = int(time.time() - path.stat().st_mtime)
            action = "noop" if observed_block == block else "replace"
            if action == "replace" and age < install["freshSeconds"]:
                raise ValueError(f"router changed within freshness window: {path}")
        plans.append(
            {
                "path": str(path),
                "template": str(template_relative),
                "block": block,
                "outside": outside,
                "mode": mode,
                "age": age,
                "action": action,
                "roleReferences": role_references,
            }
        )
    return plans


def preview_target(target: Mapping[str, Any], bundle: Path, install: Mapping[str, Any]) -> dict[str, Any]:
    identity = _read_json(bundle / "identity.json")
    home = _target_home(target)
    name = _text(target.get("name"), "target.name")
    store = _inside(home, str(install["store"]), "install.store")
    current = store / "current"
    if current.exists() and not current.is_symlink():
        raise ValueError(f"current exists and is not a symlink: {current}")
    version_target = store / "versions" / identity["version"]
    if version_target.exists():
        digest, files = tree_digest(version_target)
        if (digest, files) != (identity["digest"], identity["files"]):
            raise ValueError(f"immutable version collision: {version_target}")

    variables = {"home": str(home), "current": str(current), "version": identity["version"]}
    routers = _router_plan(
        root=home,
        entries=target.get("routers", []),
        bundle=bundle,
        replacements=install["globalReplace"],
        variables=variables,
        install=install,
        field=f"targets.{name}.routers",
    )
    projects = []
    raw_projects = target.get("projects", [])
    if not isinstance(raw_projects, list):
        raise ValueError(f"targets.{name}.projects must be an array")
    for index, raw in enumerate(raw_projects):
        if not isinstance(raw, Mapping):
            raise ValueError(f"targets.{name}.projects[{index}] must be an object")
        root = _inside(home, raw.get("path"), f"targets.{name}.projects[{index}].path")
        if not root.is_dir():
            raise ValueError(f"project root is missing: {root}")
        if install["projectRuntime"] is None:
            runtime = None
            previous = None
            action = "noop"
        else:
            runtime = _inside(root, str(install["projectRuntime"]), "install.projectRuntime")
            previous = runtime.with_name(f"{runtime.name}.prev-{identity['version']}")
            age = _newest_age(runtime)
            digest = tree_digest(runtime)[0] if runtime.is_dir() else None
            action = "noop" if digest == identity["digest"] else ("replace" if runtime.exists() else "create")
            if action != "noop" and age is not None and age < install["freshSeconds"]:
                raise ValueError(f"project runtime changed within freshness window: {runtime}")
            if action != "noop" and previous.exists():
                raise ValueError(f"project rollback target exists: {previous}")
        project_variables = {**variables, "project": str(root)}
        if runtime is not None:
            project_variables["runtime"] = str(runtime)
        project_routers = _router_plan(
            root=root,
            entries=raw.get("routers", []),
            bundle=bundle,
            replacements=install["projectReplace"],
            variables=project_variables,
            install=install,
            field=f"targets.{name}.projects[{index}].routers",
        )
        projects.append(
            {
                "root": str(root),
                "runtime": str(runtime) if runtime is not None else None,
                "previous": str(previous) if previous is not None else None,
                "action": action,
                "routers": project_routers,
            }
        )

    copies = []
    raw_copies = target.get("copies", [])
    if not isinstance(raw_copies, list):
        raise ValueError(f"targets.{name}.copies must be an array")
    for index, raw in enumerate(raw_copies):
        if not isinstance(raw, Mapping):
            raise ValueError(f"targets.{name}.copies[{index}] must be an object")
        source = _inside(bundle / "copies", raw.get("source"), f"targets.{name}.copies[{index}].source")
        destination = _inside(home, raw.get("path"), f"targets.{name}.copies[{index}].path")
        previous = destination.with_name(f"{destination.name}.prev-{identity['version']}")
        source_digest = tree_digest(source)[0] if source.is_dir() else hashlib.sha256(source.read_bytes()).hexdigest()
        observed = tree_digest(destination)[0] if destination.is_dir() else None
        action = "noop" if observed == source_digest else ("replace" if destination.exists() else "create")
        age = _newest_age(destination)
        if action != "noop" and age is not None and age < install["freshSeconds"]:
            raise ValueError(f"copy changed within freshness window: {destination}")
        if action != "noop" and previous.exists():
            raise ValueError(f"copy rollback target exists: {previous}")
        copies.append(
            {
                "source": str(source),
                "path": str(destination),
                "previous": str(previous),
                "digest": source_digest,
                "action": action,
            }
        )

    rollback_root, rollback_status = _select_rollback_root(
        store, install, identity["version"]
    )
    plan = {
        "name": name,
        "home": str(home),
        "transport": target.get("transport", "local"),
        "current": str(current),
        "currentBefore": os.readlink(current) if current.is_symlink() else None,
        "versionTarget": str(version_target),
        "rollbackRoot": str(rollback_root),
        "routers": routers,
        "projects": projects,
        "copies": copies,
    }
    has_changes = (
        plan["currentBefore"] != f"versions/{identity['version']}"
        or any(item["action"] != "noop" for item in routers)
        or any(item["action"] != "noop" for item in projects)
        or any(item["action"] != "noop" for item in copies)
    )
    if has_changes and rollback_status == "complete":
        raise ValueError(f"rollback receipt target exists: {rollback_root}")
    return plan


def _stable_plan(value: Any) -> Any:
    if isinstance(value, Mapping):
        stable = {}
        for key, item in sorted(value.items()):
            if key in {"age", "source"}:
                continue
            if key == "block":
                stable["blockSha256"] = hashlib.sha256(
                    str(item).encode("utf-8")
                ).hexdigest()
            else:
                stable[key] = _stable_plan(item)
        return stable
    if isinstance(value, list):
        return [_stable_plan(item) for item in value]
    return value


def _plan_digest(plan: Mapping[str, Any]) -> str:
    payload = json.dumps(_stable_plan(plan), sort_keys=True, separators=(",", ":"))
    return CONFIRM_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _confirmation(identity: Mapping[str, Any], targets: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(
        {"identity": identity, "targets": _stable_plan(list(targets))},
        sort_keys=True,
        separators=(",", ":"),
    )
    return CONFIRM_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _pack_bundle(bundle: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(bundle.rglob("*"), key=lambda item: item.relative_to(bundle).as_posix()):
            archive.add(path, arcname=path.relative_to(bundle).as_posix(), recursive=False)


def _extract_bundle(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            path = (destination / member.name).resolve(strict=False)
            try:
                path.relative_to(root)
            except ValueError as error:
                raise RuntimeError(f"unsafe bundle member: {member.name}") from error
            if member.issym() or member.islnk() or member.isdev():
                raise RuntimeError(f"unsupported bundle member: {member.name}")
        archive.extractall(destination)


def _ssh_base(target: Mapping[str, Any]) -> list[str]:
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=3",
    ]
    if target.get("port") is not None:
        command.extend(["-p", str(int(target["port"]))])
    command.append(_text(target.get("sshTarget"), "target.sshTarget"))
    return command


def _remote_project_staging(target: Mapping[str, Any], identity: Mapping[str, Any]) -> str:
    home = _text(target.get("home"), "target.home")
    project_relative = _relative(target.get("projectRoot"), "target.projectRoot")
    if project_relative == Path("."):
        raise ValueError("target.projectRoot must name a project below target.home")
    project = f"{home.rstrip('/')}/{project_relative.as_posix()}"
    incoming_name = f"{identity['version']}-{os.getpid()}"
    script = "\n".join(
        (
            "set -eu",
            f"home={shlex.quote(home)}",
            f"project={shlex.quote(project)}",
            'home=$(cd -- "$home" && pwd -P)',
            'project=$(cd -- "$project" && pwd -P)',
            'case "$project/" in "$home/"*) ;; *) exit 41 ;; esac',
            'gitroot=$(git -C "$project" rev-parse --show-toplevel)',
            'gitroot=$(cd -- "$gitroot" && pwd -P)',
            '[ "$gitroot" = "$project" ]',
            'tmp="$project/.tmp"',
            '[ ! -L "$tmp" ]',
            'mkdir -p -- "$tmp"',
            'tmp=$(cd -- "$tmp" && pwd -P)',
            'case "$tmp/" in "$project/"*) ;; *) exit 42 ;; esac',
            'git -C "$project" check-ignore --quiet -- .tmp/',
            'incoming="$tmp/lhc-rollout/incoming/' + incoming_name + '"',
            'mkdir -p -- "$incoming"',
            'printf "%s\\n" "$incoming"',
        )
    )
    completed = _run([*_ssh_base(target), f"sh -c {shlex.quote(script)}"])
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or f"{target.get('name')}: project-local remote staging failed"
        )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1 or "/.tmp/lhc-rollout/incoming/" not in lines[0]:
        raise RuntimeError(f"{target.get('name')}: invalid project-local staging path")
    return lines[0]


def _remote_call(
    mode: str,
    target: Mapping[str, Any],
    bundle: Path,
    install: Mapping[str, Any],
    expected_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = _read_json(bundle / "identity.json")
    remote = _remote_project_staging(target, identity)
    python = _text(target.get("python", "python3"), "target.python")
    cleanup = f"import pathlib,shutil;p=pathlib.Path({remote!r});shutil.rmtree(p) if p.is_dir() else None"
    try:
        with tempfile.TemporaryDirectory(
            prefix="lhc-rollout-remote-", dir=bundle.parent
        ) as temporary:
            root = Path(temporary)
            archive_path = root / "bundle.tar.gz"
            request_path = root / "request.json"
            _pack_bundle(bundle, archive_path)
            request = {"target": target, "install": install}
            if expected_plan is not None:
                request["expectedPlanDigest"] = _plan_digest(expected_plan)
            request_path.write_text(
                json.dumps(request, default=str) + "\n",
                encoding="utf-8",
            )
            scp = ["scp", "-q"]
            if target.get("port") is not None:
                scp.extend(["-P", str(int(target["port"]))])
            destination = f"{_text(target.get('sshTarget'), 'target.sshTarget')}:{remote}/"
            scp.extend([str(Path(__file__).resolve()), str(archive_path), str(request_path), destination])
            uploaded = _run(scp)
            if uploaded.returncode != 0:
                raise RuntimeError(uploaded.stderr.strip() or f"{target.get('name')}: upload failed")
        command = (
            f"{shlex.quote(python)} {shlex.quote(remote + '/lhc_rollout.py')} remote-{mode} "
            f"--bundle {shlex.quote(remote + '/bundle.tar.gz')} --request {shlex.quote(remote + '/request.json')}"
        )
        completed = _run([*_ssh_base(target), command])
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"{target.get('name')}: remote {mode} failed")
        reports = [line[len(REPORT_PREFIX):] for line in completed.stdout.splitlines() if line.startswith(REPORT_PREFIX)]
        if len(reports) != 1:
            raise RuntimeError(f"{target.get('name')}: expected one framed report")
        value = json.loads(reports[0])
        if not isinstance(value, dict):
            raise RuntimeError(f"{target.get('name')}: invalid remote report")
        return value
    finally:
        _run([*_ssh_base(target), f"{shlex.quote(python)} -c {shlex.quote(cleanup)}"])


def _targets(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    targets = manifest.get("targets")
    if manifest.get("schemaVersion") != 1 or not isinstance(targets, list) or not targets:
        raise ValueError("manifest requires schemaVersion 1 and a non-empty targets array")
    result = []
    names = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise ValueError(f"targets[{index}] must be an object")
        name = _text(target.get("name"), f"targets[{index}].name")
        if name in names:
            raise ValueError(f"duplicate target name: {name}")
        names.add(name)
        transport = target.get("transport", "local")
        if transport not in {"local", "ssh"}:
            raise ValueError(f"targets[{index}].transport must be local or ssh")
        project_root = _relative(
            target.get("projectRoot"), f"targets[{index}].projectRoot"
        )
        if project_root == Path("."):
            raise ValueError(f"targets[{index}].projectRoot must name a project")
        result.append(target)
    return result


def _preview_with_bundle(manifest: Mapping[str, Any], bundle: Path) -> dict[str, Any]:
    install = _install(manifest)
    identity = _read_json(bundle / "identity.json")
    plans = []
    for target in _targets(manifest):
        if target.get("transport", "local") == "ssh":
            plans.append(_remote_call("preview", target, bundle, install))
        else:
            plans.append(preview_target(target, bundle, install))
    return {
        "status": "preview",
        **identity,
        "confirmation": _confirmation(identity, plans),
        "targets": plans,
    }


def _public_preview(preview: Mapping[str, Any]) -> dict[str, Any]:
    hidden = {"age", "block", "mode", "outside", "source"}

    def clean(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: clean(item) for key, item in value.items() if key not in hidden}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(preview)


def preview_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest = _read_json(Path(manifest_path))
    with tempfile.TemporaryDirectory(
        prefix="lhc-rollout-bundle-", dir=_project_tmp(_source_repo(manifest))
    ) as temporary:
        bundle = Path(temporary) / "bundle"
        build_bundle(manifest, bundle)
        return _public_preview(_preview_with_bundle(manifest, bundle))


def _copy_payload(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _verify_router(path: Path, install: Mapping[str, Any], expected_outside: str | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    _, block, _ = _marker_parts(text, install["markerBegin"], install["markerEnd"])
    if expected_outside is not None and _outside_digest(text, install["markerBegin"], install["markerEnd"]) != expected_outside:
        raise RuntimeError(f"text outside managed marker changed: {path}")
    references = re.findall(r"`([^`]*common/agents/[^`]+\.md)`", block)
    resolved = []
    for value in references:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = path.parent / candidate
        if not candidate.is_file():
            raise RuntimeError(f"router reference is missing: {candidate}")
        resolved.append(str(candidate))
    if not resolved:
        raise RuntimeError(f"router has no resolvable role references: {path}")
    return {"path": str(path), "roleReferences": len(set(resolved))}


def _receipt_plan(
    home: Path,
    store: Path,
    identity: Mapping[str, Any],
    install: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    try:
        rollback_root, rollback_status = _select_rollback_root(
            store, install, str(identity["version"])
        )
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    if rollback_status != "complete":
        raise RuntimeError(
            f"rollback receipt is missing: {rollback_root / 'rollout.json'}"
        )
    receipt_path = rollback_root / "rollout.json"
    receipt = _read_json(receipt_path)
    if receipt.get("status") != "complete":
        raise RuntimeError(f"rollback receipt is not complete: {receipt_path}")
    observed_identity = receipt.get("identity")
    if not isinstance(observed_identity, Mapping) or any(
        observed_identity.get(key) != identity.get(key)
        for key in ("commit", "version", "digest", "files")
    ):
        raise RuntimeError(f"rollback receipt identity mismatch: {receipt_path}")
    plan = receipt.get("plan")
    if not isinstance(plan, dict) or plan.get("home") != str(home):
        raise RuntimeError(f"rollback receipt plan mismatch: {receipt_path}")
    return rollback_root, plan


def _verify_rollback_artifacts(home: Path, rollback_root: Path, plan: Mapping[str, Any]) -> None:
    for item in [*plan.get("projects", []), *plan.get("copies", [])]:
        if item.get("action") == "replace" and not Path(str(item.get("previous"))).exists():
            raise RuntimeError(f"rollback copy is missing: {item.get('previous')}")
    routers = list(plan.get("routers", []))
    for project in plan.get("projects", []):
        routers.extend(project.get("routers", []))
    for item in routers:
        if item.get("action") != "replace" or item.get("outside") is None:
            continue
        backup = rollback_root / "routers" / Path(str(item["path"])).relative_to(home)
        if not backup.is_file():
            raise RuntimeError(f"router rollback copy is missing: {backup}")


def verify_target(
    target: Mapping[str, Any],
    bundle: Path,
    install: Mapping[str, Any],
    plan: Mapping[str, Any] | None = None,
    require_rollback: bool = True,
) -> dict[str, Any]:
    identity = _read_json(bundle / "identity.json")
    home = _target_home(target)
    store = _inside(home, str(install["store"]), "install.store")
    current = store / "current"
    expected_link = f"versions/{identity['version']}"
    if not current.is_symlink() or os.readlink(current) != expected_link:
        raise RuntimeError(f"current link is invalid: {current}")
    digest, files = tree_digest(store / expected_link)
    if (digest, files) != (identity["digest"], identity["files"]):
        raise RuntimeError(f"global LHC identity mismatch: {home}")
    rollback_root: Path | None = None
    if require_rollback:
        rollback_root, receipt_plan = _receipt_plan(home, store, identity, install)
        if plan is not None and _plan_digest(plan) != _plan_digest(receipt_plan):
            raise RuntimeError("rollback receipt does not match the applied plan")
        plan = receipt_plan
    outside = {}
    if plan is not None:
        for router in plan.get("routers", []):
            outside[router["path"]] = router.get("outside")
        for project in plan.get("projects", []):
            for router in project.get("routers", []):
                outside[router["path"]] = router.get("outside")
    routers = []
    for raw in target.get("routers", []):
        path = _inside(home, raw.get("path"), "target.router.path")
        routers.append(_verify_router(path, install, outside.get(str(path))))
    projects = []
    for raw in target.get("projects", []):
        root = _inside(home, raw.get("path"), "target.project.path")
        project_routers = [
            _verify_router(_inside(root, item.get("path"), "target.project.router.path"), install, outside.get(str(_inside(root, item.get("path"), "target.project.router.path"))))
            for item in raw.get("routers", [])
        ]
        entry = {"routers": project_routers}
        if install["projectRuntime"] is not None:
            runtime = _inside(root, str(install["projectRuntime"]), "install.projectRuntime")
            observed, count = tree_digest(runtime)
            if (observed, count) != (identity["digest"], identity["files"]):
                raise RuntimeError(f"project LHC identity mismatch: {runtime}")
            entry["runtime"] = str(runtime)
        projects.append(entry)
    copies = []
    copy_sources = manifest_copy_sources(bundle)
    for raw in target.get("copies", []):
        destination = _inside(home, raw.get("path"), "target.copy.path")
        source = copy_sources[_text(raw.get("source"), "target.copy.source")]
        expected = tree_digest(source)[0] if source.is_dir() else hashlib.sha256(source.read_bytes()).hexdigest()
        observed = tree_digest(destination)[0] if destination.is_dir() else None
        if observed != expected:
            raise RuntimeError(f"copy identity mismatch: {destination}")
        copies.append(str(destination))
    if rollback_root is not None and plan is not None:
        _verify_rollback_artifacts(home, rollback_root, plan)
    return {
        "name": _text(target.get("name"), "target.name"),
        "version": identity["version"],
        "digest": digest,
        "files": files,
        "routers": routers,
        "projects": projects,
        "copies": copies,
        "rollbackRoot": str(rollback_root) if rollback_root is not None else None,
    }


def manifest_copy_sources(bundle: Path) -> dict[str, Path]:
    identity = _read_json(bundle / "identity.json")
    return {name: _inside(bundle / "copies", name, f"copies.{name}") for name in identity.get("copies", [])}


def apply_target(target: Mapping[str, Any], bundle: Path, install: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    identity = _read_json(bundle / "identity.json")
    home = _target_home(target)
    store = _inside(home, str(install["store"]), "install.store")
    versions = store / "versions"
    current = store / "current"
    version_target = versions / identity["version"]
    rollback_root = Path(str(plan["rollbackRoot"]))
    has_changes = (
        plan.get("currentBefore") != f"versions/{identity['version']}"
        or any(item.get("action") != "noop" for item in plan.get("routers", []))
        or any(item.get("action") != "noop" for item in plan.get("projects", []))
        or any(
            router.get("action") != "noop"
            for project in plan.get("projects", [])
            for router in project.get("routers", [])
        )
        or any(item.get("action") != "noop" for item in plan.get("copies", []))
    )
    if rollback_root.exists():
        if not has_changes:
            return verify_target(target, bundle, install)
        raise RuntimeError(f"rollback receipt target exists: {rollback_root}")
    rollback_root.mkdir(parents=True, exist_ok=False)
    router_backups: list[tuple[Path, Path | None, int]] = []
    directory_swaps: list[tuple[Path, Path | None]] = []
    previous_current = plan.get("currentBefore")
    try:
        if not has_changes:
            verification = verify_target(
                target, bundle, install, plan, require_rollback=False
            )
            receipt = {
                "status": "complete",
                "identity": identity,
                "plan": plan,
                "verification": verification,
            }
            (rollback_root / "rollout.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            return verify_target(target, bundle, install)
        versions.mkdir(parents=True, exist_ok=True)
        if not version_target.exists():
            incoming = Path(tempfile.mkdtemp(prefix=f".{identity['version']}.incoming-", dir=versions))
            shutil.rmtree(incoming)
            shutil.copytree(bundle / "version", incoming)
            if tree_digest(incoming) != (identity["digest"], identity["files"]):
                raise RuntimeError("incoming LHC identity mismatch")
            os.replace(incoming, version_target)

        for item in [*plan.get("projects", []), *plan.get("copies", [])]:
            if item["action"] == "noop":
                continue
            destination = Path(item.get("runtime") or item.get("path"))
            source = bundle / "version" if "runtime" in item else Path(item["source"])
            previous = Path(item["previous"])
            incoming = destination.with_name(f".{destination.name}.incoming-{identity['version']}-{os.getpid()}")
            _copy_payload(source, incoming)
            backup: Path | None = None
            if destination.exists() or destination.is_symlink():
                os.replace(destination, previous)
                backup = previous
            directory_swaps.append((destination, backup))
            os.replace(incoming, destination)

        temporary_link = store / f".current-{identity['version']}-{os.getpid()}"
        temporary_link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(f"versions/{identity['version']}", temporary_link)
        os.replace(temporary_link, current)

        router_plans = list(plan.get("routers", []))
        for project in plan.get("projects", []):
            router_plans.extend(project.get("routers", []))
        for item in router_plans:
            if item["action"] == "noop":
                continue
            path = Path(item["path"])
            backup: Path | None = None
            mode = int(item["mode"])
            if path.exists():
                backup = rollback_root / "routers" / path.relative_to(home)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
                before, _, after = _marker_parts(path.read_text(encoding="utf-8"), install["markerBegin"], install["markerEnd"])
            else:
                before = after = ""
            router_backups.append((path, backup, mode))
            _atomic_write(path, before + item["block"] + after, mode)

        verification = verify_target(
            target, bundle, install, plan, require_rollback=False
        )
        receipt = {"status": "complete", "identity": identity, "plan": plan, "verification": verification}
        (rollback_root / "rollout.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return verify_target(target, bundle, install)
    except Exception:
        for path, backup, mode in reversed(router_backups):
            if backup is None:
                path.unlink(missing_ok=True)
            elif backup.exists():
                shutil.copy2(backup, path)
                path.chmod(mode)
        if current.exists() or current.is_symlink():
            current.unlink()
        if previous_current is not None:
            os.symlink(str(previous_current), current)
        for destination, backup in reversed(directory_swaps):
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists() or destination.is_symlink():
                destination.unlink()
            if backup is not None and backup.exists():
                os.replace(backup, destination)
        (rollback_root / "rollout.json").write_text(json.dumps({"status": "rolled_back", "identity": identity}, indent=2) + "\n", encoding="utf-8")
        raise


def apply_manifest(manifest_path: str | Path, confirmation: str) -> dict[str, Any]:
    manifest = _read_json(Path(manifest_path))
    with tempfile.TemporaryDirectory(
        prefix="lhc-rollout-bundle-", dir=_project_tmp(_source_repo(manifest))
    ) as temporary:
        bundle = Path(temporary) / "bundle"
        build_bundle(manifest, bundle)
        preview = _preview_with_bundle(manifest, bundle)
        if confirmation != preview["confirmation"]:
            raise ValueError("confirmation does not match the current preview")
        install = _install(manifest)
        results = []
        plans = {item["name"]: item for item in preview["targets"]}
        for target in _targets(manifest):
            name = _text(target.get("name"), "target.name")
            if target.get("transport", "local") == "ssh":
                results.append(
                    _remote_call(
                        "apply", target, bundle, install, expected_plan=plans[name]
                    )
                )
            else:
                results.append(apply_target(target, bundle, install, plans[name]))
        return {"status": "complete", "confirmation": confirmation, "version": preview["version"], "digest": preview["digest"], "targets": results}


def verify_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest = _read_json(Path(manifest_path))
    with tempfile.TemporaryDirectory(
        prefix="lhc-rollout-bundle-", dir=_project_tmp(_source_repo(manifest))
    ) as temporary:
        bundle = Path(temporary) / "bundle"
        identity = build_bundle(manifest, bundle)
        install = _install(manifest)
        results = []
        for target in _targets(manifest):
            if target.get("transport", "local") == "ssh":
                results.append(_remote_call("verify", target, bundle, install))
            else:
                results.append(verify_target(target, bundle, install))
        return {"status": "verified", **identity, "targets": results}


def _remote(mode: str, archive_path: Path, request_path: Path) -> dict[str, Any]:
    request = _read_json(request_path)
    target = request.get("target")
    install = request.get("install")
    if not isinstance(target, Mapping) or not isinstance(install, Mapping):
        raise ValueError("remote request is invalid")
    local_target = dict(target)
    local_target["transport"] = "local"
    staging = archive_path.parent / ".tmp"
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="lhc-rollout-remote-", dir=staging
    ) as temporary:
        bundle = Path(temporary) / "bundle"
        bundle.mkdir()
        _extract_bundle(archive_path, bundle)
        plan = preview_target(local_target, bundle, install)
        if mode == "preview":
            return plan
        if mode == "apply":
            expected = request.get("expectedPlanDigest")
            if not isinstance(expected, str) or expected != _plan_digest(plan):
                raise ValueError("remote plan changed after confirmation")
            return apply_target(local_target, bundle, install, plan)
        return verify_target(local_target, bundle, install)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "verify"):
        child = subparsers.add_parser(name)
        child.add_argument("--manifest", type=Path, required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--manifest", type=Path, required=True)
    apply_parser.add_argument("--confirm", required=True)
    for name in ("remote-preview", "remote-apply", "remote-verify"):
        child = subparsers.add_parser(name, help=argparse.SUPPRESS)
        child.add_argument("--bundle", type=Path, required=True)
        child.add_argument("--request", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "preview":
        result = preview_manifest(arguments.manifest)
    elif arguments.command == "apply":
        result = apply_manifest(arguments.manifest, arguments.confirm)
    elif arguments.command == "verify":
        result = verify_manifest(arguments.manifest)
    else:
        result = _remote(arguments.command.removeprefix("remote-"), arguments.bundle, arguments.request)
        print(REPORT_PREFIX + json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
