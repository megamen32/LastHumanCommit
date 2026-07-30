# Agent role router

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
