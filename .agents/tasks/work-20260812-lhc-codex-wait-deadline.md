# Task

Status: in progress
Lifecycle snapshot: work
Supersedes: none
Snapshot commit: pending
Result file: `.agents/shared-session/results/lhc-codex-wait-deadline/result.md`
Original user request: Change LastHumanCommit so Codex `wait_agent` timeouts are observational only, preserve workers until authoritative terminal status or explicit cancellation, then push and apply/deploy the reviewed result.
Objective: Remove the misleading dead/unknown inference, document a fixed 30-minute join deadline for Codex V1/V2, and add a fail-closed regression check.
Business canary: A Codex Lead can wait for a child with `timeout_ms: 1800000`; an early timeout or mailbox wake does not authorize `close_agent`, replacement creation, or a dead/unknown conclusion.
Confirmed scope: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `adapters/codex/instructions.md`, `adapters/codex/templates/subagent.md`, `tests/validate.py`, and this lifecycle record.
Explicit exclusions: No Codex runtime source change; no global default timeout change; no unrelated dirty-file cleanup; no branch/worktree changes; no deploy before explicit release authorization.
Acceptance proof: Focused static regression and `python3 tests/validate.py` pass; reviewed task-owned diff contains the timeout invariants and fixed absolute-deadline contract; release handoff records commit, target, checks, and authorization state.
Cycle: short
Harness: Codex desktop / multi_agent_v1
PID: 38141
Agent session: current Codex task
PID status: alive
Last PID signal (UTC+3): 2026-08-12 00:03:49 +0300
Last task-file transition (UTC+3): work
Current stage: implementation
Current owner: Worker
Started at (UTC+3): 2026-08-12 00:03:49 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 00:05:00 +0300
Workspace: primary checkout
Worktree path: `/home/roomhacker/agents-projects/LastHumanCommit`
Branch: main
Initial estimate (minimum / maximum active minutes): 8 / 20
Estimate revisions (append-only: UTC+3, previous -> new, trigger, evidence): none
Stop when: The scoped files pass focused and full validation, are reviewed, committed without foreign edits, and a release handoff is ready.
Abandon/rethink when: Validation exposes a conflicting contract, the scope grows beyond the listed files, or a required release/deploy mechanism is not identifiable.
Forbidden without explicit user authorization: push, deploy/apply, restart, rollback, branch/worktree operations, destructive cleanup, secret handling.
Consequential authorization questions (append-only): 2026-08-12 00:03 +03 — exact `git push origin main` and runtime apply/deploy remain pending explicit confirmation at release handoff.

## Research

Decisive findings: The root checkout is primary `main` at `591ed96`; `AGENTS.md` and `CLAUDE.md` contain the unsafe “no completion signal => dead or unknown” rule. Codex adapter files currently have no fixed `wait_agent` join contract.
Existing mechanism: Codex `wait_agent` accepts explicit `timeout_ms`; LHC already requires authoritative lifecycle state and separates release authorization.
Canary blocker: None for local implementation; runtime deployment target/mechanism still needs to be resolved from the selected release path.
Checked/excluded: Existing unrelated dirty files and auxiliary worktrees were preserved; no Codex runtime source will be changed.
Unknowns: Whether the requested `apply(deploy)` means a specific fleet rollout command or only publishing the LHC repository; determine from repository release tooling after local verification.
Proposed <=20-minute slices and dependencies: Worker research/implementation of scoped text and validation; Lead integration and focused checks; Reviewer read-only diff gate; Overseer receipt; release handoff; explicit push/deploy authorization.

## Execution — append-only

