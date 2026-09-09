---
name: task-decomposition
description: Split a large or stalled task into the smallest independent, parallel, business-verifiable slices. Use when planning work, assigning Workers, an estimate exceeds 20 active minutes, routes are entangled, or progress has produced little business delta.
---

# Task Decomposition

Decompose for faster business proof, not for more process artifacts.

## Procedure

1. Write one accepted business outcome and one shortest real canary.
2. Draw only hard dependencies on the actual consumer path.
3. Cut at independent ownership, artifact, decision, or acceptance boundaries.
4. Give each leaf one owner, one output or business proof, one primary check,
   allowed paths, excluded scope, and a minimum/maximum active-time estimate.
5. Estimate each coherent leaf from the work and its proof: minimum, maximum,
   basis in known steps or comparable evidence, and the specific uncertainty
   that separates the bounds. Do not size tasks to 20 minutes. Twenty minutes
   is a reporting checkpoint, not a planning quantum or duration target.
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

Make integration, review and real-use verification visible where they are needed;
do not hide them in a doubled global buffer. For each bound, show its formula.
Do not quote a naked 60–120 minute range or mechanically double a minimum.
If a wide range comes from an unresolved fact, name that fact and run the cheapest
discriminating probe before expanding implementation. Keep a long coherent leaf
when its proof cannot sensibly be split; explain it rather than inventing jobs.

Example (illustrative minutes): contract 2–3; backend 4–7 and frontend 3–5 in
parallel; join 1–2; review 2–3; real use 2–4. With two executor slots available,
effort is 14–24, but delivery is 2–3 + max(4–7, 3–5) + 1–2 + 2–3 + 2–4 = 11–19.
With one available executor slot, the parallel assumption is invalid; show the
serialized schedule and its increased duration. These are estimates, not measured
active or wall-clock time and not a promise of background execution.

## Leaf contract

```text
Outcome:
Business/canary delta:
Owner:
Assigned branch/worktree/base commit (if isolated):
Depends on:
Allowed/excluded scope:
Artifact or real proof:
Primary acceptance check:
Minimum / maximum active minutes:
Estimate basis / specific uncertainty:
Execution wave / available slots / reason if serialized:
20-minute checkpoint and question-for-L boundary:
```

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
