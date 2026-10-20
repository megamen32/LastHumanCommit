#!/usr/bin/env python3
"""Read-only native identity and future child-dispatch provenance helpers.

The logical LHC state key stays separate from Codex's native session id.  This
module reads bounded JSONL metadata and never writes LHC state or interprets a
relay as human authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable


IDENTITY_SCHEMA = "lhc.native-identity.v1"
INTENT_SCHEMA = "lhc.native-spawn-intent.v1"
ASSIGNMENT_SCHEMA = "lhc.native-child-assignment.v1"
MAX_JOURNAL_BYTES = 96 * 1024 * 1024
MAX_RECORD_BYTES = 2 * 1024 * 1024
MAX_PROMPT_BYTES = 64 * 1024
MAX_DISPATCH_RECORDS = 64
_CIPHERTEXT = re.compile(r"^gAAAA[A-Za-z0-9_-]{8,}={0,2}$")
_NATIVE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


def composite_session_id(parent_logical_id: str, child_native_id: str) -> str:
    """Return the stable logical LHC key used for a spawned child."""
    parent = _native_id(parent_logical_id, "parent logical session id")
    child = _native_id(child_native_id, "child native session id")
    if ":subagent:" in parent:
        raise ValueError("nested composite parent identity needs its own verified native mapping")
    return f"{parent}:subagent:{child}"


def _identity_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{label} is missing or invalid")
    return value.strip()


def _native_id(value: Any, label: str) -> str:
    result = _identity_text(value, label)
    if not _NATIVE_ID.fullmatch(result):
        raise ValueError(f"{label} is not a supported native identifier")
    return result


def _sessions_root() -> Path:
    return (Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions").resolve()


def _session_file(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink():
        raise ValueError("native journal must be an absolute regular session file")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(_sessions_root())
    except ValueError as exc:
        raise ValueError("native journal must be inside CODEX_HOME/sessions") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_JOURNAL_BYTES:
        raise ValueError("native journal is missing or exceeds the bounded reader limit")
    return resolved


def read_native_header(journal_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and validate only the first native session_meta record."""
    path = _session_file(journal_path)
    with path.open("rb") as stream:
        line = stream.readline(MAX_RECORD_BYTES + 1)
    if not line.endswith(b"\n") or len(line) > MAX_RECORD_BYTES:
        raise ValueError("native session header is oversized or incomplete")
    try:
        row = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("native session header is invalid JSON") from exc
    payload = row.get("payload") if isinstance(row, dict) else None
    if row.get("type") != "session_meta" or not isinstance(payload, dict):
        raise ValueError("native journal does not begin with session_meta")
    native_id = _native_id(payload.get("id"), "native session id")
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise ValueError("native session cwd is missing or not absolute")
    result = {
        "schema": IDENTITY_SCHEMA,
        "native_id": native_id,
        "session_id": payload.get("session_id"),
        "parent_thread_id": payload.get("parent_thread_id"),
        "agent_path": payload.get("agent_path") or _nested_agent_path(payload),
        "native_cwd": str(Path(cwd).resolve()),
        "journal_path": str(path),
        "originator": payload.get("originator"),
    }
    return result


def find_native_journal(native_session_id: str) -> Path:
    """Resolve one filename candidate by exact header id; ambiguity fails closed."""
    session_id = _native_id(native_session_id, "native session id")
    root = _sessions_root()
    candidates = sorted(root.rglob(f"*{session_id}.jsonl"))
    if len(candidates) > 2:
        raise ValueError("native session journal is missing or ambiguous")
    matches = []
    for candidate in candidates:
        try:
            header = read_native_header(candidate)
        except (OSError, ValueError):
            continue
        if header["native_id"] == session_id:
            matches.append(Path(header["journal_path"]))
    if len(matches) != 1:
        raise ValueError("native session journal is missing or ambiguous")
    return matches[0]


def _nested_agent_path(payload: dict[str, Any]) -> str | None:
    source = payload.get("source") or {}
    if not isinstance(source, dict):
        return None
    subagent = source.get("subagent") or {}
    if not isinstance(subagent, dict):
        return None
    return subagent.get("agent_path")


