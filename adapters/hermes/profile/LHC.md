# Hermes LHC profile

Current Fleet-facing profile bundle.

This file intentionally mirrors `LHC.v1.md` so the current profile name can be
stable while the versioned bundle remains explicit. Use this profile to create
the Hermes profile `LHC` without changing Hermes source code or runtime files.

The profile:
- preserves Hermes identity and the adapter delegation overlay;
- disables native `clarify` for this profile;
- replaces it with AskHuman for ordinary user questions;
- uses AskSecret/SSS for secret requests;
- substitutes LHC Ask Secret semantics for secret requests when attested;
- keeps unknown roles untouched; and
- remains additive to the existing Hermes plugin behavior.

For the normative bundle content, see `LHC.v1.md`.
