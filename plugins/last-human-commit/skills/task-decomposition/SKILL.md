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
5. Aim for 5–20 active minutes per leaf. A coherent vertical leaf may be longer
   when splitting it would create handoff tax or divide one proof; checkpoint it
   every 20 active minutes instead of killing or replacing its owner.
6. Parallelize leaves only when they do not require the same unresolved decision
   or conflicting writes. Put the critical canary path first.
7. Remove coordination-only leaves whose output cannot change implementation,
   unblock another leaf, or prove the accepted result.

## Leaf contract

```text
Outcome:
Business/canary delta:
Owner:
Depends on:
Allowed/excluded scope:
Artifact or real proof:
Primary acceptance check:
Minimum / maximum active minutes:
20-minute checkpoint and question-for-L boundary:
```

Workers ask L at decision boundaries with evidence, recommendation, proposed
default, safe parallel work, and the exact action that waits. They continue work
valid under every plausible answer through a non-blocking parent transport.

## Compression check

For every leaf ask: can it be deleted, merged, reused, or replaced by an existing
mechanism without weakening the accepted MVP? Prefer the resulting YAGNI/Pareto
graph. More leaves are useful only when they increase independent progress or
make failure ownership and business proof clearer.

Do not create separate research, implementation, review, documentation, and
task-card leaves for one tiny change unless they are genuinely independent and
decision-relevant. Do not confuse started agents, written plans, or completed
checks with business delta.
