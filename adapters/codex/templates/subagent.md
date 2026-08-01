# Codex subagent instructions template

Before every `spawn_agent` call:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Set `fork_context: false`. Never fork the parent conversation history.
- Always pass required context explicitly in a compact Task Card: role, goal, known
  facts, allowed and excluded paths, acceptance check, stop conditions, and
  report format. For Overseer or Critic, include the raw user context required
  by their role without copying L's desired verdict or interpretation.
- Use the read-only explorer class when it is sufficient; otherwise choose the
  cheapest available working class that can own the requested action.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.

If the active Codex surface cannot create a no-history child, do not create a
history-forked substitute. Report the unsupported boundary to the user.
