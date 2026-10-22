---
name: plan-artifacts
description: Create the LHC plan artifacts in one pass — the task record, the machine-readable plan.graph.json and the HTML dashboard — with the exact commands (export, render, check-plan) and the check that proves the report and the graph agree. Use when a task is decomposed, when a plan or the plan status is asked for, when leaves are added, moved or finished, and when the dashboard must be refreshed. Never reverse-engineer the format from the tool source: this skill is the procedure.
---

# Plan artifacts

One procedure, no discovery. Do not read `lhc_grid.py`, do not grep the parser
regexes, do not infer the shape from an old task record: everything needed is here.

`<package root>` below is the directory two levels above this `SKILL.md` (in a
source checkout: `src/common`; in the installed package: the package root). Resolve
it once and reuse the value; never re-derive a path per command.

## 1. Write the report

The report is the plan for a person, in the user's language. It lives under
`## Plan` in the canonical task record, next to the objective. Three header lines,
then the leaves: finished, running, blocked, queued — an empty group is dropped and
the groups are never merged. Canonical wording (the Russian rendering; the field
wording and the emoji do not change with the language):

```text
Цель: <одна строка — чего хочет пользователь>
Бизнес-результат: <одна строка — что пользователь может использовать уже сейчас>
Декомпозиция: <N> листьев · <P> параллельно · <W> волн(а) · слотов: <S>

✅ (описание листа) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
🔄 работаем (описание листа) начата 14:12, оценка 15 минут, прошло 22 минуты, отстаём потому что: <причина>
⛔ (описание листа) начата 14:05, оценка 20 минут, блокер: <внешнее препятствие>
⏳ (описание листа) начнём после листа 3, потому что <почему нельзя параллельно>, примерно в 14:30, оценка 10 минут, закончим в 14:40
```

`✅` finished · `🔄` running · `⛔` blocked · `⏳` queued and not started. A queued
leaf names the leaf it waits for and why it could not start in parallel. A running
leaf that passed its estimate names the cause. When active time was not measured,
write `не измерено` instead of a number. The leaf labels are the labels the graph
and the dashboard show, in the user's language.

## 2. Derive the graph from the report

Do not hand-write the graph. The report already carries the leaves, their statuses,
their order and their estimates, and the tool derives the rest — ids, dependencies,
waves, parallelism:

```sh
python3 "<package root>/tools/lhc_grid.py" export <record> -o <record-dir>/plan.graph.json
```

`<record>` is the task record that holds the report under `## Plan` (a standalone
report file works too). The graph is written next to the record as
`plan.graph.json`. The export gives every leaf an id (`L01`, `L02`, …), its status,
its dependencies and its estimate bounds.

## 3. Add what the report cannot carry

The report is a person's plan; the graph is also the machine's memory. After the
export, set the fields the report has no place for. Per leaf: `owner`, `session`,
`harness`, `model`, `model_class`, `role`, `acceptance`, `read_paths`,
`write_paths`, `note`, `estimate_unknown_reason`, `blocker_details`. On the
document: `title`, `goal`, `business_result`, `current_progress`,
`external_waits`, `slots`.

They are optional: a field you do not know stays absent, and an absent optional
field is a choice, never a demand. `read_paths` and `write_paths` are how one
owner per path is proven, so write them for every leaf that touches a file — and
keep the mutable paths disjoint: two leaves that may run at the same time must
not declare the same `write_paths`. A shared mutable path needs either a
dependency between those leaves or isolated ownership, and the optional offline
checker `scripts/lhc_validate_graph.py <graph.json>` (source checkout only) fails
on exactly that conflict.

## 4. Render and reconcile

```sh
python3 "<package root>/tools/lhc_grid.py" render <record-dir>/plan.graph.json -o <record-dir>/plan.html
python3 "<package root>/tools/lhc_grid.py" check-plan <record> <record-dir>/plan.graph.json
```

`check-plan` prints every divergence between the report and the graph and exits
non-zero when they disagree. That exit code is the gate: the plan is not finished
until it passes. `status` prints the same facts as text when the answer belongs in
a chat message.

## 5. The order at every plan boundary

1. update the report in the record from the current state of the work;
2. refresh the graph — export again, then re-add the attribution fields;
3. `render` the dashboard;
4. `check-plan` — fix every divergence it prints.

Do this at each 30-minute plan boundary, before dispatching work, before reporting
a result, and before handing off after compaction. The report is what a person
reads; the graph is what the schedule, the forecast and the next session read.
They are one set of leaves, and `check-plan` is the proof that they still are.

## 6. The field reference

`common/protocols/TASK_GRAPH.md` is the canonical field list and
`common/protocols/PLAN_REPORT.md` the canonical report format; read them only for
a field this skill does not mention. One leaf in the graph looks like this:

```json
{"id": "L01", "label": "<label>", "status": "queued", "depends_on": [],
 "estimate_minutes": {"minimum": 10, "maximum": 15}}
```

`status` is one of `done`, `running`, `blocked`, `waiting`, `queued` — the state of
the work, not the state of the paperwork. `waiting` is not a blocker: a leaf that
waits for another leaf is `queued`, and `blocked` names the concrete external
obstacle. `depends_on` holds the ids that must finish first and is the only
scheduling input: waves, parallelism and the critical path are derived from it.
`estimate_minutes` keeps the original bounds and is never rewritten to fit reality;
a leaf that estimates only part of the work also carries `estimate_unknown_reason`,
so the forecast shows an unknown deadline instead of a silent zero.

## 7. What the tools cannot do for you

- They do not choose the leaves. Decomposition is yours: one accepted outcome, one
  shortest real canary, hard dependencies only on the real consumer path, one
  owner per leaf.
- They do not write the business result, the acceptance line or the blocker text.
- They do not translate: the labels, the report and the dashboard are written in
  the user's own language by you.
