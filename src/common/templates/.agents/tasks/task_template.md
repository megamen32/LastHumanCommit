# Task

Status: in progress | blocked | complete
Original user request:
Objective:
Business canary:
Confirmed scope:
Explicit exclusions:
Acceptance proof:
Cycle: direct | short | full | emergency
Harness:
PID:
Agent session:
PID status: alive | completed | dead | unknown
Last PID signal (UTC+3):
Last task-file transition (UTC+3): todo | work | done
Current stage: research | planning | YAGNI | Normal | Ultimate | review | release
Current owner:
Started at (UTC+3):
Workspace: primary checkout | auxiliary worktree | detached HEAD
Worktree path:
Branch:
Initial estimate (minimum / maximum active minutes):
Estimate revisions (append-only: UTC+3, previous -> new, trigger, evidence):
Stop when:
Abandon/rethink when:
Forbidden without explicit user authorization:
Consequential authorization questions (append-only):

## Research

Use this section for compact Worker findings only.

Decisive findings:
Existing mechanism:
Canary blocker:
Checked/excluded:
Unknowns:
Proposed <=20-minute slices and dependencies:

## Three plans — Full only

### 1. Максимально идеальный

Outcome / scope / omissions / trade-offs / risks / minimum-maximum estimate /
verification / migration / execution graph:

### 2. Нормальный

Outcome / scope / omissions / trade-offs / risks / minimum-maximum estimate /
verification / migration / execution graph:

### 3. YAGNI 80/20 — полный результат

Outcome / scope / omissions / trade-offs / risks / minimum-maximum estimate /
verification / migration / execution graph:

Recommendation:
First human selection (verbatim):

## Selected-plan technical preview — Full only

Call-stack tree:
File-tree diff:
Key types and method signatures:
Pseudocode:
Migration description:
Exact canary:
Consequential authorization boundaries:
Execution graph (each node: owner, paths, acceptance, dependencies, max <=20):
Second explicit human approval (verbatim):

## Execution — append-only

- UTC+3:
  Slice:
  Mode: research | implement: bugfix/TDD | implement: feature
  Owner:
  Estimate (minimum / maximum; maximum <=20):
  Paths:
  Acceptance check:
  Result: DONE | BLOCKED | NEEDS_REDECOMPOSITION | NEEDS_RETHINK
  Business delta:
  Evidence:
  Next:

## Overseer receipts — append-only

- UTC+3:
  Trigger:
  VERDICT: CONTINUE | RETHINK | ASK_USER | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT
  BUSINESS_DELTA:
  ESTIMATE:
  WASTE:
  NEXT:
  QUESTION:

## Critic decisions — append-only

- UTC+3:
  Current user P0:
  Evidence:
  P0 distance: CLOSER | SAME | FARTHER
  Questions for L:
  Decision: PASS | RETHINK | STOP | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT
  Minimum proof to proceed:

## Child assignment and detailed report — append-only

The explicit `<Role> <absolute-task-file-path>` bootstrap is authoritative.
The child reads only this assigned task file. Children append their detailed
evidence and result to that file, then return only TL;DR to L. Children never create a second task
card, report, ledger, specification, or recovery file.

- Role:
  Mode:
  Started:
  Allowed/excluded paths:
  Acceptance and stop conditions:
  Detailed evidence and result:
  L-facing return: TL;DR only

## Independent gates — append-only

Overseer:
Reviewer:
Tester:
Critic:

## Result

Summary:
Business canary evidence:
Tests/checks:
Review:
Workspace/branch at finish:
Commit (only if created):
Unresolved:
