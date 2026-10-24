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
what you did instead of where the plan stands. When the plan has leaf files, the
report is produced by the render command below — what you show the user is the
projected `plan.md`, not a hand-written copy of it.

## Format

This report is a projection, not a document anyone writes. When the plan has
leaf files, they are its source: the graph is collected from them, and this
report is rendered from the graph. Hand-editing the report is a defect — the
next render erases the edit. Regenerate it with one command:

```sh
python3 <LHC>/common/tools/lhc_grid.py render <objective>/plan.graph.json --out-dir <objective>
```

The command writes `plan.md` (this report) and `plan.html` (the page) from one
and the same graph revision. The projected report names the leaf id on every
line (`- L04 · ⋯ В очереди · …`), and `check-plan` reconciles the report with
the graph by that id, never by the row position. The id is read from either
side of the glyph: `✅ L04 · …` and `  - L04 · ✅ Готово · …` are the same leaf.
A line that carries no id is matched by its position, and the reader says so
instead of pretending that it found an id.

Each task line may be followed by indented detail lines, which the report parser,
JSON export, Markdown view and HTML dashboard preserve as separate fields:

```text
  Описание задачи: Исполнитель меняет форму сохранения, чтобы человек мог сохранить выбранный канал и увидеть его после перезагрузки; затрагиваются экран настроек и сохранённое значение.
  Приёмка: Выбрать канал, сохранить, перезагрузить страницу и убедиться, что выбор восстановился.
  Затрагиваемые файлы: `src/settings.py`, `tests/test_settings.py`
```

These descriptions may be as long as needed. Do not replace the business result
with test, publication or runtime status. A report and graph must keep task
description, acceptance, affected files and technical progress distinct.

Three header lines, then the leaves: finished first, running second, blocked
third, queued last. Drop an empty group. Use the user's local time on a
24-hour clock. Write the report in the user's own language — the field wording
below is the Russian rendering, canonical for a Russian-speaking user. The
order, the fields and the emoji do not change with the language. The leaf
labels written into the report, the task graph and the dashboard use that same
language: the user reads the leaves, not the plan.

```text
Цель: <чего хочет пользователь — столько, сколько нужно>
Бизнес-результат: <что пользователь может использовать уже сейчас — достигнутый факт — столько, сколько нужно>
Декомпозиция: <N> листьев · <P> параллельно · <W> волн(а) · слотов: <S>

✅ (описание листа) начата 14:02 закончена 14:09, оценка 15 минут, факт 7 минут
✅ (описание листа) начата 14:02 закончена 14:11, оценка 15 минут, факт 9 минут, ∥ параллельно с листом 1

🔄 работаем (описание листа) начата 14:12, оценка 15 минут, прошло 22 минут, отстаём потому что: <причина>
🔄 работаем (описание листа) начата 14:12, оценка 15 минут, прошло 8 минут, ∥ параллельно с листом 3

⛔ (описание листа) начата 14:05, оценка 15 минут, блокер: <внешнее препятствие>

⏳ (описание листа) начнём после листа 3, потому что <почему нельзя параллельно>, примерно в 14:30, оценка 10 минут, закончим в 14:40
⏳ (описание листа) исполнитель ещё не назначен, примерно в 14:30, оценка 15 минут, закончим в 14:45

⌛ (описание листа) ждём ответа внешнего источника, оценка 15 минут

⏸ (описание листа) владелец отложил лист, оценка 15 минут
```

The header lines carry three different facts, and no line borrows another
line's wording:

- `Цель` — the outcome the person wants. It may still be open: it is the
  target of the delivery, not a status.
- `Бизнес-результат` — what the person can already use **now**: the achieved
  fact. «пока ничего не изменилось для юзера» is a valid and useful answer;
  the benefit promised for a future delivery is not.
- `current_progress` — what is already proven on the way to the goal, apart
  from the business result. It lives in `plan.json` and in the graph, not in
  the header of this report.