- 2026-08-12 00:03 +03:
  Slice: Create task lineage and inspect current Codex/LHC contracts.
  Mode: research
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 2 / 5
  Paths: `.agents/tasks/todo-20260812-lhc-codex-wait-deadline.md`, `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `adapters/codex`, `tests/validate.py`
  Acceptance check: Root, branch, worktrees, dirty scope, unsafe anchors, and release boundary recorded.
  Result: DONE
  Business delta: Established the scoped fix and preserved foreign edits.
  Evidence: primary checkout `/home/roomhacker/agents-projects/LastHumanCommit`, branch `main`, HEAD `591ed96`; unsafe anchors at lines 55-58 of both root instruction files.
  Next: Worker implements the scoped contract and regression.

- 2026-08-12 00:05 +03:
  Slice: Transition the lifecycle snapshot from todo to work before implementation.
  Mode: implement: bugfix/TDD
  Owner: Worker
  Estimate (minimum / maximum; maximum <=20): 5 / 15
  Paths: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `adapters/codex/instructions.md`, `adapters/codex/templates/subagent.md`, `tests/validate.py`
  Acceptance check: Add the wait invariants and fixed absolute join deadline; reject unsafe inference; focused and full validation pass; no unrelated files changed.
  Result: pending
  Business delta: pending
  Evidence: pending
  Next: Worker implementation.

- 2026-08-12 00:21 +03:
  Slice: Integrate corrected Worker result and independent review.
  Mode: review
  Owner: Lead
  Estimate (minimum / maximum; maximum <=20): 3 / 8
  Paths: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `adapters/codex/instructions.md`, `adapters/codex/templates/subagent.md`, `tests/validate.py`, this task card.
  Acceptance check: Reviewer PASS; focused contract, parity, diff check, and scoped-name check pass; full validator blocker is explicitly recorded.
  Result: DONE
  Business delta: The Codex adapter now has a fail-closed absolute join contract that cannot turn a wait timeout/mailbox wake into worker termination or replacement.
  Evidence: Fresh Reviewer PASS; focused mechanics PASS; `cmp AGENTS.md CLAUDE.md` PASS; `git diff --check` PASS; `python3 tests/validate.py` reaches the pre-existing foreign task-card defect and fails there.
  Next: Commit reviewed task-owned changes, then prepare release handoff and preview.

## Overseer receipts — append-only

- 2026-08-12 00:03 +03:
  Trigger: Initial Short-task route.
  VERDICT: CONTINUE
  BUSINESS_DELTA: Scoped fix matches the stated diagnosis; no runtime source change is needed.
  ESTIMATE: 8 / 20 active minutes.
  WASTE: None identified.
  NEXT: Implement only the listed adapter/core/test files, then review before release handoff.
  QUESTION: None; push/deploy authorization is reserved for the exact release action.

## Child assignment and detailed report — append-only

The explicit `<Role> <absolute-task-file-path>` bootstrap is authoritative.
Children append detailed evidence and result to this file, then return only TL;DR to L.

- Role: Worker
  Mode: implement: bugfix/TDD
  Started: 2026-08-12 00:05 +03
  Allowed/excluded paths: Allowed — six listed contract/test files; excluded — runtime Codex source, unrelated dirty files, branches/worktrees, deployment.
  Acceptance and stop conditions: `python3 tests/validate.py` plus focused assertions pass; stop and return `NEEDS_RETHINK` on conflicting anchors or scope growth.
  Detailed evidence and result: pending
  L-facing return: TL;DR only with changed paths, checks, and blockers.

## Independent gates — append-only

Overseer: CONTINUE receipt recorded above; no dedicated Overseer capability exposed in this harness.
Reviewer: PASS — fresh read-only review confirmed observational-only timeout, authoritative terminal/cancellation gate, V1/V2 monotonic deadline, remaining-time/no-reset semantics, child preservation, scoped diff, and aggregate/surface-specific regression checks.
Tester: not applicable — this is an instruction/adapter contract change; static acceptance is the canary.
Critic: pending before irreversible release action if required by the selected release route.

## Release handoff — append-only

- handoff_id: lhc-codex-wait-deadline-2c749fb
- status: pending
- review_sent_at (UTC+3): 2026-08-12 00:23 +0300
- execution_guard: single_serialized_L
- commit_or_artifact: `2c749fbbe3cbc58963d55b5fb2fd7fb6bf5d122e`
- tests: focused contract PASS; py_compile PASS; AGENTS/CLAUDE cmp PASS; diff-check PASS; full validator blocked by pre-existing foreign task-card defect.
- target: canonical LHC Fleet manifest `100/44/88/mac` via `lhc-rollout`.
- acceptance_proof: preview status PASS; 52 files; digest `sha256:8a02925a47216d615c0c8566405de63abd0003da786cd4015a78e57c77d2ba89`; all targets currentBefore `versions/591ed96`; rollback roots present in preview.
- preview_confirmation: `sha256:0f17a6dec683295f05c9d276d213f2be5db7bebb0ad7fcb1813e6235568da13a`
- rollback_reference_if_existing: previewed per-target `.../rollbacks/2c749fb-lhc-rollout`.
- veto_state: none
- last_human_reply_at_or_id: user request to push and apply/deploy; exact confirmation still required by release policy.
- deployment_started_at (UTC+3): pending
- deployment_result: pending
- exact pending action: `git push origin main`, then apply the exact preview confirmation above, then independent verify and physical router canary.

## Result

Summary: pending
Business canary evidence: pending
Tests/checks: pending
Review: pending
Workspace/branch at finish: pending
Commit (only if created): pending
Unresolved: pending

## Worker implementation evidence — append-only

- 2026-08-12 00:08 +03:
  Slice: Implement the Codex wait-agent safety contract and fail-closed static regression.
  Owner: Worker.
  Changed paths: `AGENTS.md`, `CLAUDE.md`, `src/common/agents/Lead.md`, `adapters/codex/instructions.md`, `adapters/codex/templates/subagent.md`, `tests/validate.py`.
  Red proof: Before documentation changes, `python3 tests/validate.py` failed with `AGENTS.md lacks: wait timeout is observational only` after the new assertions were added.
  Implementation: Replaced the unsafe missing-signal dead/unknown inference with observational-only wording; required authoritative terminal status or explicit cancellation; documented Codex V1/V2 fixed absolute 30-minute join deadline as `timeout_ms: 1800000` (1800000 ms); prohibited `close_agent` and replacement on timeout; added fail-closed assertions for all five contract surfaces.
  Green focused proof: A normalized static assertion over all five files passed (`focused wait-agent contract: PASS`); `AGENTS.md == CLAUDE.md: PASS`; `git diff --check` passed.
  Full validation: `python3 tests/validate.py` reaches the pre-existing foreign task-card scan and fails at `.agents/tasks/work-20260811-lhc-three-identical-zero-knowledge-reviews.md` because `Last task-file mtime observed (UTC+3)` is missing. That path is outside the assignment, was not changed, and blocks a clean full-validator result.
  Safety: No Codex runtime source, branch/worktree, push, deploy/apply, restart, rollback, or destructive cleanup was performed. Existing unrelated dirty files were preserved.
  Result: DONE for the scoped implementation; full validation BLOCKED by the unrelated lifecycle-card defect.
  L-facing return: TL;DR only with changed paths, checks, and blocker.

## Worker correction evidence — append-only

- 2026-08-12 00:16 +03:
  Slice: Correct the Reviewer `NEEDS_RETHINK` by making V1/V2 join mechanics explicit and fail-closed.
  Owner: Worker.
  Red proof: After replacing the brittle per-file assertion loop with aggregate/surface assertions, `python3 tests/validate.py` failed on the missing `deadline = monotonicNow() + 1800000 ms` invariant.
  Implementation: Added one monotonic absolute deadline per join; distinct Codex V1 target-specific wait and Codex V2 mailbox wake mechanics using the same absolute deadline; status re-check on every mailbox wake or `timed_out` result; `remainingMs = deadline - monotonicNow()` and wait-only-with-remainingMs behavior; no reset/restart after wake/timeout; `remainingMs <= 0` returns `join-deadline-expired` with child preserved and no close/dead-inference/replacement.
  Test correction: `tests/validate.py` now checks the mechanics in a contract aggregate, requires only surface-specific markers per relevant file, and retains fail-closed forbidden legacy inferences without requiring every phrase in every file.
  Green focused proof: Aggregate/surface mechanics check passed; `AGENTS.md == CLAUDE.md` parity passed; `git diff --check` passed.
  Full validation: `python3 tests/validate.py` passes the new wait-contract assertions and remains blocked at the unchanged foreign `.agents/tasks/work-20260811-lhc-three-identical-zero-knowledge-reviews.md` lifecycle-field defect. The foreign file remains untouched.
  Safety: Only the six scoped files and this append-only task evidence changed; no runtime Codex source, branch/worktree, push, deploy/apply, or destructive cleanup was performed.
  Result: DONE for the correction; full validation BLOCKED by the same unrelated lifecycle-card defect.
  L-facing return: TL;DR only with changed paths, checks, and blocker.
