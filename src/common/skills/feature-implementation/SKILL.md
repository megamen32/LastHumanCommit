---
name: feature-implementation
description: Compatibility alias for older LHC assignments that request feature implementation. Prefer worker-code for new Worker coding tasks; use this only when an existing task or caller explicitly names feature-implementation.
---

# Feature Implementation

For new assignments, load `worker-code`; it supersedes this compact alias with
reusable research-map and `rg` guidance. `worker-code` is canonical for
implementation work, including its defect rule: a defect repair needs the fast
RED regression from `worker-bugfix` before production code changes.

Use for a coherent vertical feature contribution assigned to a Worker. The Lead
coordinates and does not execute the implementation.

## Procedure

1. Confirm the accepted outcome, actual production path, allowed scope, and
   shortest acceptance check.
2. Reuse the existing mechanism and implement the thinnest usable vertical.
3. Run the real canary early, then fix only the first claim-blocking failure.
4. Add only proportional direct-regression evidence.
5. At each 20-minute checkpoint report business delta and remain available for
   continuation or redirection.
6. Ask Lead at every context-dependent decision boundary with evidence,
   recommendation/default, parallel-safe work, and the exact blocked action;
   continue safe work through a non-blocking parent transport when available.

## Do not

- Do not implement horizontal completeness before the first usable path.
- Do not redesign architecture or add unrelated hardening.
- Do not treat local compilation as final product proof.
