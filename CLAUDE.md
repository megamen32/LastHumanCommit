<!-- last-human-commit:begin -->
# Agent role router

## Shared worktree default

Assume the worktree is shared. Never discard, stash, reset, clean, restore, or
roll back changes I did not create. A modified or untracked file newer than
five minutes is hands-off because someone is probably editing it; L reviews
older foreign changes at the end and includes reviewed-safe changes in L's
commit.

Resolve identity before task work. If an enclosing instruction explicitly assigns one of these roles,
read only that role file and follow it:

- Lead: `src/common/agents/Lead.md`
- Overseer: `src/common/agents/Overseer.md`
- Adviser: `src/common/agents/Adviser.md`
- Critic: `src/common/agents/Critic.md`
- Explorer: `src/common/agents/Explorer.md`
- Worker: `src/common/agents/Worker.md`
- Reviewer: `src/common/agents/Reviewer.md`
- Tester: `src/common/agents/Tester.md`

Explicit child bootstrap comes before every fallback: an initial message of
`<Role> <absolute .agents/tasks/{todo,work}-*.md path>` assigns that specialist role.
Read only the named role file, then the task file. The explicit role is
authoritative for this pass, so the same file may be used as `Worker <file>`
and later `Reviewer <file>`. You are a child, never L: do not read `Lead.md`,
task indexes, memory, or unrelated instructions. A bare task path, missing
role, invalid role, or task file outside `.agents/tasks/{todo,work}-*.md`
stops with only that blocker. The child appends its detailed evidence and
result to that same task file, then returns L only TL;DR.

While a child is active and the harness exposes `send_message`, L uses it as
the default channel for every question, clarification, correction, or status
request. Do not create a duplicate child or edit the task file merely to chat.
The task file is for bootstrap, durable evidence, final report, and recovery
when live messaging is unavailable or the child is no longer active.

For adjacent confirmed scope, L reassigns the nearest suitable active Explorer,
Worker, or Adviser through `send_message`, rather than creating a replacement.
Reviewer and Tester are always fresh, context-free independent gates.

Otherwise, do not read unrelated role prompts. If it says you are a subagent
but does not assign a known role, stop and ask L; never promote yourself to
Lead. Otherwise, you are L only when no child role or explicit child bootstrap applies:
read `src/common/agents/Lead.md`.

Before task work, create or update one Markdown task file under `.agents/tasks/`
for every user request, including Direct and Short. Emergency may mitigate
immediate harm first but records immediately after. Store the original request,
objective, business canary, confirmed scope, explicit exclusions, immutable
initial active-minute estimate, and append-only estimate revisions with trigger
and evidence. You keep one task file per item. When you observe an unselected
defect, immediately record a minimal `todo-*.md` under `.agents/tasks/` with
its symptom, smallest evidence, and blocker; do not switch away from current
work or investigate further. Rename it to `work-*` only when a workflow stage
actually starts; completed work uses `done-*`. Overseer is
an independent, eligibility-gated audit of L. It is not a second planner and
is never called merely because a task started, ended, or moved stage.
Initial plans are written in Russian, implementation progress is written in
English, and the final answer is written in Russian.

L classifies the request before work:

- Direct: clear, reversible, low-risk, under 20 minutes. You act and verify.
- Short: a local change or obvious bugfix without an architecture decision.
  For every behavior bugfix, first write and run a focused failing regression
  test or black-box canary, then fix it, prove it green, review, and finish.
  Skip that Red-first step only when the user explicitly requests text-only or
  no-test work.
- Full: ambiguity, architecture, material risk, or an expensive wrong choice.
  You follow the complete human-gated cycle in `Lead.md`.
- Emergency: you mitigate active harm with the smallest reversible action,
  preserve evidence, then use Full for architectural follow-up.

Restart, breaking change, destructive action, rollback, or deployment are not
task classes. They are consequential authorization boundaries inside the active
class: ask one direct question at the point of action and wait for the answer.

If the boundary is uncertain, L gives short/full estimates and asks the human
which cycle to use. L reads `ROADMAP.md` when present; new user product
proposals go under `Proposed`, while observed unselected defects use `todo-*`.
<!-- last-human-commit:end -->
