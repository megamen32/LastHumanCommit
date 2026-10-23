---
name: plan-artifacts
description: Create LHC project-plan artifacts in one pass — the user-readable task record, machine-readable plan.graph.json and HTML dashboard — with the exact commands (export, render, check-plan) and their consistency check. Use when the user asks to составить план, сделать план проекта, спланировать работу, or asks for a project/work plan; also use when tasks are decomposed, leaves change, or the dashboard needs refreshing. If the user explicitly asks only for a rough chat sketch, do not create files. Never reverse-engineer the format from the tool source: this skill is the procedure.
---

# Plan artifacts

## Requests for a project or work plan

Treat natural Russian requests including «составь план», «сделай план проекта»,
«помоги спланировать работу», «план проекта» and «план работ» as a request for a
project/work plan. Unless the user explicitly asks for a prose-only chat sketch,
create the user-readable task record and its `plan.graph.json` and `plan.html`;
rendering also produces `plan.md`. Do not route a request merely to write or update
one short file into this full project-plan flow when no project/work plan was
requested. This boundary does not waive the normal planning required for
engineering work under the selected LHC mode.

For every authorized development objective, including quickfix and a
user-assigned leaf, the Lead researches intent and chooses the overall mode from
scope and risk, then creates/presents the plan before implementation. A small
task may use one short leaf. Do not wait for a separate plan approval when
execution is already authorized. The Lead owns all plan decisions and statuses;
it may assign one named Artifact Writer as the exclusive file writer for
`task.md`, task-level `progress.md`, graph, HTML and Markdown. The writer records
only verified Lead decisions and returns the artifacts for Lead review. Execution
workers write only their assigned progress/result files in
`common/protocols/ORCHESTRATION_RECORDS.md`. Read-only/status work is outside this
development-plan rule.

One procedure, no discovery. Do not read `lhc_grid.py`, do not grep the parser
regexes, do not infer the shape from an old task record: everything needed is here.

`<tools>` below is the tools directory of the active package root: `common/tools/`
in the installed package, `src/common/tools/` in a source checkout and in the
repository-root projection of this tree. Resolve it once and reuse the value; never
re-derive a path per command.

## 1. Write the report

The report is the plan for a person, in the user's language. It lives under
`## Plan` in the canonical task record, next to the objective. Three header lines,
then the leaves: finished, running, blocked, queued — an empty group is dropped and
the groups are never merged. Canonical wording (the Russian rendering; the field
wording and the emoji do not change with the language):

```text
Цель: <какой человек выполняет какую задачу, на какой обычной поверхности и с какими главными границами>
Бизнес-результат: <какую наблюдаемую пользу получит человек после реализации>
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

The report may follow a task line with indented `Описание задачи:`, `Приёмка:`
and `Затрагиваемые файлы:` details. Explain the problem, change, human benefit,
input, visible outcome and verification path as fully as needed. There is no
small character cap for task descriptions. Put implementation identifiers in
technical details rather than replacing the human explanation with them.

## 2. Derive the graph from the report

Do not hand-write the graph. The report already carries the leaves, their statuses,
their order and their estimates, and the tool derives the rest — ids, dependencies,
waves, parallelism:

```sh
python3 "<tools>/lhc_grid.py" export <record> -o <record-dir>/plan.graph.json
```

`<record>` is the task record that holds the report under `## Plan` (a standalone
report file works too). The graph is written next to the record as
`plan.graph.json`. The export gives every leaf an id (`L01`, `L02`, …), its status,
its dependencies and its estimate bounds.

## 3. Set the attribution once

The report knows the work; the graph also carries who owns it. Four leaf fields and
two document fields have no place in a report, so set them once, on the first
export, and let `--merge` carry them through every later refresh:

- per leaf: `role`, `read_paths`, `write_paths`, `paths`, `affected_files`;
- on the document: `current_progress`, `external_waits`.

`read_paths`, `write_paths` and `paths` are how one owner per path is proven, so
write them for every leaf that touches a file — and keep the mutable paths
disjoint: two leaves that may run at the same time must not declare the same
mutable path. A shared mutable path needs either a dependency between those leaves
or isolated ownership, and the optional offline checker
`scripts/lhc_validate_graph.py <graph.json>` (source checkout only) fails on
exactly that conflict. `current_progress` is what is already proven apart from the
planned result, and `external_waits` are the pending human or platform waits.

## 4. Render and reconcile

```sh
python3 "<tools>/lhc_grid.py" render <record-dir>/plan.graph.json --out-dir <record-dir>
python3 "<tools>/lhc_grid.py" check-plan <record> <record-dir>/plan.graph.json
```

`--out-dir` writes `plan.html` and `plan.md` from one graph, and both carry the same
revision of the plan. Two artifacts of one plan are generated, never kept in sync by
hand: if the two revisions differ, they are two plans.

`check-plan` prints every divergence between the report and the graph and exits
non-zero when task IDs, statuses, or explicitly stated description, acceptance
and affected-file details disagree. That exit code is the gate: the plan is not
finished until it passes. It does not reject descriptions by length. `status`
prints the same facts as text when the answer belongs in a chat message.

## 5. The order at every plan boundary

1. update the report in the record from the current state of the work;
2. refresh the graph — export again with `--merge <the same graph>`, and the
   attribution survives;
3. `render --out-dir` — the dashboard and the text summary of one revision;
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

`status` is one of `done`, `running`, `blocked`, `waiting`, `deferred`, `queued` — the
state of the work, not the state of the paperwork. `waiting` is not a blocker: a leaf that
waits for another leaf is `queued`, and `blocked` names the concrete external
obstacle. `deferred` is a leaf the owner deferred: no answer is expected, it takes
no slot and it is outside the remainder of the delivery. `depends_on` holds the ids that must finish first and is the only
scheduling input: waves, parallelism and the critical path are derived from it.
`estimate_minutes` keeps the original bounds and is never rewritten to fit reality;
a leaf that estimates only part of the work also carries `estimate_unknown_reason`,
so the forecast shows an unknown deadline instead of a silent zero.

Two numbers about time, and they are not the same number. `actual_minutes` is the
summed effort of the executors; `started_at` and `finished_at` are the window on
the clock. 22 minutes of effort inside an 11 minute window means two executors
worked in parallel — the dashboard shows both, as «усилие» and «по часам», and
never one number quietly meaning the other.

The forecast counts from the last confirmed event, not from the moment the page is
opened: an idle plan must not push its own finish away with every minute of
silence. The dashboard shows the anchor and the idle time, and reports a horizon
that has already passed as passed.

A graph may carry its own `journal` — a change log with time, action, result and
confirmation. The report may carry the same thing as a `## Журнал изменений`
section, and the export reads it into the graph. The dashboard renders it as a
change log. Without it the panel falls back to the statuses of the leaves, which
is a second list of the table, not a history.

## 7. What the dashboard is

The dashboard is a snapshot of the plan, not a control panel. It shows what the
plan says; the actual state of the work comes from the API of the owners. A
button in it does not change the fleet — it only draws the plan.

## 8. What the tools cannot do for you

- They do not choose the leaves. Decomposition is yours: one accepted outcome, one
  shortest real canary, hard dependencies only on the real consumer path, one
  owner per leaf.
- They do not write the business result, the acceptance line or the blocker text.
- They do not translate: the labels, the report and the dashboard are written in
  the user's own language by you.
