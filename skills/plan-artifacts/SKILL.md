---
name: plan-artifacts
description: Create LHC project-plan artifacts in one pass — one JSON file per leaf, the collected plan.graph.json, the HTML dashboard and the Markdown summary — with the exact commands (build, check, render, export, check-plan) and their consistency check. The leaf file is the source of truth; the graph, the report and the page are projections of it. Use when the user asks to составить план, сделать план проекта, спланировать работу, or asks for a project/work plan; also use when tasks are decomposed, leaves change, or the dashboard needs refreshing. If the user explicitly asks only for a rough chat sketch, do not create files. Never reverse-engineer the format from the tool source: this skill is the procedure.
---

# Plan artifacts

## The owner's link (do this first)

The owner follows plans from his phone, not from your disk. Right after the
first leaves of a new plan are written, run
`python3 "<tools>/lhc_plan_mirror.py" link <plan-dir>` and give the printed URL
to the owner once, on its own line, in your next reply. It is the permanent
public page of this plan (`https://…/<project>/<plan>/`), not `plan.html`. The
prompt hook already prints this link for plans it creates; then just pass it
on. If the command says no mirror is configured, say so in one line and go on.
All plans are listed on the mirror's home page with state, stage and expected
finish.

## Requests for a project or work plan

Treat natural Russian requests including «составь план», «сделать план проекта»,
«помоги спланировать работу», «план проекта» and «план работ» as a request for a
project/work plan. Unless the user explicitly asks for a prose-only chat sketch,
create the leaf files, the `plan.graph.json` and the `plan.html`; rendering also
produces `plan.md`. Do not route a request merely to write or update one short
file into this full project-plan flow when no project/work plan was requested.
This boundary does not waive the normal planning required for engineering work
under the selected LHC mode.

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

## The plan is a directory of leaf files

A plan lives in one directory. Every leaf of the plan is one JSON file in the
`leaves/` subdirectory, named after the leaf:

```text
<plan-dir>/plan.json          purpose, expected capabilities, scenarios, current progress, slots
<plan-dir>/leaves/L01.json    one leaf — one file — one owner
<plan-dir>/leaves/L02.json
<plan-dir>/plan.graph.json    collected from the leaves; never written by hand
<plan-dir>/plan.html          the page
<plan-dir>/plan.md            the text summary of the same graph revision
```

The leaf file is the source of truth of its leaf. The graph, the report and the
page are projections of it: nobody writes them by hand. The owner of a leaf
changes his own file and nothing else, so two workers never write the same file,
never conflict and never wait for each other.

## 1. Write one file per leaf

One leaf file looks like this:

```json
{
  "id": "L01",
  "label": "Собрать сборщик листов",
  "status": "running",
  "description": "Что именно делает лист.",
  "acceptance": "Как проверить, что лист сделан.",
  "affected_files": ["src/common/tools/lhc_plan_json.py"],
  "owner": "worker-1",
  "session": "mvs_...",
  "harness": "codex",
  "model": "minimax-3.1-flash",
  "depends_on": [],
  "estimate_minutes": {"minimum": 15, "maximum": 20},
  "actual_minutes": 7,
  "started_at": "14:02",
  "finished_at": "",
  "note": "Что ещё важно знать про этот лист.",
  "updated_at": "2026-10-23T22:04"
}
```

`id` equals the name of the file: `L01.json` is the leaf `L01`, and a file whose
`id` contradicts its name is rejected. `label` is required and is the title of
the leaf in the user's language.

`status` is one of `done`, `running`, `blocked`, `waiting`, `deferred`, `queued`.
The words of the report (`готово`, `в работе`, `ожидание`, `отложено`,
`заблокировано`, `в очереди`) and its markers (`✅`, `🔄`, `⌛`, `⏸`, `⛔`, `⏳`)
mean the same thing and are accepted as well. A new leaf starts as `queued`.
`waiting` is not a blocker: a leaf that waits for another leaf is `queued`, and
`blocked` names the concrete external obstacle in `blocker`. `deferred` is a leaf
the owner deferred: no answer is expected, it takes no slot and it is outside the
remainder of the delivery.

