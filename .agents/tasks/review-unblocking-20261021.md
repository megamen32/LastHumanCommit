# Remove internal LHC review-registration delivery blockage

Direct user approval: remove the contradictory review/manifest blockage; Overseer accelerates the original business outcome and helps remove pointless blockers, never becomes another release gate.

Clock anchor (recorded after intake): 2026-10-21T06:40:24.976430+00:00; original human-message start/active intervals not measured. Initial remaining estimate: 15–25 minutes for instruction repair, bounded review and native rollout.

Plan: Luna owns canonical instruction/reminder-text repair and generated1.5.19 package; Lead reviews, publishes owned paths and installs. Source editing and read-only delivery preparation proceed in parallel. Product permissions, HumanStop, actual uncovered defects, negative findings and UNKNOWN actions remain protected. Existing strict ledger can remain pending without vetoing authorized product delivery. No product replay, fake PASS, transcript fabrication or routine human appointment of reviewers.

Current: source repair in progress. Foreign untracked records preserved; no tests/full suite scheduled.

## Delivery-owner update — 2026-10-21 06:48 UTC

Read-only preparation confirmed the LHC checkout and remote `main` were both at `fd81b9c385b665a9cf8b480ba9131b6654edfda4`, with the release worker's unpublished 92-path change set. Fleet checkout and remote `main` were both at `378dc31362569e7dee1677fbba056d48e938910f`; unrelated Fleet untracked work remains untouched. The approved rollout CLI is available as `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m harness_fleet.plugin_rollout`.

The frozen LHC diff is 92 tracked paths and matches `ee8e6d6b95c57cb11c71676c20b7e566c96beb01e05c2649b38287e732f39aa3`; `git diff --check` passes. Independent review of this exact candidate is pending. No source paths have been staged or committed, and no publication or install has been run for 1.5.19.

## Source freeze update — 2026-10-21 06:51 UTC

The source worker made a reviewed-scope legacy-text correction and issued a new freeze. The earlier 92-path SHA is superseded. Current candidate is 115 tracked paths at base `fd81b9c385b665a9cf8b480ba9131b6654edfda4`, diff SHA `76a041169e95294b824761c5176ff604d55c1787f6e31b2e167de4e2819d179c`. Local read-only verification matches the count and SHA; `git diff --check` passes. Independent review of this current candidate is pending. No source path has been staged or committed.

## Source freeze reconciliation — 2026-10-21 06:52 UTC

The source worker reports a regenerated current diff with the same 115 paths. Recomputed locally: SHA `94980a33dae4cbec927c2aee9151d2e5d363e3cf31c9593f779aabdd287da2d7`; `git diff --check` passes. This supersedes the prior `76a041…` snapshot; wait for independent approval of `94980a…` before commit.

## Final candidate recheck — 2026-10-21 06:54 UTC

A small FULL_CYCLE wording adjustment followed the two-file review delta. Current tracked diff remains 118 paths; locally verified SHA is `1611b9aef282952ef6e1d7a54229bf4c708e2c44ad81553c5927fd822f1b2b1e`, matching the source worker's report. `git diff --check` passes. Independent review is still rechecking this exact phrase; publication remains pending that result.

## Scoped publication — 2026-10-21 06:55 UTC

Independent source review approved exact 118-path diff `1611b9aef282952ef6e1d7a54229bf4c708e2c44ad81553c5927fd822f1b2b1e` on base `fd81b9c385b665a9cf8b480ba9131b6654edfda4`. I staged only those tracked paths, confirmed staged SHA/count matched review, and committed as `13a58bfc814f9ddfd4cc44074c253b8f0ca6a2d6` (`release: publish LHC 1.5.19 instruction repair`). `main` push succeeded; `git ls-remote` now reports the same commit and committed package metadata is 1.5.19. Untracked `.agents` work was not committed.

Next: apply the pinned published commit via existing Fleet rollout and record each runtime's native version/content/mode readback; no forced session restart.

## Delivery status and revised estimate — 2026-10-21 07:02 UTC

Initial remaining estimate at intake was 15–25 minutes. Wall elapsed from the recorded 06:40:24 UTC anchor is about 21 minutes 35 seconds; active work was not instrumented separately and is therefore unknown. Source-instruction review is APPROVED and commit `13a58bfc814f9ddfd4cc44074c253b8f0ca6a2d6` is published. The first 1.5.19 native apply is explicitly PARTIAL, not complete: OpenCode pointers updated on canonical profiles, while Codex/Hermes report the prior native metadata version because runtime-specific manifests in the package still declare 1.5.18 (Hermes extension manifest is 1.4.13). Apply receipt is preserved at Fleet `.tmp/lhc-1.5.19-rollout/apply.json`; do not replay those operations. The source and package-delivery claims remain separate.

