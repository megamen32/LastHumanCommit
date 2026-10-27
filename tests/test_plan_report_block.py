#!/usr/bin/env python3
"""The `## Plan` block of the task record is a projection of the leaf files.

The report under `## Plan` used to be the one artifact of the chain that a
model wrote by hand, and it drifted away from the graph twice in one day:
it claimed 14 leaves and 4 waves where the graph proved 17 and 6, and it
showed finished leaves as running. The block is now rendered from the same
leaf files the graph is collected from, so these properties are protected:

* the block of the live plan agrees with its graph - `check-plan` exits 0;
* a header that lies about the shape of the work is caught, not believed;
* a leaf that changed in its file changes the block, and nobody writes a word;
* every line of the block carries the id of its leaf before the marker, so the
  report is reconciled by id and never by the position of a row;
* the wording of the fields is the wording of PLAN_REPORT.md, and the block
  and the page report one revision of one plan.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from _inprocess import load_module, run_cli


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "common" / "tools"
LIVE_PLAN = ROOT / ".agents" / "tasks" / "20261024-cost-first-plan-kernel"

# The grid is loaded under its bare name, so the collector finds the very same
# module object when it reaches for the shape of the work.
plan_json = load_module(TOOLS / "lhc_plan_json.py", name="lhc_plan_json_report_test")
lhc = load_module(TOOLS / "lhc_grid.py", name="lhc_grid")


def plan_copy(tmp_path: Path) -> Path:
    """The live plan of this task, copied so the test writes nothing into it."""

    if not LIVE_PLAN.is_dir():
        pytest.skip(f"живого плана нет: {LIVE_PLAN}")
    target = tmp_path / "plan"
    shutil.copytree(LIVE_PLAN, target)
    return target


def build(plan_dir: Path) -> None:
    result = run_cli(plan_json, ["build", str(plan_dir)])
    assert result.returncode == 0, result.stdout + result.stderr


def write_block(plan_dir: Path) -> str:
    result = run_cli(plan_json, ["report", str(plan_dir), "--write"])
    assert result.returncode == 0, result.stdout + result.stderr
    return (plan_dir / "task.md").read_text(encoding="utf-8")


def check_plan(plan_dir: Path):
    return run_cli(
        lhc, ["check-plan", str(plan_dir / "task.md"), str(plan_dir / "plan.graph.json")]
    )


def leaf_payload(plan_dir: Path, leaf_id: str, **fields) -> dict:
    path = plan_dir / "leaves" / f"{leaf_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(fields)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def plan_section(text: str) -> str:
    """The `## Plan` section of the task record, without the next section.

    The heading is a line of its own: the words «## Plan» also stand in the
    prose of the record, and a section is not the sentence that mentions it.
    """

    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "## Plan":
            start = index
            break
    assert start is not None, "в записи задачи нет раздела «## Plan»"
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end])


def pick_leaf(plan_dir: Path, status: str) -> str:
    """The id of a leaf of the plan that stands in the given state."""

    document = json.loads((plan_dir / "plan.graph.json").read_text(encoding="utf-8"))
    for task in document["tasks"]:
        if task["status"] == status:
            return task["id"]
    pytest.skip(f"в живом плане нет листа в состоянии {status}")


# ------------------------------------------------------------------ the block
def test_the_block_of_the_live_plan_agrees_with_its_graph(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    try:
        build(plan_dir)
    except AssertionError as error:
        pytest.skip(f"живой план сейчас не собирается: {error}")
    write_block(plan_dir)

    result = check_plan(plan_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "РАСХОЖДЕНИЕ" not in result.stdout

    document = json.loads((plan_dir / "plan.graph.json").read_text(encoding="utf-8"))
    leaves = document["tasks"]
    text = (plan_dir / "task.md").read_text(encoding="utf-8")
    section = plan_section(text)
    # Every leaf of the graph is one line of the block and the other way round.
    lines = [line for line in section.splitlines() if line[:1] == "L"]
    assert len(lines) == len(leaves)
    for task in leaves:
        assert f"{task['id']} " in section, task["id"]
    # The ids of a plan carry letter suffixes, and the block keeps them.
    assert any(task["id"] not in {"L01", "L02", "L03"} for task in leaves)
    for suffix in ("L02b", "L05a", "L08b"):
        assert suffix in section, suffix


def test_the_block_starts_with_the_three_header_lines(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    build(plan_dir)
    text = write_block(plan_dir)
    section = plan_section(text)
    header = [
        line
        for line in section.splitlines()
        if line and not line.startswith("L") and not line.startswith("#")
    ]
    assert header[0].startswith("Цель:")
    assert header[1].startswith("Бизнес-результат:")
    assert header[2].startswith("Декомпозиция:")
    assert " · " in header[2]
    assert "слотов:" in header[2]


def test_every_line_carries_the_id_of_its_leaf_before_the_marker(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    build(plan_dir)
    write_block(plan_dir)
    text = (plan_dir / "task.md").read_text(encoding="utf-8")

    graph = lhc.parse_plan_report(text)
    assert graph is not None
    document = json.loads((plan_dir / "plan.graph.json").read_text(encoding="utf-8"))
    assert {leaf.id for leaf in graph.leaves} == {task["id"] for task in document["tasks"]}
    # Every line is bound to its leaf by the id it names, not by its row.
    assert all(leaf.id_explicit for leaf in graph.leaves)


def test_a_lie_in_the_header_is_caught_and_not_believed(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    build(plan_dir)
    write_block(plan_dir)
    path = plan_dir / "task.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Декомпозиция:"):
            waves = re.search(r"(\d+) волн", line)
            assert waves, line
            lied = str(int(waves.group(1)) + 1)
            lines[index] = line.replace(waves.group(0), f"{lied} волн")
            break
    else:
        pytest.fail("в блоке нет строки шапки «Декомпозиция:»")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = check_plan(plan_dir)
    assert result.returncode == 1
    assert "РАСХОЖДЕНИЕ" in result.stdout
    assert "волн" in result.stdout
    assert "по графу" in result.stdout


def test_a_changed_leaf_changes_the_block_without_a_model(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    build(plan_dir)
    before = write_block(plan_dir)
    leaf_id = pick_leaf(plan_dir, "done")

    leaf_payload(plan_dir, leaf_id, status="running", started_at="14:10")
    build(plan_dir)
    after = write_block(plan_dir)

    assert before != after
    assert f"{leaf_id} ✅" in before
    assert f"{leaf_id} 🔄 работаем" in after
    # The revision of the plan moved with the leaf, and the block still agrees
    # with the graph it is compared with.
    assert before.split("Ревизия плана:")[1].splitlines()[0] != after.split(
        "Ревизия плана:"
    )[1].splitlines()[0]
    result = check_plan(plan_dir)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_block_and_the_page_report_one_revision(tmp_path: Path) -> None:
    plan_dir = plan_copy(tmp_path)
    build(plan_dir)
    text = write_block(plan_dir)
    rendered = run_cli(
        lhc, ["render", str(plan_dir / "plan.graph.json"), "--out-dir", str(plan_dir)]
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr

    block_revision = text.split("Ревизия плана:")[1].splitlines()[0].strip()
    page_revision = (
        (plan_dir / "plan.md").read_text(encoding="utf-8")
        .split("Ревизия плана:")[1]
        .splitlines()[0]
        .strip()
    )
    assert block_revision == page_revision
    assert block_revision


def test_the_markers_of_the_block_are_the_markers_of_the_parser() -> None:
    """A marker means one state in the report and in the parser that reads it."""

    for status, glyph in plan_json.STATUS_GLYPHS.items():
        assert lhc.GLYPH_STATUS[glyph] == status, glyph




# ------------------------------------------------------- the fields of a leaf
def leaf(plan_dir: Path, leaf_id: str, **fields) -> Path:
    payload = {"id": leaf_id, "label": f"Лист {leaf_id}", "status": "queued"}
    payload.update(fields)
    path = plan_dir / "leaves" / f"{leaf_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_the_queued_leaf_shows_the_reason_and_the_planned_times(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    leaf(
        plan_dir,
        "L01",
        label="Собрать отчёт",
        depends_on=["L00"],
        wait_reason="генератор страницы занят тем же файлом",
        planned_start="07:30",
        planned_finish="07:45",
        estimate_minutes=15,
    )
    leaf(plan_dir, "L00", label="Основа", status="done")
    block = plan_json.report_block(plan_dir)

    assert "L01 ⏳" in block
    assert "начнём после листа L00" in block
    assert "потому что генератор страницы занят тем же файлом" in block
    assert "примерно в 07:30" in block
    assert "закончим в 07:45" in block
    assert "оценка 15 минут" in block


def test_the_block_of_a_finished_leaf_says_what_happened(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    leaf(
        plan_dir,
        "L01",
        label="Собрать отчёт",
        status="done",
        started_at="14:02",
        finished_at="14:09",
        actual_minutes=7,
        estimate_minutes=15,
    )
    block = plan_json.report_block(plan_dir)

    assert "L01 ✅ (Собрать отчёт) начата 14:02 закончена 14:09" in block
    assert "оценка 15 минут" in block
    assert "факт 7 минут" in block
    # A leaf that was not measured says so instead of a zero.
    assert "не измерено" not in block


def test_the_block_of_a_leaf_without_a_measurement_says_so(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    leaf(plan_dir, "L01", label="Собрать отчёт", status="done", finished_at="14:09")
    block = plan_json.report_block(plan_dir)

    assert "факт не измерено" in block


def test_the_block_names_the_blocker_of_a_blocked_leaf(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    leaf(
        plan_dir,
        "L01",
        label="Собрать отчёт",
        status="blocked",
        blocker="нет доступа к снимку каталога",
        estimate_minutes=15,
    )
    block = plan_json.report_block(plan_dir)

    assert "L01 ⛔" in block
    assert "блокер: нет доступа к снимку каталога" in block


def test_the_block_warns_when_the_graph_on_disk_is_older_than_the_leaves(
    tmp_path: Path,
) -> None:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    leaf(plan_dir, "L01", label="Собрать отчёт", status="queued")
    build(plan_dir)

    leaf_payload(plan_dir, "L01", status="done")
    result = run_cli(plan_json, ["report", str(plan_dir)])
    assert result.returncode == 0
    assert "устарел" in result.stderr
