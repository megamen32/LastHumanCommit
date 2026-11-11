import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/common/tools/lhc_entry.py"


def load_entry():
    spec = importlib.util.spec_from_file_location("lhc_entry_fast_path", ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(args, payload=None, env=None):
    merged = os.environ.copy()
    merged.pop("LHC_VERBOSE_WORKFLOW", None)
    merged.pop("LHC_STRICT_WORKFLOW", None)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        input=json.dumps(payload or {}),
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def test_context_for_is_compact_and_does_not_inject_plan_ceremony():
    entry = load_entry()
    context = entry.context_for({}, ROOT)
    assert "verify the actual consumer" in context
    assert "three short plan summaries" in context
    assert "Boss audits are mandatory" in context
    for retired in (">15 minutes", "load " + str(ROOT / "skills/plan/SKILL.md"),
                    "Lead delegates", "Overseer", "ACK chain"):
        assert retired not in context


def test_stop_gate_is_advisory_free_by_default(tmp_path):
    entry = load_entry()
    assert entry.stop_gate({"cwd": str(tmp_path)}, ROOT) is None


def test_stop_cli_never_blocks_by_default(tmp_path):
    result = run_cli(["--root", str(ROOT), "--event", "Stop", "--stop-gate"],
                     {"cwd": str(tmp_path), "session_id": "fast-path"})
    assert result.returncode == 0
    assert '"decision": "block"' not in result.stdout


def test_heartbeat_cli_is_silent_by_default(tmp_path):
    result = run_cli(["--root", str(ROOT), "--event", "PostToolUse", "--heartbeat-only"],
                     {"cwd": str(tmp_path), "session_id": "fast-path"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_plan_candidates_are_opt_in():
    entry = load_entry()
    assert entry._plan_entry({"cwd": str(ROOT), "session_id": "s", "prompt": "Fix the bug"}, ROOT) is None
    assert entry._explicit_plan_request({"prompt": "/plan the work"})
    assert entry._explicit_plan_request({"prompt": "Fix the bug"}) is False
