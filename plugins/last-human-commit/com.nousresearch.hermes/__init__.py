"""External Hermes adapter for Last Human Commit child-task instructions."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BEGIN = "<!-- last-human-commit:begin -->"
END = "<!-- last-human-commit:end -->"
ROLE_TAG = re.compile(r"\[LHC_ROLE=(?P<role>[A-Za-z]+)\]")
ROLES = {
    "lead": "Lead", "overseer": "Overseer", "adviser": "Adviser",
    "critic": "Critic", "worker": "Worker",
    "reviewer": "Reviewer", "tester": "Tester",
}
_MAX_CHARS = 64_000
_SUMMARY_PREFIX = "[CONTEXT COMPACTION — REFERENCE ONLY]"
_LEGACY_SUMMARY_PREFIX = "[CONTEXT COMPACTION]"
_SESSION_MAP = "hermes-session-map.json"
_MAX_SESSION_ALIASES = 256


def _root() -> Path:
    configured = os.environ.get("LAST_HUMAN_COMMIT_ROOT", "").strip()
    return Path(configured).expanduser() if configured else (
        Path.home() / ".local/share/last-human-commit/current"
    )


def _read(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""
    return text if len(text) <= _MAX_CHARS else ""


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace one small plugin-owned state file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _safe_session_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return safe[:120] or "unknown-session"


def _agents_root(cwd: Path) -> Path | None:
    for root in (cwd, *cwd.parents):
        candidate = root / ".agents"
        if candidate.is_dir():
            return candidate
    return None


def _logical_session_id(
    agents_root: Path, session_id: str, parent_session_id: str
) -> str:
    """Keep one durable lineage when Hermes rotates its physical session id."""

    state_root = agents_root / "shared-session" / "compaction"
    map_path = state_root / _SESSION_MAP
    lock_path = state_root / f"{_SESSION_MAP}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    current = _safe_session_id(session_id)
    parent = _safe_session_id(parent_session_id) if parent_session_id else ""
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = _read_json(map_path)
        aliases = state.get("aliases")
        if not isinstance(aliases, dict):
            aliases = {}
        recent = state.get("recent")
        if not isinstance(recent, list):
            recent = []
        logical = str(aliases.get(current) or "")
        if not logical and parent:
            logical = str(aliases.get(parent) or parent)
        logical = _safe_session_id(logical or current)
        aliases[current] = logical
        recent = [item for item in recent if item != current]
        recent.append(current)
        recent = recent[-_MAX_SESSION_ALIASES:]
        aliases = {key: aliases[key] for key in recent if key in aliases}
        _write_json(
            map_path,
            {"schema_version": 1, "aliases": aliases, "recent": recent},
        )
        return logical


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts)


def _latest_compaction_summary(history: Any) -> str:
    """Return the newest Hermes batch or micro-compaction handoff."""

    if not isinstance(history, list):
        return ""
    for message in reversed(history):
        if not isinstance(message, dict):
            continue
        text = _content_text(message.get("content")).strip()
        if not text:
            continue
        if message.get("_compressed_summary"):
            return text
        if _SUMMARY_PREFIX in text or text.startswith(_LEGACY_SUMMARY_PREFIX):
            return text
    return ""


def _run_guard(event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Call the shared LHC guard through its stable dependency-free CLI."""

    tool = _root() / "common/tools/lhc_time_guard.py"
    if not tool.is_file():
        return None
    completed = subprocess.run(
        [sys.executable, os.fspath(tool), "hook", "--runtime", "hermes", "--event", event],
        input=json.dumps(payload, ensure_ascii=False),
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


def _new_summary(
    agents_root: Path, logical_session: str, summary: str
) -> bool:
    """Mark a changed native summary exactly once across plugin reloads."""

    root = agents_root / "shared-session" / "compaction" / logical_session
    state_path = root / "hermes-observer.json"
    lock_path = root / "hermes-observer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = _read_json(state_path)
        if state.get("latest_summary_sha256") == digest:
            return False
        _write_json(
            state_path,
            {"schema_version": 1, "latest_summary_sha256": digest},
        )
        return True


def observe_pre_llm(
    *,
    session_id: str = "",
    parent_session_id: str = "",
    user_message: str = "",
    conversation_history: Any = None,
    **_: Any,
) -> dict[str, str] | None:
    """Run hourly control and restore one bounded handoff after compaction."""

    cwd = Path.cwd().resolve()
    agents_root = _agents_root(cwd)
    if agents_root is None:
        return None
    logical = _logical_session_id(agents_root, session_id, parent_session_id)
    payload: dict[str, Any] = {
        "cwd": os.fspath(cwd),
        "session_id": logical,
        "trigger": "hermes-pre-llm",
        "prompt": user_message,
    }
    contexts: list[str] = []
    control = _run_guard("chat.message", payload)
    if control and isinstance(control.get("prompt"), str) and control["prompt"].strip():
        contexts.append(control["prompt"].strip())

    summary = _latest_compaction_summary(conversation_history)
    if summary and _new_summary(agents_root, logical, summary):
        compact_payload = {**payload, "native_handoff": summary}
        _run_guard("PreCompact", compact_payload)
        completed = _run_guard("PostCompact", compact_payload)
        if completed and isinstance(completed.get("handoff"), str):
            contexts.append(completed["handoff"].strip())

    if not contexts:
        return None
    return {"context": "\n\n".join(contexts)}


def _marker(text: str) -> str:
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        return ""
    return "\n".join(lines[starts[0] : ends[0] + 1]).strip()


def load_marked_project_block(cwd: Path | None = None) -> str:
    base = cwd or Path.cwd()
    blocks = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        block = _marker(_read(base / name))
        if block:
            blocks.append(block)
    if len(blocks) == 2 and blocks[0] != blocks[1]:
        return ""
    return blocks[0] if blocks else ""


def load_role_prompt(role: str) -> str:
    filename = ROLES.get(role.strip().lower())
    if not filename:
        return ""
    return _read(_root() / "common/agents" / f"{filename}.md").strip()


def load_harness_overlay() -> str:
    """Load only the adapter's small harness-specific overlay."""
    return _read(Path(__file__).with_name("instructions.md")).strip()


def _role_from_goal(goal: str) -> str | None:
    match = ROLE_TAG.search(goal or "")
    if not match:
        return None
    role = match.group("role").lower()
    return role if role in ROLES else None


def _context(role: str) -> str:
    # The marker is an opt-in boundary. Its text is not injected here because
    # a resolved role must not also receive a router telling it to load a role.
    if not load_marked_project_block():
        return ""
    role_prompt = load_role_prompt(role)
    if not role_prompt:
        return ""
    parts = [
        f"[Last Human Commit child role: {role}]",
        "The following is the complete role context. Do not load another "
        "role file at runtime.",
        role_prompt,
    ]
    overlay = load_harness_overlay()
    if overlay:
        parts += ["", "Hermes adapter overlay:", overlay]
    return "\n\n".join(parts)


def _role_item(item: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(item)
    role = _role_from_goal(str(result.get("goal") or ""))
    if not role:
        return result
    context = _context(role)
    if context and "[Last Human Commit child role:" not in str(result.get("context") or ""):
        existing = str(result.get("context") or "").strip()
        result["context"] = "\n\n".join(x for x in (context, existing) if x)
    return result


def rewrite_delegate_task(
    tool_name: str, args: dict[str, Any], **_: Any
) -> dict[str, Any] | None:
    """Rewrite only delegate_task payloads; leave every other tool untouched."""
    if tool_name != "delegate_task" or not isinstance(args, dict):
        return None
    modified = copy.deepcopy(args)
    if isinstance(modified.get("tasks"), list):
        modified["tasks"] = [
            _role_item(item) if isinstance(item, dict) else item
            for item in modified["tasks"]
        ]
    elif isinstance(modified.get("goal"), str):
        item = _role_item({"goal": modified["goal"], "context": modified.get("context", "")})
        modified["context"] = item.get("context", modified.get("context", ""))
    return {"args": modified}


def register(ctx: Any) -> None:
    ctx.register_middleware("tool_request", rewrite_delegate_task)
    ctx.register_hook("pre_llm_call", observe_pre_llm)