`estimate_minutes` keeps the original bounds and is never rewritten to fit
reality: `{"minimum": 15, "maximum": 20}`, `{"min": 15, "max": 20}` and a plain
number are all accepted. A leaf that estimates only part of the work also carries
`estimate_unknown_reason`, so the forecast shows an unknown deadline instead of a
silent zero.

Full Cycle planning is real elapsed work: creating the plan is its first task,
so the upper rail «Начало плана» includes planning, not only coding/execution.
Native creation automatically records timezone-aware `created_at` on each leaf;
native updates preserve it. No manual timestamp is required. Build and the local
source observer freeze `plan_origin` once in `.lhc-publication/plan-origin.json`.
For legacy leaves the source host may recover filesystem birthtime, labelled
«восстановлено по файлам»; earlier recorded work takes precedence. Without birth
data or an absolute recorded start, the beginning remains explicitly unknown.
Neither mtime/ctime nor mirror receipt/render time is creation evidence. Edits,
deletion, splitting and new revisions retain this origin; copies retain its
metadata. Mirrors only consume provenance sent by the source. Read-only check
does not create metadata; historical snapshots are never rewritten.

`actual_minutes` is the summed effort of the executors; `started_at` and
`finished_at` are the window on the clock. Prefer ISO with timezone, for example
`2026-10-24T23:55:00+03:00`, to measure across midnight or days. Legacy `ЧЧ:ММ`
remains accepted; public comparison does not invent its date. 22 minutes of
effort inside an 11 minute window means two
executors worked in parallel — the dashboard shows both, as «усилие» and «по
часам», and never one number quietly meaning the other.

`depends_on` holds the ids that must finish first and is the only scheduling
input: waves, parallelism and the critical path are derived from it.
`parallel_with` names the leaves it runs at the same time as. `updated_at` is
when the leaf was last changed; the plan takes the newest of them as its own
update time.

The complete set of fields a leaf file may carry is exactly:

```text
acceptance, actual_minutes, affected_files, blocker, blocker_details, complexity, cost_source, cost_usd, created_at
depends_on, description, duration_estimate_minutes, estimate, estimate_max, estimate_min, estimate_minutes, estimate_over_limit_reason
estimate_unknown_reason, finished_at, harness, id, label, model, model_class, note
origin, owner, parallel_with, planned_finish, planned_start, progress_events, result, session
started_at, status, supersedes, tier, token_estimate, updated_at, wait_reason, wave
```

An unknown field stops the collection and is named, like every other defect.
`role`, `read_paths`, `write_paths` and `paths` are **not** leaf fields — the
collector rejects them. They belong to a hand-declared graph; see the old path
below.

Plan-level facts are not a leaf's business. They live in `plan.json` next to
`leaves/`:

```json
{
  "title": "План поставки",
  "goal": "Пользователь хочет следить за ходом работы по одной ссылке.",
  "business_result": "После сохранения локального листа новая заметка появится по прежней ссылке в течение установленного интервала.",
  "acceptance_scenarios": ["Оператор открывает страницу, меняет note обычным сохранением и проверяет появление новой заметки по прежней ссылке без publish."],
  "current_progress": "Сценарий определён; обновление страницы ещё не проверено.",
  "slots": 2,
  "updated_at": "2026-10-23T22:04"
}
```

`business_result` and optional `business_results` keep their legacy storage names
but describe future tangible capabilities, displayed as «Что будет работать».
`goal` explains why the person needs them. Optional `acceptance_scenarios`
(`list[str]`, «Как проверим») names actor/context, actions and expected visible
results for testers on the real surface. For CLI/libraries, use the actual
operator/caller and call/result instead of requiring commercial language.
`current_progress` (for display, «Что уже сделано») and evidence record current
facts separately: tests, commits and publication are not the expected capability.
A pending result is not a false claim; an achieved result requires evidence.
See `common/protocols/PLAN_REPORT.md` for the full distinction and recovery example.

New and updated plans use this contract. Keep historical reports, revisions and
user messages untouched; old fields are legacy declarations and never imply
fulfillment. Accept the old Markdown heading «Бизнес-результат» as well as the new
visible label. Do not add regex semantic classifiers or gates for wording.

