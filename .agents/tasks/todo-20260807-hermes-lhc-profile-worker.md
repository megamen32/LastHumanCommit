Role: Worker

# Worker: LHC Hermes profile bundle

Status: todo
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-07 19:15:55 +0300 (last write observed, not start)

Goal: implement only the committed LastHumanCommit-side Hermes profile/native
instruction bundle needed for Fleet to create profile `LHC`, replace native
Clarify with AskHuman, and route secrets through LHC Ask Secret.

Known facts: Hermes reads `~/.hermes/SOUL.md`; current LHC plugin only rewrites
delegate_task. The profile must be separate from default. Do not edit Hermes
checkout or runtime files.

Allowed write paths: `/home/roomhacker/agents-projects/LastHumanCommit/adapters/hermes/**`,
and its focused tests/docs only. Read-only context may include the common
capability contract and existing adapter templates.

Acceptance: produce a versioned profile overlay/template with explicit
Clarify-to-AskHuman replacement and Ask Secret semantics, preserve Hermes identity and
delegation overlay, and add focused deterministic coverage. Do not invent
SSS secrets or Fleet behavior. Append detailed evidence here and return L
only TL;DR.

Excluded: Hermes source, Fleet code, runtime config, deployment, restart,
credentials, and broad Notify/resume integration.

Estimate active minutes: 10 / 20 / 35. Stop if the requested behavior cannot
be represented through the plugin/config/profile seam; report the exact gap.

Progress log:

- Read `adapters/hermes/instructions.md`, `templates/subagent.md`,
  `VERIFICATION.md`, `adapter.yaml`, `plugin/instructions.md`,
  `plugin/README.md`, `plugin/plugin.yaml`, and `plugin/tests/test_plugin.py`.
- Found the existing Hermes seam: external `tool_request` middleware preserves
  Hermes native `role: leaf|orchestrator` and already injects the resolved role
  prompt. There was no committed Hermes-side profile bundle yet.
- Added a versioned profile bundle under `adapters/hermes/profile/`:
  - `LHC.v1.md` is the normative bundle with explicit Hermes identity
    preservation, Clarify-disabled semantics, Ask Secret semantics, and the
    seam-only boundary.
  - `LHC.md` is the stable Fleet-facing profile name and points to v1.
  - `README.md` documents the bundle split.
- Updated `adapters/hermes/plugin/README.md` to mention the profile bundle.
- Added deterministic coverage in `adapters/hermes/plugin/tests/test_plugin.py`
  for the versioned profile content and the Clarify/Ask Secret wording.
- Verification:
  - `pytest -q /home/roomhacker/agents-projects/LastHumanCommit/adapters/hermes/plugin/tests/test_plugin.py`
    → `5 passed in 0.06s`
  - `git -C /home/roomhacker/agents-projects/LastHumanCommit status --short adapters/hermes .agents/tasks/todo-20260807-hermes-lhc-profile-worker.md`
    → confirms modified plugin docs/tests, the new `adapters/hermes/profile/`
    directory, and this task file are the only touched paths in scope.
- Failure encountered:
  - First test run failed because the test looked for `profile/LHC.md` under
    `plugin/profile/`. Fixed by moving the path up to the adapter directory.
  - Second test run failed because the assertion text was too exact for the
    stable profile file. Fixed by asserting the actual wording.
- Remaining risk:
  - This is a committed profile bundle only. It does not claim Hermes core has a
    native profile loader or live Ask Secret transport. If Fleet lacks a seam to
    materialize `LHC`, that gap is external to this repo and must be handled
    there.
