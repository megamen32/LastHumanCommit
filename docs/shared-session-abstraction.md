# LHC shared session: optional file-first durability

This is an abstraction, not an installed MCP, daemon, scheduler, or mandatory
workflow. Use it when coordination, recovery, handoff, reuse, or audit value
exceeds file-maintenance cost. The absence of shared-session files does not
block a simple business result.

Use one project-local state root: `<working-directory>/.agents/`. Do not create
parallel top-level `.lhc/` or `.at/` roots.

## Optional durable layout

```text
.agents/shared-session/
├── session.json
├── workers/<session-id>.json
├── files/<session-id>.json
├── messages/user.md
├── search/<task-id>/search-<task-slug>.md
├── results/<task-id>/result-<result-slug>.md
├── overseer/context.md
├── overseer/state.md
└── events/<UTC>-<event>.json
```

Keep only components that pay for themselves. A compact current task or result
is preferable to duplicate task cards, append-only execution histories, and
separate handoff/review packages.

## Operations

| Operation | Behavior when used |
| --- | --- |
| `session_start` | Register harness/session/cwd/pid without claiming business progress. |
| `session_stop` | Mark transport stopped while preserving useful evidence. |
| `session_heartbeat` | Refresh liveness observation; never prove completion. |
| `workers_list` | Show status, declared files, and filesystem observations separately. |
| `task_update` | Update one compact current state rather than multiplying snapshots. |
| `research_record` | Persist only when handoff/recovery/reuse/rediscovery economics justify it. |
| `send_parent` | Deliver the same compact checkpoint/result to L; do not duplicate it. |
| `overseer_continue` | Resume optional route audit when a concrete trigger justifies it. |

Filesystem mtime, missing completion signal, dead PID observation, timeout, and
mailbox wake are observations only. None independently proves agent completion,
death, ownership, or authorization to replace it.

## Worker control and join

Every 20 active minutes is a reporting checkpoint, not a Worker lifetime limit.
Record progress, business delta, blocker, route value, and the shortest next
action. L prefers continuing, redirecting, or resuming the same Worker and uses
Overseer only when independent route judgment is worth its cost. Cancellation
is exceptional.

Use the harness wait/join transport whenever a child result is required. A wait
window may expire without deciding lifecycle. Inspect authoritative status,
request/consume the checkpoint, take one control action, and join again if the
child remains required. Do not finish the parent response while a required
child is non-terminal.

## Cost-triggered research persistence

Persist research when handoff, recovery, reuse, or the cost of rediscovery
justifies it. The result file contains the decision-relevant answer, evidence,
unknowns, and canary implication. A search journal exists only when query/path
history has future value.

No elapsed-time threshold by itself requires a file or Git commit. Research may
remain a compact child return when that is the cheapest sufficiently durable
handoff. A commit is created only when requested or when the actual deliverable
requires one.

## Failure behavior

If an MCP, hook, parent transport, or adapter fails, use available files or chat
directly and report the capability gap. Tool success is not business success;
claim completion only from evidence matching the accepted outcome.
