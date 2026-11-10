#!/usr/bin/env python3
"""Overdue ROADMAP backlog lines and overdue LHC:LEGACY marks, printed at SessionStart."""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

LINE = re.compile(r"^\s*- \[ \] (\d{4}-\d{2}-\d{2})\s+(.*)$")
MARK = re.compile(r"LHC:LEGACY\b(?:\s+remove=(\d{4}-\d{2}-\d{2}))?\s*(.*)")
SKIP_NAMES = {"lhc_backlog.py", "test_lhc_backlog.py"}


def _day(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def overdue_backlog(roadmap_text: str, today: date) -> list[dict]:
    out = []
    for no, line in enumerate(roadmap_text.splitlines(), 1):
        m = LINE.match(line)
        due = _day(m.group(1)) if m else None
        if due and due < today:
            out.append({"line_no": no, "due": m.group(1), "text": m.group(2).strip(),
                        "days_late": (today - due).days})
    return out


def overdue_legacy(matches: list[tuple[str, int, str]], today: date) -> list[dict]:
    out = []
    for path, no, text in matches:
        m = MARK.search(text)
        if not m:
            continue
        due = _day(m.group(1)) if m.group(1) else None
        if due is None:
            out.append({"path": path, "line_no": no, "due": None, "text": m.group(2).strip()})
        elif due < today:
            out.append({"path": path, "line_no": no, "due": m.group(1), "text": m.group(2).strip()})
    return out


def _group(head: str, lines: list[str], limit: int) -> list[str]:
    more = len(lines) - limit
    return [head, *lines[:limit], *([f"… and {more} more"] if more > 0 else [])]


def render(backlog: list[dict], legacy: list[dict], limit: int = 8) -> str:
    parts: list[str] = []
    if backlog:
        parts += _group(
            "Overdue backlog (ROADMAP.md): take each into this cycle's plan as a leaf, or do it now "
            "if it is under 15 minutes. Do not move the dates.",
            [f"- {b['due']} ({b['days_late']} days late) {b['text']}" for b in backlog], limit)
    if legacy:
        parts += _group(
            "Overdue legacy: delete it in this cycle. An undated mark must get a "
            "remove=YYYY-MM-DD date now.",
            [f"- {g['path']}:{g['line_no']} " + (f"remove={g['due']}" if g["due"] else "undated")
             + f" {g['text']}" for g in legacy], limit)
    return "\n".join(parts)


def find_legacy(root: Path) -> list[tuple[str, int, str]]:
    try:
        run = subprocess.run(["rg", "-n", "--no-heading", "LHC:LEGACY", str(root)],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for raw in run.stdout.splitlines():
        m = re.match(r"^(.*?):(\d+):(.*)$", raw)
        if not m or m.group(1).endswith(".md") or Path(m.group(1)).name in SKIP_NAMES:
            continue
        found.append((str(Path(m.group(1)).relative_to(root)) if m.group(1).startswith(str(root)) else m.group(1),
                      int(m.group(2)), m.group(3)))
    return found


def session_block(root: Path, today: date | None = None) -> str:
    today = today or date.today()
    roadmap = root / "ROADMAP.md"
    text = roadmap.read_text(encoding="utf-8") if roadmap.is_file() else ""
    return render(overdue_backlog(text, today), overdue_legacy(find_legacy(root), today))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".")
    p.add_argument("--today")
    a = p.parse_args()
    try:
        block = session_block(Path(a.root).resolve(), _day(a.today) if a.today else None)
        if block:
            print(block)
    except Exception:  # noqa: BLE001 - never fails
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
