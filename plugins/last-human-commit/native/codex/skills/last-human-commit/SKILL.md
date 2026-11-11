---
name: last-human-commit
description: Outcome-first engineering workflow. Make the smallest useful change, verify it with a real canary, and deliver it. Use a plan or delegation only when the owner asks or the work genuinely has independent lanes.
---

# Last Human Commit

The owner gives the goal. The Lead makes the shortest working path real.

## Default loop

1. Identify the observable result and the intended consumer.
2. Reuse the regular path already present in the project.
3. Make the smallest vertical change.
4. Run focused tests and one real canary/readback.
5. Fix concrete failures and rerun the changed path.
6. Commit and deliver.

A bounded task does not require a plan, worker, reviewer, council, ACK, evidence manifest,
leaf ledger or independent tester. These are optional tools. A missing receipt or plan state
must never make a working local result look unfinished.

## When to plan or delegate

Use a short plan only when the owner asks for one, the work has several independent lanes,
or an irreversible release needs coordination. Keep it to three stages: implementation,
verification, delivery. Delegate only when it saves time or supplies a meaningful independent
check. Do not create a leaf for every observation.

## Verification

Use a real consumer canary whenever one is available. A quickfix or assigned leaf does not
require a fresh independent Tester. The Lead's canary is valid when it exercises the changed
path. Use independent testers for explicit release/high risk work or when the owner asks for
them.

## Boundaries

Keep effect-level protections: secret/data privacy, target ownership, production scope,
unknown external mutation results, shared-worktree ownership and human STOP/revocation.
Process metadata such as goal binding, native outcome, ACK, timer, lease, evidence path and
review status is advisory. Never repeat an unknown mutation; do continue independent work.

## Report

Report the consumer result first. Include only the exact blocker and the next action when
the consumer is unavailable. Do not turn bookkeeping into a second task.
