---
name: plan
description: Build and keep the plan of any engineering task longer than 15 minutes, and /plan. Load it before the first leaf, when the owner types /plan or asks to fix the plan, and when a leaf runs far past its estimate.
---

# Plan

The plan is what you will do and, as you go, what you have done. After a compaction the next
you reads it to know where you are, so every finished leaf says what works and where.
Work with the plan only through the LhcPlan MCP: `create_leaf`, `update_leaf`, `update_progress`,
`activate_leaf`, `update_plan` (plan fields, revisions), `show_plan` (refresh the bound context),
`worker_register`, `worker_finish`, and the explicit execution operations `assign_leaf`,
`dispatch_leaf`, `reconcile_leaf`, `accept_leaf`, `read_goal_control`,
`record_frontier_decision`. Every answer ends with the state of the plan; every refusal
says what to do. Without the MCP use the same commands of `lhc_plan_json.py`. Never edit plan
files by hand. After restart or compaction, use the bound plan snapshot supplied by the
hook; if that snapshot is absent or needs refreshing, call `show_plan`. Never choose a
plan merely because it shares the working directory.

Record the requested result in `deliverable`: `plan` for planning only, `implementation`
for execution. Use `decomposition: complete` when the owner wants every stage prepared
for handoff; otherwise `progressive` keeps the existing stage-by-stage workflow.
Structural `check` validates the files; `check --handoff` also checks the declared
handoff requirements. Neither check proves implementation or consumer acceptance.

## 1. The order of planning: no step skipped

A plan written without these steps, or with them out of order, is redone.

1. **Research, at least 10 minutes**, more while you still find new objects. It is the cheapest part of the
   work and makes the rest cheaper; use the fast model class for it. Find what exists, what is broken and
   which objects the work touches: environments, hosts, services, endpoints, screens. Look for an old
   mechanism that already does the job (`protocols/CODE.md` §1). Put the facts into `recon` (3+ lines
   `fact :: evidence`) with `mode: fullcycle` and an `acceptance_scenario`. Every «needs checking» in `recon`
   becomes a research leaf with its question. No stage is written before `recon` is.
2. **Draft** the route to the owner's result.
3. **Criticize it** as a stranger would: what is missing, what fails first, what is done twice, what rests on
   a guess. Fix and repeat until a pass finds nothing. Record the pass as a revision `{reason, summary}`, and
   write what the critique found and what the Pareto cut removed into plan field `critique`.
4. **Pareto cut.** Keep the fifth of the work that gives most of the result; everything else leaves the plan
   and goes into the `ROADMAP.md` backlog with a date. A stage that does not move the acceptance scenario is cut.
5. **Stages in plain words** (section 2). Put the list into plan field `summary` (one page, at most 3000
   characters). The tool refuses the first executable leaf of a fullcycle plan while `summary` or `critique`
   is empty. Only now the plan is shown and work starts.
6. **Leaves** are cut per stage, when that stage starts, never for the whole plan in advance.

## 2. Stages first, in words a person reads

- Write the whole route as stages (`kind: milestone`) of at most 45 minutes each, with that estimate. A longer
  stage is two stages. At the start you cannot know every step, so do not pretend to.
- A stage label is one sentence in the owner's language saying what will work after it, with no file names,
  identifiers or jargon: «Бот отвечает на новые посты без задержки», not «refactor scanner dispatch». All
  stages together fit on one A4 page (about 12 stages at most). This list is the summary of the plan: a person
  reads it and knows what is being done; if it reads only to an ИИ, rewrite it.
- Leaves of a stage get `parent: <stage id>`. Cut them when you start the stage and add more as the work
  shows them; the page shows stages and opens each to its leaves. Decomposition and parallel work are decided
  inside the stage you are in, so no work is planned before it is needed.
- Git follows the plan: a leaf closes with a commit, a stage closes with a push of the task branch. Deploy to
  the test environment and the testers run once, in the last stage, after everything is built; then the PR
  and the merge. A stage holds leaves, never other stages.
- With progressive decomposition, cut only the stage you start now. With complete decomposition, prepare
  executable leaves for every active stage before handoff. A plan with one leaf and no stages is not a plan.
- A leaf is created before its work starts, never for work already done.
- A blocked leaf does not stop the plan: mark it, do every other leaf. A leaf left unfinished is `deferred`
  and its `result` starts with «отложено человеком: …» or «отложено ИИ: <reason> · вернуться, когда <condition>».

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
- Independent ready leaves of the same kind start together: one Worker per leaf. Each Worker gets its own worktree (`lhc_worktree.py create`) and its own
  run directory on shared stands; register it with `worker_register` before it starts. Close
  its leaf with `worker_finish`: it merges the branch into the task branch and removes the
  worktree, the branch and the run directory. A Worker that is not merged and removed is not
  finished. Registration proves a worktree exists, not that a remote native turn started.
  For an explicit session assignment, use the execution flow below. L keeps the critical
  path and the joins.

