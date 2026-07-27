# Kanban

The kanban is a pointer board, not a storage format. Every real task is one
file under `.agents/tasks/`. Status is encoded in the filename prefix:

- `.agents/tasks/todo-{id}.md` — accepted, not started.
- `.agents/tasks/wip-{id}.md`  — in progress.
- `.agents/tasks/done-{id}.md` — finished, retained for audit.

State transitions are `git mv` only; do not edit-and-rename in place. The
working tree is the lock, the commit is the audit trail. Tasks are versioned,
diffable, greppable. No SaaS task tracker, no API latency, no race condition.

Priority header below picks which `tasks/` entries to surface. Each line under
the header is `path — owner — one-line status`. Bodies live in the file, not in
this board.

## P0_URGENT
<!-- Empty unless a real urgent user-visible P0 exists. -->

## CORE

## BEST_EFFORT

## OPT_IN
<!-- Requires explicit user choice. -->