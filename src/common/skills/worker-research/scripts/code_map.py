#!/usr/bin/env python3
"""Maintain a bounded, rewritable project-local map of verified code locations."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
MAX_ENTRIES = 256
MAX_LOCATIONS = 24
MAX_EVIDENCE = 12
MAX_SUMMARY_CHARS = 2_000
KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")
KINDS = (
    "production-path",
    "ownership",
    "configuration",
    "test-path",
    "decision",
    "failure-shield",
)


def find_project_root(start: Path) -> Path:
    """Find the nearest project carrying the shared `.agents` state root."""

    current = start.expanduser().resolve()
    for root in (current, *current.parents):
        if (root / ".agents").is_dir():
            return root
    raise ValueError(f"no .agents directory found from {current}")


def paths(root: Path) -> tuple[Path, Path]:
    store = root / ".agents/shared-session/knowledge/code-map.json"
    return store, store.with_suffix(".lock")


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "entries": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported code-map schema at {path}")
    entries = value.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"code-map entries must be an object at {path}")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=2,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def parse_location(root: Path, raw: str) -> dict[str, Any]:
    path_text, separator, symbol = raw.partition("::")
    candidate = Path(path_text).expanduser()
    absolute = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if absolute != root and root not in absolute.parents:
        raise ValueError(f"location escapes project root: {path_text}")
    relative = absolute.relative_to(root).as_posix() if absolute != root else "."
    exists = absolute.exists()
    kind = "file" if absolute.is_file() else "directory" if absolute.is_dir() else "missing"
    return {
        "path": relative,
        "symbol": symbol.strip() if separator else "",
        "observed_kind": kind,
        "observed_sha256": file_digest(absolute) if absolute.is_file() else "",
        "exists_at_verification": exists,
    }


def inspect_entry(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    locations = []
    overall = "fresh"
    for saved in entry.get("locations", []):
        absolute = (root / str(saved.get("path") or "")).resolve()
        if absolute != root and root not in absolute.parents:
            status = "outside-root"
        elif not absolute.exists():
            status = "missing"
        elif saved.get("observed_kind") == "file" and not absolute.is_file():
            status = "type-changed"
        elif saved.get("observed_kind") == "directory" and not absolute.is_dir():
            status = "type-changed"
        elif absolute.is_file() and saved.get("observed_sha256") != file_digest(absolute):
            status = "content-changed"
        else:
            status = "fresh"
        if status != "fresh":
            overall = "stale"
        locations.append({**saved, "status": status})
    return {**entry, "freshness": overall, "locations": locations}


def locked_update(root: Path, callback: Any) -> Any:
    store, lock = paths(root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        state = load(store)
        result = callback(state)
        atomic_write(store, state)
        return result


def command_upsert(args: argparse.Namespace, root: Path) -> int:
    if not KEY.fullmatch(args.key):
        raise ValueError("key must be lowercase letters, digits, dot, underscore, or hyphen")
    summary = args.summary.strip()
    if not summary or len(summary) > MAX_SUMMARY_CHARS:
        raise ValueError(f"summary must contain 1..{MAX_SUMMARY_CHARS} characters")
    if not args.location or len(args.location) > MAX_LOCATIONS:
        raise ValueError(f"provide 1..{MAX_LOCATIONS} locations")
    if len(args.evidence) > MAX_EVIDENCE:
        raise ValueError(f"provide no more than {MAX_EVIDENCE} evidence items")
    locations = [parse_location(root, raw) for raw in args.location]
    if args.confidence == "verified" and not all(
        location["exists_at_verification"] for location in locations
    ):
        raise ValueError(
            "verified entries require existing locations; use --confidence inferred"
        )

    def update(state: dict[str, Any]) -> dict[str, Any]:
        entries = state["entries"]
        if args.key not in entries and len(entries) >= MAX_ENTRIES:
            raise ValueError(
                f"code map already has {MAX_ENTRIES} entries; consolidate or remove stale keys"
            )
        entry = {
            "key": args.key,
            "kind": args.kind,
            "summary": summary,
            "confidence": args.confidence,
            "locations": locations,
            "evidence": [item.strip() for item in args.evidence if item.strip()],
            "verified_at": datetime.now().astimezone().isoformat(),
            "git_head": git_head(root),
        }
        entries[args.key] = entry
        return entry

    entry = locked_update(root, update)
    print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
    return 0


def score(entry: dict[str, Any], terms: list[str]) -> int:
    key = str(entry.get("key") or "").casefold()
    summary = str(entry.get("summary") or "").casefold()
    haystack = json.dumps(entry, ensure_ascii=False, sort_keys=True).casefold()
    total = 0
    for term in terms:
        if term in key:
            total += 10
        if term in summary:
            total += 5
        total += min(haystack.count(term), 5)
    return total


def render(entry: dict[str, Any]) -> str:
    lines = [
        f"[{entry['freshness'].upper()}] {entry['key']} "
        f"({entry.get('kind')}, {entry.get('confidence')})",
        str(entry.get("summary") or ""),
    ]
    for location in entry.get("locations", []):
        symbol = f"::{location['symbol']}" if location.get("symbol") else ""
        lines.append(f"- {location.get('path')}{symbol} [{location.get('status')}]")
    return "\n".join(lines)


def command_search(args: argparse.Namespace, root: Path) -> int:
    store, _ = paths(root)
    entries = list(load(store)["entries"].values())
    terms = [term.casefold() for raw in args.query for term in raw.split() if term]
    ranked = sorted(
        ((score(entry, terms), entry) for entry in entries),
        key=lambda item: (-item[0], str(item[1].get("key") or "")),
    )
    selected = [inspect_entry(root, entry) for value, entry in ranked if not terms or value > 0]
    selected = selected[: args.limit]
    if args.json:
        print(json.dumps(selected, ensure_ascii=False, indent=2, sort_keys=True))
    elif selected:
        print("\n\n".join(render(entry) for entry in selected))
    else:
        print("no matching code-map entries")
    return 0


def command_check(args: argparse.Namespace, root: Path) -> int:
    store, _ = paths(root)
    entries = load(store)["entries"]
    selected = entries if not args.key else {key: entries[key] for key in args.key if key in entries}
    checked = [inspect_entry(root, entry) for entry in selected.values()]
    if args.json:
        print(json.dumps(checked, ensure_ascii=False, indent=2, sort_keys=True))
    elif checked:
        print("\n\n".join(render(entry) for entry in checked))
    else:
        print("no code-map entries selected")
    return 2 if any(entry["freshness"] == "stale" for entry in checked) else 0


def command_remove(args: argparse.Namespace, root: Path) -> int:
    def update(state: dict[str, Any]) -> bool:
        return state["entries"].pop(args.key, None) is not None

    removed = locked_update(root, update)
    print(json.dumps({"key": args.key, "removed": removed}, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path.cwd())
    commands = result.add_subparsers(dest="command", required=True)

    upsert = commands.add_parser("upsert", help="replace one stable knowledge key")
    upsert.add_argument("--key", required=True)
    upsert.add_argument("--kind", choices=KINDS, required=True)
    upsert.add_argument("--summary", required=True)
    upsert.add_argument("--location", action="append", default=[])
    upsert.add_argument("--evidence", action="append", default=[])
    upsert.add_argument("--confidence", choices=("verified", "inferred"), default="verified")

    search = commands.add_parser("search", help="rank reusable findings")
    search.add_argument("query", nargs="*")
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--json", action="store_true")

    check = commands.add_parser("check", help="check saved locations for drift")
    check.add_argument("--key", action="append", default=[])
    check.add_argument("--json", action="store_true")

    remove = commands.add_parser("remove", help="delete one invalid knowledge key")
    remove.add_argument("--key", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        root = find_project_root(args.root)
        return {
            "upsert": command_upsert,
            "search": command_search,
            "check": command_check,
            "remove": command_remove,
        }[args.command](args, root)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        raise SystemExit(f"code map error: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
