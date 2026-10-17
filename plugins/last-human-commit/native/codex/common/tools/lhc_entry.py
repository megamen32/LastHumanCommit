#!/usr/bin/env python3
"""Small fail-open native context hook; never starts a session or creates tasks."""
import argparse
import json
from pathlib import Path
import sys

def context_for(event, root):
    root = Path(root).resolve()
    context = (f"LHC engineering workflow: {root/'AGENTS.md'}. "
               "For an engineering request, read that router once and work from the user's normal language; no slash command or setup interview is needed. "
               "Plain questions need no workflow. Preserve the current objective and user corrections after compaction. "
               "Use a project worktree when another session can write to the same repository; keep doing independent work before waiting. "
               "Use the shared file-per-message chat when Herder is unavailable. This hook adds context only, not another agent or supervisor.")
    return context

def main():
    import io
    import os
    import lhc_time_guard as guard
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event',default='SessionStart')
    parser.add_argument('--root',type=Path)
    parser.add_argument('--runtime',choices=('codex','claude'),default='claude' if os.environ.get('CLAUDE_PROJECT_DIR') else 'codex')
    args=parser.parse_args()
    try:
        event=json.loads(sys.stdin.read(65536) or '{}')
    except ValueError:
        event={}
    if not isinstance(event,dict):event={}
    if event.get("agent_id"):
        event["session_id"] = str(event.get("session_id") or "unknown") + ":subagent:" + str(event["agent_id"])
    root=args.root or Path(__file__).resolve().parents[1]
    contexts=[]
    if args.event in ('SessionStart','UserPromptSubmit','PostCompact'):
        contexts.append(context_for(event,root))
    try:
        sys.stdin=io.StringIO(json.dumps(event))
        result=guard.hook(argparse.Namespace(runtime=args.runtime,event=args.event,now=None,idle_cap_seconds=300,session_only=True)) or {}
        context=result.get('hookSpecificOutput',{}).get('additionalContext') or result.get('prompt') or result.get('systemMessage')
        if context:contexts.append(context)
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('LHC checkpoint unavailable: '+type(error).__name__+'; perform the due review manually.',file=sys.stderr)
    if contexts:
        print(json.dumps({'hookSpecificOutput':{'hookEventName':args.event,'additionalContext':'\n\n'.join(contexts)}}))

if __name__=='__main__': main()
