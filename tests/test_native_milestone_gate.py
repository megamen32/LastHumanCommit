"""Actual native hook subprocesses, real Git edits and raw tester transcripts."""
import json
from pathlib import Path
import subprocess
import sys
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone, timedelta
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/common/tools/lhc_entry.py"
GOAL = "Build a complete customer dashboard with search, import and mobile navigation at https://demo.test/dashboard"

def invoke(root, event, **fields):
    result = subprocess.run([sys.executable, str(ENTRY), "--root", str(ROOT), "--runtime", "codex", "--event", event],
        input=json.dumps({"cwd": str(root), "session_id": "leader", "turn_id": "one", **fields}),
        capture_output=True, text=True, check=True, timeout=8, env={**os.environ, "HOME": str(root / "native-home"), "CODEX_HOME": str(root / "native-home/.codex")})
    return json.loads(result.stdout) if result.stdout.strip() else {}

def state(root):
    return json.loads(next((root / ".agents/shared-session/learning").glob("*.json")).read_text())

def setup(root, prompt=GOAL):
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    invoke(root, "UserPromptSubmit", prompt=prompt)
    (root / "dashboard.html").write_text("<main><input type=search><button>Import</button><nav>Reports</nav></main>")
    invoke(root, "PostToolUse", tool_name="exec_command", tool_input={"cmd": "write dashboard"}, tool_response={"exit_code": 0})

def test_normal_major_ui_finish_requires_real_independent_attempts(tmp_path):
    setup(tmp_path)
    result = invoke(tmp_path, "Stop", last_assistant_message="UI done, no user testing")
    assert result.get("decision") == "block", result
    assert "Zero Knowledge" in result["reason"]
    assert state(tmp_path)["milestone"]["status"] == "pending"

def test_own_pass_cannot_clear_milestone(tmp_path):
    setup(tmp_path)
    result = invoke(tmp_path, "Stop", last_assistant_message="Verified. All testers PASS. UI acceptance complete.",
                    acceptance={"status": "accepted", "testers": ["fake1", "fake2"]})
    assert result.get("decision") == "block"
    assert state(tmp_path)["milestone"]["status"] != "accepted"

