# Claude Code subagent instructions template

Before every delegated task:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Send one compact assignment in the child prompt: role, Worker mode when
  applicable, root task path as read-only context, goal, decisive evidence,
  allowed/excluded paths, one acceptance check, minimum/maximum with maximum
  <=20, stop conditions, and compact return format.
- Do not create a child `todo-*`, Task Card, report, ledger, or spec file. The
  child returns evidence to L; only L writes the root task file.
- Use a fresh agent for initial Worker research. Resume the same Worker for its
  selected implementation lane when supported; otherwise pass the compact
  Research section to a fresh Worker.
- Overseer and Critic are always fresh no-history agents with raw user context
  and no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
