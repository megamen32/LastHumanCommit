# Hermes adapter instructions

The plugin uses Hermes' public `tool_request` middleware. Prefix a delegated
goal with `[LHC_ROLE=<role>]`; the middleware adds that complete canonical role
to the child context before Hermes builds the child. Hermes' native
`leaf/orchestrator` role remains independent.

The plugin reads the explicit LastHumanCommit marker block and role source but
never edits project instructions. A missing or unknown role is left untouched
so Hermes retains its normal behavior.