`plan.json` may also carry `business_results`, `current_progress`,
`external_waits`, `journal` and `planned_start_at` (ISO with timezone, only when
the intended start is known). When it is absent the collector falls back to the
plan-level fields of an existing `plan.graph.json`, so a plan that already has a
graph keeps its title, goal and business result.

Optional plan-level `started_at` and `finished_at` record actual execution,
preferably ISO with timezone. Record the start when real execution begins;
never backfill a guessed date from publication, mtime or a planned start.
Keep existing valid times. Missing historical times remain unknown. The upper
card shows a separate time rail: its forecast is anchored to the last confirmed
absolute source event, while task percentages still count tasks. Browser clocks
use the explicitly labelled local timezone; archived/downloaded pages say
«На момент снимка» and freeze time. Unknown waits/estimates withhold a full ETA.

## 2. Collect the leaves into the graph

Do not hand-write the graph. The collector reads the leaf files, validates them
and gathers them into one `plan.graph.json` of the existing graph schema:

```sh
python3 "<tools>/lhc_plan_json.py" build <plan-dir>
python3 "<tools>/lhc_plan_json.py" check <plan-dir>
```

`build` writes `<plan-dir>/plan.graph.json` atomically, so a reader never sees
half of it, and prints the path it wrote. `check` validates the leaves and
writes nothing — it is the same validation without the write.

The collection is deterministic: the same leaves always give the same graph,
byte for byte, and the order of the leaves does not depend on the order the
filesystem hands them over. A rebuilt plan is therefore comparable with the one
before it.

A leaf that cannot be read stops the collection and is named — a broken leaf
never becomes a missing leaf:

```text
LHC: <plan-dir>/leaves/L12.json: битый JSON: Expecting value: line 1 column 21 (char 20)
```

The same is true for an unknown status, an unknown field, an id that contradicts
the name of the file, a dependency on a leaf that does not exist and a cycle of
dependencies. Both commands exit non-zero on such a defect, and the message
names the file to fix.

## 3. Render the page

```sh
python3 "<tools>/lhc_grid.py" render <plan-dir>/plan.graph.json --out-dir <plan-dir>
```

`--out-dir` writes `plan.html` and `plan.md` from one graph, and both carry the
same revision of the plan. Two artifacts of one plan are generated, never kept
in sync by hand: if the two revisions differ, they are two plans.

`python3 "<tools>/lhc_grid.py" status <plan-dir>/plan.graph.json` prints the same
facts as text when the answer belongs in a chat message. It also prints the
leaves in the order of the graph, which is the order the report has to use (see
section 5).

## 4. The page rebuilds itself

The agent does not have to remember the commands of sections 2 and 3. The hook
(`<tools>/lhc_entry.py`) watches the files a tool has written: a write into
`leaves/` rebuilds the graph of the whole plan from the leaf files and then
rebuilds the page. The hook is installed for `codex`, `claude-code`, `zcode` and
`opencode`; `hermes` registers no LHC hook, so there the collector command is
what rebuilds the page. The chain never loops — the hook reacts to the files the
agent wrote, and the files the hook writes are not part of that event.

Measured on this machine: the collect-and-render chain takes about half a
second (0.43–0.51 s over five runs), and the whole hook call about 0.7 s. The
hook says so when it did the work:

```text
LHC: страница плана пересобрана из <plan-dir>
```

A leaf that cannot be collected stops the rebuild and is named:

```text
LHC: план не пересобран: <plan-dir>/leaves/L12.json: битый JSON: ...
```

Run the commands of sections 2 and 3 by hand when you need the graph or the
page right now — after a compaction, before a handoff, or when the hook does not
run in the current harness.

## 5. The readable report and the reconcile

The report is the plan for a person, in the user's language. It lives under
`## Plan` in the canonical task record, next to the objective. When the plan has
leaf files, the report is written **from** them, never the other way round.
Three header lines, then the leaves: finished, running, blocked, queued — an
empty group is dropped and the groups are never merged. Canonical wording (the
Russian rendering; the field wording and the emoji do not change with the
language):

