# The live plan report

One live plan per objective. It is the session's working memory: what is finished,
what runs now, what waits and why. The same canonical format is used whenever the
user asks for it and at every 30-minute plan boundary, so the plan never depends on
who asked or on how the session was started.

## When to produce it

- The user writes "декомпозиция задач", "какой план", "план", "статус плана", or
  asks in English for the current task list, decomposition, plan or progress.
- A 30-minute plan boundary arrives (the `plan:` bucket of the native heartbeat).
- Before dispatching work, reporting a result, or handing off after compaction.

Produce the report itself. Do not describe the format, ask which format to use, or
replace it with prose, a list of changed files, a task-card dump, or a story about
what you did instead of where the plan stands.

## Format

Three header lines, then the leaves: finished first, running second, blocked
third, queued last. Drop an empty group. Use the user's local time on a
24-hour clock. Write the report in the user's own language — the field wording
below is the Russian rendering, canonical for a Russian-speaking user. The
order, the fields and the emoji do not change with the language. The leaf
labels written into the report, the task graph and the dashboard use that same
language: the user reads the leaves, not the plan.

```text
Цель: <одна строка — чего хочет пользователь>
Бизнес-результат: <одна строка — что пользователь может использовать уже сейчас>
Декомпозиция: <N> листьев · <P> параллельно · <W> волн(а) · слотов: <S>

✅ (описание листа) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
✅ (описание листа) начата 14:02 закончена 14:11, оценка 15 минут, факт 9 минут, ∥ параллельно с листом 1

🔄 работаем (описание листа) начата 14:12, оценка 15 минут, прошло 22 минут, отстаём потому что: <причина>
🔄 работаем (описание листа) начата 14:12, оценка 20 минут, прошло 8 минут, ∥ параллельно с листом 3

⛔ (описание листа) начата 14:05, оценка 20 минут, блокер: <внешнее препятствие>

⏳ (описание листа) начнём после листа 3, потому что <почему нельзя параллельно>, примерно в 14:30, оценка 10 минут, закончим в 14:40
```

The change log is an optional section of the report. It is what the dashboard shows
as a history, so it names an action, a result and a confirmation, not the leaves
again:

```text
## Журнал изменений

- 13:27 · L03 · выпущен 1.5.31 · результат: дефекты дашборда исправлены · подтверждение: e9838c6
- 13:40 · результат: план пересобран из одной ревизии · подтверждение: check-plan
```

- `✅` finished · `🔄` running · `⛔` blocked · `⏳` queued and not started.
- The groups stand in that order: finished, running, blocked, queued. An empty
  group is dropped, a non-empty one is never merged into another.
- `⛔` is a leaf that cannot move because of a concrete external obstacle. It
  names that obstacle in `блокер: <текст>` — the fact that blocks it: no
  access, a rejected request, an unanswered question, a missing external
  decision. The blocker text is required. `waiting` or `later` is not a blocker;
  a leaf whose blocker is not named yet is not blocked yet.
- `waiting` is not a blocker. A leaf that waits for another leaf is `⏳`
  queued and names the leaf it waits for; only `⛔` carries `блокер:`.
- «Декомпозиция» is the shape of the work: how many leaves it was split into, how many
  of them run at the same time, how many waves that takes, and how many slots exist.
  A quick task says so honestly — «1 лист · параллельно нет · 1 волна · слотов: 1» —
  and a full cycle shows the whole structure. The line is never omitted and never
  padded: if the work was not split, it says it was not split.
- `∥ параллельно с листом N` marks a leaf that ran, or runs, at the same time as
  another one. A leaf without the marker is sequential, and a queued leaf must name
  the leaf it waits for and why it could not start in parallel.
- «оценка» is the leaf's original estimate. It is never rewritten to fit reality.
- «факт» and «прошло» are measured active time for that leaf. When it was not
  measured, write `не измерено` instead of a number.
- «отстаём потому что» is required whenever elapsed exceeds the estimate, and names
  the cause rather than apologising. Omit it while elapsed is inside the estimate.
- «начнём после листа N, потому что …» is required for every queued leaf. If a leaf
  can start in parallel with a running one, it is `🔄`, not `⏳`.
- Start and finish times are when the leaf actually ran, not when it was planned.
- Leaves come from the existing plan. The report never invents leaves to look
  complete and never hides a leaf that was already started.

## Where it lives

Keep the current report under `## Plan` in the canonical task record, so it
survives compaction and the Overseer can read it. The report in chat and the report
in the record are the same content; the record is not a second format.

## The report and the task graph are one unit

Every decomposed objective also keeps a machine-readable task graph next to its
task record as `plan.graph.json`, written and updated with this report:
`TASK_GRAPH.md`. The report is the same content for a person; the graph is the same
content for the schedule, the forecast and the next session.

Render it with one command:

```sh
python3 <LHC>/common/tools/lhc_grid.py render <objective>/plan.graph.json -o <objective>/plan.html
```

The dashboard shows what is done, what runs now, what is blocked, the rough
finish time and how much of the work runs in parallel. A decomposition without a
graph is not finished.

The task list in the report and the leaf list in `plan.graph.json` are one set:
the same ids, the same statuses, no task without a leaf and no leaf without a
task. A difference is a defect, not "roughly the same".

Check it with one command:

```sh
python3 <LHC>/common/tools/lhc_grid.py check-plan <objective>/plan.report.md <objective>/plan.graph.json
```

It prints every divergence — a task without a leaf, a leaf without a task, a
different status — and exits non-zero when the two disagree. Reconcile the
divergence in the same boundary; do not carry it to the next one.

## What the report is for

The Overseer reads this report against the original request and the accepted
business canary. A report whose leaves are all process — receipts, hashes, extra
reviews, re-planning — with no user-visible delta is exactly the drift it looks
for. Keep the business-result line honest: «пока ничего не изменилось для юзера»
is a valid and useful answer.
