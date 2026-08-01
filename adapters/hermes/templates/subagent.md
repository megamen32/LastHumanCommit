# Hermes subagent instructions template

Before every delegated goal:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Use Hermes' fresh delegated context and give it one compact Task Card with
  the `[LHC_ROLE=<role>]` prefix, goal, evidence, scope, acceptance check, stop
  conditions, and report format.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.
