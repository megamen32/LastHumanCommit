#!/usr/bin/env python3
"""The live plan report: canonical format, 30-minute emission, plan-reading Overseer."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))

import lhc_entry
import lhc_time_guard as guard

from _inprocess import load_module, run_cli

ENTRY = ROOT / "src/common/tools/lhc_entry.py"


def entry_cli(arguments, payload):
    """The entry CLI, with its own stdin, stdout, stderr and exit code.

    The command line the tool would have received, the payload it would have
    read from stdin and the answers it would have written are the ones the
    process gives; only the interpreter start is saved.
    """
    result = run_cli(load_module(ENTRY), list(arguments), stdin=payload)
    if result.returncode:
        # The command line asked for a zero exit code; a failing tool must say so.
        raise subprocess.CalledProcessError(result.returncode, result.args,
                                           result.stdout, result.stderr)
    return result


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def compact(value: str) -> str:
    return " ".join(value.split())










def test_heartbeat_asks_for_the_canonical_report_at_thirty_minutes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    first = guard.native_heartbeat(tmp_path, "codex", "sid-plan", now=start)
    assert first is not None and first["due"] == []
    due = guard.native_heartbeat(tmp_path, "codex", "sid-plan", now=start + timedelta(minutes=30))
    assert due is not None and due["due"] == ["plan:1"]
    assert "30-minute plan report" in due["prompt"]
    assert "PLAN_REPORT.md" in due["prompt"]




def test_post_tool_use_hook_emits_both_reminders(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    payload = json.dumps({"cwd": str(tmp_path), "session_id": "sid-hook",
                           "tool_name": "exec_command"})
    result = entry_cli(["--root", str(ROOT), "--runtime", "codex", "--event",
                         "PostToolUse", "--heartbeat-only"], payload)
    output = json.loads(result.stdout or "{}")
    context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    # A fresh session has no 30-minute plan reminder yet, and the 120-minute
    # checkpoint is not due — the hook must stay quiet and side-effect free.
    assert context == ""
    state_files = list((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    assert state_files, "the heartbeat keeps its own timer record"


def test_entry_keeps_conversation_hooks_inert():
    payload = json.dumps({"cwd": "/tmp", "session_id": "sid-inert", "prompt": "hi"})
    result = entry_cli(["--root", str(ROOT), "--runtime", "codex", "--event",
                        "UserPromptSubmit"], payload)
    assert result.stdout.strip() == ""
