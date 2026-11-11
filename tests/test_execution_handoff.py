"""Durable scoped dispatch through canonical plan admission, without native sends."""
import hashlib
import json
from pathlib import Path
import sys
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_plan_json as pj
import lhc_execution as ex

BRIEF = """task_id: fixture-task
leaf_id: L1
owner/session: worker
parent_lead_identity: lead
parent_task_id/session/route: fixture-task/lead/records/L1/result.md
role: execution_worker
mode: quickfix
user_outcome: The consumer receives the corrected output.
task_title: Repair the scoped output
description: Read the supplied fixture and repair its output for the consumer.
acceptance: {"output": "Corrected fixture output", "destination": "records/L1/result.md", "checks": "The fixture yields the expected output"}
dependencies: []
read_paths: [input/source.py, input/case.json]
write_paths: [output/result.py]
affected_files: [output/result.py]
excluded_scope: [runtime, external messages]
estimate_minutes: {minimum: 1, maximum: 15}
estimate_basis/uncertainty: One local fixture.
next_action: Open input/case.json and reproduce its wrong output.
verified_lead_decisions: Only the listed local paths are authorized.
"""

class Transport:
    host_id = "fixture-host"
    def __init__(self):
        self.sent = []
    def call(self, name, args):
        if name == "deliver":
            self.sent.append(args)
            return {"delivery": "accepted", "inputId": args["inputId"],
                    "sessionId": "worker", "harness": "codex"}
        assert name == "session_info"
        return {"session": {"id": "worker", "harness": "codex", "hostId": self.host_id,
                            "status": "idle", "meta": {}}}

@pytest.fixture
def plan(tmp_path, monkeypatch):
    tmp_path = tmp_path / "fixture-task"
    tmp_path.mkdir()
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("LHC_MCP_ACTOR_CONTEXT", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "absent"))
    (tmp_path / "leaves").mkdir()
    (tmp_path / "briefs").mkdir()
    (tmp_path / "plan.json").write_text(json.dumps({"title": "Handoff", "slots": 1}))
    (tmp_path / "leaves/L1.json").write_text(json.dumps({"id": "L1", "label": "repair", "status": "queued"}))
    lead = {"host_id": "fixture-host", "harness": "codex", "session_id": "lead"}
    pj.assign_leaf(tmp_path, "L1", {"schema_version": 1, "attempt_id": "attempt", "state": "assigned",
        "executor_kind": "session", "lead": lead, "executor": {**lead, "session_id": "worker"}})
    return tmp_path

def read(plan):
    return json.loads((plan / "leaves/L1.json").read_text())

@pytest.mark.parametrize("missing", ["brief", "description", "acceptance", "read_paths", "write_paths", "excluded_scope", "next_action"])
def test_incomplete_brief_cannot_dispatch(plan, missing):
    if missing != "brief":
        brief = chr(10).join(line for line in BRIEF.splitlines() if not line.startswith(missing + ":"))
        (plan / "briefs/L1.md").write_text(brief)
    transport = Transport()
    with pytest.raises(ValueError, match="brief"):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent
    assert read(plan)["assignment"]["state"] == "assigned"

def test_exact_packet_is_saved_and_delivered_without_public_payload(plan):
    (plan / "briefs/L1.md").write_text(BRIEF)
    transport = Transport()
    result = ex.dispatch_leaf(plan, "L1", "attempt", "private caller input: 934-xyz", transport=transport)
    assert len(transport.sent) == 1
    message = transport.sent[0]["message"]
    assert str(plan.resolve()) in message and "leaf: L1" in message and "attempt: attempt" in message
    assert BRIEF in message and "private caller input: 934-xyz" in message
    identity = result["dispatch"]["handoff"]
    assert identity["brief_sha256"] == hashlib.sha256(BRIEF.encode()).hexdigest()
    assert identity["payload_sha256"] == hashlib.sha256(message.encode()).hexdigest()
    saved = json.loads((plan / identity["record_path"]).read_text())
    assert saved["message"] == message and saved["brief"] == BRIEF
    assert "934-xyz" not in json.dumps(read(plan))
    ex.dispatch_leaf(plan, "L1", "attempt", "do not replay", transport=transport)
    assert len(transport.sent) == 1


