# LHC shared session: file-first abstraction

This is an abstraction, not an installed MCP, daemon, scheduler, or Agent
Plugin implementation. A future adapter may expose these operations as an LHC
mini-tool, but the files remain the durable source of truth when an MCP or hook
fails.

Use one project-local state root: `<working-directory>/.agents/`. Do not create
separate top-level `.lhc/`, `.at/`, or other agent-state roots; all LHC state and
Agent Tools are subdirectories of `.agents/`.

## Source of truth per working directory

The canonical root is:

```text
<working-directory>/.agents/shared-session/
```

The directory must contain a short `README.md` describing these paths so an
agent can recover without the MCP:

```text
.agents/shared-session/
├── README.md
├── session.json                 # current directory/session registry
├── tasks/                       # optional registry; canonical task is .agents/tasks/
├── workers/<session-id>.json    # harness, pid, cwd, status, task id
├── files/<session-id>.json      # declared active files and last observation
├── messages/user.md             # user messages, append-only in task scope
├── search/<task-id>/            # ignored search journal
│   └── search-<task-slug>.md
├── results/<task-id>/           # tracked final result
│   └── result-<result-slug>.md
├── overseer/context.md          # persistent Overseer working context
├── overseer/state.md            # current canary, blockers, time, last verdict
└── events/<UTC>-<event>.json    # append-only lifecycle receipts
```

The MCP is a convenience index and writer. It must never be the only copy of a
task, task-file handoff, research result, user message, or Overseer receipt.
The canonical task snapshot remains `.agents/tasks/{todo,work,done}-*.md`;
`shared-session/tasks/` is not a second task-card store.

## Minimal operations

The future LHC tool may expose these names; the file contract is normative:

| Operation | Required behavior |
| --- | --- |
| `session_start` | Register harness/session/cwd/pid, create or update worker record, and append a start event. |
| `session_stop` | Mark the worker stopped, append a stop event, and leave all task/research files intact. |
| `session_heartbeat` | Refresh liveness and declared active-file observation; it is not proof of task completion. |
| `workers_list` | List parallel workers for this directory, their task/status, declared active files, and files observed changed in the last 10 minutes. |
| `task_create` | Create one task file with `Status: todo` or `Status: in progress`; return its path and id. |
| `task_update` | Update the same task file append-only where possible; status transitions include `todo → in progress → complete/blocked`. |
| `research_record` | After the first 3 active minutes, write named search and result files in their separate trees; return only a compact TL;DR/link in chat. |
| `send_parent` | Append the handoff to the assigned `.agents/tasks/{todo,work}-*.md` file; a live parent transport is optional and must not be claimed unless attested. Never create a separate handoff file. |
| `overseer_continue` | Continue the persistent Overseer context by reading `messages/user.md`, the task, `overseer/context.md`, and `overseer/state.md`; no full history argument is required. |

`workers_list` uses two different signals and labels them: declared active
files are claims from the task/worker record; “changed in last 10 minutes” is a
filesystem mtime observation only. Neither signal alone proves that a worker
is alive or owns a file.

## Lifecycle hooks

Adapters should map their native lifecycle to these semantic events:

1. `session_start` — register the session before the first task action.
2. `task_create` — create `todo` before work is selected; transition to
   `in_progress` when the worker actually starts.
3. `task_update` — append progress, worker/file claims, blockers, and handoffs.
4. `response_stop` — after every harness response finishes, inspect the task
   status and the final assistant message.
5. `session_stop` — close the worker registration without deleting evidence.

For an adapter with lifecycle hooks, count monotonic elapsed time from
`session_start` and inject `overseer_continue` at each 30-minute boundary.
This is an additional trigger, never a cooldown. For an adapter without hooks,
the template must expose the capability gap literally:
`<cap-off:hooks>каждые 30 минут </cap-off:hooks>`.

The `response_stop` hook is the human-question guard. If the response appears
to wait for a human answer and the task is not `complete`, it must invoke the
registered human-request capability with:

```text
Harness: <harness>
Task: <task path/id>
State: waiting for human; task is not complete
Last message: <verbatim final assistant message>
```

It must not merely print a question into the transcript and assume that a
human was notified. If the human-request capability is unavailable, record an
explicit `STOP_MISSING_CONTEXT`/capability failure in the task/event file.

## Durable research and parent handoff

The first 3 active minutes are reserved for basic orientation. At that point,
create two separate persistent files:

```text
.agents/shared-session/search/<task-id>/search-<task-slug>.md
.agents/shared-session/results/<task-id>/result-<result-slug>.md
```

`search-<task-slug>.md` is an append-only journal of how the Worker searched: queries,
paths, commands, probes, rejected routes, and repeated-path hints. It is
physically Git-ignored by the shared-session search-tree rule, but remains
available for later bulk analysis and deduplication.

`result-<result-slug>.md` is the separate current final result. The Worker may rewrite it as
evidence changes; it contains the answer, decisive evidence, unknowns,
blockers, and business-canary implication. Chat carries only a compact TL;DR
and the two paths. The assigned task file must record the exact `Result file:`
path; a result whose name exists only in chat is invalid.

If active research exceeds 10 minutes, `result-<result-slug>.md` becomes mandatory evidence:
it may not be ignored, omitted, or left only in chat, and the completed change
must include a Git commit. A task is not complete until that commit is recorded.

A dead or disconnected harness therefore leaves recoverable evidence without
forcing Lead to load the whole child session.
`send_parent` appends a dated `## Parent handoff` entry to the same task file,
including the child, status, blockers, next action, and exact result path. There
is no handoff artifact to reconcile. A live Agent Herder/parent delivery is an
optional transport of that same entry, never its source of truth.

## Agent Tools scratch rule

One-off scripts are forbidden in `/tmp`, `.tmpbin/`, and other temporary
locations. They must be written under `<working-directory>/.agents/at/`. The directory
is intentionally durable because one-off scripts frequently become reusable
Agent Tools and can later be promoted into an MCP. This is a workflow rule, not
an invitation to add unrelated tooling.

## Persistent Overseer

Overseer is a continuing auditor for the task/session, not a disposable child
that receives the entire conversation on every invocation. User messages are
appended verbatim to `messages/user.md` in task scope. The Overseer reads the
persistent files, updates `overseer/state.md`, and appends a short receipt to
the task file.

It answers from the durable state:

- where the business canary currently is;
- what was completed since the last audit;
- current blockers and remaining time;
- whether the route is closer, unchanged, or farther from the result;
- one minimum next action or a direct human question.

Continuation is preferred. A fresh Overseer context is only a recovery path
when the persistent state is missing/corrupt, the user explicitly asks for an
independent audit, or a separate gate requires no-history behavior. The
Overseer verdict remains binding on Lead.

## Failure behavior

If the MCP, hook, parent transport, or Agent Plugin adapter fails, agents use
the documented files directly and record the failure. No task is considered
complete merely because a tool call returned success; completion requires the
same task file to be changed to `complete` and the business result to be
evidenced.