```text
Цель: <какой человек выполняет какую задачу, на какой обычной поверхности и с какими главными границами>
Что будет работать: <какая осязаемая возможность появится у пользователя после изменений>
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

Reconcile the report with the graph:

```sh
python3 "<tools>/lhc_grid.py" check-plan <record> <plan-dir>/plan.graph.json
```

`check-plan` prints every divergence between the report and the graph and exits
non-zero when task IDs, statuses, or explicitly stated description, acceptance
and affected-file details disagree. That exit code is the gate: the plan is not
finished until it passes. It does not reject descriptions by length.

The report's leaf lines carry a positional id — the first line is `L01`, the
second is `L02` — and `check-plan` matches the report to the graph by that id
first; a unique title match is the only fallback. Write the report's lines in the
order of the graph, which is the order `status` prints.

## 6. The live page

The built page carries a small poller: every two seconds it asks the server for
the very same `plan.html` and, when the content differs from what is on the
screen, swaps the content in without a reload. The plan that changed a second
ago is visible without asking anyone to reload the page.

The poller fetches the page over HTTP. A page opened straight from the disk
(`file://`) is not allowed by the browser to fetch itself, so it stays as it was
rendered — the content is still correct, only the automatic refresh is
unavailable. Serve the plan directory over HTTP to get the live page:

```sh
python3 -m http.server --directory <plan-dir> 8000
```

Then open `http://localhost:8000/plan.html`.

## 7. A plan without `leaves/` — the old path still works

A plan that has no `leaves/` directory is not a leaf-file plan, and its behaviour
stays exactly as it was. The collector refuses it and says so:

```text
LHC: <plan-dir>: каталог leaves/ не найден
```

Such a plan keeps the report-first way of working:

```sh
python3 "<tools>/lhc_grid.py" export <record> -o <plan-dir>/plan.graph.json
python3 "<tools>/lhc_grid.py" render <plan-dir>/plan.graph.json --out-dir <plan-dir>
python3 "<tools>/lhc_grid.py" check-plan <record> <plan-dir>/plan.graph.json
```

`export` derives the graph from the report under `## Plan` — the ids, the
statuses, the dependencies and the estimate bounds. The report cannot carry the
attribution, so set it once on the first export and let `--merge` carry it
through every later refresh:

```sh
python3 "<tools>/lhc_grid.py" export <record> -o <plan-dir>/plan.graph.json --merge <plan-dir>/plan.graph.json
```

The fields `--merge` carries are `role`, `read_paths`, `write_paths`, `paths` and
`affected_files` per leaf, plus `current_progress` and `external_waits` on the
document. `read_paths`, `write_paths` and `paths` are how one owner per path is
proven, so write them for every leaf that touches a file — and keep the mutable
paths disjoint: two leaves that may run at the same time must not declare the
same mutable path. A shared mutable path needs either a dependency between those
leaves or isolated ownership, and the optional offline checker
`scripts/lhc_validate_graph.py <graph.json>` (source checkout only) fails on
exactly that conflict. A graph made by `export` always carries `depends_on`, even
an empty one, and therefore passes that checker.

## 8. The order at every plan boundary

1. update the leaf file of the leaf that changed — the owner of a leaf writes
   his own file and nothing else;
2. the page rebuilds itself (or run `build` and `render` from sections 2 and 3);
3. update the report in the record from the leaf files;
4. `check-plan` — fix every divergence it prints.

Do this at each 30-minute plan boundary, before dispatching work, before reporting
a result, and before handing off after compaction. The leaves are what the work
is; the graph is what the schedule, the forecast and the next session read. They
are one set of leaves, and `check-plan` is the proof that the report and the
graph still are.

## 9. The field reference

`common/protocols/TASK_GRAPH.md` is the canonical field list of the graph,
`common/protocols/PLAN_REPORT.md` the canonical report format and the canonical
leaf-file format; read them only for a field this skill does not mention.

The forecast counts from the last confirmed event, not from the moment the page is
opened: an idle plan must not push its own finish away with every minute of
silence. The dashboard shows the anchor and the idle time, and reports a horizon
that has already passed as passed.

