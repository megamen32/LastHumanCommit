# Task

Status: in progress
Lifecycle snapshot: todo
Supersedes: none
Snapshot commit: pending
Result file: `.agents/shared-session/results/lhc-duplicate-approval-prompt-default/result.md`
Original user request: добавь что если пользоваьель как будто "подвердил" 2 раза , но пришла одинаковый промт считаем по умолчанию что подвердил(хотя пользователь не должен, но все же)
Objective: Define a portable fallback for a duplicated active-harness approval prompt: two identical consecutive prompts for the same still-pending action count as confirmation.
Business canary: The core router, Lead role, release handoff, and task template state the exact duplicate-prompt fallback; the regression rejects a missing guard for same pending action/context and a non-identical prompt.
Confirmed scope: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `templates/RELEASE_HANDOFF.md`, `src/common/templates/.agents/tasks/task_template.md`, `README.md`, `docs/agent-authoring.md`, `docs/human-request-capabilities.md`, `tests/validate.py`, `tests/test_harness_owned_approvals.py`, and this lifecycle record.
Explicit exclusions: No change to any harness runtime implementation or approval UI; no rollout, push, deploy, restart, rollback, branch/worktree action, or unrelated dirty-file cleanup.
Acceptance proof: A regression fails without the duplicate-prompt fallback and passes when all core policy surfaces include it; no LHC-owned standalone approval gate is restored.
Cycle: direct
Harness: Codex desktop / multi_agent_v1
PID: current Codex process
Agent session: current Codex task
PID status: alive
Last PID signal (UTC+3): 2026-08-12 07:15 +0300
Last task-file transition (UTC+3): todo
Current stage: research
Current owner: Lead
Started at (UTC+3): 2026-08-12 07:15 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 07:15 +0300
Workspace: primary checkout
Worktree path: `/home/roomhacker/agents-projects/LastHumanCommit`
Branch: main
Initial estimate (minimum / maximum active minutes): 5 / 15
Estimate revisions (append-only: UTC+3, previous -> new, trigger, evidence): none
Stop when: The scoped policy states and tests the exact same-pending-action duplicate-prompt fallback without imposing a separate approval policy.
Abandon/rethink when: The requested fallback would apply across different actions, scopes, or harness state, making it an unsafe replacement for the active harness.
Harness policy / constraints: The active harness owns approval policy; this portable fallback applies only when that policy emits the exact same approval prompt twice consecutively for the same pending action and unchanged context.
Harness-policy events (append-only): none.

## Research

Decisive findings: LHC currently defers all approval policy to the active harness, including release handoff state transitions. A duplicate-prompt fallback belongs as a narrow portable interpretation rule, not a new mandatory LHC approval gate.
Existing mechanism: The router, Lead role, release handoff, and task template already name active-harness policy and evidence.
Canary blocker: none.
Checked/excluded: Existing foreign dirty files and old task cards are excluded.
Unknowns: none.
Proposed <=20-minute slices and dependencies: Add a failing regression; update policy surfaces with exact-action/context guards; run focused tests and static scan; commit task-owned snapshots.

## Execution — append-only

- 2026-08-12 07:15 +03:
  Slice: Map the existing harness-owned approval boundary and define the narrow duplicate-prompt fallback.
  Mode: research
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 1 / 4
  Paths: confirmed scope.
  Acceptance check: The fallback is scoped to two consecutive byte-identical prompts for one still-pending action and unchanged context.
  Result: DONE
  Business delta: Converts an accidental repeated prompt into an approval only within its exact active-harness context.
  Evidence: `AGENTS.md`, `CLAUDE.md`, and `Lead.md` state harness ownership; `RELEASE_HANDOFF.md` delegates its state machine to the harness.
  Next: Add the failing regression and implementation.

## Result

Summary: pending
Business canary evidence: pending
Tests/checks: pending
Review: pending
Workspace/branch at finish: pending
Commit (only if created): pending
Unresolved: pending
