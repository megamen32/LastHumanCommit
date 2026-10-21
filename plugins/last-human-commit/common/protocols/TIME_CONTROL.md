# Business time control

## One objective, one cumulative clock

Before implementation, name the accepted result and stopping condition, retain
one objective start anchor, and estimate the whole remaining delivery path,
including integration, deployment, proof and external waits. Keep measured
wall-clock separate from effort and from unmeasured active time. Leaf estimates
do not replace this total. New phases, task cards, workers and compactions never
reset the objective clock or its original forecast.

At each completed vertical result, compare the accepted outcome with what is
already proven. If complete, deliver it; do not open another feature. Otherwise
name only the remaining required blockers and update their remaining forecast
against the original total. Classify new discoveries as required blocker,
authorized remaining scope, or Proposed; discovery alone does not select work.

At an overrun or two equivalent failed routes, stop adding work. Choose one
bounded continuation justified by evidence or change approach. Make a concise evidence-based route decision with the achieved user result,
concrete remaining blocker, next proof and time bound. The Overseer may advise;
its response is not a permission or continuation receipt. Never weaken accepted scope silently to make a budget green.

Every 30 minutes, write the live plan report (`../protocols/PLAN_REPORT.md`): the
goal, the current business result, and every leaf as finished, running or queued
with its start/finish time, original estimate, actual minutes and the reason it
is behind or blocked. Keep it under `## Plan` in the canonical task note so it
survives compaction, and show it to the user. Every 60 minutes, reread the
original direct user goal and check useful business progress. Native PostToolUse
reminders track only time and deduplicate each due interval; without tool
activity, a reminder arrives at the next work boundary. They never classify text,
mutate task/evidence/holds or block completion.

## Timers and what each one is for

| Timer | Cadence | What it protects | What it must not become |
|---|---|---|---|
| Plan report | 30 min | The plan stays in the model's head and in the record; the Overseer reads it against the original request and the canary | A second task-card format, a file list, or a progress theatre report |
| Goal direction check | 60 min | The original request is still the goal after an hour of work | A mandatory hourly ritual, a tester dispatch, or an empty status message to the user |
| Learning checkpoint | 120 min unfinished work | The method is examined instead of repeated; an allowed-model adviser may identify a useful correction | A seven-field form, binding verdict, or acknowledgement loop |
| Estimate overrun | On event | Crossing the original maximum forces a route decision instead of grinding | A scolding, a forced estimate rewrite, or more governance that costs more than the overrun |
| Worker checkpoint | 20 min | A delegated worker reports delta, blocker and next action so it cannot hang silently | A separate report format, or content that must be re-merged into the 30-minute plan report |
| Independent milestone evidence | When the accepted claim warrants it (often around 3 h of coherent work) | A fresh allowed-model tester may try the real consumer surface without implementation history | A standing reviewer queue or a gate on every edit, commit, or elapsed-time threshold |
| Active-time ledger | Per interval | Real work time is separated from waiting, so overrun means something | Mandatory accounting where the harness does not manage it; `not measured` stays honest |

One clock serves the whole objective. New phases, cards, workers and compactions
never reset it.

Every 120 wall-clock minutes of unfinished work, the Lead follows SELF_IMPROVE.md
at the next observable boundary. This is a Lead responsibility without a native
hook veto. Wall time is a trigger, not active effort; do not wake idle sessions.

Every declared work cycle has its own immutable `minimum / maximum active
minutes` estimate before execution. A cycle is one coherent route to one
business proof: one Worker lane, one real canary, any warranted review,
one rollout, or another named operation. Tiny atomic commands may share the
estimate of their enclosing cycle; do not create an estimate per shell command.

## Start anchor

Before setting an anchor, construct the estimate from the work. Thirty minutes
is the plan-update interval; decompose work into subtasks estimated at about 15
minutes. This is planning granularity, not a maximum actual task duration.
Split large work into independently verifiable results before dispatch;
an estimate materially larger than 15 minutes means the next steps are not yet
understood well enough: clarify and decompose further. First sum all subtask
estimates as the whole work estimate; then choose parallel lanes and blocking
dependencies and derive the separate elapsed forecast. Do not reverse this by
inventing a total first and distributing it across tasks.
External waits are named separately, never disguised as completed work. Every coherent
leaf has a minimum/maximum, a basis in known work or comparable evidence, and a
named uncertainty explaining the range. Do not mechanically double a minimum.

Show the actual dispatch plan, dependencies and available slots. Sum leaf work
as effort; calculate delivery duration from the capacity-respecting critical
path or planned waves, using the maximum of concurrent lanes. Show integration,
review and real-use testing where required, plus external waits separately.
Explain why ready independent work must be serialized. A dependency-only graph
duration is a lower bound, not a complete forecast when capacity is constrained.

