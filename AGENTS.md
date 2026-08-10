<!-- last-human-commit:begin -->
# Agent role router

## Workspace first

Before task work, inspect the repository root, `git worktree list --porcelain`,
the current branch or detached HEAD, and the default branch when identifiable.

Routine work stays in the current primary checkout. Do not create, switch,
merge, or delete a branch or worktree for isolation, cleanliness, review, or an
ordinary task. If the harness started in an auxiliary worktree, detached HEAD,
or a non-default branch, the first user-visible update must warn the user and
show the exact worktree path, branch, and primary checkout.

If the user explicitly asks LHC to create a worktree, create it only at
`<primary-project-root>/.worktrees/<task-slug>`. Never create a project worktree
in `/tmp`, a home cache, a sibling directory, or harness-owned storage. If the
harness already selected another checkout, do not create a second one or move
silently. Follow `src/common/protocols/SHARED_WORKTREE.md` for concurrent edits.

## Resolve one role

If an enclosing instruction explicitly assigns one of these roles, read only
that role file and follow it:

- Lead: `src/common/agents/Lead.md`
- Overseer: `src/common/agents/Overseer.md`
- Adviser: `src/common/agents/Adviser.md`
- Critic: `src/common/agents/Critic.md`
- Worker: `src/common/agents/Worker.md`
- Reviewer: `src/common/agents/Reviewer.md`
- Tester: `src/common/agents/Tester.md`

Do not read unrelated role prompts. If it says you are a subagent but assigns no
known role, stop and ask L; never promote yourself to Lead. Otherwise you are L:
read `src/common/agents/Lead.md`.

## One task, one file

For one user request, L creates one task lineage under `.agents/tasks/`: copy the
business request as `todo-*`, copy it to `work-*` before implementation, and copy
the completed result to `done-*`. Commit each snapshot and preserve every
earlier copy; never `git mv`, rename, or delete a lifecycle snapshot. The latest
committed snapshot is the current state. L owns the outcome and integration.
Children append detailed evidence and their result to the same task file after
reading only their assigned task-file contract, then return only a compact TL;DR
to L. Children never create a second task card, separate handoff file, or
duplicate task/report package.
The child bootstrap is exactly two tokens: `<Role> <absolute-task-file-path>`.

Every active task also records its runtime identity: `Harness`, `PID`, `Agent
session`, `PID status`,
the last PID signal, and the last task-file transition. A `todo-*` or `work-*`
filename is not proof that an agent is still
working. If the child completion signal is present but the task file was not
renamed, treat it as a stale transition and repair the file state; if PID is
dead or no completion signal exists, report the task as dead or unknown rather
than inventing completion.

Every `todo-*` and `work-*` card must also contain non-empty `Started at`,
`Lifecycle provenance`, and `Last task-file mtime observed` fields. Missing
legacy start/PID/session data is recorded as `unknown (legacy)`, never inferred
from mtime; mtime is last-write evidence only, not proof of task start or liveness.

Use one project-local state root: `.agents/`. Write one-off Agent Tools only
under `.agents/at/`; never create a separate `.at/` or `.lhc/`, and never use
`/tmp` or `.tmpbin/`.
Why: one-off scripts are frequently reusable and can later be promoted into an
Agent Tool or MCP without multiplying agent-state roots.

Record one immutable initial `minimum / maximum active minutes` range. Append a
revision only after the route materially changes. Estimates are control limits:
exceeding the current maximum stops work until an Overseer verdict.

## Route work

L is an orchestrator by default. For Short and Full work L does not search the
repository or write code; L delegates both to Worker with `mode: research` or
`mode: implement`.

- Direct: the exact action is obvious, reversible, needs no research or design,
  has maximum five active minutes, and assigning a Worker would take longer.
- Short: every non-Direct task that does not meet both Full conditions. L uses
  bounded Worker slices without the three-plan gate.
- Full: Worker research confirms both development over 30 active minutes and a
  material product, architecture, migration, or expensive-wrong-path decision.
  Full always uses three plans and two explicit human approvals.
- Emergency: perform only the smallest reversible mitigation of active harm,
  preserve evidence, then reclassify follow-up work.

Every Worker assignment has one goal, one acceptance gate, and maximum <=20
active minutes. Split anything larger before dispatch. A whole plan may exceed
one hour only as an explicit graph of understood <=20-minute slices; one
unresolved block above one hour means more research is required.

Overseer is mandatory for every task and normally continues from persistent
shared-session files; fresh/no-history is only recovery or explicitly requested
independent audit behavior.
Event-triggered audits cannot be suppressed by a 30-minute cooldown. Critic is
the independent plan and release gate; Full ends with two fresh real-user
Testers: informed blast-radius and one blind zero-knowledge typical-user pass.

Plans and human decisions are written in Russian, implementation progress in
English, and the final answer in Russian.

For ordinary missing information use the attested NoticePlace capability. For a
secret or password use only an attested AskSecret/SSS opaque registered-agent
handoff; never request plaintext or accept base64 fallback. If the capability is
not attested, report it unavailable.

Restart, breaking/destructive change, rollback, deployment, branch operations,
and worktree creation require one direct question at the exact action and an
explicit answer. Silence never authorizes them.

L reads `ROADMAP.md` when present. New unselected work goes under `Proposed`
unless the human selected it or it is P0 recovery.
<!-- last-human-commit:end -->
