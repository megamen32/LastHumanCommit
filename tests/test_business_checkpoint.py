"""Behavioral regressions for compulsory original-goal reviews, not file-count checks."""
import argparse
import importlib.util
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("business_guard_test", ROOT/"src/common/tools/lhc_time_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
START = datetime(2026,10,17,tzinfo=timezone.utc)

@pytest.fixture
def clock(tmp_path, monkeypatch):
    subprocess.run(["git","init","-q",str(tmp_path)],check=True)
    moment = [0]
    monkeypatch.setattr(guard,"business_clock_sample",lambda: {
        "monotonic_ns":(100000+moment[0])*10**9,
        "wall_ns":int((START+timedelta(seconds=moment[0])).timestamp())*10**9,
        "boot":{"id":"fixture-boot","source":"test","limitations":[]},
    })
    return moment

def tick(root, clock, seconds, event="PostToolUse", runtime="codex", session="lead", prompt=None):
    clock[0]=seconds
    args=argparse.Namespace(runtime=runtime,event=event,now=START+timedelta(seconds=seconds))
    guard.learning_checkpoint(args,root,session)
    payload={"session_id":session,"cwd":str(root)}
    if prompt is not None:payload["prompt"]=prompt
    return guard.business_checkpoint(args,root,session,payload)

def ack(root, seconds, review_id, **overrides):
    args=argparse.Namespace(runtime="codex",session_id="lead",cwd=root,now=START+timedelta(seconds=seconds),
        review_id=review_id,source_ref=["original request DEV-07; latest user correction"],
        business_result="Manager can inspect objections in existing conversations",
        scope_decision="Drop invented analytics expansion; deliver DEV-07",
        next_action="Verify the exact conversation link",
        zk_session="codex:independent-reader",zk_result="Conversation link opens another customer",
        zk_evidence="readonly-check/run1.json",zk_unavailable=None)
    vars(args).update(overrides)
    return guard.business_checkpoint(args,root,"lead",{},acknowledge=True)

def test_no_card_hourly_is_due_and_notification_is_not_completion(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Show scenarios and objections")
    assert not tick(tmp_path,clock,3599)["due"]
    due=tick(tmp_path,clock,3600)
    assert due["due"] and "Zero Knowledge" in due["prompt"]
    assert "original" in due["prompt"].lower()
    again=tick(tmp_path,clock,3601)
    assert again["due"] and again["review_id"]==due["review_id"]
    assert not again["prompt"], "Pending obligation stays due without per-tool spam"
    ack(tmp_path,3601,due["review_id"])
    assert not tick(tmp_path,clock,3602)["due"]
    assert tick(tmp_path,clock,7201)["due"]

def test_prompt_refresh_does_not_repeat_the_same_pending_feedback(tmp_path,clock):
    prompt="Original customer task"
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt=prompt)
    first=tick(tmp_path,clock,3600,"PostToolUse")
    assert first["prompt"] and first["review_id"]=="business-1"
    repeated=tick(tmp_path,clock,3601,"UserPromptSubmit",prompt=prompt)
    assert repeated["due"] and repeated["review_id"]==first["review_id"]
    assert not repeated["prompt"]

def test_hourly_reminder_uses_clean_scope_but_preserves_raw_coordination_source(tmp_path,clock):
    board='<agent-herder-coordination board="active">\n- [working] status\n</agent-herder-coordination>'
    raw=board+"\nOriginal customer task"
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt=raw)
    due=tick(tmp_path,clock,3600)
    saved=json.loads(Path(due["state"]).read_text())["business"]
    assert saved["original_prompt"]==raw
    assert saved["execution_context"]["direct_user_messages"][-1]["prompt"]==raw
    assert "Original customer task" in due["prompt"]
    assert "<agent-herder-coordination" not in due["prompt"]

def test_long_coordination_prefix_hourly_reminder_uses_full_task_scope(tmp_path,clock):
    prefix = '<agent-herder-coordination board="active">\n' + ("coordination filler " * 300)
    task = "Fix the small total CLI. Verify the empty basket returns 0."
    prompt = prefix + "\n</agent-herder-coordination>\n" + task
    assert prompt.index("</agent-herder-coordination>") > 4096
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt=prompt)
    due = tick(tmp_path,clock,3600)
    assert due["due"]
    assert task in due["prompt"]
    assert "<agent-herder-coordination" not in due["prompt"]
    assert "</agent-herder-coordination>" not in due["prompt"]

