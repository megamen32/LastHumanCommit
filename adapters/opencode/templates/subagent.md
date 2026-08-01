# OpenCode subagent instructions template

Before every delegated task:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Start a fresh child context through the native agent profile and give it one
  compact Task Card with the role, goal, evidence, scope, acceptance check, stop
  conditions, and report format.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.
