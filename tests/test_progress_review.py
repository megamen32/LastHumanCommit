"""Deterministic scheduling/source boundaries; semantics need native model proof."""
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_progress_review as review


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(review.guard, "learning_path", lambda cwd, runtime, sid: tmp_path / "clock.json")
    now = datetime.now(timezone.utc)
    path = tmp_path / "native.jsonl"
    rows = [{"type": "session_meta", "payload": {"id": "sid", "cwd": str(tmp_path), "source": "cli"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "Установи готовый код и проверь реальный результат."}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "channel": "analysis",
                "content": [{"type": "output_text", "text": "PRIVATE_REASONING"}]}},
            {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call1", "output": "code ready but uninstalled"}},
            {"type": "event_msg", "timestamp": now.isoformat(), "payload": {"type": "token_count", "rate_limits": {
                "limit_id": "codex", "primary": {"used_percent": 39}}}}]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    event = {"session_id": "sid", "cwd": str(tmp_path), "turn_id": "turn1", "hook_event_name": "PostToolUse",
             "transcript_path": str(path), "tool_name": "exec_command"}
    (tmp_path / "clock.json").write_text(json.dumps({"native_heartbeat": {
        "started_at": (now - timedelta(minutes=31)).isoformat()}}))
    return tmp_path, event, now


def advice(evidence):
    return {"decision": "redirect", "evidence": "code ready but uninstalled", "action": "Install ready code",
            "owner": "Worker", "uncertainty": "Consumer not checked"}


def state(root):
    return json.loads((root / "clock.progress.json").read_text())


def test_due_once_passes_actual_actions_and_never_private_reasoning(fixture):
    root, event, now = fixture
    captured = []
    result = review.handle(event, now=now, reviewer=lambda e: captured.append(e) or advice(e))
    assert "Install ready code" in result["hookSpecificOutput"]["additionalContext"]
    assert "code ready but uninstalled" in json.dumps(captured)
    assert "PRIVATE_REASONING" not in json.dumps(captured)
    assert review.handle(event, now=now, reviewer=lambda e: pytest.fail("duplicate")) is None
    assert state(root)["status"] == "advised"


def test_not_due_does_not_read_transcript_and_missing_clock_anchor_persists(fixture, monkeypatch):
    root, event, now = fixture
    (root / "clock.json").unlink()
    monkeypatch.setattr(review, "transcript", lambda *a: pytest.fail("read before due"))
    assert review.handle(event, now=now) is None
    assert state(root)["started_at"] == now.isoformat()


def test_model_failure_is_nonblocking_and_not_retried_same_bucket(fixture):
    root, event, now = fixture
    def unavailable(_):
        raise ValueError("model unavailable")
    assert review.handle(event, now=now, reviewer=unavailable) is None
    assert state(root)["status"] == "unavailable"
    assert review.handle(event, now=now, reviewer=lambda e: pytest.fail("retry")) is None


@pytest.mark.parametrize("kind", ["Interrupt", "SessionEnd", "Stop", "UserPromptSubmit"])
def test_native_stop_or_new_user_turn_discards_inflight_advice(fixture, kind):
    root, event, now = fixture
    def stop_then_answer(e):
        review.handle({**event, "hook_event_name": kind, "turn_id": "turn2"}, invalidate=True)
        return advice(e)
    assert review.handle(event, now=now, reviewer=stop_then_answer) is None
    assert state(root)["status"] == "superseded"


def test_native_new_turn_discards_stale_goal(fixture):
    root, event, now = fixture
    def change_goal(e):
        with Path(event["transcript_path"]).open("a") as handle:
            handle.write(json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "Остановись. Только аудит."}]}}) + "\n")
            handle.write(json.dumps({"type": "turn_context", "payload": {"turn_id": "turn2"}}) + "\n")
        return advice(e)
    assert review.handle(event, now=now, reviewer=change_goal) is None
    assert state(root)["status"] == "superseded"


def test_peer_relay_and_tool_results_do_not_starve_inflight_review(fixture):
    root, event, now = fixture
    def peer_delta(e):
        with Path(event["transcript_path"]).open("a") as f:
            f.write(json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "Peer reports ready interface."}]}}) + "\n")
            f.write(json.dumps({"type": "response_item", "payload": {"type": "function_call_output",
                "output": "peer result"}}) + "\n")
        return advice(e)
    assert review.handle(event, now=now, reviewer=peer_delta)
    assert state(root)["status"] == "advised"


def test_inflight_deduplicates_nested_invocation(fixture):
    root, event, now = fixture
    def nested(e):
        assert review.handle(event, now=now, reviewer=lambda e: pytest.fail("second model")) is None
        return advice(e)
    assert review.handle(event, now=now, reviewer=nested)