def test_pause_does_not_count_idle_or_wake_a_session(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    tick(tmp_path,clock,1800,"Stop")
    assert not tick(tmp_path,clock,10000,"UserPromptSubmit")["due"]
    due=tick(tmp_path,clock,11800)
    assert due["due"] and due["active_seconds"]==3600

def test_compaction_and_new_cards_keep_original_goal_and_clock(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Original customer goal")
    tick(tmp_path,clock,1000,"PostCompact")
    (tmp_path/".agents/tasks").mkdir(parents=True,exist_ok=True)
    (tmp_path/".agents/tasks/work-new.md").write_text("Invented expansion")
    tick(tmp_path,clock,2000,"UserPromptSubmit",prompt="Latest correction: use the existing report")
    due=tick(tmp_path,clock,3600)
    state=json.loads(Path(due["state"]).read_text())["business"]
    assert state["original_prompt"]=="Original customer goal"
    assert state["latest_prompt"]=="Latest correction: use the existing report"
    assert due["due"]

def test_ack_requires_source_and_cannot_claim_milestone_acceptance(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    due=tick(tmp_path,clock,3600)
    with pytest.raises(ValueError):ack(tmp_path,3601,due["review_id"],source_ref=[])
    with pytest.raises(ValueError):ack(tmp_path,3601,due["review_id"],zk_evidence=" ")
    with pytest.raises(ValueError):ack(tmp_path,3601,"wrong-review")
    partial=ack(tmp_path,3601,due["review_id"],zk_session=None,zk_result=None,zk_evidence=None,zk_unavailable="Native subagents unavailable")
    assert not partial["due"]
    state=json.loads(Path(due["state"]).read_text())["business"]
    assert state["last_review"]["status"]=="direction_reviewed"
    assert state["last_review"]["milestone_acceptance"]=="not_evaluated"

def test_runtime_without_full_lifecycle_uses_honest_wall_fallback(tmp_path,clock):
    tick(tmp_path,clock,0,"chat.message",runtime="hermes")
    due=tick(tmp_path,clock,3600,"chat.message",runtime="hermes")
    assert due["due"] and due["active_seconds"] is None
    assert "wall" in due["clock_source"]

def test_unchanged_review_cannot_silently_accept_scope_expansion(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    due=tick(tmp_path,clock,3600)
    text=due["prompt"]
    assert "SHA" in text and "user" in text.lower()
    assert "continue" in text.lower() and "reduce" in text.lower()


def test_decision_receipt_is_not_action_or_delivery_and_repeat_changes_next_step(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Deliver the report")
    due=tick(tmp_path,clock,3600)
    first=ack(tmp_path,3601,due["review_id"],zk_session=None,zk_result=None,zk_evidence=None,zk_unavailable="not needed")
    path=Path(first["state"])
    review=json.loads(path.read_text())["business"]["last_review"]
    assert review["action_status"]=="decision-only"
    assert "delivery" not in review
    due=tick(tmp_path,clock,7201)
    second=ack(tmp_path,7202,due["review_id"],zk_session=None,zk_result=None,zk_evidence=None,zk_unavailable="not needed")
    review=json.loads(path.read_text())["business"]["last_review"]
    assert review["repeated_review_without_action"] is True
    assert "do not repeat" in review["next_action"]


def test_unrelated_native_tool_receipt_does_not_execute_chosen_action(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Deliver the report")
    state=guard.load_state(guard.learning_path(tmp_path,"codex","lead"))
    state["business"]["last_review"]={"status":"direction_reviewed","next_action":"Deploy demo",
                                     "action_status":"decision-only","action_evidence_count":0}
    guard.write_state(guard.learning_path(tmp_path,"codex","lead"),state)
    clock[0]=10
    args=argparse.Namespace(runtime="codex",event="PostToolUse",now=START+timedelta(seconds=10))
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"call-1",
        "tool_input":{"cmd":"git status --short","workdir":"/project/deploy-demo"},
        "tool_response":{"exit_code":0,"stdout":"deployed"}},acknowledge=False)
    clock[0]=11; args.now=START+timedelta(seconds=11)
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"call-echo",
        "tool_input":{"cmd":"echo 'deploy demo'","workdir":"/project"},
        "tool_response":{"exit_code":0,"stdout":"deploy demo"}},acknowledge=False)
    clock[0]=12; args.now=START+timedelta(seconds=12)
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"call-print",
        "tool_input":{"cmd":"python3 -c 'print(\"deploy demo\")'","cwd":"/project/deploy-demo"},
        "tool_response":{"exit_code":0,"stdout":"deploy demo"}},acknowledge=False)
    business=guard.load_state(guard.learning_path(tmp_path,"codex","lead"))["business"]
    assert [row["source"] for row in business["tool_observations"][-3:]]==[
        "native-tool:lead:call-1", "native-tool:lead:call-echo", "native-tool:lead:call-print"]
    assert all(row["relation"]=="unrelated" for row in business["tool_observations"][-3:])
    assert not business.get("action_evidence")
    assert business["last_review"]["action_status"]=="decision-only"
    assert "delivery" not in business["last_review"]


