"""Tests for the delivery-side renderer of a plan.

The product renders the audit data of a finished audit page: what was
checked, what was concluded, what is left to do and what exactly goes to
the executor. The rules these tests protect:

* every field of the input is on the page — a field with no home is a bug,
  not a reason to drop it;
* the counts of the page match the counts of the input;
* a value from the data is escaped, never rendered raw;
* the fragment is embeddable: it is a fragment, and it is balanced.

A fix without a test is a fix that comes back.
"""

from __future__ import annotations

import html as html_module
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_product.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("lhc_product", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lhc = load_tool()


# --------------------------------------------------------------------------
# the data under test
# --------------------------------------------------------------------------

AUDIT_DATA_CANDIDATES = (
    ROOT.parent / "airlock-audit" / "audit-data.json",
    ROOT / ".tmp" / "airlock-audit" / "audit-data.json",
    ROOT.parent.parent / "airlock-audit" / "audit-data.json",
)


def synthetic_audit_data() -> dict:
    """A stand-in with the shape of the real audit data.

    It is used when the real audit file is not next to the checkout, so the
    contract of the renderer is checked either way.
    """

    return {
        "schemaVersion": 1,
        "reportId": "synthetic-audit-20261022",
        "auditDateLabel": "22 октября 2026 · срез на 16:29 МСК",
        "title": "Основа реализована. Полный процесс ещё нужно довести до приёмки.",
        "lead": "Найдены работающие сервисы и существенная реализация.",
        "method": "Чтение текущего кода, журналов версий и состояния сервисов.",
        "planStart": "2026-10-23",
        "specUrl": "https://example.invalid/space/page_synthetic",
        "specText": "# Первая версия дашборда задач\n\nРабочая спецификация.",
        "coverageNote": "Матрица содержит 2 требования.",
        "estimateNote": "Оценки в инженерных часах, 1 рабочий день = 8 часов.",
        "summary": [
            {
                "status": "ready",
                "label": "Уже реализовано",
                "title": "Переиспользовать готовые части",
                "items": ["Канонический Todo.", "Каталог Airlock Plan."],
                "sources": ["S01", "S02"],
            },
            {
                "status": "missing",
                "label": "Подтверждённые разрывы",
                "title": "Соединить вход с автозапуском",
                "items": ["Вход и автозапуск не соединены."],
                "sources": ["S02"],
            },
        ],
        "notes": [
            {
                "type": "blue",
                "title": "Новый дашборд с нуля не нужен.",
                "text": "IntegratorTaskDashboard уже есть в каноническом Todo.",
                "sources": ["S01"],
            },
            {
                "type": "normal",
                "title": "Обычное замечание",
                "text": "Текст замечания.",
                "sources": ["S02"],
            },
        ],
        "requirements": [
            {
                "id": "R01",
                "component": "Секретарь / доска",
                "title": "Разделять явное поручение и идею",
                "status": "ready",
                "proof": "Подтверждено в canonical admission-коде",
                "found": "Есть explicit-task / idea / ambiguous.",
                "remaining": "Подключить это правило ко всем входам.",
                "sources": ["S01"],
                "tasks": ["W01"],
            },
            {
                "id": "R02",
                "component": "Приёмка",
                "title": "Ручная приёмка владельцем",
                "status": "missing",
                "proof": "",
                "found": "Наблюдаемого runtime нет.",
                "remaining": "Собрать ручную приёмку.",
                "sources": ["S02"],
                "tasks": ["W02"],
            },
        ],
        "health": [
            {
                "name": "Todo",
                "repo": "/home/roomhacker/excode",
                "native": "Next backend kanban работает на private port 43327.",
                "app": "todo-board active.",
                "conclusion": "Дорабатывать существующий backend и UI.",
                "sources": ["S01"],
            },
            {
                "name": "Notice",
                "repo": "/opt/noticeplace",
                "native": "Таймер на 30 минут.",
                "app": "notice-proxy active.",
                "conclusion": "Оставить как есть.",
                "sources": ["S02"],
                "url": "https://notice.example.invalid/",
            },
        ],
        "phases": [
            {"id": "base", "name": "1. Действующие версии и вход", "color": "#245dd8"},
            {"id": "flow", "name": "2. Сквозные связи", "color": "#5e64b6"},
        ],
        "tasks": [
            {
                "id": "W01",
                "title": "Сопоставить исходники, сборки и рабочие точки входа",
                "phase": "base",
                "priority": "P0",
                "owner": "Агент интеграции",
                "repo": "server-100; /home/roomhacker/excode; /opt/noticeplace",
                "locks": ["runtime-baseline"],
                "deps": [],
                "hours": {"min": 4, "base": 8, "max": 12},
                "scope": ["Зафиксировать текущие git revisions."],
                "acceptance": ["Есть таблица ревизий и точек входа."],
                "result": "Таблица ревизий и точек входа.",
                "reuse": "Канонический Todo.",
                "sources": ["S01"],
            },
            {
                "id": "W02",
                "title": "Собрать ручную приёмку",
                "phase": "flow",
                "priority": "P1",
                "owner": "Агент приёмки",
                "repo": "server-100",
                "locks": [],
                "deps": ["W01"],
                "hours": {"min": 2, "base": 4, "max": 6},
                "scope": ["Описать форму приёмки."],
                "acceptance": ["Владелец может принять задачу."],
                "result": "Форма приёмки.",
                "reuse": "Ничего.",
                "sources": ["S02"],
            },
        ],
        "rules": [
            "Явные поручения запускаются автоматически.",
            "Идеи остаются в бэклоге.",
        ],
        "agentPrompt": "Продолжи реализацию первой версии системы работы.\n\nЦель: одно поручение проходит весь процесс.",
        "sources": [
            {
                "id": "S01",
                "kind": "Код",
                "title": "Канонический Todo",
                "location": "repo: /home/roomhacker/excode; file: src/board.ts",
                "finding": "Канонический Todo уже есть.",
                "excerpt": "explicit-task / idea / ambiguous",
                "revision": "HEAD abc123; чистое дерево",
                "time": "22.10.2026, 15:48-16:29 МСК",
            },
            {
                "id": "S02",
                "kind": "Runtime",
                "title": "Состояние сервисов",
                "location": "server-100: systemctl status",
                "finding": "Сервис работает.",
                "excerpt": "",
                "revision": "",
                "time": "22.10.2026, 15:48-16:29 МСК",
            },
        ],
    }


def load_audit_data() -> dict:
    """The real audit data when it is next to the checkout."""

    for candidate in AUDIT_DATA_CANDIDATES:
        try:
            if candidate.is_file():
                with candidate.open(encoding="utf-8") as handle:
                    return json.load(handle)
        except OSError:
            continue
    return synthetic_audit_data()


AUDIT = load_audit_data()
HTML = lhc.render_product_sections(AUDIT)


def section_html(section_id: str) -> str:
    """The markup of one section of the rendered product."""

    match = re.search(
        rf'<section id="{re.escape(section_id)}".*?</section>', HTML, re.S
    )
    assert match, f"section {section_id} is missing"
    return match.group(0)


def element_text(markup: str, element_id: str) -> str:
    """The text of one element of the rendered product."""

    match = re.search(
        rf'<(\w+)[^>]*\bid="{re.escape(element_id)}"[^>]*>(.*?)</\1>', markup, re.S
    )
    assert match, f"element {element_id} is missing"
    return html_module.unescape(match.group(2))


# --------------------------------------------------------------------------
# every field of the input is on the page
# --------------------------------------------------------------------------


def test_every_top_level_key_is_rendered():
    for key, value in AUDIT.items():
        if isinstance(value, str):
            assert lhc.escape(value) in HTML, f"the value of {key} is not on the page"
        elif isinstance(value, (int, float)):
            assert str(value) in HTML, f"the value of {key} is not on the page"
        elif isinstance(value, list):
            assert value, f"{key} is empty, nothing was rendered"
        else:  # pragma: no cover - the audit data has no other shape
            pytest.fail(f"unexpected type of {key}: {type(value)}")


def test_every_field_of_a_sample_element_is_rendered():
    for key, items in AUDIT.items():
        if not isinstance(items, list) or not items:
            continue
        sample = items[0]
        if isinstance(sample, str):
            assert lhc.escape(sample) in HTML, f"{key}[0] is not on the page"
            continue
        for field, value in sample.items():
            for single in _flatten(value):
                text = lhc.escape(single)
                if not text:
                    continue
                assert text in HTML, f"{key}[0].{field} is not on the page: {single!r}"


def _flatten(value):
    """The scalar values of a field, however deep it is nested."""

    if isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _flatten(item)
    else:
        yield value


def test_the_estimate_of_a_task_is_on_the_page():
    """The hours of a task are shown as a range, not as raw numbers."""

    task = AUDIT["tasks"][0]
    hours = task["hours"]
    expected = f"{hours['min']}–{hours['max']} ч"
    card = re.search(
        rf'<article class="lhc-work" id="lhc-work-{re.escape(task["id"])}".*?</article>',
        HTML,
        re.S,
    )
    assert card and expected in card.group(0), f"{expected} is not on the card"


def test_the_optional_fields_are_rendered_when_present():
    """A field that is absent in the sample must still work when it comes."""

    with_url = [item for item in AUDIT["health"] if item.get("url")]
    for item in with_url:
        assert lhc.escape(item["url"]) in HTML
    with_revision = [item for item in AUDIT["sources"] if item.get("revision")]
    for item in with_revision:
        assert lhc.escape(item["revision"]) in HTML


def test_the_headline_fields_have_a_home():
    for key in ("lead", "method", "coverageNote", "estimateNote", "planStart", "specUrl"):
        assert lhc.escape(AUDIT[key]) in HTML, f"{key} has no home"
    assert AUDIT["title"] in HTML
    assert AUDIT["reportId"] in HTML
    assert AUDIT["auditDateLabel"] in HTML


# --------------------------------------------------------------------------
# the counts of the page match the counts of the input
# --------------------------------------------------------------------------


def test_the_requirements_matrix_has_one_row_per_requirement():
    rows = re.findall(r'<tr class="lhc-row" data-lhc-status=', HTML)
    assert len(rows) == len(AUDIT["requirements"])


def test_the_health_table_has_one_row_per_service():
    rows = re.findall(r'<tr class="lhc-row lhc-row--health">', HTML)
    assert len(rows) == len(AUDIT["health"])


def test_the_summary_has_one_card_per_conclusion():
    cards = re.findall(r'<article class="lhc-card lhc-card--', HTML)
    assert len(cards) == len(AUDIT["summary"])


def test_the_notes_have_one_block_per_note():
    blocks = re.findall(r'lhc-note-block', HTML)
    assert len(blocks) == len(AUDIT["notes"])


def test_the_rules_have_one_item_per_rule():
    rules = section_html("lhc-rules")
    items = re.findall(r"<li>", rules)
    assert len(items) == len(AUDIT["rules"])


def test_the_sources_have_one_card_per_source():
    cards = re.findall(r'<article class="lhc-source"', HTML)
    assert len(cards) == len(AUDIT["sources"])


def test_the_metrics_count_the_requirements_by_status():
    metrics = section_html("lhc-metrics")
    for status in ("ready", "partial", "missing", "unverified"):
        expected = sum(
            1 for item in AUDIT["requirements"] if item.get("status") == status
        )
        tile = re.search(
            rf'<div class="lhc-metric lhc-metric--{status}"><b>(\d+)</b>', metrics
        )
        assert tile, f"the metric {status} is missing"
        assert int(tile.group(1)) == expected
    total = re.search(r'<div class="lhc-metric lhc-metric--total"><b>(\d+)</b>', metrics)
    assert int(total.group(1)) == len(AUDIT["requirements"])


# --------------------------------------------------------------------------
# the gantt
# --------------------------------------------------------------------------


def test_the_gantt_has_one_row_per_task_and_one_band_per_phase():
    gantt = section_html("lhc-gantt")
    rows = re.findall(r'<div class="lhc-gantt-row" data-lhc-task="([^"]+)"', gantt)
    bands = re.findall(r'<div class="lhc-gantt-band" data-lhc-phase="([^"]+)"', gantt)
    assert len(rows) == len(AUDIT["tasks"])
    assert len(bands) == len(AUDIT["phases"])
    assert [task["id"] for task in AUDIT["tasks"]] == rows
    assert [phase["id"] for phase in AUDIT["phases"]] == bands


def test_the_gantt_places_a_bar_on_every_row():
    gantt = section_html("lhc-gantt")
    rows = re.findall(r'<div class="lhc-gantt-row".*?</div></div>', gantt, re.S)
    assert len(rows) == len(AUDIT["tasks"])
    for row in rows:
        assert 'class="lhc-bar"' in row


# --------------------------------------------------------------------------
# the work cards
# --------------------------------------------------------------------------


def test_the_work_card_carries_its_scope_and_its_acceptance():
    for task in AUDIT["tasks"]:
        card = re.search(
            rf'<article class="lhc-work" id="lhc-work-{re.escape(task["id"])}".*?</article>',
            HTML,
            re.S,
        )
        assert card, f"the card of {task['id']} is missing"
        markup = card.group(0)
        assert lhc.escape(task["title"]) in markup
        assert lhc.escape(task["result"]) in markup
        assert lhc.escape(task["reuse"]) in markup
        for line in task["scope"]:
            assert lhc.escape(line) in markup, f"the scope of {task['id']} is missing a line"
        for line in task["acceptance"]:
            assert lhc.escape(line) in markup, f"the acceptance of {task['id']} is missing a line"
        assert lhc.escape(task["repo"]) in markup
        assert lhc.escape(task["priority"]) in markup


def test_the_work_card_is_a_control_that_opens_its_body():
    for task in AUDIT["tasks"]:
        card = re.search(
            rf'<article class="lhc-work" id="lhc-work-{re.escape(task["id"])}".*?</article>',
            HTML,
            re.S,
        )
        markup = card.group(0)
        assert 'aria-expanded="false"' in markup
        assert f'aria-controls="lhc-work-body-{task["id"]}"' in markup
        assert f'id="lhc-work-body-{task["id"]}"' in markup
        assert "hidden" in markup


# --------------------------------------------------------------------------
# the agent task
# --------------------------------------------------------------------------


def test_the_agent_prompt_is_on_the_page_in_full():
    text = element_text(HTML, "lhc-agent-text")
    assert len(text) == len(AUDIT["agentPrompt"])
    assert text == AUDIT["agentPrompt"]


def test_the_copy_button_reads_the_element_with_the_prompt():
    button = re.search(r'<button[^>]*id="lhc-copy-agent"[^>]*>', HTML)
    assert button, "the copy button is missing"
    markup = button.group(0)
    target = re.search(r'data-lhc-copy-target="([^"]+)"', markup)
    assert target, "the copy button does not name the element it reads"
    assert target.group(1) == "lhc-agent-text"
    assert element_text(HTML, target.group(1)) == AUDIT["agentPrompt"]


def test_the_script_copies_the_element_of_the_button():
    scripts = lhc.product_scripts()
    assert "lhc-copy-agent" in scripts
    assert "data-lhc-copy-target" in scripts
    assert "Задание скопировано" in scripts


# --------------------------------------------------------------------------
# escaping
# --------------------------------------------------------------------------


def test_a_dangerous_value_is_escaped_and_not_rendered_raw():
    hostile = {
        "title": "<script>alert('x')</script>",
        "lead": 'Кавычка " и амперсанд &',
        "method": "</section><script>bad()</script>",
        "specText": "<img src=x onerror=alert(1)>",
        "agentPrompt": "<script>steal()</script>",
        "summary": [
            {
                "status": "ready",
                "label": "<b>жирный</b>",
                "title": "Заголовок <script>",
                "items": ["<script>item</script>"],
                "sources": ["<script>S</script>"],
            }
        ],
        "notes": [
            {"type": "blue", "title": "<script>t</script>", "text": "<script>x</script>", "sources": []}
        ],
        "requirements": [
            {
                "id": "R01",
                "component": "<script>c</script>",
                "title": "<script>t</script>",
                "status": "ready",
                "proof": "<script>p</script>",
                "found": "<script>f</script>",
                "remaining": "<script>r</script>",
                "sources": ["<script>s</script>"],
                "tasks": ["<script>W01</script>"],
            }
        ],
        "health": [
            {
                "name": "<script>n</script>",
                "repo": "<script>r</script>",
                "native": "<script>n</script>",
                "app": "<script>a</script>",
                "conclusion": "<script>c</script>",
                "sources": [],
                "url": "javascript:alert(1)",
            }
        ],
        "phases": [{"id": "<script>p</script>", "name": "<script>n</script>", "color": "red;} body{display:none"}],
        "tasks": [
            {
                "id": "<script>W01</script>",
                "title": "<script>t</script>",
                "phase": "<script>p</script>",
                "priority": "<script>P0</script>",
                "owner": "<script>o</script>",
                "repo": "<script>r</script>",
                "locks": ["<script>l</script>"],
                "deps": ["<script>d</script>"],
                "hours": {"min": 1, "base": 2, "max": 3},
                "scope": ["<script>s</script>"],
                "acceptance": ["<script>a</script>"],
                "result": "<script>res</script>",
                "reuse": "<script>u</script>",
                "sources": ["<script>s</script>"],
            }
        ],
        "rules": ["<script>rule</script>"],
        "sources": [
            {
                "id": "<script>S01</script>",
                "kind": "<script>k</script>",
                "title": "<script>t</script>",
                "location": "<script>l</script>",
                "finding": "<script>f</script>",
                "excerpt": "<script>e</script>",
                "revision": "<script>v</script>",
                "time": "<script>ti</script>",
            }
        ],
    }
    rendered = lhc.render_product_sections(hostile)
    # the plan as a file is an inert payload, the markup around it is not
    markup = re.sub(r'<template id="lhc-plan-json">.*?</template>', "", rendered, flags=re.S)
    assert "<script>" not in rendered
    assert "</script>" not in rendered
    assert "<img" not in markup
    assert "&lt;script&gt;" in rendered
    # a color from the data cannot break out of the style attribute
    assert "red;} body{display:none" not in markup
    # a link from the data cannot become a javascript: link
    assert 'href="javascript:alert(1)"' not in markup


def test_a_quote_in_a_value_is_escaped():
    rendered = lhc.render_product_sections({"title": 'Он сказал "привет"'})
    assert "&quot;привет&quot;" in rendered
    assert '"привет"' not in rendered


# --------------------------------------------------------------------------
# the styles and the scripts
# --------------------------------------------------------------------------


def test_the_styles_are_not_empty_and_declare_the_theme_variables():
    styles = lhc.product_styles()
    assert styles.strip()
    assert "<style" not in styles
    for name in (
        "--bg", "--panel", "--line", "--text", "--muted", "--accent",
        "--ok", "--warn", "--bad", "--st-done", "--st-running",
        "--st-blocked", "--st-waiting", "--st-deferred", "--st-queued",
    ):
        assert name in styles, f"the theme variable {name} is not declared"
    assert ':root[data-theme="light"]' in styles


def test_the_scripts_are_not_empty_and_carry_the_controls():
    scripts = lhc.product_scripts()
    assert scripts.strip()
    assert "<script" not in scripts
    for control in (
        "lhc-theme-toggle",
        "lhc-gantt-zoom",
        "data-lhc-req-filter",
        "lhc-work-head",
        "lhc-copy-agent",
        "lhc-download-json",
    ):
        assert control in scripts, f"the control {control} has no script"


def test_the_styles_respect_the_dashboard_palette():
    """The product borrows the palette of the dashboard, it does not invent one."""

    palette = lhc.dashboard_palette()
    if not palette:
        pytest.skip("the dashboard module is not next to this one")
    styles = lhc.product_styles()
    for theme in ("dark", "light"):
        for name, value in palette[theme].items():
            assert f"--lhc-{theme}-{name}" in styles
            assert value in styles


# --------------------------------------------------------------------------
# the fragment is embeddable
# --------------------------------------------------------------------------


def test_the_output_is_a_fragment_and_not_a_page():
    for tag in ("<html", "<head", "<body", "<style"):
        assert tag not in HTML, f"the fragment carries a {tag} of its own"


def test_the_sections_are_balanced():
    assert HTML.count("<section") == HTML.count("</section>")
    for section_id in (
        "lhc-summary", "lhc-notes", "lhc-metrics", "lhc-requirements",
        "lhc-health", "lhc-gantt", "lhc-work", "lhc-rules", "lhc-agent",
        "lhc-sources", "lhc-spec",
    ):
        assert f'<section id="{section_id}"' in HTML


def test_the_navigation_points_at_the_sections():
    nav = re.search(r'<nav class="lhc-nav".*?</nav>', HTML, re.S)
    assert nav
    for section_id in (
        "lhc-summary", "lhc-notes", "lhc-metrics", "lhc-requirements",
        "lhc-health", "lhc-gantt", "lhc-work", "lhc-rules", "lhc-agent",
        "lhc-sources", "lhc-spec",
    ):
        assert f'href="#{section_id}"' in nav.group(0)


def test_the_gantt_scrolls_inside_its_own_box():
    gantt = section_html("lhc-gantt")
    assert 'class="lhc-gantt-scroll"' in gantt
    styles = lhc.product_styles()
    assert ".lhc-gantt-scroll{overflow:auto" in styles
    assert ".lhc-product [hidden]{display:none!important}" in styles


def test_the_plan_is_carried_whole_for_the_download():
    """The download button reads the plan out of the page, so it must be whole."""

    island = re.search(r'<template id="lhc-plan-json">(.*?)</template>', HTML, re.S)
    assert island, "the plan is not on the page"
    payload = json.loads(island.group(1))
    assert payload == AUDIT


def test_a_link_from_the_data_is_a_link_only_when_it_is_safe():
    rendered = lhc.render_product_sections({
        "health": [{
            "name": "Todo", "repo": "/repo", "native": "n", "app": "a",
            "conclusion": "c", "sources": [], "url": "javascript:alert(1)",
        }],
        "specUrl": "javascript:alert(2)",
    })
    markup = re.sub(r'<template id="lhc-plan-json">.*?</template>', "", rendered, flags=re.S)
    assert 'href="javascript:' not in markup
    # an address that is not a link is not offered as a link
    assert "Открыть приложение" not in markup
    assert "Открыть оригинал" not in markup
    assert '<a id="lhc-spec-link"' not in markup


def test_the_action_links_are_touch_targets():
    styles = lhc.product_styles()
    line = next(part for part in styles.split("\n") if part.startswith(".lhc-link{"))
    assert "min-height:44px" in line
    assert "min-width:44px" in line


def test_the_touch_targets_are_at_least_44_pixels():
    styles = lhc.product_styles()
    for rule in (
        ".lhc-btn{", ".lhc-chip--btn{", ".lhc-nav-link{",
    ):
        line = next(part for part in styles.split("\n") if part.startswith(rule))
        assert "min-height:44px" in line, f"{rule} is smaller than a finger"
    assert ".lhc-ref{min-height:44px" in styles


def test_the_long_text_wraps_instead_of_pushing_the_page():
    styles = lhc.product_styles()
    assert "overflow-wrap:anywhere" in styles
    assert ".lhc-location{" in styles
    location = next(part for part in styles.split("\n") if part.startswith(".lhc-location{"))
    assert "overflow-wrap:anywhere" in location
    assert ".lhc-gantt-scroll{overflow:auto" in styles


# --------------------------------------------------------------------------
# the leaves
# --------------------------------------------------------------------------


def test_the_leaves_carry_the_shape_of_the_dashboard_table():
    leaves = lhc.product_leaves(AUDIT)
    assert len(leaves) == len(AUDIT["tasks"])
    for leaf, task in zip(leaves, AUDIT["tasks"]):
        assert leaf["id"] == task["id"]
        assert leaf["label"] == task["title"]
        assert leaf["owner"] == task["owner"]
        assert leaf["depends_on"] == task["deps"]
        assert leaf["estimate_minutes"] == task["hours"]["min"]
        assert leaf["estimate_max_minutes"] == task["hours"]["max"]
        assert leaf["estimate_base_minutes"] == task["hours"]["base"]
        assert leaf["estimate_min"] == leaf["estimate_minutes"]
        assert leaf["estimate_max"] == leaf["estimate_max_minutes"]
        assert task["priority"] in leaf["note"]
        for lock in task["locks"]:
            assert lock in leaf["note"]
        assert task["repo"] in leaf["note"]


def test_a_task_without_an_executed_state_stays_queued():
    leaves = lhc.product_leaves(AUDIT)
    assert leaves, "there is nothing to render"
    for leaf in leaves:
        assert leaf["status"] == "queued"
    done = lhc.product_leaves({"tasks": [{"id": "W01", "title": "Сделано", "status": "done"}]})
    assert done[0]["status"] == "done"
    invented = lhc.product_leaves({"tasks": [{"id": "W01", "title": "Готово", "result": "ок"}]})
    assert invented[0]["status"] == "queued"


def test_the_leaves_survive_an_empty_plan():
    assert lhc.product_leaves({}) == []
    assert lhc.product_leaves({"tasks": []}) == []


def test_the_renderer_survives_an_empty_plan():
    rendered = lhc.render_product_sections({})
    assert rendered.count("<section") == rendered.count("</section>")
    assert "lhc-product" in rendered


# --------------------------------------------------------------------------
# the interactive grid: the card of a task, the arrows and the blocking
# --------------------------------------------------------------------------


def _div_block(markup: str, start: int) -> tuple[str, int]:
    """The markup of the div that opens at ``start`` and the index behind it."""

    depth = 0
    for match in re.finditer(r"<div\b|</div>", markup[start:]):
        depth += 1 if match.group(0) != "</div>" else -1
        if depth == 0:
            return markup[start:start + match.end()], start + match.end()
    raise AssertionError("the div is never closed")


def test_the_gantt_has_a_click_target_for_every_task():
    """A click on the label, on the bar or on the track opens the card."""

    gantt = section_html("lhc-gantt")
    labels = re.findall(r'<button type="button" class="lhc-gantt-label">', gantt)
    bars = re.findall(r'<button type="button" class="lhc-bar" data-lhc-task="([^"]+)"', gantt)
    assert len(labels) == len(AUDIT["tasks"])
    assert bars == [task["id"] for task in AUDIT["tasks"]]
    # the row itself carries the task, so the empty track is a target too
    for task in AUDIT["tasks"]:
        assert f'data-lhc-task="{task["id"]}"' in gantt


def test_the_card_of_a_task_carries_every_field_of_the_plan():
    """The card shows the whole task, not a summary of it."""

    phases = {phase["id"]: phase["name"] for phase in AUDIT["phases"]}
    titles = {task["id"]: task["title"] for task in AUDIT["tasks"]}
    for task in AUDIT["tasks"]:
        start = HTML.index(f'<div class="lhc-detail" data-lhc-detail="{task["id"]}">')
        card, _ = _div_block(HTML, start)
        assert lhc.escape(task["id"]) in card
        assert lhc.escape(task["title"]) in card
        assert lhc.escape(phases.get(task["phase"], "")) in card
        assert lhc.escape(task["priority"]) in card
        assert lhc.escape(task["owner"]) in card
        assert lhc.escape(task["repo"]) in card
        for lock in task["locks"]:
            assert lhc.escape(lock) in card, f"the lock {lock} is missing"
        for dep in task["deps"]:
            assert lhc.escape(dep) in card, f"the dependency {dep} is missing"
            assert lhc.escape(titles[dep]) in card, f"the title of {dep} is missing"
        hours = task["hours"]
        expected = f"мин {hours['min']} · база {hours['base']} · макс {hours['max']} ч"
        assert expected in card, f"the estimate of {task['id']} is missing"
        for line in task["scope"]:
            assert lhc.escape(line) in card
        for line in task["acceptance"]:
            assert lhc.escape(line) in card
        assert lhc.escape(task["reuse"]) in card
        assert lhc.escape(task["result"]) in card
        for source in task["sources"]:
            assert f'#lhc-source-{source}"' in card


def test_the_card_does_not_invent_a_state_of_the_work():
    """The data has no executed state, so the card says "план"."""

    start = HTML.index('<div class="lhc-detail" data-lhc-detail="')
    card, _ = _div_block(HTML, start)
    assert 'lhc-chip--plan">план<' in card
    assert '">готово<' not in card.lower()


def test_the_card_is_one_implementation_for_the_grid_and_the_work():
    """The grid opens the very card the work card shows."""

    body = re.search(
        r'<div class="lhc-gantt-detail-body" id="lhc-gantt-detail-body">(.*?)</div>',
        HTML,
        re.S,
    )
    assert body, "the card of the grid is missing"
    assert not body.group(1).strip(), "the card of the grid is not filled by the script"
    assert "detailBody.innerHTML = source.innerHTML" in lhc.product_scripts()
    # the work card carries that card, not a second copy of it
    work = re.search(
        r'<div class="lhc-work-body" id="lhc-work-body-W01" hidden>(.*?)</div></article>',
        HTML,
        re.S,
    )
    assert work and 'class="lhc-detail" data-lhc-detail="W01"' in work.group(1)


def test_the_card_sits_next_to_the_grid_and_not_inside_its_scrolling_strip():
    """The card is reachable without scrolling the grid sideways."""

    gantt = section_html("lhc-gantt")
    start = gantt.index('<div class="lhc-gantt-scroll">')
    strip, end = _div_block(gantt, start)
    assert "lhc-gantt-detail" not in strip, "the card is inside the scrolling strip"
    assert 'class="lhc-gantt-detail"' in gantt[end:end + 200], "the card is not under the grid"


def test_the_card_can_be_closed():
    gantt = section_html("lhc-gantt")
    assert 'id="lhc-gantt-detail-close"' in gantt
    assert 'id="lhc-gantt-detail" hidden' in gantt
    assert "lhc-gantt-detail-close" in lhc.product_scripts()


def test_the_arrows_are_drawn_for_every_dependency_of_the_plan():
    gantt = section_html("lhc-gantt")
    paths = re.findall(
        r'<path class="lhc-net-edge" data-lhc-from="([^"]+)" data-lhc-to="([^"]+)"', gantt
    )
    expected = [(dep, task["id"]) for task in AUDIT["tasks"] for dep in task["deps"]]
    assert sorted(paths) == sorted(expected)
    assert len(paths) == sum(len(task["deps"]) for task in AUDIT["tasks"])
    # every arrow has a head
    assert gantt.count('marker-end="url(#lhc-gantt-arrow)"') == len(paths)
    assert 'id="lhc-gantt-arrow"' in gantt


def test_the_arrows_can_be_switched_off():
    gantt = section_html("lhc-gantt")
    assert '<input type="checkbox" id="lhc-gantt-deps" checked>' in gantt
    assert "Связи работ" in gantt
    scripts = lhc.product_scripts()
    assert "lhc-gantt-deps" in scripts
    assert "lhc-gantt--no-deps" in scripts
    assert ".lhc-gantt--no-deps .lhc-gantt-net{display:none}" in lhc.product_styles()


def test_the_selected_row_is_marked():
    assert "is-selected" in lhc.product_scripts()
    styles = lhc.product_styles()
    assert ".lhc-gantt-row.is-selected .lhc-bar{outline" in styles


def test_the_blocking_is_visible_in_the_grid_and_in_the_card():
    """A task says what it waits for and what it holds back."""

    gantt = section_html("lhc-gantt")
    for task in AUDIT["tasks"]:
        row = re.search(
            rf'<div class="lhc-gantt-row" data-lhc-task="{re.escape(task["id"])}".*?</div></div>',
            gantt,
            re.S,
        )
        assert row, f"the row of {task['id']} is missing"
        markup = row.group(0)
        waits = re.search(r'data-lhc-waits="([^"]*)"', markup)
        assert waits, f"the row of {task['id']} does not say what it waits for"
        for dep in task["deps"]:
            assert dep in waits.group(1), f"the row of {task['id']} hides {dep}"
        held = [other["id"] for other in AUDIT["tasks"] if task["id"] in other["deps"]]
        if held:
            assert f'data-lhc-blocks="{", ".join(held)}"' in markup
    assert "ждёт" in gantt and "блокирует" in gantt


# --------------------------------------------------------------------------
# the groups of the delivery side
# --------------------------------------------------------------------------


def test_every_group_renders_a_fragment_of_its_own():
    for group in ("all", "plan", "evidence"):
        markup = lhc.render_product_sections(AUDIT, group=group)
        assert 'class="lhc-product"' in markup
        assert markup.count("<section") == markup.count("</section>")
        for tag in ("<html", "<head", "<body", "<style"):
            assert tag not in markup, f"the group {group} carries a {tag} of its own"


def test_the_groups_together_carry_the_sections_of_the_whole():
    whole = lhc.render_product_sections(AUDIT)
    plan = lhc.render_product_sections(AUDIT, group="plan")
    evidence = lhc.render_product_sections(AUDIT, group="evidence")

    def sections(markup: str) -> set:
        return set(re.findall(r'<section id="([^"]+)"', markup))

    assert sections(plan) == {"lhc-gantt", "lhc-work"}
    assert sections(evidence)
    assert sections(plan) | sections(evidence) == sections(whole)
    assert not sections(plan) & sections(evidence)


def test_the_groups_do_not_share_an_id():
    plan = lhc.render_product_sections(AUDIT, group="plan")
    evidence = lhc.render_product_sections(AUDIT, group="evidence")

    def ids(markup: str) -> set:
        return set(re.findall(r'\sid="([^"]+)"', markup))

    plan_ids = ids(plan)
    evidence_ids = ids(evidence)
    assert not plan_ids & evidence_ids, "the groups collide on an id"
    # the card of a task belongs to the plan group; the evidence refers to it
    assert "lhc-gantt-detail" in plan_ids
    assert "lhc-gantt-detail" not in evidence_ids
    # the plan as a file belongs to the plan group as well
    assert "lhc-plan-json" in plan_ids
    assert "lhc-plan-json" not in evidence_ids


def test_an_unknown_group_is_refused():
    with pytest.raises(ValueError):
        lhc.render_product_sections(AUDIT, group="nowhere")
