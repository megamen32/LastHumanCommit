# OpenCode subagent instructions template

Before every delegated task:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Send one compact assignment: role, Worker mode when applicable, goal, decisive
  evidence, allowed/excluded paths, one acceptance check, minimum/maximum
  estimate with maximum <=20, stop conditions, and report format.
- Start the initial Worker through the native fresh-agent boundary. Resume the
  same Worker from research into its selected implementation lane when the
  active OpenCode surface supports resume; otherwise pass the task-file research
  to a fresh Worker.
- Overseer and Critic are always fresh no-history agents with the raw user
  request/corrections passed explicitly, never L's desired verdict.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
