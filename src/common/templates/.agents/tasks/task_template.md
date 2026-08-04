# Task

Status: todo | in progress | blocked | complete
Initial role (informational):
Original user request:
Objective:
Business canary:
Confirmed scope:
Explicit exclusions:
Acceptance:
Initial estimate (optimistic / likely / pessimistic active minutes):
Estimate revisions (append-only; trigger and evidence):
Cycle: direct | short | full | emergency
Workflow:
Current delivery slice:
Stop when:
Abandon when:
Forbidden without explicit user request:
Consequential authorization questions (append-only):

## Overseer audit receipts (append-only)

Add an entry only for an eligible audit. Never replace or delete an earlier
entry. `CONTINUE` is not repeated to the user.

- Timestamp:
  Stage:
  Evidence:
  Business delta:
  Avoidable spend:
  Next minimal action:
  Direct user question:
  Decision: CONTINUE | ASK_USER | STOP_DRIFT

## Critic decision history (append-only)

Add one entry for every decision. Never replace or delete an earlier entry.

- Timestamp:
  Stage:
  Evidence:
  Current user P0:
  Business delta:
  P0 distance: CLOSER | SAME | FARTHER
  Questions for L:
  Decision: PASS | RETHINK | STOP | STOP_SCOPE_DRIFT | STOP_MISSING_CONTEXT

## Decision

Research:
Plans:
Human selection:
Selected-plan WSFF:

## Work

Current:
Next:
Blocked by:
Evidence:

## Child assignment

The explicit role in `<Role> <task-file-path>` is authoritative for this pass.
Reuse this same file for sequential passes such as Worker then Reviewer; append
each pass and its detailed result below.
Goal and known facts:
Allowed and excluded paths:
Acceptance and stop conditions:
Model and budget:
Detailed report appended here:
L-facing return: TL;DR only

## Role passes (append-only)

- Role:
  Started:
  Detailed result:

## Result

Summary:
Tests:
Review:
Commit:
Unresolved:
