"""Source-backed presentation of the complete LHC lifecycle (no runtime changes)."""
from __future__ import annotations
import re
from pathlib import Path

PHILOSOPHY = "PRODUCT-PHILOSOPHY.md"
# IDs are presentation keys; source sections and original prose are read on every build.
STEPS = [
    ("intent", "plan", "1", "Lead"),
    ("research", "plan", "2", "Lead · Worker"),
    ("options", "plan", "4.2", "Lead · Adviser · Critic"),
    ("ideal", "plan", "4.2", "Lead · Adviser"),
    ("yagni", "plan", "4.2", "Lead"),
    ("decompose", "build", "5", "Lead"),
    ("parallel", "build", "6", "Lead"),
    ("estimate", "build", "7", "Lead"),
    ("workers", "build", "8", "Worker"),
    ("review", "proof", "review", "Reviewer"),
    ("deploy", "proof", "9", "Worker"),
    ("test", "proof", "10", "Tester"),
    ("repair", "proof", "11", "Lead · Worker · Tester"),
    ("integrate", "proof", "12b", "Lead · Worker"),
]
QUICK = ("intent", "quick-plan", "workers", "deploy", "test", "integrate")


def read_section(text: str, key: str) -> tuple[str, int, int]:
    heading = re.search(r"(?m)^(#{2,3}) " + re.escape(key) + r"(?:\.|\s)", text)
    if not heading:
        raise ValueError(f"Missing canonical philosophy section {key!r}")
    level = len(heading.group(1))
    end_heading = text.find("\n", heading.end())
    if end_heading < 0:
        raise ValueError(f"Empty canonical philosophy section {key!r}")
    tail = text[end_heading + 1:]
    next_heading = re.search(r"(?m)^#{1," + str(level) + r"} ", tail)
    stop = end_heading + 1 + (next_heading.start() if next_heading else len(tail))
    body = text[end_heading + 1:stop].strip()
    start_line = text.count("\n", 0, heading.start()) + 1
    end_line = text.count("\n", 0, stop)
    return body, start_line, end_line


def create_story(root: Path, sha: str, repo: str) -> dict:
    philosophy = (root / PHILOSOPHY).read_text(encoding="utf-8")
    source_base = f"{repo}/blob/{sha}/"

    def item(identifier: str, group: str, section: str, owner: str) -> dict:
        if section == "review":
            path = "src/common/agents/Reviewer.md"
            original = (root / path).read_text(encoding="utf-8")
            # Use a useful verbatim paragraph without inherited language boilerplate.
            paragraphs = re.split(r"\n\s*\n", original)
            candidates = [p for p in paragraphs if len(p) > 50 and not p.startswith(("#", ">", "Inherit"))]
            body = candidates[0] if candidates else original
            source = source_base + path
        else:
            body, first, last = read_section(philosophy, section)
            source = source_base + PHILOSOPHY + f"#L{first}-L{last}"
            # All three design cards retain canonical source text, not translated copies.
            bullet = {"options": "1", "ideal": "3", "yagni": "4"}.get(identifier)
            if bullet:
                match = re.search(r"(?ms)^" + bullet + r"\. .*?(?=^\d+\. |\Z)", body)
                if match:
                    body = match.group(0).strip()
        if not body:
            raise ValueError(f"No source content for stage {identifier}")
        return {
            "id": identifier, "group": group, "owner": owner,
            "titleKey": f"story.{identifier}.title", "copyKey": f"story.{identifier}.copy",
            "sourceExcerpt": body[:1000] + ("…" if len(body) > 1000 else ""),
            "source": source,
        }

    full = [item(*row) for row in STEPS]
    lookup = {step["id"]: step for step in full}
    lookup["quick-plan"] = item("quick-plan", "plan", "4.1", "Lead")
    quick = [dict(lookup[key]) for key in QUICK]
    # Quick's direct implementation belongs to its execution group; it has the same destination.
    for route in (full, quick):
        for number, step in enumerate(route, 1):
            step["number"] = f"{number:02d}"
    _, first, last = read_section(philosophy, "15")
    return {
        "version": 1, "full": full, "quick": quick,
        "philosophySource": source_base + PHILOSOPHY,
        "gapsSource": source_base + PHILOSOPHY + f"#L{first}-L{last}",
        "sourceText": philosophy,
    }
