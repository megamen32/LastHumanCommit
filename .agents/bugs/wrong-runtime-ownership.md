# Lead incorrectly delegates its runtime responsibility

Description: current instructions assign waiting, veto evaluation, deployment,
and rollback to Agent Fleet or an external scheduler instead of L.
Evidence: `CANON.md` and `src/common/agents/Lead.md` contain that ownership.
Blocks: `work-20260730-role-router-yagni.md`
