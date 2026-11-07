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

## Explicit assignment and Herder execution

A durable brief and a registered worktree describe the work. The explicit
`leaf.assignment` describes the current attempt and separates the Lead, executor,
native parent, dispatch receipt, observed runtime and continuation wait. Use the
LhcPlan operations; do not add these fields by editing JSON. The assignment is a
record, not a new approval layer. Authorship is attributed from native caller
metadata when available; `--actor` is declared attribution and never proves a
native identity or authority.

| MCP operation | CLI subcommand of `lhc_plan_json.py` | Effect |
| --- | --- | --- |
| `assign_leaf` | `assign-leaf PLAN LEAF --assignment JSON` | Record one explicit attempt and preserve previous attempts. |
| `dispatch_leaf` | `dispatch-leaf PLAN LEAF --attempt-id ID --message TEXT` | Refresh availability, atomically admit a ready assignment, deliver through Herder and arm its exact completion wake. |
| `reconcile_leaf` | `reconcile-leaf PLAN LEAF --attempt-id ID` | Read native state and the exact saved wait without sending another task. |
| `accept_leaf` | `accept-leaf PLAN LEAF --attempt-id ID --result TEXT` | Record Lead acceptance and the proven leaf result. |

These operations accept `expected_hash` in MCP or `--expected-hash` in CLI for
compare-and-swap. They use the same canonical persistence path. An attempt ID is
stable for this assignment and is not replaced to retry an uncertain effect.
Before a new external dispatch, `briefs/<leaf-id>.md` must contain explicit
`task_id`, `leaf_id`, `owner/session`, `parent_lead_identity`,
`parent_task_id/session/route`, `role`, `mode`, `description`, `acceptance`,
`read_paths`, `write_paths`, `excluded_scope` and `next_action` fields.
`task_id` is the canonical plan directory's name, not a second metadata ID.
Owner and Lead identities must match the assignment; the return route names that
same task and Lead session. `acceptance` states `output`, `destination`, and
`checks`. A reader/tester may explicitly use `write_paths: []`; execution and
artifact writers require a write scope. `read_paths: []` requires supplied `input`.
Artifact writers also require `exclusive_plan_write_paths` and
`artifact_writer_acceptance` as described above. These are structural records,
not an automated judgment of prose quality or an instruction to copy unrelated
chat history. Use a JSON object or the explicit field format above, without
repeating keys, including keys in nested JSON objects.

The gate reads a regular UTF-8 file through the canonical plan and its real
`briefs` directory. Directory/file symlinks and non-regular inputs are refused;
FIFO input cannot block admission. The brief limit is 128 KiB and the delivered
payload limit is 256 KiB; an oversized input is refused with its byte limit and
is never silently truncated.

Under the existing admission lock/CAS, the gate saves the exact brief, leaf hash,
caller input and composed message in an immutable private attempt receipt at
`records/<leaf-id>/attempts/<sha256(attempt-id)>/handoff.json`. The file uses mode
0600, new directories use 0700, and an attempt-local 0600 `.gitignore` containing
`*` excludes the private receipt from ordinary Git adds even outside `.agents`.
This does not change repository-level ignores or protect an explicit forced add.
Public assignment/graph state retains only the immutable identity, hashes and
receipt path. CLI/MCP error argv hides `--message`. The saved intent is flushed
before external I/O. A changed brief after admission cannot change the delivered
snapshot; an existing conflicting snapshot fails closed. Reconciliation reads the
saved attempt and does not send it again. Self work retains its verified local
identity path and sends nothing.

The required task message is scoped by the brief; it is not reconstructed from
unrelated chat history. For example, with the real explicit refs already checked:

```sh
python3 "$LHC_TOOLS/lhc_plan_json.py" assign-leaf "$PLAN" L04 \
  --assignment "$ASSIGNMENT_JSON"
python3 "$LHC_TOOLS/lhc_plan_json.py" dispatch-leaf "$PLAN" L04 \
  --attempt-id "$ATTEMPT_ID" --message "$SCOPED_TASK"
```

`ASSIGNMENT_JSON` has this shape. Replace the example values with real refs;
this sample is not a target to send to:

```json
{
  "schema_version": 1,
  "attempt_id": "task-L04-attempt-1",
  "executor_kind": "session",
  "lead": {"host_id": "exact-host", "harness": "codex", "session_id": "exact-lead"},
  "executor": {"host_id": "exact-host", "harness": "codex", "session_id": "exact-worker"},
  "parent": null,
  "state": "assigned"
}
```

