"""The surface the owner reads: progress first, everything clickable, no water.

Three things are protected here, and all three came from the owner looking at
the page on a phone:

* the progress is at the very top and stays in sight while the page scrolls;
* every number on the page can be opened and shows the tasks behind it;
* """
from __future__ import annotations

import json
import sys
from pathlib import Path

from _inprocess import load_module, run_cli

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"
ENTRY = ROOT / "plugins" / "last-human-commit" / "tools" / "lhc_entry.py"
entry = load_module(ENTRY, name="lhc_entry_plan_surface_test")


def load(name: str, path: Path):
    return load_module(path, name=name)


def sample_graph():
    lhc = load("lhc_grid_surface", TOOL)
    graph = lhc.parse_graph_json({
        "schema_version": 2,
        "goal": "Свести рабочий набор к одному",
        "business_result": "Владелец видит тот же набор в обоих местах",
        "tasks": [
            {"id": "L01", "label": "Сделано", "status": "done", "depends_on": [],
             "estimate_minutes": {"minimum": 10, "maximum": 10}},
            {"id": "L02", "label": "В работе", "status": "running", "depends_on": ["L01"],
             "estimate_minutes": {"minimum": 20, "maximum": 30}},
            {"id": "L03", "label": "Ждёт владельца", "status": "waiting", "depends_on": ["L02"],
             "estimate_minutes": {"minimum": 5, "maximum": 5},
             "blocker_details": {"human_required": "yes",
                                 "human_action": "Выдать доступ"}},
        ],
    })
    return lhc, graph


# ---------------------------------------------------------------- the top
def test_the_progress_is_the_first_thing_and_sticks():
    lhc, graph = sample_graph()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    body = html[html.find("<body"):]
    assert body.find("progress-strip") < body.find("kpis")
    assert ".progress-strip { position: sticky; top: 0;" in html
    # The strip carries the real numbers of the plan, not a made-up percentage.
    assert "1 / 3" in html
    assert "33.3%" in html


def test_every_number_of_the_page_opens_the_tasks_behind_it():
    lhc, graph = sample_graph()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    for key in ("done", "running", "blocked", "queued", "deferred", "unfinished",
                "parallel", "remaining", "forecast", "effort", "all"):
        assert f'data-tile="{key}"' in html, f"плитка {key} не кликабельна"
    assert 'id="lhc-tile-card"' in html
    assert "querySelectorAll('[data-tile]')" in html
    assert "renderTileList" in html
    # The tasks behind the tiles travel with the page.
    assert 'id="lhc-tile-index"' in html
    assert "L01" in html and "L02" in html and "L03" in html


def test_what_blocks_and_what_needs_the_owner_are_told_apart():
    lhc, graph = sample_graph()
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "Что блокирует" in html
    assert "Держит работу" in html
    assert "Нужно от меня" in html
    assert "Выдать доступ" in html
    # A leaf that waits is not a leaf that is blocked.
    assert html.count('class="blocker"') == 0
    assert html.count('class="holding"') == 1


# ------------------------------------------------------------ no text cap
def test_long_plan_and_task_descriptions_are_never_capped():
    """The wording of a human is not capped: a long, precise text is better."""
    lhc, graph = sample_graph()
    graph.goal = "Д" * 400
    graph.business_result = "Р" * 800
    graph.business_results = [graph.business_result]
    graph.leaves[0].description = "Описание с контекстом, действием и ожидаемым результатом. " * 120
    html = lhc.render_html(graph, lhc.build_metrics(graph))
    assert "Д" * 400 in html
    assert "Р" * 800 in html
    # No cap function survives in the renderer.
    assert not hasattr(lhc, "check_text_budget")



def test_writing_the_plan_rebuilds_the_page(tmp_path):
    """The agent writes the plan; the page is generated from it."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    graph_path = plan_dir / "plan.graph.json"
    graph_path.write_text(json.dumps({
        "schema_version": 2,
        "goal": "Цель",
        "business_result": "Результат",
        "tasks": [{"id": "L01", "label": "Задача", "status": "queued", "depends_on": []}],
    }, ensure_ascii=False), encoding="utf-8")
    page = plan_dir / "plan.html"
    assert not page.exists()

    event = {"cwd": str(plan_dir), "session_id": "s", "tool_input": {"file_path": str(graph_path)}}
    proc = run_cli(entry, ["--event", "PostToolUse", "--heartbeat-only"],
                   stdin=json.dumps(event), text=False)
    assert page.exists(), f"страница не пересобрана: {proc.stdout!r} {proc.stderr!r}"
    assert "пересобрана" in proc.stdout.decode("utf-8", "replace")


