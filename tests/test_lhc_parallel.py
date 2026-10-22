#!/usr/bin/env python3
"""Tests for the parallel-lane tool and the 30-minute parallel-lines reminder.

The tool answers one question about a task graph: which lines can start right
now. The reminder repeats that answer in the 30-minute checkpoint. Both are
readings of the plan: neither estimates, reviews, judges or blocks.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_parallel.py"
GUARD = ROOT / "src/common/tools/lhc_time_guard.py"
ENTRY = ROOT / "src/common/tools/lhc_entry.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("lhc_parallel", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_guard():
    spec = importlib.util.spec_from_file_location("lhc_time_guard_parallel", GUARD)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lhc = load_tool()
guard = load_guard()


def write_graph(path: Path, tasks: list[dict], **extra) -> Path:
    """Write one task graph file and return its path."""

    document = {"schema_version": 2, "title": "Demo objective", "goal": "one result", "tasks": tasks}
    document.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


# --------------------------------------------------------------------------
# ready lines
# --------------------------------------------------------------------------


def test_a_queued_line_whose_dependencies_are_done_is_ready(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "contract", "status": "done", "depends_on": []},
            {"id": "L02", "label": "build and push", "status": "queued", "depends_on": ["L01"]},
        ],
        slots=2,
    )

    summary = lhc.summarize(graph)

    assert [task.id for task in summary.ready] == ["L02"]
    assert summary.ready[0].estimate_label == "оценка не указана"


def test_a_queued_line_whose_dependency_is_not_done_waits_and_names_it(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "contract", "status": "running", "depends_on": []},
            {"id": "L02", "label": "integration", "status": "queued", "depends_on": ["L01"]},
        ],
        slots=2,
    )

    summary = lhc.summarize(graph)

    assert summary.ready == []
    assert [(task.id, unmet) for task, unmet in summary.waiting] == [("L02", ["L01"])]
    text = lhc.render_text(summary)
    assert "L02" in text and "L01" in text


def test_a_dependency_that_does_not_exist_is_never_satisfied(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "orphan", "status": "queued", "depends_on": ["MISSING"]}],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.ready == []
    assert summary.waiting[0][1] == ["MISSING"]
    assert "нет такой задачи в графе" in lhc.render_text(summary)


def test_a_queued_line_with_a_blocker_text_is_not_blocked(tmp_path):
    """One rule of the count of blockers: the status says it, the text does not."""

    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "signed certificate", "status": "queued",
          "depends_on": [], "blocker": "the source sent no certificate"}],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.blocked == []
    assert [task.id for task in summary.ready] == ["L01"]


def test_a_deferred_line_is_not_unknown_and_waits_for_nothing(tmp_path):
    """A line the owner deferred is not an unknown state and takes no slot."""

    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "deferred by the owner", "status": "deferred", "depends_on": []},
            {"id": "L02", "label": "first line", "status": "queued", "depends_on": []},
            {"id": "L03", "label": "second line", "status": "queued", "depends_on": []},
        ],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.unknown_status == []
    assert [task.id for task in summary.ready] == ["L02"]
    assert [task.id for task in summary.deferred] == ["L03"]
    assert summary.blocked == []
    assert summary.waiting == []


def test_a_deferred_line_is_named_in_the_answer_of_the_planner(tmp_path):
    """It is not waiting and it is not blocked: it is named apart."""

    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "правка объявления", "status": "deferred", "depends_on": []}],
        slots=1,
    )

    text = lhc.render_text(lhc.summarize(graph))

    assert "Отложено владельцем" in text
    assert "правка объявления" in text
    assert "Ждут зависимостей" not in text
    assert "Заблокированы" not in text


# --------------------------------------------------------------------------
# slots
# --------------------------------------------------------------------------


def test_free_slots_are_slots_minus_the_running_lines(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "a", "status": "running", "depends_on": []},
            {"id": "L02", "label": "b", "status": "running", "depends_on": []},
            {"id": "L03", "label": "c", "status": "queued", "depends_on": []},
        ],
        slots=3,
    )

    summary = lhc.summarize(graph)

    assert summary.free_slots == 1
    assert [task.id for task in summary.ready] == ["L03"]
    assert summary.slot_of == {"L03": 1}


def test_without_a_free_slot_the_ready_line_is_deferred_not_lost(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "a", "status": "running", "depends_on": []},
            {"id": "L02", "label": "b", "status": "queued", "depends_on": []},
        ],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.free_slots == 0
    assert summary.ready == []
    assert [task.id for task in summary.deferred] == ["L02"]
    text = lhc.render_text(summary)
    assert "Готовы, но ждут свободного слота" in text
    assert "L02" in text


def test_a_graph_without_slots_does_not_limit_the_parallel_lines(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "a", "status": "running", "depends_on": []},
            {"id": "L02", "label": "b", "status": "queued", "depends_on": []},
            {"id": "L03", "label": "c", "status": "queued", "depends_on": []},
        ],
    )

    summary = lhc.summarize(graph)

    assert summary.slots is None
    assert summary.free_slots is None
    assert [task.id for task in summary.ready] == ["L02", "L03"]
    assert "без ограничения" in lhc.render_text(summary)


# --------------------------------------------------------------------------
# blocked lines
# --------------------------------------------------------------------------


def test_a_blocked_line_reports_its_reason(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "signed certificate", "status": "blocked",
          "depends_on": [], "blocker": "the source sent no certificate"}],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert len(summary.blocked) == 1
    task, reason = summary.blocked[0]
    assert task.id == "L01"
    assert reason == "the source sent no certificate"
    assert "the source sent no certificate" in lhc.render_text(summary)


def test_blocker_details_reason_is_used_when_the_flat_blocker_is_empty(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "signed certificate", "status": "blocked", "depends_on": [],
          "blocker_details": {"reason": "waiting for the source since monday"}}],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.blocked[0][1] == "waiting for the source since monday"


def test_a_graph_without_blocker_details_is_not_an_error(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [{"id": "L01", "label": "plain", "status": "blocked", "depends_on": []}],
        slots=1,
    )

    summary = lhc.summarize(graph)

    assert summary.blocked[0][1] == "причина не указана"


# --------------------------------------------------------------------------
# broken input
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content,marker",
    [
        ("", "пуст"),
        ("{ not json", "JSON"),
        ('{"tasks": []}', "ни одной задачи"),
        ('{"schema_version": 2, "tasks": [{"label": "no id"}]}', "id"),
    ],
)
def test_a_broken_graph_exits_non_zero_with_a_readable_diagnostic(tmp_path, content, marker):
    path = tmp_path / "plan.graph.json"
    path.write_text(content, encoding="utf-8")

    result = run_tool(str(path))

    assert result.returncode != 0
    assert marker in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""


def test_a_missing_graph_file_exits_non_zero(tmp_path):
    result = run_tool(str(tmp_path / "absent.graph.json"))

    assert result.returncode != 0
    assert "не найден" in result.stderr
    assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------
# machine output
# --------------------------------------------------------------------------


def test_the_json_mode_returns_one_valid_json_object(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "a", "status": "running", "depends_on": [],
             "estimate_minutes": {"minimum": 10, "maximum": 15}},
            {"id": "L02", "label": "b", "status": "queued", "depends_on": [],
             "estimate_minutes": {"minimum": 5, "maximum": 5}},
        ],
        slots=2,
    )

    result = run_tool(str(graph), "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["slots"] == 2
    assert payload["free_slots"] == 1
    assert [item["id"] for item in payload["running"]] == ["L01"]
    assert [item["id"] for item in payload["ready"]] == ["L02"]
    assert payload["ready"][0]["estimate_minutes"]["minimum"] == 5
    assert payload["next_step"]["id"] == "L02"


def test_the_slot_mode_assigns_a_concrete_slot_to_every_ready_line(tmp_path):
    graph = write_graph(
        tmp_path / "plan.graph.json",
        [
            {"id": "L01", "label": "a", "status": "queued", "depends_on": []},
            {"id": "L02", "label": "b", "status": "queued", "depends_on": []},
        ],
        slots=2,
    )

    result = run_tool(str(graph), "--slot")

    assert result.returncode == 0
    assert "слот 1" in result.stdout
    assert "слот 2" in result.stdout


# --------------------------------------------------------------------------
# the 30-minute reminder
# --------------------------------------------------------------------------


def project_with_graph(tmp_path: Path, tasks: list[dict], **extra) -> Path:
    """Build a project directory that carries a canonical plan graph."""

    project = tmp_path / "project"
    write_graph(project / ".agents" / "tasks" / "objective" / "plan.graph.json", tasks, **extra)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    return project


def heartbeat_context(project: Path, session_id: str) -> str:
    """Run the live heartbeat hook and return the additional context."""

    payload = {"cwd": str(project), "session_id": session_id, "tool_name": "exec_command"}
    result = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(ROOT), "--runtime", "codex",
         "--event", "PostToolUse", "--heartbeat-only"],
        input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, check=True)
    return json.loads(result.stdout or "{}").get("hookSpecificOutput", {}).get("additionalContext", "")


def rewind(state_file: Path, minutes: int) -> None:
    """Move the observed wall clock and the heartbeat start into the past."""

    state = json.loads(state_file.read_text(encoding="utf-8"))
    past = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    state["started_at"] = past.isoformat()
    state["last_observed_at"] = past.isoformat()
    state["due_at"] = (past + timedelta(minutes=120)).isoformat()
    timer = state["native_heartbeat"]
    timer["started_at"] = past.isoformat()
    timer["last_seen_at"] = past.isoformat()
    state_file.write_text(json.dumps(state), encoding="utf-8")


def state_file(project: Path) -> Path:
    files = list((project / ".agents/shared-session/learning").glob("*.json"))
    assert len(files) == 1, files
    return files[0]


def test_the_reminder_names_the_ready_parallel_lines(tmp_path):
    project = project_with_graph(
        tmp_path,
        [
            {"id": "L03", "label": "board intake", "status": "running", "depends_on": []},
            {"id": "L05", "label": "build and push", "status": "queued", "depends_on": [],
             "estimate_minutes": {"minimum": 10, "maximum": 10}},
        ],
        slots=3,
    )

    context = guard.render_parallel_lines(project)

    assert "параллельные линии" in context
    assert "Сейчас в работе: L03" in context
    assert "Готовы к запуску: L05 «build and push»" in context
    assert "Свободно слотов: 2" in context
    assert "Запусти параллельные линии, которые готовы" in context


def test_the_reminder_is_delivered_by_the_live_heartbeat(tmp_path):
    project = project_with_graph(
        tmp_path,
        [
            {"id": "L03", "label": "board intake", "status": "running", "depends_on": []},
            {"id": "L05", "label": "build and push", "status": "queued", "depends_on": []},
        ],
        slots=3,
    )
    heartbeat_context(project, "parallel-reminder")
    rewind(state_file(project), 31)

    context = heartbeat_context(project, "parallel-reminder")

    assert "30-minute plan report" in context
    assert "параллельные линии" in context
    assert "L05" in context


def test_the_reminder_says_nothing_when_the_plan_graph_is_missing(tmp_path):
    project = tmp_path / "no-plan"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)

    context = guard.render_parallel_lines(project)

    assert "параллельные линии" in context
    assert "план-граф не найден" in context
    assert "не определены" in context
    # Nothing is invented when the plan is absent.
    assert "L0" not in context


def test_the_reminder_carries_no_evaluation_or_blocking_command(tmp_path):
    project = project_with_graph(
        tmp_path,
        [
            {"id": "L03", "label": "board intake", "status": "running", "depends_on": []},
            {"id": "L05", "label": "build and push", "status": "queued", "depends_on": []},
        ],
        slots=3,
    )

    context = guard.render_parallel_lines(project)

    forbidden = [
        "оцени", "оценка работы", "ревью", "вердикт", "заблокируй", "отклони",
        "must review", "must judge", "verdict", "approve", "reject",
    ]
    for marker in forbidden:
        assert marker not in context.lower(), marker
    # The reminder keeps the time-only guarantee of the guard.
    assert "never estimates, reviews, judges or blocks" in context
