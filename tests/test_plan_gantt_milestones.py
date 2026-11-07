"""The Gantt shows stages that open to leaves, on real time, with the overrun drawn."""
import json
import re
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


def event(at, status):
    return {"at": at, "changes": {"status": status}}


def leaf(ident, label, status, *, parent=None, estimate=15, events=(), kind=None):
    raw = {"id": ident, "label": label, "status": status, "depends_on": [],
           "estimate_minutes": {"minimum": estimate, "maximum": estimate},
           "progress_events": list(events)}
    if parent:
        raw["parent"] = parent
    if kind:
        raw["kind"] = kind
    return raw


def page(tmp_path, leaves):
    plan = tmp_path / "plan"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"title": "Gantt"}), encoding="utf-8")
    for raw in leaves:
        (plan / "leaves" / f"{raw['id']}.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    document = pj.build_document(plan)
    document["snapshot_at"] = "2026-11-06T12:00:00+00:00"
    graph = grid.parse_graph_json(document)
    graph.snapshot_at = "2026-11-06T12:00:00+00:00"
    html = grid.render_html(graph, grid.build_metrics(graph))
    return html[html.index('id="lhc-plan-gantt"'):html.index('id="comparison"')], html


def test_leaf_times_come_from_its_history_when_nobody_stamped_them(tmp_path):
    raw = leaf("L01", "Лист", "done", events=[
        event("2026-11-06T10:00:00+00:00", "running"),
        event("2026-11-06T10:40:00+00:00", "done"),
    ])
    task = pj.task_from_leaf(raw, tmp_path / "L01.json")
    assert task["started_at"] == "2026-11-06T10:00:00+00:00"
    assert task["finished_at"] == "2026-11-06T10:40:00+00:00"


def test_stages_open_to_their_leaves_and_the_choice_is_remembered(tmp_path):
    panel, html = page(tmp_path, [
        leaf("M1", "Первый этап", "queued", kind="milestone", estimate=45),
        leaf("L01", "Лист этапа", "done", parent="M1", events=[
            event("2026-11-06T10:00:00+00:00", "running"), event("2026-11-06T10:10:00+00:00", "done")]),
    ])
    assert '<details class="gantt-group" data-milestone="M1">' in panel
    assert "Первый этап" in panel and "1 из 1 листьев готово" in panel
    assert 'data-gantt-expand="all"' in panel and 'data-gantt-expand="none"' in panel
    assert "localStorage.setItem('lhc-gantt-expand'" in html


def test_overrun_is_drawn_and_the_plan_is_ordered_by_real_time(tmp_path):
    panel, _ = page(tmp_path, [
        leaf("L01", "Ещё не начат", "queued"),
        leaf("L02", "Шёл час при плане 15", "done", events=[
            event("2026-11-06T10:00:00+00:00", "running"), event("2026-11-06T11:00:00+00:00", "done")]),
        leaf("L03", "Идёт сейчас", "running", events=[event("2026-11-06T11:50:00+00:00", "running")]),
    ])
    assert 'class="bar bar-over"' in panel
    assert 'class="bar bar-plan bar-pending"' in panel
    assert "сейчас" in panel
    order = re.findall(r'data-leaf="(L\d+)"', panel)
    assert order == ["L02", "L03", "L01"], order


def test_a_page_published_by_an_older_client_still_shows_real_time():
    """The published document has the history of a leaf but no stamped times."""
    document = {"schema_version": 2, "snapshot_at": "2026-11-06T12:00:00+00:00", "tasks": [
        leaf("L01", "Без штампов", "done", events=[
            event("2026-11-06T10:00:00+00:00", "running"), event("2026-11-06T10:50:00+00:00", "done")]),
    ]}
    graph = grid.parse_graph_json(document)
    assert graph.leaves[0].started_at == "2026-11-06T10:00:00+00:00"
    assert graph.leaves[0].finished_at == "2026-11-06T10:50:00+00:00"
    html = grid.render_html(graph, grid.build_metrics(graph))
    assert 'class="bar bar-over"' in html


def test_a_leaf_that_went_back_to_the_queue_stops_where_it_left_running(tmp_path):
    panel, _ = page(tmp_path, [
        leaf("L01", "Начат и возвращён", "queued", estimate=60, events=[
            event("2026-11-06T10:00:00+00:00", "running"), event("2026-11-06T10:30:00+00:00", "queued")]),
    ])
    assert 'class="bar bar-over"' not in panel, "30 минут работы при плане 60 — не перерасход"
    assert 'class="bar bar-fact"' in panel
