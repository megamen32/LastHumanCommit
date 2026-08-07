# Worker implementation protocol

Use only for `Worker(mode=implement)`. Load `../profiles/Code.md` for code
changes and `../profiles/Test.md` when designing or changing tests.

The assignment names one subtype.

## Bugfix / TDD

1. Reproduce the real reported symptom or establish the exact failing condition.
2. Trace the smallest root cause inside assigned scope.
3. Make the smallest coherent fix.
4. Repeat the same failing check and prove it is now green.
5. Run the assigned business canary and focused direct-regression checks.

A new unit test is not mandatory when the real canary or an existing check is a
better red/green proof. Never write a test merely to satisfy ceremony.

## Feature

1. Follow existing project patterns and interfaces found during research.
2. Implement the thinnest working vertical slice of the selected plan/stage.
3. Add the smallest tests that prove new behavior or protect an obvious
   regression.
4. Run the assigned business canary and focused direct-regression checks.

## Common rules

- Stay inside assigned paths, stage, and acceptance gate.
- Do not add unrelated refactors, cleanup, hardening, dashboards, migrations, or
  abstractions.
- If implementation exposes an unknown interface, architecture decision, or
  package above 20 minutes, stop and return to research via `NEEDS_RETHINK`.
- A local test alone is not user-outcome proof when a real canary is available.
- Stop as soon as the assigned canary is proven.
