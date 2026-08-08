# Hermes subagent instructions template

Before every delegated goal:

Bootstrap the child with exactly `<Role> <absolute-task-file-path>`.

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Prefix the goal with `[LHC_ROLE=<role>]` and send one compact assignment:
  Worker mode when applicable, root task path, goal,
  decisive evidence, allowed/excluded paths, one acceptance check,
  minimum/maximum with maximum <=20, stop conditions, and compact return format.
- The child reads only the assigned task file, appends detailed evidence and its
  result there, and returns only TL;DR to L. It never creates a second task
  card, report, ledger, or spec file.
- Resume the same Worker from research into its selected implementation lane
  when Hermes exposes a proven resume path; otherwise pass the compact Research
  section to a fresh Worker.
- Overseer and Critic are always fresh delegated contexts with raw user context
  and no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
