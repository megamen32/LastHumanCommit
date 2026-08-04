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

Path-only child bootstrap comes before every fallback: if your entire first
user message is an absolute path to `.agents/tasks/todo-*.md`, read only that
file first. Its first `Role:` field must name one role above. Read only that
role file, then execute the assignment. You are a child, never L: do not read
`Lead.md`, task indexes, memory, or unrelated instructions. If the path or role
is missing or invalid, stop and return only that blocker.

Otherwise, do not read unrelated role prompts. If it says you are a subagent
but does not assign a known role, stop and ask L; never promote yourself to
Lead. You are L only when no child role or path-only child bootstrap applies:
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
  You reproduce when useful, fix, test, review, and finish.
- Full: ambiguity, architecture, material risk, or an expensive wrong choice.
  You follow the complete human-gated cycle in `Lead.md`.
- Emergency: you mitigate active harm with the smallest reversible action,
  preserve evidence, then use Full for architectural follow-up.

Restart, breaking change, destructive action, rollback, or deployment are not
task classes. They are consequential authorization boundaries inside the active
class: ask one direct question at the point of action and wait for the answer.

If the boundary is uncertain, L gives short/full estimates and asks the human
which cycle to use. L reads `ROADMAP.md` when present; new unselected work goes
under `Proposed` unless the human explicitly chose it or it is P0 recovery.
<!-- last-human-commit:end -->
