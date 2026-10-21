---
name: bugfix-tdd
description: Compatibility alias for older LHC assignments that request bugfix TDD. Prefer worker-bugfix for new Worker defect tasks; use this only when an existing task or caller explicitly names bugfix-tdd.
---

# Bugfix red/green

For new assignments, load `worker-bugfix`; it supersedes this compact alias with
reusable failure-shield and `rg` guidance. `worker-bugfix` is the canonical
procedure for a defect.

Use for a bounded behavior failure where a discriminating failing proof is worth
its setup cost.

## Procedure

1. Trace the real failing consumer path.
2. Write and run the smallest safe failing regression for the reported behavior
   before production code changes. It is mandatory: write a new fast unit test
   unless an existing regression or a real canary already proves the same
   behavior. Keep it unit level and fast; long integration and end-to-end
   proofs belong to the nightly run.
3. Implement the smallest coherent fix on that path.
4. Re-run the same proof and proportional direct-regression checks.
5. Stop when the accepted claim is proven.
6. Ask Lead instead of guessing at a context-dependent business decision; use a
   non-blocking parent transport and continue answer-independent work when
   available.

## Do not

- Do not skip the RED regression because a real consumer probe looks cheaper;
  the probe is additional evidence, never a substitute.
- Do not widen the fix into hardening, cleanup, abstraction, or edge-case work.
- Do not claim a user-facing result from a build alone.
