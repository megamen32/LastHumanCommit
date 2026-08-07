# Hermes subagent instructions template

Before every delegated goal:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Prefix the goal with `[LHC_ROLE=<role>]` and send one compact assignment:
  Worker mode when applicable, goal, decisive evidence, allowed/excluded paths,
  one acceptance check, minimum/maximum estimate with maximum <=20, stop
  conditions, and report format.
- Resume the same Worker from research into its selected implementation lane
  when Hermes exposes a proven resume path; otherwise pass the compact task-file
  research to a fresh Worker.
- Overseer and Critic are always fresh delegated contexts with raw user
  request/corrections and no desired verdict from L.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
