"""Regression: automatic native lifecycle, not mere reading of a skill file."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta
import pytest

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/"src/common/tools/lhc_entry.py"

@pytest.fixture(autouse=True)
def isolated_git_root(tmp_path):
    subprocess.run(["git","init","-q",str(tmp_path)],check=True)

def invoke(root,event,**fields):
    payload={"cwd":str(root),"session_id":"existing-thread","turn_id":"turn-one",**fields}
    result=subprocess.run([sys.executable,str(ENTRY),"--root",str(ROOT),"--runtime","codex","--event",event],
        input=json.dumps(payload),capture_output=True,text=True,check=True,timeout=8)
    return json.loads(result.stdout) if result.stdout.strip() else {}

def state_file(root):return next((root/".agents/shared-session/learning").glob("*.json"))
def due(root):
    p=state_file(root);d=json.loads(p.read_text())
    d["business"]["interval"]["active_ns"]=3600*10**9
    d["due_at"]="2020-01-01T00:00:00+00:00"
    p.write_text(json.dumps(d))
def context(output):return output.get("hookSpecificOutput",{}).get("additionalContext","")

def test_existing_thread_bootstraps_on_first_tool_without_sessionstart(tmp_path):
    text=context(invoke(tmp_path,"PreToolUse",tool_name="exec_command",tool_input={"cmd":"true"}))
    assert str(ROOT/"AGENTS.md") in text
    assert "RED" in text and "80%" in text and "consumer result" in text
    assert not context(invoke(tmp_path,"PostToolUse")), "do not repeat the entry on every tool"

def test_plain_prompt_gets_outcome_design_tdd_and_milestone_contract(tmp_path):
    text=context(invoke(tmp_path,"UserPromptSubmit",prompt="поправь отображение пустого отчёта"))
    for term in ("before", "after", "RED", "GREEN", "80%", "milestone"):
        assert term in text

def test_unchanged_in_progress_outcome_feedback_is_not_repeated_on_each_prompt(tmp_path):
    prompt="Fix the small total CLI. Verify the empty basket returns 0."
    first=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "LHC outcome: quickfix" in first
    second=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "LHC outcome:" not in second
    assert "Original input" not in second
    assert second == ""

def test_rejection_and_contract_acceptance_each_refresh_notice_once(tmp_path):
    prompt="Fix the small total CLI. Verify the empty basket returns 0."
    first=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "LHC outcome: quickfix" in first
    tool=str(ROOT/"src/common/tools/lhc_outcome.py")
    command=f"python3 {tool} --cwd {tmp_path} --runtime codex --session-id existing-thread contract --scenario Empty --target FEEDBACK.md --expected zero"
    error="LHC outcome: research file target must name the scoped in-project source, not the requested report output"
    rejected_tool=context(invoke(tmp_path,"PostToolUse",tool_name="exec_command",tool_input={"cmd":command},
                                 tool_response={"exit_code":1,"stderr":error}))
    assert error in rejected_tool
    invoke(tmp_path,"PostToolUse",tool_name="exec_command",tool_input={"cmd":command},
           tool_response={"status":"completed","stdout":"finished"})
    rejected=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert error not in rejected
    unchanged=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "LHC outcome: quickfix" not in unchanged
    assert "Contract rejection (exact)" not in unchanged
    contract=subprocess.run([sys.executable,str(ROOT/"src/common/tools/lhc_outcome.py"),
        "--cwd",str(tmp_path),"--runtime","codex","--session-id","existing-thread","contract",
        "--scenario","Empty basket total","--target","python3 total.py","--expected","0",
        "--owned-path","total.py"],capture_output=True,text=True,check=True)
    accepted=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "Contract confirmed" in accepted and "Next stage: technical" in accepted
    assert error not in accepted and "contract --help" not in accepted
    after_acceptance=context(invoke(tmp_path,"UserPromptSubmit",prompt=prompt))
    assert "LHC outcome: quickfix" not in after_acceptance

def test_compaction_rehydrates_original_correction_and_keeps_clock_running(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Original report must open for the manager")
    invoke(tmp_path,"UserPromptSubmit",prompt="Correction: preserve the CSV export")
    invoke(tmp_path,"PreCompact")
    compact=invoke(tmp_path,"PostCompact")
    assert "hookSpecificOutput" not in compact, "Codex ignores compact additionalContext"
    restored=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert "Original report must open" in restored and "preserve the CSV export" in restored
    assert json.loads(state_file(tmp_path).read_text())["business"]["interval"]["status"]=="running"

def test_rehydration_keeps_raw_coordination_source_out_of_task_instructions(tmp_path):
    board='<agent-herder-coordination board="active">\n- [working] status\n</agent-herder-coordination>'
    prompt=board+"\nOriginal customer task"
    invoke(tmp_path,"UserPromptSubmit",prompt=prompt)
    restored=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert "Original customer task" in restored
    assert "<agent-herder-coordination" not in restored
    saved=json.loads(state_file(tmp_path).read_text())["business"]
    assert saved["original_prompt"]==prompt

def test_long_coordination_prefix_is_removed_before_source_excerpt_truncation(tmp_path):
    prefix='<agent-herder-coordination board="active">\n'+("coordination filler "*260)
    board=prefix+"\n</agent-herder-coordination>\n"
    task="Fix the small total CLI. Verify the empty basket returns 0."
    prompt=board+task
    invoke(tmp_path,"UserPromptSubmit",prompt=prompt)
    saved=json.loads(state_file(tmp_path).read_text())["business"]
    assert saved["original_prompt"]==prompt[:4096]
    assert saved["original_prompt_full"]==prompt
    assert saved["original_scope_prompt"]==task
    assert saved["execution_context"]["direct_user_messages"][-1]["scope_prompt"]==task
    outcome=saved["outcome"]
    assert outcome["task_class"]=="quickfix"
    assert outcome["original_goal"]==prompt
    restored=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert task in restored
    assert "<agent-herder-coordination" not in restored

def test_compaction_does_not_consume_an_undelivered_due_reminder(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Original business task")
    due(tmp_path)
    invoke(tmp_path,"PreCompact"); invoke(tmp_path,"PostCompact")
    business=json.loads(state_file(tmp_path).read_text())["business"]
    assert not business.get("last_injected_at")
    text=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert "business-1" in text and "improve-workflow" in text and "Original business task" in text

def test_overdue_finish_continues_once_and_does_not_forge_acceptance(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Make the actual report usable")
    due(tmp_path)
    first=invoke(tmp_path,"Stop",stop_hook_active=False)
    assert first.get("decision")=="block"
    assert "business-review" in first["reason"] and "checkpoint" in first["reason"]
    assert invoke(tmp_path,"Stop",stop_hook_active=True).get("decision")!="block"
    assert invoke(tmp_path,"Stop",stop_hook_active=False).get("decision")!="block", "persist the loop bound"
    d=json.loads(state_file(tmp_path).read_text())
    assert d["business"]["pending"] and d["business"]["last_review"] is None and d["last_checkpoint"] is None

def test_stop_learning_checkpoint_wording_when_business_review_is_not_due(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Deliver the report")
    p=state_file(tmp_path);d=json.loads(p.read_text())
    d["due_at"]=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    d["business"]["pending"]=None
    d["business"]["wall_due_at"]=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    d["business"]["next_active_seconds"]=24*3600
    p.write_text(json.dumps(d))

    result=invoke(tmp_path,"Stop",stop_hook_active=False)
    reason=result.get("reason","")
    assert result.get("decision")=="block"
    assert "120-minute learning checkpoint" in reason.lower()
    assert "lhc_time_guard.py checkpoint" in reason
    assert "direction/method review" not in reason.lower()
    assert "business-review" not in reason

def test_repeated_stop_reblocks_only_for_changed_progress_or_due_identity(tmp_path):
    def start_case(name,prompt):
        root=tmp_path/name
        subprocess.run(["git","init","-q",str(root)],check=True)
        invoke(root,"UserPromptSubmit",session_id=name,turn_id=f"{name}-start",prompt=prompt)
        due(root)
        first=invoke(root,"Stop",session_id=name,turn_id=f"{name}-stop",stop_hook_active=False)
        assert first.get("decision")=="block"
        return root,name

    same_root,same_session=start_case("same-progress","Deliver the report")
    same_state_before=json.loads(state_file(same_root).read_text())
    repeated=invoke(same_root,"Stop",session_id=same_session,turn_id="new-turn-same-progress",stop_hook_active=False)
    same_state_after=json.loads(state_file(same_root).read_text())

    progress_root,progress_session=start_case("changed-progress","Implement the dashboard and verify the final page")
    p=state_file(progress_root);d=json.loads(p.read_text())
    d["business"]["outcome"]["latest_correction"]="Include CSV export in the accepted result"
    d["business"]["outcome"]["canary"]["expected"]+=" and include CSV export"
    p.write_text(json.dumps(d))
    changed_progress=invoke(progress_root,"Stop",session_id=progress_session,turn_id="changed-progress-stop",stop_hook_active=False)

    due_root,due_session=start_case("new-due-id","Deliver the report")
    p=state_file(due_root);d=json.loads(p.read_text())
    d["business"]["pending"]["id"]="business-2"
    p.write_text(json.dumps(d))
    changed_due=invoke(due_root,"Stop",session_id=due_session,turn_id="new-due-id-stop",stop_hook_active=False)

    assert changed_progress.get("decision")=="block", changed_progress
    assert changed_due.get("decision")=="block", changed_due
    assert repeated.get("decision")!="block", repeated
    assert "systemMessage" not in repeated, repeated
    assert same_state_after["business"]["pending"] == same_state_before["business"]["pending"]
    assert same_state_after["business"]["outcome"]["finish_verdict"] == "pending"

def test_explicit_interrupt_and_permission_wait_never_force_continuation(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Keep my original task")
    due(tmp_path)
    assert invoke(tmp_path,"Interrupt").get("decision")!="block"
    assert invoke(tmp_path,"PermissionRequest").get("decision")!="block"
    assert json.loads(state_file(tmp_path).read_text())["business"]["interval"]["status"]=="paused"

def test_due_review_uses_the_installed_absolute_tool_and_protocol_paths(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Use a report")
    due(tmp_path)
    text=context(invoke(tmp_path,"PostToolUse"))
    assert str(ROOT/"src/common/tools/lhc_time_guard.py") in text
    assert str(ROOT/"src/common/protocols/BUSINESS_CHECKPOINT.md") in text

def test_codex_global_bootstrap_has_no_frozen_cache_version(tmp_path):
    spec=importlib.util.spec_from_file_location("install_runtime",ROOT/"plugins/last-human-commit/scripts/install_runtime.py")
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    p=tmp_path/".codex/AGENTS.md";p.parent.mkdir()
    p.write_text("My unrelated rules\n<!-- lhc-autoentry:begin -->read cache/1.4.3/AGENTS.md<!-- lhc-autoentry:end -->\n")
    installer.configure(tmp_path,ROOT/"plugins/last-human-commit","codex",True)
    text=p.read_text()
    assert "My unrelated rules" in text
    assert "cache/1.4.3" not in text
    assert str(ROOT/"plugins/last-human-commit") not in text, "native hook owns current root, not a second pinned version"
    assert "native" in text.lower() and "RED" in text and "80%" in text


def test_large_native_tool_result_keeps_exact_session_clock(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Preserve the real user goal")
    due(tmp_path)
    text=context(invoke(tmp_path,"PostToolUse",tool_response={"stdout":"a"*180000}))
    assert "business-1" in text and "Preserve the real user goal" in text
    assert len(list((tmp_path/".agents/shared-session/learning").glob("*.json")))==1


def test_bad_native_input_is_reported_not_recorded_as_an_unknown_session(tmp_path):
    result=subprocess.run([sys.executable,str(ENTRY),"--root",str(ROOT),"--runtime","codex","--event","PostToolUse"],
        cwd=tmp_path,input='{"session_id":',capture_output=True,text=True,check=True)
    output=json.loads(result.stdout)
    assert "systemMessage" in output
    assert not (tmp_path/".agents/shared-session/learning").exists()


def test_rooting_reminders_never_rewrites_literal_user_goal(tmp_path):
    prompt="Review src/common/tools/lhc_time_guard.py without changing the application"
    invoke(tmp_path,"UserPromptSubmit",prompt=prompt)
    due(tmp_path)
    assert prompt in context(invoke(tmp_path,"PostToolUse"))


def test_rehydration_keeps_late_constraints_and_the_native_source_reference(tmp_path):
    prompt="Inspect the original report. "+("context "*180)+"NEVER_CHANGE_BILLING"
    transcript=str(tmp_path/"native-source.jsonl")
    invoke(tmp_path,"UserPromptSubmit",prompt=prompt,transcript_path=transcript)
    text=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert "NEVER_CHANGE_BILLING" in text and transcript in text


def test_finish_command_templates_are_real_parser_commands(tmp_path):
    import shlex
    invoke(tmp_path,"UserPromptSubmit",prompt="Deliver the report")
    due(tmp_path)
    text=invoke(tmp_path,"Stop")["reason"]
    commands=[line.strip() for line in text.splitlines() if line.startswith("python3 ")]
    assert len(commands)==2
    spec=importlib.util.spec_from_file_location("stop_parser_guard",ROOT/"src/common/tools/lhc_time_guard.py")
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    for command in commands:
        args=shlex.split(command)
        assert args[2] in ["business-review","checkpoint"]
        g.parser().parse_args(args[2:])


def test_concurrent_acknowledgement_prevents_a_stale_stop_decision(tmp_path,monkeypatch):
    invoke(tmp_path,"UserPromptSubmit",prompt="Deliver the report")
    due(tmp_path)
    spec=importlib.util.spec_from_file_location("race_guard",ROOT/"src/common/tools/lhc_time_guard.py")
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    real=g.business_checkpoint
    def acknowledged_after_snapshot(*args,**kwargs):
        old=real(*args,**kwargs)
        p=Path(old["state"]);d=json.loads(p.read_text())
        d["business"]["pending"]=None
        d["due_at"]=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
        p.write_text(json.dumps(d))
        return old
    monkeypatch.setattr(g,"business_checkpoint",acknowledged_after_snapshot)
    monkeypatch.setitem(sys.modules,"lhc_time_guard",g)
    spec=importlib.util.spec_from_file_location("race_entry",ENTRY)
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    output=e.handle({"cwd":str(tmp_path),"session_id":"existing-thread","turn_id":"turn-one"},"Stop","codex",ROOT)
    assert output.get("decision")!="block"


def test_opencode_native_global_entry_has_no_second_pinned_version(tmp_path):
    spec=importlib.util.spec_from_file_location("lhc_opencode_install",ROOT/"plugins/last-human-commit/scripts/install_runtime.py")
    installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    p=tmp_path/".config/opencode/AGENTS.md";p.parent.mkdir(parents=True)
    p.write_text("My personal preferences\n<!-- lhc-autoentry:begin -->old releases/1.4.4/AGENTS.md<!-- lhc-autoentry:end -->\n")
    installer.configure(tmp_path,ROOT/"plugins/last-human-commit","opencode",False)
    final=p.read_text()
    assert "My personal preferences" in final
    assert "releases/1.4.4" not in final
    assert "plugins/last-human-commit/AGENTS.md" not in final
    assert "native OpenCode" in final
    assert "review" in final.lower() and "Zero Knowledge" in final