class UnknownOnceTransport(Transport):
    """Herder fixture: the first delivery answers admissionUnknown."""

    def __init__(self):
        super().__init__()
        self.failures = 1

    def call(self, name, args):
        if name == "deliver" and self.failures > 0:
            self.failures -= 1
            self.sent.append(args)
            return {"admissionUnknown": True, "delivery": "unknown"}
        return super().call(name, args)


def test_unknown_delivery_retries_the_exact_persisted_payload_once(plan):
    (plan / "briefs/L1.md").write_text(BRIEF)
    transport = UnknownOnceTransport()
    first = ex.dispatch_leaf(plan, "L1", "attempt", "private caller input: 934-xyz", transport=transport)
    assert first["state"] == "delivery_unknown"
    assert len(transport.sent) == 1
    # ACTION_POLICY: the guarded retry re-sends the exact persisted bytes under
    # the same request id, even when the caller supplies a different message.
    second = ex.dispatch_leaf(plan, "L1", "attempt", "different retry text: 935-abc", transport=transport)
    assert len(transport.sent) == 2
    assert transport.sent[1]["inputId"] == transport.sent[0]["inputId"]
    assert transport.sent[1]["message"] == transport.sent[0]["message"]
    assert "935-abc" not in transport.sent[1]["message"]
    leaf = read(plan)
    assert leaf["assignment"]["state"] == "submitted"
    assert leaf["assignment"]["dispatch"]["retries"] == 1
    assert leaf["assignment"]["dispatch"]["handoff"] == first["dispatch"]["handoff"]
    identity = second["dispatch"]["handoff"]
    assert identity["payload_sha256"] == hashlib.sha256(transport.sent[1]["message"].encode()).hexdigest()
    # The budget is spent: a third call is a read, never another send.
    ex.dispatch_leaf(plan, "L1", "attempt", "still no third send", transport=transport)
    assert len(transport.sent) == 2


def test_public_cli_and_mcp_raw_message_require_brief(plan):
    import os
    import subprocess
    env = {**os.environ, "XDG_STATE_HOME": str(plan / "state"),
           "LHC_PLAN_MIRROR_CONFIG": str(plan / "absent")}
    command = [sys.executable, str(TOOLS / "lhc_plan_json.py"), "dispatch-leaf",
               str(plan), "L1", "--attempt-id", "attempt", "--message", "private-caller-918"]
    cli = subprocess.run(command, capture_output=True, text=True, env=env, timeout=20)
    assert cli.returncode != 0 and "brief" in cli.stderr
    assert "private-caller-918" not in cli.stderr + cli.stdout
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "dispatch_leaf", "arguments": {"plan_dir": str(plan), "leaf_id": "L1",
        "attempt_id": "attempt", "message": "private-caller-918"}}}
    mcp = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_mcp.py")],
        input=json.dumps(request) + "\n", capture_output=True, text=True, env=env, timeout=20)
    reply = json.loads(mcp.stdout)
    assert reply["result"]["isError"] and "brief" in mcp.stdout
    assert "private-caller-918" not in mcp.stdout + mcp.stderr
    assert read(plan)["assignment"]["state"] == "assigned"


def test_brief_change_after_intent_cannot_change_delivered_bytes(plan, monkeypatch):
    (plan / "briefs/L1.md").write_text(BRIEF)
    write = pj._write_atomic
    def edit_after_intent(path, value):
        result = write(path, value)
        if Path(path).name == "L1.json" and json.loads(value)["assignment"]["state"] == "dispatching":
            (plan / "briefs/L1.md").write_text(BRIEF.replace("Read the supplied", "CHANGED Read the supplied"))
        return result
    monkeypatch.setattr(pj, "_write_atomic", edit_after_intent)
    transport = Transport()
    result = ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert BRIEF in transport.sent[0]["message"]
    assert "CHANGED" not in transport.sent[0]["message"]
    identity = result["dispatch"]["handoff"]
    assert identity["brief_sha256"] == hashlib.sha256(BRIEF.encode()).hexdigest()
    saved = plan / identity["record_path"]
    assert saved.stat().st_mode & 0o777 == 0o600
    assert saved.parent.stat().st_mode & 0o777 == 0o700


