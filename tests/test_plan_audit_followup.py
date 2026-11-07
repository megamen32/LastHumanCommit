"""The plan audit cases use the ordinary editor, CLI and MCP facade."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
pj = load_module(TOOLS / "lhc_plan_json.py", name="lhc_plan_json_audit_test")
mcp = load_module(TOOLS / "lhc_plan_mcp.py", name="lhc_plan_mcp_audit_test")
RECON = {"recon": ["The editor serializes canonical plan mutations :: src/common/tools/lhc_plan_json.py",
                   "The facade invokes the canonical editor CLI :: src/common/tools/lhc_plan_mcp.py",
                   "The audit has regression cases for each reported failure :: tests/test_plan_audit_followup.py"],
         "acceptance_scenario": "Create, resume and hand off the same plan through the CLI."}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "no-mirror.json"))
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)


def plan(tmp_path, name="plan", **fields):
    path = tmp_path / name
    (path / "leaves").mkdir(parents=True)
    (path / "plan.json").write_text(json.dumps({"title": name, **RECON, **fields}))
    return path


def row(path, ident, **fields):
    value = {"id": ident, "label": ident, "status": "queued", "estimate_minutes": 15,
             "description": "A bounded change", "acceptance": "The stated behavior works", **fields}
    (path / "leaves" / f"{ident}.json").write_text(json.dumps(value))


def cli(*args):
    return subprocess.run([sys.executable, str(TOOLS / "lhc_plan_json.py"), *map(str, args)],
                          capture_output=True, text=True, env=os.environ.copy())


def test_scoped_cap_survives_restart_and_does_not_change_another_plan(tmp_path):
    path = plan(tmp_path)
    pj.update_plan(path, {"estimate_policy": {"leaf_cap_minutes": 60,
                                              "reason": "The owner requested leaves up to one hour."}})
    pj.update_leaf(path, "L01", {"label": "Hour", "estimate_minutes": 60}, create=True)
    restarted = cli("create-leaf", path, "L02", "--fields",
                    json.dumps({"label": "Another hour", "estimate_minutes": 60}))
    assert restarted.returncode == 0, restarted.stderr
    checked = cli("check", path)
    assert checked.returncode == 0, checked.stderr
    assert pj.LEAF_ESTIMATE_CAP_MINUTES == 15
    with pytest.raises(pj.LeafError):
        pj.update_leaf(path, "L03", {"label": "Too long", "estimate_minutes": 61,
                                    "estimate_over_limit_reason": "Still too long"}, create=True)
    other = plan(tmp_path, "other")
    with pytest.raises(pj.LeafError):
        pj.update_leaf(other, "L01", {"label": "Too long here", "estimate_minutes": 60}, create=True)


@pytest.mark.parametrize("cap", [True, 0, -1, 15.5, float("nan"), float("inf"), "60"])
def test_invalid_cap_is_rejected_without_writing(tmp_path, cap):
    path = plan(tmp_path)
    before = (path / "plan.json").read_bytes()
    with pytest.raises(pj.LeafError, match="estimate_policy"):
        pj.update_plan(path, {"estimate_policy": {"leaf_cap_minutes": cap, "reason": "Owner decision"}})
    assert (path / "plan.json").read_bytes() == before


@pytest.mark.parametrize("reason", [None, "", "   ", 7])
def test_cap_change_requires_a_recorded_reason(tmp_path, reason):
    path = plan(tmp_path)
    with pytest.raises(pj.LeafError, match="estimate_policy"):
        pj.update_plan(path, {"estimate_policy": {"leaf_cap_minutes": 60, "reason": reason}})


def test_changing_a_large_stage_to_a_task_cannot_bypass_the_cap(tmp_path):
    path = plan(tmp_path)
    pj.update_leaf(path, "M01", {"label": "Stage", "kind": "milestone", "estimate_minutes": 60}, create=True)
    with pytest.raises(pj.LeafError):
        pj.update_leaf(path, "M01", {"kind": "task"})
    assert json.loads((path / "leaves/M01.json").read_text())["kind"] == "milestone"


def test_completed_current_leaf_is_not_reported_as_now(tmp_path):
    path = plan(tmp_path)
    row(path, "L01", status="done", result="The change is verified")
    summary = "\n".join(pj.plan_summary(path, current=["L01"]))
    assert "Done:" in summary and "The change is verified" in summary
    assert "Now:" not in summary


def test_empty_stage_remains_visible_when_all_created_leaves_are_done(tmp_path):
    path = plan(tmp_path)
    row(path, "M01", kind="milestone")
    row(path, "L01", parent="M01", status="done")
    row(path, "M02", kind="milestone", depends_on=["M01"], estimate_minutes=180)
    state = pj.plan_state(path)
    assert "1/2 done" in state and "undecomposed stages: M02" in state
    assert "ready to start M02" not in state
    assert "M02" in "\n".join(pj.plan_summary(path))


def test_ready_state_expands_stage_dependencies(tmp_path):
    path = plan(tmp_path)
    row(path, "M01", kind="milestone")
    row(path, "L01", parent="M01", status="done")
    row(path, "L02", depends_on=["M01"])
    assert "ready to start L02" in pj.plan_state(path)


def test_plan_state_counts_beyond_the_display_limit(tmp_path):
    path = plan(tmp_path)
    for i in range(401):
        row(path, f"L{i:03}", status="done" if i < 400 else "queued")
    assert "400/401 done" in pj.plan_state(path)


def test_plan_intent_and_policy_survive_graph_projection_and_fallback(tmp_path):
    path = plan(tmp_path)
    policy = {"leaf_cap_minutes": 60, "reason": "Owner's one-hour limit"}
    evidence = {"checked_by": "lead", "edges_kept": []}
    pj.update_plan(path, {"deliverable": "plan", "decomposition": "complete",
                         "estimate_policy": policy, "decomposition_check": evidence})
    row(path, "L01")
    document = pj.build_document(path)
    assert document["deliverable"] == "plan" and document["decomposition"] == "complete"
    assert document["estimate_policy"] == policy and document["decomposition_check"] == evidence
    (path / "plan.graph.json").write_text(json.dumps(document))
    (path / "plan.json").unlink()
    assert pj.plan_metadata(path)["estimate_policy"] == policy
    assert pj.build_document(path)["deliverable"] == "plan"
    summary = "\n".join(pj.plan_summary(path))
    assert "deliverable: plan" in summary and "decomposition: complete" in summary


def test_structural_check_and_complete_handoff_are_different_claims(tmp_path):
    path = plan(tmp_path, deliverable="plan", decomposition="complete")
    row(path, "M01", kind="milestone")
    row(path, "L01", description="", acceptance="")
    structural = cli("check", path)
    assert structural.returncode == 0, structural.stderr
    handoff = cli("check", path, "--handoff")
    assert handoff.returncode == 1
    assert "M01" in handoff.stderr and "L01" in handoff.stderr
    assert "description" in handoff.stderr and "acceptance" in handoff.stderr
    row(path, "L01", parent="M01")
    handoff = cli("check", path, "--handoff")
    assert handoff.returncode == 0, handoff.stderr
    assert "deliverable: plan" in handoff.stdout and "complete" in handoff.stdout


def test_progressive_handoff_does_not_claim_a_complete_plan(tmp_path):
    path = plan(tmp_path)
    row(path, "L01")
    row(path, "M02", kind="milestone", estimate_minutes=180)
    result = cli("check", path, "--handoff")
    assert result.returncode == 0, result.stderr
    assert "progressive" in result.stdout and "M02" in result.stdout
    assert "complete handoff ready" not in result.stdout


@pytest.mark.parametrize("field,value", [("deliverable", "release"), ("decomposition", "all")])
def test_invalid_plan_intent_is_rejected(tmp_path, field, value):
    path = plan(tmp_path)
    with pytest.raises(pj.LeafError, match=field):
        pj.update_plan(path, {field: value})


def test_mcp_build_exposes_and_forwards_optional_handoff(tmp_path, monkeypatch):
    path = plan(tmp_path)
    seen = []
    def run(argv):
        seen.append(argv)
        return {"argv": argv, "returncode": 0, "stdout": "", "stderr": ""}
    monkeypatch.setattr(mcp, "run_cli", run)
    definition = next(tool for tool in mcp.TOOLS if tool["name"] == "build_plan")
    assert definition["inputSchema"]["properties"]["handoff"]["type"] == "boolean"
    for extra in ({}, {"report": "task.md"}):
        seen.clear()
        mcp.build_plan({"plan_dir": str(path), "handoff": True, **extra})
        assert any("--handoff" in argv for argv in seen)


def test_missing_activation_session_is_a_short_cli_error(tmp_path):
    path = plan(tmp_path)
    row(path, "L01")
    result = cli("activate", path, "L01")
    assert result.returncode == 1
    assert "--session" in result.stderr and "Traceback" not in result.stderr
    assert json.loads((path / "leaves/L01.json").read_text())["status"] == "queued"


def test_unexpected_activation_value_error_is_not_mislabelled_as_user_input(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("programming error")
    expected = type("ActivationError", (ValueError,), {})
    monkeypatch.setitem(sys.modules, "lhc_plan_mirror", SimpleNamespace(activate=broken, ActivationError=expected))
    with pytest.raises(ValueError, match="programming error"):
        pj.main(["activate", str(tmp_path), "L01", "--session", "real-session"])
