# Independent gates and time checkpoints

> «overseer должен быть независимым от L … критик должен сам проводить свой
> независимый аудит … удалить kanban.md … каждые 30 команд должно быть одно
> обязательно uptime»

## Objective

Make Overseer and Critic user-governed independent gates over L, remove the
duplicated kanban task surface, normalize stale task states, and require every
long-running agent to perform a time/progress checkpoint at least every 30
commands.

## Business canary

The validator rejects an LHC tree where L can frame an Overseer/Critic verdict,
where `kanban.md` or its instructions remain, where a completed task is still
named `work-*`, or where any agent role lacks the 30-command uptime/progress
checkpoint contract.

## Confirmed scope

- independently reconstruct project-wide user P0 in Overseer and Critic;
- make their stop/rethink decisions binding on L and require unanswered
  questions to block progress;
- keep Adviser as L's obedient bounded advice role;
- repair the stop/rethink protocol used when a gate rejects L's route;
- remove tracked kanban files, templates, references, and duplicate task rules;
- normalize the repository's own completed/incomplete task filenames and state;
- add a harness-neutral `uptime` plus progress checkpoint every 30 commands for
  L and every long-running agent;
- add regression coverage for all contracts above.

## Explicit exclusions

- do not touch `graphify-out/` or unrelated repositories;
- do not deploy or roll out LHC globally in this task;
- do not redesign Worker, Explorer, Reviewer, or Adviser beyond the shared
  checkpoint contract;
- do not add dashboards, permissions, secrets, DB, provider, or log work.

## Cycle and estimate

- Cycle: Full follow-up with the human-selected architecture already approved.
- Optimistic: 35 active minutes.
- Likely: 60 active minutes.
- Pessimistic: 90 active minutes.

## State

Status: complete

## Independent gate history (append-only)

- Gate: Critic
  Decision: RETHINK
  Current user P0: independent user-governed gates, one exact task-state source,
    and mandatory uptime checkpoints.
  Business delta: architecture implemented, but status validation accepted
    arbitrary and compound values.
  P0 distance: CLOSER
  Questions for L: why malformed states were accepted; whether L would make the
    state matrix exact before completion.
  Response: compatibility used `startswith`, which was an oversight. L confirms
    exact `work-* = in progress|blocked` and `done-* = complete` before finish.
- Gate: Overseer
  Decision: RETHINK
  Current user P0: one enforceable LHC governance contract with independent
    user gates, one task-state source, and uptime checkpoints.
  Business delta: primary architecture implemented; five schema and cadence
    contradictions remained.
  P0 distance: CLOSER
  Questions for L: Critic verdict enum, legacy `State`, compound status,
    missing P0 distance, and 30-command versus 30-minute cadence.
  Response: unified the full Critic verdict enum; removed legacy `State`;
    normalized exact statuses; added P0 distance; checkpoint now fires on the
    first of 30 commands or 30 measurable minutes.

## Verification so far

- Red proof: strict status validator rejected the historical compound status.
- Green: `python3 tests/validate.py`.
- Green: `bash tests/test_block_adapter.sh`.
- Green: `python3 -m pytest -q adapters/hermes/plugin/tests` (`4 passed`).
- Green: `python3 -m py_compile tests/validate.py` and `git diff --check`.
- Red: `tests/test_task_states.sh` proved the previous validator accepted a
  `todo-*` task; its first post-fix run also caught an invalid branch that
  applied the done rule to a valid work task.
- Green: `tests/test_task_states.sh` now proves unknown prefixes fail and the
  exact current `work-*`/`done-*` matrix passes.

## L progress checkpoint

- Raw `uptime`: `01:52:56 up 1 day, 4:07, 2 users, load average: 32.04, 32.56, 32.74`.
- Current P0: close the exact LHC governance contract without a third task-state
  namespace or an unproven checkpoint claim.
- Business delta: strict state values, independent gate relay, full Critic
  verdicts, two-limit cadence, and append-only gate schemas are implemented and
  green; unknown task prefixes are now the remaining regression.
- Elapsed: harness task elapsed time is not reliably exposed; checkpoint wall
  time is `01:52:56` Europe/Moscow and host uptime is shown above.
- Blocker: Critic `RETHINK` on unknown task prefixes and missing recorded
  checkpoint.
- Next action: add a red/green unknown-prefix test, rerun all verification, and
  return the evidence to the same Critic.

## Additional gate history

- Gate: Overseer
  Decision: APPROVE
  Current user P0: finish the independent-gate, exact task-state, and uptime
    contract.
  Business delta: prior five contradictions fixed and verified.
  P0 distance: CLOSER
  Questions for L: none.
- Gate: Critic
  Decision: RETHINK
  Current user P0: the same exact contract with no third task namespace and a
    real recorded L checkpoint.
  Business delta: previous blockers fixed; validator still accepted unknown
    task prefixes and the task record lacked the checkpoint evidence.
  P0 distance: CLOSER
  Questions for L: whether any third task prefix is allowed; whether L performed
    and recorded its checkpoint.
  Response: no third prefix is allowed. A fresh `uptime` checkpoint is recorded
    above; a persistent red/green regression now covers the unknown prefix.
- Gate: Critic
  Decision: PASS
  Current user P0: finish one strict LHC contract with independent gates,
    canonical task state, and real checkpoints.
  Business delta: unknown prefixes now fail; exact status matrix, checkpoint
    evidence, independent gates, and all regressions are green.
  P0 distance: CLOSER
  Questions for L: none.
  Proof needed: finalize the same task file, rename it to `done-*`, and rerun
    validation before the completion claim.
- Gate: Overseer
  Decision: APPROVE
  Current user P0: finalize one enforceable LHC contract with independent
    user-controlled gates, one exact task namespace, and real checkpoints.
  Business delta: unknown prefixes are rejected, the checkpoint is durable,
    Critic passed, and the full live test set is green.
  P0 distance: CLOSER
  Questions for L: none.

## Result

- Overseer and Critic independently reconstruct the raw user P0, obey only the
  user, bind L, and must reach the user complete and unchanged.
- STOP/RETHINK resolves conflicting gates strictly and blocks on unanswered
  questions; Adviser remains the compliant bounded advice role.
- Duplicate kanban files are removed. `.agents/tasks/` accepts only exact
  `work-* = in progress|blocked` and `done-* = complete` records.
- All seven roles checkpoint with `uptime` on the first of 30 commands or 30
  measurable minutes.
- Regression proof covers role contracts, exact task state, router markers,
  and Hermes integration. Critic verdict: `PASS`; Overseer verdict: `APPROVE`.
- Actual active time: within the original 35/60/90-minute range.
- Unresolved: none inside confirmed scope. Global rollout is a separate task.
