---
name: bugfix-tdd
description: Compatibility alias for older LHC assignments that request bugfix TDD. Prefer worker-bugfix for new Worker defect tasks; use this only when an existing task or caller explicitly names bugfix-tdd.
---

# Bugfix red/green

For new assignments, load `worker-bugfix`; it supersedes this compact alias with
reusable failure-shield and `rg` guidance.

Use for a bounded behavior failure where a discriminating failing proof is worth
its setup cost.

## Procedure

1. Trace the real failing consumer path.
2. Capture the smallest safe failing regression, existing check, or black-box
   canary that distinguishes the symptom.
3. Implement the smallest coherent fix on that path.
4. Re-run the same proof and proportional direct-regression checks.
5. Stop when the accepted claim is proven.
6. Ask Lead instead of guessing at a context-dependent business decision; use a
   non-blocking parent transport and continue answer-independent work when
   available.

## Do not

- Do not write a new unit test when an existing or real canary is cheaper and
  stronger.
- Do not widen the fix into hardening, cleanup, abstraction, or edge-case work.
- Do not claim a user-facing result from a build alone.
