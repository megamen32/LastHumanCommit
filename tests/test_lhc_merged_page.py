"""The merged page: the state of the plan and the delivery narrative are one page.

The owner asked for the best of two pages - the plan dashboard and the
delivery audit - and for one page that carries all of it. These tests protect
the seams of that merge:

* the delivery side is rendered into the plan page, not beside it;
* the page has one headline, one navigation and one theme switch;
* every anchor of the navigation points at a section that exists;
* the leaves of the plan are still there: a merge that loses the task table
  loses the state of the work;
* the delivery data reaches the page field by field.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"
PRODUCT = ROOT / "src" / "common" / "tools" / "lhc_product.py"
DATA = Path(
    "/Users/user/Documents/ServerAdministartion/.tmp/airlock-audit/audit-data.json"
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def merged_html():
    lhc = load("lhc_grid_merged", TOOL)
    product = load("lhc_product_merged", PRODUCT)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    leaves = product.product_leaves(data)
    tasks = []
    for leaf in leaves:
        low = leaf.get("estimate_minutes")
        high = leaf.get("estimate_max_minutes")
        tasks.append({
            "id": leaf.get("id"),
            "label": leaf.get("label") or "",
            "status": leaf.get("status") or "queued",
            "owner": leaf.get("owner") or "",
            "estimate_minutes": {"minimum": low, "maximum": high if high is not None else low},
            "depends_on": leaf.get("depends_on") or [],
            "note": leaf.get("note") or "",
        })
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "title": str(data.get("title") or ""),
        "goal": str(data.get("title") or ""),
        "business_result": str(data.get("coverageNote") or ""),
        "current_progress": str(data.get("method") or ""),
        "tasks": tasks,
    })
    return lhc, product, data, lhc.render_html(graph, lhc.build_metrics(graph), data)


def test_the_delivery_side_is_inside_the_plan_page():
    _, _, _, html = merged_html()
    for anchor in ("lhc-summary", "lhc-requirements", "lhc-health", "lhc-gantt",
                   "lhc-work", "lhc-agent", "lhc-sources", "lhc-spec"):
        assert f'id="{anchor}"' in html, f"нет секции {anchor}"
    # The state of the plan is on the same page.
    for anchor in ("lhc-state", "lhc-leaves", "lhc-plan-gantt", "lhc-blocking",
                   "lhc-forecast", "lhc-journal"):
        assert f'id="{anchor}"' in html, f"нет секции плана {anchor}"


def test_one_headline_one_navigation_one_theme_switch():
    _, _, _, html = merged_html()
    assert html.count("class=\"lhc-nav\"") == 1, "навигация должна быть одна"
    assert html.count('id="lhc-theme-toggle"') == 1, "переключатель темы должен быть один"
    assert html.count('id="theme-toggle"') == 0, "второй переключатель темы не нужен"
    assert html.count("<h1") == 0, "заголовок страницы один — в герое"


def test_every_anchor_of_the_navigation_exists():
    _, _, _, html = merged_html()
    anchors = re.findall(r'class="lhc-nav-link" href="#([^"]+)"', html)
    assert len(anchors) >= 12
    for anchor in anchors:
        assert f'id="{anchor}"' in html, f"якорь {anchor} ведёт в никуда"


def test_the_leaves_of_the_plan_survive_the_merge():
    _, _, data, html = merged_html()
    rows = re.findall(r"<tr data-status=", html)
    assert len(rows) == len(data["tasks"]), "листья плана должны остаться на странице"
    assert "class='leaf-row'" in html


def test_the_delivery_data_reaches_the_page():
    _, product, data, html = merged_html()
    for probe in (
        "Версия: 1.5.32",  # a version of the dashboard, not of the data
    ):
        if probe in html:
            break
    # every requirement of the matrix
    for requirement in data["requirements"]:
        assert requirement["id"] in html, f"требование {requirement['id']} не на странице"
        assert requirement["title"][:24] in html
    # every source of the evidence
    for source in data["sources"]:
        assert source["id"] in html, f"источник {source['id']} не на странице"
    # the agent task and the rules
    assert data["agentPrompt"][:120] in html
    for rule in data["rules"][:3]:
        assert rule[:30] in html


def test_the_page_without_a_delivery_side_is_still_the_plan_page():
    lhc = load("lhc_grid_plain", TOOL)
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "title": "План",
        "goal": "Цель",
        "business_result": "Результат",
        "tasks": [{"id": "L01", "label": "Задача", "status": "done", "depends_on": []}],
    })
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "lhc-summary" not in html, "без delivery side её секций быть не должно"
    assert "class='leaf-row'" in html
    assert "lhc-state" in html
