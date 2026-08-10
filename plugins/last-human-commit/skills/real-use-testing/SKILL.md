---
name: real-use-testing
description: Tester-owned black-box procedure for proving the user-facing result on the real surface with fresh context.
---

# Real Use Testing

Use this skill for the final black-box gate that checks the user-visible result
on the real product surface.

## Procedure

1. Start from the accepted implementation and choose the smallest real surface
   that exercises the outcome.
2. Run the check as a fresh, black-box flow without reading source or relying
   on synthetic internals.
3. Capture the exact observed result, the acceptance decision, and the
   evidence needed to reproduce the run.
4. If the real surface is missing or unusable, stop and report that boundary
   instead of substituting a weaker proxy.

## Do not

- Do not implement fixes.
- Do not replace real-user evidence with unit tests or logs alone.
- Do not inspect source to explain away a failing surface.
