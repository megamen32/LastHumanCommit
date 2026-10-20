#!/usr/bin/env python3
"""Build the LHC landing from the checked-out Git sources, with no dependencies."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = SITE / "dist"
REPO_URL = "https://github.com/megamen32/LastHumanCommit"
STEP_MARKER = re.compile(r"(?m)^<!-- lhc-workflow-step:([a-z0-9-]+) -->\s*$")
DEPTH_MARKER = re.compile(r"(?m)^<!-- lhc-decision-depth:([a-z0-9-]+) -->\s*$")


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[\\\x60*_#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def first_paragraph(body: str, limit: int = 420, *, skip_policy: bool = False) -> str:
    """Pick a useful prose paragraph; headings, lists and inherited boilerplate are ignored."""
    for block in re.split(r"\n\s*\n", body):
        lines = [line.strip() for line in block.splitlines()]
        if not lines or not all(lines):
            continue
        if any(line.startswith((">", "-", "* ", "|", "```", "#")) for line in lines):
            continue
        paragraph = plain(" ".join(lines))
        if len(paragraph) < 25:
            continue
        if skip_policy and re.match(
            r"^(Inherit the current router language policy|Optional method reference\.)",
            paragraph,
            re.IGNORECASE,
        ):
            continue
        if len(paragraph) > limit:
            paragraph = paragraph[:limit].rsplit(" ", 1)[0] + "…"
        return paragraph
    return ""


def structured_blocks(content: str, marker: re.Pattern[str], path: str) -> list[dict]:
    """Read stable-ID blocks and their following heading/body without matching heading text."""
    markers = list(marker.finditer(content))
    items = []
    seen = set()
    for index, match in enumerate(markers):
        identifier = match.group(1)
        if identifier in seen:
            raise ValueError(f"Duplicate structured ID {identifier!r} in {path}")
        seen.add(identifier)
        stop = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        tail = content[match.end():stop]
        heading = re.search(r"(?m)^#{2,6}\s+(.+?)\s*$", tail)
        if not heading:
            raise ValueError(f"Structured ID {identifier!r} has no following heading in {path}")
        body = tail[heading.end():].strip()
        items.append({"id": identifier, "heading": heading.group(1).strip(), "body": body})
    return items


def source_url(commit: str, path: str) -> str:
    return f"{REPO_URL}/blob/{commit}/{path}"


def role_summary(content: str, role_name: str) -> str:
    heading = re.search(r"(?m)^# .+$", content)
    body = content[heading.end():].strip() if heading else content
    summary = first_paragraph(body, skip_policy=True)
    if not summary:
        raise ValueError(f"Missing meaningful role description in {role_name}.md")
    return summary


def role_kind(content: str) -> str:
    headline = re.search(r"(?m)^# (.+)$", content)
    title = headline.group(1) if headline else ""
    preamble = content[:headline.start()] if headline else ""
    if re.search(r"\bcompatibility alias\b", title, re.IGNORECASE):
        return "compatibility-alias"
    if re.search(r"Optional method reference\.", preamble, re.IGNORECASE):
        return "method-reference"
    return "role"


def role_data(path: Path, sha: str) -> dict:
    md = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^# (.+)$", md)
    if not match:
        raise ValueError(f"Missing role title in {path}")
    return {
        "name": path.stem,
        "subtitle": match.group(1).strip(),
        "kind": role_kind(md),
        "summary": role_summary(md, path.stem),
        "details": md,
        "source": source_url(sha, path.relative_to(ROOT).as_posix()),
    }


def build() -> dict:
    sha = git("rev-parse", "HEAD")
    if sha == "unknown":
        raise ValueError("Cannot identify the Git snapshot; refusing to generate source links")
    concept_path = "docs/PRODUCT_CONCEPT.md"
    router_path = "AGENTS.md"
    full_path = "templates/FULL_CYCLE.md"
    concept = (ROOT / concept_path).read_text(encoding="utf-8")
    router = (ROOT / router_path).read_text(encoding="utf-8")
    full = (ROOT / full_path).read_text(encoding="utf-8")
    workflow = structured_blocks(concept, STEP_MARKER, concept_path)
    if not workflow:
        raise ValueError(f"No stable workflow sections found in {concept_path}")
    depths = structured_blocks(full, DEPTH_MARKER, full_path)
    material_depth = next((item for item in depths if item["id"] == "material-choice"), None)
    if not material_depth:
        raise ValueError(f"Missing material-choice decision depth in {full_path}")

    role_paths = sorted((ROOT / "src" / "common" / "agents").glob("*.md"))
    if not role_paths:
        raise ValueError("No agent roles found; refusing to publish stale role data")
    role_order = {"Lead": 0, "Worker": 1, "Adviser": 2, "Critic": 3, "Reviewer": 4, "Tester": 5, "Overseer": 6}
    roles = sorted((role_data(p, sha) for p in role_paths), key=lambda r: (role_order.get(r["name"], 99), r["name"]))
    plugin = json.loads((ROOT / "plugins/last-human-commit/plugin.json").read_text(encoding="utf-8"))
    role_text = "".join(p.read_text(encoding="utf-8") for p in role_paths)
    source_hash = hashlib.sha256((concept + router + full + role_text).encode("utf-8")).hexdigest()[:12]
    steps = []
    for number, item in enumerate(workflow, start=1):
        excerpt = first_paragraph(item["body"])
        if not excerpt:
            raise ValueError(f"Workflow step {item['id']!r} has no source prose")
        steps.append({
            "id": item["id"], "number": f"{number:02d}",
            "titleKey": f"workflow.{item['id']}.title",
            "descriptionKey": f"workflow.{item['id']}.description",
            "sourceExcerpt": excerpt,
            "source": source_url(sha, concept_path),
        })

    data = {
        "schemaVersion": 2,
        "revision": sha,
        "shortRevision": sha[:8],
        "productVersion": plugin["version"],
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sourceHash": source_hash,
        "repository": REPO_URL,
        "conceptSource": source_url(sha, concept_path),
        "routerSource": source_url(sha, router_path),
        "fullSource": source_url(sha, full_path),
        "decisionDepth": {
            "id": material_depth["id"],
            "titleKey": f"decision.{material_depth['id']}.title",
            "noteKey": f"decision.{material_depth['id']}.note",
            "sourceExcerpt": first_paragraph(material_depth["body"]),
            "source": source_url(sha, full_path),
        },
        "modes": {
            "quick": {
                "name": "Quick loop", "taglineKey": "mode.quick.tagline",
                "noteKey": "mode.quick.note", "steps": steps,
            },
            "full": {
                "name": "Full cycle", "taglineKey": "mode.full.tagline",
                "noteKey": "mode.full.note", "steps": steps,
                "decisionDepth": "material-choice",
            },
        },
        "roles": roles,
    }
    DIST.mkdir(parents=True, exist_ok=True)
    assets = ("styles.css", "locale.css", "i18n.js", "app.js")
    for name in ("index.html", *assets):
        shutil.copy2(SITE / name, DIST / name)
    markup = (DIST / "index.html").read_text(encoding="utf-8")
    for name in assets:
        digest = hashlib.sha256((DIST / name).read_bytes()).hexdigest()[:12]
        markup = markup.replace(f'"./{name}"', f'"./{name}?v={digest}"')
    (DIST / "index.html").write_text(markup, encoding="utf-8")
    (DIST / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    data = build()
    print(
        f"Built site/dist from {data['shortRevision']} (LHC {data['productVersion']}) "
        f"with {len(data['modes']['quick']['steps'])} lifecycle stages, "
        f"{len(data['roles'])} Git roles and source hash {data['sourceHash']}"
    )
