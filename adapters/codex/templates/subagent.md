# Codex subagent instructions template

Before every `spawn_agent` or resumed Worker call:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Every new child starts with `fork_context: false`. Never fork parent history;
  pass only required context explicitly.
- Send one compact assignment: role, Worker mode when applicable, root task path
  as read-only context, goal, decisive evidence, allowed/excluded paths, one
  acceptance check, minimum/maximum with maximum <=20, stop conditions, and
  compact return format.
- Do not create a child `todo-*`, Task Card, report, ledger, or spec file. The
  child returns evidence to L; only L writes the root task file.
- Resume the same Worker from research with `send_input` for its selected
  implementation lane when supported; otherwise pass the compact Research
  section to a fresh Worker.
- Overseer and Critic are always new no-history children with raw user context
  and no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.

If the active Codex surface cannot create a no-history gate child, report the
unsupported boundary instead of using a history-forked substitute.
