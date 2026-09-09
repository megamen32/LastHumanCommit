---
name: last-human-commit
description: Use for engineering tasks that need the Last Human Commit workflow, bounded roles, and a real product canary.
---

# Last Human Commit

Use this skill when an engineering task needs the LHC workflow. Start each
cycle from the current objective, current repository state, and current
product and LHC feedback. Read `../../AGENTS.md` from this installed package,
then follow the assigned role package under `common/agents/` and its referenced
`common/protocols/` and `common/skills/` files. Use the package's bundled tools,
including `common/tools/lhc_worktree.py`, when the role requires them.

Do not read or depend on a legacy external store. Keep the user outcome and
shortest real canary explicit, preserve unrelated work, and report evidence.
