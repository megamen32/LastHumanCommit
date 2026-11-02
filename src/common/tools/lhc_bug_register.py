#!/usr/bin/env python3
"""Durable per-plan bug register using the existing LHC file lock and atomic writer.

CRUD semantics: register, get/list, update, resolve (audited tombstone, never
delete), check. This remains a local-file CLI, called by the existing LhcPlan MCP.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid
from typing import Any

from lhc_plan_json import file_lock, _write_atomic

BUG_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
HEX_HASH = re.compile(r"[0-9a-f]{64}\Z")
ACTIVE = {"open", "blocked"}
RESOLVED = {"fixed", "duplicate", "false_positive"}
ALL_STATUSES = ACTIVE | RESOLVED
EDITABLE = {"title", "details", "source", "owner", "severity", "status", "blocker"}


class BugError(ValueError):
    pass


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BugError(f"{name} required")
    return value.strip()


def _dir(plan_dir: Path) -> Path:
    root = Path(plan_dir).expanduser()
    if not root.is_dir():
        raise BugError("existing plan_dir is required")
    folder = root / "bugs"
    if folder.is_symlink():
        raise BugError("symlink bug directory forbidden")
    if folder.exists() and not folder.is_dir():
        raise BugError("bug directory must be a directory")
    return folder


def _id(raw: str) -> str:
    if not isinstance(raw, str) or not BUG_ID.fullmatch(raw):
        raise BugError("invalid bug id")
    return raw


def _file(folder: Path, bug_id: str) -> Path:
    target = folder / (_id(bug_id) + ".json")
    if target.is_symlink():
        raise BugError("symlink bug record forbidden")
    return target


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(folder: Path, bug_id: str) -> tuple[dict[str, Any], str]:
    target = _file(folder, bug_id)
    if not target.is_file():
        raise BugError(f"missing registered bug: {bug_id}")
    raw = target.read_bytes()
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise BugError(f"corrupt bug record: {bug_id}") from exc
    if not isinstance(record, dict) or record.get("id") != bug_id or not isinstance(record.get("events"), list):
        raise BugError(f"corrupt bug record: {bug_id}")
    return record, _hash(raw)


def _write(folder: Path, record: dict[str, Any]) -> dict[str, Any]:
    target = _file(folder, record["id"])
    raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    _write_atomic(target, raw.decode("utf-8"))
    return {"bug": record, "sha256": _hash(raw)}


def _journal_file(plan_dir: Path) -> Path:
    target = Path(plan_dir) / ".lhc-bugs.jsonl"
    if target.is_symlink():
        raise BugError("symlink journal forbidden")
    if target.exists() and not target.is_file():
        raise BugError("journal must be a regular file")
    return target


def _journal(plan_dir: Path, result: dict[str, Any], action: str, actor: str) -> None:
    """Append one durable history receipt under the same plan lock as the record."""
    target = _journal_file(plan_dir)
    entry = {"id": result["bug"]["id"], "action": action, "actor": actor,
             "at": result["bug"]["updated_at"], "sha256": result["sha256"],
             "status": result["bug"]["status"]}
    # Existing LHC file_lock already serializes all writers for this plan.
    # A torn append is a hard check failure, never grounds for discarding history.
    with target.open("ab") as stream:
        stream.write((json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        stream.flush()
        import os
        os.fsync(stream.fileno())


def _journal_last(plan_dir: Path) -> dict[str, str]:
    path = _journal_file(plan_dir)
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_bytes().splitlines(), start=1):
        try:
            entry = json.loads(raw)
            bug_id = _id(entry["id"])
            sha = entry["sha256"]
            if not HEX_HASH.fullmatch(sha) or entry["action"] not in {"register", "update", "resolve"}:
                raise ValueError("bad journal record")
        except (ValueError, TypeError, KeyError) as exc:
            raise BugError(f"corrupt bug journal line {line_number}") from exc
        if bug_id not in result and entry["action"] != "register":
            raise BugError(f"corrupt bug journal origin for {bug_id}")
        result[bug_id] = sha
    return result


def _time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _lock(plan_dir: Path):
    return file_lock(Path(plan_dir) / ".lhc-bugs.lock")


def register(plan_dir: Path, *, title: str, details: str, reporter: str,
             source: str = "observed", bug_id: str | None = None) -> dict[str, Any]:
    folder = _dir(plan_dir)
    title, details, reporter = (_required(title, "title"),
                                _required(details, "details"), _required(reporter, "reporter"))
    source = _required(source, "source")
    bug_id = _id(bug_id or ("B" + uuid.uuid4().hex[:20]))
    with _lock(plan_dir):
        target = _file(folder, bug_id)
        if target.exists():
            raise BugError(f"bug {bug_id} already registered; update with expected sha256")
        folder.mkdir(exist_ok=True)
        at = _time()
        record = {"id": bug_id, "title": title, "details": details, "source": source,
                  "reporter": reporter, "owner": reporter, "status": "open",
                  "created_at": at, "updated_at": at,
                  "events": [{"at": at, "actor": reporter, "action": "register",
                              "changes": {"title": title, "details": details,
                                          "source": source, "status": "open"}}]}
        saved = _write(folder, record)
        _journal(plan_dir, saved, "register", reporter)
        return saved


def get(plan_dir: Path, bug_id: str) -> dict[str, Any]:
    folder = _dir(plan_dir)
    with _lock(plan_dir):
        record, sha = _read(folder, bug_id)
        return {"bug": record, "sha256": sha}


def list_bugs(plan_dir: Path, status: str | None = None) -> dict[str, Any]:
    folder = _dir(plan_dir)
    if status is not None and status not in ALL_STATUSES:
        raise BugError("invalid status filter")
    with _lock(plan_dir):
        result = []
        for f in sorted(folder.glob("*.json")) if folder.exists() else []:
            record, sha = _read(folder, f.stem)
            if status is None or record.get("status") == status:
                result.append({"bug": record, "sha256": sha})
    return {"bugs": result, "total": len(result)}


def _expected(value: str, actual: str) -> None:
    if not isinstance(value, str) or not HEX_HASH.fullmatch(value):
        raise BugError("expected_sha256 required (64 hex characters)")
    if value != actual:
        raise BugError("conflict: bug record changed; reread before update")


def update(plan_dir: Path, bug_id: str, actor: str, expected_sha256: str,
           fields: dict[str, Any], reason: str = "") -> dict[str, Any]:
    folder = _dir(plan_dir)
    actor = _required(actor, "actor")
    if not isinstance(fields, dict) or not fields:
        raise BugError("fields must be a non-empty object")
    unknown = set(fields) - EDITABLE
    if unknown:
        raise BugError("immutable or unknown bug fields: " + ", ".join(sorted(unknown)))
    if "status" in fields and fields["status"] not in ACTIVE:
        raise BugError("invalid update status: fixed/duplicate/false_positive require resolve with evidence/reason")
    if fields.get("status") == "blocked" and not _required(fields.get("blocker"), "blocker"):
        raise BugError("blocked status requires blocker")
    with _lock(plan_dir):
        record, sha = _read(folder, bug_id)
        _expected(expected_sha256, sha)
        changes = {k: v for k, v in fields.items() if record.get(k) != v}
        if not changes:
            return {"bug": record, "sha256": sha}
        if record["status"] in RESOLVED and "status" not in fields:
            raise BugError("resolved bug is immutable until explicitly reopened")
        if record["status"] in RESOLVED and fields.get("status") in ACTIVE:
            _required(reason, "reopen reason")
            record.pop("resolution", None)
        for key, value in changes.items():
            if key != "status" and (not isinstance(value, str) or not value.strip()):
                raise BugError(f"invalid field {key}")
            record[key] = value
        at = _time()
        record["updated_at"] = at
        record["events"].append({"at": at, "actor": actor, "action": "update",
                                 "reason": reason, "changes": changes})
        saved = _write(folder, record)
        _journal(plan_dir, saved, "update", actor)
        return saved


def _evidence(plan_dir: Path, evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise BugError("fixed requires evidence object with real proof file")
    ref = _required(evidence.get("proof_path"), "evidence.proof_path")
    command = _required(evidence.get("test_command"), "evidence.test_command")
    result = _required(evidence.get("result"), "evidence.result")
    if not re.search(r"\b(passed|pass|success|green|успешн)\b", result, re.I):
        raise BugError("evidence.result must document a passing check")
    root = Path(plan_dir).resolve()
    rel = Path(ref)
    if rel.is_absolute() or ".." in rel.parts:
        raise BugError("evidence.proof_path must be within plan_dir")
    target = root / rel
    if any(path.is_symlink() for path in [target, *target.parents] if path != root and root in path.parents):
        raise BugError("evidence symlink forbidden")
    if not target.is_file():
        raise BugError("evidence.proof_path must exist")
    if target.stat().st_size > 4 * 1024 * 1024:
        raise BugError("evidence.proof_path too large")
    proof = target.read_bytes()
    if result.casefold() not in proof.decode("utf-8", errors="replace").casefold():
        raise BugError("evidence.result is not supported by the actual proof file")
    return {"proof_path": ref, "sha256": _hash(proof),
            "test_command": command, "result": result}


def resolve(plan_dir: Path, bug_id: str, actor: str, expected_sha256: str,
            status: str, *, reason: str = "", duplicate_of: str = "",
            evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    folder = _dir(plan_dir)
    actor = _required(actor, "actor")
    if status not in RESOLVED:
        raise BugError("invalid resolution status")
    if status in {"duplicate", "false_positive"}:
        _required(reason, "resolution reason")
    with _lock(plan_dir):
        record, sha = _read(folder, bug_id)
        _expected(expected_sha256, sha)
        if record["status"] in RESOLVED:
            raise BugError("bug already resolved; reopen explicitly before resolving again")
        resolution: dict[str, Any] = {"kind": status, "reason": reason}
        if status == "fixed":
            resolution["evidence"] = _evidence(plan_dir, evidence)
        if status == "duplicate":
            if not duplicate_of or duplicate_of == bug_id:
                raise BugError("duplicate resolution requires another registered bug")
            try:
                other, _ = _read(folder, duplicate_of)
            except BugError as exc:
                raise BugError("duplicate resolution target is not a registered bug") from exc
            resolution["duplicate_of"] = other["id"]
        at = _time()
        record["status"] = status
        record["resolution"] = resolution
        record["updated_at"] = at
        record["events"].append({"at": at, "actor": actor, "action": "resolve",
                                 "changes": {"status": status, "resolution": resolution}})
        saved = _write(folder, record)
        _journal(plan_dir, saved, "resolve", actor)
        return saved


def check(plan_dir: Path) -> dict[str, Any]:
    # Verify both sources; deleting a record does not make an issue vanish,
    # and changing an old fixed record without a CAS event is never accepted.
    entries = list_bugs(plan_dir)["bugs"]
    with _lock(plan_dir):
        latest = _journal_last(plan_dir)
    by_id = {r["bug"]["id"]: r for r in entries}
    if set(latest) != set(by_id):
        raise BugError("registered bug missing or unjournaled file: " +
                       ", ".join(sorted(set(latest) ^ set(by_id))))
    for bug_id, item in by_id.items():
        if item["sha256"] != latest[bug_id]:
            raise BugError("bug journal SHA mismatch: " + bug_id)
        record = item["bug"]
        status = record.get("status")
        resolution = record.get("resolution", {})
        if status == "fixed":
            if not isinstance(resolution, dict) or resolution.get("kind") != "fixed":
                raise BugError("fixed bug missing resolution evidence: " + bug_id)
            recorded = resolution.get("evidence")
            fresh = _evidence(plan_dir, recorded)
            if fresh != recorded:
                raise BugError("fixed bug evidence changed: " + bug_id)
        elif status == "duplicate":
            if not isinstance(resolution, dict) or not resolution.get("reason") or resolution.get("duplicate_of") not in by_id:
                raise BugError("duplicate bug missing reason/original: " + bug_id)
        elif status == "false_positive":
            if not isinstance(resolution, dict) or not resolution.get("reason"):
                raise BugError("false-positive bug missing explicit reason: " + bug_id)
    for bug_id, item in by_id.items():
        if item["bug"].get("status") != "duplicate":
            continue
        seen = set()
        cursor = bug_id
        while by_id[cursor]["bug"].get("status") == "duplicate":
            if cursor in seen:
                raise BugError("duplicate cycle cannot resolve a defect: " + bug_id)
            seen.add(cursor)
            cursor = by_id[cursor]["bug"]["resolution"]["duplicate_of"]
    active = [bug_id for bug_id, item in by_id.items()
              if item["bug"].get("status") not in RESOLVED]
    if active:
        raise BugError("unresolved bugs (must fix or explicitly resolve): " + ", ".join(active))
    return {"total": len(entries), "unresolved": 0, "all_registered_bugs_resolved": True,
            "tests_green_required_separately": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action")
    parser.add_argument("plan_dir", type=Path)
    parser.add_argument("--bug-id", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--details", default="")
    parser.add_argument("--source", default="observed")
    parser.add_argument("--reporter", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--expected-sha256", default="")
    parser.add_argument("--fields", default="{}")
    parser.add_argument("--status", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--duplicate-of", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    try:
        p, n = args.plan_dir, args.bug_id
        if args.action == "register":
            value = register(p, title=args.title, details=args.details, reporter=args.reporter,
                             source=args.source, bug_id=n or None)
        elif args.action == "get":
            value = get(p, n)
        elif args.action == "list":
            value = list_bugs(p, args.status or None)
        elif args.action == "update":
            value = update(p, n, args.actor, args.expected_sha256,
                           json.loads(args.fields), reason=args.reason)
        elif args.action == "resolve":
            value = resolve(p, n, args.actor, args.expected_sha256, args.status,
                            reason=args.reason, duplicate_of=args.duplicate_of,
                            evidence=json.loads(args.evidence) if args.evidence else None)
        elif args.action == "check":
            value = check(p)
        else:
            raise BugError("unknown bug action")
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0
    except (BugError, OSError, ValueError, TypeError) as exc:
        print(f"bug registry: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