A graph may carry its own `journal` — a change log with time, action, result and
confirmation. The report may carry the same thing as a `## Журнал изменений`
section. The dashboard renders it as a change log. Without it the panel falls
back to the statuses of the leaves, which is a second list of the table, not a
history.

## 10. What the dashboard is

The dashboard is a snapshot of the plan, not a control panel. It shows what the
plan says; the actual state of the work comes from the API of the owners. A
button in it does not change the fleet — it only draws the plan.

## 11. What the tools cannot do for you

- They do not choose the leaves. Decomposition is yours: one accepted outcome, one
  shortest real canary, hard dependencies only on the real consumer path, one
  owner per leaf.
- They do not write the business result, the acceptance line or the blocker text.
- They do not translate: the labels, the report and the dashboard are written in
  the user's own language by you.

## 12. Public HTML, CLI first

### Local-first mirror (preferred when configured)

The local `plan.json`, `leaves/*.json` and `.lhc-publication/` history are
authoritative. A separate no-LLM observer automatically mirrors ordinary file
saves. The server renders sanitized JSON; it never writes local source files.
For plans in the configured observer roots, just save the files: no publish,
build, MCP call or environment variable is needed for website updates.

Configure the narrow scope once with `~/.config/lhc/plan-mirror/client.json`
(`mode: "mirror"`, `endpoint`, `base_url`, protected `token_file`, `data_dir`,
explicit `roots`/`plans`). Never scan the whole home or private transcripts.
Deployment starts `lhc_plan_mirror.py watch --config CLIENT` as a user service
or LaunchAgent, independent of agent hooks. `register PLAN --config CLIENT`
can migrate a previously published plan: URL and immutable r001 remain.
Registration/discovery stores a local binding in `.lhc-publication/mirror.json`;
normal CLI/MCP publish/revise then use it automatically with zero network.
The first stable source snapshot creates r001 locally. `revise --reason TEXT`
stores the new immutable local revision even offline. Do not remove history
or copy a registered plan to another owner and overwrite its URL.

Only the observer uses HTTP. It keeps one durable latest pending snapshot with
all revisions and observed facts, retries with backoff, and catches up after
restart without an agent retry. Broken/partial/temporarily absent files retain
the last valid replica. A server outage is never a leaf blocker or development
gate. `lhc_plan_mirror.py status --config CLIENT` reports local file event,
last successful sync, server receipt and error separately; missing means unknown.
The private dashboard capability URL lists recent/reported-running plans.
Freshness and a reported running leaf never prove that an agent is alive.

The optional LhcPlan MCP edits the same local leaves and uses the same revision
CLI. The default `scripts/plan_mcp.py` exposes create_leaf, update_leaf,
update_progress, build_plan, estimate_cost, publish_html and revise_plan.
All invoke one canonical implementation; the deprecated plan_publish_mcp.py
launcher delegates to the same server and is not registered separately.
The old four-tool/default and seven-tool/publishing split is removed.
MCP remains optional; local files and CLI remain usable without it.
It is not a second planner. Local standalone rendering and the legacy
publisher below remain available for unbound plans.

When continuing an existing plan from a new Codex session/worktree, reuse that
plan; do not create a duplicate. The native `UserPromptSubmit` hook automatically
binds an unambiguous ready leaf in the current worktree, records the actual
session/owner and one progress event, then rebuilds the local graph and HTML.
When no matching source exists it creates a local fullcycle scaffold before the
model starts. This path does not require a command, MCP, network, SSO, or server
availability. If a mirror config is installed, only the selected local plan is
registered there; otherwise local plan files remain the source of truth and can
be synced later. The worktree root and session binding stay in the local
`.lhc-publication/mirror.json`, not in the public plan. For non-Codex harnesses,
use the local activation API with an actual session id; never invent one. Keep
using the leaf CLI for later status changes so progress history is retained; raw
saves remain supported, and the observer rebuilds local graph/HTML when it detects
them. Do not make MCP, network, SSO, or public publication a prerequisite for
local execution.

### Legacy standalone publication

Use the actual shared plan-dir in every worker assignment. A worktree is not a
new plan. For NEW plans, after writing the initial leaves, run the following
initial publication whenever the host has configured `~/.config/lhc/publish.json`:

