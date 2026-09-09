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
bounded continuation justified by evidence or change approach. An Overseer
CONTINUE receipt must name the achieved user result, concrete remaining blocker,
next proof and time bound; approving another phase without the cumulative cost
is not control. Never weaken accepted scope silently to make a budget green.

Every120 wall-clock minutes during unfinished work, run SELF_IMPROVE.md before
further implementation at the next observable boundary, even inside one slice.
The persistent hook checkpoint survives phase
changes and remains due until the improvement result is recorded. Wall time is
a trigger, not a claim about active work; after idle time check on resumption,
without waking an idle agent. Missing hooks require an explicit manual check at
observable work boundaries, never a silent exemption.

Every declared work cycle has its own immutable `minimum / maximum active
minutes` estimate before execution. A cycle is one coherent route to one
business proof: direct Lead work, one Worker lane, one real canary, one review,
one rollout, or another named operation. Tiny atomic commands may share the
estimate of their enclosing cycle; do not create an estimate per shell command.

## Start anchor

Before setting an anchor, construct the estimate from the work. Twenty minutes
is a reporting interval; decompose work into subtasks estimated at about 30
minutes. This is planning granularity, not a maximum actual task duration.
Split large work into independently verifiable results before dispatch;
an estimate materially larger than 30 minutes means the next steps are not yet
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

Validate the leaf JSON plan with `../tools/lhc_task_budget.py PLAN.json` before
dispatch. It flags larger estimates for decomposition without rejecting the task;
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

- ZCode: the SessionStart hook writes
  `.agents/shared-session/time/zcode-<session-id>.json`; cite that file.
- Codex, Hermes, OpenCode: the native lifecycle time-guard hook state.
- No hook available: capture `date --iso-8601=seconds` at cycle start and name
  the source `manual clock`.

Wall-clock comes from this anchor. Active time requires explicit measured work
intervals, never file mtimes, the objective's wall-clock or capped hook gaps.
L owns starting, pausing, resuming and closing interval accounting; each executor
owns its own intervals and reports them without double-counting concurrent work
as delivery time. Use `../tools/lhc_active_time.py` with state under the existing
`.agents/shared-session/time/` directory. Pause when yielding to the user or
waiting without doing work; resume before execution. Record missing lifecycle
coverage or interrupted intervals as gaps, not measured work.
Historical `не контролировал` stays honest, but L must repair missing accounting
before new execution. Overseer enforces that repair and checks the resulting
measurement evidence; a disclaimer alone never closes the finding.

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

## Hourly Lead report

At every crossed wall-clock hour while the task remains active, L reports to the
user, without stopping safe work:

```text
Какие реальные задачи закрыты:
Реальная бизнес-дельта:
Завершённые файлы:
План minimum/maximum активных минут:
Факт active / wall-clock:
Что мешает:
Какие гейты или инструкции задерживают бизнес-результат:
Контроль времени и следующий самый короткий маршрут:
```

If nothing real closed, say `ничего` and explain the blocker. Do not substitute
workers started, tests run, reviews completed, task-card edits, or process
receipts for closed business tasks.

## Estimate overrun

Crossing the original maximum immediately emits the tool's complete Russian
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
