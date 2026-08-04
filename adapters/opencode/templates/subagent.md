# OpenCode subagent instructions template

Before every delegated task:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Start a fresh child context through the native agent profile. Write one
  compact `todo-*.md` Task Card, invoke `<Role> <absolute-task-file-path>` with
  no parent history, require the child to append its detailed result there, and
  accept only TL;DR back to L.
- If OpenCode exposes a live child-message channel, use it for every question,
  correction, or status request; do not replace the active child or use the
  task file as chat.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.