def test_relevant_deploy_tool_receipt_is_action_result_not_delivery(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Deliver the report")
    path=guard.learning_path(tmp_path,"codex","lead")
    state=guard.load_state(path)
    state["business"]["last_review"]={"status":"direction_reviewed","next_action":"Deploy demo with ship.py",
                                     "action_status":"decision-only","action_evidence_count":0}
    guard.write_state(path,state)
    clock[0]=10
    args=argparse.Namespace(runtime="codex",event="PostToolUse",now=START+timedelta(seconds=10))
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"call-deploy",
        "tool_input":{"cmd":"python ship.py deploy --demo"},
        "tool_response":{"exit_code":0}},acknowledge=False)
    business=guard.load_state(path)["business"]
    assert business["action_evidence"][-1]["relation"]=="relevant"
    assert business["last_review"]["action_status"]=="action-result-observed"
    assert "delivery" not in business["last_review"]
    assert business["action_evidence_sequence"]==1


def test_action_after_direction_review_prevents_false_same_action_loop(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Deliver the demo")
    due=tick(tmp_path,clock,3600)
    ack(tmp_path,3601,due["review_id"],next_action="Deploy demo with ship.py",
        zk_session=None,zk_result=None,zk_evidence=None,zk_unavailable="not needed")
    clock[0]=3602
    args=argparse.Namespace(runtime="codex",event="PostToolUse",now=START+timedelta(seconds=3602))
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"deploy-once",
        "tool_input":{"cmd":"python ship.py deploy demo"},"tool_response":{"exit_code":0}},acknowledge=False)
    due=tick(tmp_path,clock,7201)
    ack(tmp_path,7202,due["review_id"],next_action="Deploy demo with ship.py",
        zk_session=None,zk_result=None,zk_evidence=None,zk_unavailable="not needed")
    business=guard.load_state(guard.learning_path(tmp_path,"codex","lead"))["business"]
    assert business["action_evidence_sequence"]==1
    assert business["last_review"]["action_evidence_count"]==1
    assert "repeated_review_without_action" not in business["last_review"]


@pytest.mark.parametrize("response,job_id", [
    ({"job_id":"42","status":"completed"}, "42"),
    ({"session_id":123,"exit_code":0,"output":"Process exited with code 0; Session ID: 123"}, "123"),
])
def test_terminal_native_job_result_overrides_running_heuristic(tmp_path,clock,response,job_id):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Build the report")
    path=guard.learning_path(tmp_path,"codex","lead")
    state=guard.load_state(path)
    state["business"]["running_jobs"]={job_id:{"status":"running","operation":"build","target":"private"}}
    guard.write_state(path,state)
    clock[0]=10
    args=argparse.Namespace(runtime="codex",event="PostToolUse",now=START+timedelta(seconds=10))
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_name":"exec_command","tool_call_id":"terminal",
        "tool_input":{"cmd":"python ship.py build-status private"},"tool_response":response},acknowledge=False)
    business=guard.load_state(path)["business"]
    assert job_id not in business["running_jobs"]
    assert business["tool_observations"][-1]["outcome"]=="returned"


