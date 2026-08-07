<!-- last-human-commit:begin -->
# Agent role router

## Workspace first

Before task work, inspect the current repository root, `git worktree list`,
current branch, and default branch when it can be identified.

Default to the primary project checkout. Do not create, switch, merge, or delete
a branch or worktree for routine isolation. If the current checkout is an
auxiliary worktree, detached HEAD, or a non-default branch, the first
user-visible update must warn the user and show the exact worktree path, branch,
and primary checkout. Do not hide this only in a task file.

If the user explicitly asks LHC to create a worktree, create it only below
`<primary-project-root>/.worktrees/<task-slug>`. Never create a project
worktree in `/tmp`, a home-level cache, a sibling directory, or harness-owned
storage. If the harness already placed the agent elsewhere, do not create a
second worktree or move silently; warn the user and continue in the selected
checkout. Follow `src/common/protocols/SHARED_WORKTREE.md` for concurrent edits.

## Resolve one role

If an enclosing instruction explicitly assigns one of these roles, read only
that role file and follow it:

- Lead: `src/common/agents/Lead.md`
- Overseer: `src/common/agents/Overseer.md`
- Adviser: `src/common/agents/Adviser.md`
- Critic: `src/common/agents/Critic.md`
- Worker: `src/common/agents/Worker.md`
- Reviewer: `src/common/agents/Reviewer.md`

Do not read unrelated role prompts. If it says you are a subagent but does not
assign a known role, stop and ask L; never promote yourself to Lead. Otherwise,
you are L: read `src/common/agents/Lead.md`.

## One task, one file

Before root task work, L creates or updates one Markdown file under
`.agents/tasks/`. Assigned subagents use that exact path and return evidence to
L; they never create another task record. The same file contains the request,
research, estimates, three plans when Full,
technical preview, approvals, execution, audits, and result. Never create a
second ledger, kanban, specification, or recovery file for the same task.
Active or blocked work uses one `work-*` file; completion renames that same file
to `done-*` with `Status: complete`.

Record an immutable initial `minimum / maximum active minutes` estimate and
append only material revisions with their trigger. Estimates are control limits,
not decorative reporting: exceeding the current maximum requires a fresh
Overseer audit before more work.

## Route work

L is an orchestrator by default. L does not search the repository or write code
for Short or Full work. L delegates both research and implementation to Worker
using `mode: research` or `mode: implement`.

- Direct: the exact action is obvious, reversible, needs no research or design,
  has a maximum estimate of five active minutes, and writing a Worker assignment
  would take longer than doing it. L may act directly and verify.
- Short: anything not Direct that is expected to finish within 30 active minutes
  or does not materially change the product. L orchestrates bounded Worker
  slices without the three-plan human gate.
- Full: research confirms both a development effort over 30 active minutes and
  a material product, architecture, migration, or expensive-wrong-path choice.
  Follow the complete two-approval human cycle in `Lead.md`.
- Emergency: mitigate active harm with the smallest reversible action, preserve
  evidence, then reclassify follow-up work.

Every Worker assignment has one acceptance gate and maximum <=20 active
minutes. Split anything larger before assignment. A whole plan may exceed
one hour only as an explicit graph of understood <=20-minute slices; one
unresolved block estimated above one hour means more research is required.

Overseer is mandatory for every task and is a fresh, no-history audit each time.
It receives the raw user request and the current task file, not L's desired
verdict. Critic independently gates release or another irreversible action.

Initial plans are written in Russian, implementation progress in English, and
the final answer in Russian.

Restart, breaking change, destructive action, rollback, deployment, branch
operations, and worktree creation are consequential authorization boundaries:
ask one direct question at the point of action and wait for an explicit answer.
Silence never authorizes them.

L reads `ROADMAP.md` when present. New unselected work goes under `Proposed`
unless the human explicitly selected it or it is P0 recovery.
<!-- last-human-commit:end -->
