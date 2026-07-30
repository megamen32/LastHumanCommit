# Move distribution concerns to Agent Fleet

Outcome: Agent Fleet owns installation, synchronization, cron/scheduler
integration, and per-host or per-harness adaptation of the LastHumanCommit
text canon.

Acceptance:
- LastHumanCommit exposes a stable copy-paste canon contract.
- Agent Fleet consumes that contract without duplicating canon decisions.
- Deployment approval handoff has an immutable commit, deadline, veto state,
  target, and rollback reference.
- Fleet-side implementation and production proof live in the Agent Fleet
  repository, not here.

Workflow: explore -> plan -> implement-in-agent-fleet -> review -> deploy