The cause is that native entry manifest versions were not included in the approved package parity check. Source/review owners are correcting this as 1.5.20. Remaining work is bounded to: (1) verify the corrected native manifest version parity and its narrow review; (2) capture read-only current state for the canonical five physical hosts and already-proven installed profiles; (3) apply the corrected pinned package once and verify each actual runtime's version and package bytes/modes, preserving disabled Mini Hermes and recording absent binaries/unsupported profiles. Estimate: about 15 minutes per step; no full suite or product replay.

## Native-manifest correction published — 2026-10-21 07:05 UTC

The source owner prepared a metadata-only 1.5.20 delta. Independent metadata review approved its exact 12-path SHA `5e0e451ef6b7494b9af743aed53e96168e8342daccd2331e23fa3ef997682c4b`; all nine native JSON/YAML manifest entry points now assert 1.5.20, and Changelog/README versions agree. The staged SHA/count matched review. Scoped commit `5d3f0eab7916da316bb8024df7e39104223c99e7` (`release: align LHC 1.5.20 native manifests`) was pushed to `main`; `ls-remote` confirms this commit. The earlier 1.5.19 attempt remains PARTIAL and unchanged in its preserved receipt. Next: use the pinned published 1.5.20 commit, target only canonical physical hosts and previously proven installed runtime profiles, then read back actual manifest version and package bytes/modes. ZCode server-100's native file marketplace shape requires a native CLI update through its already registered LHC-only catalog; no Fleet source changes.

## Corrected 1.5.20 native rollout complete — 2026-10-21 07:17 UTC

Published source is LHC `main` commit `5d3f0eab7916da316bb8024df7e39104223c99e7`, package digest `sha256:962883146eef6cfadabb5c59b1c1620eac8c7f74f905d8ad19128b56f8f2762e`. The reviewed 1.5.20 metadata delta is in that commit. No LHC source edits were made by the delivery owner. The earlier 1.5.19 partial attempt remains preserved and was not replayed.

Canonical installed profile matrix:

- Server-100: Codex 1.5.20 enabled; Hermes 1.5.20 enabled; OpenCode instructions/skills pointer ready; ZCode `last-human-commit@fleet-lhc` 1.5.20 enabled. ZCode's older `last-human-commit@last-human-commit` 1.5.18 remains disabled.
- Server-44: Codex 1.5.20 enabled; primary OpenCode pointer ready. Hermes and ZCode binaries were absent in prior verified inventory. A second OpenCode profile had no existing LHC pointers and was left unchanged.
- Server-88: Codex 1.5.20 enabled; primary OpenCode pointer ready. Hermes and ZCode binaries were absent in prior verified inventory. A second OpenCode profile had no existing LHC pointers and was left unchanged.
- MacBook: Codex 1.5.20 enabled; Hermes 1.5.20 enabled; primary OpenCode pointer ready; ZCode `last-human-commit@fleet-lhc` 1.5.20 enabled. Older `last-human-commit@last-human-commit` 1.5.18 remains disabled. An additional Fleet OpenCode profile referenced nonexistent home/config paths and was not mutated.
- Mac Mini: Codex 1.5.20 enabled; Hermes 1.5.20 remains disabled; ZCode and OpenCode binaries/profiles were absent in prior verified inventory.

Readback evidence: Codex installed native packages on all five hosts match the pinned package's 111-file `native/codex` subtree by path, bytes, and mode. ZCode active LHC packages on server-100 and Mac match all 244 pinned package files by path, bytes, and mode. Hermes 244-file packages on Mac and Mini match path, bytes, and mode; server-100 Hermes bytes match and the native manager tightened file permissions from 0644/0755 to 0600/0700. OpenCode's existing configs on 100/44/88/Mac point to the pinned digest path for both AGENTS.md and skills; rollout readback reports ready. OpenCode `sessionLoaded` was not verified, and no session was restarted.

The Mac ZCode list command exits 1 because two pre-existing unrelated `megamen32-plugins` entries lack manifests (`ask-human`, `ask-secret`); its JSON still reports the selected LHC plugin at 1.5.20 enabled, and the package readback passed. Those unrelated plugins were not modified. Per-host apply receipts and the 100 ZCode catalog backup are in Fleet `.tmp/lhc-1.5.20-rollout/`. The Mac ZCode catalog backup is under its Fleet rollout backup directory. Foreign untracked `.agents`, Fleet registry, and NoticePlace package state were preserved; only the existing LHC-only `fleet-lhc` ZCode catalogs were updated. No product replay, tests, full suite, forced restart, or binary installation was performed.

Time: original recorded estimate was 15–25 minutes; wall time from the 06:40:24 UTC intake anchor is about 36 minutes 40 seconds. Active work time was not separately measured. Delay was caused by the first package's runtime manifest version mismatch, requiring the source owner to publish and review the metadata-only 1.5.20 correction. Delivery is complete; remaining limitation is that existing active OpenCode sessions were not restarted or proven to have loaded the new pointers.
