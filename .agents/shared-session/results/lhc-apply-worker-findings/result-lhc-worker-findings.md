# Result: LHC worker findings applied

Status: complete
Task: `.agents/tasks/work-20260811-lhc-apply-worker-findings.md`

The core contract now records task-local handoff and exact named result paths,
preserves todo/work/done snapshots, and documents Worker resume from committed
work. Adviser/Critic ordering includes adversarial review of all three plans
before Adviser revision and human selection. Full completion requires two fresh
blind real-use Testers with durable business-result evidence. Overseer has an
explicit veto for unsolicited strict validation, security, and hardening;
NoticePlace is the canonical human-request capability; and the 30-minute hook
fallback marker is documented.

Verification: `python3 tests/validate.py`, `sh tests/test_task_states.sh`,
`sh tests/test_task_resume_snapshots.sh`, and `cmp -s AGENTS.md CLAUDE.md` all
passed.

No plugin installation, plugin-source audit, deployment, runtime change, or
unsolicited security/strict-validation work was performed.
