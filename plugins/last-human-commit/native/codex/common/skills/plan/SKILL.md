---
name: plan
description: Build and keep the plan of any engineering task longer than 15 minutes, and /plan. Load it before the first leaf, when the owner types /plan or asks to fix the plan, and when a leaf runs far past its estimate.
---

# Plan

The plan is what you will do and, as you go, what you have done. After a compaction the next
you reads it to know where you are, so every finished leaf says what works and where.
Work with the plan only through the LhcPlan MCP: `create_leaf`, `update_leaf`, `update_progress`,
`activate_leaf`, `update_plan` (plan fields, revisions), `show_plan` (refresh the bound context),
`worker_register`, `worker_finish`. Every answer ends with the state of the plan; every refusal
says what to do. Without the MCP use the same commands of `lhc_plan_json.py`. Never edit plan
files by hand. After restart or compaction, use the bound plan snapshot supplied by the
hook; if that snapshot is absent or needs refreshing, call `show_plan`. Never choose a
plan merely because it shares the working directory.

Record the requested result in `deliverable`: `plan` for planning only, `implementation`
for execution. Use `decomposition: complete` when the owner wants every stage prepared
for handoff; otherwise `progressive` keeps the existing stage-by-stage workflow.
Structural `check` validates the files; `check --handoff` also checks the declared
handoff requirements. Neither check proves implementation or consumer acceptance.

## 1. Research before you plan: at least 10 minutes

Research is the cheapest part of the work and makes the rest cheaper. Spend at least 10
minutes, more while you still find new objects. Find what exists, what is broken and which
objects the work touches: environments, hosts, services, endpoints, screens. Put them into
`recon` (3+ lines `fact :: evidence`) with `mode: fullcycle` and an `acceptance_scenario`.
Every «needs checking» in `recon` becomes a research leaf with its question.

## 2. Stages, each ending in a release

- At the start you cannot know every step, so write the whole route to the owner's result as
  stages (`kind: milestone`) of at most 45 minutes each, with that estimate. A longer stage is
  two stages.
- Leaves of a stage get `parent: <stage id>`. Cut them when you start the stage and add more
  as the work shows them; the page shows stages and opens each to its leaves.
- Every stage ends by deploying what already works, so the owner gets value stage by stage:
  the last leaf of a stage is a release task leaf (a stage holds leaves, never other stages).
  Example: first the check of Codex and OpenCode on the installed service, then one stage per
  added environment. Never one big release at the end.
- With progressive decomposition, cut only the stage you start now. With complete
  decomposition, prepare executable leaves for every active stage before handoff.
  A plan with one leaf and no stages is not a plan.
- A leaf is created before its work starts, never for work already done.

## 3. One leaf per object

- Each environment, host, service or endpoint gets its own leaf. Wrong: one leaf «ZCode,
  MiniMax и остальные среды». Right: a leaf for ZCode, a leaf for MiniMax, a leaf for Claude.
- An unknown («как установленный процесс достучится до тестового приложения?») is a
  research leaf with that question, not a build leaf.

## 4. Honest estimates

- The default leaf limit is 15 minutes. If the owner explicitly changes that limit,
  record `estimate_policy: {"leaf_cap_minutes": 60, "reason": "the owner's instruction"}`
  through `update_plan`, using the actual limit and instruction. All tools use this
  plan-scoped policy; do not patch the installed code or use a private wrapper.
  Estimate honestly and split work above the effective limit; never reduce a number
  merely to satisfy validation. The reason records a scheduling decision, not authority
  to change access controls, human stops or the task scope.
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
