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
