> Background reference. Load only when the task needs this mechanism. `AGENTS.md` wins on any conflict: its finish line, blocker lists, escalation chain and delivery rules override this file.

# The task graph

Every objective that is decomposed has one machine-readable task graph. It is the
same content as the live plan report, kept in a form a tool can read: the report
is written for a person, the graph is written for the schedule, the dashboard and
the next session. One objective, one graph, updated together with the report.

## Where it lives

Next to the objective's task record, as `plan.graph.json`:

```text
<project-root>/.agents/tasks/<objective>/plan.graph.json
```

The report stays under `## Plan` in the task record. Both files describe the same
leaves: the graph is never a second plan, and the report is never the only copy.

## One command

```sh
python3 <LHC>/common/tools/lhc_grid.py render <project-root>/.agents/tasks/<objective>/plan.graph.json -o <project-root>/.agents/tasks/<objective>/plan.html
```

`render` writes one self-contained HTML file: what is done, what runs now, what is
blocked, the rough finish time and how much of the work runs in parallel. Add
`--open` to open it in a browser. The same file opens on a phone, attaches to a
message and needs no server, no network and no dependencies.

`status` prints the same facts as text for a chat answer, `export` converts a
plan report or a free-form replan into the standard graph, and `validate` checks
the graph structure.

`check-plan` reconciles the report with the graph:

```sh
python3 <LHC>/common/tools/lhc_grid.py check-plan <objective>/plan.report.md <objective>/plan.graph.json
```

The report's task list and the graph's leaf list are one set: the same ids, the
same statuses, no task without a leaf and no leaf without a task. The command
prints every divergence and exits non-zero when the two disagree.

The graph is not the canonical artifact — the leaf files are. The graph is
collected from `leaves/<ID>.json`, and the dashboard, the text view and the plan
section of a compaction handoff are all rendered from it, so a stale report
never becomes the plan of record and a hand-edited graph never becomes the
source either. One leaf file, one owner; the graph is its projection.

## Format

`schema_version: 2`. Version 1 (the planning graph) stays readable: the live
fields are optional there.

```json
{
  "schema_version": 2,
  "title": "ExManager → Board integration",
  "goal": "why the person wants the changes",
  "business_result": "the tangible capability the person will have after the changes",
  "acceptance_scenarios": ["Actor/context, ordinary actions, expected visible result on the real surface."],
  "current_progress": "what is actually done or checked now, with verification limits",
  "external_waits": "pending human or platform waits, outside the active work",
  "slots": 4,
  "updated_at": "2026-10-21T06:16:00",
  "tasks": [
    {
      "id": "contract",
      "label": "checked source lookup and author rights",
      "status": "done",
      "depends_on": [],
      "parallel_with": [],
      "estimate_minutes": {"minimum": 10, "maximum": 15},
      "actual_minutes": 12,
      "started_at": "14:02",
      "finished_at": "14:09",
      "owner": "A",
      "session": "codex:948b",
      "harness": "codex",
      "model_class": "gpt-6-luna",
      "model": "gpt-6-luna",
      "blocker": "",
      "description": "Кто и что изменит, зачем это человеку и какой путь это затронет; текст не обрезается искусственным лимитом.",
      "acceptance": "Как человек проверит ожидаемое изменение и что увидит.",
      "affected_files": ["src/module.py", "tests/test_module.py"],
      "blocker_details": {
        "reason": "the concrete reason this task cannot continue",
        "responsible": "the named person or active owner who handles it",
        "next_action": "the smallest specific next step",
        "human_required": "yes",
        "human_action": "the exact decision or access the person must provide"
      },
      "note": "",
      "wave": 1
    }
  ]
}
```

Required per task: `id`, `label`, `status`, `depends_on`. `description`,
`acceptance`, and `affected_files` are separate optional fields: the first
explains the work in human language, the second says how to recognize its result,
and the third lists affected paths. Descriptions and file lists have no
application-imposed short character cap. Older schema-v1 and schema-v2 graphs
remain readable; legacy task `description` is retained as a description, and
existing acceptance data remains available. Everything else is
optional but expected for a live objective. An optional field is checked only
when it is present: declaring a path, a model class, an acceptance line or an
unknown estimate is a choice, never a demand.

- `status` is `done`, `running`, `blocked`, `waiting`, `deferred` or `queued`. It is the
  state of the work, not the state of the paperwork.
- `depends_on` holds ids of tasks that must be finished first. It is the only
  scheduling input: the renderer derives waves, the parallel profile and the
  critical path from it.
- `parallel_with` records that two leaves actually ran together. It documents
  parallelism; it never creates a dependency.
- `estimate_minutes.minimum` / `.maximum` are the original bounds. They are
  never rewritten to fit reality; the revision goes into `note`. A graph may
  estimate only some of its leaves; the total is then aggregated over the
  leaves that declare a bound, and an unestimated leaf never becomes a silent
  zero.
- `estimate_minutes.basis` and `estimate_minutes.uncertainty` name the work the
  bound came from and what could widen it. They are optional; when they are
  present they must say something.
- `estimate_unknown_reason` is an optional, nonempty explanation for a task
  whose active effort cannot yet be estimated. It is a deliberate statement, not
  a substitute for a missing field: when a task declares it, the validator
  reports no total at all and the renderer labels the deadline unknown instead
  of treating the task as zero minutes. A task that declares neither an
  estimate nor a reason simply stays outside the total.
