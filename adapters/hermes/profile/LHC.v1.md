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
- Use AskHuman for ordinary questions that require the user's decision or
  missing information.
- Use LHC Ask Secret semantics through AskSecret/SSS for a missing secret or
  password; never use AskHuman for secret delivery.
- Ask Secret means a named secret request with opaque handling only; do not
  surface plaintext, token values, storage details, or delivery mechanics.
- If Fleet cannot attest the Ask Secret capability, treat it as unavailable
  rather than simulating it.

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
