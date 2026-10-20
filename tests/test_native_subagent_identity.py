from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_native_identity as identity  # noqa: E402


PARENT = "01a15955-14be-7920-acc6-e6e9dd947cb7"
CHILD = "01a15a4f-1dd2-78e3-8dad-cf63d441b3b4"
SIBLING = "01a15a4f-aaaa-7bbb-8ccc-cf63d441b3b4"
AGENT_PATH = "/root/worker"


def native_home(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / ".codex"
    (home / "sessions").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODEX_HOME", str(home))
    return home


def write_jsonl(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def session_header(session_id: str, *, parent: str | None = None, cwd: str = "/repo",
                   agent_path: str | None = None) -> dict:
    payload = {"id": session_id, "session_id": parent or session_id, "cwd": cwd}
    if parent:
        payload.update({"parent_thread_id": parent, "originator": "agent-herder",
                        "agent_path": agent_path,
                        "source": {"subagent": {"thread_spawn": {"parent_thread_id": parent}}}})
    return {"type": "session_meta", "timestamp": "2026-10-20T17:00:00Z", "payload": payload}


def parent_rows(child_id: str = CHILD, *, child_path: str = AGENT_PATH,
                parent_id: str = PARENT, cwd: str = "/repo", call_id: str = "call-1",
                receipt_call_id: str | None = None,
                output: str = '{"task_name":"/root/worker"}', kind: str = "started"):
    return [
        session_header(parent_id, cwd=cwd),
        {"type": "response_item", "timestamp": "2026-10-20T17:00:01Z", "payload": {
            "type": "function_call", "name": "spawn_agent", "call_id": call_id,
            "arguments": '{"task_name":"worker","message":"opaque historical content"}'}},
        {"type": "event_msg", "timestamp": "2026-10-20T17:00:02Z", "payload": {
            "type": "item_completed", "thread_id": parent_id,
            "item": {"type": "SubAgentActivity", "id": receipt_call_id or call_id, "kind": kind,
                      "agent_thread_id": child_id, "agent_path": child_path}}},
        {"type": "response_item", "timestamp": "2026-10-20T17:00:03Z", "payload": {
            "type": "function_call_output", "call_id": call_id, "output": output}},
    ]


def resolved_pair(tmp_path: Path, monkeypatch, *, child_id: str = CHILD,
                  logical_id: str | None = None, child_parent: str = PARENT,
                  receipt_parent: str = PARENT, child_path: str = AGENT_PATH,
                  receipt_path: str = AGENT_PATH, child_cwd: str = "/repo",
                  observed_native_cwd: str | None = None,
                  parent_cwd: str = "/repo", call_id: str = "call-1",
                  receipt_call_id: str | None = None, kind: str = "started",
                  output: str = '{"task_name":"/root/worker"}', captured_intents=()):
    home = native_home(tmp_path, monkeypatch)
    parent_path = write_jsonl(home / "sessions" / f"parent-{receipt_parent}.jsonl", parent_rows(
        child_id, child_path=receipt_path, parent_id=receipt_parent,
        cwd=parent_cwd, call_id=call_id, receipt_call_id=receipt_call_id,
        output=output, kind=kind))
    child_path_file = write_jsonl(home / "sessions" / f"child-{child_id}.jsonl", [
        session_header(child_id, parent=child_parent, cwd=child_cwd, agent_path=child_path)])
    logical_id = logical_id or identity.composite_session_id(PARENT, child_id)
    result = identity.resolve_child_identity(
        logical_id, parent_path, child_path_file,
        observed_native_cwd=observed_native_cwd or child_cwd,
        captured_intents=captured_intents)
    return result, parent_path, child_path_file


def test_composite_logical_key_resolves_verified_child_to_self(tmp_path, monkeypatch):
    result, parent_path, child_path = resolved_pair(tmp_path, monkeypatch)
    assert result["logical_session_id"] == f"{PARENT}:subagent:{CHILD}"
    assert result["native_id"] == CHILD
    assert result["parent_native_id"] == PARENT
    assert result["agent_path"] == AGENT_PATH
    assert result["native_cwd"] == "/repo"
    assert result["dispatch_call_id"] == "call-1"
    assert result["assignment"]["status"] == "unavailable"
    assert result["assignment"]["reason"] == "no plaintext pre-call capture for this dispatch"
    assert identity.classify_session_relation(result, result) == "self"
    bare = identity.resolve_child_identity(CHILD, None, child_path,
                                           observed_native_cwd="/repo")
    assert identity.classify_session_relation(result, bare) == "self"


@pytest.mark.parametrize("wrong", ["parent", "wrong-parent", "wrong-path", "wrong-cwd"])
def test_child_identity_rejects_nonmatching_logical_or_native_tuple(tmp_path, monkeypatch, wrong):
    kwargs = {}
    if wrong == "sibling":
        kwargs.update(child_id=SIBLING)
    elif wrong == "parent":
        kwargs.update(child_id=PARENT, logical_id=f"{PARENT}:subagent:{PARENT}")
    elif wrong == "wrong-parent":
        kwargs.update(child_parent=SIBLING)
    elif wrong == "wrong-path":
        kwargs.update(child_path="/root/other")
    elif wrong == "wrong-cwd":
        kwargs.update(child_cwd="/other", observed_native_cwd="/repo")
    with pytest.raises(ValueError):
        resolved_pair(tmp_path, monkeypatch, **kwargs)


def test_receipt_must_be_successful_and_match_exact_call_child_and_path(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        resolved_pair(tmp_path, monkeypatch, receipt_call_id="call-other")
    with pytest.raises(ValueError):
        resolved_pair(tmp_path, monkeypatch, kind="failed")
    with pytest.raises(ValueError):
        resolved_pair(tmp_path, monkeypatch, output='{"error":"spawn rejected"}')
    with pytest.raises(ValueError):
        resolved_pair(tmp_path, monkeypatch, kind="interacted")


def test_ambiguous_or_out_of_codex_sources_fail_closed(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    parent = write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", parent_rows())
    child = write_jsonl(home / "sessions" / f"child-{CHILD}.jsonl", [
        session_header(CHILD, parent=PARENT, cwd="/repo", agent_path=AGENT_PATH)])
    with parent.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(parent_rows()[2]) + "\n")
    with pytest.raises(ValueError, match="ambiguous"):
        identity.resolve_child_identity(f"{PARENT}:subagent:{CHILD}", parent, child,
                                         observed_native_cwd="/repo")
    write_jsonl(home / "sessions" / f"duplicate-{CHILD}.jsonl", [
        session_header(CHILD, parent=PARENT, cwd="/repo", agent_path=AGENT_PATH)])
    with pytest.raises(ValueError, match="ambiguous"):
        identity.resolve_child_identity(f"{PARENT}:subagent:{CHILD}", parent, child,
                                         observed_native_cwd="/repo")
    outside = write_jsonl(tmp_path / f"outside-{CHILD}.jsonl", [
        session_header(CHILD, parent=PARENT, cwd="/repo", agent_path=AGENT_PATH)])
    with pytest.raises(ValueError, match="sessions"):
        identity.resolve_child_identity(f"{PARENT}:subagent:{CHILD}", parent, outside,
                                         observed_native_cwd="/repo")


def test_plaintext_pretool_intent_binds_only_after_exact_success_receipt(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", [session_header(PARENT)])
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=None,
        tool_name="spawn_agent", tool_call_id="call-1",
        tool_input={"task_name": "worker", "message": "Inspect and fix the CLI"},
        observed_at="2026-10-20T17:00:00Z")
    assert captured["status"] == "captured"
    result, _, _ = resolved_pair(tmp_path, monkeypatch, captured_intents=[captured])
    assignment = result["assignment"]
    assert assignment["status"] == "bound"
    assert assignment["prompt"] == "Inspect and fix the CLI"
    assert assignment["origin"] == "agent-relay"
    assert assignment["source_call_id"] == "call-1"
    assert assignment["child_id"] == CHILD


def test_actual_collaboration_tool_name_is_captured(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    parent_journal = write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", [session_header(PARENT)])
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_journal,
        tool_name="collaborationspawn_agent", tool_call_id="call-1",
        tool_input={"task_name": "worker", "message": "Scope"},
        observed_at="2026-10-20T17:00:00Z")
    assert captured["status"] == "captured"


def test_child_race_stays_unavailable_until_matching_capture_arrives(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    parent_path = write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", parent_rows())
    child_path = write_jsonl(home / "sessions" / f"child-{CHILD}.jsonl", [
        session_header(CHILD, parent=PARENT, cwd="/repo", agent_path=AGENT_PATH)])
    logical = f"{PARENT}:subagent:{CHILD}"
    before = identity.resolve_child_identity(logical, parent_path, child_path,
                                             observed_native_cwd="/repo")
    assert before["assignment"]["status"] == "unavailable"
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_path, tool_name="spawn_agent",
        tool_call_id="call-1", tool_input={"message": "Actual future task"},
        observed_at="2026-10-20T17:00:04Z")
    after = identity.resolve_child_identity(logical, parent_path, child_path,
                                            observed_native_cwd="/repo",
                                            captured_intents=[captured])
    assert after["dispatch_call_id"] == before["dispatch_call_id"]
    assert after["assignment"]["status"] == "bound"
    assert after["assignment"]["prompt"] == "Actual future task"


@pytest.mark.parametrize("tool_input", [None, "gAAAAABencrypted", {"task_name": "worker"},
                                          {"task_name": "worker", "message": "  "}])
def test_missing_or_encrypted_task_text_stays_unavailable(tmp_path, monkeypatch, tool_input):
    home = native_home(tmp_path, monkeypatch)
    parent_journal = write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", [session_header(PARENT)])
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_journal,
        tool_name="spawn_agent", tool_call_id="call-1", tool_input=tool_input,
        observed_at="2026-10-20T17:00:00Z")
    assert captured["status"] == "unavailable"
    result, _, _ = resolved_pair(tmp_path, monkeypatch, captured_intents=[captured])
    assert result["assignment"]["status"] == "unavailable"
    assert not result["assignment"].get("prompt")


def test_followup_capture_is_not_original_spawn_and_duplicate_conflicts_fail(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    parent_journal = write_jsonl(home / "sessions" / f"parent-{PARENT}.jsonl", [session_header(PARENT)])
    first = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_journal,
        tool_name="spawn_agent", tool_call_id="call-1",
        tool_input={"task_name": "worker", "message": "Original scope"},
        observed_at="2026-10-20T17:00:00Z")
    duplicate = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_journal,
        tool_name="spawn_agent", tool_call_id="call-1",
        tool_input={"task_name": "worker", "message": "Original scope"},
        observed_at="2026-10-20T17:00:01Z")
    assert identity.merge_dispatch_records([first], duplicate) == [first]
    conflict = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_journal,
        tool_name="spawn_agent", tool_call_id="call-1",
        tool_input={"task_name": "worker", "message": "Rewritten scope"},
        observed_at="2026-10-20T17:00:02Z")
    with pytest.raises(ValueError, match="conflict"):
        identity.merge_dispatch_records([first], conflict)
    result, _, _ = resolved_pair(tmp_path, monkeypatch, captured_intents=[first])
    assert result["assignment"]["prompt"] == "Original scope"