def export_tester(root, sid="tester-one", persona="Maya, 29, new customer on mobile", outcome="achieved", *,
                  related=True, fresh=True, login=False, interact=True, native=True, same_goal=False):
    m = state(root)["milestone"]
    started = datetime.now(timezone.utc) if fresh else datetime.now(timezone.utc) - timedelta(days=1)
    prompt = (m["goal"] if same_goal else f"Task {m['task']} surface {m['surface_key']}") if related else "An unrelated payroll report task"
    prompt += f"\nPersona: {persona}\nTry the customer goal independently at https://demo.test/dashboard"
    meta = {"id": sid, "timestamp": started.isoformat(), "cwd": str(root)}
    rows = [{"type": "session_meta", "payload": meta}, {"type": "response_item", "payload": {
        "type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}}]
    def operation(n, command, output):
        rows.extend([{"type": "response_item", "payload": {"type": "function_call", "name": "functions.exec_command", "call_id": str(n),
            "arguments": json.dumps({"cmd": command})}}, {"type": "response_item", "payload": {
            "type": "function_call_output", "call_id": str(n), "output": output}}])
    operation(1, f"agent-browser --session {sid} open https://demo.test/dashboard", "Opened dashboard")
    operation(2, f"agent-browser --session {sid} snapshot -i", '- heading "Sign in"\n- textbox "Password"' if login else '- heading "Customers"\n- textbox "Search"\n- button "Import"')
    if interact:
        operation(25, f"agent-browser --session {sid} click @e3", "Imported Maya")
        operation(3, f"agent-browser --session {sid} fill @e2 Maya", "Done")
        operation(4, f"agent-browser --session {sid} snapshot -i", '- heading "Sign in"\n- textbox "Password"' if login else '- heading "Customers"\n- link "Maya, imported customer"')
    final = ("Blocked, not-tested: login requires an authorized test identity. " if login else
             "Goal not achieved; changes-required. " if outcome == "changes-required" else "Goal achieved. ")
    final += "My goal was to import a customer and find them through search. I clicked Import and typed Maya; I saw the imported customer in the results. Positive: I liked the visible import button; it helped me start without searching. Negative: the search label confused me at first."
    rows.append({"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final_answer", "content": [{"type": "output_text", "text": final}]}})
    raw = "\n".join(json.dumps(r) for r in rows) + "\n"
    source = root / ("native-home/.codex/sessions/2026/10/18" if native else "leader-authored") / f"rollout-{sid}.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True); source.write_text(raw)
    archive = root / ".agent-herder/transcripts/codex"
    archive.mkdir(parents=True, exist_ok=True)
    exported = archive / f"{sid}.jsonl"; exported.write_text(raw)
    target = {"harness": "codex", "sessionId": sid, "path": str(exported), "complete": True,
              "source": {"kind": "native-file", "location": str(source), "format": "jsonl"}, "timestampCoverage": "native"}
    manifest = archive / f"{sid}.manifest.json"
    manifest.write_text(json.dumps({"format": "agent-herder-transcript-manifest-v1", "workspaceRoot": str(root), "target": target, "exported": [target]}))
    return manifest

def test_genuine_fresh_feedback_closes_without_leader_attestation(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path)
    export_tester(tmp_path, "tester-two", "Ivan, 61, methodical accountant on desktop")
    assert invoke(tmp_path, "Stop").get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "accepted"
    assert len(state(tmp_path)["milestone"]["feedback"]) == 2

@pytest.mark.parametrize("kwargs", [{"sid": "tester-one"}, {"persona": "Maya, 29, new customer on mobile"},
    {"related": False}, {"fresh": False}, {"interact": False}, {"native": False}, {"sid": "leader"}])
def test_invalid_second_attempt_never_accepts(tmp_path, kwargs):
    setup(tmp_path)
    export_tester(tmp_path)
    export_tester(tmp_path, **{"sid": "tester-two", "persona": "Ivan, 61, accountant on desktop", **kwargs})
    assert invoke(tmp_path, "Stop").get("decision") == "block"
    assert state(tmp_path)["milestone"]["status"] == "pending"

def test_login_only_is_blocked_not_accepted(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path, login=True)
    export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop", login=True)
    assert invoke(tmp_path, "Stop").get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "blocked"

def test_actionable_feedback_is_changes_required_then_fresh_retest_closes(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path, outcome="changes-required")
    export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop")
    assert invoke(tmp_path, "Stop").get("decision") == "block"
    assert state(tmp_path)["milestone"]["status"] == "changes-required"
    (tmp_path / "dashboard.html").write_text("<main><input aria-label='Find customers'><button>Import CSV</button></main>")
    invoke(tmp_path, "PostToolUse")
    export_tester(tmp_path, "tester-three", "Lena, 45, mobile importer")
    export_tester(tmp_path, "tester-four", "Alex, 33, desktop explorer")
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] == "accepted"

def test_compaction_restart_preserves_debt_and_never_repeats_stop_loop(tmp_path):
    setup(tmp_path)
    assert invoke(tmp_path, "Stop").get("decision") == "block"
    invoke(tmp_path, "PreCompact"); invoke(tmp_path, "PostCompact")
    restored = invoke(tmp_path, "SessionStart", source="compact")
    assert "milestone_acceptance" in str(restored)
    assert state(tmp_path)["milestone"]["status"] == "pending"
    for fields in ({"stop_hook_active": True}, {"turn_id": "two"}, {"turn_id": "three"}):
        assert invoke(tmp_path, "Stop", **fields).get("decision") != "block"

@pytest.mark.parametrize("event", ["Interrupt", "PermissionRequest", "ToolFailure", "session.error"])
def test_stopped_permission_and_failure_do_not_reawaken(tmp_path, event):
    setup(tmp_path)
    invoke(tmp_path, event)
    assert invoke(tmp_path, "Stop").get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "pending"

def test_blocked_final_can_explain_incomplete_acceptance(tmp_path):
    setup(tmp_path)
    assert invoke(tmp_path, "Stop", last_assistant_message="Blocked: no authorized login identity; UI acceptance is incomplete.").get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "blocked"

@pytest.mark.parametrize("prompt", ["Fix a small CSS padding issue in the dashboard", "Read-only review of the complete UI dashboard",
    "You are a fresh Zero Knowledge tester. Try the UI goal, do not modify code.", "Status of the dashboard?"])
def test_minor_questions_and_readonly_testers_do_not_recruit(tmp_path, prompt):
    setup(tmp_path, prompt)
    assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_arbitrary_tool_text_and_unchanged_task_do_not_create_milestone(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt="Explain the module")
    invoke(tmp_path, "PostToolUse", tool_response={"stdout": GOAL})
    assert invoke(tmp_path, "Stop").get("decision") != "block"
    invoke(tmp_path, "UserPromptSubmit", prompt=GOAL)
    assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_later_human_ui_task_and_generated_html_are_detected(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt="Explain the import format")
    invoke(tmp_path, "UserPromptSubmit", prompt="Build a complete customer dashboard with search and mobile navigation")
    (tmp_path / "server.mjs").write_text('res.end(`<html><main><button>Import customers</button></main></html>`)')
    invoke(tmp_path, "PostToolUse")
    assert invoke(tmp_path, "Stop").get("decision") == "block"

def test_feedback_without_url_in_original_goal_uses_real_browser_surface(tmp_path):
    setup(tmp_path, "Build a complete customer dashboard with search, import and mobile navigation")
    (tmp_path / "LOCAL_RUN.md").write_text("Use https://demo.test/dashboard for the local consumer.")
    export_tester(tmp_path, same_goal=True)
    export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop", same_goal=True)
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] == "accepted"

