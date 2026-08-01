# Hermes adapter instructions

The plugin uses Hermes' public `tool_request` middleware. Prefix a delegated
goal with `[LHC_ROLE=<role>]`; the middleware adds that complete canonical role
to the child context before Hermes builds the child. Hermes' native
`leaf/orchestrator` role remains independent.

The plugin reads the explicit Last Human Commit marker block and role source but
never edits project instructions. A missing or unknown role is left untouched
so Hermes retains its normal behavior.

Hermes owns self-improvement natively: it reviews memory/skills after selected
completed turns and exposes `/learn` for reusable successful workflows. Do not
add the LHC `SELF_IMPROVE.md` record here.
