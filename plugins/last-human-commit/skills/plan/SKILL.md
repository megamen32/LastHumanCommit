---
name: plan
description: The owner typed /plan or asked to update or check the plan. Relate the current state of the work to the plan and check that the plan is still true; if there is no plan, create it and check its decomposition.
---

# /plan

One entry for plan work. It puts the steps in order and points to the skill that owns
each part; it copies none of them. Text after `/plan` is the goal or a correction,
read as it is: nothing in it is classified. A task of 15 minutes or less is one leaf
with no independent check.

## 1. Find the plan

The newest `.agents/tasks/<plan>/plan.json` of this checkout with a leaf not `done`,
or the one the text names. Several open: take the one the current work belongs to and
say which in one line. A plan whose leaves are all `done` while the work goes on: add
leaves to it when the goal is the same, otherwise create a new plan (section 3).
No plan: section 3.

## 2. A plan exists: reconcile it with the work

1. Read `plan.json` and `leaves/L*.json`; the format belongs to `$plan-artifacts`.
2. Write one line per leaf: `L# status -> evidence` (commit, file, run output). A leaf
   without evidence is not `done`. Apply the facts the hooks also report:
   - a leaf is `done` only when everything it depends on is `done`;
   - a leaf running past its estimate is re-planned: keep it `done` for the part that is
     proven (name the proof), or `deferred` with "replaced by L07-L10" when nothing is,
     and put the rest into new leaves of about 15 minutes (`$task-decomposition`,
     `TIME_CONTROL.md`);
   - a dependency may be dropped only when the leaf does not read the other's output;
     the dropped edge and what was checked go into `revisions`, and it never rescues a
     leaf already marked `done`;
   - work that matches no leaf gets a leaf.
3. Freshness, in one sentence: what was learned since the plan was written, or
   "nothing". If the text or that sentence changes the goal, re-plan the affected part
   (`$planning`); otherwise leave the plan alone.
4. Edges but no `decomposition_check`: run the check of section 3, step 3.
5. If the goal, the edges or the leaves changed, append `{at, reason, summary}` to
   `revisions` in `plan.json` (a status change alone is not a revision). Write the leaf
   files first, then rebuild graph and page (`$plan-artifacts`).

## 3. No plan: create it

1. Goal and the shortest route to the next real canary: `$planning`. The text is the
   goal; without text, the owner's latest request.
2. Leaves of about 15 minutes with real dependencies: `$task-decomposition` and
   `TASK_GRAPH.md`. Write the files per `$plan-artifacts`.
3. Check the decomposition once (`TASK_GRAPH.md`, Check the decomposition) with a
   separate subagent that is given only `plan.json` and the leaves, never yourself. Fix
   what it flags, once, and record it as `decomposition_check` with its id in `who`.
   Check again only after a re-plan changes edges.
4. Lanes, models, parallel dispatch: `$decompose-and-dispatch`.

## 4. Report, then go on

The leaf lines of step 2.2, then four lines: running, next ready leaves, what changed
(the `revisions` entry if any), and the public link once, on its own line. Then
continue per `$decompose-and-dispatch`. With no ready leaf, name the blocker and who
can remove it; do not invent work. `/plan` is a checkpoint, not a stop.