def test_failed_intent_write_never_sends_and_conflicting_snapshot_fails_closed(plan, monkeypatch):
    (plan / "briefs/L1.md").write_text(BRIEF)
    write = pj._write_atomic
    def fail_intent(path, value):
        if Path(path).name == "L1.json" and json.loads(value)["assignment"]["state"] == "dispatching":
            raise OSError("fixture crash before durable intent")
        return write(path, value)
    monkeypatch.setattr(pj, "_write_atomic", fail_intent)
    transport = Transport()
    with pytest.raises(OSError, match="fixture crash"):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent
    assert read(plan)["assignment"]["state"] == "assigned"
    monkeypatch.setattr(pj, "_write_atomic", write)
    with pytest.raises(ValueError, match="brief_record_mismatch"):
        ex.dispatch_leaf(plan, "L1", "attempt", "changed input", transport=transport)
    assert not transport.sent


def test_handoff_identity_persists_and_cannot_be_replaced(plan):
    (plan / "briefs/L1.md").write_text(BRIEF)
    result = ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=Transport())
    identity = result["dispatch"]["handoff"]
    with pytest.raises(ValueError, match="handoff identity"):
        pj.transition_leaf(plan, "L1", "attempt", "submitted", receipt={
            "dispatch": {"handoff": {**identity, "payload_sha256": "0" * 64}}})
    assert read(plan)["assignment"]["dispatch"]["handoff"] == identity


@pytest.mark.parametrize("field,value,error", [
    ("acceptance", "Tests pass.", "brief_acceptance"),
    ("parent_task_id/session/route", "task/other/result.md", "brief_return_route"),
    ("owner/session", "different-worker", "brief_executor"),
    ("parent_lead_identity", "different-lead", "brief_return_identity"),
    ("read_paths", "[]", "brief_source_or_input"),
    ("write_paths", "[]", "brief_write_scope"),
])
def test_role_contract_rejects_ambiguous_input_output_or_owner(plan, field, value, error):
    brief = "\n".join(field + ": " + value if line.startswith(field + ":") else line
                      for line in BRIEF.splitlines())
    (plan / "briefs/L1.md").write_text(brief)
    transport = Transport()
    with pytest.raises(ValueError, match=error):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent


def test_reader_can_explicitly_own_no_source_writes(plan):
    brief = BRIEF.replace("role: execution_worker", "role: research_worker").replace(
        "write_paths: [output/result.py]", "write_paths: []")
    (plan / "briefs/L1.md").write_text(brief)
    transport = Transport()
    result = ex.dispatch_leaf(plan, "L1", "attempt", "read and report", transport=transport)
    assert result["state"] == "submitted" and len(transport.sent) == 1


@pytest.mark.parametrize("oversize", ["brief", "payload"])
def test_oversize_packet_is_actionable_without_truncating_or_sending(plan, oversize):
    import lhc_handoff
    brief = BRIEF + ("\ninput: " + "x" * lhc_handoff.MAX_BRIEF_BYTES if oversize == "brief" else "")
    (plan / "briefs/L1.md").write_text(brief)
    transport = Transport()
    message = "x" * lhc_handoff.MAX_PAYLOAD_BYTES if oversize == "payload" else "read"
    with pytest.raises(ValueError, match="too_large:limit_bytes"):
        ex.dispatch_leaf(plan, "L1", "attempt", message, transport=transport)
    assert not transport.sent

def test_private_snapshot_self_excludes_from_git_in_any_plan_location(plan):
    import subprocess
    subprocess.run(["git", "init", "-q", str(plan)], check=True, capture_output=True)
    (plan / "briefs/L1.md").write_text(BRIEF)
    result = ex.dispatch_leaf(plan, "L1", "attempt", "private caller input", transport=Transport())
    snapshot = result["dispatch"]["handoff"]["record_path"]
    ignored = subprocess.run(["git", "check-ignore", "--no-index", snapshot],
                             cwd=plan, capture_output=True, text=True)
    assert ignored.returncode == 0, "private handoff must exclude itself without root ignore changes"

