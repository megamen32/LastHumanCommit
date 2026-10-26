> Background reference. Load only when the task needs this mechanism. `AGENTS.md` wins on any conflict: its finish line, blocker lists, escalation chain and delivery rules override this file.

# Durable task and worker records

The task record is the durable source of the assignment, current plan and Lead
decisions. Use the owning project's `.agents/tasks/<task-id>/` directory, even
when the native session started elsewhere. Do not create a competing workflow,
tracker or parallel task directory.

## Canonical files and owners

| Path | Writer | Purpose |
| --- | --- | --- |
| `task.md` | Lead owns decisions; Lead or one assigned Artifact Writer writes | Original user intent/corrections, accepted result and current `## Plan`. |
| `progress.md` | Lead owns decisions; Lead or one assigned Artifact Writer writes | Stable chronology, actual work, decisions, blockers, evidence links and next action. |
| `plan.graph.json`, `plan.html`, `plan.md` | Lead or one assigned Artifact Writer/tool | Derived task graph and readable views of the same plan revision. |
| `briefs/<leaf-id>.md` | Lead | The exact current worker assignment and its authority/scope. |
| `records/<leaf-id>/progress.md` | Assigned worker | Worker-owned checkpoints, observations, question/decision needed, and next action. |
| `records/<leaf-id>/result.md` | Assigned worker | Final result and verifiable handoff receipt. |

The Lead owns user intent, selected mode, plan decisions, status decisions,
dependencies, ownership and acceptance criteria. The Lead may assign one named
`Artifact Writer` exclusive write ownership for `task.md`, task-level
`progress.md`, graph, HTML and Markdown. That writer records the Lead's verified
decisions; it cannot choose the mode, reinterpret user intent, change acceptance,
infer a status, assign work, or claim parent acceptance. No other worker edits
those plan files while the Artifact Writer owns them. The Lead receives and
reviews its result and retains final integration and consumer-acceptance decisions.
Execution Workers write only their own `records/<leaf-id>/progress.md` and
`result.md`; they do not mark another leaf complete. For a small task, one
Artifact Writer may create a minimal plan before implementation, without a
separate approval or ceremony.

## Brief fields

Every `briefs/<leaf-id>.md` contains:

```text
task_id:
leaf_id:
owner/session:
parent_lead_identity:
parent_task_id/session/route:
role: artifact_writer | execution_worker | tester | research_worker
mode: quickfix | fullcycle | testing | research
user_outcome:
task_title:
description: <include the user benefit in the ordinary-language explanation>
acceptance:
dependencies:
read_paths:
write_paths:
affected_files:
excluded_scope:
estimate_minutes: {minimum, maximum}
estimate_basis/uncertainty:
next_action:
verified_lead_decisions:
exclusive_plan_write_paths: []
artifact_writer_acceptance:
  user_language:
  semantic_completeness:
  readable_artifacts:
```

The brief describes the assigned slice in ordinary user language and preserves
the complete input, not a short machine-oriented summary. `affected_files` is
about products/paths touched; `read_paths` and `write_paths` grant the worker's
exact source ownership. A leaf assignment is created and scoped by the Lead. It
does not ask the worker to reconstruct the parent goal, re-plan, change the mode,
or recursively recruit another agent. The Lead records the selected mode after
research and owns the required plan in both quickfix and fullcycle.

For an `Artifact Writer`, the brief also names its exclusive write set and the
exact Lead-decided text/status/ownership/acceptance that may be recorded. The
writer must not infer or introduce a plan decision. The parent task/session/route
must be explicit in both the brief and receipt so a result returns to the right
Lead. Its brief MUST forward this acceptance to the writer: human-facing plan
fields and rendered views use the user's language (Russian when the user uses
Russian); descriptions explain the complete meaning without dropping user benefit,
input, action, visible outcome, or important limits; HTML and Markdown are
readable and preserve the distinct fields. Lead acceptance includes reviewing
those readable artifacts.

Worker-to-worker and parent-route wording may be concise Russian or English.
There is no global human-readability or zero-context constraint on internal
routing. Workers receive the context needed for their role; do not impose a
blanket no-context rule. Use fresh context only for an independent blind reader
when the accepted review requires it.

## Progress and result fields

`progress.md` is append-only by dated entries; do not replace earlier evidence.
Each update includes `status` (`queued`, `running`, `blocked`, `done`,
`deferred`), owner, observed business delta, completed step, actual active time
and its source (or `not measured`), decisions with the evidence/source that
authorized them, blocker/decision-needed if any, and one next action.
No timer, start notice or agent message is itself progress evidence.

The assigned worker completes `result.md` using this stable receipt shape:

```text
status: done | blocked | deferred
owner:
parent_lead_identity:
parent_task_id/session/route:
read_paths: []
write_paths: []
acceptance:
changes:
tests: []
decisions: []
receipts: []
artifacts_written: []
blockers: []
commit: <hash or none>
next_action:
```

List exact commands and outcomes, or file paths and hashes for artifact-only
evidence. Preserve failures and unsupported claims. A worker receipt closes only
its assigned leaf; it does not prove publication, installation, runtime state,
or consumer acceptance unless that exact action and evidence were in its brief.

## Decisions, blockers and communication

The Lead records decisions in `progress.md` with the source that authorized the
choice and the affected plan fields. A Worker records a needed decision under
`decision_needed` in its progress file, gives evidence, recommended choice,
proposed default, and the exact action that waits. A blocker names the cause,
owner, impact, evidence and smallest next action. Unknown or external waits remain
explicit; do not turn them into a completed status or a guessed estimate.

Workers keep detailed progress, tests, results and receipts in their files. Chat
is reserved for an actual decision needed from Lead, a blocker that changes the
route, or a concise readiness notice that points to `result.md`. The Lead checks
the file receipt against the brief and source before changing plan status. Do not
repeat unchanged status in chat.

## Handoff and recovery

Before dispatch, Lead writes and checks the brief, declares exclusive paths and
dependencies, names the canonical parent task/session/route, and provides the
canonical task directory. An Artifact Writer gets only the plan write paths and
verified decisions listed in its brief. It writes the initial plan before any
implementation and may record status changes only after the Lead verifies the
underlying receipt and supplies the new status decision. Before handoff, the
writer updates its result receipt with the exact plan artifacts/revision and
returns their paths to that parent Lead. Execution Workers update only their own
progress/result files. The Lead reads the files (using context-mode for compact
extraction when helpful), checks the handoff, and retains final integration and
consumer-acceptance decisions.

For a plan edit, refresh graph → HTML/Markdown → `check-plan` from the same
revision. Keep one Artifact Writer as the exclusive writer through the handoff;
the Lead may resume file ownership explicitly after it has received and reviewed
the artifacts.

After compaction or session recovery, the Lead reads `progress.md` first, then
`task.md`, the graph/report, and only the active workers' referenced progress and
result files. It verifies live source and receipts before resuming. A Worker reads
its brief and own progress file before continuing. Chat history and memory are
helpful pointers, not the authority or the only copy of task state. Never store
credential values, personal session data or unrelated project records here.
