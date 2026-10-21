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

## Format

`schema_version: 2`. Version 1 (the planning graph) stays readable: the live
fields are optional there.

```json
{
  "schema_version": 2,
  "title": "ExManager → Board integration",
  "goal": "one accepted business outcome",
  "business_result": "what the user can already use now",
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
      "model": "gpt-6-luna",
      "blocker": "",
      "acceptance": "what a person can verify when this task is done",
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

Required per task: `id`, `label`, `status`, `depends_on`. Everything else is
optional but expected for a live objective.

- `status` is `done`, `running`, `blocked`, `waiting` or `queued`. It is the
  state of the work, not the state of the paperwork.
- `depends_on` holds ids of tasks that must be finished first. It is the only
  scheduling input: the renderer derives waves, the parallel profile and the
  critical path from it.
- `parallel_with` records that two leaves actually ran together. It documents
  parallelism; it never creates a dependency.
- `estimate_minutes.minimum` / `.maximum` are the original bounds. They are
  never rewritten to fit reality; the revision goes into `note`.
- `estimate_unknown_reason` is an optional, nonempty explanation for a task
  whose active effort cannot yet be estimated. When a graph contains numeric
  estimates, every other task must either provide this field or a numeric
  estimate. The validator accepts the graph but reports aggregate duration as
  unavailable; the renderer labels the deadline unknown instead of treating
  the task as zero minutes.
- Top-level `external_waits` records pending human/platform waits separately
  from active work. If it is nonempty, the renderer withholds a clock ETA and
  labels the finish time unknown; it still shows the bounded active-work
  subtotal.
- `actual_minutes` is measured active time. If it was not measured, leave it out
  instead of inventing a number.
- `owner`, `session`, `harness` and `model` say who works on the leaf now. The
  dashboard shows them so the user can see which session owns what.
- `blocker` names the concrete external obstacle. `waiting` is not a blocker: a
  leaf waiting for a dependency is `queued`.
- `acceptance` states the result a person can verify. It is shown in task
  details; validated live plans must include it.
- `model_class` is optional. Add it only when the worker class is known and
  intentionally assigned; do not fill an unknown assignment with a default.
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
2. Update the graph and the report together at every plan boundary. A graph that
   says `queued` while the report says `done` is wrong in both directions.
3. Estimate from the work and its proof, in minutes, with the named uncertainty.
   An unknown estimate is honest; a padded one is not.
4. Record the real blocker text, not "waiting" or "later".
5. A blocked leaf keeps its estimate and dependency; the forecast then shows the
   blocked work separately instead of hiding it inside a total.
6. The forecast is a plan, not a promise: capacity, resource conflicts and
   external waits stay visible in the report next to the graph.

## Checking it

The offline checker validates declared path and dependency conflicts:

```sh
python3 scripts/lhc_validate_graph.py <plan.graph.json>
```

It checks only declared paths and dependencies. It does not run a scheduler and
does not judge whether two leaves are conceptually independent.