Optionally check a structured leaf plan with `../tools/lhc_task_budget.py PLAN.json`. It flags larger estimates for decomposition without rejecting the task;
it rejects malformed estimates and cycles and computes sums and dependency
bounds. Its parallel duration is explicitly a lower bound; show the actual slot
assignment or waves before calling that number a delivery forecast. Include all
required integration and acceptance work. Never replace the computed effort
with an unrelated top-level estimate.

Preserve the original estimate for control. A revised remaining-work forecast
must explain the new evidence and show the old estimate; it cannot reset the
guard or hide an overrun. Estimated effort and delivery duration are not measured
active or wall-clock time.

A cycle does not start before its task record carries
`Started at <UTC+3 ISO> (<source>)` taken from a real clock anchor:

- Record `date --iso-8601=seconds` at the actual task/cycle start and cite it. The
  anchor is a real manual clock reading, never an inferred or reconstructed value.
- A native time-only heartbeat anchors its own first tool boundary, not the task
  start. It cannot establish historical active time or reset the original estimate.
- Preserve existing verified start receipts; do not manufacture old timestamps.

Wall-clock comes from this anchor. Active time requires explicit measured work
intervals, never file mtimes, the objective's wall-clock or capped hook gaps.
L owns starting, pausing, resuming and closing interval accounting; each executor
owns its own intervals and reports them without double-counting concurrent work
as delivery time. Use `../tools/lhc_active_time.py` with state under the existing
`.agents/shared-session/time/` directory. Pause when yielding to the user or
waiting without doing work; resume before execution. Record missing lifecycle
coverage or interrupted intervals as gaps, not measured work.
Historical `not measured` stays honest. When practical, begin measuring forward;
missing historical accounting is a disclosed gap, not a pre-execution block. The
Lead uses the available evidence to make an honest route decision.

For a native guard's discovered work card, use the exact state path and actor/task
identity printed by its repair prompt: `<card-stem>-<session-sha256-prefix>.active.json`.
The guard verifies both identities. Measurements cover only their recorded
intervals, remain separate from the card's historical total, and never erase or
silently add to it. Explicitly resume a stopped ledger to retain its prior total
while excluding the stopped gap. Missing native session identity cannot prove
isolated ownership; use an explicitly owned standalone ledger and disclose that
the native guard cannot bind it. The tool measures declared work intervals,
not CPU usage; pause/resume discipline is owned by the executor, not inferred.

Use `../tools/lhc_time_guard.py` at cycle start and every observable checkpoint.
When the harness exposes lifecycle hooks or scheduler wakeups, connect the same
tool there. Its JSON state belongs under
`.agents/shared-session/time/<cycle-id>.json` or the harness's equivalent durable
task state.

## Mandatory hourly business checkpoint

Follow BUSINESS_CHECKPOINT.md every 60 measured native active minutes: reread the
original user source and latest corrections, compare the usable result, decide the
next route. This hourly direction review is not milestone acceptance: do not launch
Zero Knowledge on every hour. When independent user-path evidence is part of the
accepted claim, assign a fresh goal-driven tester with a relevant persona and record
observed behavior. Generated plans and green technical checks cannot replace the
actual evidence required by the claim.
The default native hook does not require a formatted task-card. It reuses the
persistent session state and the existing monotonic interval tool. Idle/permission
waits are paused; incomplete lifecycle coverage uses an explicit wall fallback,
never invented active-time claims. No background wake is created.

The review is mandatory; an hourly user-facing status message is not. Report only
meaningful results, blockers or decisions. Notification never acknowledges review.

## Estimate overrun

Crossing the original maximum immediately emits the tool's complete English
business-first diagnostic. The original estimate remains visible; changing it
does not clear the event. L must answer with evidence and choose a shorter route,
one concrete canary-reaching continuation, or one necessary user decision.

The diagnostic does not authorize weaker essential safety, secret exposure,
missing human authority, destructive action, or unproven business claims. Its
purpose is to remove process and optional hardening that do not protect the
accepted result.

## Capability boundary

A native hook calls the guard at session/cycle start, material update, response
finalizer, and scheduler wake. Without hooks, L calls it manually on each
observable update. Without hourly wake support, the next call reports every
crossed hour once; report the delayed-delivery limitation rather than pretending
the reminder fired on time.

## Compaction continuity

Native compaction hooks write one atomically replaced
`.agents/shared-session/compaction/<session-id>/current-handoff.md` plus a small
`state.json`. This is not append-only. `state.json` keeps a monotonic compaction
count and only the last three marks so repeated loops remain visible without
creating a new context-growth problem.

The handoff includes the current task contract, accepted result/canary, timing
truth, blockers, next action, and bounded workspace/changed-path evidence. It
must say unknown when active time or historical pre-install compaction count is
not known. Codex restores it through SessionStart after PreCompact/PostCompact;
OpenCode injects it directly through `experimental.session.compacting`.
