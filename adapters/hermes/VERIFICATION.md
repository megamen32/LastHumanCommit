# Hermes adapter verification

Verified on 2026-07-31 against the Hermes checkout on
`roomhacker-server-100` without modifying Hermes source or user project files.

- `last-human-commit` is enabled in `~/.hermes/config.yaml`.
- A fresh Hermes plugin discovery loaded the user plugin and registered one
  `tool_request` middleware.
- A `delegate_task` smoke payload with `[LHC_ROLE=worker]` was rewritten before
  dispatch and contained the complete Worker role plus the Hermes overlay.
- A non-delegation tool payload was unchanged.
- The plugin source and installed user-plugin files matched by SHA-256.

This proves plugin loading and middleware composition. It does not claim a
live child model, provider, or resume transport; those remain adapter-dependent
until an end-to-end child event is recorded.

## Native self-improve boundary

Also inspected on 2026-07-31, without changing Hermes: after a successful,
uninterrupted response, `agent/turn_finalizer.py` conditionally starts its
background memory/skill review after delivering the response. Hermes' `/learn`
path turns an explicitly named successful workflow into one `SKILL.md`; its
skill manager asks to create after complex or corrected work, patch stale
instructions/pitfalls, and confirm creation or deletion with the user. LHC
therefore records `self_improve: hermes-native` and deliberately does not add a
second retrospective log there.