### Explicit execution and automatic continuation

- Record an explicit assignment attempt with `assign_leaf`: executor kind, exact
  lead/executor refs (host, harness, native session), and a distinct parent ref for a
  subagent. A leaf owner label, legacy session field or relayed message is not accepted
  dispatch. Unknown historical provenance stays unknown.
- Before `dispatch_leaf`, write the complete `briefs/<leaf-id>.md` contract from
  `ORCHESTRATION_RECORDS.md`: canonical task directory name, exact identities and
  return route, role/mode, description, explicit source/write/excluded scope,
  acceptance output/destination/checks and next action. Raw `message` is not a brief.
  Internal routing does not require unrelated chat context. The gate saves a private
  immutable snapshot and public hashes with the exact admitted attempt; do not add
  private attempt receipts to Git or copy their payload into public projections.
- Use `dispatch_leaf` with the attempt ID and the scoped task message. Its canonical
  path refreshes native availability, checks the unified dependencies/capacity/runtime
  evaluator, and saves dispatch intent atomically before calling the existing Herder.
  Missing evidence, STOP, quota, an occupied executor or an unmet dependency is a reason
  to work on another available leaf, never permission to bypass admission.
- A confirmed submission is `submitted`. Only fresh observation of the exact correlated
  native turn proves `running`. The command also arms the existing Herder `resume_after`
  for that turn and the Lead. Read the returned wake state; a tool success alone does
  not prove the Lead will resume. No polling loop or second scheduler is needed.
- On the wake, reread the latest user goal and the canonical plan/leaf/attempt named in
  the wake. Read the result, integrate it, and perform the required acceptance. Then
  use `accept_leaf` with the proven result, or `worker_finish` for a registered worker.
  Reread unified readiness and dispatch the next available work immediately; a wave is
  a group of available assignments, not a barrier across unrelated leaves.
- `reconcile_leaf` reads native execution and wait receipts without sending a task.
  Completion becomes `result_ready`, including failed/cancelled outcomes for inspection;
  it does not itself mean accepted or done. For UNKNOWN delivery, verify the actual
  receipt, message or target state. Confirmed delivery is used without duplication;
  confirmed absence permits a corrected authorized attempt with linked history.
  An unresolved outcome holds only that operation, not independent tests or recovery.
  Check uncertain wake registration by its existing Herder wait ID before deciding
  whether any new registration is needed; never create duplicate active timers.
  A rejected or unverified wake remains visible
  with its reason.
- A self assignment sends nothing to itself. The current local singleton cannot create a
  cross-host dependency join through this bridge; it returns the explicit unsupported
  reason. Native quota, holds, approvals and scope intake remain Herder/harness decisions.

Concrete CLI/MCP examples and isolated consumer setup:
`protocols/ORCHESTRATION_RECORDS.md` and `protocols/EXECUTION_CONSUMER.md`.

### Goal acceptance and an exhausted frontier

Explicit `activate_leaf` binds the actual selected Lead session/harness to its
existing native outcome when available. A historical missing outcome stays unknown.
Read `read_goal_control` (CLI `goal-control PLAN`) before choosing the next action;
`goal_control` in the graph is a display snapshot, not acceptance or dispatch
permission. All cards done and native completion still do not accept the goal.
If the current goal remains unaccepted with no executable work, record an explicit
`record_frontier_decision` (CLI `goal-control PLAN --session ID --harness NAME
--decision JSON`): existing permitted work, bounded research/decomposition, an
external dependency with its resume condition, or an already observed human stop.
Include evidence, action, owner and uncertainty. The existing native store and
binding lock remain authoritative; no second plan ID, scheduler or automatic
redispatch is introduced. STOP, quota and UNKNOWN/no-replay controls still apply.

## 6. Done means written down

Close an accepted leaf at once, with a `result` that says what works, where the files,
commit and receipts are, and what remains unproven. For explicit assignments, native
completion first becomes `result_ready`; use `accept_leaf` after checking the result,
or `worker_finish` for the registered integration/cleanup flow. Legacy self-work keeps
its existing saved-status workflow. This record is what the next you reads after a compaction.
A change of route goes into `update_plan` as a revision `{reason, summary}`.

## /plan

When the owner types `/plan` (text after it is the goal or a correction): find the plan bound
to this session, write one line per leaf `L# status -> evidence`, fix what is wrong by the
rules above, and continue the work. No plan: build one by sections 1–5.

## Which skill when

| Step | Load |
|---|---|
| Plan files, commands, the public link | `plan-artifacts` |
| Writing code | `protocols/CODE.md` |
| Choosing a model for a Worker | `model-routing` |
| Fixing a bug | `bugfix-tdd` |
| Real-use check after deploy | `real-use-testing` |
| Release | `release` |
