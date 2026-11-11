"""Plan gates: a leaf is at most 15 minutes, and a real plan starts from research.

2026-11-05: a plan was written 'for show': one leaf of an hour, no recon, no way to
check. The tools now refuse that shape; a single bounded action needs no plan.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "common" / "tools"
pj = load_module(TOOLS / "lhc_plan_json.py", name="lhc_plan_json_gates_test")
lhc = load_module(TOOLS / "lhc_grid.py", name="lhc_grid_gates_test")


def plan(tmp_path, **fields):
    (tmp_path / "plan.json").write_text(json.dumps({"title": "T", **fields}, ensure_ascii=False))
    return tmp_path


RECON = {"recon": ["файл a.conf задаёт маршрут default через шлюз :: /etc/a.conf",
                   "хост gw: ip rule показывает таблицу 100 для клиента :: ssh gw ip rule show",
                   "сервис xray на узле слушает порт 443 и активен :: systemctl status xray"],
         "acceptance_scenario": "curl с клиента, в ответе виден IP шлюза",
         "summary": "Этап 1: маршрут. Этап 2: проверка с клиента.",
         "critique": "Критика: лишних этапов нет; Парето убрало отдельный аудит."}


def test_leaf_of_16_minutes_is_refused_and_15_passes(tmp_path):
    plan(tmp_path)
    pj.update_leaf(tmp_path, "L01", {"label": "ok", "estimate_minutes": 15}, create=True)
    with pytest.raises(pj.LeafError, match="лист .* мин: разбей на листья"):
        pj.update_leaf(tmp_path, "L02", {"label": "big", "estimate_minutes": 16}, create=True)
    with pytest.raises(pj.LeafError):  # the max of the bounds counts, a reason does not help
        pj.update_leaf(tmp_path, "L03", {"label": "b", "estimate_minutes": {"minimum": 5, "maximum": 30},
                                          "estimate_over_limit_reason": "long"}, create=True)
    with pytest.raises(pj.LeafError):
        pj.update_leaf(tmp_path, "L01", {"estimate_minutes": 60})


def test_fullcycle_without_recon_is_refused_and_with_it_passes(tmp_path):
    plan(tmp_path, mode="fullcycle")
    with pytest.raises(pj.LeafError, match="сначала исследуй"):
        pj.update_leaf(tmp_path, "L01", {"label": "impl", "estimate_minutes": 10}, create=True)
    # the first leaf may be research, then recon must exist before the next one
    pj.update_leaf(tmp_path, "L01", {"label": "recon", "kind": "research", "estimate_minutes": 10}, create=True)
    with pytest.raises(pj.LeafError, match="сначала исследуй"):
        pj.update_leaf(tmp_path, "L02", {"label": "impl", "estimate_minutes": 10}, create=True)
    with pytest.raises(pj.LeafError):
        pj.check_activation(tmp_path, {"id": "L02", "estimate_minutes": 10})
    plan(tmp_path, mode="fullcycle", recon=["one fact"], acceptance_scenario="run x")
    with pytest.raises(pj.LeafError):  # one fact is not recon
        pj.update_leaf(tmp_path, "L02", {"label": "impl", "estimate_minutes": 10}, create=True)
    plan(tmp_path, mode="fullcycle", **RECON)
    pj.update_leaf(tmp_path, "L02", {"label": "impl", "estimate_minutes": 10}, create=True)
    pj.check_activation(tmp_path, {"id": "L02", "estimate_minutes": 10})


def test_second_leaf_of_a_plan_needs_recon(tmp_path):
    plan(tmp_path)
    pj.update_leaf(tmp_path, "L01", {"label": "one", "estimate_minutes": 10}, create=True)
    with pytest.raises(pj.LeafError, match="сначала исследуй"):
        pj.update_leaf(tmp_path, "L02", {"label": "two", "estimate_minutes": 10}, create=True)
    plan(tmp_path, **RECON)
    pj.update_leaf(tmp_path, "L02", {"label": "two", "estimate_minutes": 10}, create=True)


def test_single_quickfix_plan_is_allowed_without_recon(tmp_path):
    plan(tmp_path)
    pj.update_leaf(tmp_path, "L01", {"label": "fix", "estimate_minutes": 10}, create=True)
    pj.check_activation(tmp_path, {"id": "L01", "estimate_minutes": 10})


def test_old_plan_with_long_leaf_reads_renders_and_activation_only_warns(tmp_path, capsys):
    plan(tmp_path)
    leaves = tmp_path / "leaves"
    leaves.mkdir()
    (leaves / "L01.json").write_text(json.dumps(
        {"id": "L01", "label": "old", "status": "queued", "estimate_minutes": 60}))
    document = pj.build_document(tmp_path)
    assert document["tasks"][0]["estimate_minutes"]["maximum"] == 60
    assert document["recon"] == []
    pj.check_activation(tmp_path, {"id": "L01", "estimate_minutes": 60})
    assert "предупреждение" in capsys.readouterr().err
    pj.update_leaf(tmp_path, "L01", {"note": "touch"})  # progress on a legacy leaf still works
    graph = lhc.load_graph(pj.build_graph(tmp_path))
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "Сценарии проверки ещё не описаны" in html and "разведка" not in html


def test_recon_and_scenario_are_rendered_on_the_page(tmp_path):
    plan(tmp_path, mode="fullcycle", **RECON)
    pj.update_leaf(tmp_path, "L01", {"label": "x", "estimate_minutes": 10}, create=True)
    graph = lhc.load_graph(pj.build_graph(tmp_path))
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "ip rule показывает таблицу 100" in html
    assert "curl с клиента" in html and "Сценарии проверки ещё не описаны" not in html


def test_router_says_a_single_short_action_needs_no_plan():
    text = " ".join((ROOT / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "A bounded task can be done directly" in text
    assert "smallest complete change" in text
    assert "Fullcycle work first follows the three-summary user choice" in text
    assert "one executable leaf" not in text
    assert (ROOT / "AGENTS.md").read_text().count("\n") <= 300
