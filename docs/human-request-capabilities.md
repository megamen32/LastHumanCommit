# Human request capabilities policy

This document defines the portable LastHumanCommit boundary for agent-facing
AskHuman / Ask Secret behavior. It describes instruction semantics only; it does
not define runtime installation, transport, or secret storage.

NoticePlace is the canonical human-request capability for LHC. When its live
adapter is available, `response_stop` must deliver the waiting-state notice
through NoticePlace rather than merely printing a question in the transcript.
The portable contract does not claim installation or transport; if NoticePlace
is not attested, agents must report it unavailable.

## Boundary

- LHC owns portable instructions, task flow, and role-bound policy text.
- Fleet owns capability resolution, installation, transport, and attestation.
- LHC must not own SSS secret values, Notify timing, or session resumption.
- LHC must not replace NoticePlace with an untracked chat question or a second
  notification path.

## Rendering rule

Render a capability to agents only when both conditions are true:

1. The capability descriptor includes the fragment.
2. Fleet attests that the fragment is present in the live runtime.

Do not render a fragment because it is documented, proposed, or expected later.
Do not render install hints or capability placeholders as if they were live
behavior.

## Required and optional behavior

- Required fragments define the minimum contract for the capability to count as
  available.
- Optional fragments may be exposed only when attested, and only if their
  absence still leaves a valid degraded path.
- If a required fragment is missing, the capability is unavailable and must not
  be presented as usable.

## Operating note

This policy is intentionally narrow: it tells agents what to trust, what to
render, and what not to attribute to LHC. Any implementation detail that depends
on SSS values, Notify scheduling, or session resume state belongs in Fleet or
another runtime owner, not in this document.
