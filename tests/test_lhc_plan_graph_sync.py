#!/usr/bin/env python3
"""The live plan report, the task graph and the compaction handoff stay one unit.

Three properties are protected here:

* `lhc_grid.py check-plan` says out loud when the report's task list and the
  graph's leaf list diverge, and fails loudly when they do;
* the 30-minute reminder names the call order (map first, view second,
  reconcile third) without turning into a review or a verdict;
* the compaction handoff carries the plan as readable text rendered from the
  canonical graph, never as a JSON dump, and stays inside its size budget.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from _inprocess import git_repo, load_module, run_cli


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"
GRID = TOOLS / "lhc_grid.py"
sys.path.insert(0, str(TOOLS))

import lhc_time_guard as guard  # noqa: E402


REPORT = """Цель: закрыть интеграцию источника
Бизнес-результат: сообщение превращается в карточку
Декомпозиция: 4 листа · 2 параллельно · 2 волны · слотов: 2

✅ (контракт источника) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
✅ (поиск источника) начата 14:02 закончена 14:11, оценка 15 минут, факт 9 минут, ∥ параллельно с листом 1

🔄 работаем (приём в доске) начата 14:12, оценка 20 минут, прошло 22 минут, отстаём потому что: ждём ключ
⏳ (сборка и push) начнём после листа 3, потому что нужен принятый контракт, примерно в 14:30, оценка 10 минут, закончим в 14:40
"""


grid = load_module(GRID, name="lhc_grid_plan_sync")


def run_grid(*args: str):
    return run_cli(grid, args)


def write_report_and_graph(base: Path, report: str = REPORT) -> tuple[Path, Path]:
    base.mkdir(parents=True, exist_ok=True)
    report_path = base / "plan.report.md"
    report_path.write_text(report, encoding="utf-8")
    graph_path = base / "plan.graph.json"
    exported = run_grid("export", str(report_path), "-o", str(graph_path))
    assert exported.returncode == 0, exported.stderr
    return report_path, graph_path


def compact(cwd: Path, session_id: str = "sid-compact-plan") -> str:
    payload = {"session_id": session_id, "trigger": "auto"}
    args = SimpleNamespace(
        runtime="codex", event="PreCompact", now=datetime.now(timezone.utc)
    )
    guard.compaction_hook(args, payload, cwd)
    _state, handoff_path, _lock = guard.compaction_paths(cwd / ".agents", payload)
    return handoff_path.read_text(encoding="utf-8")


def plan_section(handoff: str) -> str:
    start = handoff.index("## Current plan and task graph")
    section = handoff[start:]
    following = section.find("\n## ", 10)
    return section[:following] if following != -1 else section


# --------------------------------------------------------------------------
# check-plan
# --------------------------------------------------------------------------


def test_check_plan_passes_when_report_and_graph_agree(tmp_path: Path) -> None:
    report_path, graph_path = write_report_and_graph(tmp_path)
    result = run_grid("check-plan", str(report_path), str(graph_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
    assert "РАСХОЖДЕНИЕ" not in result.stdout


def test_check_plan_names_a_task_without_a_leaf(tmp_path: Path) -> None:
    report_path, graph_path = write_report_and_graph(tmp_path)
    report_path.write_text(
        REPORT
        + "\n✅ (дополнительный лист) начата 14:20 закончена 14:25, оценка 5 минут, факт 5 минут\n",
        encoding="utf-8",
    )
    result = run_grid("check-plan", str(report_path), str(graph_path))
    assert result.returncode != 0
    assert "РАСХОЖДЕНИЕ" in result.stdout
    assert "без листа в графе" in result.stdout
    assert "дополнительный лист" in result.stdout
    assert "L05" in result.stdout


def test_check_plan_names_a_leaf_without_a_task(tmp_path: Path) -> None:
    report_path, graph_path = write_report_and_graph(tmp_path)
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    document["tasks"].append(
        {"id": "L05", "label": "приёмка в проде", "status": "queued", "depends_on": ["L03"]}
    )
    graph_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result = run_grid("check-plan", str(report_path), str(graph_path))
    assert result.returncode != 0
    assert "без задачи в отчёте" in result.stdout
    assert "приёмка в проде" in result.stdout
    assert "L05" in result.stdout


def test_check_plan_names_a_different_status(tmp_path: Path) -> None:
    report_path, graph_path = write_report_and_graph(tmp_path)
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    for task in document["tasks"]:
        if task["id"] == "L03":
            task["status"] = "queued"
    graph_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result = run_grid("check-plan", str(report_path), str(graph_path))
    assert result.returncode != 0
    assert "разные статусы" in result.stdout
    assert "L03" in result.stdout
    assert "В работе" in result.stdout
    assert "В очереди" in result.stdout


def test_check_plan_refuses_an_unreadable_report(tmp_path: Path) -> None:
    _report_path, graph_path = write_report_and_graph(tmp_path)
    broken = tmp_path / "broken.md"
    broken.write_text("просто текст без структуры отчёта\n", encoding="utf-8")
    result = run_grid("check-plan", str(broken), str(graph_path))
    assert result.returncode == 2
    assert "отчёт не распознан" in result.stderr


# --------------------------------------------------------------------------
# the 30-minute reminder
# --------------------------------------------------------------------------


def test_heartbeat_names_the_map_then_the_view_then_the_reconciliation(
    tmp_path: Path,
) -> None:
    git_repo(tmp_path)
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    guard.native_heartbeat(tmp_path, "codex", "sid-plan-graph", now=start)
    due = guard.native_heartbeat(
        tmp_path, "codex", "sid-plan-graph", now=start + timedelta(minutes=30)
    )
    assert due is not None and due["due"] == ["plan:1"]
    prompt = due["prompt"]
    assert "lhc_grid.py export" in prompt
    assert "lhc_grid.py render" in prompt
    assert "lhc_grid.py status" in prompt
    assert "lhc_grid.py check-plan" in prompt
    # The order matters: the map is refreshed first, the view is built on it.
    assert prompt.index("lhc_grid.py export") < prompt.index("lhc_grid.py render")
    assert prompt.index("lhc_grid.py render") < prompt.index("lhc_grid.py check-plan")
    assert "fix every divergence" in prompt


# --------------------------------------------------------------------------
# the compaction handoff
# --------------------------------------------------------------------------


def test_compaction_handoff_carries_the_plan_as_text_not_as_json(tmp_path: Path) -> None:
    git_repo(tmp_path)
    write_report_and_graph(tmp_path / ".agents/tasks/objective-demo")
    handoff = compact(tmp_path)
    section = plan_section(handoff)
    assert "Листья плана" in section
    assert "L01" in section
    assert "контракт источника" in section
    assert "оценка 15 мин" in section
    assert "Критический путь" in section
    # The machine artifact stays in the file; the handoff carries no JSON dump.
    assert '"schema_version"' not in handoff
    assert '"tasks"' not in handoff
    assert '"depends_on"' not in handoff


def test_compaction_handoff_reads_the_canonical_graph_not_the_report(
    tmp_path: Path,
) -> None:
    git_repo(tmp_path)
    objective = tmp_path / ".agents/tasks/objective-demo"
    _report_path, graph_path = write_report_and_graph(objective)
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    document["tasks"][0]["label"] = "графовый контракт"
    graph_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    section = plan_section(compact(tmp_path))
    assert "графовый контракт" in section


def test_compaction_handoff_says_when_the_map_is_missing(tmp_path: Path) -> None:
    git_repo(tmp_path)
    (tmp_path / ".agents/tasks").mkdir(parents=True)
    handoff = compact(tmp_path)
    assert "Plan graph not found" in handoff
    assert "## Current plan and task graph" in handoff


def test_compaction_handoff_keeps_the_plan_section_inside_its_budget(
    tmp_path: Path,
) -> None:
    git_repo(tmp_path)
    objective = tmp_path / ".agents/tasks/objective-big"
    leaves = "\n".join(
        f"⏳ (задача номер {index} с достаточно длинным названием) оценка 15 минут"
        for index in range(1, 400)
    )
    report = (
        "Цель: большая цель\n"
        "Бизнес-результат: виден результат\n"
        "Декомпозиция: 399 листьев · 1 параллельно · 1 волна · слотов: 1\n\n"
        f"{leaves}\n"
    )
    write_report_and_graph(objective, report)
    handoff = compact(tmp_path)
    section = plan_section(handoff)
    assert len(section) <= guard.MAX_HANDOFF_PLAN_CHARS + 1_000
    assert "plan text truncated" in section
    assert len(handoff) < 60_000


def test_a_nested_project_never_borrows_the_outer_projects_plan_graph(
    tmp_path: Path,
) -> None:
    outer = tmp_path / "outer-project"
    git_repo(outer)
    objective = outer / ".agents/tasks/objective-outer"
    _report_path, graph_path = write_report_and_graph(objective)
    assert graph_path.is_file()

    nested = outer / "service"
    nested.mkdir()
    git_repo(nested)

    # The nested repository has its own task records and no graph of its own.
    assert guard.find_plan_graph(nested) is None
    # The outer project still finds its own graph.
    assert guard.find_plan_graph(outer) == graph_path
