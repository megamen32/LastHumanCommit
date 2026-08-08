# Hermes adapter instructions

The plugin uses Hermes' public `tool_request` middleware. Prefix a delegated goal
with `[LHC_ROLE=<role>]`; the middleware adds that complete canonical role before
Hermes builds the child. Hermes' native `leaf/orchestrator` role remains
independent.

Before every delegated goal, load `templates/subagent.md` for the role prefix,
compact assignment, assigned task-file boundary, and cheapest-sufficient model
rules.

For ordinary missing information use AskHuman. For a secret or password use
AskSecret/SSS only when attested; require opaque registered-agent handoff and
reject plaintext or base64 fallback.

The plugin reads the explicit LHC marker and role source but never edits project
instructions. Missing or unknown roles remain untouched. Hermes owns self-
improvement natively; do not add the LHC retrospective loop here.
