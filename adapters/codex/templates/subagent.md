# Codex subagent instructions template

Before every `spawn_agent` call:

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Set `fork_history: NEVER`. In the Codex call this means `fork_context: false`;
  never omit it or fork the parent conversation history.
- Before the call, write the complete assignment into one `todo-*.md`. Pass the
  child only `Read and execute <task-file-path>`. The file contains its role,
  goal, evidence, paths, acceptance, stop conditions, and report contract. The
  child appends its detailed result there and returns only TL;DR to L.
- Use the read-only explorer class when it is sufficient; otherwise choose the
  cheapest available working class that can own the requested action.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.

If the active Codex surface cannot create a no-history child, do not create a
history-forked substitute. Report the unsupported boundary to the user.
