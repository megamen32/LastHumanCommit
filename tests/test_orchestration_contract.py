"""Static orchestration contract checks; installed tests prove runtime routing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_delegated_artifact_writer_routes_verified_plan_back_to_parent_lead():
    protocol = (ROOT / "src/common/protocols/ORCHESTRATION_RECORDS.md").read_text()
    router = (ROOT / "src/common/templates/project-router.md").read_text()
    adapter = (ROOT / "adapters/codex/templates/subagent.md").read_text()
    combined = "\n".join((protocol, router, adapter))

    for path in ("task.md", "progress.md", "plan.graph.json", "plan.html", "plan.md"):
        assert path in protocol
    assert "one named" in protocol and "Artifact Writer" in protocol
    assert "exclusive write ownership" in protocol
    assert "verified decisions" in protocol
    assert "parent_lead_identity" in protocol
    assert "parent_task_id/session/route" in protocol
    assert "returns" in protocol and "parent Lead" in protocol
    assert "write only their own" in protocol and "result.md" in protocol
    assert "context-mode" in protocol
    assert "Artifact Writer" in router and "verified decisions" in router
    assert "preserve that acceptance" in adapter


def test_writer_acceptance_requires_user_language_complete_readable_artifacts():
    protocol = (ROOT / "src/common/protocols/ORCHESTRATION_RECORDS.md").read_text()
    router = (ROOT / "src/common/templates/project-router.md").read_text()
    adapter = (ROOT / "adapters/codex/templates/subagent.md").read_text()
    combined = "\n".join((protocol, router, adapter))

    assert "human-facing plan" in combined
    assert "Russian when the user" in combined
    assert "user benefit" in combined
    assert "visible outcome" in combined
    assert "HTML and Markdown" in combined
    assert "readable" in combined
    assert "forward this acceptance" in combined


def test_internal_routing_has_no_global_zero_context_or_readability_rule():
    protocol = (ROOT / "src/common/protocols/ORCHESTRATION_RECORDS.md").read_text()
    router = (ROOT / "src/common/templates/project-router.md").read_text()
    adapter = (ROOT / "adapters/codex/templates/subagent.md").read_text()
    instructions = (ROOT / "adapters/codex/instructions.md").read_text()
    worker = (ROOT / "src/common/agents/Worker.md").read_text()
    overseer = (ROOT / "src/common/agents/Overseer.md").read_text()
    combined = "\n".join((protocol, router, adapter, instructions, worker, overseer))

    assert "may be concise Russian or English" in protocol
    assert "no global human-readability or zero-context constraint" in protocol
    assert "Give each role the context it needs" in router
    assert "fork_context: false" not in combined
    assert "zero-knowledge context" not in combined
    assert "verified parent\ndecisions and evidence" in worker
    assert "task context and verified parent decisions/evidence they need" in " ".join(overseer.split())
    assert "fresh isolated context only" in " ".join(worker.split())
