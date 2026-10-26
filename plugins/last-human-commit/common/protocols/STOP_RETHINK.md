# Stop and rethink

Use when the current route may no longer be the shortest way to the accepted
result.

## Triggers

- Two failed independent hypotheses on the same route.
- A leaf well over its estimate without proportional progress.
- Evidence contradicts the chosen implementation surface.
- The owner repeats that the same result still fails.
- Process, hardening or proof strength grows while the result does not move.

## Decision

1. Restate the accepted result and how it will be proven.
2. Record what moved and what it cost.
3. Pick one: continue with one credible next step; redirect the same Worker
   (cheaper than replacing it); `REDECOMPOSE`; `CHANGE_MODEL`; cut back to the
   accepted minimum; or go up the escalation chain in `AGENTS.md`
   (Adviser → Overseer).
4. Never resume the failed route by only changing the estimate or the wording.

A 20-minute Worker report is a checkpoint, not a lifetime limit. Cancel an agent
only for active harm, conflicting writes, an obsolete duplicate, the owner's word
or an unrecoverably stuck child.

When a real business question remains, ask the owner once with the blocker,
evidence, two genuinely different routes with cost, and your recommendation and
default; continue other work while waiting.
