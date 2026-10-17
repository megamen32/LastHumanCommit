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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event',default='SessionStart')
    parser.add_argument('--root',type=Path)
    args=parser.parse_args()
    try:
        event=json.loads(sys.stdin.read(65536) or '{}')
    except ValueError:
        event={}
    root=args.root or Path(__file__).resolve().parents[1]
    if args.event == 'UserPromptSubmit':
        # Universal Claude-compatible stdout context, accepted by clients that
        # do not expose a structured UserPromptSubmit hook result.
        print(context_for(event,root))
    else:
        print(json.dumps({'hookSpecificOutput':{'hookEventName':args.event,
              'additionalContext':context_for(event,root)}}))

if __name__=='__main__': main()
