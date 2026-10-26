"""The paper version of the plan: the print sheet and the PDF command.

The owner asked for the plan on paper: an HTML sheet that prints as one wave
per page and a PDF that comes out of the same graph. Two things must hold for
that paper to be worth anything:

* the sheet is self-contained — a document that waits for a font server
  prints differently on the next machine, and a reference to anything outside
  the file is a reference the printer cannot follow;
* the PDF command is honest — it prints the file through a headless renderer
  that is installed, and when none is, it names the renderer it looked for
  and exits with code 2 instead of leaving an empty file behind.

A fix without a test is a fix that comes back.
"""
from __future__ import annotations

import json
import re
import stat
from pathlib import Path

from _inprocess import load_module, run_cli


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_grid.py"

lhc = load_module(TOOL, name="lhc_grid_print")


GRAPH = {
    "schema_version": 2,
    "slots": 2,
    "title": "План бумажной версии",
    "goal": "проверить, что план печатается",
    "business_result": "план на бумаге читается без экрана",
    "tasks": [
        {
            "id": "L01",
            "label": "контракт источника",
            "status": "done",
            "estimate_minutes": 15,
            "depends_on": [],
            "owner": "worker-1",
        },
        {
            "id": "L02",
            "label": "поиск источника",
            "status": "done",
            "estimate_minutes": 15,
            "depends_on": [],
            "owner": "worker-2",
        },
        {
            "id": "L03",
            "label": "долгий лист в работе",
            "status": "running",
            "estimate_minutes": 20,
            "started_at": "14:00",
            "depends_on": ["L01"],
            "owner": "worker-3",
        },
        {
            "id": "L04",
            "label": "лист в очереди с причиной",
            "status": "queued",
            "estimate_minutes": 10,
            "depends_on": ["L03"],
            "wait_reason": "нужен принятый контракт",
            "planned_start": "16:00",
            "planned_finish": "16:10",
        },
        {
            "id": "L05",
            "label": "лист в очереди без причины",
            "status": "queued",
            "estimate_minutes": 10,
            "depends_on": ["L04"],
        },
    ],
}


def _graph_file(tmp_path: Path) -> Path:
    path = tmp_path / "plan.graph.json"
    path.write_text(json.dumps(GRAPH, ensure_ascii=False), encoding="utf-8")
    return path


