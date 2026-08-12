---
name: real-use-testing
description: Optional claim-calibrated black-box procedure for proving a real user-facing result.
---

# Real Use Testing

Use when the accepted user-facing claim still needs real-surface proof and the
test's expected value exceeds its cost.

## Procedure

1. Start from the accepted claim, target surface, allowed actions, and stop
   conditions.
2. Run the shortest actual user journey without source-based shortcuts.
3. Capture evidence appropriate to that claim and surface.
4. Report claim blockers and material direct regressions only.

## Do not

- Do not make two Testers, blindness, screenshots, or video ceremonial defaults.
- Do not replace real-user evidence with unit tests or logs for a stronger claim.
- Do not raise the accepted Definition of Done while testing it.
