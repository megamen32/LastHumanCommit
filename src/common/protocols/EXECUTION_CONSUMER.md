> Test setup reference. Use it only for an isolated execution-control consumer.
> The product workflow is in `ORCHESTRATION_RECORDS.md`.

# Isolated execution-control consumers

A fresh consumer can exercise the staged package over its real CLI and stdio
MCP using a copied plan and the existing HTTP fixture. The fixture implements
native admission, exact turn observation and wait receipts without a native
harness or a model. No live plan or worker is an input.

Choose two separate run directories under the task's `.tmp/`. One consumer uses
the CLI. The other starts `common/tools/lhc_plan_mcp.py` from the staged package
and uses JSON-RPC initialize, notifications/initialized, tools/list and tools/call.
The same canonical leaf and assignment result should be visible from either
surface. Keep each consumer's temporary plan and environment separate.

## Inputs and boundary

- `LHC_TOOLS` points at the staged package's `common/tools` directory. Do not use
  a second installed package for one half of the scenario.
- Copy `tests/test_lhc_execution.py` from the matching source revision into the
  consumer's run directory as `execution_fixture.py`. It is the existing test
  fixture, not a product server or scheduler.
- Use only the fixture URL and the literal test token below. Remove inherited
  native session IDs from the child environment. Put `XDG_STATE_HOME` in the run
  directory and set `LHC_PLAN_MIRROR_CONFIG` to a nonexistent file there, so
  fixture state and publication settings remain local.
- The fixture IDs `lead` and `worker` exist only in the fake HTTP server. The
  assignment host is the current machine hostname. They are not targets on the
  configured Herder singleton.

A setup driver may keep the fixture alive while launching the package processes:

```python
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

run_dir = Path(sys.argv[1]).resolve()
tools = Path(sys.argv[2]).resolve()  # staged common/tools
spec = importlib.util.spec_from_file_location(
    "execution_fixture", run_dir / "execution_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
fixture_scope = fixture.endpoint.__wrapped__()
endpoint = next(fixture_scope)
url, calls, responses = endpoint
fixture.configure(endpoint)

phase = {"submitted": False, "complete": False}
hostname = socket.gethostname()

def native_read(args):
    terminal = phase["complete"]
    status = "idle" if terminal or not phase["submitted"] else "running"
    turn = "completed" if terminal or not phase["submitted"] else "inProgress"
    return {"session": {
        "id": args["sessionId"], "harness": args["harness"],
        "hostId": hostname, "status": status,
        "model": "fixture-model", "cwd": str(run_dir),
        "meta": {"nativeLastTurn": {"turnId": "turn-1", "status": turn}}
    }}

def deliver(args):
    phase["submitted"] = True
    return {"ok": True, "admitted": True, "delivery": "accepted",
            "inputId": args["inputId"], "turnId": "turn-1",
            "sessionId": args["sessionId"], "harness": args["harness"]}

def resume(args):
    state = "resumed" if phase["complete"] else "waiting"
    return {"wait": fixture.fixture_wait(args, state=state)}

responses.update(session_info=native_read, deliver=deliver, resume_after=resume)
env = dict(os.environ, AGENT_HERDER_HTTP_URL=url,
           AGENT_HERDER_HTTP_TOKEN="fixture-token",
           XDG_STATE_HOME=str(run_dir / "state"),
           LHC_PLAN_MIRROR_CONFIG=str(run_dir / "absent-mirror.json"))
for key in ("CODEX_THREAD_ID", "CLAUDE_SESSION_ID", "OPENCODE_SESSION_ID",
            "LHC_MCP_ACTOR_CONTEXT"):
    env.pop(key, None)

def cli(*args):
    return subprocess.run(
        [sys.executable, str(tools / "lhc_plan_json.py"), *map(str, args)],
        env=env, capture_output=True, text=True, timeout=20)

# Create the copied plan/assignment below, then exercise CLI or stdio.
# Set phase["complete"] = True only after the dispatch result was inspected.
def close_fixture():
    try:
        next(fixture_scope)
    except StopIteration:
        pass

# Call close_fixture() at the end of the consumer journey.
```

Create `plan/leaves/L01.json` with `id`, `label`, `status: "queued"` and no
dependencies. Put `{"title": "isolated execution consumer", "slots": 1}` in its
`plan.json`. Use a fresh assignment:

```python
assignment = {
    "schema_version": 1,
    "attempt_id": "consumer-attempt-1",
    "executor_kind": "session",
    "lead": {"host_id": hostname, "harness": "codex", "session_id": "lead"},
    "executor": {"host_id": hostname, "harness": "codex", "session_id": "worker"},
    "parent": None,
    "state": "assigned",
}
```

## Two consumer journeys

The CLI consumer calls `assign-leaf`, then `dispatch-leaf` with the same attempt
and a scoped fixture message. Inspect the returned assignment and the saved leaf.
Native running requires the exact admission turn, and the Lead wake must contain
the same captured turn. The continuation text should name this plan, leaf and
attempt, not another bound plan.

Then set the fixture's `phase["complete"] = True` and call `reconcile-leaf`.
The result becomes `result_ready` and its wait reads `resumed`. It is still not
accepted or done. Call `accept-leaf --result` with the consumer's verified result
and confirm the leaf becomes done. Save stdout, exit codes and the public leaf
projection.

The stdio consumer performs the same journey with `assign_leaf`,
`dispatch_leaf`, `reconcile_leaf` and `accept_leaf`. Their argument names are
`plan_dir`, `leaf_id`, `assignment` or `attempt_id`, plus required `message` for
dispatch and `result` for acceptance. The MCP process receives exactly the same
fixture environment. A missing caller metadata field should produce unknown
event attribution, not an invented executor or a new permission gate.

For one refusal journey, add another queued prerequisite to the copied plan and
point the target leaf's `depends_on` at it. Dispatch must explain the unmet
dependency and make zero `deliver` calls. A submitted receipt alone must not
satisfy that dependency. Alternatively, let the fixture return a
`delivery: "not_attempted"` quota refusal: it must stay blocked with its reason.

The test fixture's own focused tests cover ambiguous dispatch, unknown wake
registration, a foreign wait receipt and exact-turn mismatch. A consumer may
repeat one of these using its own fresh plan. Never reset or resend an UNKNOWN
attempt to make the demonstration pass.

## Evidence and release impact

Keep exact package revision, tool paths, command/RPC inputs, returned state and
the fixture's call names. The call log must show only the intended read/write
sequence against the local fixture. Redact headers; do not save environment
dumps or credentials.

A separate read-only installed Herder canary may call `list_sessions(scope=node)`
through `HerderMcpClient` to verify the existing transport and protected
configuration. It must not call `deliver`, start a model turn or change an
existing plan. That canary proves connectivity and node identity, while fixture
journeys prove isolated execution-control behavior. Neither is proof that a real
worker's task or an installed product acceptance has completed.

The package adds compatible assignment and execution operations. Existing plan
events and legacy session fields remain readable. Release verification should
check the staged CLI and stdio surface, the lifecycle/actor tests, readiness
consumers, installation readback and existing hook trust. No consumer should need
a new token store, external server, polling agent, scheduler, quota change or
approval workaround.