- Top-level `external_waits` records pending human/platform waits separately
  from active work. If it is nonempty, the renderer withholds a clock ETA and
  labels the finish time unknown; it still shows the bounded active-work
  subtotal.
- Top-level `goal` states the user's purpose. `business_result` and optional
  `business_results` keep legacy storage names but declare future tangible
  capabilities («Что будет работать»). Optional `acceptance_scenarios` is a
  `list[str]`: actor/context, actions and expected visible result for testers on
  the real surface. `current_progress` records only current facts («Что уже
  сделано»); evidence supports observations, not the declaration itself. For
  CLI/libraries, name the actual operator/caller and call/result. A pending
  expectation is valid; claiming achievement requires real-scenario evidence.
  New/updated plans follow `PLAN_REPORT.md`; historical reports/revisions stay
  untouched, and loading legacy declarations never invents fulfillment. The old
  «Бизнес-результат» heading remains accepted. This is a meaning contract, not a
  regex semantic classifier or a new gate.
- `actual_minutes` is the summed effort of the executors on the leaf. If it was not
  measured, leave it out instead of inventing a number. The window on the clock is
  `started_at` and `finished_at`, and it is a different number: 22 minutes of effort
  inside an 11 minute window means two executors worked in parallel. The dashboard
  shows both as «усилие» and «по часам».
- `journal` is an optional top-level change log of the plan: a list of entries with
  `at` (the time), `action`, `result` and `evidence` (the confirmation). The
  dashboard renders it as a change log. Without it the panel falls back to the
  statuses of the leaves, which repeats the task names and is not a history.
- `owner`, `session`, `harness` and `model` say who works on the leaf now. The
  dashboard shows them so the user can see which session owns what.
- `role`, `acceptance`, `read_paths` and `write_paths` declare who owns the
  leaf, how it is accepted and which mutable paths it touches. They are
  optional; when they are present the offline checker validates them.
- `acceptance` states the result a person can verify. It is shown in the task
  details of the dashboard.
- `model_class` is the declared worker class of the leaf, one of the allowed
  model names (`glm-5.3-flash`, `minimax-3.1-flash`, `gpt-6-luna`, `glm-5.3`,
  `gpt-6.1-sol`). `model` is the model actually in use on that leaf. Both are
  optional: add `model_class` only when the worker class is known and
  intentionally assigned, and do not fill an unknown assignment with a default.
- `blocker` names the concrete external obstacle. `waiting` is not a blocker: a
  leaf waiting for a dependency is `queued`. A leaf is blocked when its status
  says `blocked`; a blocker text alone does not make a queued leaf blocked.
- `deferred` is a leaf the owner deferred: no answer is expected, it waits for
  nothing, it takes no slot and it is not part of the remainder of the delivery.
- `blocker_details` is an optional, additive object for blocked tasks. Its
  optional keys are `reason`, `responsible`, `next_action`,
  `human_required` (`yes`, `no`, or `unknown`), and `human_action`. Existing
  graphs that contain only `blocker` continue to render; the renderer supplies
  honest unknown/unspecified fallbacks instead of inventing an owner or action.
  Keep technical task IDs in the task detail panel, while dependencies and
  blocker cards show human-readable task names.
- `wave` is optional. When absent, the renderer derives the wave from the
  dependency layers.

## Rules

1. Write the graph when the objective is decomposed, before dispatch. A
   decomposition without a graph is not finished.
2. Update the leaf file at every plan boundary; the graph, the report and the
   page are projections of it. A projection that says `queued` while the leaf
   file says `done` is wrong in both directions. The order is fixed: write the
   leaf file, build the graph from the leaf files (`lhc_plan_json.py build`),
   then build the view on the built graph, then reconcile the projections with
   `check-plan`.
3. The leaf files, the report's tasks and the graph's leaves are one set. No task
   without a leaf, no leaf without a task, no two places claiming a different
   status for the same task. `check-plan` prints the divergence and exits
   non-zero.
4. Estimate from the work and its proof, in minutes, with the named uncertainty.
   An unknown estimate is honest; a padded one is not.
5. Record the real blocker text, not "waiting" or "later".
6. A blocked leaf keeps its estimate and dependency; the forecast then shows the
   blocked work separately instead of hiding it inside a total.
7. The forecast is a plan, not a promise: capacity, resource conflicts and
   external waits stay visible in the report next to the graph.

## Check the decomposition

One pass after the graph is written, before dispatch, by someone who did not
draw it (Adviser or Critic, plan only): for every `depends_on` edge name the
concrete output of the first leaf that the second one reads. No output named
means no edge: drop it. Then ask of every leaf in a later wave whether it can
start now, and move it forward when it can. Record the result in `plan.json`
as `decomposition_check` (who checked, the edges kept with what they read, the
leaves moved). A leaf is `done` only when everything it depends on is `done`.

## Checking it

The offline checker validates declared path and dependency conflicts:

```sh
python3 scripts/lhc_validate_graph.py <plan.graph.json>
```

It accepts exactly the format above: `id`, `label`, `status` and `depends_on`
are required, every other field is checked only when it is present. A graph
exported by `lhc_grid.py export` passes it unchanged, as does the published
example above. A declared `model_class` must be one of the allowed model names.

It checks only declared paths and dependencies. It does not run a scheduler and
does not judge whether two leaves are conceptually independent.
