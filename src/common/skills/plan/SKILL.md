---
name: plan
description: Plan larger or parallel work, keep its current state, and answer requests for the session's overall plan.
---

# Plan

Use a saved plan when work needs coordination or recovery, or when the user asks for one. One clear action of about 15 minutes or less can be done directly. The plan records what will work, the path to it, current work and actual results.

## Choose the route

Read the goal, latest corrections and existing implementation. Investigate questions that affect the next decision. Draft a complete route, resolve significant weaknesses and remove optional work. A critique is useful when it changes the plan; it does not need repeated rounds until nobody can object.

Describe stages in the user's language by what will work after each. Create the tasks needed for the stage being started. With `decomposition: complete`, prepare executable tasks for all active stages before handoff; `progressive` leaves later details open. Record `deliverable: plan` for planning-only work and `implementation` for execution.

Use `plan-artifacts` for the current schema and commands. The tools require fullcycle setup fields including `mode`, `recon`, `acceptance_scenario`, `summary` and `critique`. Record the relevant facts and decision once. The summary has a current tool limit of 3000 characters; full task descriptions keep the detail.

## Tasks and estimates

Split at useful result, ownership and dependency boundaries. Different hosts or environments often need separate checks and can run independently. A research task names the uncertainty it will resolve.

The default leaf limit is 15 minutes. Record a direct user change through `update_plan` as `estimate_policy: {"leaf_cap_minutes": 60, "reason": "the actual instruction"}`, using the real limit. Keep the original estimate visible and explain a changed forecast.

The tool may require an overdue large task to be split; preserve completed work and record the remaining pieces. A checkpoint is a reason to inspect progress, not to cancel a healthy Worker.

## Execute and keep state

Use LhcPlan MCP (`create_leaf`, `update_leaf`, `activate_leaf`, `update_progress`, `update_plan`) or the same CLI in `lhc_plan_json.py`. Use actual native identities. Continue the plan bound to the current session and goal.

Ready independent work can run in parallel. Give each writer a clear scope and worktree; `worker_register` records it and `worker_finish` handles registered integration and cleanup. Dependencies name actual required outputs.

Explicit native assignments use `assign_leaf`, `dispatch_leaf`, `reconcile_leaf` and `accept_leaf`. `common/protocols/ORCHESTRATION_RECORDS.md` documents their brief, identity and continuation contracts. Reconcile an uncertain delivery before sending another job.

Close a task when its result is established, with what works and the relevant evidence. Record a changed route as a revision `{reason, summary}`. Keep genuinely blocked and deferred work visible.

## Show the plan

For «покажи общий план», «план целиком» or a status request, call `show_plan` for the explicitly bound plan. Show the whole ordered stage list, states, current work, blockers and public link. A read request does not create or resume work. If no plan is bound, say so rather than borrowing an unrelated plan.

Use `plan-artifacts` to render and publish the saved state. After compaction, use the bound snapshot or refresh it with `show_plan`. For explicit goal acceptance or exhausted ready work, `read_goal_control` and `record_frontier_decision` preserve the current decision; their API is in `ORCHESTRATION_RECORDS.md`.
