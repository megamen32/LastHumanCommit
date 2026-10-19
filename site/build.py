#!/usr/bin/env python3
"""Build the LHC landing using the checked-out Git sources, with no dependencies."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
REPO_URL = "https://github.com/megamen32/LastHumanCommit"

QUICK_STEPS = [
    ("01", "Define the outcome", "Осязаемый результат до кода", "Name the real user, before/after difference and a hands-on canary."),
    ("02", "Route intelligently", "Понять и сделать", "Work directly when the path is clear; use specialists only when evidence justifies them."),
    ("03", "Keep work isolated", "Параллельная работа", "Protect colleagues' in-flight changes and delegate only useful independent work."),
    ("04", "Prove it works", "Проверка и общение", "Run the real scenario, fix failures, and report only verified progress."),
    ("05", "Deliver the result", "Единая зелёная история", "Integrate a tested branch through push and review into one reachable history."),
]
FULL_STEPS = [
    ("01", "Business claim", "Business claim", "Pin down the consumer outcome and the exact acceptance path."),
    ("02", "Least-cost route", "Least-cost route", "Choose the smallest reversible move toward real-world proof."),
    ("03", "Material options", "Material options — only when a route choice matters", "Compare genuinely different choices, then retain the best 80%-value implementation."),
    ("04", "Delivery order", "Delivery order", "Run a real canary, independent review, and fresh user acceptance at the right milestone."),
    ("05", "Verified result", "Result", "Record actual evidence, integration, and deployment state—not a promise."),
]


def git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def sections(content: str) -> dict[str, str]:
    """Markdown H2 sections, preserving text as the authoritative source."""
    matches = list(re.finditer(r"(?m)^## (.+?)\s*$", content))
    return {
        match.group(1).strip(): content[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(content)].strip()
        for i, match in enumerate(matches)
    }


def plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[\\\x60*_#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def first_paragraph(body: str, limit: int = 360) -> str:
    for block in re.split(r"\n\s*\n", body):
        lines = [line.strip() for line in block.splitlines()]
        if not lines or not all(lines):
            continue
        if any(line.startswith((">", "-", "* ", "|", "```", "#")) for line in lines):
            continue
        paragraph = plain(" ".join(lines))
        if len(paragraph) < 25:
            continue
        if len(paragraph) > limit:
            paragraph = paragraph[:limit].rsplit(" ", 1)[0] + "…"
        return paragraph
    return ""


def source_url(commit: str, path: str) -> str:
    return f"{REPO_URL}/blob/{commit}/{path}"


def make_steps(source: str, mapping: list[tuple[str, str, str, str]], path: str, sha: str) -> list[dict]:
    found = sections(source)
    items = []
    for number, title, heading, editorial in mapping:
        if heading not in found:
            raise ValueError(f"Required source heading {heading!r} missing from {path}")
        body = found[heading]
        items.append({
            "number": number, "title": title, "editorial": editorial,
            "section": heading, "sourceExcerpt": first_paragraph(body, 420),
            "source": source_url(sha, path),
        })
    return items


def role_data(path: Path, sha: str) -> dict:
    md = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^# (.+)$", md)
    if not match:
        raise ValueError(f"Missing role title in {path}")
    name = path.stem
    main = md[match.end():].strip()
    summary = first_paragraph(main)
    if not summary:
        raise ValueError(f"Missing meaningful role description in {path}")
    # The current AGENTS.md router makes every specialist conditional.
    # Warn about legacy role wording that predates the active router.
    legacy_notice = "Optional method reference" in md[:180]
    if legacy_notice:
        summary = "Optional method reference; the active router decides when to use it. " + summary
    return {
        "name": name, "subtitle": match.group(1).strip(), "summary": summary,
        "details": md, "optional": name != "Lead",
        "source": source_url(sha, path.relative_to(ROOT).as_posix()),
    }


def build() -> dict:
    sha = git("rev-parse", "HEAD")
    raw_router = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    raw_full = (ROOT / "templates" / "FULL_CYCLE.md").read_text(encoding="utf-8")
    role_paths = sorted((ROOT / "src" / "common" / "agents").glob("*.md"))
    if not role_paths:
        raise ValueError("No agent roles found; refusing to publish stale role data")
    role_order = {"Lead": 0, "Worker": 1, "Adviser": 2, "Critic": 3, "Reviewer": 4, "Tester": 5, "Overseer": 6}
    roles = sorted((role_data(p, sha) for p in role_paths), key=lambda r: (role_order.get(r["name"], 99), r["name"]))
    source_hash = hashlib.sha256(
        (raw_router + raw_full + "".join((p.read_text(encoding="utf-8") for p in role_paths))).encode("utf-8")
    ).hexdigest()[:12]
    data = {
        "revision": sha, "shortRevision": sha[:8],
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sourceHash": source_hash,
        "repository": REPO_URL,
        "routerSource": source_url(sha, "AGENTS.md"),
        "fullSource": source_url(sha, "templates/FULL_CYCLE.md"),
        "modes": {
            "quick": {
                "name": "Quick loop", "tagline": "Smallest useful route",
                "note": "An illustration of the short path through the actual LHC router, not a separately mandated protocol.",
                "steps": make_steps(raw_router, QUICK_STEPS, "AGENTS.md", sha),
            },
            "full": {
                "name": "Full cycle", "tagline": "When a material decision remains",
                "note": "Full is conditional, not a synonym for long or important. The template guides material product, architecture and migration decisions.",
                "steps": make_steps(raw_full, FULL_STEPS, "templates/FULL_CYCLE.md", sha),
            },
        },
        "roles": roles,
    }
    DIST.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(SITE / name, DIST / name)
    (DIST / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    data = build()
    print(f"Built site/dist at {data['shortRevision']} with {len(data['roles'])} live Git roles and hash {data['sourceHash']}")
