# LHC:COVERS src/common/tools/lhc_plan_json.py src/common/tools/lhc_grid.py src/common/tools/lhc_parallel.py src/common/tools/lhc_plan_catalog.py src/common/tools/lhc_readiness.py
"""«Отложено ИИ» is a second deferred status: out of the remainder, own label and count."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_grid as grid  # noqa: E402
import lhc_parallel as parallel  # noqa: E402
import lhc_plan_json as pj  # noqa: E402


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "no-mirror.json"))


def make_plan(tmp_path):
    plan = tmp_path / "plan"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"title": "Defer"}), encoding="utf-8")
    rows = [("L01", "done", ""), ("L02", "deferred", ""), ("L03", "deferred_ai", "отложено ИИ: нет ключа"),
            ("L04", "queued", "")]
    for ident, status, result in rows:
        raw = {"id": ident, "label": "Лист " + ident, "status": status, "depends_on": [],
               "estimate_minutes": {"minimum": 10, "maximum": 10}}
        if result:
            raw["result"] = result
        (plan / "leaves" / f"{ident}.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return plan


@pytest.mark.parametrize("word", ["deferred_ai", "отложено_ии", "отложено ии", "deferred_by_ai", "Отложено ИИ"])
def test_ai_aliases_normalise_and_owner_aliases_stay(word):
    assert pj._status(word, Path("x")) == "deferred_ai"
    assert grid.normalize_status(word) == "deferred_ai"
    assert parallel.STATUS_ALIASES[word.lower().replace(" ", "_")] == "deferred_ai"
    for owner in ("deferred", "отложено", "отложено_владельцем"):
        assert pj._status(owner, Path("x")) == "deferred"


def test_deferred_ai_is_out_of_the_remainder_like_deferred(tmp_path):
    document = pj.build_document(make_plan(tmp_path))
    metrics = grid.build_metrics(grid.parse_graph_json(document))
    assert (metrics["deferred"], metrics["deferred_ai"]) == (1, 1)
    assert metrics["unfinished"] == 1  # only L04 is left


def test_both_labels_and_counts_in_text_and_html(tmp_path):
    plan = make_plan(tmp_path)
    text = pj.report_block_of(pj.build_document(plan))
    assert "L03" in text
    document = pj.build_document(plan)
    graph = grid.parse_graph_json(document)
    html = grid.render_html(graph, grid.build_metrics(graph))
    assert "Отложено владельцем" in html and "Отложено ИИ" in html
    out = parallel.render_text(parallel.analyze(parallel.parse_graph_json(document)))
    assert "Отложено владельцем (1):" in out and "Отложено ИИ (1):" in out


def test_writing_gate_wants_a_result_for_deferred_ai(tmp_path):
    plan = tmp_path / "plan"
    plan.mkdir()
    (plan / "plan.json").write_text(json.dumps({"title": "T"}), encoding="utf-8")
    pj.update_leaf(plan, "L01", {"label": "a", "estimate_minutes": 10}, create=True)
    with pytest.raises(pj.LeafError, match="deferred_ai.*result"):
        pj.update_leaf(plan, "L01", {"status": "deferred_ai"})
    pj.update_leaf(plan, "L01", {"status": "deferred_ai", "result": "отложено ИИ: нет ключа · вернуться, когда выдадут"})
    assert pj.read_leaf(plan / "leaves" / "L01.json")["status"] == "deferred_ai"
