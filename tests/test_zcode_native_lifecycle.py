"""Native ZCode must enter the same LHC lifecycle as the other adapters."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import pytest


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/common/tools/lhc_entry.py"
PLUGIN = ROOT / "plugins/last-human-commit"
NATIVE_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "Stop",
}


def invoke(cwd, event, *, runtime="zcode", **fields):
    payload = {"cwd": str(cwd), "session_id": "zcode-native-test", "turn_id": "turn-one", **fields}
    result = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(ROOT), "--runtime", runtime, "--event", event],
        input=json.dumps(payload), capture_output=True, text=True, timeout=8,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout) if result.stdout.strip() else {}


@pytest.fixture(autouse=True)
def isolate_git_root(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)


def state_file(cwd):
    return next((cwd / ".agents/shared-session/learning").glob("*.json"))


def test_ordinary_zcode_prompt_gets_complete_lhc_context_and_state(tmp_path):
    output = invoke(tmp_path, "UserPromptSubmit", prompt="Fix the empty account label")
    context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert str(ROOT / "AGENTS.md") in context
    for term in ("before", "after", "RED", "80%", "120-minute", "Zero Knowledge"):
        assert term in context
    state = json.loads(state_file(tmp_path).read_text())
    assert state["business"]["original_prompt"] == "Fix the empty account label"
    assert state["native_entry"]["last_context_event"] == "UserPromptSubmit"
    assert state["business"]["interval"]["status"] == "running"


def test_zcode_tool_failure_stays_held_until_a_later_success(tmp_path):
    invoke(tmp_path, "UserPromptSubmit", prompt="Build a complete customer dashboard with search, import and mobile navigation")
    (tmp_path / "dashboard.html").write_text("<main><button>Import</button></main>")
    invoke(tmp_path, "PostToolUseFailure", tool_name="Write", error="permission denied")
    state = json.loads(state_file(tmp_path).read_text())
    assert state["milestone"]["hold"] == "ToolFailure"
    stopped = invoke(tmp_path, "Stop", last_assistant_message="Done")
    assert stopped.get("decision") != "block"
    invoke(tmp_path, "PostToolUse", tool_name="Write", tool_response={"exit_code": 0})
    state = json.loads(state_file(tmp_path).read_text())
    assert state["milestone"].get("hold") is None


def test_zcode_stop_requires_real_milestone_acceptance(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "dashboard.html").write_text("<main>old</main>")
    subprocess.run(["git", "-C", str(tmp_path), "add", "dashboard.html"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Tester", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt="Build a complete customer dashboard with search, import and mobile navigation at https://demo.test/dashboard")
    (tmp_path / "dashboard.html").write_text("<main><input><button>Import</button></main>")
    invoke(tmp_path, "PostToolUse", tool_name="Write", tool_response={"exit_code": 0})

    first = invoke(tmp_path, "Stop", last_assistant_message="The dashboard is implemented.")
    assert first.get("decision") == "block"
    assert "Zero Knowledge" in first["reason"]
    assert json.loads(state_file(tmp_path).read_text())["milestone"]["status"] == "pending"


def test_zcode_stop_holds_an_overdue_workflow_check_once(tmp_path):
    invoke(tmp_path, "UserPromptSubmit", prompt="Ship the actual report")
    path = state_file(tmp_path)
    state = json.loads(path.read_text())
    state["business"]["interval"]["active_ns"] = 3600 * 10**9
    state["due_at"] = "2020-01-01T00:00:00+00:00"
    path.write_text(json.dumps(state))

    first = invoke(tmp_path, "Stop", stop_hook_active=False, last_assistant_message="Done")
    assert first.get("decision") == "block"
    assert "business-review" in first["reason"] and "checkpoint" in first["reason"]
    second = invoke(tmp_path, "Stop", stop_hook_active=True, last_assistant_message="Still working")
    assert second.get("decision") != "block", "native Stop continuation must remain bounded"
    after = json.loads(path.read_text())
    assert after["business"]["pending"] and after["business"]["last_review"] is None


def test_zcode_stop_suppresses_unchanged_due_work_across_new_camelcase_turn(tmp_path):
    invoke(tmp_path, "UserPromptSubmit", prompt="Ship the actual report")
    path = state_file(tmp_path)
    state = json.loads(path.read_text())
    state["business"]["interval"]["active_ns"] = 3600 * 10**9
    state["due_at"] = "2020-01-01T00:00:00+00:00"
    path.write_text(json.dumps(state))

    first = invoke(tmp_path, "Stop", turn_id=None, turnId="turn-one", stop_hook_active=False)
    assert first.get("decision") == "block"
    repeated_same_turn = invoke(tmp_path, "Stop", turn_id=None, turnId="turn-one", stop_hook_active=False)
    assert repeated_same_turn.get("decision") != "block"
    next_turn = invoke(tmp_path, "Stop", turn_id=None, turnId="turn-two", stop_hook_active=False)
    assert next_turn.get("decision") != "block"
    assert "systemMessage" not in next_turn
    after = json.loads(path.read_text())
    assert after["business"]["pending"] and after["business"]["last_review"] is None


def test_zcode_persists_long_prompt_instead_of_referencing_temporary_transcript(tmp_path):
    prompt = "Original ZCode request: retain every requirement. " + "DO_NOT_DROP " * 500
    temporary_transcript = tmp_path / "hook-temp" / "transcript.jsonl"
    invoke(tmp_path, "UserPromptSubmit", prompt=prompt, transcript_path=str(temporary_transcript))

    state = json.loads(state_file(tmp_path).read_text())
    assert state["business"].get("original_prompt_full") == prompt.strip()
    assert state["business"]["runtime"] == "zcode"
    assert "transcript_path" not in state["business"]
    restored = invoke(tmp_path, "SessionStart", source="startup")["hookSpecificOutput"]["additionalContext"]
    assert str(temporary_transcript) not in restored
    assert "original_prompt_full" in restored and str(state_file(tmp_path)) in restored


def test_zcode_short_context_points_to_original_between_excerpt_and_full_prompt_limits(tmp_path):
    prompt = "Original ZCode request: retain every requirement. " + "MID_LENGTH_REQUIREMENT " * 36
    assert 600 < len(prompt) < 4096
    invoke(tmp_path, "UserPromptSubmit", prompt=prompt)

    state = json.loads(state_file(tmp_path).read_text())
    assert state["business"]["original_prompt"] == prompt.strip()
    restored = invoke(tmp_path, "SessionStart", source="startup")["hookSpecificOutput"]["additionalContext"]
    assert "truncated_prompt_source_fields" in restored
    assert "business.original_scope_prompt" in restored
    assert str(state_file(tmp_path)) in restored
    assert prompt not in restored


def test_zcode_hook_bundle_declares_its_supported_native_events():
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
    zcode_hooks = json.loads((PLUGIN / "hooks/zcode-hooks.json").read_text())["hooks"]
    assert (NATIVE_EVENTS - {"PostToolUseFailure"}) <= hooks.keys()
    assert set(zcode_hooks) == {"PostToolUseFailure"}
    manifest = json.loads((PLUGIN / ".zcode-plugin/plugin.json").read_text())
    assert manifest["hooks"] == "./hooks/zcode-hooks.json"


def test_entry_infers_zcode_from_native_plugin_environment(tmp_path):
    payload = json.dumps({"cwd": str(tmp_path), "session_id": "zcode-env-test", "prompt": "Add a label"})
    result = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(ROOT), "--event", "UserPromptSubmit"],
        input=payload, capture_output=True, text=True, timeout=8,
        env={**os.environ, "ZCODE_PLUGIN_ROOT": str(PLUGIN)},
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output.get("hookSpecificOutput", {}).get("hookEventName") == "UserPromptSubmit"
    digest = hashlib.sha256(b"zcode\0zcode-env-test").hexdigest()
    assert state_file(tmp_path).name == digest + ".json"
