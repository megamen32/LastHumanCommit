"""Execution evidence remains separate from saved plan metadata in every view."""
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
grid = load_module(TOOLS / "lhc_grid.py", name="lhc_grid_execution_display")
entry = load_module(TOOLS / "lhc_entry.py", name="lhc_entry_execution_display")
pj = load_module(TOOLS / "lhc_plan_json.py", name="lhc_plan_json_execution_display")

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, value):
        self.parts.append(value)

def page_text(html):
    parser = Text(); parser.feed(html)
    return " ".join(" ".join(parser.parts).split())

def ref(sid):
    return {"host_id": "server100", "harness": "codex", "session_id": sid}

def leaf(state="blocked", status="queued"):
    now = datetime.now(timezone.utc).isoformat()
    return {"id": "L01", "label": "Executor evidence", "status": status,
        "session": "LEGACY_PLANNER", "harness": "codex", "owner": "planned owner", "model": "PLANNED_MODEL",
        "estimate_minutes": 5,
        "progress_events": [{"at": now, "note": "report", "actor": {**ref("ACTUAL_ACTOR"), "source": "mcp_metadata"}}],
        "assignment": {"schema_version": 1, "attempt_id": "ATTEMPT-7", "executor_kind": "subagent",
            "lead": ref("ROOT_LEAD"), "parent": ref("NATIVE_PARENT"), "executor": ref("CHILD_EXECUTOR"), "state": state,
            "dispatch": {"request_id": "REQUEST-7", "status": "accepted", "turn_id": "TURN-7", "reason": "codex_quota_guard"},
            "observed_runtime": {"state": "idle", "turn_id": "TURN-7", "model": "OBSERVED_MODEL", "worktree": "/exact/worktree",
                                 "source": "native.status", "observed_at": now},
            "wake": {"wait_id": "WAIT-7", "state": "delivery_blocked", "reason": "codex_quota_guard", "next_at": "NEXT_WAKE",
                     "captured_turn_id": "TURN-7", "observed_at": now}, "events": []}}

def document(rows):
    return {"schema_version": 2, "title": "Execution control", "goal": "CURRENT_GOAL", "slots": 2, "tasks": rows}

def test_html_shows_exact_roles_models_runtime_wake_and_reason():
    graph = grid.parse_graph_json(document([leaf()]))
    html = grid.render_html(graph, grid.build_metrics(graph))
    text = page_text(html)
    for expected in ("Автор последнего события", "ACTUAL_ACTOR", "mcp_metadata", "Lead", "ROOT_LEAD", "Native parent", "NATIVE_PARENT",
                     "Исполнитель", "CHILD_EXECUTOR", "Сохранённый статус", "Назначение", "blocked", "Наблюдаемый runtime", "idle",
                     "Плановая модель", "PLANNED_MODEL", "Наблюдаемая модель", "OBSERVED_MODEL", "ATTEMPT-7", "TURN-7",
                     "WAIT-7", "delivery_blocked", "NEXT_WAKE", "codex_quota_guard", "server100"):
        assert expected in text, expected
    assert "Кандидаты по зависимостям" in text
    assert "Подтверждённый допуск к запуску" in text
    assert "Готовы к запуску" not in text
    assert "Ничего не блокировано и от меня ничего не нужно" not in text
    assert 'data-execution-leaf="L01"' in html

def test_export_round_trip_preserves_author_assignment_and_history():
    original = leaf()
    original["assignment_history"] = [{"attempt_id": "OLD_ATTEMPT", "state": "cancelled"}]
    exported = grid.export_graph(grid.parse_graph_json(document([original])))
    task = exported["tasks"][0]
    assert task["assignment"] == original["assignment"]
    assert task["progress_events"] == original["progress_events"]
    assert task["assignment_history"] == original["assignment_history"]
    assert task["session"] == "LEGACY_PLANNER"
    assert task["model"] == "PLANNED_MODEL"

def test_text_separates_roles_and_does_not_promote_legacy_session_to_executor():
    graph = grid.parse_graph_json(document([leaf(), {"id": "L02", "label": "Legacy", "status": "queued", "session": "ONLY_LEGACY"}]))
    text = grid.render_text(graph, grid.build_metrics(graph))
    for expected in ("ACTUAL_ACTOR", "CHILD_EXECUTOR", "ROOT_LEAD", "NATIVE_PARENT", "PLANNED_MODEL", "OBSERVED_MODEL", "WAIT-7", "codex_quota_guard"):
        assert expected in text
    legacy = grid.execution_view(graph.by_id()["L02"], grid.readiness_decision(graph)["by_id"]["L02"])
    assert legacy["executor"]["session_id"] is None
    assert legacy["actor"]["source"] == "unknown"
    assert legacy["observed_model"] is None
    assert legacy["legacy_binding"]["session_id"] == "ONLY_LEGACY"

