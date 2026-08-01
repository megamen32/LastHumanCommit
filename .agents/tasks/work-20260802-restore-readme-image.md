# Restore README image

> «верни картику»

## Objective

Restore the original Last Human Commit role-map image directly below the
`README.md` title.

## Business canary

The current README contains the original `<img>` element and its GitHub-hosted
asset returns a successful HTTP response.

## Confirmed scope

- restore the exact image URL and descriptive alt text from the last known-good
  README revision;
- preserve all current README prose and installation instructions;
- commit only the README and this task's required LHC records.

## Explicit exclusions

- do not rewrite or reorganize the README;
- do not touch `graphify-out/` or unrelated files;
- do not audit unrelated technical surfaces.

## Cycle and estimate

- Cycle: Direct; this is one known, reversible documentation regression.
- Optimistic: 2 active minutes.
- Likely: 5 active minutes.
- Pessimistic: 10 active minutes.

## State

Status: publication pending

## Pre-publication result

- Restored the exact original image element below the current title while
  preserving all other README content.
- The asset returns HTTP 200 as `image/png` with a 1,700,584-byte body.
- `git diff --check` passes.
- `tests/validate.py` passes all 7 router and marker-block contracts.
- `tests/test_block_adapter.sh` passes.
- Hermes plugin regression suite passes: 4 tests.
