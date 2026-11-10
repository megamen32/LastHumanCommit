# LHC:COVERS src/common/tools/lhc_plan_json.py src/common/tools/lhc_grid.py
"""Plan field `summary`: the stages in plain words for a person, one page at most."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_grid as grid  # noqa: E402
import lhc_plan_json as pj  # noqa: E402


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "no-mirror.json"))


def plan_dir(tmp_path):
    plan = tmp_path / "plan"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"title": "S"}), encoding="utf-8")
    (plan / "leaves" / "L01.json").write_text(json.dumps(
        {"id": "L01", "label": "a", "estimate_minutes": 10}), encoding="utf-8")
    return plan


def test_summary_round_trips_through_update_plan_graph_and_html(tmp_path):
    plan = plan_dir(tmp_path)
    text = "Этап 1: разведка\nЭтап 2: <b>сборка</b>"
    pj.update_plan(plan, {"summary": text})
    document = pj.build_document(plan)
    assert document["summary"] == text
    graph = grid.parse_graph_json(document)
    assert graph.summary == text
    html = grid.render_html(graph, grid.build_metrics(graph))
    assert "Коротко о плане" in html
    assert "Этап 1: разведка\nЭтап 2: &lt;b&gt;сборка&lt;/b&gt;" in html and "<b>сборка</b>" not in html
    assert "Коротко о плане:" in pj.report_block_of(document)


def test_summary_longer_than_a_page_is_refused_and_leaves_the_plan_alone(tmp_path):
    plan = plan_dir(tmp_path)
    pj.update_plan(plan, {"summary": "x" * 3000})
    with pytest.raises(pj.LeafError, match="summary is one page for a person: shorten it to 3000 characters"):
        pj.update_plan(plan, {"summary": "x" * 3001})
    assert pj.build_document(plan)["summary"] == "x" * 3000
    with pytest.raises(pj.LeafError, match="summary"):
        pj.update_plan(plan, {"summary": 5})
