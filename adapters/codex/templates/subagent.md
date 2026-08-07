# Codex subagent instructions template

Before every `spawn_agent` call:

Task Card

The assigned task file is the complete contract: read only that file after
loading the named role, append the detailed evidence and result there, and
return only its TL;DR to L. Never fork the parent conversation history.
pass required context explicitly through the task card, never through parent history.

- Select the lowest sufficient working model class for the assigned role and
  bounded acceptance check. Do not inherit L's model by default merely because
  it is the parent default.
- Set `fork_history: NEVER`. In the Codex call this means `fork_context: false`;
  never omit it or fork the parent conversation history.
- Before the call, write the complete assignment into one `todo-*.md`. Its
  top-level `Role:` must be one known specialist role. Pass exactly two tokens:
  `<Role> <absolute-task-file-path>`, with no other prose, parent context, or
  memory. The explicit role resolves before the Lead fallback and is
  authoritative for that pass; reuse the same file for Worker then Reviewer.
  The child appends its detailed result there and returns only TL;DR to L.
- When the child remains active, use Codex `send_message` for every live
  question, correction, or status request. Do not create a second child or use
  task-file edits as chat while that message channel works.
- For nearby confirmed scope, reassign the same active Explorer, Worker, or
  Adviser through `send_message`; Reviewer and Tester are always fresh,
  context-free gates.
- When an Explorer returns a bounded implementation in its owned scope, send
  that same active child exactly `Worker <same-absolute-task-file-path>`; do not
  spawn a duplicate Worker or repeat its research. Independent review still
  uses a separate Reviewer.
- Use the read-only explorer class when it is sufficient; otherwise choose the
  cheapest available working class that can own the requested action.
- Escalate only after `NEEDS_REDECOMPOSITION` or concrete acceptance evidence
  shows that the selected class cannot complete the bounded package.

If the active Codex surface cannot create a no-history child, do not create a
history-forked substitute. Report the unsupported boundary to the user.
