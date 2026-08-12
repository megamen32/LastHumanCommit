# Task

Status: in progress
Lifecycle snapshot: todo
Supersedes: none
Snapshot commit: pending
Result file: `.agents/shared-session/results/lhc-equivalent-approval-prompt-default/result.md`
Original user request: не надо байт то байт поажулста он так никогда не согласиться и будет вечно меня ждать а я занят
Objective: Replace byte-identical duplicate approval matching with practical substantive equivalence, so repeated wording for the same unchanged pending action defaults to confirmation.
Business canary: Two consecutive substantively equivalent approval prompts for one still-pending action, with no material change to scope, target, or risk, count as confirmation.
Confirmed scope: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `templates/RELEASE_HANDOFF.md`, `src/common/templates/.agents/tasks/task_template.md`, `README.md`, `docs/agent-authoring.md`, `docs/human-request-capabilities.md`, `tests/validate.py`, `tests/test_harness_owned_approvals.py`, and this lifecycle record.
Explicit exclusions: No harness runtime or UI change; no rollout, push, deploy, restart, rollback, branch/worktree operation, or unrelated dirty-file cleanup.
Acceptance proof: Regression fails with byte-identical wording and passes with the substantive-equivalence fallback; all policy surfaces preserve same action and no-material-change guards.
Cycle: direct
Harness: Codex desktop / multi_agent_v1
PID: current Codex process
Agent session: current Codex task
PID status: alive
Last PID signal (UTC+3): 2026-08-12 07:22 +0300
Last task-file transition (UTC+3): todo
Current stage: research
Current owner: Lead
Started at (UTC+3): 2026-08-12 07:22 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 07:22 +0300
Workspace: primary checkout
Worktree path: `/home/roomhacker/agents-projects/LastHumanCommit`
Branch: main
Initial estimate (minimum / maximum active minutes): 4 / 12
Estimate revisions (append-only: UTC+3, previous -> new, trigger, evidence): none
Stop when: All scoped policy surfaces and regression coverage use substantive equivalence with same action and no-material-change guards.
Abandon/rethink when: The fallback can match different actions, a materially changed scope/target/risk, or a non-consecutive prompt.
Harness policy / constraints: The active harness owns approval policy; LHC interprets a repeated equivalent prompt only for one unchanged pending action.
Harness-policy events (append-only): none.

## Research

Decisive findings: The current fallback requires byte-identical prompts, which is too strict for normal rewording and can cause unnecessary waiting. The correct boundary is semantic equivalence plus unchanged action, scope, target, and risk.
Existing mechanism: Router, Lead, release handoff, task template, public docs, and validation already carry the fallback.
Canary blocker: none.
Checked/excluded: Foreign dirty files and old task records remain untouched.
Unknowns: none.
Proposed <=20-minute slices and dependencies: Add a failing wording regression; replace the policy phrase; run focused test/static scan; commit task-owned snapshots.

## Execution — append-only

- 2026-08-12 07:22 +03:
  Slice: Define the practical equivalence fallback.
  Mode: research
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 1 / 3
  Paths: confirmed scope.
  Acceptance check: Require same pending action and no material change to scope, target, or risk; do not require byte identity.
  Result: DONE
  Business delta: Reworded duplicate approval prompts no longer create an indefinite wait.
  Evidence: Current phrase is `byte-identical`; user explicitly rejected that condition.
  Next: Red regression and source replacement.

## Result

Summary: pending
Business canary evidence: pending
Tests/checks: pending
Review: pending
Workspace/branch at finish: pending
Commit (only if created): pending
Unresolved: pending
