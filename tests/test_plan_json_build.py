"""One leaf, one file: the plan's source of truth and the chain it drives.

Four properties are protected here:

* the leaf file is the source of truth of its leaf, and the graph collected
  from the leaves is read by the existing reader without a single change;
* the collector is deterministic and names every leaf it cannot collect;
* writing a leaf file rebuilds the graph and the page of that plan;
* the chain stops where it should: the page the hook wrote does not feed the
  chain again.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _inprocess import load_module, run_cli


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "common" / "tools"

plan_json = load_module(TOOLS / "lhc_plan_json.py", name="lhc_plan_json_test")
lhc = load_module(TOOLS / "lhc_grid.py", name="lhc_grid_plan_json_test")
entry = load_module(TOOLS / "lhc_entry.py", name="lhc_entry_plan_json_test")
live = load_module(TOOLS / "lhc_live.py", name="lhc_live_test")


def leaf(plan_dir: Path, leaf_id: str, **fields) -> Path:
    """Write one leaf file and return its path."""

    payload = {"id": leaf_id, "label": f"Лист {leaf_id}", "status": "queued"}
    payload.update(fields)
    path = plan_dir / "leaves" / f"{leaf_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# --------------------------------------------------------------- the leaf
def test_the_leaf_file_becomes_a_task_the_existing_reader_understands(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(
        plan_dir,
        "L12",
        label="Собрать сборщик листов",
        description="Описание работы",
        acceptance="Приёмка работы",
        affected_files=["src/common/tools/lhc_plan_json.py"],
        status="running",
        owner="worker-1",
        session="mvs_1",
        harness="codex",
        model="minimax-3.1-flash",
        estimate_minutes={"minimum": 15, "maximum": 20},
        started_at="14:02",
    )
    graph_path = plan_json.build_graph(plan_dir)
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    assert document["schema_version"] == 2
    task = document["tasks"][0]
    assert task["id"] == "L12"
    assert task["label"] == "Собрать сборщик листов"
    assert task["description"] == "Описание работы"
    assert task["acceptance"] == "Приёмка работы"
    assert task["affected_files"] == ["src/common/tools/lhc_plan_json.py"]
    assert task["status"] == "running"
    assert task["owner"] == "worker-1"
    assert task["session"] == "mvs_1"
    assert task["harness"] == "codex"
    assert task["model"] == "minimax-3.1-flash"
    assert task["estimate_minutes"] == {"minimum": 15.0, "maximum": 20.0}
    assert task["started_at"] == "14:02"

    # The reader of the canon reads the collected graph without a change.
    graph = lhc.parse_graph_json(document)
    collected = graph.by_id()["L12"]
    assert collected.label == "Собрать сборщик листов"
    assert collected.status == "running"
    assert collected.estimate_min == 15
    assert collected.estimate_max == 20
    assert collected.started_at == "14:02"
    assert collected.affected_files == ["src/common/tools/lhc_plan_json.py"]
    # And the file on disk is read by the very same path the renderer uses.
    assert lhc.load_graph(graph_path).by_id()["L12"].label == "Собрать сборщик листов"


def test_the_estimate_may_be_written_in_the_short_shape(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(plan_dir, "L01", estimate={"min": 5, "max": 9})
    task = plan_json.build_document(plan_dir)["tasks"][0]
    assert task["estimate_minutes"] == {"minimum": 5.0, "maximum": 9.0}


def test_a_dependency_comes_before_the_leaf_that_waits_for_it(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(plan_dir, "L12", depends_on=["L03"])
    leaf(plan_dir, "L03")
    document = plan_json.build_document(plan_dir)
    assert [task["id"] for task in document["tasks"]] == ["L03", "L12"]
    assert document["tasks"][1]["depends_on"] == ["L03"]


def test_the_order_of_the_leaves_does_not_depend_on_the_filesystem(tmp_path):
    plan_dir = tmp_path / "plan"
    for leaf_id in ("L10", "L2", "L1"):
        leaf(plan_dir, leaf_id)
    document = plan_json.build_document(plan_dir)
    assert [task["id"] for task in document["tasks"]] == ["L1", "L2", "L10"]


def test_the_same_leaves_give_byte_for_byte_the_same_graph(tmp_path):
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12", status="running")
    first = plan_json.build_graph(plan_dir).read_bytes()
    second = plan_json.build_graph(plan_dir).read_bytes()
    assert first == second
    # A file that was written again with the same content changes nothing.
    path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    assert plan_json.build_graph(plan_dir).read_bytes() == first


# ------------------------------------------------------------- validation
def test_a_broken_leaf_is_named(tmp_path):
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    (plan_dir / "leaves" / "L12.json").write_text("{ не json", encoding="utf-8")
    with pytest.raises(plan_json.LeafError) as error:
        plan_json.build_document(plan_dir)
    assert "L12.json" in str(error.value)


def test_an_unknown_status_is_named(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(plan_dir, "L12", status="мистика")
    with pytest.raises(plan_json.LeafError) as error:
        plan_json.build_document(plan_dir)
    assert "L12.json" in str(error.value)
    assert "мистика" in str(error.value)


def test_a_dependency_on_a_missing_leaf_is_named(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(plan_dir, "L12", depends_on=["L99"])
    with pytest.raises(plan_json.LeafError) as error:
        plan_json.build_document(plan_dir)
    assert "L12.json" in str(error.value)
    assert "L99" in str(error.value)


def test_a_leaf_that_contradicts_its_own_name_is_named(tmp_path):
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12")
    path.write_text(
        json.dumps({"id": "L13", "label": "Лист"}, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(plan_json.LeafError) as error:
        plan_json.build_document(plan_dir)
    assert "L12.json" in str(error.value)


def test_the_command_line_names_the_file_it_could_not_collect(tmp_path):
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    (plan_dir / "leaves" / "L12.json").write_text("{ не json", encoding="utf-8")
    result = run_cli(plan_json, ["build", str(plan_dir)])
    assert result.returncode == 1
    assert "L12.json" in result.stderr


def test_a_plan_without_leaves_is_not_this_collectors_plan(tmp_path):
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    with pytest.raises(plan_json.LeafError) as error:
        plan_json.build_document(plan_dir)
    assert "leaves" in str(error.value)


def test_the_statuses_are_the_ones_the_existing_reader_understands():
    for status in plan_json.STATUSES:
        assert lhc.normalize_status(status) == status
    # The words of the markdown report mean the same thing in both places.
    for word in ("готово", "в_работе", "ожидание", "отложено", "заблокировано", "в_очереди"):
        assert lhc.normalize_status(word) == plan_json.STATUS_ALIASES[word]


# ----------------------------------------------------------------- the chain
def test_writing_a_leaf_rebuilds_the_graph_and_the_page(tmp_path):
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12", label="Первый заголовок")
    event = {"cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}
    assert entry.render_written_plan(event, ROOT) == plan_dir

    document = json.loads((plan_dir / "plan.graph.json").read_text(encoding="utf-8"))
    assert document["tasks"][0]["label"] == "Первый заголовок"
    html = (plan_dir / "plan.html").read_text(encoding="utf-8")
    assert "Первый заголовок" in html
    assert (plan_dir / "plan.md").is_file()


def test_the_worker_changes_only_his_own_leaf(tmp_path):
    plan_dir = tmp_path / "plan"
    leaf(plan_dir, "L01", label="Первый")
    mine = leaf(plan_dir, "L02", label="Второй")
    event = {"cwd": str(tmp_path), "tool_input": {"file_path": str(mine)}}
    entry.render_written_plan(event, ROOT)

    mine.write_text(
        json.dumps(
            {"id": "L02", "label": "Второй, закончен", "status": "done"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    entry.render_written_plan(event, ROOT)

    document = json.loads((plan_dir / "plan.graph.json").read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in document["tasks"]}
    assert by_id["L01"]["label"] == "Первый"
    assert by_id["L02"]["label"] == "Второй, закончен"
    assert by_id["L02"]["status"] == "done"


def test_the_page_the_hook_wrote_does_not_feed_the_chain_again(tmp_path):
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12", label="Первый заголовок")
    entry.render_written_plan(
        {"cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}, ROOT
    )
    html = (plan_dir / "plan.html").read_bytes()
    graph = (plan_dir / "plan.graph.json").read_bytes()

    assert entry.render_written_plan(
        {"cwd": str(tmp_path), "tool_input": {"path": str(plan_dir / "plan.html")}}, ROOT
    ) is None
    assert (plan_dir / "plan.html").read_bytes() == html
    assert (plan_dir / "plan.graph.json").read_bytes() == graph


def test_a_plan_without_leaves_keeps_the_old_behaviour(tmp_path):
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    graph = {
        "schema_version": 2,
        "title": "Старый план",
        "tasks": [{"id": "L01", "label": "Старый лист", "status": "queued"}],
    }
    (plan_dir / "plan.graph.json").write_text(
        json.dumps(graph, ensure_ascii=False), encoding="utf-8"
    )
    before = (plan_dir / "plan.graph.json").read_bytes()
    assert entry.render_written_plan(
        {"cwd": str(tmp_path), "tool_input": {"path": str(plan_dir / "plan.graph.json")}},
        ROOT,
    ) == plan_dir
    assert (plan_dir / "plan.graph.json").read_bytes() == before
    assert (plan_dir / "plan.html").is_file()


# ------------------------------------------------------------------- the page
def test_the_page_polls_its_own_file_and_swaps_the_content():
    script = live.live_script()
    assert "fetch(" in script
    assert "setInterval" in script
    assert "DOMParser" in script
    assert "2000" in script
    # One poller per page: the page refuses to start a second one.
    assert "window.__lhcLive" in script
    # The script tag of the poller must not end the script tag it lives in.
    assert "</script>" not in script


def test_the_snippet_is_inserted_once():
    html = "<html><body><p>привет</p></body></html>"
    once = live.inject_live(html)
    assert live.LIVE_SCRIPT_ID in once
    assert once.index("<script") < once.index("</body>")
    assert live.inject_live(once) == once


def test_the_poller_is_not_restarted_by_the_swap():
    script = live.live_script()
    assert live.LIVE_MARKER in live.live_snippet()
    assert "old.getAttribute" in script


def test_render_written_plan_accepts_a_str_root(tmp_path):
    """The hook may hand the root as plain text; the page still gets rebuilt.

    ``render_written_plan`` used to raise TypeError the moment ``root`` was a
    ``str`` instead of a ``Path``, so a caller that passed the root from a
    config value crashed instead of rebuilding the plan page.
    """

    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12", label="Первый заголовок")
    event = {"cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}
    assert entry.render_written_plan(event, str(ROOT)) == plan_dir
    assert (plan_dir / "plan.md").is_file()
