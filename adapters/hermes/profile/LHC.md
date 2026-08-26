# Hermes LHC profile

Current Fleet-facing profile bundle.

This file intentionally mirrors `LHC.v1.md` so the current profile name can be
stable while the versioned bundle remains explicit. Use this profile to create
the Hermes profile `LHC` without changing Hermes source code or runtime files.

The profile:
- preserves Hermes identity and the adapter delegation overlay;
- disables native `clarify` for this profile;
- replaces it with one compact direct question for ordinary user decisions;
- reads secrets directly from an environment variable, `.env`, or a secret file
  in one step (Secrets are not work);
- keeps unknown roles untouched; and
- remains additive to the existing Hermes plugin behavior.

For the normative bundle content, see `LHC.v1.md`.
