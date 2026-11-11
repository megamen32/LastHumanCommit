# OpenCode child assignment

Follow the effective subagent setting in the package guide. Use the Lead's assigned checkout, goal, role, context and paths. The worktree helper `common/tools/lhc_worktree.py` creates `lhc/<task-slug>` under `<primary-project-root>/.worktrees/<task-slug>` when one is needed. Pass the assigned cwd to the native runtime.

Give the child the facts and previous attempts needed for its task, the expected result and a way to check it. Use fresh context for independent review or first-contact testing; reuse a useful Worker's context for continuation. Resolve the model from the actual catalog through `model-routing`.

Use the task's existing brief and result paths when a durable handoff is needed. The Lead owns plan decisions; an assigned Artifact Writer records those decisions in its named files. `common/protocols/ORCHESTRATION_RECORDS.md` describes the explicit-dispatch fields.

Ask the Lead about a decision its wider context can change. Continue independent work while awaiting the answer. A Worker still running reports progress, a blocker or next step by the agreed checkpoint. Measured time and estimates remain distinct.

Join a required child result through the native wait/status interface. A timeout prompts a status check and route decision; it does not establish failure. Preserve a healthy running child. After compaction, use the bound handoff and current plan to continue.

Write user-facing artifacts in the user's language and return useful detail without an arbitrary answer-length limit.

The independent Boss uses OpenCode 2 native sessions and injects its full prose. It does not need a manual initial audit or approval.
