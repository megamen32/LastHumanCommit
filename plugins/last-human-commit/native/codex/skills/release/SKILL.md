---
name: release
description: Lead-owned claim-calibrated procedure for a controlled consequential release action.
---

# Release

Use only when the accepted result needs a release, deploy, tag, publication, or
another consequential action.

Before implementation, testing or deployment, load the primary checkout's
`.agents/TEST_ACCESS.md` via Git worktree mapping and follow the active package's
`common/protocols/REVIEW_TO_DELIVERY.md` execution-access contract. Reuse/recover
authorized local test access with supported administration; persist only protected
references/scope at handoff. Existing authority permits preparation without reasking;
unknown/revoked operations stay blocked. Sudo alone never grants authority.

## Procedure

1. Confirm the target, artifact/commit, accepted claim, active-harness policy,
   and exact release canary.
2. Use only the review/testing/rollback gates justified by this action's actual
   blast radius and reversibility.
3. Before merge, verify the published task branch with `lhc_worktree.py delivery` and a matching PR only when configured `pr_stage=on`;
   source evidence is not merge/deploy authorization. After an authorized merge,
   do not require an open PR or task checkout: verify the merged PR/commit is on
   the current permitted target and the candidate artifact is built from that
   exact revision. Acquire the existing
   Agent Herder `project_release_lease` for this canonical project, inspect its
   status/owner and use the returned `SendMessage` target for contention.
   Immediately before mutation, check token/fence and compare the expected
   deployed revision with the actual revision. A stale owner or newer release
   blocks the candidate. Release in `finally`; terminal lifecycle hooks and TTL
   are recovery, not permission to bypass ownership. Do not use normal turn end
   as session termination. Keep authorized rollback explicit.
4. Record source/test proof, release state, and post-action business proof
   separately.

## Do not

- Do not treat every release as requiring the same roles or number of tests.
- Do not invent deployment or rollback work outside the accepted boundary.
- Do not treat a timer, wake, or process health as authorization or business
  success.