def test_pending_and_unavailable_dispatch_records_are_never_evicted():
    rows = [{"call_id": f"call-{n}", "status": "unavailable" if n == 0 else "captured",
             "prompt": f"task-{n}"} for n in range(64)]
    with pytest.raises(ValueError, match="capacity"):
        identity.merge_dispatch_records(rows, {"call_id": "call-new", "status": "pending"})
    assert rows[0]["status"] == "unavailable"


def test_standalone_identity_remains_compatible(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    path = write_jsonl(home / "sessions" / f"standalone-{CHILD}.jsonl", [session_header(CHILD)])
    standalone = identity.resolve_standalone_identity(CHILD, path, observed_native_cwd="/repo")
    assert standalone["native_id"] == CHILD
    assert standalone["logical_session_id"] == CHILD
    assert standalone["parent_native_id"] is None
    assert identity.classify_session_relation(standalone, standalone) == "self"


def test_vscode_native_header_source_string_is_supported(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    path = write_jsonl(home / "sessions" / f"vscode-{CHILD}.jsonl", [{
        "type": "session_meta", "payload": {
            "id": CHILD, "session_id": CHILD, "cwd": "/repo", "source": "vscode"}}])
    header = identity.read_native_header(path)
    assert header["native_id"] == CHILD
    assert header["agent_path"] is None


def test_distinct_standalone_identity_can_be_independent(tmp_path, monkeypatch):
    home = native_home(tmp_path, monkeypatch)
    owner_path = write_jsonl(home / "sessions" / f"owner-{PARENT}.jsonl", [session_header(PARENT)])
    other_path = write_jsonl(home / "sessions" / f"other-{CHILD}.jsonl", [session_header(CHILD)])
    owner = identity.resolve_standalone_identity(PARENT, owner_path, observed_native_cwd="/repo")
    other = identity.resolve_standalone_identity(CHILD, other_path, observed_native_cwd="/repo")
    assert identity.classify_session_relation(owner, other) == "independent"


def test_composite_alias_does_not_turn_sibling_or_parent_into_self(tmp_path, monkeypatch):
    owner, parent_path, _ = resolved_pair(tmp_path, monkeypatch)
    home = parent_path.parent
    sibling_parent_path = parent_path
    with sibling_parent_path.open("a", encoding="utf-8") as stream:
        for row in [
            {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent",
                                                     "call_id": "call-sibling"}},
            {"type": "event_msg", "payload": {"type": "item_completed", "thread_id": PARENT,
                                                   "item": {"type": "SubAgentActivity", "id": "call-sibling",
                                                             "kind": "started", "agent_thread_id": SIBLING,
                                                             "agent_path": "/root/sibling"}}},
            {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call-sibling",
                                                      "output": "{\"task_name\":\"/root/sibling\"}"}},
        ]:
            stream.write(json.dumps(row) + "\n")
    sibling_child_path = write_jsonl(home / "sessions" / f"sibling-{SIBLING}.jsonl", [
        session_header(SIBLING, parent=PARENT, cwd="/repo", agent_path="/root/sibling")])
    sibling = identity.resolve_child_identity(
        f"{PARENT}:subagent:{SIBLING}", sibling_parent_path, sibling_child_path,
        observed_native_cwd="/repo")
    parent = identity.resolve_standalone_identity(PARENT, parent_path, observed_native_cwd="/repo")
    with pytest.raises(ValueError):
        identity.classify_session_relation(owner, sibling)
    with pytest.raises(ValueError):
        identity.classify_session_relation(owner, parent)