```sh
python3 "<tools>/lhc_plan_publish.py" publish-html <plan-dir> --autopublish
```

This workflow initialization binds only that new safe plan; never bulk-publish
existing unbound plans. Existing plans require an explicit initial publish.
The configuration is a host-local object:

```json
{"webroot":"/var/www/lhc","base_url":"https://lhc.bezrabotnyi.com"}
```

An optional `ssh_host` is an existing SSH alias; the same CLI copies the bundle
using existing SSH credentials. No new key/token store. Use `--config FILE` to
select a different target before first publication. The stable identity and
binding stay in `<plan-dir>/.lhc-publication/state.json`; do not remove/reset this
directory when rebuilding the graph. Keep it local and back it up with the plan.

The first publish freezes r001. Source estimates, dependencies and original
intent remain in that immutable snapshot. Status/notes do not create revisions.
Planning edits are shown as unaccepted changes until the deliberate command:

```sh
python3 "<tools>/lhc_plan_publish.py" revise <plan-dir> --reason "Изменилась зависимость"
```

r002 links to r001; old HTML/JSON remain byte-identical, including facts known
at that time. To split/remove tasks, keep stable IDs and record `origin` and
`supersedes` (list of prior IDs). Removed tasks remain visible from snapshots.
Measured effort is `actual_minutes`; independent scheduled duration can use
`duration_estimate_minutes`. Without the latter the legacy estimate is an
explicit scheduling assumption. No active minutes are inferred from mtime.

```sh
python3 "<tools>/lhc_plan_json.py" create-leaf <plan-dir> L01 --fields '{"label":"Проверить страницу","estimate_minutes":10}'
python3 "<tools>/lhc_plan_json.py" progress <plan-dir> L01 --note "Страница открыта, проверка продолжается" --fields '{"status":"running"}'
python3 "<tools>/lhc_plan_json.py" update-leaf <plan-dir> L01 --fields '{"status":"done"}' --expected-hash <sha256-from-previous-write>
python3 "<tools>/lhc_plan_json.py" build-plan <plan-dir>
```

The CLI appends `progress_events`, atomically validates/replaces one leaf, and
serializes writers with a plan-local lock. Direct file edits remain supported;
use the CLI to preserve append-only history and optimistic conflict detection.
Reliable Codex `CODEX_THREAD_ID` binds session/harness only when missing. Other
harnesses pass actual identity explicitly; missing is unknown. The tool never
invents model identity or turns a successful command into business acceptance.

After opting in, collector builds and the normal leaf-write hook re-publish
without MCP. Unchanged public inputs skip delivery; a short coalescing window
bounds burst work. Failure logs a warning and leaves the last good page while
leaf work continues. Do not re-enable globally disabled native hooks.

The page is unlisted and gets a random suffix of at least 96 bits. Anyone with
the link can read/copy/share it. `noindex` is NOT authentication. Publish only
authorized safe plan metadata/notes: never credentials, transcripts or private
project dumps. Paths and recognizable credential patterns are redacted as a
best-effort backstop, not a security boundary. Configure the static host to deny
directory listing/dotfiles and set no-store, no-referrer and noindex headers.

The current page polls `version.json` with no-store every 12 seconds over HTTP,
reloads only changed versions and restores scroll. Revision pages and downloaded
HTML are standalone immutable snapshots. The badge reports missing connection
or an old snapshot; it does not prove the worker is online. Delivery keeps the
current and one previous generated bundle; revision files remain in each bundle.

`plugins/last-human-commit` is the single self-contained package. Its optional
LhcPlan server starts with `scripts/plan_mcp.py` and exposes `create_leaf`,
`update_leaf`, `update_progress`, `build_plan`, `estimate_cost`, `publish_html`
and `revise_plan` through the same canonical CLIs. Native plugin discovery
registers that one server; clients without native discovery can use
`scripts/setup_plan_mcp.py` (dry-run by default). The deprecated
`scripts/plan_publish_mcp.py` is an alias for the same implementation, not a
second registration. Local CLI and offline mirror workflows need no MCP.