def test_plan_state_uses_canonical_owner_and_deferred_dependency_rules(tmp_path):
    plan = tmp_path / "plan"; (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"slots": 2}))
    tasks = [{"id": "A", "status": "running", "owner": "busy"},
             {"id": "B", "status": "queued", "owner": "busy"},
             {"id": "D", "status": "deferred"},
             {"id": "C", "status": "queued", "depends_on": ["D"]}]
    for task in tasks:(plan / "leaves" / (task["id"] + ".json")).write_text(json.dumps(task))
    state = pj.plan_state(plan)
    assert "ready to start" not in state
    assert "B=owner_busy" in state
    assert "C=dependencies_unmet" in state
    assert "dispatchable none" in state

def test_recovery_finds_explicit_lead_and_keeps_no_retry_and_goal_precedence(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; (repo / ".git").mkdir(parents=True)
    plan = repo / ".agents/tasks/execution"; (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"goal": "CURRENT_GOAL", "slots": 2}))
    value = leaf(status="blocked")
    (plan / "leaves/L01.json").write_text(json.dumps(value))
    before = {p: p.read_bytes() for p in plan.rglob("*") if p.is_file()}
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    text = entry.plan_resume_context({"cwd": str(repo), "session_id": "ROOT_LEAD"}, ROOT)
    assert text is not None
    for expected in ("Latest direct human request and STOP take precedence", "CURRENT_GOAL", "ACTUAL_ACTOR", "CHILD_EXECUTOR",
                     "ROOT_LEAD", "NATIVE_PARENT", "PLANNED_MODEL", "OBSERVED_MODEL", "WAIT-7", "delivery_blocked", "codex_quota_guard", "Next action:"):
        assert expected in text, expected
    assert "Do not automatically retry" in text
    assert len(text) <= 4000
    assert {p: p.read_bytes() for p in plan.rglob("*") if p.is_file()} == before

def test_revision_changes_when_execution_receipt_changes():
    a = leaf(); b = json.loads(json.dumps(a)); b["assignment"]["wake"]["state"] = "resumed"
    assert grid.graph_revision(grid.parse_graph_json(document([a]))) != grid.graph_revision(grid.parse_graph_json(document([b])))


def test_published_navigation_prefers_exact_executor_and_keeps_legacy_unchanged():
    pub = load_module(TOOLS / "lhc_plan_publish.py", name="lhc_plan_publish_execution_display")
    source = leaf()
    before = json.loads(json.dumps(source))
    doc = document([source])
    page = pub.page(doc, doc, doc, [{"id": "r001", "document": doc, "reason": "test"}],
                    "r001", datetime.now(timezone.utc).isoformat(), True)
    assert "#/session/codex%3ACHILD_EXECUTOR" in page
    assert "#/session/codex%3ALEGACY_PLANNER" not in page
    assert "server100" in page
    assert source == before
    source["assignment"]["executor"]["session_id"] = None
    panel_tasks = pub.herder_targets([source])
    assert panel_tasks == []
    assert pub.herder_targets([{"session": "LEGACY", "harness": "codex"}])[0]["session"] == "LEGACY"


def test_real_cli_preserves_execution_in_html_text_and_export(tmp_path):
    import subprocess, sys
    source = tmp_path / "graph.json"; source.write_text(json.dumps(document([leaf()])))
    output = tmp_path / "rendered"
    render = subprocess.run([sys.executable, str(TOOLS / "lhc_grid.py"), "render", str(source), "--out-dir", str(output)], capture_output=True, text=True)
    assert render.returncode == 0, render.stderr
    assert "CHILD_EXECUTOR" in page_text((output / "plan.html").read_text())
    assert "Наблюдаемая модель: OBSERVED_MODEL" in (output / "plan.md").read_text()
    exported = tmp_path / "exported.json"
    export = subprocess.run([sys.executable, str(TOOLS / "lhc_grid.py"), "export", str(source), "-o", str(exported)], capture_output=True, text=True)
    assert export.returncode == 0, export.stderr
    assert json.loads(exported.read_text())["tasks"][0]["assignment"]["executor"]["session_id"] == "CHILD_EXECUTOR"
