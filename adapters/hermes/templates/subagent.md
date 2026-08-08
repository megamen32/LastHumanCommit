# Hermes subagent instructions template

Before every delegated goal:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Prefix the goal with `[LHC_ROLE=<role>]` and send one compact assignment:
  Worker mode when applicable, root task path as read-only context, goal,
  decisive evidence, allowed/excluded paths, one acceptance check,
  minimum/maximum with maximum <=20, stop conditions, and compact return format.
- Do not create a child `todo-*`, Task Card, report, ledger, or spec file. The
  child returns evidence to L; only L writes the root task file.
- Resume the same Worker from research into its selected implementation lane
  when Hermes exposes a proven resume path; otherwise pass the compact Research
  section to a fresh Worker.
- Overseer and Critic are always fresh delegated contexts with raw user context
  and no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
