# Task

Status: in progress
Lifecycle snapshot: todo
Supersedes: none
Snapshot commit: pending
Result file: `.agents/shared-session/results/lhc-harness-owned-approvals/result.md`
Original user request: lhc -заебал меня заставлять все подверждать. убери эти строчки в инстукциях! в harnessah естьсвои правила approve
Objective: Remove LHC-owned mandatory approval gates and defer approval policy to the active harness while preserving optional capability-based requests for missing information and secrets.
Business canary: A generated LHC instruction set contains no mandatory first/second human approval, explicit-selection, or action-specific authorization requirement; it states that the active harness owns approval policy.
Confirmed scope: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `templates/FULL_CYCLE.md`, `templates/RELEASE_HANDOFF.md`, `src/common/templates/.agents/tasks/task_template.md`, `README.md`, `docs/agent-authoring.md`, `docs/human-request-capabilities.md`, `skills/business-delivery/SKILL.md`, `tests/validate.py`, and this lifecycle record.
Explicit exclusions: No change to harness approval configuration; no deployment, restart, rollback, branch/worktree operation, push, or unrelated dirty-file cleanup.
Acceptance proof: Regression validation fails before the source/documentation change and passes after it; static scan finds no LHC rule that requires a human approval/selection/authorization, while the active-harness ownership phrase appears in the router and Lead role.
Cycle: direct
Harness: Codex desktop / multi_agent_v1
PID: current Codex process
Agent session: current Codex task
PID status: alive
Last PID signal (UTC+3): 2026-08-12 07:04 +0300
Last task-file transition (UTC+3): todo
Current stage: research
Current owner: Lead
Started at (UTC+3): 2026-08-12 07:04 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 07:04 +0300
Workspace: primary checkout
Worktree path: `/home/roomhacker/agents-projects/LastHumanCommit`
Branch: main
Initial estimate (minimum / maximum active minutes): 8 / 20
Estimate revisions (append-only: UTC+3, previous -> new, trigger, evidence): none
Stop when: The scoped source, templates, public documentation, and regression checks demonstrate harness-owned approval policy without task-owned approval gates.
Abandon/rethink when: A rule proves to govern secret handling or missing-information capability semantics rather than approval policy, or required validation would entail unrelated dirty-file edits.
Forbidden without explicit user authorization: No additional policy constraints; the active harness defines approval rules.
Consequential authorization questions (append-only): none; approval policy is owned by the active harness.

## Research

Decisive findings: LHC enforces its own approval policy in the root router, Lead role, Full-cycle/template/task card, release handoff, documentation, skill, and static validator. The active runtime contract already exposes harness capabilities such as AskHuman and AskSecret/SSS.
Existing mechanism: Harness adapters resolve and attest capabilities; LHC must keep only portable task and role policy.
Canary blocker: none.
Checked/excluded: Existing unrelated dirty task records and auxiliary worktrees are preserved.
Unknowns: none.
Proposed <=20-minute slices and dependencies: Add a failing harness-ownership regression; revise the listed instruction sources; run focused and full static validation; inspect the task-owned diff.

## Execution — append-only

- 2026-08-12 07:04 +03:
  Slice: Establish task lineage and map all LHC-owned approval gates.
  Mode: research
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 2 / 5
  Paths: listed confirmed scope.
  Acceptance check: Every mandatory approval phrase and validator constraint is identified before mutation.
  Result: DONE
  Business delta: Defined the portable boundary: LHC must defer approvals to the active harness.
  Evidence: Root router lines 107 and 131-133; Lead Full-cycle and consequential-actions sections; template, handoff, public docs, skill, and `tests/validate.py` assertions.
  Next: Add a failing regression, then replace the duplicate policy with harness ownership.

## Result

Summary: pending
Business canary evidence: pending
Tests/checks: pending
Review: pending
Workspace/branch at finish: pending
Commit (only if created): pending
Unresolved: pending