The change log is an optional section of the report. It is what the dashboard shows
as a history, so it names an action, a result and a confirmation, not the leaves
again:

```text
## Журнал изменений

- 13:27 · L03 · выпущен 1.5.31 · результат: дефекты дашборда исправлены · подтверждение: e9838c6
- 13:40 · результат: план пересобран из одной ревизии · подтверждение: check-plan
```

- `✅` finished · `🔄` running · `⛔` blocked · `⌛` waiting for an answer · `⏸` deferred
  by the owner · `⏳` queued and not started.
- The groups stand in that order: finished, running, blocked, queued. An empty
  group is dropped, a non-empty one is never merged into another.
- `⛔` is a leaf that cannot move because of a concrete external obstacle. It
  names that obstacle in `блокер: <текст>` — the fact that blocks it: no
  access, a rejected request, an unanswered question, a missing external
  decision. The blocker text is required. `waiting` or `later` is not a blocker;
  a leaf whose blocker is not named yet is not blocked yet.
- `waiting` is not a blocker. A leaf that waits for another leaf is `⏳`
  queued and names the leaf it waits for; only `⛔` carries `блокер:`.
- `⌛` is a leaf that waits for an answer that may still come; `⏸` is a leaf the
  owner deferred: no answer is expected, it takes no slot and it is not part of
  the remainder of the delivery.
- «Декомпозиция» is the shape of the work: how many leaves it was split into, how many
  of them run at the same time, how many waves that takes, and how many slots exist.
  A quick task says so honestly — «1 лист · параллельно нет · 1 волна · слотов: 1» —
  and a full cycle shows the whole structure. The line is never omitted and never
  padded: if the work was not split, it says it was not split. In a projected
  report the numbers are computed from the graph; a hand-stated line that
  contradicts the graph is a divergence and `check-plan` exits on it.
- `∥ параллельно с листом N` marks a leaf that ran, or runs, at the same time as
  another one. A leaf without the marker is sequential, and a queued leaf states
  honestly why it has not started: it waits for a named leaf, or no executor has
  been dispatched for it yet.
- «оценка» is the leaf's original estimate. It is never rewritten to fit reality.
  A leaf is by definition no larger than 15 minutes (PRODUCT-PHILOSOPHY.md §5), so
  «оценка» never exceeds 15 минут. The separate 20-minute worker checkpoint rule
  bounds how long a worker runs before reporting; it is not a leaf estimate and
  never raises one.
- «факт» and «прошло» are measured active time for that leaf: `lhc_time_guard.py`
  and `lhc_active_time.py` measure it from the journal and the leaf writes it, and
  the renderer projects it into the report. Nobody fills these numbers in by hand.
  When a leaf was genuinely not measured, the value reads `не измерено`.
- «отстаём потому что» is required whenever elapsed exceeds the estimate, and names
  the cause rather than apologising. Omit it while elapsed is inside the estimate.
- Every queued leaf names its real reason for waiting: «начнём после листа N,
  потому что …» when it waits for another leaf, «исполнитель ещё не назначен» when
  the only true reason is that no executor has been dispatched for it yet. An
  invented dependency is a lie; the honest reason is required, the after-leaf
  phrasing only when it is true. If a leaf can start in parallel with a running
  one, it is `🔄`, not `⏳`.
- Start and finish times are when the leaf actually ran, not when it was planned.
- Leaves come from the existing plan. The report never invents leaves to look
  complete and never hides a leaf that was already started.

## The wording is not capped

The goal, the business result and the description of a leaf are written as long
as they need to be. A long, precise result beats a short one, and a limit on the
wording of a person is never the answer to a slow plan. What is limited is the
number of leaves, not the size of the text.

## What a plan is not

The plan is the report, the graph and the page generated from them. It is not a
project archive. A plan does not carry:

