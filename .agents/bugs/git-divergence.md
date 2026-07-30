# Published history diverges from local canon

Description: Local main is seven commits ahead and one stale README commit
behind origin/main.
Evidence: `git rev-list --left-right --count origin/main...HEAD` returns `1 7`;
`git merge-tree` predicts one README conflict.
Blocks: `.agents/tasks/work-20260730-text-canon-yagni.md`

