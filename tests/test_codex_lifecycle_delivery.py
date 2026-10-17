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
    assert "RED" in text and "80%" in text and "результат" in text
    assert not context(invoke(tmp_path,"PostToolUse")), "do not repeat the entry on every tool"

def test_plain_prompt_gets_outcome_design_tdd_and_milestone_contract(tmp_path):
    text=context(invoke(tmp_path,"UserPromptSubmit",prompt="поправь отображение пустого отчёта"))
    for term in ("раньше", "после", "RED", "GREEN", "80%", "milestone"):
        assert term in text

def test_compaction_rehydrates_original_correction_and_keeps_clock_running(tmp_path):
    invoke(tmp_path,"UserPromptSubmit",prompt="Original report must open for the manager")
    invoke(tmp_path,"UserPromptSubmit",prompt="Correction: preserve the CSV export")
    invoke(tmp_path,"PreCompact")
    compact=invoke(tmp_path,"PostCompact")
    assert "hookSpecificOutput" not in compact, "Codex ignores compact additionalContext"
    restored=context(invoke(tmp_path,"SessionStart",source="compact"))
    assert "Original report must open" in restored and "preserve the CSV export" in restored
    assert json.loads(state_file(tmp_path).read_text())["business"]["interval"]["status"]=="running"

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
