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
range. Twenty minutes is a checkpoint, not a task size. Do not manufacture
20-minute slices or turn a small set of leaves into an unexplained 60–120 total.

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
the capacity-respecting critical path uses the longest concurrent lane plus
required sequential joins/review/testing. Include external waits separately.
Show the arithmetic and each uncertainty rather than doubling a global buffer.
The checker can summarize declared per-node estimates, but its dependency-only
critical path is a lower bound until capacity, resource conflicts and waits are
accounted for. It does not measure active time or run a scheduler.

## Dispatch and close

Supply compact task evidence and relevant skill references, not the full parent
history. Use the adapter's real role/model delivery and event/receipt mechanisms.
Reuse useful research sessions for implementation when supported. Independent
Reviewer/Tester/challenger runs remain fresh; task resumption does not remove them.

At joins, verify the accepted result of each predecessor and test the combined
behavior. A set of independent PASS receipts is not an integration test. New
uncertainty returns to the strong decision layer instead of cascading guesses.

Use Overseer for material drift, repeated failure, overrun or inefficient model
allocation. Re-decompose rather than defending the original graph. Record what
worked well enough to improve the next allocation, without inventing a scheduler
or background continuation the harness does not provide.
