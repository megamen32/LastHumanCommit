# Codex subagent instructions template

Before every `spawn_agent` or resumed Worker call:

- Select the lowest sufficient working model class. Do not inherit L's model by
  default.
- Every new child starts with `fork_context: false`. Never fork the parent
  conversation history; pass required context explicitly.
- Send one compact assignment: role, Worker mode when applicable, goal, decisive
  evidence, allowed/excluded paths, one acceptance check, minimum/maximum
  estimate with maximum <=20, stop conditions, and report format.
- For `Worker(mode=research)`, resume that same Worker for its selected
  implementation lane with `send_input` when the active surface supports it.
  Otherwise pass the compact task-file research to a fresh Worker.
- Overseer and Critic are always new no-history children. Include the raw user
  request/corrections and task file; never include L's desired verdict.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.

If the active Codex surface cannot create a no-history gate child, report the
unsupported boundary instead of using a history-forked substitute.
