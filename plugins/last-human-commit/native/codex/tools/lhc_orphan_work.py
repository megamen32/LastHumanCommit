#!/usr/bin/env python3
"""Verdict on uncommitted and untracked files: is there an owner, or are they orphaned?

Facts in, JSON out (exit status 0; the verdict is in the JSON). Nothing here changes a file.

For every dirty or untracked file of every worktree of the repository the tool decides:

* owner=active: a live session works in that directory (an LHC native heartbeat in
  .agents/shared-session/learning, a Codex rollout or an OpenCode session whose cwd covers the file,
  seen within --quiet-minutes), or the file itself was written within --quiet-minutes and no
  session record can say whose it is. Instruction: do not touch it, contact the session through
  SendMessage (or wait for the quiet time to pass for a file without a session).
* owner=none: no such session and the file is older than --quiet-minutes. Instruction: there is
  no owner; review it, run the tests, commit it on your own task branch and take it to a PR;
  do not ask the owner.

Uncertainty (an unreadable heartbeat, no session records at all) is never "ambiguous": it falls back
to the age of the file's mtime.

  lhc_orphan_work.py --repo PATH [--quiet-minutes 30] [--me SESSION_ID]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lhc_dispatcher as dispatcher  # noqa: E402
import lhc_worktree as worktree  # noqa: E402

BOOKKEEPING = (".agents/shared-session/", ".agents/mail/", ".agents/sessions.json")
NONE_RULE = ("no owner: review it, run the tests, commit it on your own task branch and take it to a PR; "
             "do not ask the owner")
ACTIVE_RULE = "do not touch: contact the owning session through SendMessage"
RECENT_RULE = ("do not touch yet: written {age} min ago by a writer no session record names; "
               "check again after {wait} more min, then it has no owner")


def covers(cwd: str, path: Path) -> bool:
    try:
        path.resolve().relative_to(Path(cwd).resolve())
    except (ValueError, OSError):
        return False
    return True


def dirty_files(root: Path) -> list[dict]:
    done = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "-z", "-uall"],
                          capture_output=True, text=True, timeout=30)
    if done.returncode != 0:
        return []
    fields = done.stdout.split("\0")
    files, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        status, name = entry[:2], entry[3:]
        if status[0] in "RC":
            i += 1  # the source name of a rename or copy follows
        if not name.startswith(BOOKKEEPING):
            files.append({"path": name, "status": status})
    return files


def mtime_of(root: Path, name: str) -> float | None:
    """Own mtime, else that of the nearest existing parent (a deleted file has none)."""
    path = root / name
    while True:
        try:
            return path.stat().st_mtime
        except OSError:
            if path == root or path.parent == path:
                return None
            path = path.parent


def heartbeats(roots: list[Path]) -> tuple[list[dict], int]:
    """LHC native heartbeats; the count of unreadable ones is the uncertainty."""
    found, unreadable, seen_files = [], 0, set()
    for root in roots:
        for item in sorted((root / ".agents" / "shared-session" / "learning").glob("*.json")):
            if item in seen_files:
                continue
            seen_files.add(item)
            try:
                timer = json.loads(item.read_text(encoding="utf-8")).get("native_heartbeat") or {}
                if not timer:
                    continue
                seen = datetime.fromisoformat(str(timer["last_seen_at"])).timestamp()
                found.append({"id": str(timer["session_id"]), "runtime": str(timer.get("runtime", "")),
                              "cwd": str(timer["cwd"]), "seen": seen, "source": "lhc-heartbeat"})
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                unreadable += 1
    return found, unreadable


def live_sessions(roots: list[Path], since: float) -> list[dict]:
    def inside(cwd: str) -> bool:
        return bool(cwd) and any(covers(str(r), Path(cwd)) or covers(cwd, r) for r in roots)
    live = dispatcher.codex_live("", since, match=inside) + dispatcher.opencode_live("", since, match=inside)
    return [{**s, "source": s["runtime"] + "-session"} for s in live]


def judge(root: Path, item: dict, sessions: list[dict], now: float, quiet: int) -> dict:
    path = root / item["path"]
    stamp = mtime_of(root, item["path"])
    age = None if stamp is None else max(0, int((now - stamp) // 60))
    row = {"path": str(path), "git_status": item["status"], "mtime_age_min": age}
    active = [s for s in sessions if now - s["seen"] <= quiet * 60 and covers(s["cwd"], path)]
    if active:
        who = max(active, key=lambda s: s["seen"])
        row["owner"] = {"state": "active", "who": who["id"], "runtime": who["runtime"], "source": who["source"],
                        "seen_min_ago": int((now - who["seen"]) // 60)}
        row["instruction"] = ACTIVE_RULE
    elif age is not None and age < quiet:
        row["owner"] = {"state": "active", "who": "unknown writer", "source": "mtime", "seen_min_ago": age}
        row["instruction"] = RECENT_RULE.format(age=age, wait=quiet - age)
    else:
        row["owner"] = {"state": "none", "source": f"no session and quiet for {quiet}+ min"}
        row["instruction"] = NONE_RULE
    return row


def verdict(repo: Path, quiet: int = 30, me: str = "", now: float | None = None) -> dict:
    now = now or time.time()
    roots = [Path(r["worktree"]) for r in worktree.worktrees(repo) if "bare" not in r and Path(r["worktree"]).is_dir()]
    beats, unreadable = heartbeats(roots)
    sessions = [s for s in beats + live_sessions(roots, now - quiet * 60) if s["id"] != me]
    rows = []
    for root in roots:
        for item in dirty_files(root):
            row = judge(root, item, sessions, now, quiet)
            row["worktree"] = str(root)
            rows.append(row)
    states = {r["owner"]["state"] for r in rows}
    overall = "clean" if not rows else "none" if states == {"none"} else "active" if states == {"active"} else "mixed"
    orphans = [r["path"] for r in rows if r["owner"]["state"] == "none"]
    return {"repo": str(repo), "quiet_minutes": quiet, "overall": overall,
            "checked": {"worktrees": len(roots), "sessions_seen": len(sessions), "unreadable_heartbeats": unreadable,
                        "fallback": "mtime age"},
            "orphans": orphans, "orphan_instruction": NONE_RULE if orphans else "", "files": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--quiet-minutes", type=int, default=30)
    parser.add_argument("--me", default="", help="this session's id: its own heartbeat is not another owner")
    args = parser.parse_args()
    try:
        result = verdict(args.repo.resolve(), args.quiet_minutes, args.me)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
