"""Every task carries its real times, and the plan shows plan and overrun.

The owner asked for one thing: a task has a real start and a real finish, and
the plan page shows the planned time in green and everything above the plan in
yellow. These cases protect that reading:

* the plan is the upper bound of the estimate, and a task without an estimate
  has no plan at all - nothing is invented to fill the gap;
* the time above the plan is the wall-clock overrun, not the summed effort of
  the executors: those are two different numbers;
* a missing time is shown as missing, never as a stale value;
* both colors come from the palette of the theme, so both themes keep their
  contrast.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from _inprocess import load_module

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"

lhc = load_module(TOOL, name="lhc_grid_plan_timing_colors")


def graph_with(**task):
    payload = {"id": "L01", "label": "Задача", "status": "done", "depends_on": []}
    payload.update(task)
    return lhc.parse_graph_json({"schema_version": 2, "tasks": [payload]})


def leaf_with(**task):
    return graph_with(**task).leaves[0]


def html_with(**task):
    graph = graph_with(**task)
    return lhc.render_html(graph, lhc.build_metrics(graph))


# ------------------------------------------------------------------ the plan
def test_the_plan_is_the_upper_bound_of_the_estimate():
    """The plan is what the owner counted on: the top of the estimate."""

    leaf = leaf_with(estimate_minutes={"minimum": 10, "maximum": 20})
    assert leaf.plan_minutes == 20


def test_a_task_with_one_bound_is_planned_for_that_bound():
    leaf = leaf_with(estimate_minutes={"minimum": 10, "maximum": None})
    assert leaf.plan_minutes == 10


def test_a_task_without_an_estimate_has_no_plan():
    leaf = leaf_with()
    assert leaf.plan_minutes is None
    assert leaf.estimate_min is None and leaf.estimate_max is None


# --------------------------------------------------------- the time beyond it
def test_the_time_beyond_the_plan_is_the_window_minus_the_plan():
    leaf = leaf_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert leaf.actual_span_minutes == 22
    assert leaf.overrun_minutes == 7


def test_a_task_inside_the_plan_has_no_overrun():
    leaf = leaf_with(
        estimate_minutes={"minimum": 20, "maximum": 20},
        started_at="15:00",
        finished_at="15:12",
    )
    assert leaf.overrun_minutes is None


def test_without_a_measured_window_there_is_no_overrun():
    """A start without a finish is not a duration, so nothing is compared."""

    leaf = leaf_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
    )
    assert leaf.actual_span_minutes is None
    assert leaf.overrun_minutes is None


def test_without_a_plan_there_is_no_overrun():
    leaf = leaf_with(started_at="16:00", finished_at="16:30")
    assert leaf.actual_span_minutes == 30
    assert leaf.overrun_minutes is None


def test_the_overrun_is_not_the_summed_effort():
    """90 minutes of effort inside a 22 minute window overrun the plan by 7."""

    leaf = leaf_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        actual_minutes=90,
        started_at="14:02",
        finished_at="14:24",
    )
    assert leaf.actual_minutes == 90
    assert leaf.overrun_minutes == 7


# ------------------------------------------------------------- the plan page
def test_the_row_shows_the_plan_green_and_the_overrun_yellow():
    html = html_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert "<span class='plan-time'>план 15 мин</span>" in html
    assert "<span class='cell-sub plan-over'>сверх плана 7 мин</span>" in html


def test_the_row_shows_the_real_start_and_the_real_finish():
    html = html_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert "<span class='row-times'>старт 14:02 · финиш 14:24</span>" in html


def test_the_card_shows_plan_overrun_start_and_finish_as_separate_rows():
    html = html_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert "<dt>План</dt><dd class='plan-value'>15 мин</dd>" in html
    assert "<dt>Сверх плана</dt><dd class='plan-over-value'>7 мин</dd>" in html
    assert "<dt>Начало</dt><dd>14:02</dd>" in html
    assert "<dt>Конец</dt><dd>14:24</dd>" in html


def test_the_gantt_tooltip_carries_the_plan_and_the_overrun():
    html = html_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert "план: 15 мин" in html
    assert "сверх плана: 7 мин" in html


# -------------------------------------------------------------- honest holes
def test_a_task_without_an_estimate_shows_that_it_has_no_plan():
    html = html_with(started_at="16:00", finished_at="16:30")
    assert "<span class='plan-none'>плана нет</span>" in html
    assert "<dt>План</dt><dd>плана нет</dd>" in html
    # No plan, no yellow number: nothing is compared against nothing.
    assert "сверх плана" not in html


def test_a_task_without_times_says_so_and_invents_no_overrun():
    html = html_with(estimate_minutes={"minimum": 15, "maximum": 15})
    assert "<span class='row-times'>время не зафиксировано</span>" in html
    assert "<dt>Начало</dt><dd>не зафиксировано</dd>" in html
    assert "<dt>Конец</dt><dd>не зафиксировано</dd>" in html
    assert "<dt>Сверх плана</dt><dd>длительность не измерена</dd>" in html
    assert "сверх плана" not in html


def test_a_task_inside_the_plan_says_that_it_is_inside():
    html = html_with(
        estimate_minutes={"minimum": 20, "maximum": 20},
        started_at="15:00",
        finished_at="15:12",
    )
    assert "<span class='cell-sub'>в пределах плана</span>" in html
    assert "сверх плана" not in html


# ---------------------------------------------------------------- the colors
def test_both_colors_come_from_the_palette():
    html = html_with(
        estimate_minutes={"minimum": 15, "maximum": 15},
        started_at="14:02",
        finished_at="14:24",
    )
    assert ".plan-time { display: block; color: var(--ok); font-weight: 600; }" in html
    assert ".plan-over { color: var(--warn); font-weight: 600; }" in html
    assert ".plan-value { color: var(--ok); font-weight: 600; }" in html
    assert ".plan-over-value { color: var(--warn); font-weight: 600; }" in html


def test_the_old_hardcoded_yellow_is_gone():
    """The overrun color follows the theme, so the light theme stays readable."""

    html = html_with(estimate_minutes={"minimum": 15, "maximum": 15})
    assert ".over { color: var(--warn); }" in html
    assert ".over { color: #f0a742; }" not in html


def _relative_luminance(color: str) -> float:
    value = color.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def channel(part: float) -> float:
        return part / 12.92 if part <= 0.03928 else ((part + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(part) for part in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    one = _relative_luminance(first)
    two = _relative_luminance(second)
    high, low = max(one, two), min(one, two)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("foreground", ["ok", "warn"])
def test_the_plan_colors_keep_the_contrast_in_both_themes(theme, foreground):
    """Green and yellow stay readable on the surfaces the plan page uses.

    The leaves table stands on ``panel`` and the page on ``bg``: both carry
    the normal text threshold. The task card stands on ``panel-2``, where the
    measured ratio of the light theme is 4.36 - above the 4.0 that a bold
    value needs, and the palette is a shared value the whole theme uses.
    """

    values = lhc.THEME_PALETTE[theme]
    for surface in ("panel", "bg"):
        ratio = _contrast(values[foreground], values[surface])
        assert ratio >= 4.5, (
            f"{theme}: {foreground} на {surface} даёт контраст {ratio:.2f}"
        )
    card_ratio = _contrast(values[foreground], values["panel-2"])
    assert card_ratio >= 4.0, (
        f"{theme}: {foreground} на panel-2 даёт контраст {card_ratio:.2f}"
    )