- a `receipts/` file per leaf, a `consumer-tests/` matrix per scenario, a
  `research/` or `reviews/` folder, or any other directory of evidence;
- a second copy of the plan in another format, another language or another
  place;
- a narrative of what was tried, what was considered and what was rejected.

Everything a leaf needs in order to be understood and checked lives in the leaf:
its description, its acceptance, the files it touches, its owner and its
relations. The change log says what changed and how it was confirmed, once per
change - not once per leaf.

The plan is written once, before the work, and the work starts. Re-reading a
plan that grew a directory tree is a sign that the plan was used as a place to
put the work instead of as a way to start it.

## Where it lives

Keep the current report under `## Plan` in the canonical task record, so it
survives compaction and the Overseer can read it. That copy is pasted from the
rendered `plan.md`, never rewritten in place: when the record and the rendered
file disagree, re-render and re-paste. The report in chat and the report in the
record are the same content; the record is not a second format.

## The report and the task graph are one unit

Every decomposed objective also keeps a machine-readable task graph next to its
task record as `plan.graph.json`, collected from the leaf files and updated
with this report: `TASK_GRAPH.md`. The report is the same content for a
person; the graph is the same content for the schedule, the forecast and the
next session.

Render both projections with one command:

```sh
python3 <LHC>/common/tools/lhc_grid.py render <objective>/plan.graph.json --out-dir <objective>
```

It writes `plan.md` and `plan.html` from one and the same graph revision.
The dashboard shows what is done, what runs now, what is blocked, the rough
finish time and how much of the work runs in parallel. A decomposition without a
graph is not finished.

The task list in the report and the leaf list in `plan.graph.json` are one set:
the same ids, the same statuses, no task without a leaf and no leaf without a
task. A difference is a defect, not "roughly the same".

When the plan has leaf files, that set has one source: the leaf files. The
report and the graph are two projections of them, and the check below compares
two projections of one source.

Check it with one command:

```sh
python3 <LHC>/common/tools/lhc_grid.py check-plan <objective>/plan.report.md <objective>/plan.graph.json
```

It reconciles the two projections by leaf id — ids, statuses, dependencies, the
estimates and the «Декомпозиция» shape line — never by row position, and exits
`0` when they agree, `1` on a named divergence (a task without a leaf, a leaf
without a task, a different status, a header that contradicts the graph), and
`2` when the report cannot be recognised at all. Reconcile the divergence in the
same boundary; do not carry it to the next one.

## The leaf file is the source of truth

A plan that has a `leaves/` directory keeps every leaf in one JSON file of its
own:

```text
<objective>/leaves/L12.json
```

The file is named after the leaf and carries the same id. The owner of a leaf
changes his own file and nothing else, so two workers never write the same
file, never conflict and never wait for each other. The graph, this report and
the page are projections of those files: nobody writes them by hand.

One leaf file looks like this:

```json
{
  "id": "L12",
  "label": "Собрать сборщик листов",
  "status": "running",
  "description": "Что именно делает лист.",
  "acceptance": "Как проверить, что лист сделан.",
  "affected_files": ["common/tools/lhc_plan_json.py"],
  "owner": "worker-1",
  "session": "mvs_...",
  "harness": "codex",
  "model": "minimax-3.1-flash",
  "depends_on": ["L03"],
  "estimate_minutes": {"minimum": 10, "maximum": 15},
  "started_at": "14:02",
  "finished_at": "",
  "actual_minutes": 7,
  "note": "Что ещё важно знать про этот лист.",
  "updated_at": "2026-10-23T22:04"
}
```

The fields, one by one:

- `id` — the identifier of the leaf. It equals the name of the file: `L12.json`
  is the leaf `L12`.