def test_existing_thread_bootstraps_goal_from_native_transcript(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    transcript = tmp_path / "existing.jsonl"
    transcript.write_text(json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": GOAL}]}}))
    invoke(tmp_path, "PreToolUse", transcript_path=str(transcript))
    (tmp_path / "dashboard.html").write_text("<main><button>Import</button></main>")
    invoke(tmp_path, "PostToolUse")
    assert invoke(tmp_path, "Stop").get("decision") == "block"

def test_exact_herder_card_captures_archive_outside_product_cwd(tmp_path):
    setup(tmp_path)
    manifests = [export_tester(tmp_path), export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop")]
    central = tmp_path.parent / (tmp_path.name + "-herder-process")
    central.mkdir()
    for manifest in manifests:
        data = json.loads(manifest.read_text())
        original = Path(data["target"]["path"])
        copied = central / original.name; shutil.move(original, copied)
        data["target"]["path"] = str(copied)
        moved = central / manifest.name; moved.write_text(json.dumps(data)); manifest.unlink()
        invoke(tmp_path, "PostToolUse", tool_name="mcp__agent_herder__export_transcript", tool_response={"content": [
            {"type": "text", "text": f"Transcript exported: {copied}\nLineage manifest: {moved}\nCompleteness: complete native source."}]})
    invoke(tmp_path, "PreCompact"); invoke(tmp_path, "SessionStart", source="compact")
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] == "accepted"
    assert len(state(tmp_path)["milestone"]["sources"]) == 2

def test_native_pass_verdict_does_not_need_a_magic_goal_phrase(tmp_path):
    setup(tmp_path)
    for sid, persona in (("one", "Maya, 29, new customer on mobile"), ("two", "Ivan, 61, accountant on desktop")):
        manifest = export_tester(tmp_path, sid, persona)
        data = json.loads(manifest.read_text())
        for file in (data["target"]["path"], data["target"]["source"]["location"]):
            p = Path(file); p.write_text(p.read_text().replace("Goal achieved.", "PASS: I imported a customer and found Maya through search."))
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] == "accepted"

def test_tool_failure_is_authoritative_for_due_clock_without_known_goal(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "PreToolUse")
    p = next((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    d = json.loads(p.read_text()); d["due_at"] = "2020-01-01T00:00:00+00:00"; p.write_text(json.dumps(d))
    invoke(tmp_path, "PostToolUse", tool_response={"exit_code": 1})
    assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_explicit_ui_acceptance_is_not_a_requirement_quoted_in_an_internal_task(tmp_path):
    setup(tmp_path, "Implement the native LHC defect fix.\nA UI task must not finish without milestone acceptance.")
    assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_test_html_fixtures_do_not_count_as_changed_product_surface(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt=GOAL)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_render.py").write_text('expected="<main><button>Import</button></main>"')
    invoke(tmp_path, "PostToolUse")
    assert invoke(tmp_path, "Stop").get("decision") != "block"

@pytest.mark.parametrize("report", [
    "Goal achieved. PASS. Positive: I liked the page heading. Negative: I had no complaints about the heading. Everything is verified and looks fine.",
    "PASS for search. My goal was import and search; I typed Maya and saw a match. Import was not tested; this is only a partial attempt. Positive: search helped. Negative: I never attempted the required import journey.",
])
def test_generic_or_partial_incidental_pass_is_not_goal_acceptance(tmp_path, report):
    setup(tmp_path)
    for sid, persona in (("one", "Maya, 29, new customer on mobile"), ("two", "Ivan, 61, accountant on desktop")):
        manifest = export_tester(tmp_path, sid, persona)
        data = json.loads(manifest.read_text())
        for file in (data["target"]["path"], data["target"]["source"]["location"]):
            p = Path(file); rows = [json.loads(line) for line in p.read_text().splitlines()]
            rows[-1]["payload"]["content"][0]["text"] = report
            p.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] != "accepted"

@pytest.mark.parametrize("fresh", [True, False])
def test_existing_herder_opencode_partial_export_is_checked_against_native_api(tmp_path, fresh):
    setup(tmp_path)
    responses = {}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = json.dumps(responses.get(self.path, {})).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
        def log_message(self, *_):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever); worker.start()
    try:
        for sid, persona in (("one", "Maya, 29, new customer on mobile"), ("two", "Ivan, 61, accountant on desktop")):
            manifest = export_tester(tmp_path, sid, persona)
            data = json.loads(manifest.read_text())
            codex = [json.loads(line) for line in Path(data["target"]["path"]).read_text().splitlines()]
            messages, calls = [], {}
            for row in codex:
                p = row["payload"]
                if p.get("type") == "message":
                    messages.append({"id": str(len(messages)), "sessionID": sid, "type": p["role"], "content": [{"type": "text", "text": p["content"][0]["text"]}]})
                elif p.get("type") == "function_call":
                    calls[p["call_id"]] = p
                elif p.get("type") == "function_call_output":
                    call = calls[p["call_id"]]
                    command = json.loads(call["arguments"])["cmd"]
                    messages.append({"id": str(len(messages)), "sessionID": sid, "type": "assistant", "content": [
                        {"type": "tool", "tool": "bash", "state": {"status": "completed", "input": {"command": command}, "output": p["output"]}}]})
            path = Path(data["target"]["path"]).with_suffix(".json"); path.write_text(json.dumps(messages))
            endpoint = f"/api/session/{sid}/message?limit=200"
            responses[endpoint] = messages
            created = datetime.now(timezone.utc) - (timedelta(days=1) if not fresh else timedelta())
            responses[f"/api/session/{sid}"] = {"id": sid, "location": {"directory": str(tmp_path)}, "time": {"created": created.timestamp()*1000}}
            data["target"].update(harness="opencode", path=str(path), complete=False, timestampCoverage="partial",
                source={"kind": "native-api", "location": f"http://127.0.0.1:{server.server_port}{endpoint}", "format": "json"})
            manifest.write_text(json.dumps(data))
        invoke(tmp_path, "Stop")
        assert state(tmp_path)["milestone"]["status"] == ("accepted" if fresh else "pending")
    finally:
        server.shutdown(); worker.join(); server.server_close()

def test_order_status_is_a_ui_goal_not_a_readonly_status_question(tmp_path):
    setup(tmp_path, "Build a complete UI dashboard with order status and import")
    assert invoke(tmp_path, "Stop").get("decision") == "block"

def test_new_small_task_after_accepted_major_does_not_recruit_new_group(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path)
    export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop")
    invoke(tmp_path, "Stop")
    assert state(tmp_path)["milestone"]["status"] == "accepted"
    invoke(tmp_path, "UserPromptSubmit", prompt="Fix a small padding issue in the dashboard")
    (tmp_path / "style.css").write_text("main { padding: 2px }")
    invoke(tmp_path, "PostToolUse")
    assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_exact_native_stop_reason_is_control_not_a_new_human_ui_assignment(tmp_path):
    setup(tmp_path)
    reason = invoke(tmp_path, "Stop")["reason"]
    before = state(tmp_path)
    invoke(tmp_path, "UserPromptSubmit", prompt=reason)
    after = state(tmp_path)
    for field in ("task", "goal", "surface_key", "changed_at"):
        assert after["milestone"][field] == before["milestone"][field]
    assert after["business"]["latest_prompt"] == GOAL
    assert invoke(tmp_path, "Stop", turn_id="native-continuation").get("decision") != "block"

@pytest.mark.parametrize("held", ["PermissionRequest", "Interrupt", "SessionEnd"])
def test_successful_tool_releases_permission_wait_but_not_manual_stop(tmp_path, held):
    setup(tmp_path)
    invoke(tmp_path, held)
    invoke(tmp_path, "PostToolUse", tool_response={"exit_code": 0})
    s = state(tmp_path)
    if held == "PermissionRequest":
        assert not s["milestone"].get("hold") and not s["native_entry"].get("finish_hold")
        assert invoke(tmp_path, "Stop").get("decision") == "block"
    else:
        assert s["milestone"]["hold"] == s["native_entry"]["finish_hold"] == held
        assert invoke(tmp_path, "Stop").get("decision") != "block"

def test_blocked_acceptance_explanation_overrides_incidental_technical_pass(tmp_path):
    setup(tmp_path)
    output = invoke(tmp_path, "Stop", last_assistant_message="Unit tests PASS. UI acceptance is blocked: login needs an authorized test identity; not-tested.")
    assert output.get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "blocked"

def test_confirmed_acceptance_survives_archive_unavailability_for_same_surface(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path)
    export_tester(tmp_path, "tester-two", "Ivan, 61, accountant on desktop")
    invoke(tmp_path, "Stop")
    shutil.rmtree(tmp_path / ".agent-herder")
    invoke(tmp_path, "SessionStart")
    assert invoke(tmp_path, "Stop").get("decision") != "block"
    assert state(tmp_path)["milestone"]["status"] == "accepted"


def test_assigned_browser_tunnel_and_batched_native_commands_are_real_attempts(tmp_path):
    setup(tmp_path)
    for sid, persona in [('tester-one','Maya, 29, customer on mobile'),('tester-two','Ivan, 61, desktop manager')]:
        manifest=export_tester(tmp_path,sid,persona)
        data=json.loads(manifest.read_text());target=data['target']
        rows=[json.loads(line) for line in Path(target['path']).read_text().splitlines()]
        prompt=rows[1]['payload']['content'][0]['text']
        rows[1]['payload']['content'][0]['text']=prompt+'\nAuthorized browser tunnel for the same product: http://127.0.0.1:29957/dashboard'
        for row in rows:
            p=row.get('payload',{})
            if p.get('type')=='function_call':
                args=json.loads(p['arguments']);command=args['cmd'];call=p['call_id']
                if call=='1':
                    # Navigation previously completed in the managed browser scope;
                    # read back actual URL and the before-state in one native command.
                    command=f'agent-browser --session {sid} get url; agent-browser --session {sid} snapshot'
                args['cmd']="ssh -o BatchMode=yes tester@browser 'mkdir -p .tmp && "+command+"'"
                p['arguments']=json.dumps(args)
            if p.get('type')=='function_call_output' and p.get('call_id')=='1':
                p['output']='http://127.0.0.1:29957/dashboard\n- heading "Customers"\n- textbox "Search"\n- button "Import"'
        raw='\n'.join(json.dumps(row) for row in rows)+'\n'
        Path(target['path']).write_text(raw);Path(target['source']['location']).write_text(raw)
    invoke(tmp_path,'Stop')
    assert state(tmp_path)['milestone']['status']=='accepted'


def test_quoted_browser_command_is_not_an_executed_user_attempt(tmp_path):
    setup(tmp_path)
    for sid,persona in [('tester-one','Maya, 29, mobile'),('tester-two','Ivan, 61, desktop')]:
        manifest=export_tester(tmp_path,sid,persona)
        data=json.loads(manifest.read_text());target=data['target']
        rows=[json.loads(line) for line in Path(target['path']).read_text().splitlines()]
        for row in rows:
            p=row.get('payload',{})
            if p.get('type')=='function_call':
                command=json.loads(p['arguments'])['cmd']
                p['arguments']=json.dumps({'cmd':"printf '%s' "+__import__('shlex').quote(command)})
        raw='\n'.join(json.dumps(row) for row in rows)+'\n'
        Path(target['path']).write_text(raw);Path(target['source']['location']).write_text(raw)
    invoke(tmp_path,'Stop')
    assert state(tmp_path)['milestone']['status']=='pending'


def test_candid_no_defects_and_scope_limitations_count_as_critical_feedback(tmp_path):
    setup(tmp_path)
    for sid,persona in [('tester-one','Maya, 29, mobile'),('tester-two','Ivan, 61, desktop')]:
        manifest=export_tester(tmp_path,sid,persona)
        data=json.loads(manifest.read_text());target=data['target']
        raw=Path(target['path']).read_text().replace('Negative: the search label confused me at first.',
            'Limitations: no product defects observed in my assigned desktop scenario; other devices are outside this persona.')
        Path(target['path']).write_text(raw);Path(target['source']['location']).write_text(raw)
    invoke(tmp_path,'Stop')
    assert state(tmp_path)['milestone']['status']=='accepted'


def test_explicit_personas_win_over_russian_word_endings_in_shared_assignment(tmp_path):
    setup(tmp_path)
    for sid,persona in [('tester-one','Maya, 29, mobile'),('tester-two','Ivan, 61, desktop')]:
        manifest=export_tester(tmp_path,sid,persona)
        data=json.loads(manifest.read_text());target=data['target']
        rows=[json.loads(line) for line in Path(target['path']).read_text().splitlines()]
        rows[1]['payload']['content'][0]['text']='Все аккаунты вымышленные. Не меняй данные пользователей.\n'+rows[1]['payload']['content'][0]['text']
        raw='\n'.join(json.dumps(row) for row in rows)+'\n'
        Path(target['path']).write_text(raw);Path(target['source']['location']).write_text(raw)
    invoke(tmp_path,'Stop')
    m=state(tmp_path)['milestone']
    assert m['status']=='accepted'
    assert len({v['persona'] for v in m['feedback']})==2


def test_reentry_reads_existing_genuine_feedback_before_requesting_duplicate_testers(tmp_path):
    setup(tmp_path)
    export_tester(tmp_path)
    export_tester(tmp_path,'tester-two','Ivan, 61, desktop manager')
    invoke(tmp_path,'SessionStart')
    assert state(tmp_path)['milestone']['status']=='accepted'
