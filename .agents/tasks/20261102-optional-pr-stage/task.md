# Optional PR stage (LHC 1.7.22)

Owner request: PR stage on/off at build/config time; user installation off. No Codex/Work sessions.

- [x] Confirmed source megamen32/LastHumanCommit; origin/main 809cff9 (v1.7.21); isolated task worktree and branch.
- [x] Herder workspace owners for main/publish/PR/adoption paths returned empty; global session inventory partial. Preserve other work.
- [x] Add pr_stage switch in existing package publication/config path, with safe default on.
- [x] PR off: clean isolated task branch and verified remote HEAD still mandatory; PR URL not mandatory; final merge, review, tests, deploy and consumer proof still mandatory.
- [x] Offline tests both modes, source/generated protocol and manifest parity, reviewer check.
- [x] Commit/push; integrated v1.7.22 into main without PR as 54e0399 (host rules allowed).
- [ ] Build/install into intended current user environment with release guard and effective-config readback; report exact blocker if unavailable.

Owned paths: scripts/publish_package.py; src/common/config/workflow.json;
src/common/tools/lhc_worktree.py; AGENTS.md and delivery protocols;
matching generated package files; scoped tests and plugin version manifests.
Do not touch broker/proxy/consumer lifecycle, unrelated WIP or old PRs.

Checkpoint: v1.7.22 source and build config; 697 passed/6 skipped full offline suite; no Codex/Work sessions. Production install pending final merge and Herder release lease.

## Required addition: bug registry (same owner, 2026-11-02)
- [x] Source/ownership continuity: existing task worktree fast-forwarded to merged v1.7.22; no extra writer.
- [x] Existing issue-like persistence: canonical plan CLI file_lock and _write_atomic, immutable leaf creation/progress history/sha256. No preexisting standalone bug register found in this source.
- [x] RED regression: register/read/update/resolve; concurrency; immutable history; evidence for fixed; reasons for duplicate/false-positive; unresolved gate; shipped stdio MCP.
- [x] GREEN implementation: canonical local-file bug registry CLI using existing atomic primitives, exposed by the same LhcPlan MCP (no second service/database).
- [x] Document zero-baseline-exemption and last-worker all-tests-green contract for every role/hook.
- [ ] Full offline validation; review; new logical commit/version; push; authorized merge without PR when host permits.
- [ ] Verified effective installed config and native package; if Herder release gate remains denied, report blocker without bypass.

Checkpoint 1.7.23: unified LhcPlan bug_register/get/list/update/resolve/check,
file-backed records plus append-only journal and optimistic sha256. Five real
regression failures were registered, then resolved with retained full-suite
evidence; bug_check => 5 total, 0 unresolved. Full offline validation:
713 passed, 6 existing conditional skips; source/package parity PASS.
No live Codex/Work session was created. Runtime install remains gated
by registered Herder's unresolved ownership check; do not bypass it.
