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
      "model": "frontier",
      "blocker": "",
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
- `actual_minutes` is measured active time. If it was not measured, leave it out
  instead of inventing a number.
- `owner`, `session`, `harness` and `model` say who works on the leaf now. The
  dashboard shows them so the user can see which session owns what.
- `blocker` names the concrete external obstacle. `waiting` is not a blocker: a
  leaf waiting for a dependency is `queued`.
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
