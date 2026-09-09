---
name: worker-bugfix
description: Worker-owned least-cost bug-fixing procedure for one bounded behavior failure. Use when a symptom, regression, broken business flow, failing test, or production-path defect must be reproduced, localized, and fixed. Reuse prior failure shields, prefer rg for fresh source tracing, choose the cheapest discriminating red proof, make the smallest coherent fix, and preserve a reusable root-cause map entry when recurrence is likely.
---

# Worker Bugfix

Fix one proven failure without turning it into a hardening project.

## Procedure

1. Search the reusable code map for the symptom, consumer, and prior
   `failure-shield` entries. Check freshness and verify decisive locations with
   targeted `rg`.
2. Reproduce the real failure with the cheapest discriminating proof: an
   existing check, focused regression, protocol probe, or black-box canary.
   Write a new unit test only when it is the cheapest strong red proof.
3. Trace the failing consumer path and reject nearby but unused adapters or
   fixtures.
4. Change the smallest coherent source slice that makes the same proof green.
5. Re-run that proof and only proportional direct-regression checks.
6. If the root cause or false route is likely to recur, resolve
   `../worker-research/scripts/code_map.py` from this skill and upsert a compact
   `failure-shield` entry with verified locations and the discriminating probe.
   Replace or remove knowledge invalidated by the fix.
7. Stop when the accepted behavior claim is proven.

Ask Lead non-blockingly instead of guessing when product intent, accepted
fallback, data migration, blast radius, or proof strength changes the fix.
Continue only answer-independent work while waiting.

## Do not

- Do not widen the fix into cleanup, abstraction, security hardening, logging,
  compatibility, or exhaustive edge cases.
- Do not create a fake-contract test when a real consumer probe is cheaper and
  stronger.
- Do not claim production or UI recovery from source tests alone.
- Do not keep retrying after two failed hypotheses; report evidence and the
  shortest changed route to Lead.
