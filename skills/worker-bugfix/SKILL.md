---
name: worker-bugfix
description: Worker-owned least-cost bug-fixing procedure for one bounded behavior failure. Use when a symptom, regression, broken business flow, failing test, or production-path defect must be reproduced, localized, and fixed. Reuse prior failure shields, prefer rg for fresh source tracing, choose the cheapest discriminating red proof, make the smallest coherent fix, and preserve a reusable root-cause map entry when recurrence is likely.
---

# Worker Bugfix

Fix one proven failure without turning it into a hardening project.

Before implementation, testing or deployment, load the primary checkout's
`.agents/TEST_ACCESS.md` via Git worktree mapping and follow the active package's
`common/protocols/REVIEW_TO_DELIVERY.md` execution-access contract. Reuse/recover
authorized local test access with supported administration; persist only protected
references/scope at handoff. Existing authority permits preparation without reasking;
unknown/revoked operations stay blocked. Sudo alone never grants authority.

## Procedure

1. **Mandatory TDD for every bugfix.** Before changing production source, write and run a focused regression that fails for the reported behavior. Record the exact failing command and its Red result, then rerun it Green after the smallest fix. A live/black-box failure is additional consumer evidence, never a substitute for this regression.
2. Search the reusable code map for the symptom, consumer, and prior
   `failure-shield` entries. Check freshness and verify decisive locations with
   targeted `rg`.
3. Reproduce the real failure with the focused Red regression and, when the
   claim is user-facing, the cheapest safe consumer canary.
4. Trace the failing consumer path and reject nearby but unused adapters or
   fixtures.
5. Change the smallest coherent source slice that makes the same proof green.
6. If the root cause or false route is likely to recur, resolve
   `../worker-research/scripts/code_map.py` from this skill and upsert a compact
   `failure-shield` entry with verified locations and the discriminating probe.
   Replace or remove knowledge invalidated by the fix.
7. Stop when the accepted behavior claim is proven.

Ask Lead non-blockingly instead of guessing when product intent, accepted
fallback, data migration, blast radius, or proof strength changes the fix.
Continue only answer-independent work while waiting.

## Test length

Keep the regression fast. It is unit level: no external service, no network, no
long-running integration, seconds to run. It belongs to the ordinary test run.

Long proofs — integration, end-to-end, real services — belong to the nightly
suite. Write them when the defect needs that coverage, but never let a slow test
stand in for the fast regression.

Reuse an existing regression or a real canary only when it already proves the
same behavior and is itself fast and repeatable. Otherwise write the new unit
test.

## Do not

- Do not widen the fix into cleanup, abstraction, security hardening, logging,
  compatibility, or exhaustive edge cases.
- Do not write a fake-contract test that asserts the mock instead of the
  reported behavior.
- Do not skip the fast RED regression because a real consumer probe looks
  cheaper; the probe is additional evidence, never a substitute.
- Do not claim production or UI recovery from source tests alone.
- Do not keep retrying after two failed hypotheses; report evidence and the
  shortest changed route to Lead.
