"""Plan policy must survive graph export and every visible estimate check."""
from pathlib import Path

import pytest
from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]
grid = load_module(ROOT / "src/common/tools/lhc_grid.py", name="lhc_grid_plan_policy")


def document(cap=60):
    return {
        "schema_version": 2,
        "estimate_policy": {"leaf_cap_minutes": cap, "reason": "Owner explicitly requested this limit"},
        "deliverable": "plan",
        "decomposition": "complete",
        "decomposition_check": {"mode": "complete", "ready": True},
        "tasks": [{"id": "L01", "label": "Prepare executable work", "status": "queued",
                   "estimate_minutes": {"minimum": 30, "maximum": 60}}],
    }


def test_owner_limit_is_used_by_checks_and_both_pages():
    graph = grid.parse_graph_json(document())
    assert grid.estimate_cap_findings(graph) == []
    assert grid.estimate_cap_warnings(graph) == []
    metrics = grid.build_metrics(graph)
    assert "id='lhc-estimate-cap'" not in grid.render_html(graph, metrics)
    assert "выше предела" not in grid.render_print_html(graph, metrics)


def test_smaller_plan_limit_is_not_replaced_with_default():
    doc = document(5)
    doc["tasks"][0]["estimate_minutes"] = {"minimum": 10, "maximum": 10}
    graph = grid.parse_graph_json(doc)
    findings = grid.estimate_cap_findings(graph)
    assert len(findings) == 1
    assert findings[0]["cap"] == 5
    assert findings[0]["breach"] is True
    assert "5 мин" in "\n".join(grid.estimate_cap_warnings(graph))


def test_export_and_refresh_retain_assignment_and_policy():
    source = document()
    exported = grid.export_graph(grid.parse_graph_json(source))
    keys = ("estimate_policy", "deliverable", "decomposition", "decomposition_check")
    for key in keys:
        assert exported.get(key) == source[key]
    fresh = {"schema_version": 2, "tasks": [{"id": "L01"}]}
    grid.merge_attribution(fresh, exported)
    for key in keys:
        assert fresh.get(key) == source[key]
    assert grid.estimate_cap_findings(grid.parse_graph_json(exported)) == []


@pytest.mark.parametrize("policy", [
    None,
    {"leaf_cap_minutes": True, "reason": "owner"},
    {"leaf_cap_minutes": 60, "reason": ""},
])
def test_invalid_policy_is_not_silently_ignored(policy):
    doc = document()
    doc["estimate_policy"] = policy
    with pytest.raises(ValueError, match="estimate_policy"):
        grid.parse_graph_json(doc)


def test_legacy_graph_keeps_default_limit():
    doc = document()
    del doc["estimate_policy"]
    findings = grid.estimate_cap_findings(grid.parse_graph_json(doc))
    assert findings[0]["cap"] == 15
    assert findings[0]["breach"] is True
