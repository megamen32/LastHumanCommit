"""Real CLI/stdio exercise attribution and explicit execution surfaces."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_plan_json as pj

@pytest.fixture
def plan(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "absent"))
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    (tmp_path / "leaves").mkdir()
    (tmp_path / "plan.json").write_text(json.dumps({"title": "interface", "slots": 1}))
    (tmp_path / "leaves/L01.json").write_text(json.dumps(
        {"id": "L01", "label": "test", "status": "queued", "session": "legacy-assignee", "harness": "codex"}))
    return tmp_path

def run_cli(*args):
    return subprocess.run([sys.executable, str(TOOLS / "lhc_plan_json.py"), *map(str, args)],
                          capture_output=True, text=True, timeout=20)

def rpc(name, arguments, meta=None, identifier=1):
    params = {"name": name, "arguments": arguments}
    if meta is not None:
        params["_meta"] = meta
    return {"jsonrpc": "2.0", "id": identifier, "method": "tools/call", "params": params}

def read(plan):
    return json.loads((plan / "leaves/L01.json").read_text())

def assignment(attempt="attempt"):
    lead = {"host_id": "test-host", "harness": "codex", "session_id": "test-lead"}
    return {"schema_version": 1, "attempt_id": attempt, "executor_kind": "session", "lead": lead,
            "executor": {**lead, "session_id": "test-executor"}, "parent": None, "state": "assigned"}

def serve(messages, env=None):
    result = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_mcp.py")],
        input="".join(json.dumps(x) + "\n" for x in messages), text=True,
        capture_output=True, env=env, timeout=40)
    assert result.returncode == 0, result.stderr
    return [json.loads(x) for x in result.stdout.splitlines()]

def test_real_stdio_request_actor_never_leaks_or_borrows_assignee(plan):
    providers = [
        ({"threadId": "codex-one"}, "codex", "codex-one"),
        ({"ai.opencode/sessionID": "ses_two"}, "opencode", "ses_two"),
        ({"com.zcode/request-context": {"session_id": "zcode-three"}}, "zcode", "zcode-three"),
        (None, None, None),
        ({"threadId": "conflict", "ai.opencode/sessionID": "ses_conflict"}, None, None),
        ({"ai.opencode/sessionID": "wrong-prefix"}, None, None),
        ({"threadId": 12}, None, None),
        ({"threadId": "x" * 513}, None, None),
    ]
    messages = [rpc("update_leaf", {"plan_dir": str(plan), "leaf_id": "L01",
                  "fields": {"note": f"request {i}"}}, meta, i)
                for i, (meta, _, _) in enumerate(providers)]
    # An inherited native environment is the server's identity, not the caller.
    env = {**os.environ, "CODEX_THREAD_ID": "11111111-1111-1111-1111-111111111111",
           "LHC_MCP_ACTOR_CONTEXT": json.dumps({**assignment()["lead"], "source": "mcp_metadata"})}
    replies = serve(messages, env)
    assert all("error" not in x and not x["result"]["isError"] for x in replies), replies
    events = read(plan)["progress_events"]
    assert len(events) == len(providers)
    for event, (_, harness, session) in zip(events, providers):
        actor = event["actor"]
        assert actor["session_id"] == session and actor["harness"] == harness
        assert actor["source"] == ("mcp_metadata" if session else "unknown")
    assert read(plan)["session"] == "legacy-assignee"

def test_public_mcp_surface_and_error_does_not_retain_previous_actor(plan):
    messages = [
        {"jsonrpc": "2.0", "id": 0, "method": "tools/list"},
        rpc("assign_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "assignment": assignment()},
            {"threadId": "native-assigner"}, 1),
        rpc("dispatch_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "attempt_id": "wrong",
                             "message": "do test"}, {"threadId": "error-caller"}, 2),
        rpc("reconcile_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "attempt_id": "wrong"}, None, 3),
        rpc("update_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "fields": {"note": "after error"}}, None, 4),
    ]
    replies = serve(messages)
    names = {x["name"] for x in replies[0]["result"]["tools"]}
    assert {"assign_leaf", "dispatch_leaf", "reconcile_leaf", "accept_leaf"} <= names
    assert not replies[1]["result"]["isError"]
    assert replies[2]["result"]["isError"] and replies[3]["result"]["isError"]
    assert read(plan)["assignment"]["events"][0]["actor"]["session_id"] == "native-assigner"
    assert read(plan)["progress_events"][-1]["actor"]["source"] == "unknown"

def test_actual_cli_assign_accept_and_strict_attempt_error(plan):
    created = run_cli("assign-leaf", plan, "L01", "--assignment", json.dumps(assignment()))
    assert created.returncode == 0, created.stderr
    bad = run_cli("accept-leaf", plan, "L01", "--attempt-id", "wrong", "--result", "not accepted")
    assert bad.returncode == 1 and read(plan)["assignment"]["state"] == "assigned"
    pj.transition_leaf(plan, "L01", "attempt", "dispatching",
        receipt={"dispatch": {"request_id": "r", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt", "submitted",
        receipt={"dispatch": {"request_id": "r", "status": "accepted", "turn_id": "t"}})
    pj.transition_leaf(plan, "L01", "attempt", "result_ready",
        receipt={"observed_runtime": {"state": "completed", "turn_id": "t", "source": "fixture"}})
    accepted = run_cli("accept-leaf", plan, "L01", "--attempt-id", "attempt",
                       "--result", "consumer result", "--actor",
                       json.dumps({**assignment()["lead"], "source": "native_verified"}))
    assert accepted.returncode == 0, accepted.stderr
    assert read(plan)["status"] == "done" and read(plan)["result"] == "consumer result"
    assert read(plan)["assignment"]["events"][-1]["actor"]["source"] == "declared"

def test_atomic_admission_blocks_dependency_and_second_leaf_same_executor(plan):
    pj.assign_leaf(plan, "L01", assignment())
    pj.transition_leaf(plan, "L01", "attempt", "assigned",
        receipt={"observed_runtime": {"state": "idle", "source": "native_verified",
                                     "observed_at": pj.assignments.now()}})
    second = {"id": "L02", "label": "second", "status": "queued", "depends_on": ["L01"]}
    (plan / "leaves/L02.json").write_text(json.dumps(second))
    pj.assign_leaf(plan, "L02", assignment("other-attempt"))
    pj.transition_leaf(plan, "L02", "other-attempt", "assigned",
        receipt={"observed_runtime": {"state": "idle", "source": "native_verified",
                                     "observed_at": pj.assignments.now()}})
    with pytest.raises(ValueError, match="dependencies_unmet"):
        pj.admit_leaf(plan, "L02", "other-attempt", {"dispatch": {"request_id": "r2", "status": "dispatching"}})
    pj.admit_leaf(plan, "L01", "attempt", {"dispatch": {"request_id": "r1", "status": "dispatching"}})
    pj.update_leaf(plan, "L02", {"depends_on": []})
    with pytest.raises(ValueError, match="owner_busy|capacity_full"):
        pj.admit_leaf(plan, "L02", "other-attempt", {"dispatch": {"request_id": "r2", "status": "dispatching"}})


def test_declared_actor_and_malformed_metadata_cannot_claim_native(plan):
    declared = {**assignment()["lead"], "source": "mcp_metadata"}
    first = rpc("update_leaf", {"plan_dir": str(plan), "leaf_id": "L01",
                "fields": {"note": "declared"}, "actor": declared}, identifier=1)
    second = rpc("update_leaf", {"plan_dir": str(plan), "leaf_id": "L01",
                 "fields": {"note": "malformed"}, "actor": declared}, identifier=2)
    second["params"]["_meta"] = None
    replies = serve([first, second])
    assert all(not x["result"]["isError"] for x in replies)
    actors = [e["actor"] for e in read(plan)["progress_events"]]
    assert actors[0]["source"] == "declared"
    assert actors[1]["source"] == "unknown"

def test_atomic_admission_race_and_stop_are_not_bypassed(plan):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    stamp = pj.assignments.now()
    for leaf_id, attempt in [("L01", "a"), ("L02", "b")]:
        if leaf_id == "L02":
            (plan / "leaves/L02.json").write_text(json.dumps(
                {"id": "L02", "label": "second", "status": "queued"}))
        pj.assign_leaf(plan, leaf_id, assignment(attempt))
        pj.transition_leaf(plan, leaf_id, attempt, "assigned",
            receipt={"observed_runtime": {"state": "idle", "source": "native_verified", "observed_at": stamp}})
    barrier = Barrier(2)
    def admit(leaf_id, attempt):
        barrier.wait(timeout=5)
        try:
            pj.admit_leaf(plan, leaf_id, attempt,
                {"dispatch": {"request_id": "r-" + attempt, "status": "dispatching"}})
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: admit(*pair), [("L01", "a"), ("L02", "b")]))
    assert sum(results) == 1
    remaining = "L02" if results[0] else "L01"
    attempt = "b" if remaining == "L02" else "a"
    pj.transition_leaf(plan, remaining, attempt, "assigned",
        receipt={"observed_runtime": {"state": "stopped", "source": "native_verified",
                                     "observed_at": stamp, "reason_code": "human_stop"}})
    with pytest.raises(ValueError, match="human_stop"):
        pj.admit_leaf(plan, remaining, attempt,
            {"dispatch": {"request_id": "not-sent", "status": "dispatching"}})


def test_mcp_never_auto_binds_the_servers_thread_and_native_activate_uses_caller(plan):
    fresh = plan / "fresh"
    (fresh / "leaves").mkdir(parents=True)
    (fresh / "plan.json").write_text(json.dumps({"title": "fresh"}))
    env = {**os.environ, "CODEX_THREAD_ID": "11111111-1111-1111-1111-111111111111"}
    created = serve([rpc("create_leaf", {"plan_dir": str(fresh),
                        "leaf": {"id": "L01", "label": "fresh", "status": "queued"}})], env)
    assert not created[0]["result"]["isError"]
    leaf = json.loads((fresh / "leaves/L01.json").read_text())
    assert not leaf.get("session")
    assert leaf["progress_events"][-1]["actor"]["source"] == "unknown"
    activated = serve([rpc("activate_leaf", {"plan_dir": str(plan), "leaf_id": "L01"},
                          {"threadId": "actual-caller"})], env)
    assert not activated[0]["result"]["isError"], activated
    assert read(plan)["session"] == "actual-caller"
    assert read(plan)["progress_events"][-1]["actor"]["session_id"] == "actual-caller"


def test_public_cli_dispatch_then_stdio_reconcile_and_accept_on_isolated_http(plan, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import socket
    from threading import Thread
    calls = []
    control = {"delivered": False, "completed": False}
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            assert self.headers.get("Authorization") == "Bearer isolated-fixture-token"
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            method, params = request["method"], request.get("params", {})
            if method == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {}, "serverInfo": {"name": "fixture", "version": "1"}}
            elif method.startswith("notifications/"):
                result = {}
            else:
                name, args = params["name"], params["arguments"]
                calls.append((name, args))
                if name == "session_info":
                    running = control["delivered"] and not control["completed"]
                    result = {"session": {"id": args["sessionId"], "harness": args["harness"],
                        "hostId": args["hostId"], "status": "running" if running else "idle",
                        "cwd": "/fixture", "meta": {"nativeLastTurn": {
                            "turnId": "test-turn" if control["delivered"] else "previous-turn",
                            "status": "inProgress" if running else "completed"}}}}
                elif name == "deliver":
                    control["delivered"] = True
                    result = {"delivery": "accepted", "inputId": args["inputId"],
                              "sessionId": args["sessionId"], "harness": args["harness"], "turnId": "test-turn"}
                elif name == "resume_after" and args["action"] == "wait":
                    dependency = args["dependencies"][0]
                    key = json.dumps([dependency["harness"], dependency["sessionId"]], separators=(",", ":"))
                    result = {"wait": {"id": "fixture-wait", "state": "waiting", "owner": args["owner"],
                                       "dependencyTurns": {key: "test-turn"}}}
                elif name == "resume_after" and args["action"] == "status":
                    result = {"wait": {"id": "fixture-wait", "state": "completed" if control["completed"] else "waiting"}}
                else:
                    raise AssertionError((name, args))
            data = json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": result}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("AGENT_HERDER_HTTP_TOKEN", "isolated-fixture-token")
    monkeypatch.setenv("AGENT_HERDER_HTTP_URL", f"http://127.0.0.1:{server.server_port}/mcp")
    a = assignment()
    a["lead"]["host_id"] = a["executor"]["host_id"] = socket.gethostname()
    try:
        assigned = run_cli("assign-leaf", plan, "L01", "--assignment", json.dumps(a))
        assert assigned.returncode == 0, assigned.stderr
        (plan / "briefs").mkdir()
        (plan / "briefs/L01.md").write_text(json.dumps({
            "task_id": plan.resolve().name, "leaf_id": "L01", "owner/session": a["executor"],
            "parent_lead_identity": a["lead"], "parent_task_id/session/route": {
                "task_id": plan.resolve().name, "session_id": a["lead"]["session_id"],
                "route": "records/L01/result.md"},
            "role": "execution_worker", "mode": "quickfix", "description": "Verify the isolated consumer flow.",
            "acceptance": {"output": "fixture result", "destination": "records/L01/result.md", "checks": "complete fixture flow"},
            "read_paths": ["fixture"], "write_paths": ["records/L01/result.md"],
            "excluded_scope": ["native sessions", "external accounts"], "next_action": "Run the isolated fixture."}))
        dispatched = run_cli("dispatch-leaf", plan, "L01", "--attempt-id", "attempt",
                             "--message", "isolated test work")
        assert dispatched.returncode == 0, dispatched.stderr
        assert read(plan)["assignment"]["state"] == "running"
        assert read(plan)["status"] == "queued"
        control["completed"] = True
        replies = serve([
            rpc("reconcile_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "attempt_id": "attempt"},
                {"threadId": "reconciling-lead"}, 1),
            rpc("accept_leaf", {"plan_dir": str(plan), "leaf_id": "L01", "attempt_id": "attempt",
                               "result": "fixture consumer accepted"}, {"threadId": "accepting-lead"}, 2),
        ])
        assert all(not r["result"]["isError"] for r in replies), replies
        assert read(plan)["assignment"]["state"] == "accepted"
        assert read(plan)["status"] == "done"
        assert read(plan)["progress_events"][-1]["actor"]["session_id"] == "accepting-lead"
        assert sum(name == "deliver" for name, _ in calls) == 1
        assert sum(name == "resume_after" and args["action"] == "wait" for name, args in calls) == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
