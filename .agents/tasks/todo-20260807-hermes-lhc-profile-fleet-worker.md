Role: Worker

# Worker: Fleet Hermes LHC profile rollout

Status: todo
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-07 19:22:29 +0300 (last write observed, not start)

Goal: implement the Fleet rollout operation that clones the Hermes default
profile into a separate `LHC` profile, applies the committed LHC profile
overlay and SSS MCP configuration, and leaves default untouched.

Known facts: current manifest copies only the Hermes plugin. Hermes native
profile is `~/.hermes/profiles/<name>/`; no auth/session/secret stores may be
copied. Runtime source policy forbids Hermes core edits.

Allowed write paths: `/home/roomhacker/agents-projects/agent-harness-fleet/catalog/skills/lhc-rollout/**`
and focused tests for that rollout script only. Read LHC adapter manifest and
templates as needed, but do not edit LastHumanCommit.

Acceptance: manifest/schema and rollout code can preview/apply a profile clone
and overlay deterministically; preview states exact files and preserves a
freshness/approval boundary; tests cover default preservation and exclusion of
auth/session/secret material. Do not deploy or restart. Append evidence here
and return L only TL;DR.

Excluded: Hermes source, live home files, SSS server changes, credentials,
Notify/resume orchestration, and unrelated Fleet resources.

Estimate active minutes: 15 / 30 / 50. Stop on unsupported manifest semantics
and report the smallest required schema extension.

## L integration evidence (2026-08-07)

The Worker was stopped after a partial implementation because its manifest
entry and profile-only change detection were incomplete. L completed the
bounded Fleet scope in the same files:

- `lhc_rollout.py` now supports profile clone/apply/verify, explicit sensitive
  exclusions, append SOUL overlays, and recursive YAML config merges.
- The manifest packages `LHC.v1.md` and `lhc-config.yaml`, and applies the LHC
  profile to every target that already copies the Hermes plugin.
- The profile source is the real Hermes default home `.hermes`, not the
  nonexistent `.hermes/profiles/default`; runtime/auth/session material is
  explicitly excluded.
- The overlay disables native `clarify`, enables Agent Herder AskHuman seam,
  and adds the authenticated SSS MCP entry without embedding a token.

Focused evidence: `test_profile_rollout.py` passes 3 tests, including default
preservation, sensitive exclusion, manifest wiring, and YAML merge preservation.
