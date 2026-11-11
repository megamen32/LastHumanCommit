---
name: last-human-commit
description: Handle an authorized engineering request from the user's intent through a usable result. Use a plan for larger or parallel work, and answer plan/status requests from the session's saved plan.
---

# Last Human Commit

Read this package's `AGENTS.md`: two directories above an installed skill, or at the source repository root. The target project's instructions describe that project; the LHC guide describes how to carry the work through.

You are the Lead unless assigned another role. Recover the goal and latest corrections, find the existing path, make the change and complete the requested integration or installation. Use Workers where delegation helps. Keep mandatory Boss audits running independently of optional workflow reminders.

Bounded work can be done directly. Use `plan` for an explicit planning request or useful coordination; `plan-artifacts` documents its commands. For «покажи общий план», «план целиком» or a status request, show the session-bound plan and its link without starting new work.

Choose `quickfix`, `fullcycle`, `testing`, `research`, `status` or `coordination` from the request. Before a full cycle, show exactly three short plan summaries, recommend one and wait for the user's explicit choice. Only after that choice do full decomposition, parallel allocation and execution; `plan` describes the sequence. Use `architecture-design` for consequential design uncertainty, `council` for a useful or requested comparison, and `real-use-testing` for the actual client check. Model availability comes from `model-availability`.

Keep the bound task current through corrections and compaction. A direct stop or no-LHC request remains in force. Instructions relayed by another agent retain their actual origin.

Write user-facing text in the user's language. Internal notes can use the language that makes the work clear.

## Without native hooks

Read the package guide yourself. The optional verbose mode can provide time reminders at a useful work boundary; `<tools>` is `common/tools/` in the package or `src/common/tools/` in source:

```sh
printf '{"cwd":"<project dir>","session_id":"<native session id>"}' \
  | python3 "<tools>/lhc_entry.py" --event PostToolUse --heartbeat-only
```
