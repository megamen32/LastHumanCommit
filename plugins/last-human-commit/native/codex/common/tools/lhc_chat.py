#!/usr/bin/env python3
"""Shared project/system mailbox: immutable message files, per-reader cursors."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

MAX_TEXT = 16384

def project_root(repo: Path) -> Path:
    repo = Path(repo).expanduser().resolve()
    from lhc_worktree import absolute_git_dir, common_dir, worktrees
    common = common_dir(repo)
    for entry in worktrees(repo):
        candidate = Path(entry["worktree"])
        if "bare" not in entry and "prunable" not in entry and candidate.exists():
            if absolute_git_dir(candidate) == common:
                return candidate.resolve()
    raise ValueError("No primary checkout; pass the owning project explicitly")

def state_root(repo: Path | None = None) -> Path:
    if repo is None:
        return Path(os.environ.get("LHC_SYSTEM_CHAT_ROOT", str(Path.home()/".agents/shared-session"))).expanduser().resolve()
    return project_root(repo)/".agents/shared-session"

def _key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:32]

def _publish(path: Path, value: dict, *, replace: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent/(".write-"+uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            # link is exclusive and atomic: no shared writer lock, no half file,
            # no accidental overwrite when two writers retry the same message.
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def send(root: Path, sender: str, text: str, *, recipient: str | None = None,
         message_id: str | None = None, reply_to: str | None = None) -> dict:
    if not sender.strip() or not text.strip() or len(text.encode("utf-8")) > MAX_TEXT:
        raise ValueError("sender and text required; text must fit 16 KiB")
    stamp = datetime.now(timezone.utc)
    identity = message_id if message_id is not None else stamp.strftime("%Y%m%dT%H%M%S%fZ-")+uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", identity):
        raise ValueError("invalid message id")
    message = {"id":identity,"at":stamp.isoformat(),"sender":sender,"text":text}
    if recipient: message["to"] = recipient
    if reply_to: message["reply_to"] = reply_to
    path = Path(root)/"chat"/(identity+".json")
    try:
        _publish(path, message)
    except FileExistsError:
        old = json.loads(path.read_text())
        if {k:v for k,v in old.items() if k != "at"} != {k:v for k,v in message.items() if k != "at"}:
            raise ValueError("message id already belongs to different content")
        return old
    return message

def read_new(root: Path, reader: str, *, limit: int = 30) -> list[dict]:
    if not reader.strip() or not 1 <= limit <= 1000:
        raise ValueError("reader required; limit must be 1..1000")
    root = Path(root)
    cursor = root/"readers"/(_key(reader)+".json")
    seen = set(json.loads(cursor.read_text())["seen"]) if cursor.exists() else set()
    result = []
    for path in sorted((root/"chat").glob("*.json")):
        if path.name in seen: continue
        try:
            if path.stat().st_size > MAX_TEXT+4096: continue
            message = json.loads(path.read_text())
            if not isinstance(message, dict) or not all(isinstance(message.get(k),str) for k in ("id","sender","text")): continue
        except (OSError, ValueError):
            continue
        seen.add(path.name)
        if message.get("to") not in (None, reader): continue
        result.append(message)
        if len(result) >= limit: break
    # Remember IDs, not timestamps: a slow concurrent publisher can appear after
    # a later-dated message has already been read. Each reader owns its cursor.
    if seen:
        _publish(cursor, {"reader":reader,"seen":sorted(seen)}, replace=True)
    return result

def presence(root: Path, session: str, state: str, task: str, paths: list[str]) -> dict:
    if state not in ("running","waiting","done") or not session.strip():
        raise ValueError("session and running/waiting/done state required")
    record = {"session":session,"state":state,"task":task,"paths":paths,
              "at":datetime.now(timezone.utc).isoformat()}
    _publish(Path(root)/"sessions"/(_key(session)+".json"), record, replace=True)
    return record

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--repo", type=Path)
    scope.add_argument("--root", type=Path, help="explicit shared authority directory")
    scope.add_argument("--system", action="store_true")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("paths")
    post = commands.add_parser("send")
    post.add_argument("--sender", required=True)
    post.add_argument("--text", help="otherwise read message from stdin")
    post.add_argument("--to"); post.add_argument("--id"); post.add_argument("--reply-to")
    read = commands.add_parser("read")
    read.add_argument("--reader",required=True); read.add_argument("--limit",type=int,default=30)
    status = commands.add_parser("session")
    status.add_argument("--session",required=True); status.add_argument("--state",required=True,choices=("running","waiting","done"))
    status.add_argument("--task",default=""); status.add_argument("--paths",nargs="*",default=[])
    args = parser.parse_args()
    try:
        root = args.root.expanduser().resolve() if args.root else state_root(None if args.system else args.repo or Path.cwd())
        if args.action == "paths": result = {"root":str(root),"chat":str(root/"chat")}
        elif args.action == "send": result = send(root,args.sender,args.text if args.text is not None else sys.stdin.read(MAX_TEXT+1),recipient=args.to,message_id=args.id,reply_to=args.reply_to)
        elif args.action == "read": result = read_new(root,args.reader,limit=args.limit)
        else: result = presence(root,args.session,args.state,args.task,args.paths)
        print(json.dumps(result,ensure_ascii=False))
    except (OSError,ValueError,KeyError) as exc:
        parser.exit(2,str(exc)+"\n")

if __name__ == "__main__": main()
