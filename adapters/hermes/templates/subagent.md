# Hermes subagent instructions template

Before every delegated goal:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Use Hermes' fresh delegated context. Write one compact `todo-*.md` Task Card;
  the delegated goal carries `[LHC_ROLE=<role>]` and its absolute task-file
  path. The child reads that file, appends its detailed result there, and
  returns only TL;DR to L.
- If Hermes exposes a live child-message channel, use it for every question,
  correction, or status request; do not replace the active child or use the
  task file as chat.
- For nearby confirmed scope, reassign the same active Explorer, Worker, or
  Adviser through its message channel; Reviewer and Tester are always fresh,
  context-free gates.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.
