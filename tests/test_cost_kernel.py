"""Tests for the cost kernel of the plan: price, tokens, slots and waits.

What these cases protect, in the owner's words: «сколько план стоит» must be
readable by a human without an LLM, and every number in that reading must say
where it came from. So the cases here are the acceptance of leaf L03:

* a plan of two leaves - one simple on the cheap class, one complex on the
  frontier - shows the cost of each leaf, the cost of the whole plan and the
  frontier share of the dollars, and every one of those figures carries the
  label of its source (``measured`` or ``provisional``);
* a leaf that declares no cost cannot disappear quietly: ``validate`` says
  where the figure came from and that the leaf has none of its own;
* a leaf without a chosen model says «модель не выбрана» and never $0.00;
* swapping the catalog snapshot moves the price and nothing else - the list
  of models stays in the catalog, not in the code;
* a slot is a pair of hands: one executor holding two leaves is one busy
  executor, and only more distinct owners than slots is an overload;
* the progress row separates the leaves that wait for a predecessor from the
  leaves that wait only for an executor, and «заблокировано» still counts the
  leaves whose status says blocked.

The catalog and the measured token-burn table are fixtures: the prices and
the rates under test are written by the test, never by the production code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _inprocess import load_module, run_cli


ROOT = Path(__file__).resolve().parent.parent
GRID_TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"
MODELS_TOOL = ROOT / "src" / "common" / "tools" / "lhc_models.py"


def load_tool(path, name):
    return load_module(path, name=name)


lhc = load_tool(GRID_TOOL, "lhc_grid")
models = load_tool(MODELS_TOOL, "lhc_models")


# --------------------------------------------------------------------- fixtures


def mk_model(model_id, name, *, input_price, output_price, context=1_000_000):
    return {
        "id": model_id,
        "name": name,
        "tool_call": True,
        "reasoning": True,
        "structured_output": True,
        "attachment": False,
        "open_weights": False,
        "temperature": True,
        "limit": {"context": context, "output": 32_000},
        "modalities": {"input": ["text"], "output": ["text"]},
        "cost": {"input": input_price, "output": output_price},
    }


def write_catalog(path: Path, *, frontier_model="acme-pro-1", frontier_price=3.0) -> Path:
    """A small models.dev-shaped catalog: one flash route, one frontier route.

    The ids are invented on purpose: a model the code has never seen must be
    selectable, because the list of models is data and lives in the catalog.
    """

    payload = {
        "acme": {
            "id": "acme",
            "name": "Acme",
            "models": {
                "acme-flash-1": mk_model("acme-flash-1", "Acme Flash 1",
                                         input_price=0.10, output_price=0.40),
                "acme-mid-1": mk_model("acme-mid-1", "Acme Mid 1",
                                       input_price=0.50, output_price=1.50),
                frontier_model: mk_model(frontier_model, "Acme Frontier 1",
                                         input_price=frontier_price,
                                         output_price=frontier_price * 2),
            },
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def write_measured(path: Path, *, fast_rate=373_609, fast_samples=(322_436, 359_243, 373_609, 848_146),
                   frontier_rate=622_397, frontier_samples=(622_397,)) -> Path:
    """The pinned token-burn table: one entry per class, with its samples."""

    payload = {
        "version": 1,
        "measured_at": "2026-10-24T05:57",
        "source": "замер исполнителей плана",
        "tiers": {
            "fast": {
                "tokens_per_minute": fast_rate,
                "samples": list(fast_samples),
                "note": "четыре пробы исполнителей",
            },
            "frontier": {
                "tokens_per_minute": frontier_rate,
                "samples": list(frontier_samples),
                "note": "одна проба",
            },
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def write_plan(path: Path, tasks, *, slots=4) -> Path:
    document = {"schema_version": 2, "title": "Смета", "goal": "проверка сметы",
                "slots": slots, "tasks": tasks}
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def run_grid(*args, catalog, measured, cwd=None):
    env = {"LHC_CATALOG_FILE": str(catalog), "LHC_TPM_MEASURED_FILE": str(measured)}
    return run_cli(lhc, list(args), env=env, cwd=cwd)


@pytest.fixture
def catalog(tmp_path):
    return write_catalog(tmp_path / "api.json")


@pytest.fixture
def measured(tmp_path):
    return write_measured(tmp_path / "tpm-measured.json")


@pytest.fixture
def two_leaf_plan(tmp_path):
    """One simple leaf on the cheap class, one complex leaf on the frontier."""

    return write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lsimple", "label": "Простая работа", "status": "queued",
         "owner": "worker-a", "tier": "fast", "complexity": "S",
         "estimate_minutes": 15},
        {"id": "Lcomplex", "label": "Сложная работа", "status": "queued",
         "owner": "worker-b", "tier": "frontier", "complexity": "L",
         "estimate_minutes": 15},
    ])


# ------------------------------------------------- 1. the money and its labels


def test_two_leaf_plan_shows_every_leaf_the_total_and_the_frontier_share(
        catalog, measured, two_leaf_plan):
    result = run_grid("status", str(two_leaf_plan), catalog=catalog, measured=measured)
    assert result.returncode == 0, result.stderr
    text = result.stdout

    # Each leaf carries its own money and the label of the rate behind it.
    assert "стоимость $" in text
    assert "цена measured" in text
    assert "скорость 373 609 ток/мин measured" in text
    assert "скорость 622 397 ток/мин measured" in text
    # The plan carries the total and the frontier share of the dollars.
    assert "Смета плана: $" in text
    assert "всех долларов плана" in text
    # And every one of those figures says where it came from.
    assert "(measured)" in text

    payload = json.loads(run_grid("validate", str(two_leaf_plan),
                                  catalog=catalog, measured=measured).stdout)
    assert payload["cost"]["available"] is True
    assert payload["cost"]["total_usd"] > 0
    assert payload["cost"]["frontier_usd"] > 0
    assert 0 < payload["cost"]["frontier_share_pct"] < 100
    assert payload["cost"]["priced_count"] == 2


def test_a_class_without_a_measurement_is_labelled_provisional_next_to_the_money(
        catalog, tmp_path):
    """A leaf priced by the old constants says so next to its figure."""

    table = tmp_path / "tpm-measured.json"
    table.write_text(json.dumps(
        {"tiers": {"fast": {"tokens_per_minute": 373_609, "samples": [373_609]}}}),
        encoding="utf-8")
    plan = write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lsimple", "label": "Простая работа", "status": "queued",
         "owner": "worker-a", "tier": "fast", "complexity": "S", "estimate_minutes": 15},
        {"id": "Lcomplex", "label": "Сложная работа", "status": "queued",
         "owner": "worker-b", "tier": "frontier", "complexity": "L", "estimate_minutes": 15},
    ])
    text = run_grid("status", str(plan), catalog=catalog, measured=table).stdout
    assert "цена measured" in text
    assert "цена provisional" in text
    # The plan total stands on both, and says so.
    assert "(measured+provisional)" in text


def test_the_frontier_share_is_counted_in_dollars_not_in_leaves(
        catalog, measured, tmp_path):
    """Five cheap leaves against one expensive one is not «20% frontier»."""

    tasks = [{"id": f"Lcheap{index}", "label": "Дешёвая работа", "status": "queued",
              "owner": f"worker-{index}", "tier": "fast", "complexity": "S",
              "estimate_minutes": 15} for index in range(5)]
    tasks.append({"id": "Lrich", "label": "Дорогая работа", "status": "queued",
                  "owner": "worker-x", "tier": "frontier", "complexity": "L",
                  "estimate_minutes": 15})
    plan = write_plan(tmp_path / "plan.graph.json", tasks)
    payload = json.loads(run_grid("validate", str(plan), catalog=catalog,
                                  measured=measured).stdout)
    cost = payload["cost"]
    assert cost["frontier_count"] == 1
    assert cost["fast_count"] == 5
    # The share follows the dollars, so the one expensive leaf carries the
    # share even though it is one leaf of six.
    assert cost["frontier_share_pct"] > 50


def test_the_html_dashboard_shows_the_same_numbers_with_their_labels(
        catalog, measured, two_leaf_plan, tmp_path):
    html = tmp_path / "plan.html"
    markdown = tmp_path / "plan.md"
    result = run_grid("render", str(two_leaf_plan), "-o", str(html),
                      "--markdown", str(markdown), catalog=catalog, measured=measured)
    assert result.returncode == 0, result.stderr
    page = html.read_text(encoding="utf-8")
    summary = markdown.read_text(encoding="utf-8")

    payload = json.loads(run_grid("validate", str(two_leaf_plan),
                                  catalog=catalog, measured=measured).stdout)
    total = payload["cost"]["total_usd"]
    frontier = payload["cost"]["frontier_usd"]
    assert f"${total:.2f}" in page
    assert f"${frontier:.2f}" in page
    # The label stands next to the figure, in the page and in the summary.
    assert "measured" in page
    assert "measured" in summary
    assert f"${total:.2f}" in summary


# ------------------------------------- 2. a leaf without a cost is not silent


def test_validate_says_where_the_number_came_from_when_the_leaf_declares_none(
        catalog, measured, two_leaf_plan):
    payload = json.loads(run_grid("validate", str(two_leaf_plan),
                                  catalog=catalog, measured=measured).stdout)
    warnings = " ".join(payload["warnings"])
    assert "не объявили свою стоимость" in warnings
    assert "Lsimple" in warnings and "Lcomplex" in warnings
    assert "снимку каталога" in warnings
    # The classes and the label of the rate are named too.
    assert "fast measured" in warnings
    assert "frontier measured" in warnings


def test_a_leaf_that_declares_its_own_cost_says_so_in_the_warning(
        catalog, measured, tmp_path):
    plan = write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lown", "label": "Своя цифра", "status": "queued", "owner": "worker-a",
         "tier": "fast", "complexity": "S", "estimate_minutes": 15,
         "cost_usd": 1.25, "cost_source": "measured"},
    ])
    payload = json.loads(run_grid("validate", str(plan), catalog=catalog,
                                  measured=measured).stdout)
    warnings = " ".join(payload["warnings"])
    assert "не объявили свою стоимость" not in warnings


# ----------------------------------------- 3. the model comes from the catalog


def test_a_leaf_without_a_model_says_the_model_is_not_chosen(
        catalog, measured, tmp_path):
    plan = write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lnoun", "label": "Без класса", "status": "queued", "owner": "worker-a",
         "estimate_minutes": 15},
    ])
    result = run_grid("status", str(plan), catalog=catalog, measured=measured)
    assert "модель не выбрана" in result.stdout
    # A leaf with no chosen model is not a cheap leaf: it carries no money at
    # all, and the plan says so instead of drawing a zero.
    assert "стоимость $0.00" not in result.stdout
    # The plan total is an unknown number of dollars, not zero dollars.
    assert "нет посчитанных денег" in result.stdout
    assert "$0.0000" not in result.stdout
    payload = json.loads(run_grid("validate", str(plan), catalog=catalog,
                                  measured=measured).stdout)
    assert payload["cost"]["unpriced_ids"] == ["Lnoun"]
    assert payload["cost"]["priced_count"] == 0


def test_swapping_the_catalog_moves_the_price_and_nothing_else(
        catalog, measured, two_leaf_plan, tmp_path):
    """The tokens come from the measurement; only the price comes from the catalog."""

    first = json.loads(run_grid("validate", str(two_leaf_plan),
                                catalog=catalog, measured=measured).stdout)
    other = write_catalog(tmp_path / "other.json", frontier_model="acme-ultra-1",
                          frontier_price=30.0)
    second = json.loads(run_grid("validate", str(two_leaf_plan),
                                 catalog=other, measured=measured).stdout)
    assert first["cost"]["frontier_usd"] != second["cost"]["frontier_usd"]
    assert second["cost"]["frontier_usd"] > first["cost"]["frontier_usd"]

    # The token estimate did not move with the price: it comes from the
    # measured table, not from the catalog.
    first_text = run_grid("status", str(two_leaf_plan), catalog=catalog,
                           measured=measured).stdout
    second_text = run_grid("status", str(two_leaf_plan), catalog=other,
                            measured=measured).stdout

    def parts(text, needle):
        return [part.strip()
                for line in text.splitlines() if "стоимость $" in line
                for part in line.split("·") if needle in part]

    assert parts(first_text, "токенов") == parts(second_text, "токенов")
    assert parts(first_text, "скорость") == parts(second_text, "скорость")
    # The money of the frontier leaf did move, and it moved with the catalog.
    assert parts(first_text, "стоимость $") != parts(second_text, "стоимость $")


def test_the_catalog_holds_the_models_and_not_the_code():
    """No price and no model list is written into the kernel."""

    for path in (GRID_TOOL, MODELS_TOOL):
        source = path.read_text(encoding="utf-8")
        assert "acme-flash-1" not in source
        assert "acme-pro-1" not in source
        assert "373609" not in source and "373_609" not in source
        assert "622397" not in source and "622_397" not in source


# ---------------------------------------------- 4. slots are counted by hands


def test_one_executor_holding_two_leaves_is_one_busy_executor(
        catalog, measured, tmp_path):
    plan = write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lone", "label": "Первый", "status": "running", "owner": "worker-a",
         "tier": "fast", "complexity": "S", "estimate_minutes": 15},
        {"id": "Ltwo", "label": "Второй", "status": "running", "owner": "worker-a",
         "tier": "fast", "complexity": "S", "estimate_minutes": 15},
    ], slots=4)
    text = run_grid("status", str(plan), catalog=catalog, measured=measured).stdout
    assert "Исполнители: занято 1 из 4 слотов" in text
    assert "исполнителей больше, чем слотов" not in text
    # The number of running leaves is still shown, and it is a different
    # number from the number of busy executors.
    assert "Параллельность: сейчас 2 из 4 слотов" in text


def test_overload_is_only_declared_when_owners_outnumber_the_slots(
        catalog, measured, tmp_path):
    tasks = [{"id": f"L{index}", "label": "Работа", "status": "running",
              "owner": f"worker-{index}", "tier": "fast", "complexity": "S",
              "estimate_minutes": 15} for index in range(5)]
    plan = write_plan(tmp_path / "plan.graph.json", tasks, slots=4)
    text = run_grid("status", str(plan), catalog=catalog, measured=measured).stdout
    assert "Исполнители: занято 5 из 4 слотов" in text
    assert "исполнителей больше, чем слотов" in text


# ------------------------------------------- 5. the progress row and its waits


def test_the_progress_row_separates_the_two_waits_and_keeps_blocked(
        catalog, measured, tmp_path):
    plan = write_plan(tmp_path / "plan.graph.json", [
        {"id": "Lblocked", "label": "Заблокирован", "status": "blocked",
         "owner": "worker-a", "tier": "fast", "complexity": "S",
         "estimate_minutes": 15},
        {"id": "Lparent", "label": "Предок", "status": "running", "owner": "worker-b",
         "tier": "fast", "complexity": "S", "estimate_minutes": 15},
        {"id": "Lchild", "label": "Наследник", "status": "queued", "owner": "worker-c",
         "tier": "fast", "complexity": "S", "estimate_minutes": 15,
         "depends_on": ["Lparent"]},
        {"id": "Lsame", "label": "Тот же исполнитель", "status": "queued",
         "owner": "worker-b", "tier": "fast", "complexity": "S",
         "estimate_minutes": 15},
    ], slots=4)
    text = run_grid("status", str(plan), catalog=catalog, measured=measured).stdout
    progress = [line for line in text.splitlines() if line.startswith("Прогресс")][0]
    # «заблокировано» still counts the leaves whose status says blocked.
    assert "заблокировано 1" in progress
    # The leaf behind an unfinished predecessor and the leaf that only waits
    # for an executor are two different problems, and the row says so.
    assert "ждёт листа 1" in progress
    assert "ждёт исполнителя 1" in progress


# ------------------------------------------------- the measured rate is data


def test_the_rate_comes_from_the_pinned_table_and_keeps_its_label(tmp_path):
    table = write_measured(tmp_path / "tpm-measured.json")
    loaded = models.load_measured_tpm(table)
    assert loaded["fast"]["tokens_per_minute"] == 373_609
    assert loaded["fast"]["samples"] == 4
    assert loaded["frontier"]["tokens_per_minute"] == 622_397
    assert loaded["frontier"]["samples"] == 1
    fast = models.tpm_for_tier("fast", measured=loaded)
    assert fast["label"] == "measured"
    assert fast["tokens_per_minute"] == 373_609


def test_a_class_without_a_measurement_is_priced_provisionally(tmp_path):
    table = tmp_path / "tpm-measured.json"
    table.write_text(json.dumps({"tiers": {"fast": {"tokens_per_minute": 1000}}}),
                     encoding="utf-8")
    loaded = models.load_measured_tpm(table)
    assert "frontier" not in loaded
    frontier = models.tpm_for_tier("frontier", measured=loaded)
    assert frontier["label"] == "provisional"
    assert frontier["tokens_per_minute"] == models.PROVISIONAL_TPM["frontier"]


def test_a_table_of_samples_without_a_rate_takes_the_median(tmp_path):
    table = tmp_path / "tpm-measured.json"
    table.write_text(json.dumps(
        {"tiers": {"fast": {"samples": [100, 200, 300, 400]}}}), encoding="utf-8")
    loaded = models.load_measured_tpm(table)
    assert loaded["fast"]["tokens_per_minute"] == 250
    assert loaded["fast"]["samples"] == 4


def test_a_new_measurement_is_recorded_without_editing_the_code(tmp_path):
    out = tmp_path / "tpm-measured.json"
    result = run_cli(models, ["tpm", "--class", "fast", "--samples", "100,200,300",
                              "--note", "три пробы", "--out", str(out)])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tokens_per_minute"] == 200
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["tiers"]["fast"]["samples"] == [100, 200, 300]
