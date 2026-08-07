"""External Hermes adapter for Last Human Commit child-task instructions."""

from __future__ import annotations

import copy
import os
import re
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
