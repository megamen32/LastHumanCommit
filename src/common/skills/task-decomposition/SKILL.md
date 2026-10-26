---
name: task-decomposition
description: Decompose large or stalled work into independently verifiable subtasks planned around 15 minutes where useful. Use when planning, assigning Workers, routes are entangled, or progress has produced little business delta.
---

# Task Decomposition

Every authorized development task has a Lead-owned plan before implementation,
including one bounded fix or a small behavior change. A small task can use one
concise leaf; it does not require a review ceremony or another user approval.
Research enough to understand intent and affected path, then explicitly choose
quickfix or fullcycle from scope and risk. A user-assigned leaf remains an
execution slice created and managed by the Lead; it cannot choose the parent mode
or waive its plan. Questions, status requests and read-only investigations do not
need a development plan.

The Lead retains authority for plan meaning, mode, acceptance, owners,
dependencies and status decisions. To reduce bookkeeping, the Lead may name one
exclusive `Artifact Writer` to create/update `task.md`, task-level `progress.md`,
graph, HTML and Markdown from the Lead's verified decisions. The writer returns
the exact revision for Lead review before execution/status changes proceed.

Decompose for faster business proof, not for more process artifacts.

## Procedure

1. Write one accepted business outcome and one shortest real canary.
2. Draw only hard dependencies on the actual consumer path.
3. Cut at independent ownership, artifact, decision, or acceptance boundaries.
4. Give each leaf one owner, one output or business proof, one primary check,
   allowed paths, excluded scope, and a minimum/maximum active-time estimate.
5. Estimate each coherent leaf from the work and its proof: minimum, maximum,
   basis in known steps or comparable evidence, and the specific uncertainty
   that separates the bounds. Plan small useful pieces around 15 minutes,
   including verification; this is planning granularity, not a runtime cutoff.
   Smaller natural results need no padding. Split larger work at meaningful proof boundaries
   before execution. Twenty minutes is a reporting checkpoint, not a planning
   quantum or duration target.
6. Parallelize leaves only when they do not require the same unresolved decision
   or conflicting writes. Put the critical canary path first.
7. Remove coordination-only leaves whose output cannot change implementation,
   unblock another leaf, or prove the accepted result.

## Derive the total before quoting it

Show the dependency graph and available execution slots, including any Lead work
that occupies a slot. Identify which ready leaves actually run concurrently.
For every serialized pair, name its dependency, shared mutable resource or
capacity limit. Dispatch ready independent work when capacity exists; a diagram
of parallel lanes followed by sequential execution is not parallel delivery.

Separate three quantities:

- Work effort: sum of the leaf estimates, including each leaf's verification.
- Delivery duration: the planned capacity-respecting critical path or execution
  waves; parallel work contributes the longest lane, not the sum of all lanes.
- External waits: queue, approval, build service or unavailable environment,
  listed separately with their evidence or marked unknown.

Keep the same leaves in a machine-readable task graph next to the task record as
`plan.graph.json` and render it with
`python3 "<tools>/lhc_grid.py" render <objective>/plan.graph.json -o
<objective>/plan.html`, where `<tools>` is the tools directory of the
active package root. The procedure — record, graph, report, render, check — is the
`plan-artifacts` skill; the canonical format is `common/protocols/TASK_GRAPH.md`.
The graph carries the schedule, the parallelism and the forecast; the report
carries the same content for a person. A decomposition without a graph is not
finished.

Use the TIME_CONTROL protocol's `lhc_task_budget.py` to validate leaf bounds and
sum effort. Its dependency-only duration bounds exclude capacity/resources/waits;
Lead must supply the actual feasible schedule before quoting elapsed delivery.

Make the integration join, one final review of the integrated Full-cycle result,
and real-use verification visible where needed; quickfix review stays risk-triggered.
Do not create a review task for every
worker leaf or wave, or hide release work in a doubled global buffer. Workers keep
running local checks during implementation. The final sequence is review → permitted
deploy → real consumer test → push on the configured route. For each bound, show its
formula.
Do not quote a naked 60–120 minute range or mechanically double a minimum.
If a wide range comes from an unresolved fact, name that fact and run the cheapest
discriminating probe before expanding implementation. If a proof cannot yet be
split into roughly 15-minute planning pieces, return that boundary to Lead to refine the
decomposition. Never abort or reject ongoing work solely for passing a planning piece;
compare progress with the estimate and adjust the remaining route. Account for passive
external waits separately without dropping them from the elapsed forecast.

Example (illustrative minutes): contract 2–3; backend 4–7 and frontend 3–5 in
parallel; join 1–2; review 2–3; real use 2–4. With two executor slots available,
effort is 14–24, but delivery is 2–3 + max(4–7, 3–5) + 1–2 + 2–3 + 2–4 = 11–19.
With one available executor slot, the parallel assumption is invalid; show the
serialized schedule and its increased duration. These are estimates, not measured
active or wall-clock time and not a promise of background execution.

## Leaf contract

```text
Outcome:
User outcome and benefit:
Human-readable task title and full description:
Expected visible result and acceptance path:
Affected files (separate from owned read/write paths):
Business/canary delta:
Owner:
Assigned branch/worktree/base commit (if isolated):
Depends on:
Allowed/excluded scope:
Artifact or real proof:
Primary acceptance check:
Minimum / maximum active minutes (roughly 15-minute planning pieces, including verification):
Estimate basis / specific uncertainty:
Execution wave / available slots / reason if serialized:
20-minute checkpoint and question-for-L boundary:
```

Lead initializes/verifies/repairs actual active accounting; each executor records
its own intervals and source/coverage using TIME_CONTROL's `lhc_active_time.py`.
Keep measured time, unknown historical gaps
and estimates distinct; idlecap estimates never become measured active time.

Workers ask L at decision boundaries with evidence, recommendation, proposed
default, safe parallel work, and the exact action that waits. They continue work
valid under every plausible answer through a non-blocking parent transport.

## Compression check

For independent parallel writes, Lead may assign canonical `lhc/<task-slug>`
branches at `<primary-project-root>/.worktrees/<task-slug>` through the shared
LHC worktree tool. Reuse the same assignment across harnesses. Worktree isolation
does not remove dependencies on shared test accounts, services, data or contracts.
Keep small non-conflicting work in the existing checkout when that is cheaper.

For every leaf ask: can it be deleted, merged, reused, or replaced by an existing
mechanism without weakening the accepted MVP? Prefer the resulting YAGNI/Pareto
graph. More leaves are useful only when they increase independent progress or
make failure ownership and business proof clearer.

Preserve the original estimate. If evidence changes the forecast, show original
versus revised remaining work and the changed assumption; never erase an overrun.

Do not create separate research, implementation, review, documentation, and
task-card leaves for one tiny change unless they are genuinely independent and
decision-relevant. Do not confuse started agents, written plans, or completed
checks with business delta.

Use `common/protocols/ORCHESTRATION_RECORDS.md` for durable Lead briefs, worker
progress, decisions, blockers and result receipts. Detailed execution state lives
in the canonical task directory; chat carries only a required decision, a
route-changing blocker, or concise readiness with a receipt path.