def test_method_holds_do_not_become_authority(fixture):
    root, event, now = fixture
    clock = json.loads((root / "clock.json").read_text())
    clock.update(native_entry={"finish_hold": "stale metadata"}, milestone={"hold": "receipt"})
    (root / "clock.json").write_text(json.dumps(clock))
    assert review.handle(event, now=now, reviewer=advice)


def test_snapshot_has_total_budget_and_redacts_credentials(fixture):
    root, event, now = fixture
    event.update(tool_input={"token": "DO_NOT_SHARE", "cmd": "curl -H 'Bearer abcdefghijklmnopqrstuvwxyz'"},
                 tool_response={"output": "x" * 240_000})
    def capture(e):
        assert len(json.dumps(e, ensure_ascii=False)) <= 64_000
        assert "DO_NOT_SHARE" not in json.dumps(e)
        assert "abcdefghijklmnopqrstuvwxyz" not in json.dumps(e)
        return advice(e)
    assert review.handle(event, now=now, reviewer=capture)


def test_json_native_arguments_and_output_secrets_are_redacted():
    for value in ['{"token": "EXAMPLE_VALUE", "password": "EXAMPLE_VALUE"}',
                  'Tool output: {"token": "EXAMPLE_VALUE"}']:
        assert "EXAMPLE_VALUE" not in review.scrub(value)


def test_previous_recommendation_and_subsequent_actions_are_compared(fixture):
    root, event, now = fixture
    assert review.handle(event, now=now, reviewer=advice)
    later = now + timedelta(minutes=30)
    with Path(event["transcript_path"]).open("a") as f:
        f.write(json.dumps({"type": "event_msg", "timestamp": later.isoformat(), "payload": {"type": "token_count",
            "rate_limits": {"limit_id": "codex", "primary": {"used_percent": 40}}}}) + "\n")
        f.write(json.dumps({"type": "response_item", "payload": {"type": "function_call_output", "output": "installed; consumer green"}}) + "\n")
    def capture(e):
        assert e["previous_advice"]["action"] == "Install ready code"
        assert "installed; consumer green" in json.dumps(e["recent_actions_results"])
        return {**advice(e), "decision": "continue"}
    assert review.handle(event, now=later, reviewer=capture)


@pytest.mark.parametrize("quota", [None, {"limit_id": "codex", "primary": {"used_percent": 81}}])
def test_unknown_or_low_allowance_does_not_launch_adviser(fixture, quota):
    root, event, now = fixture
    path = Path(event["transcript_path"])
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-1]["payload"]["rate_limits"] = quota
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert review.handle(event, now=now, reviewer=lambda e: pytest.fail("quota")) is None


def test_native_quota_utc_z_is_supported_on_python_310(fixture):
    root, event, now = fixture
    source = {"native_quota": {"at": now.isoformat().replace("+00:00", "Z"),
        "limits": {"limit_id": "codex", "primary": {"used_percent": 40}}}}
    assert review.quota_allows(source, now)


def test_missing_first_quota_has_one_bounded_metadata_retry(fixture):
    root, event, now = fixture
    path = Path(event["transcript_path"])
    original = path.read_text()
    rows = original.splitlines()
    path.write_text("\n".join(rows[:-1]) + "\n")
    assert review.handle(event, now=now, reviewer=lambda e: pytest.fail("no quota")) is None
    assert review.handle(event, now=now+timedelta(seconds=5), reviewer=lambda e: pytest.fail("too early")) is None
    path.write_text(original)
    assert review.handle(event, now=now+timedelta(seconds=11), reviewer=advice)
    assert review.handle(event, now=now+timedelta(seconds=12), reviewer=lambda e: pytest.fail("duplicate")) is None


def test_overseer_role_and_native_subagents_never_recurse(fixture, monkeypatch):
    root, event, now = fixture
    assert review.handle({**event, "agent_id": "child"}, now=now) is None
    monkeypatch.setenv(review.ROLE, "overseer")
    assert review.handle(event, now=now) is None


def test_codex_extension_is_async_and_does_not_force_trust_or_enable_hooks():
    root = TOOLS.parents[2]
    config = json.loads((root / "adapters/codex/hooks/hooks.json").read_text())
    handler = config["hooks"]["PostToolUse"][0]["hooks"][0]
    assert handler["async"] is True
    assert "--invalidate" not in handler["command"]
    for name in ("Interrupt", "Stop", "SessionEnd", "UserPromptSubmit"):
        assert "--invalidate" in config["hooks"][name][0]["hooks"][0]["command"]
    source = (TOOLS / "lhc_progress_review.py").read_text()
    assert "--dangerously" not in source and "--ignore-rules" not in source
