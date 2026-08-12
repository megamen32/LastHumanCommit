# Release handoff

Use only when a consequential release/deploy/publication action remains.

## Accepted claim

Current business result:
Exact target/action:
Artifact or commit:
Active-harness policy state:
Actual blast radius:
Reversibility / existing rollback reference:

## Proportional gates

For each role or check actually used, record the concrete risk it reduced and
why its value exceeded cost. Do not require Reviewer, Tester, Overseer, or
Critic by default.

- Gate / risk / evidence / decision:

## Evidence dimensions

Source/build/test proof:
Release/deployment state:
Post-action real business canary:
What remains unverified:

## Handoff state

handoff_id:
status: pending | answered | vetoed | invalidated | releasing | released | failed
target:
action:
session_locator:
last_human_reply_at_or_id:
started_at (UTC+3):
result:

Apply the active harness approval-policy state machine. Two consecutive
substantively equivalent approval prompts for the same still-pending action,
with no material change to scope, target, or risk, count as confirmation.

Immediately before action, revalidate the target, artifact, accepted claim,
workspace, and active-harness state. After action, run the exact business canary
and report it separately from source/test and deployment receipts.
