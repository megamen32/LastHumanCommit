---
name: plan
description: Build and keep the plan of any engineering task longer than 15 minutes, and /plan. Load it before the first leaf, when the owner types /plan or asks to fix the plan, and when a leaf runs far past its estimate.
---

# Plan

The plan is what you will do and, as you go, what you have done. After a compaction the next
you reads it to know where you are, so every finished leaf says what works and where.
Work with the plan only through the LhcPlan MCP: `create_leaf`, `update_leaf`, `update_progress`,
`activate_leaf`, `update_plan` (plan fields, revisions), `show_plan` (first after a compaction),
`worker_register`, `worker_finish`. Every answer ends with the state of the plan; every refusal
says what to do. Without the MCP use the same commands of `lhc_plan_json.py`. Never edit plan
files by hand.

## 1. Research before you plan: at least 10 minutes

Research is the cheapest part of the work and makes the rest cheaper. Spend at least 10
minutes, more while you still find new objects. Find what exists, what is broken and which
objects the work touches: environments, hosts, services, endpoints, screens. Put them into
`recon` (3+ lines `fact :: evidence`) with `mode: fullcycle` and an `acceptance_scenario`.
Every «needs checking» in `recon` becomes a research leaf with its question.

## 2. Stages, each ending in a release

- Write the whole route to the owner's result as stages (`kind: milestone`, a rough estimate
  in hours is fine).
- Every stage ends by deploying what already works, so the owner gets value stage by stage:
  the last leaf of a stage is a release task leaf (a stage holds leaves, never other stages).
  Example: first the check of Codex and OpenCode on the installed service, then one stage per
  added environment. Never one big release at the end.
- Cut into leaves only the stage you start now. A plan with one leaf and no stages is not a plan.
- A leaf is created before its work starts, never for work already done.

## 3. One leaf per object

- Each environment, host, service or endpoint gets its own leaf. Wrong: one leaf «ZCode,
  MiniMax и остальные среды». Right: a leaf for ZCode, a leaf for MiniMax, a leaf for Claude.
- An unknown («как установленный процесс достучится до тестового приложения?») is a
  research leaf with that question, not a build leaf.

## 4. Honest estimates

- A leaf is at most 15 minutes; the tool refuses more. Estimate from what research showed; a
  piece that needs 45 minutes is three leaves (for example: server, its stream format, its
  test), not one leaf with 45 and not one leaf with a false 15.
- A leaf past twice its estimate and at least 45 minutes is split: close the proven part as
  `done`, put the rest into new leaves, continue. Until then the tool refuses progress notes
  on it.

## 5. Parallel

- `depends_on` only when a leaf reads another leaf's output. Leaves for different
  environments or hosts do not depend on each other.
- Independent ready leaves of the same kind start together: one Worker per leaf, also when
  subagents are off. Each Worker gets its own worktree (`lhc_worktree.py create`) and its own
  run directory on shared stands; register it with `worker_register` before it starts. Close
  its leaf with `worker_finish`: it merges the branch into the task branch and removes the
  worktree, the branch and the run directory. A Worker that is not merged and removed is not
  finished. L keeps the critical path and the joins.

## 6. Done means written down

Close a finished leaf at once: `status: done` and a `result` that says what works; where:
files, commit, receipt; not proven: … This line is what the next you reads after a compaction.
A change of route goes into `update_plan` as a revision `{reason, summary}`.

## /plan

When the owner types `/plan` (text after it is the goal or a correction): find the plan bound
to this session, write one line per leaf `L# status -> evidence`, fix what is wrong by the
rules above, and continue the work. No plan: build one by sections 1–5.

## Which skill when

| Step | Load |
|---|---|
| Plan files, commands, the public link | `plan-artifacts` |
| Choosing a model for a Worker | `model-routing` |
| Fixing a bug | `bugfix-tdd` |
| Real-use check after deploy | `real-use-testing` |
| Release | `release` |
