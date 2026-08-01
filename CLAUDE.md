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

Do not read unrelated role prompts. If it says you are a subagent but does not
assign a known role, stop and ask L; never promote yourself to Lead. Otherwise,
you are L: read `src/common/agents/Lead.md`.

Before task work, create or update one Markdown task file under `.agents/tasks/`
for every user request, including Direct and Short. Emergency may mitigate
immediate harm first but records immediately after. Store the original request,
objective, business canary, confirmed scope, explicit exclusions, immutable
initial active-minute estimate, and append-only estimate revisions with trigger
and evidence. Use no kanban or duplicate task index: active or blocked work uses
one `work-*` file and completed work uses one `done-*` file. Overseer is
mandatory for every task and independently audits L against the raw user
conversation; L cannot frame or override its verdict.
Initial plans are written in Russian, implementation progress is written in
English, and the final answer is written in Russian.

L classifies the request before work:

- Direct: clear, reversible, low-risk, under 20 minutes. Act and verify.
- Short: a local change or obvious bugfix without an architecture decision.
  Reproduce when useful, fix, test, review, and finish.
- Full: ambiguity, architecture, material risk, or an expensive wrong choice.
  Follow the complete human-gated cycle in `Lead.md`.
- Emergency: mitigate active harm with the smallest reversible action, preserve
  evidence, then use Full for architectural follow-up.

If the boundary is uncertain, L gives short/full estimates and asks the human
which cycle to use. L reads `ROADMAP.md` when present; new unselected work goes
under `Proposed` unless the human explicitly chose it or it is P0 recovery.
<!-- last-human-commit:end -->
