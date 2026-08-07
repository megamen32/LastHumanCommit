# Claude Code subagent instructions template

Before every delegated task:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Give the child one compact assignment: role, Worker mode when applicable,
  goal, decisive evidence, allowed/excluded paths, one acceptance check,
  minimum/maximum estimate with maximum <=20, stop conditions, and report
  format.
- Use a fresh agent for initial Worker research. Resume the same Worker for its
  selected implementation lane when the active Claude surface supports it;
  otherwise pass the compact task-file research to a fresh Worker.
- Overseer and Critic are always fresh no-history agents with raw user
  request/corrections passed explicitly and no desired verdict from L.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
