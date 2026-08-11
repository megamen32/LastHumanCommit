# Task

Status: in progress
Lifecycle snapshot: todo
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
Last task-file transition (UTC+3): todo
Current stage: research
Current owner: Lead
Started at (UTC+3): 2026-08-12 00:03:49 +0300
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-12 00:03:49 +0300
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
  Next: Commit todo snapshot, then Worker implementation.

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

## Independent gates — append-only

Overseer: CONTINUE receipt recorded above; no dedicated Overseer capability exposed in this harness.
Reviewer: pending
Tester: not applicable — this is an instruction/adapter contract change; static acceptance is the canary.
Critic: pending before irreversible release action if required by the selected release route.

## Result

Summary: pending
Business canary evidence: pending
Tests/checks: pending
Review: pending
Workspace/branch at finish: pending
Commit (only if created): pending
Unresolved: pending
