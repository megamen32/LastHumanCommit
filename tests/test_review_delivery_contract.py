"""Prompt delivery regression for review->metadata->review loops.

These verify the instructions actually delivered, not future model compliance.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/"src/common/tools/lhc_entry.py"

def invoke(root,event,**payload):
    value={"cwd":str(root),"session_id":"review-delivery-test",**payload}
    result=subprocess.run([sys.executable,str(ENTRY),"--root",str(ROOT),"--runtime","codex","--event",event],input=json.dumps(value),text=True,capture_output=True,check=True,timeout=8)
    data=json.loads(result.stdout) if result.stdout.strip() else {}
    return data, data.get("hookSpecificOutput",{}).get("additionalContext","")

def prepare(root):
    subprocess.run(["git","init","-q",str(root)],check=True)

def test_native_entry_distinguishes_receipt_error_from_material_change(tmp_path):
    prepare(tmp_path)
    result,text=invoke(tmp_path,"UserPromptSubmit",prompt="Tests passed; the reviewer typed a wrong SHA in its receipt. Deliver the fix.")
    assert "Ошибка в receipt" in text
    assert "не новое ревью" in text
    assert "изменении кода" in text
    assert "ближайший рабочий результат" in text
    assert "decision" not in result
    assert "RED" in text and "Zero Knowledge" in text

def test_old_session_first_tool_gets_delivery_rule_without_new_gate(tmp_path):
    prepare(tmp_path)
    first,text=invoke(tmp_path,"PreToolUse",tool_name="exec_command",tool_input={"cmd":"git status --short"})
    assert "Ошибка в receipt" in text
    assert first.get("decision")!="block"
    second,text=invoke(tmp_path,"PostToolUse")
    assert not text, "Do not start a per-tool ritual or rereview every tool result"
    assert second.get("decision")!="block"

def test_hourly_checkpoint_challenges_proof_rework_not_only_sha_count(tmp_path):
    prepare(tmp_path)
    invoke(tmp_path,"UserPromptSubmit",prompt="Restore usable accounts, not receipts")
    path=next((tmp_path/".agents/shared-session/learning").glob("*.json"))
    state=json.loads(path.read_text());state["business"]["interval"]["active_ns"]=3600*10**9
    path.write_text(json.dumps(state))
    _,text=invoke(tmp_path,"PostToolUse")
    assert "ревью справки" in text and "доступное пользователю" in text
    assert "business-1" in text
    state=json.loads(path.read_text())
    assert state["business"]["pending"] is not None
    assert state["business"]["last_review"] is None

def test_reviewer_has_no_second_receipt_or_hidden_test_pass():
    text=(ROOT/"src/common/agents/Reviewer.md").read_text()
    for term in ("native response is the review result", "not a second JSON receipt", "unexecuted", "metadata-only", "known reviewed source", "dependencies", "existing release gates"):
        assert term in text
    assert "material repairs" in text

def test_policy_preserves_business_testing_and_uncertainty():
    text=(ROOT/"src/common/protocols/REVIEW_TO_DELIVERY.md").read_text()
    for term in ("неизвестно", "PostgreSQL", "Zero Knowledge", "deployment", "не обходить", "Машин", "новый сервис"):
        assert term in text
    assert "git diff" in text

def test_source_only_requests_do_not_acquire_a_deployment_requirement():
    text=(ROOT/"src/common/protocols/REVIEW_TO_DELIVERY.md").read_text()
    assert "Если исходное поручение включает установку" in text
    assert "иначе заверши результат в согласованных границах" in text
