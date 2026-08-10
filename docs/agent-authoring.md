# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical marker-delimited routers.
`Lead.md` owns orchestration. Every other role file is a self-contained child
prompt.

## Non-negotiable shape

- One request uses one Markdown `.agents/tasks/` lineage: copy `todo-*` to `work-*`, then
  copy `work-*` to `done-*`, committing each snapshot and preserving all earlier
  copies. Never `git mv`, rename, or delete a lifecycle snapshot; the latest
  committed snapshot is current. Only L writes the task content. Never add a
  child todo, separate handoff file, duplicate kanban, spec, ledger, recovery
  file, or review package.
- L is an orchestrator by default. It may execute only an obvious <=5-minute
  Direct action. Short and Full repository search and code belong to Worker.
- There is no Explorer role. Worker uses `mode: research` and `mode: implement`;
  implementation names `bugfix/TDD` or `feature`.
- Every Worker assignment has one acceptance gate and maximum <=20 active
  minutes. A whole task above one hour must be an explicit graph of understood
  <=20-minute slices.
- Estimates are `minimum / maximum`, never a three-value report. Keep the initial
  range immutable. A maximum overrun requires an Overseer verdict before continuation.
- Overseer is mandatory for every task and normally continues from the
  persistent shared-session files; fresh/no-history is only recovery or an
  explicitly requested independent audit. Event-triggered audits are never
  suppressed by a 30-minute cooldown.
- Full is reserved for researched work over 30 minutes with material product,
  architecture, migration, or expensive-wrong-path impact.
- Full always preserves three Russian plans, first selection, full technical
  preview, and second explicit approval. Never remove call-stack tree, file-tree
  diff, key signatures, pseudocode, migration, canary, or execution graph.
- `YAGNI 80/20` is a complete third plan, not an unfinished MVP or a partial
  delivery state.
- Reviewer sees only task-owned diff; Tester is the fresh real-user gate before
  Critic; Critic independently gates release or irreversible action.
- Silence never authorizes deploy, rollback, destructive action, branch, or
  worktree operations.

## Workspace ownership

Routine work stays in the primary checkout. An auxiliary worktree, detached
HEAD, or non-default branch is reported in the first visible update. With
explicit authorization, a new worktree may exist only under
`<primary-project-root>/.worktrees/<task-slug>`. Foreign edits are preserved but
never silently staged or committed with the current task.

## Prompt ownership

- The router names roles and paths but does not duplicate their workflows.
- L sends one role/mode and compact assignment; children append detailed
  evidence to the assigned task file and return only TL;DR to L.
- Profiles supplement an assigned role. Protocols load only on their trigger.
- Templates are views of the same root task, not a second workflow.
- `profiles/Code.md` deliberately owns code-as-docs, structured/rotated logs,
  cross-platform rules, file-size limits, and dated legacy removal.
- Adapter syntax for Codex, OpenCode, Claude Code, Hermes, and ZCode stays in adapters; portable behavior stays in common roles.
- Worker research may resume into implementation. Independent gates start fresh.
- AskHuman/AskSecret render only when the exact active capability is attested.

## Changing instructions

1. Change the file that owns the rule.
2. Align only direct references, templates, adapters, and validation.
3. Keep runtime prompts concise; tests may enforce invariants instead of
   repeating prose everywhere.
4. Review the diff, run `git diff --check`, and run
   `python3 tests/validate.py`.

The marker lines are the ownership boundary. Preserve every byte outside them.
`scripts/lhc-block` remains an explicit marker utility, not an installer,
daemon, scheduler, or harness manager.
