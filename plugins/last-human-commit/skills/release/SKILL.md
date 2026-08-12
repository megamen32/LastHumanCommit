---
name: release
description: Lead-owned claim-calibrated procedure for a controlled consequential release action.
---

# Release

Use only when the accepted result needs a release, deploy, tag, publication, or
another consequential action.

## Procedure

1. Confirm the target, artifact/commit, accepted claim, active-harness policy,
   and exact release canary.
2. Use only the review/testing/rollback gates justified by this action's actual
   blast radius and reversibility.
3. Revalidate target and evidence immediately before action.
4. Record source/test proof, release state, and post-action business proof
   separately.

## Do not

- Do not treat every release as requiring the same roles or number of tests.
- Do not invent deployment or rollback work outside the accepted boundary.
- Do not treat a timer, wake, or process health as authorization or business
  success.
