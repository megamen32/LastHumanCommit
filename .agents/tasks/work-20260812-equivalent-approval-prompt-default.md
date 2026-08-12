# Task

Status: complete
Lifecycle snapshot: work
Supersedes: `.agents/tasks/todo-20260812-equivalent-approval-prompt-default.md`
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
PID status: completed
Last PID signal (UTC+3): 2026-08-12 07:26 +0300
Last task-file transition (UTC+3): done
Current stage: release
Current owner: Lead
Started at (UTC+3): 2026-08-12 07:22 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 07:26 +0300
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

- 2026-08-12 07:25 +03:
  Slice: Replace byte-identical matching with substantive equivalence and validate.
  Mode: implement: feature
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 3 / 7
  Paths: confirmed policy source, documentation, validation, and test paths.
  Acceptance check: The policy has equivalent-prompt, same-action, and no-material-change guards; byte-identical matching is absent.
  Result: DONE
  Business delta: Reworded duplicate prompts confirm a task instead of creating an indefinite wait, provided scope, target, and risk have not materially changed.
  Evidence: Red `pytest` failed before replacement; green `python3 -m pytest -q tests/test_harness_owned_approvals.py` passed `3 passed`; source audit found the new fallback on all required surfaces and no byte-identical policy match; `git diff --check` passed. Full validation is blocked by unrelated `.agents/tasks/work-20260811-lhc-three-identical-zero-knowledge-reviews.md` missing `Last task-file mtime observed (UTC+3)`.
  Next: Commit task-owned snapshots and handoff.

- 2026-08-12 07:26 +03:
  Slice: Final scoped review and handoff.
  Mode: review
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 1 / 2
  Paths: confirmed scope and lifecycle snapshots.
  Acceptance check: Equivalent wording is constrained to the same action without material scope, target, or risk change, and LHC still defers approval ownership to the harness.
  Result: DONE
  Business delta: Duplicate wording becomes practical confirmation rather than an infinite approval loop.
  Evidence: Focused suite `3 passed`; byte-identical scan clean; whitespace check clean.
  Next: Commit scope only; no rollout or push.

## Result

Summary: Replaced byte-identical matching with substantive equivalence: two consecutive equivalent approval prompts confirm the same pending action when scope, target, and risk are unchanged.
Business canary evidence: The core router, Lead role, release handoff, and task template carry the practical fallback.
Tests/checks: Red `pytest` proof before source replacement; green `python3 -m pytest -q tests/test_harness_owned_approvals.py` (`3 passed`); `git diff --check` passed; full validator remains blocked by the unrelated legacy task-card field defect.
Review: Scoped review passed; no standalone LHC approval gate was reintroduced.
Workspace/branch at finish: `/home/roomhacker/agents-projects/LastHumanCommit`, `main`.
Commit (only if created): pending.
Unresolved: Installed version unchanged; no rollout or push performed.
