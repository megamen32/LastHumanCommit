---
name: plan
description: Optional short plan for genuinely multi-lane or explicitly requested work. Ordinary engineering uses the outcome-first path without a plan.
---

# Plan

Planning is a tool, not a gate.

Use a plan when the owner asks for one, when the work has several independent lanes, or when
an irreversible release needs coordination. Do not create a plan merely because a change may
take more than fifteen minutes.

For ordinary work, go directly to the smallest vertical slice and verify the real consumer.

When a plan is useful, keep it to at most three stages:

1. implement the smallest working path;
2. verify it with focused tests and a real canary;
3. deliver it to the authorized target.

Write the goal, the observable acceptance scenario, the current blocker if any, and the next
action. Recon facts, leaf files, worker registration, model routing, critique rounds, ACKs,
frontier decisions, evidence manifests and hourly checkpoints are optional telemetry. They
must never block a local edit, test, canary or truthful report.

A plan may contain parallel tasks when parallelism materially reduces elapsed time. A single
owner may also complete a bounded task directly. Delete or merge unnecessary tasks instead
of preserving them for ceremony.

A real unknown external mutation remains unresolved until its target or result is checked.
That effect-level rule does not suspend unrelated work.