def _render_print(tmp_path: Path) -> Path:
    """Render the paper version of the fixture and return the sheet."""

    graph_path = _graph_file(tmp_path)
    out_dir = tmp_path / "out"
    rendered = run_cli(
        lhc,
        ["render", str(graph_path), "--out-dir", str(out_dir), "--print"],
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    sheet = out_dir / "plan.print.html"
    assert sheet.exists(), rendered.stdout
    return sheet


def _fake_renderer(tmp_path: Path, body: str) -> Path:
    """A stand-in for a headless renderer, so the test needs no browser.

    A real renderer would be one more thing to install and one more thing to
    break; what the command has to get right is the contract - the sheet goes
    in, the PDF comes out - and that contract is the same for any renderer
    that honours it.
    """

    script = tmp_path / "fake-renderer.sh"
    script.write_text(
        "#!/bin/sh\n"
        "# $1 = the sheet, $2 = the PDF to write\n"
        f"{body}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return script


def test_render_print_writes_the_paper_version_next_to_the_plan(tmp_path):
    """The paper version lands next to the artifacts of the same revision."""

    sheet = _render_print(tmp_path)
    out_dir = sheet.parent
    assert (out_dir / "plan.html").exists()
    assert (out_dir / "plan.md").exists()
    assert sheet.name == "plan.print.html"
    text = sheet.read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>")
    assert '<html lang="ru">' in text


def test_the_paper_version_references_nothing_outside_itself(tmp_path):
    """A sheet that waits for another file prints differently elsewhere."""

    text = _render_print(tmp_path).read_text(encoding="utf-8")
    for pattern in (
        r"<link\b",
        r"<img\b",
        r"<iframe\b",
        r"<object\b",
        r"<embed\b",
        r'src\s*=\s*["\']https?:',
        r"url\(\s*['\"]?https?:",
        r"@import\b",
    ):
        assert not re.search(pattern, text, re.IGNORECASE), pattern


def test_the_paper_version_has_nothing_to_click(tmp_path):
    """Paper does not fold, search or scroll - so the sheet carries no machinery."""

    text = _render_print(tmp_path).read_text(encoding="utf-8")
    for pattern in (r"<script\b", r"<details\b", r"<button\b", r"onclick\s*=", r"onload\s*="):
        assert not re.search(pattern, text, re.IGNORECASE), pattern


def test_the_paper_version_breaks_the_pages_by_wave(tmp_path):
    """One wave per page: the sheet says so in its rules and in its sections."""

    sheet = _render_print(tmp_path)
    text = sheet.read_text(encoding="utf-8")
    # The page rules are in the sheet itself, not in the reader's browser.
    # The rules are looked for as rules: the mere word "@page" in a comment
    # would satisfy a substring and prove nothing.
    assert re.search(r"@page\s*\{[^}]*\}", text), "the sheet declares no page rule"
    assert re.search(r"\.wave\s*\{[^}]*break-before\s*:\s*page", text)
    assert re.search(r"\.cover\s*\{[^}]*break-after\s*:\s*page", text)
    # Every wave of the schedule is a section of the sheet, and the sections
    # are numbered the way the schedule numbers them.
    headings = re.findall(r"<h2>Волна (\d+)</h2>", text)
    assert headings == sorted(headings, key=int)
    assert len(headings) >= 2
    # The first wave follows the cover, so the cover ends the page.
    assert '<section class="cover">' in text
    assert text.count('<section class="wave') == len(headings)


def test_the_paper_version_carries_the_same_truth_as_the_screen(tmp_path):
    """The queue names its reason and its times; a leaf in work names the time."""

    text = _render_print(tmp_path).read_text(encoding="utf-8")
    # The leaf in the queue with a reason shows the reason and both times.
    assert "ждёт: нужен принятый контракт" in text
    assert "начнём 16:00" in text
    assert "закончим 16:10" in text
    # The leaf in the queue without a reason does not pass in silence.
    assert "ждёт: причина не названа" in text
    # The leaf in work shows the time that has passed since it started, and
    # says that the time comes from the moment of the build.
    assert "на момент сборки" in text


def test_the_pdf_command_names_the_missing_renderer_and_exits_with_two(tmp_path):
    """A machine without a renderer is told which renderer is missing."""

    graph_path = _graph_file(tmp_path)
    result = run_cli(
        lhc,
        [
            "pdf",
            str(graph_path),
            "-o",
            str(tmp_path / "plan.pdf"),
            "--renderer",
            "definitely-not-installed-renderer",
        ],
    )
    assert result.returncode == 2, result.stdout + result.stderr
    message = result.stdout + result.stderr
    assert "рендерер не найден" in message
    # The absent renderer is named, not merely mentioned as a category.
    assert "definitely-not-installed-renderer" in message
    # Nothing was written, and nothing claims it was.
    assert not (tmp_path / "plan.pdf").exists()


def test_the_pdf_command_prints_a_pdf_when_a_renderer_is_installed(tmp_path):
    """With a renderer on the machine, the command hands back a PDF."""

    graph_path = _graph_file(tmp_path)
    renderer = _fake_renderer(tmp_path, 'printf "%%PDF-1.4\\n" > "$2"')
    target = tmp_path / "plan.pdf"
    result = run_cli(
        lhc,
        [
            "pdf",
            str(graph_path),
            "-o",
            str(target),
            "--renderer",
            str(renderer),
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.exists()
    assert target.stat().st_size > 0
    assert target.read_bytes()[:5] == b"%PDF-"
    assert str(target) in result.stdout


def test_the_pdf_command_refuses_to_call_an_empty_file_a_pdf(tmp_path):
    """A renderer that prints nothing does not get the command to claim success."""

    graph_path = _graph_file(tmp_path)
    renderer = _fake_renderer(tmp_path, "exit 0")
    target = tmp_path / "plan.pdf"
    result = run_cli(
        lhc,
        [
            "pdf",
            str(graph_path),
            "-o",
            str(target),
            "--renderer",
            str(renderer),
        ],
    )
    assert result.returncode == 2, result.stdout + result.stderr
    message = result.stdout + result.stderr
    assert "PDF не собран" in message
    assert str(renderer) in message
