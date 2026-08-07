# Hermes profile bundle

This is the Hermes-side LHC profile content. Fleet rollout is a separate
installation adapter: it consumes this bundle and materializes the profile on
the target host; it does not become part of the Hermes adapter or change Hermes
source code.

The files in this directory define the committed Last Human Commit-side Hermes
profile bundle for Fleet.

- `LHC.v1.md` is the versioned normative bundle.
- `LHC.md` is the current stable profile name and points at the versioned
  bundle.

Both files stay inside the adapter seam and avoid Hermes source or runtime
edits.
