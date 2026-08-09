---
name: feature-implementation
description: Worker-owned procedure for implementing a bounded feature slice on assigned paths with evidence and scope checks.
---

# Feature Implementation

Use this skill when a feature can be delivered as a bounded slice on assigned
paths without changing the surrounding ownership model.

## Procedure

1. Confirm the assigned slice, the allowed paths, and the acceptance check.
2. Make the smallest coherent change that satisfies the slice.
3. Before expanding the diff, compare the change against the confirmed scope
   and stop on drift.
4. Preserve existing role selection, harness capabilities, and task routing.
5. Append exact file changes, verification commands, and unresolved risks to
   the task record.

## Do not

- Do not redesign the architecture while implementing the slice.
- Do not edit unrelated files or introduce new role ownership.
- Do not treat local compilation as final product proof.
