#!/usr/bin/env python3
"""Validate the current package and behavior, not mandatory prompt wording."""
from __future__ import annotations
import ast
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
require(router==(ROOT/"CLAUDE.md").read_bytes(),"agent and Claude routers differ")
require(len(router.decode().splitlines())<=150,"automatic entry grew beyond its context budget")
for role in ("Lead","Worker","Overseer","Tester","Reviewer","Adviser","Critic"):
    require((ROOT/f"src/common/agents/{role}.md").is_file(),f"missing optional role {role}")
for harness in ("codex","opencode","claude-code","hermes","zcode"):
    folder=ROOT/"adapters"/harness
    manifest=(folder/"adapter.yaml").read_text()
    for field in ("role_source","optional_instructions","subagent_instructions_template"):
        match=re.search(rf"^{field}:\s*(.+)$",manifest,re.MULTILINE)
        require(bool(match and (folder/match.group(1).strip()).exists()),f"{harness} has invalid {field}")
for tool in ("lhc_chat.py","lhc_entry.py","lhc_worktree.py","lhc_time_guard.py","lhc_active_time.py","lhc_task_budget.py","lhc_milestone.py"):
    path=ROOT/"src/common/tools"/tool
    ast.parse(path.read_text())
    require(path.read_bytes()==(PACKAGE/"tools"/tool).read_bytes(),f"tool projection differs: {tool}")
hooks=json.loads((PACKAGE/"hooks/hooks.json").read_text())["hooks"]
require("SessionStart" in hooks and "UserPromptSubmit" in hooks,"automatic entry hooks missing")
require("PostToolUse" in hooks and "Stop" in hooks,"mandatory business checkpoints must have active and idle lifecycle hooks")
for groups in hooks.values():
    for group in groups:
        for hook in group["hooks"]:
            require("lhc_entry.py" in hook["command"],"default hook is not the small entrypoint")
run(sys.executable,"plugins/last-human-commit/scripts/sync_skills.py","--check")
run(sys.executable,"plugins/last-human-commit/scripts/validate.py")
run(sys.executable,"-m","pytest","-q","tests","--disable-warnings")
run("sh","tests/test_block_adapter.sh")
print("PASS: current LHC package, automatic entry, optional adapters and complete behavioral suite")
