#!/usr/bin/env python3
"""Validate the current package and behavior, not mandatory prompt wording."""
from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/"plugins/last-human-commit"

def run(*command:str)->None:
    result=subprocess.run(command,cwd=ROOT,env={**os.environ,"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"})
    if result.returncode: raise SystemExit(result.returncode)

def require(condition:bool,message:str)->None:
    if not condition: raise SystemExit("FAIL: "+message)

router=(ROOT/"AGENTS.md").read_bytes()
# CLAUDE.md is not a second router a person has to remember to edit: the
# publisher copies the bytes of AGENTS.md into it. A difference here is a build
# leftover, so the gate names the command that fixes it instead of asking for
# a hand edit.
require(router==(ROOT/"CLAUDE.md").read_bytes(),
        "CLAUDE.md is stale; it is generated from AGENTS.md - run: python3 scripts/publish_package.py")
# And it stays a copy: the publisher derives it from AGENTS.md, and no projection
# reads CLAUDE.md as a source. Otherwise the router silently gains a second author.
_spec=importlib.util.spec_from_file_location("publish_package",ROOT/"scripts/publish_package.py")
_publisher=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_publisher)
require(("AGENTS.md","CLAUDE.md",()) in _publisher.COPIES,
        "the publisher must generate CLAUDE.md from AGENTS.md - add that copy to COPIES, do not edit CLAUDE.md by hand")
require(not any(source=="CLAUDE.md" for source,_,_ in _publisher.COPIES),
        "CLAUDE.md must not be a projection source again; AGENTS.md is the only authored router")
_router_lines=len(router.decode().splitlines())
require(_router_lines<=300,"automatic entry grew beyond its context budget (hard limit 300 lines)")
if _router_lines>250:
    print(f"warning: AGENTS.md has {_router_lines} lines; the soft limit is 250 - trim before adding more",file=sys.stderr)
for role in ("Lead","Worker","Overseer","Tester","Reviewer","Adviser","Critic","Maintainer"):
    require((ROOT/f"src/common/agents/{role}.md").is_file(),f"missing optional role {role}")
for harness in ("codex","opencode","claude-code","hermes","zcode"):
    folder=ROOT/"adapters"/harness
    manifest=(folder/"adapter.yaml").read_text()
    for field in ("role_source","optional_instructions","subagent_instructions_template"):
        match=re.search(rf"^{field}:\s*(.+)$",manifest,re.MULTILINE)
        require(bool(match and (folder/match.group(1).strip()).exists()),f"{harness} has invalid {field}")
for tool in ("lhc_chat.py","lhc_entry.py","lhc_worktree.py","lhc_time_guard.py","lhc_active_time.py","lhc_task_budget.py","lhc_milestone.py","lhc_outcome.py","lhc_outcome_review.py"):
    path=ROOT/"src/common/tools"/tool
    ast.parse(path.read_text())
    require(path.read_bytes()==(PACKAGE/"tools"/tool).read_bytes(),f"tool projection differs: {tool}")
hooks=json.loads((PACKAGE/"hooks/hooks.json").read_text())["hooks"]
require("SessionStart" in hooks and "PostCompact" in hooks,"automatic entry hooks missing")
require("PostToolUse" in hooks,"time-only plan and direction reminders need the heartbeat hook")
require("UserPromptSubmit" not in hooks,
        "conversation-driven control hooks must stay removed; they vetoed ordinary work")
# The one Stop hook allowed reads plan files only, never the conversation, and holds a stop at most twice.
require(all("--stop-gate" in h["command"] for r in hooks.get("Stop",[]) for h in r["hooks"]),
        "a Stop hook is allowed only as the bounded plan-file stop gate (--stop-gate)")
for groups in hooks.values():
    for group in groups:
        for hook in group["hooks"]:
            require("lhc_entry.py" in hook["command"],"default hook is not the small entrypoint")
run(sys.executable,"plugins/last-human-commit/scripts/sync_skills.py","--check")
run(sys.executable,"plugins/last-human-commit/scripts/validate.py")
run(sys.executable,"-m","pytest","-q","tests","--disable-warnings")
run("sh","tests/test_block_adapter.sh")
print("PASS: current LHC package, automatic entry, optional adapters and complete behavioral suite")
