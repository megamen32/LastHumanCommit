# Time and progress

Keep the original task start and estimate visible. Separate measured active work, elapsed clock time, estimated effort and external waiting. A new card, stage or compaction does not restart the task's history.

## Existing reminders

| Interval | Useful question |
| --- | --- |
| 20 minutes for a running Worker | What changed, what is blocked and what comes next? |
| 30 minutes | Does the saved plan reflect the work? |
| 60 minutes | Are we still moving toward the user's latest goal? |
| 120 minutes of unfinished work | Is there a repeated method problem worth correcting? |

Use these as prompts to inspect relevant facts, not as a schedule of new reports or review sessions. Update changed state, remove a useless step or correct the route when needed. Report material progress to the user.

OpenCode 2's native Boss runs independently about every 30 minutes of observed active work. It reads the original goal, corrections and recent visible work, with available history in a file. Its complete prose goes into the parent session. Other runtimes do not acquire this capability merely by reading the role.

The ordinary PostToolUse heartbeat observes work boundaries. Without tool activity its reminder arrives at the next boundary. A wall-clock fallback is labeled as such; it is not measured active effort.

## Estimates and parallel work

Estimate the required tasks, then calculate delivery time from dependencies and available workers. Include integration, installation and checks needed for the requested result. External waits remain separate. A changed forecast explains the new facts without rewriting the original estimate.

The plan's leaf limit is normally 15 minutes and a direct user change is recorded in `estimate_policy`. Split large work at meaningful boundaries. A Worker checkpoint is not a task lifetime limit.

`lhc_parallel.py <plan.graph.json>` shows dependency-ready tasks and capacity; `--json` serves callers and `--slot` shows a slot assignment. This is scheduling information. Native availability can still make an assignment unavailable.

`lhc_task_budget.py PLAN.json` checks declared estimates and dependency cycles. Its dependency duration is a lower bound until capacity, resource conflicts and external waits are included.

## Measured time

Record a real start when observed. `lhc_active_time.py` keeps declared work intervals under the existing `.agents/shared-session/time/` store. Pause an interval when yielding or waiting without working, and resume for execution. Concurrent effort can exceed elapsed delivery time. Missing historical intervals stay unknown.

For a native guard repair, use the exact path and actor/task identity in the message: `<card-stem>-<session-sha256-prefix>.active.json`. Resume an existing ledger to preserve its previous total. A ledger measures declared intervals, not CPU use.

## Changes and recovery

When work substantially overruns or repeats a failed route, inspect the result and change the approach where needed. `STOP_RETHINK.md` gives the decision procedure. `BUSINESS_CHECKPOINT.md` documents the optional recorded direction check; `SELF_IMPROVE.md` covers a useful method correction.

Compaction retains one replaced `current-handoff.md` and `state.json` under `.agents/shared-session/compaction/<session-id>/`. The handoff includes the current goal, plan, next step, blockers and evidence. Restore the bound task rather than constructing a new plan from a partial summary.

The current hooks provide pointers and observed state. Confirm the installed runtime's hook and resume behavior before claiming it ran on schedule.