For a `subagent`, record its distinct parent ref and verified relation; the Lead
and native parent need not be the same session. A `self` assignment records local
work and sends nothing to itself. The initial bridge supports existing local
sessions on one Herder singleton. A cross-host join and an unsupported native
source harness return an explicit blocked reason. Do not route around the reason
by dropping source attribution or choosing a different owner.

### What the saved states prove

`assigned` means assignment, not acceptance by the native session. `dispatching`
is a durable intent saved before RPC. `submitted` means a correlated admission
receipt was returned. `running` needs fresh observation of the same exact native
turn. `result_ready` means that turn reached a terminal native outcome; a failed
or stopped turn may produce a result to inspect. `accepted` records the Lead's
separate acceptance and changes the leaf to done. Saved leaf status and observed
runtime are displayed separately.

The canonical dispatch path uses the unified evaluator for prerequisites,
capacity and executor availability. It admits the assignment under the same
plan lock that saves its dispatch intent, so two leaves cannot both reserve one
session or the last slot. A dependency candidate is not proof of dispatchability.
Only done satisfies a dependency; deferred does not. Missing runtime evidence is
unknown, and blocked intake, quota and human Stop retain their reasons.

The dispatch response also contains `wake`. A valid wait belongs to the Lead and
captures the admitted executor turn, with its exact wait ID, observed time and
state. The continuation message includes the canonical plan directory, leaf and
attempt. After completion the existing Herder service wakes the Lead once.
That wake is a trigger to reread the latest user goal and current readiness,
inspect and integrate the result, perform acceptance, then choose the next
available work. It does not authorize replaying the old task message or accepting
whatever an idle session last said. Independent work does not wait for an
unrelated wave.

A missing, rejected or ambiguous continuation is visible in `wake.state` and
`wake.reason`. Use `reconcile_leaf` for a read-only check. An uncertain registration
is queried by the deterministic wait ID of the existing Herder request; it is
never resubmitted to create another timer. A status receipt must match the wait,
Lead, executor and captured turn before it can update this assignment. A quota
or permission refusal stays blocked. An UNKNOWN delivery is never automatically
replayed, even after restart or compaction.

### Adopting a legacy plan

Existing plans remain readable. A legacy owner label or `leaf.session` is a
historical hint, not proof of an executor, host, model, parent or running turn.
Inspect the existing result and native readback first. Record an explicit new
assignment only for the remaining authorized work, preserving earlier events
and unknown provenance. Do not retroactively invent a native start, mark deferred
requirements accepted, or reset an uncertain previous dispatch. Local legacy
self-work keeps its existing activate/saved-status workflow.

For a registered worker use `worker_finish` for integration and cleanup before
the leaf closes. For another explicit assignment use `accept_leaf` after the
required checks. Both are separate from native completion. The public page must
retain the distinction among source evidence, native evidence and installed
consumer acceptance.

Isolated setup for fresh CLI/stdio consumers is in
`protocols/EXECUTION_CONSUMER.md`. It uses copied test data and a local fake Herder,
with no real native sessions, messages or model turns.


### Current goal and frontier

`activate PLAN LEAF` also binds the selected actual session/harness to its existing
native outcome through `lhc_plan_control.bind_session_plan`. Missing historical
native state remains an explicit unknown binding; reading or activating an old
plan does not create an outcome or migrate it into a second store.

Use `goal-control PLAN` (`read_goal_control` in MCP) to read current native
`goal_status`, `frontier`, `next_decision` and fingerprint. `show` and newly built
graphs include the same derived control. The graph's `goal_control` is a display
snapshot; always reread the live adapter before a decision. Finished cards and a
completed native turn do not prove acceptance of the current goal.

Use `goal-control PLAN --session ID --harness NAME --decision JSON`
(`record_frontier_decision` in MCP) for an explicit frontier decision. The adapter
verifies current Lead ownership, session-plan index and exact outcome binding
under the existing native state lock. MCP defaults to the request's native caller,
never the long-lived server's session. The decision records evidence, action,
owner and uncertainty; external waits also require a resume condition, and a
human stop requires an existing observed stop. It is not an automatic dispatch,
new scheduler, or authority to override STOP, quota or UNKNOWN/no-replay gates.
