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
    # --session is the explicit agent command that advances the stateful
    # lifecycle. The native hook templates stay time-only and never block.
    result=subprocess.run([sys.executable,str(ENTRY),"--root",str(ROOT),"--runtime","codex","--event",event,"--session"],input=json.dumps(value),text=True,capture_output=True,check=True,timeout=8)
    data=json.loads(result.stdout) if result.stdout.strip() else {}
    return data, data.get("hookSpecificOutput",{}).get("additionalContext","")

def prepare(root):
    subprocess.run(["git","init","-q",str(root)],check=True)

def delivery_protocol():
    return (ROOT/"src/common/protocols/REVIEW_TO_DELIVERY.md").read_text()

def test_native_entry_distinguishes_receipt_error_from_material_change(tmp_path):
    prepare(tmp_path)
    result,text=invoke(tmp_path,"UserPromptSubmit",prompt="Tests passed; the reviewer typed a wrong SHA in its receipt. Deliver the fix.")
    # The delivered context points at the router and keeps the saved goal; the
    # delivery rule itself is written down once, in the protocol.
    assert str(ROOT/"AGENTS.md") in text
    assert "Deliver the fix." in text
    assert "decision" not in result
    protocol=delivery_protocol()
    assert "SHA typo, filename, JSON formatting" in protocol
    assert "No new LLM review, second JSON or receipt-review" in protocol
    assert "Real delta." in protocol and "Metadata error over known checked code." in protocol

def test_old_session_first_tool_gets_delivery_rule_without_new_gate(tmp_path):
    prepare(tmp_path)
    first,text=invoke(tmp_path,"PreToolUse",tool_name="exec_command",tool_input={"cmd":"git status --short"})
    assert str(ROOT/"AGENTS.md") in text
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
    assert "reviewed a receipt" in text and "user-available" in text
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
    for term in ("unknown", "PostgreSQL", "Zero Knowledge", "deployment", "Never bypass", "machine fields", "build a service"):
        assert term in text
    assert "git diff" in text

def test_source_only_requests_do_not_acquire_a_deployment_requirement():
    text=(ROOT/"src/common/protocols/REVIEW_TO_DELIVERY.md").read_text()
    assert "If installation was requested" in text
    assert "otherwise close within agreed boundaries" in text

def test_review_obligation_is_recorded_by_the_explicit_cli_not_by_a_hook():
    # The review loop is a CLI-driven ritual. The hook bundle may only point at
    # the method and track elapsed time, so it may never open the review
    # itself, and it may never advance the stateful lifecycle.
    hooks=json.loads((ROOT/"plugins/last-human-commit/hooks/hooks.json").read_text())["hooks"]
    assert set(hooks)=={"SessionStart","PostCompact","PostToolUse"}
    for group in hooks.values():
        for entry in group:
            command=entry["hooks"][0]["command"]
            assert "--instructions-only" in command or "--heartbeat-only" in command, command
            assert "--session" not in command, command
            assert "business-review" not in command, command
            assert "checkpoint" not in command, command
    # The review itself is recorded by the explicit time-guard CLI.
    guard=ROOT/"src/common/tools/lhc_time_guard.py"
    spec=importlib.util.spec_from_file_location("review_delivery_guard",guard)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    args=module.parser().parse_args(["business-review","--cwd",str(ROOT),"--runtime","codex",
        "--session-id","review-delivery-test","--review-id","business-1",
        "--source-ref","original request","--business-result","Report opens",
        "--scope-decision","Keep the report","--next-action","Implement the filter"])
    assert args.command=="business-review"
    assert args.review_id=="business-1"
    assert args.source_ref==["original request"]
