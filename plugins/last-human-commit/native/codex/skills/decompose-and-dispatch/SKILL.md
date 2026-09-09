---
name: decompose-and-dispatch
description: Let the strongest suitable Lead turn a goal into coherent model-assigned tasks, dependency-aware parallel lanes and verified integration joins.
---

# Decompose, allocate, execute, learn

Use before substantial dispatch and whenever execution reveals a bad boundary.
For a trivial task, keep the graph implicit and compact; do not manufacture jobs.

## Resolve uncertainty before distributing it

Specify the complete user outcome and its observable acceptance. Identify facts,
unknowns, shared contracts and existing work. Lead/Adviser decides difficult
architecture; use council where independent strong-model reasoning is valuable.
Research can itself be parallelized when its questions are independent.

Create coherent nodes, not line-count or token-sized fragments. Each node has a
clear goal, known inputs, dependencies, owned mutable paths/resources, acceptance
check and next checkpoint. A cheap executor should not have to reconstruct the
whole architecture or choose an unmade product decision. Use
`../model-routing/SKILL.md` for each meaningful allocation.

Estimate each node from its actual work and verification: minimum/maximum minutes,
known steps or comparable evidence, and the specific uncertainty widening the
range. Decompose into subtasks estimated at about 30 minutes, including verification;
this is planning granularity, never an actual execution cutoff or rejection rule.
Split larger work at meaningful proof boundaries before dispatch, including
direct Lead, review and testing work. Twenty minutes remains a checkpoint, not
a duration target. Do not manufacture arbitrary time boxes or an overall range.

## Parallelism with joins

A lane is ready only when its required input contracts/results exist. Independent
work can run concurrently. Shared writes, a mutable input produced by another
lane, shared test-account state and resource limits can make otherwise separate
files dependent. Freeze interfaces, isolate mutable fixtures, designate one owner,
or sequence the conflicting work. Do not parallelize dependent steps for appearance.

When a graph is useful, run the optional offline checker from the LastHumanCommit
repository: `python3 scripts/lhc_validate_graph.py <graph.json>`. See
`references/execution-graph.json`. The checker is repository tooling; installed
skills do not assume that a source checkout exists beside the common bundle.
It checks only declared path/dependency conflicts, not runtime semantics, resource
locks, real model capability or whether tasks are conceptually independent.

Use available concurrency rather than launching all ready jobs without regard to
quota, context, tool capacity or real costs. Preserve existing workspace conventions;
creating extra worktrees is not a mandatory part of this method.
For independent parallel writes, Lead may allocate canonical branches and
worktrees through the active SHARED_WORKTREE protocol and its common tool.
Record primary root, `lhc/<task-slug>`, `.worktrees/<task-slug>`, immutable base
commit and owner. Give the harness that existing path; never let it create a
second private checkout. Main integration and task-owned cleanup remain Lead-owned.

Show which ready lanes will actually dispatch together and the available slots.
Explain each serialization by a dependency, shared mutable resource or capacity
limit. Quote total effort separately from delivery duration: effort sums nodes;
delivery bounds come from a feasible schedule respecting dependencies, capacity
(including Lead work) and shared resources. Each concurrent wave contributes its
longest lane plus required sequential joins/review/testing. Include external waits
separately; do not mistake a dependency-only longest path for scheduled elapsed.
Show the arithmetic and each uncertainty rather than doubling a global buffer.
The checker can summarize declared per-node estimates, but its dependency-only
critical path is a lower bound until capacity, resource conflicts and waits are
accounted for. It does not measure active time or run a scheduler. Use
`../../tools/lhc_task_budget.py` per TIME_CONTROL to flag decomposition candidates
and calculate effort sums; its dependency-only bounds also exclude capacity
and waits, so Lead still owns the feasible elapsed schedule.

## Dispatch and close

Lead initializes, verifies and repairs actual active accounting through the
existing TIME_CONTROL mechanism (`../../tools/lhc_active_time.py`); each role
records/reports its own intervals
and source/coverage. Unknown historical gaps stay unknown. Idlecap estimates
are estimates, never measured active time; summed parallel effort is not elapsed.

Choose the least capable reliable model per bounded node, preferring fast cheap
executors. Default to zero-knowledge dispatch: fresh context with a self-contained
contract and only the required inputs, not the parent conversation or unrelated
history. Lead keeps the global context and controls dependencies, concurrency and
acceptance. Use the adapter's real role/model delivery and event/receipt mechanisms.
Reuse research context within the same bounded task when it avoids rework. Independent
Reviewer/Tester/challenger runs remain fresh; task resumption does not remove them.

At joins, verify the accepted result of each predecessor and test the combined
behavior. A set of independent PASS receipts is not an integration test. New
uncertainty returns to the strong decision layer instead of cascading guesses.

Use Overseer for material drift, repeated failure, overrun or inefficient model
allocation. Overseer demands a BUSINESS RESULT; re-decompose rather than defending
the original graph. Learn after substantial overrun (SELF_IMPROVE.md threshold),
repeated errors and cycle
end, retaining the maximum 120-wall-clock-minute interval during unfinished work. Verified
learning or its paperwork never authorizes continuation without a justified route
to the accepted result. Do not invent a scheduler or background continuation.