def resolve_standalone_identity(logical_session_id: str,
                                journal_path: str | os.PathLike[str], *,
                                observed_native_cwd: str) -> dict[str, Any]:
    """Resolve an ordinary native session without inventing a parent relation."""
    header = read_native_header(journal_path)
    if find_native_journal(header["native_id"]) != Path(header["journal_path"]):
        raise ValueError("standalone native journal path is ambiguous")
    if logical_session_id != header["native_id"]:
        raise ValueError("standalone LHC id must equal its native session id")
    if str(Path(observed_native_cwd).resolve()) != header["native_cwd"]:
        raise ValueError("standalone native cwd differs from the owning session cwd")
    if header.get("parent_thread_id") or header.get("agent_path"):
        raise ValueError("subagent native session needs its verified parent dispatch")
    return {
        **header,
        "logical_session_id": logical_session_id,
        "parent_logical_id": None,
        "parent_native_id": None,
        "dispatch_call_id": None,
        "verified": True,
    }


def _parent_dispatch(parent_journal: Path, parent_id: str, child_id: str,
                     child_path: str) -> tuple[str, str]:
    """Find one real spawn call and its successful SubAgentActivity receipt."""
    header = read_native_header(parent_journal)
    if header["native_id"] != parent_id:
        raise ValueError("parent native id does not match the parent journal")
    call_ids: list[str] = []
    receipts: list[tuple[str, str]] = []
    output_ids: set[str] = set()
    with parent_journal.open("rb") as stream:
        while True:
            line = stream.readline(MAX_RECORD_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_RECORD_BYTES or not line.endswith(b"\n"):
                raise ValueError("parent native record is oversized or incomplete")
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("parent native journal contains invalid JSON") from exc
            payload = row.get("payload") or {}
            if row.get("type") == "response_item" and payload.get("type") in {"function_call", "custom_tool_call"}:
                if payload.get("name") == "spawn_agent":
                    call_id = payload.get("call_id")
                    if isinstance(call_id, str) and call_id:
                        call_ids.append(call_id)
            elif row.get("type") == "response_item" and payload.get("type") == "function_call_output":
                call_id = payload.get("call_id")
                output = payload.get("output")
                if isinstance(call_id, str) and call_id and _successful_output(output):
                    output_ids.add(call_id)
            elif row.get("type") == "event_msg" and payload.get("type") == "item_completed":
                item = payload.get("item") or {}
                if (item.get("type") == "SubAgentActivity" and item.get("kind") == "started"
                        and item.get("agent_thread_id") == child_id
                        and item.get("agent_path") == child_path
                        and payload.get("thread_id") == parent_id
                        and isinstance(item.get("id"), str)):
                    receipts.append((item["id"], item.get("agent_path")))
    if len(receipts) != 1:
        raise ValueError("child dispatch receipt is missing or ambiguous")
    call_id, receipt_path = receipts[0]
    if receipt_path != child_path or call_ids.count(call_id) != 1 or call_id not in output_ids:
        raise ValueError("child receipt does not match one successful spawn_agent call")
    return call_id, receipt_path


def _successful_output(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return not value.lstrip().casefold().startswith(("error:", "failed:", "rejected:"))
    return (isinstance(parsed, dict)
            and not any(key in parsed for key in ("error", "isError"))
            and parsed.get("status") not in {"error", "failed", "rejected"})


def _intent_for_call(captured_intents: Iterable[dict[str, Any]], call_id: str,
                     parent_logical_id: str, parent_native_id: str,
                     parent_native_cwd: str, parent_journal_path: str) -> dict[str, Any] | None:
    matches = [row for row in captured_intents if row.get("call_id") == call_id]
    if not matches:
        return None
    if len(matches) > 1:
        stable = {(row.get("parent_logical_id"), row.get("parent_native_id"),
                   row.get("parent_native_cwd"), row.get("parent_journal_path"),
                   row.get("prompt_sha256"), row.get("status")) for row in matches}
        if len(stable) != 1:
            raise ValueError("conflicting pre-call captures for the same dispatch")
    intent = matches[0]
    if (intent.get("schema") != INTENT_SCHEMA or intent.get("parent_logical_id") != parent_logical_id
            or intent.get("parent_native_id") != parent_native_id
            or intent.get("parent_native_cwd") != parent_native_cwd
            or intent.get("parent_journal_path") != parent_journal_path):
        raise ValueError("pre-call capture does not belong to the verified parent dispatch")
    return intent


def resolve_child_identity(logical_session_id: str,
                           parent_journal_path: str | os.PathLike[str] | None,
                           child_journal_path: str | os.PathLike[str], *,
                           observed_native_cwd: str,
                           captured_intents: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    """Bind one composite logical key to a verified native parent/child pair.

    Historical tool arguments are not used as assignment text. Only a matching
    plaintext pre-call capture may supply the future assignment after the real
    spawn call and child-start receipt have both been observed.
    """
    child_path = _session_file(child_journal_path)
    child = read_native_header(child_path)
    if find_native_journal(child["native_id"]) != child_path:
        raise ValueError("child native journal path is ambiguous")
    child_id = child["native_id"]
    if not isinstance(child.get("parent_thread_id"), str) or not child.get("parent_thread_id"):
        raise ValueError("child header has no native parent id")
    parent_path = (_session_file(parent_journal_path) if parent_journal_path is not None
                   else find_native_journal(child["parent_thread_id"]))
    parent = read_native_header(parent_path)
    if find_native_journal(parent["native_id"]) != parent_path:
        raise ValueError("parent native journal path is ambiguous")
    parent_id = parent["native_id"]
    if child_id == parent_id:
        raise ValueError("parent and child native session ids must differ")
    expected_logical = composite_session_id(parent_id, child_id)
    if logical_session_id not in {expected_logical, child_id}:
        raise ValueError("composite logical id does not match the verified parent and child")
    if (child.get("parent_thread_id") != parent_id or child.get("session_id") != parent_id
            or not child.get("agent_path") or child.get("originator") != "agent-herder"):
        raise ValueError("child header does not verify its parent and Agent Herder path")
    if str(Path(observed_native_cwd).resolve()) != child["native_cwd"]:
        raise ValueError("child native cwd differs from the owning LHC session cwd")
    raw_child = _raw_header(child_path)
    raw_source = raw_child.get("source") or {}
    if not isinstance(raw_source, dict):
        raw_source = {}
    raw_subagent = raw_source.get("subagent") or {}
    if not isinstance(raw_subagent, dict):
        raw_subagent = {}
    thread_spawn = raw_subagent.get("thread_spawn") or {}
    if not isinstance(thread_spawn, dict):
        thread_spawn = {}
    if thread_spawn.get("parent_thread_id") != parent_id:
        raise ValueError("child thread_spawn metadata does not match the parent journal")
    dispatch_call_id, receipt_path = _parent_dispatch(parent_path, parent_id, child_id, child["agent_path"])
    intent = _intent_for_call(captured_intents, dispatch_call_id, parent_id, parent_id,
                              parent["native_cwd"], str(parent_path))
    assignment: dict[str, Any]
    if intent is None:
        assignment = {"schema": ASSIGNMENT_SCHEMA, "status": "unavailable",
                      "reason": "no plaintext pre-call capture for this dispatch"}
    elif intent.get("status") != "captured" or not isinstance(intent.get("prompt"), str):
        assignment = {"schema": ASSIGNMENT_SCHEMA, "status": "unavailable",
                      "reason": intent.get("reason") or "pre-call task text was unavailable"}
    else:
        assignment = {"schema": ASSIGNMENT_SCHEMA, "status": "bound",
                      "source_call_id": dispatch_call_id, "prompt": intent["prompt"],
                      "prompt_sha256": intent["prompt_sha256"], "origin": "agent-relay",
                      "observed_at": intent["observed_at"], "child_id": child_id,
                      "parent_native_cwd": parent["native_cwd"],
                      "parent_journal_path": str(parent_path),
                      "child_journal_path": str(child_path)}
    return {
        "schema": IDENTITY_SCHEMA,
        "verified": True,
        "logical_session_id": logical_session_id,
        "parent_logical_id": parent_id,
        "native_id": child_id,
        "parent_native_id": parent_id,
        "parent_native_cwd": parent["native_cwd"],
        "agent_path": child["agent_path"],
        "native_cwd": child["native_cwd"],
        "journal_path": str(child_path),
        "parent_journal_path": str(parent_path),
        "dispatch_call_id": dispatch_call_id,
        "dispatch_agent_path": receipt_path,
        "assignment": assignment,
    }


def _raw_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        row = json.loads(stream.readline(MAX_RECORD_BYTES + 1))
    return row["payload"]


def capture_spawn_intent(parent_logical_id: str, *, parent_journal_path: str | os.PathLike[str] | None,
                         tool_name: str, tool_call_id: str, tool_input: Any,
                         observed_at: str) -> dict[str, Any]:
    """Capture plaintext before spawn; the result alone conveys no authority."""
    parent_path = (_session_file(parent_journal_path) if parent_journal_path is not None
                   else find_native_journal(parent_logical_id))
    parent = read_native_header(parent_path)
    if find_native_journal(parent["native_id"]) != parent_path:
        raise ValueError("parent native journal path is ambiguous")
    if parent_logical_id != parent["native_id"]:
        raise ValueError("spawn capture needs the verified logical parent session")
    if (not isinstance(tool_name, str) or
            not (tool_name in {"spawn_agent", "collaborationspawn_agent"} or tool_name.endswith(".spawn_agent")
                 or tool_name.endswith("__spawn_agent"))):
        raise ValueError("only the native spawn_agent pre-call can be captured")
    call_id = _identity_text(tool_call_id, "native tool call id")
    record: dict[str, Any] = {
        "schema": INTENT_SCHEMA, "status": "unavailable", "reason": "spawn input did not contain readable task text",
        "call_id": call_id, "parent_logical_id": parent_logical_id,
        "parent_native_id": parent["native_id"], "parent_journal_path": str(parent_path),
        "parent_native_cwd": parent["native_cwd"],
        "origin": "agent-relay", "observed_at": _identity_text(observed_at, "capture timestamp"),
    }
    if isinstance(tool_input, str):
        if _CIPHERTEXT.fullmatch(tool_input.strip()):
            record["reason"] = "spawn task text is encrypted in the pre-call event"
            return record
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            return record
    if not isinstance(tool_input, dict):
        return record
    message = tool_input.get("message")
    if not isinstance(message, str) or not message.strip():
        return record
    message = message.strip()
    encoded = message.encode("utf-8")
    if len(encoded) > MAX_PROMPT_BYTES:
        record["reason"] = "spawn task text exceeds the bounded capture limit"
        return record
    if _CIPHERTEXT.fullmatch(message):
        record["reason"] = "spawn task text is encrypted in the pre-call event"
        return record
    record.update(status="captured", reason=None, prompt=message,
                  prompt_sha256=hashlib.sha256(encoded).hexdigest())
    return record


def merge_dispatch_records(existing: Iterable[dict[str, Any]], record: dict[str, Any], *,
                           limit: int = MAX_DISPATCH_RECORDS) -> list[dict[str, Any]]:
    """Idempotently retain captures; refuse conflicts or unsafe eviction."""
    if not isinstance(limit, int) or limit < 1 or limit > MAX_DISPATCH_RECORDS:
        raise ValueError("dispatch capture capacity is outside the supported bound")
    rows = [dict(row) for row in existing]
    call_id = _identity_text(record.get("call_id"), "dispatch call id")
    current = next((row for row in rows if row.get("call_id") == call_id), None)
    if current is not None:
        stable_keys = ("schema", "parent_logical_id", "parent_native_id", "parent_native_cwd",
                       "parent_journal_path", "status", "prompt_sha256", "prompt", "reason")
        if any(current.get(key) != record.get(key) for key in stable_keys):
            raise ValueError("conflicting capture for an existing native dispatch call")
        return rows
    if len(rows) >= limit:
        raise ValueError("dispatch capture capacity reached; pending/unknown records cannot be evicted")
    rows.append(dict(record))
    return rows


def _identity_tuple(identity: dict[str, Any]) -> tuple[Any, ...]:
    if identity.get("schema") != IDENTITY_SCHEMA or identity.get("verified") is not True:
        raise ValueError("session relation requires verified native identity records")
    return tuple(identity.get(key) for key in
                 ("native_id", "parent_native_id", "agent_path", "native_cwd", "journal_path",
                  "parent_journal_path"))


def classify_session_relation(owner_identity: dict[str, Any],
                              candidate_identity: dict[str, Any]) -> str:
    """Distinguish exact self from an independently sourced native session."""
    owner = _identity_tuple(owner_identity)
    candidate = _identity_tuple(candidate_identity)
    if owner == candidate:
        return "self"
    owner_id, owner_parent, owner_path, _, _, _ = owner
    candidate_id, candidate_parent, candidate_path, _, _, _ = candidate
    if owner_id == candidate_id or owner_id == candidate_parent or candidate_id == owner_parent:
        raise ValueError("native session ids overlap by parent/child relation but verified tuples differ")
    if owner_parent and owner_parent == candidate_parent and owner_path and candidate_path:
        raise ValueError("sibling subagent sessions are not an independent review identity")
    return "independent"
