# Instructions: on any edit this file then commit it.

# Task Layer

## Before Start

Fill this layer before work begins. Workflow is the ordered chain for this task,
not a list of every possible role. Add, remove, or name custom stages now.

Description:
Severity: P0_URGENT | CORE | BEST_EFFORT | OPT_IN
workflow: [e.g. explore(Explorer) -> work(Worker) -> review(Reviewer) -> commit(Lead); any custom stage(actor)]
estimated min-max complete time: (min: , max: )
Acceptance: [proof]

## On Start

Fill this layer when the first workflow stage starts.
DO `git mv todo-<id>.md work-<id>.md`.
On every handoff, replace the current executor identity and Next action, then
commit this file.

started (UTC+3): [ISO-8601]
Executor: [agent name or ID]
PID: [process ID]
Harness: [opencode | claude | codex | zcode | vscode | other]
session identifier: [session ID]
Next action: [current workflow stage and its concrete next action]

# Message layer

## Notes

[append decisions, stage results, handoffs, and information learned during work]

## Blocker

[none, `.agents/bugs/<id>.md`, or exact user decision]

# When complete

Fill this layer only after the workflow and Acceptance are complete.

## Result

[full durable result of the task; this file must remain sufficient if every
agent message or chat response is lost]

## Completion checklist

- [ ] Every selected workflow stage is complete or its omission is explained.
- [ ] Acceptance is proven with exact commands, immutable artifacts, or paths.
- [ ] Blockers are resolved or explicitly retained.
- [ ] Result contains the full handoff and does not depend on a delivered agent message.
- [ ] DO `git mv work-<id>.md done-<id>.md` and commit this file.
