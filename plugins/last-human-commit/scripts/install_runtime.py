#!/usr/bin/env python3
"""Point supported user instructions to a natively installed LHC package."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid

BEGIN="<!-- lhc-autoentry:begin -->"
END="<!-- lhc-autoentry:end -->"

def configure(home:Path,root:Path,runtime:str,replace_gsd:bool=False)->dict:
    home=home.expanduser().resolve();root=root.expanduser().resolve()
    if not (root/"AGENTS.md").is_file() or not (root/"skills/last-human-commit/SKILL.md").is_file():
        raise ValueError("Select an installed package with its router and skills")
    destinations={"codex":".codex/AGENTS.md","claude":".claude/CLAUDE.md","opencode":".config/opencode/AGENTS.md"}
    file=home/destinations[runtime]
    before=file.read_text() if file.exists() else ""
    text=before
    markers=[("lhc-autoentry","lhc-autoentry"),("last-human-commit","last-human-commit")]
    if replace_gsd:markers.append(("ogsd-autoentry","ogsd-autoentry"))
    for start,end in markers:
        pattern=re.compile(r"<!-- "+re.escape(start)+r":begin -->.*?<!-- "+re.escape(end)+r":end -->\s*",re.S)
        text=pattern.sub("",text)
    pointer=f"{BEGIN}\nFor an engineering request, automatically read `{root/'AGENTS.md'}` once and follow the user's normal language. No LHC command is required. Resume the same task after compaction. This LHC router is the default; other workflow skills are optional methods.\n{END}\n"
    after=text.rstrip()+"\n\n"+pointer
    if before==after:return {"path":str(file),"changed":False,"root":str(root)}
    backup=home/".local/state/last-human-commit/backups"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]+"-"+runtime+".md")
    backup.parent.mkdir(parents=True,exist_ok=True)
    if file.exists():backup.write_text(before)
    file.parent.mkdir(parents=True,exist_ok=True)
    temporary=file.with_name(file.name+".lhc-"+uuid.uuid4().hex)
    try:
        temporary.write_text(after)
        os.replace(temporary,file)
    finally:temporary.unlink(missing_ok=True)
    return {"path":str(file),"changed":True,"root":str(root),"backup":str(backup) if before else None}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',choices=('codex','claude','opencode'),required=True)
    parser.add_argument('--plugin-root',type=Path,required=True)
    parser.add_argument('--home',type=Path,default=Path.home())
    parser.add_argument('--replace-gsd-entry',action='store_true')
    args=parser.parse_args()
    try:print(json.dumps(configure(args.home,args.plugin_root,args.runtime,args.replace_gsd_entry),ensure_ascii=False))
    except (OSError,ValueError) as error:parser.exit(2,str(error)+'\n')
if __name__=='__main__':main()