def test_graph_and_show_derive_control_from_live_adapter_not_cached_claim(plan, monkeypatch):
    import types
    control = {"goal_status": "unaccepted", "frontier": "exhausted", "next_decision": "required",
               "fingerprint": "fixture-live-fingerprint", "reason": "bound_native_outcome"}
    seen = []
    def resolve(path):
        seen.append(str(Path(path).resolve()))
        return dict(control)
    monkeypatch.setitem(sys.modules, "lhc_plan_control", types.SimpleNamespace(resolve_control=resolve))
    (plan / "plan.graph.json").write_text(json.dumps({"goal_control": {"goal_status": "accepted"}}))
    document = pj.build_document(plan)
    assert document["goal_control"] == control
    assert "goal=unaccepted" in pj.plan_state(plan)
    assert "next_decision=required" in "\\n".join(pj.plan_summary(plan))
    assert seen and all(value == str(plan.resolve()) for value in seen)


def test_explicit_cli_activation_binds_existing_outcome_with_actual_selected_identity(plan, monkeypatch, capsys):
    import types
    called = []
    def bind(path, session, cwd, runtime=None):
        called.append((str(Path(path).resolve()), session, runtime))
        return {"binding": "unknown", "reason": "native_outcome_missing"}
    monkeypatch.setitem(sys.modules, "lhc_plan_control", types.SimpleNamespace(bind_session_plan=bind))
    result = pj.main(["activate", str(plan), "L1", "--session", "lead", "--harness", "codex", "--owner", "fixture"])
    assert result == 0
    assert called == [(str(plan.resolve()), "lead", "codex")]
    assert "native_outcome_missing" in capsys.readouterr().out


def test_mcp_exposes_live_control_and_explicit_decision_with_native_actor(monkeypatch, plan):
    import importlib
    mcp = importlib.import_module("lhc_plan_mcp")
    names = {tool["name"] for tool in mcp.TOOLS}
    assert {"read_goal_control", "record_frontier_decision"} <= names
    calls = []
    monkeypatch.setattr(mcp, "_plan_cli", lambda arguments, operation, *extra: calls.append((operation, extra)) or {})
    token = mcp._request_actor.set({"source": "mcp_metadata", "harness": "codex", "session_id": "lead"})
    try:
        mcp.record_frontier_decision({"plan_dir": str(plan),
            "decision": {"decision": "need_fact", "action_kind": "research", "action": "inspect fixture",
                         "owner": "lead", "evidence": "missing proof", "uncertainty": "fixture not run"}})
    finally:
        mcp._request_actor.reset(token)
    assert calls[0][0] == "goal-control" and "--decision" in calls[0][1]
    assert "--session" in calls[0][1] and "lead" in calls[0][1]


@pytest.mark.parametrize("linked", ["directory", "file"])
def test_brief_symlinks_are_rejected_without_native_io(plan, linked):
    outside = plan.parent / "outside"
    outside.mkdir()
    (outside / "L1.md").write_text(BRIEF)
    if linked == "directory":
        (plan / "briefs").rmdir()
        (plan / "briefs").symlink_to(outside, target_is_directory=True)
    else:
        (plan / "briefs/L1.md").symlink_to(outside / "L1.md")
    transport = Transport()
    with pytest.raises(ValueError, match="brief"):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent
    assert read(plan)["assignment"]["state"] == "assigned"


