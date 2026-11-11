# Plan reports

Show the plan bound to the current session and goal when the user asks for the overall plan or its status. Present all stages, their current states, the work in progress and real blockers, with the public link. A request to read a plan does not create or resume work.

## Source and rendering

`plan.json` holds plan-level facts; `leaves/<ID>.json` holds each task. The graph, Markdown and HTML are generated views. Update the source through LhcPlan or its CLI, then render the current revision:

```sh
python3 <LHC>/common/tools/lhc_plan_json.py build <plan-dir>
python3 <LHC>/common/tools/lhc_grid.py render <plan-dir>/plan.graph.json --out-dir <plan-dir>
```

The second command writes `plan.md` and `plan.html`. `status` prints the graph's current facts for chat. Registered write hooks or the source observer may do this automatically; use the command when the view needs refreshing.

`check-plan` compares a report with its graph when a discrepancy is suspected or a consumer needs reconciliation:

```sh
python3 <LHC>/common/tools/lhc_grid.py check-plan <plan.report.md> <plan.graph.json>
```

It matches explicit leaf IDs and reports conflicts. Legacy rows without IDs use the supported fallback and disclose it. Exit 0 means matching projections, 1 a divergence, 2 an unrecognized report. Correct the source or regenerate the stale view.

## Meaning of the fields

| Field | What it says |
| --- | --- |
| `goal` / «Цель» | Why the user wants the change |
| `business_result` or `business_results` / «Что будет работать» | The capability the change will provide |
| `acceptance_scenarios` / «Как проверим» | Who acts, what they do and what result should be visible |
| `current_progress` / «Что уже сделано» | What was actually implemented or checked, with the limits of that evidence |

Keep legacy storage names and accept the heading «Бизнес-результат». An expected capability can be pending. Claim completion from the relevant result, not from the presence of a declaration. For a CLI or library, describe the actual caller and observed output; commercial wording is unnecessary. Historical reports retain what was known at their time.

Write labels and descriptions in the user's language. Use enough detail to explain the work and its acceptance. File paths belong in technical details rather than replacing the explanation.

## Example

```text
Цель: Пользователь следит за работой по одной ссылке.
Что будет работать: После сохранения задачи новая заметка появится по прежней ссылке, в том числе после восстановления сервера.
Декомпозиция: 3 листа · 2 параллельно · 2 волны · слотов: 2

✅ L01 · Сохранять заметку · начата 14:02 закончена 14:09, оценка 10 минут, факт 7 минут
🔄 L02 · Показывать свежую заметку · начата 14:10, оценка 15 минут, прошло 8 минут
⏳ L03 · Проверить восстановление · начнём после L02: нужен работающий путь обновления, оценка 10 минут

  Описание задачи: После обычного сохранения оператор увидит выбранный канал и новую заметку после перезагрузки.
  Приёмка: Выбрать канал, сохранить заметку, перезагрузить страницу и проверить результат.
  Затрагиваемые файлы: `src/settings.py`, `tests/test_settings.py`
```

The renderer preserves description, acceptance and affected files separately. Its groups show finished, running, blocked and queued tasks and omit empty groups. `⌛` denotes an external answer being awaited; `⏸` a deferred task. A dependency wait is queued rather than an external blocker.

A blocked task names the actual obstacle and next step. A queued task names its real dependency or lack of an assigned executor. Readiness alone does not mean that a Worker has started. `∥` records work running in parallel.

## Timing

Keep the original `estimate_minutes` alongside a revised forecast. The current tool's default leaf limit is 15 minutes; a direct user change is saved in plan-level `estimate_policy`. The 20-minute Worker checkpoint is a different setting.

`actual_minutes` is measured effort. `started_at` and `finished_at` are the observed clock window; prefer timestamps with timezone across days. Missing measurement stays «не измерено». Explain a material overrun and update the remaining route rather than rewriting the old estimate.

`estimate_unknown_reason` means only part of the work can be estimated. Show that subtotal and an unknown full deadline. Missing estimates never silently become zero or a default 15 minutes. External waits and capacity affect delivery time.

## Leaf reference

```json
{
  "id": "L12",
  "label": "Показать сохранённую заметку",
  "status": "running",
  "description": "Оператор увидит выбранный канал и заметку после перезагрузки.",
  "acceptance": "Сохранить и перезагрузить страницу; выбор и текст восстановились.",
  "affected_files": ["src/settings.py"],
  "owner": "worker-1",
  "session": "<actual-native-id>",
  "harness": "opencode",
  "model": "<selected-catalog-model>",
  "depends_on": ["L03"],
  "estimate_minutes": {"minimum": 10, "maximum": 15},
  "note": "Форма сохраняет значение; проверяем восстановление."
}
```

The filename matches `id`; `label` is required. Status is `queued`, `running`, `blocked`, `waiting`, `deferred` or `done`. The collector also accepts its documented localized aliases. Use actual native identities and a declared planned model; missing runtime evidence stays unknown.

`result` holds the executor's result. `planned_start`, `planned_finish` and `wait_reason` describe scheduling; actual start/finish are separate. `tier` uses `fast|middle|frontier`, `complexity` uses `S|M|L`; pricing and token fields distinguish provisional estimates from observed usage.

Invalid JSON, conflicting IDs and broken dependencies are reported with the file to fix. `plan-artifacts` contains write commands and the current supported fields.

## History and recovery

An optional `journal` records material changes with time, action, result and evidence. Preserve original estimates and revisions. Keep long investigation or test evidence in referenced task files rather than copying it into every view.

After compaction, use the bound plan snapshot or `show_plan`. Boss compares this work with the original request and latest corrections; its feedback is independent of report formatting. The plan's `goal_control` view distinguishes completed cards from acceptance of the original goal.
