"""Readiness, goal acceptance and uncertain time stay distinct in plan views."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
import lhc_grid as grid
import lhc_plan_catalog as catalog

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)

def entry(tasks, **extra):
    return {"snapshot": {"project": "lhc", "name": "plan-test", "last_file_event": NOW.isoformat(),
                         "document": {"title": "План", "slots": 2, "tasks": tasks, **extra}}}

def test_candidate_wording_never_claims_launch_admission():
    graph = grid.parse_graph_json({"schema_version": 2, "slots": 1, "tasks": [
        {"id": "L01", "label": "Шаг", "status": "queued", "estimate_minutes": 10}]})
    metrics = grid.build_metrics(graph)
    text = grid.render_text(graph, metrics)
    html = grid.render_html(graph, metrics)
    assert "Подтверждённый допуск к запуску: нет" in text
    assert "готово к запуску:" not in text
    assert "кандидаты по зависимостям и вместимости:" in text
    assert "Кандидаты по зависимостям и вместимости" in html

def test_unknown_leaf_does_not_get_default_whole_plan_eta():
    item = entry([
        {"id": "L01", "status": "queued", "estimate_minutes": 10},
        {"id": "L02", "status": "queued", "estimate_unknown_reason": "нужен замер"}])
    summary = catalog.summarize(item, NOW)
    assert summary["eta"] is None
    assert summary["known_remaining_minutes"] == 10
    assert summary["unknown_estimate_ids"] == ["L02"]
    page = catalog.render([item], now=NOW)
    assert "Срок неизвестен" in page
    assert "Известная работа: 10 мин" in page
    assert "Завершится ≈" not in page

def test_partial_scope_keeps_numeric_work_but_hides_catalog_finish():
    summary = catalog.summarize(entry([
        {"id": "L01", "status": "queued", "estimate_minutes": 10,
         "estimate_unknown_reason": "старое диагностическое поле"}]), NOW)
    assert summary["eta"] is None
    assert summary["known_remaining_minutes"] == 10

def test_completed_cards_never_accept_legacy_goal_or_hide_deferred_work():
    summary = catalog.summarize(entry([
        {"id": "L01", "status": "done"},
        {"id": "L02", "status": "deferred"}]), NOW)
    assert summary["state"] != "completed"
    assert summary["goal_status"] == "unknown"
    assert (summary["done"], summary["total"]) == (1, 2)
    assert "Цель не подтверждена" in summary["stage"]
    assert "отложено: 1" in summary["stage"]

def test_all_done_cards_only_complete_work_not_goal():
    summary = catalog.summarize(entry([{"id": "L01", "status": "done"}]), NOW)
    assert summary["state"] != "completed"
    assert summary["goal_status"] == "unknown"
    assert "Все шаги выполнены" in summary["stage"]
    assert "Цель не подтверждена" in summary["stage"]

def projection(status):
    return {"goal_status": status, "fingerprint": "a" * 64,
            "source": {"kind": "native_outcome", "harness": "codex", "session_id": "S1",
                       "outcome_id": "O1", "source_fingerprint": "b" * 64}}

def test_superseded_plan_never_appears_completed():
    summary = catalog.summarize(entry([{"id": "L01", "status": "done"}],
                                      goal_control=projection("superseded")), NOW)
    assert summary["state"] != "completed"
    assert "заменён" in summary["stage"].lower()

def test_verified_snapshot_goal_acceptance_is_labelled_as_snapshot():
    item = entry([{"id": "L01", "status": "done"}], goal_control=projection("accepted"))
    summary = catalog.summarize(item, NOW)
    assert summary["state"] == "completed"
    assert "Цель принята по исходному снимку" in summary["stage"]

def test_unverified_cached_goal_control_does_not_accept_goal():
    summary = catalog.summarize(entry([{"id": "L01", "status": "done"}],
                                      goal_control={"goal_status": "accepted"}), NOW)
    assert summary["state"] != "completed"
    assert summary["goal_status"] == "unknown"


def test_known_work_keeps_dependencies_through_unknown_leaf():
    summary = catalog.summarize(entry([
        {"id": "A", "status": "queued", "estimate_minutes": 10},
        {"id": "B", "status": "queued", "depends_on": ["A"]},
        {"id": "C", "status": "queued", "estimate_minutes": 10, "depends_on": ["B"]}]), NOW)
    assert summary["eta"] is None
    assert summary["known_remaining_minutes"] == 20

def test_partial_scope_keeps_numeric_work_but_hides_grid_finish():
    graph = grid.parse_graph_json({"schema_version": 2, "slots": 1, "tasks": [
        {"id": "L01", "label": "Измерить часть", "status": "queued", "estimate_minutes": 10,
         "estimate_unknown_reason": "оценена только диагностика"}]})
    metrics = grid.build_metrics(graph)
    assert metrics["remaining_minutes_max"] == 10
    assert not metrics["eta_exact"]
    assert "финиш неизвестен" in grid.render_text(graph, metrics)
    assert "Срок неизвестен" in grid.render_html(graph, metrics)

def test_full_finite_estimate_has_a_step_eta():
    summary = catalog.summarize(entry([
        {"id": "L01", "status": "queued", "estimate_minutes": 10}]), NOW)
    assert summary["eta"] == NOW + timedelta(minutes=10)

def test_explicit_goal_acceptance_keeps_deferred_cards_visible():
    item = entry([{"id": "L01", "status": "done"}, {"id": "L02", "status": "deferred"}],
                 goal_control=projection("accepted"))
    summary = catalog.summarize(item, NOW)
    assert summary["goal_status"] == "accepted"
    assert "Цель принята по исходному снимку" in summary["stage"]
    assert "Все шаги выполнены" not in summary["stage"]
    assert "отложено: 1" in summary["stage"]
    assert (summary["done"], summary["total"]) == (1, 2)

def test_no_known_work_does_not_display_one_invented_minute():
    item = entry([{"id": "L01", "status": "queued", "estimate_unknown_reason": "не оценено"}])
    assert catalog.summarize(item, NOW)["known_remaining_minutes"] == 0
    page = catalog.render([item], now=NOW)
    assert "Известная работа: 1 мин" not in page
    assert "Срок неизвестен" in page