def test_fifo_brief_is_rejected_without_waiting_for_writer(plan):
    import os
    import subprocess
    os.mkfifo(plan / "briefs/L1.md")
    code = """import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import lhc_handoff
plan = Path(sys.argv[2])
assignment = json.loads((plan / 'leaves/L1.json').read_text())['assignment']
try:
    lhc_handoff.read_brief(plan, 'L1', assignment, {})
except ValueError as error:
    print(error)
else:
    raise SystemExit('non-regular brief accepted')
"""
    try:
        run = subprocess.run([sys.executable, "-c", code, str(TOOLS), str(plan)],
                             capture_output=True, text=True, timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail("FIFO brief blocks admission before any native I/O")
    assert run.returncode == 0 and "brief" in run.stdout
    assert read(plan)["assignment"]["state"] == "assigned"


@pytest.mark.parametrize("nested", [False, True])
def test_duplicate_json_contract_keys_fail_closed(plan, nested):
    import lhc_handoff
    fields = lhc_handoff._fields(BRIEF)
    fields["acceptance"] = {"output": "result", "destination": "records/L1/result.md", "checks": "run fixture"}
    if nested:
        fields["owner/session"] = read(plan)["assignment"]["executor"]
        brief = json.dumps(fields).replace('"session_id": "worker"',
                                          '"session_id": "different", "session_id": "worker"')
    else:
        brief = json.dumps(fields).replace('"leaf_id": "L1"', '"leaf_id": "OTHER", "leaf_id": "L1"')
    (plan / "briefs/L1.md").write_text(brief)
    transport = Transport()
    with pytest.raises(ValueError, match="brief_duplicate"):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent


def test_task_identity_is_canonical_directory_not_optional_metadata(plan):
    (plan / "briefs/L1.md").write_text(BRIEF.replace("fixture-task", "foreign-task"))
    assert "task_id" not in pj.plan_metadata(plan)
    transport = Transport()
    with pytest.raises(ValueError, match="brief_task_mismatch"):
        ex.dispatch_leaf(plan, "L1", "attempt", "repair now", transport=transport)
    assert not transport.sent


def test_public_cli_and_stdio_share_existing_native_control(plan):
    import os
    import subprocess
    pytest.importorskip("lhc_plan_control")
    import lhc_time_guard as guard
    target = plan / "native-control"
    (target / "leaves").mkdir(parents=True)
    (target / "plan.json").write_text(json.dumps({"goal": "Deliver fixture", "deliverable": "implementation"}))
    (target / "leaves/G1.json").write_text(json.dumps({"id": "G1", "label": "Fixture", "status": "queued"}))
    outcome = {"id": "fixture-goal", "task_class": "fullcycle", "contract_confirmed": True,
               "original_goal": "Deliver fixture", "latest_correction": "Deliver fixture",
               "owner": {"harness": "codex", "session_id": "lead"}, "cwd": str(target),
               "canary": {"scenario": "Run fixture", "target": "isolated", "expected": "Fixture result"},
               "stages": {key: {"status": "pending", "basis": "fixture not accepted"}
                          for key in ("technical", "deploy", "consumer", "publication", "integration")}}
    state_path = guard.learning_path(target, "codex", "lead")
    guard.write_state(state_path, {"business": {"outcome": outcome}})
    def cli(*args):
        run = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_json.py"), *map(str, args)],
                             capture_output=True, text=True, timeout=20)
        assert run.returncode == 0, run.stderr
        return json.loads(run.stdout)
    activated = cli("activate", target, "G1", "--session", "lead", "--harness", "codex", "--owner", "lead")
    assert activated["goal_binding"]["binding"] == "bound"
    pj.update_leaf(target, "G1", {"status": "done", "result": "Fixture implementation complete"})
    view = cli("goal-control", target)
    assert view["goal_status"] == "unaccepted" and view["next_decision"] == "required"
    decision = {"decision": "need_fact", "action_kind": "research", "action": "Inspect fixture result",
                "owner": "lead", "evidence": "Consumer proof missing", "uncertainty": "Fixture not accepted"}
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "record_frontier_decision", "arguments": {"plan_dir": str(target), "decision": decision},
        "_meta": {"threadId": "lead"}}}
    env = {**os.environ, "CODEX_THREAD_ID": "unrelated-server-thread"}
    run = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_mcp.py")],
                         input=json.dumps(request) + "\n", capture_output=True, text=True, env=env, timeout=20)
    reply = json.loads(run.stdout)
    assert "error" not in reply and not reply["result"]["isError"], reply
    saved = guard.load_state(state_path)["business"]["outcome"]
    assert saved["frontier_decision"]["action"] == decision["action"]
    assert saved["owner"]["session_id"] == "lead"
    view = cli("goal-control", target)
    assert view["goal_status"] == "unaccepted" and view["next_decision"] == "work"
    assert pj.build_document(target)["goal_control"]["fingerprint"] == view["fingerprint"]
    # Unknown MCP callers cannot borrow the server process's native thread.
    request["params"].pop("_meta")
    denied = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_mcp.py")],
                           input=json.dumps(request) + "\n", capture_output=True, text=True, env=env, timeout=20)
    assert "explicit native session" in json.loads(denied.stdout)["error"]["message"]
    assert guard.load_state(state_path)["business"]["outcome"] == saved