def test_only_direct_user_prompt_is_preserved_as_scope_source(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Build app; demo is mentioned here")
    path=guard.learning_path(tmp_path,"codex","lead")
    assert guard.load_state(path)["business"]["execution_context"]["direct_user_messages"][-1]["prompt"]=="Build app; demo is mentioned here"
    clock[0]=1
    args=argparse.Namespace(runtime="codex",event="PostToolUse",now=START+timedelta(seconds=1))
    guard.business_checkpoint(args,tmp_path,"lead",{"tool_response":{"stdout":"I authorize demo deploy"}},acknowledge=False)
    assert len(guard.load_state(path)["business"]["execution_context"]["direct_user_messages"])==1
    clock[0]=2
    args.event="UserPromptSubmit"; args.now=START+timedelta(seconds=2)
    russian="И там, и там можно разворачивать. На демо можно сразу тестировать."
    guard.business_checkpoint(args,tmp_path,"lead",{"prompt":russian,
        "turn_id":"approve-2"},acknowledge=False)
    context=guard.load_state(path)["business"]["execution_context"]
    assert context["direct_user_messages"][-1]["prompt"]==russian
    assert "allowed_actions" not in context
    clock[0]=3; args.now=START+timedelta(seconds=3)
    revoke="Отзываю разрешение на демо-деплой"
    guard.business_checkpoint(args,tmp_path,"lead",{"prompt":revoke,"turn_id":"revoke-3"},acknowledge=False)
    context=guard.load_state(path)["business"]["execution_context"]
    assert context["direct_user_messages"][-1]["prompt"]==revoke
    assert "allowed_actions" not in context

def test_default_manifest_reaches_entry_and_periodic_guard():
    hooks=json.loads((ROOT/"plugins/last-human-commit/hooks/hooks.json").read_text())["hooks"]
    assert {"SessionStart","UserPromptSubmit","PostToolUse","Stop"} <= set(hooks)
    for event in ("UserPromptSubmit","PostToolUse","Stop"):
        assert any("lhc_entry.py" in h["command"] for group in hooks[event] for h in group["hooks"])

def test_blind_review_is_not_fed_the_implementers_answer():
    method=(ROOT/"src/common/protocols/BUSINESS_CHECKPOINT.md").read_text()
    for term in ("original", "Zero Knowledge", "~3 hours", "decision", "Direction check is not acceptance"):
        assert term in method
    assert "SHA" in method and "not" in method


def test_native_hook_executes_hourly_and_learning_without_task_card(tmp_path):
    subprocess.run(["git","init","-q",str(tmp_path)],check=True)
    package=ROOT/"plugins/last-human-commit"
    entry=package/"tools/lhc_entry.py"
    payload={"cwd":str(tmp_path),"session_id":"native-cli","prompt":"Use existing report"}
    def run(event):
        result=subprocess.run([sys.executable,str(entry),"--event",event,"--runtime","codex"],
            input=json.dumps(payload),capture_output=True,text=True,check=True)
        return result.stdout
    run("UserPromptSubmit")
    state_path=next((tmp_path/".agents/shared-session/learning").glob("*.json"))
    state=json.loads(state_path.read_text())
    state["business"]["interval"]["active_ns"]=3600*10**9
    state["due_at"]="2020-01-01T00:00:00+00:00"
    state_path.write_text(json.dumps(state))
    out=run("PostToolUse")
    context=json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "Zero Knowledge" in context and "improve-workflow" in context
    assert not (tmp_path/".agents/tasks").exists()
    assert "business-1" in context
    state=json.loads(state_path.read_text())
    assert state["business"]["last_review"] is None
    assert state["last_checkpoint"] is None


def test_native_reconnect_retains_completed_work_and_discards_unknown_gap(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    tick(tmp_path,clock,1800)
    reconnect=tick(tmp_path,clock,10000,"SessionStart")
    assert reconnect["active_seconds"]==1800 and not reconnect["due"]
    tick(tmp_path,clock,10001,"UserPromptSubmit")
    assert tick(tmp_path,clock,11801)["due"]


def test_opencode_permission_reply_resumes_long_tool_time(tmp_path,clock):
    tick(tmp_path,clock,0,"chat.message",runtime="opencode")
    tick(tmp_path,clock,10,"permission.asked",runtime="opencode")
    tick(tmp_path,clock,20,"permission.replied",runtime="opencode")
    due=tick(tmp_path,clock,3620,"tool.execute.after",runtime="opencode")
    assert due["active_seconds"]==3610 and due["due"]
    assert "Zero Knowledge" in due["prompt"]


def test_opencode_before_tool_does_not_consume_an_undelivered_prompt(tmp_path,clock):
    tick(tmp_path,clock,0,"chat.message",runtime="opencode")
    before=tick(tmp_path,clock,3600,"tool.execute.before",runtime="opencode")
    assert before["due"] and not before["prompt"]
    after=tick(tmp_path,clock,3601,"tool.execute.after",runtime="opencode")
    assert "Zero Knowledge" in after["prompt"]


def test_opencode_compaction_delivers_business_reminder_in_consumed_handoff(tmp_path,clock,monkeypatch):
    import io
    raw_scope="И там, и там можно разворачивать. На демо можно сразу тестировать."
    tick(tmp_path,clock,0,"chat.message",runtime="opencode",prompt=raw_scope)
    clock[0]=3600
    monkeypatch.setattr(sys,"stdin",io.StringIO(json.dumps({"cwd":str(tmp_path),"sessionID":"lead"})))
    args=argparse.Namespace(runtime="opencode",event="PreCompact",now=START+timedelta(seconds=3600),idle_cap_seconds=300)
    result=guard.hook(args)
    assert "Zero Knowledge" in result["handoff"]
    assert raw_scope in result["handoff"]


def test_hourly_direction_review_does_not_require_a_blind_tester(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit",prompt="Make report usable for a manager")
    due=tick(tmp_path,clock,3600)
    result=ack(tmp_path,3601,due["review_id"],zk_session=None,zk_result=None,zk_evidence=None)
    assert not result["due"]
    review=json.loads(Path(result["state"]).read_text())["business"]["last_review"]
    assert review["status"]=="direction_reviewed"
    assert review["milestone_acceptance"]=="not_evaluated"
    assert not tick(tmp_path,clock,3602)["due"]
    assert tick(tmp_path,clock,7201)["due"], "The hourly direction clock must remain active"


def test_unavailable_milestone_tester_does_not_block_hourly_direction(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    due=tick(tmp_path,clock,3600)
    result=ack(tmp_path,3601,due["review_id"],zk_session=None,zk_result=None,zk_evidence=None,
               zk_unavailable="Milestone is not ready; no blind test was run")
    assert not result["due"]
    review=json.loads(Path(result["state"]).read_text())["business"]["last_review"]
    assert review["zk_unavailable"]=="Milestone is not ready; no blind test was run"
    assert review["milestone_acceptance"]=="not_evaluated"


def test_real_cli_records_direction_without_zk_flags(tmp_path):
    subprocess.run(["git","init","-q",str(tmp_path)],check=True)
    tool=ROOT/"src/common/tools/lhc_time_guard.py"
    payload={"cwd":str(tmp_path),"session_id":"native-direction","prompt":"Open the actual report"}
    def cli(*arguments, data=None):
        result=subprocess.run([sys.executable,str(tool),*map(str,arguments)],
            input=json.dumps(data) if data is not None else None,
            capture_output=True,text=True,check=True,timeout=10)
        return json.loads(result.stdout) if result.stdout.strip() else None
    cli("hook","--runtime","codex","--event","UserPromptSubmit",data=payload)
    path=next((tmp_path/".agents/shared-session/learning").glob("*.json"))
    state=json.loads(path.read_text())
    state["business"]["interval"]["active_ns"]=3600*10**9  # controlled test clock, not a live-time claim
    path.write_text(json.dumps(state))
    cli("hook","--runtime","codex","--event","PostToolUse",data=payload)
    identity=json.loads(path.read_text())["business"]["pending"]["id"]
    result=cli("business-review","--runtime","codex","--cwd",tmp_path,
        "--session-id","native-direction","--review-id",identity,
        "--source-ref","original request","--business-result","Report opens but filtering remains",
        "--scope-decision","Keep the existing report","--next-action","Implement its filter")
    assert result["due"] is False
    review=json.loads(path.read_text())["business"]["last_review"]
    assert review["status"]=="direction_reviewed"
    assert review["milestone_acceptance"]=="not_evaluated"
    assert "zk_session" not in review


def test_optional_old_verifier_fields_require_a_complete_honest_observation(tmp_path,clock):
    tick(tmp_path,clock,0,"UserPromptSubmit")
    due=tick(tmp_path,clock,3600)
    with pytest.raises(ValueError):
        ack(tmp_path,3601,due["review_id"],zk_result=None)
    with pytest.raises(ValueError):
        ack(tmp_path,3601,due["review_id"],zk_unavailable="Unavailable")
    result=ack(tmp_path,3601,due["review_id"])
    review=json.loads(Path(result["state"]).read_text())["business"]["last_review"]
    assert review["zk_evidence"]=="readonly-check/run1.json"
    assert review["milestone_acceptance"]=="not_evaluated"
