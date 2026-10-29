#!/usr/bin/env python3
"""The orchestrator's agenda from facts, not from a prompt that goes stale.

The registry (.agents/sessions.json in the primary checkout) says what the owner's
sessions are for. The live sources (Codex rollout files, the OpenCode database) say
which sessions are working right now. tick puts the two side by side and prints one
line per thing that needs an action. Nothing here decides or changes a session.

Commands: tick | init ID | set ID [fields] | archive [--hours N]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lhc_mail as mail  # noqa: E402

IDLE = 7200      # seconds without activity before a working session counts as silent
LOOKBACK = 86400  # live sources are read for this long
STATES = ("working", "blocked", "accepted", "released")


def iso(value=None):
    return datetime.fromtimestamp(value or time.time(), timezone.utc).isoformat(timespec="seconds")


def reg_file(root):
    return Path(root) / ".agents" / "sessions.json"


def load(root):
    try:
        doc = json.loads(reg_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    if not isinstance(doc, dict):
        doc = {}
    doc.setdefault("orchestrator", "")
    doc.setdefault("sessions", [])
    return doc


def save(root, doc):
    path = reg_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc["updated"] = iso()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def upsert(doc, sid, **fields):
    row = next((r for r in doc["sessions"] if r.get("id") == sid), None)
    if row is None:
        row = {"id": sid, "status": "working"}
        doc["sessions"].append(row)
    for key, value in fields.items():
        if value is not None:
            row[key] = value
    if row.get("status") not in STATES:
        raise ValueError("status must be one of " + ", ".join(STATES))
    row["last_seen"] = iso()
    return row


def archive(root, hours=6, now=None):
    """Move finished rows out of the registry: it holds the current state, not a log."""
    now = now or time.time()
    doc = load(root)
    keep, gone = [], []
    for row in doc["sessions"]:
        seen = _epoch(row.get("last_seen"))
        done = row.get("status") in ("accepted", "released")
        (gone if done and seen is not None and now - seen > hours * 3600 else keep).append(row)
    if gone:
        old = reg_file(root).with_name("sessions-archive.jsonl")
        with old.open("a", encoding="utf-8") as handle:
            for row in gone:
                handle.write(json.dumps({**row, "archived": iso(now)}, ensure_ascii=False) + "\n")
        doc["sessions"] = keep
        save(root, doc)
    return gone


def _epoch(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _cwd_of(rollout):
    with open(rollout, "rb") as handle:
        first = handle.readline(600_000)
    try:
        return str(json.loads(first).get("payload", {}).get("cwd") or "")
    except ValueError:
        return ""


def _belongs(cwd, project):
    return bool(cwd) and project.lower() in (part.lower() for part in Path(cwd).parts)


def codex_live(project, since, home=None):
    base = Path(home or os.environ.get("LHC_CODEX_HOME") or Path.home() / ".codex") / "sessions"
    found = []
    for rollout in base.glob("*/*/*/rollout-*.jsonl"):
        try:
            seen = rollout.stat().st_mtime
        except OSError:
            continue
        if seen < since:
            continue
        cwd = _cwd_of(rollout)
        if _belongs(cwd, project):
            found.append({"id": rollout.stem[-36:], "name": Path(cwd).name, "runtime": "codex", "seen": seen})
    return found


def opencode_live(project, since, database=None):
    path = Path(database or os.environ.get("LHC_OPENCODE_DB") or Path.home() / ".local/share/opencode/opencode.db")
    if not path.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        rows = con.execute("select id, title, directory, time_updated from session_v2 "
                           "where parent_id is null and time_updated > ?", (int(since * 1000),)).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [{"id": sid, "name": title or "", "runtime": "opencode", "seen": updated / 1000}
            for sid, title, directory, updated in rows if _belongs(directory, project)]


def live_sessions(root, now=None):
    since = (now or time.time()) - LOOKBACK
    project = Path(root).resolve().name
    return codex_live(project, since) + opencode_live(project, since)


def tick(root, live, now=None, idle=IDLE):
    """One line per thing that needs the orchestrator to act. Empty means nothing does."""
    now = now or time.time()
    doc = load(root)
    here = {s["id"]: s for s in live}
    rows = {r.get("id"): r for r in doc["sessions"]}
    lines = []
    for row in doc["sessions"]:
        if row.get("status") not in ("working", "blocked"):
            continue
        sid, task = row.get("id"), row.get("task", "")
        seen = here.get(sid, {}).get("seen")
        quiet = None if seen is None else int((now - seen) // 60)
        if seen is None:
            lines.append(f"DEAD {sid} {row.get('name', '')}: registered as {row.get('status')}, no live session. "
                         f"Accept its result or start a replacement. Task: {task}")
        elif now - seen > idle:
            lines.append(f"SILENT {sid} {row.get('name', '')}: quiet for {quiet} min. Send its L one concrete step. Task: {task}")
        else:
            lines.append(f"RUNNING {sid} {row.get('name', '')}: active {quiet} min ago. "
                         f"Is the acceptance closer ({row.get('acceptance', 'not set')})? Next: {row.get('next', 'not set')}")
    for sid, session in here.items():
        if sid not in rows and sid != doc.get("orchestrator") and now - session["seen"] <= idle:
            lines.append(f"UNREGISTERED {sid} {session['name']} ({session['runtime']}, active "
                         f"{int((now - session['seen']) // 60)} min ago): ask what it is for and register it, "
                         "or leave it if it is not the owner's.")
    for sid in [doc.get("orchestrator")] + list(rows):
        waiting = mail.inbox(root, sid) if sid else []
        if waiting:
            lines.append(f"MAIL {sid}: {len(waiting)} unread, oldest {waiting[0].name}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    tk = sub.add_parser("tick")
    tk.add_argument("--idle-min", type=int, default=IDLE // 60)
    init = sub.add_parser("init")
    init.add_argument("id")
    st = sub.add_parser("set")
    st.add_argument("id")
    for field in ("name", "host", "task", "acceptance", "status", "next"):
        st.add_argument("--" + field)
    ar = sub.add_parser("archive")
    ar.add_argument("--hours", type=int, default=6)
    args = parser.parse_args(argv)
    root = (args.root or mail.primary_root(Path.cwd())).resolve()
    if args.cmd == "tick":
        doc = load(root)
        age = "never" if not reg_file(root).exists() else f"{int((time.time() - reg_file(root).stat().st_mtime) // 60)} min ago"
        print(f"registry updated {age}; {len(doc['sessions'])} sessions; orchestrator {doc.get('orchestrator') or 'not set'}")
        lines = tick(root, live_sessions(root), idle=args.idle_min * 60)
        print("\n".join(lines) if lines else "nothing needs an action")
    elif args.cmd == "init":
        doc = load(root)
        doc["orchestrator"] = args.id
        save(root, doc)
    elif args.cmd == "set":
        doc = load(root)
        upsert(doc, args.id, name=args.name, host=args.host, task=args.task,
               acceptance=args.acceptance, status=args.status, next=args.next)
        save(root, doc)
    else:
        for row in archive(root, args.hours):
            print("archived", row.get("id"), row.get("name", ""))


if __name__ == "__main__":
    main()
