# Release handoff

Use only when a consequential release/deploy/publication action remains.

## Accepted claim

Expected tangible capability after the action:
Tester scenario (actor/context, actions, expected visible result):
Current progress / observed facts and supporting evidence:
Exact target/action:
Artifact or commit:
Active-harness policy state:
Actual blast radius:
Reversibility / existing rollback reference:

## Proportional gates

For each check actually used, record the concrete risk it reduced and its result.
The Overseer advises on route; it does not gate release. Independent review or
testing is added when risk and claim warrant it. A concrete defect or missing
claim-critical proof blocks only the affected release action.

- Gate / risk / evidence / decision:

## Evidence dimensions

Source/build/test proof:
Release/deployment state:
Post-action real business canary:
Tree clean / pushed:
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

Apply the active harness approval-policy state machine. The active harness owns approval policy. Repeated prompts do not manufacture user consent.

Immediately before action, revalidate the target, artifact, accepted claim,
workspace, and active-harness state. After action, run the exact business canary
and report it separately from source/test and deployment receipts.
