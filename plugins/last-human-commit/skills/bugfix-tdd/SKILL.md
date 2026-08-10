---
name: bugfix-tdd
description: Worker-owned bugfix procedure that starts with a focused failing regression or black-box canary and ends with a verified fix.
---

# Bugfix TDD

Use this skill for a narrow behavior bug where the fix must be proven against a
focused failing check before the code changes land.

## Procedure

1. Identify the smallest reproducible symptom and capture the expected
   behavior.
2. Write or run one focused failing regression, black-box canary, or equivalent
   proof of failure for that symptom.
3. Implement the smallest change that addresses the failure.
4. Re-run the same check and confirm it passes.
5. Record the exact changed paths, commands, results, and any remaining risk in
   the task file.

## Do not

- Do not skip the red phase unless the user explicitly asked for text-only or
  no-test work.
- Do not widen the bugfix into unrelated cleanup or feature work.
- Do not claim success from a build alone.