- `label` — the title of the leaf, in the user's language. Required.
- `status` — one of `queued`, `running`, `blocked`, `waiting`, `deferred`,
  `done`. The words of this report (`готово`, `в работе`, `ожидание`,
  `отложено`, `заблокировано`, `в очереди`) and its markers (`✅`, `🔄`, `⌛`,
  `⏸`, `⛔`, `⏳`) mean the same thing and are accepted as well. A new leaf
  starts as `queued`.
- `description` — what the leaf does. As long as it needs to be.
- `acceptance` — how to check that the leaf is done.
- `affected_files` — the files the leaf touches.
- `owner`, `session`, `harness`, `model` — who does the leaf and with what.
- `depends_on` — the leaves that have to be finished before this one starts.
  `parallel_with` — the leaves it runs at the same time as.
- `estimate_minutes` — the original estimate as `{"minimum": 10, "maximum": 15}`;
  the maximum is normally 15 or less, because a leaf larger than 15 minutes is
  not one leaf (PRODUCT-PHILOSOPHY.md §5). A leaf that is deliberately larger
  says why in `estimate_over_limit_reason`, and only that reason lets it
  through the collector. `{"min": 10, "max": 15}` is accepted as well. The
  estimate is never rewritten to fit reality.
- `actual_minutes` — the measured active time of the leaf, when it was measured.
- `started_at`, `finished_at` — when the leaf actually ran, as `ЧЧ:ММ` on a
  24-hour clock in the user's local time. `planned_start` and `planned_finish`
  are the planned window, also as `ЧЧ:ММ`, and `wait_reason` says why a queued
  leaf cannot start yet.
- `result` — the executor's own answer for the leaf: what the finished worker
  delivered, in his words.
- `tier`, `complexity`, `token_estimate`, `cost_usd`, `cost_source` — the
  economics the leaf declares about itself: the class of the worker (`fast` or
  `frontier`), the size of the work (`S`, `M` or `L`), the token budget, the
  price and where the price came from (`measured` or `provisional`).
- `note` — anything else the leaf has to carry.
- `updated_at` — when the leaf was last changed, as `2026-10-23T22:04`. The
  plan takes the newest of these as its own update time.

A leaf that cannot be read stops the collection and is named: a broken leaf
never becomes a missing leaf. The same is true for an unknown status, a
dependency on a leaf that does not exist, and an id that contradicts the name of
the file.

The plan-level facts — the goal, the business result, the number of slots — are
not a leaf's business. They live in `<objective>/plan.json` next to `leaves/`:

```json
{
  "title": "План поставки",
  "goal": "Чего хочет пользователь, когда поставка закончится.",
  "business_result": "Что пользователь может использовать уже сейчас — достигнутый факт.",
  "current_progress": "Что уже доказано по дороге к цели.",
  "slots": 2,
  "updated_at": "2026-10-23T22:04"
}
```

`business_result` is the achieved fact, `goal` is the outcome that may still be
open, and `current_progress` is what is already proven on the way. The three
never borrow each other's wording.

Collect the leaves into the graph with one command:

```sh
python3 <LHC>/common/tools/lhc_plan_json.py build <objective>
```

The hook does it by itself: after a worker writes his leaf file, the graph of
the plan and the page of the plan are rebuilt without a command and without a
reload. That is what the LHC write hook does where it is registered: `codex`,
`claude-code` and `zcode` install it, while `hermes` and `opencode` do not, so
their pages are rebuilt by the collector command and
receives the written paths: codex, claude-code, zcode and opencode. A harness
that registers no LHC hook at all (hermes) rebuilds nothing by itself — there
the plan is rebuilt by running the command above and the render command. The
collection is deterministic — the same leaves always give the same graph, byte
for byte — so a rebuilt plan is comparable with the one before it.

## What the report is for

The Overseer reads this report against the original request and the accepted
business canary. A report whose leaves are all process — receipts, hashes, extra
reviews, re-planning — with no user-visible delta is exactly the drift it looks
for. Keep the business-result line honest: «пока ничего не изменилось для юзера»
is a valid and useful answer.
