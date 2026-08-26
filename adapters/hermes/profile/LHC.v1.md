# Hermes LHC profile v1

This profile is the committed Last Human Commit-side bundle for the Hermes
surface. Fleet may materialize it as profile `LHC` without changing Hermes
source or runtime files.

## Identity

- Preserve Hermes native identity and its `role: leaf|orchestrator` behavior.
- Preserve the adapter's delegated `tool_request` rewrite overlay.
- Do not change project-owned instruction files outside the adapter seam.

## Clarify replacement

- Hermes' native `clarify` tool is disabled for this profile.
- Ask the user one compact question directly for ordinary missing decisions or
  information.
- Secrets are not work: read a missing secret or password directly from an
  environment variable, `.env`, or a secret file in one step; never build
  secret handoff infrastructure or refuse an env read.

## Delegation

- Child tasks still use `[LHC_ROLE=<role>]` tagging.
- The Hermes overlay must still prepend the complete resolved role prompt and
  the Hermes adapter instructions before dispatch.
- Unknown or missing roles remain untouched.

## Boundary

- This bundle is additive. It does not claim Hermes core support for a native
  profile loader or a changed runtime transport.
- If a requested behavior cannot be represented through the plugin/profile
  seam, stop and report the exact gap.
