# Optional PR stage (LHC 1.7.22)

Owner request: PR stage on/off at build/config time; user installation off. No Codex/Work sessions.

- [x] Confirmed source megamen32/LastHumanCommit; origin/main 809cff9 (v1.7.21); isolated task worktree and branch.
- [x] Herder workspace owners for main/publish/PR/adoption paths returned empty; global session inventory partial. Preserve other work.
- [x] Add pr_stage switch in existing package publication/config path, with safe default on.
- [ ] PR off: clean isolated task branch and verified remote HEAD still mandatory; PR URL not mandatory; final merge, review, tests, deploy and consumer proof still mandatory.
- [x] Offline tests both modes, source/generated protocol and manifest parity, reviewer check.
- [ ] Commit/push; integrate into permitted main without PR only if host gates permit; record SHA.
- [ ] Build/install into intended current user environment with release guard and effective-config readback; report exact blocker if unavailable.

Owned paths: scripts/publish_package.py; src/common/config/workflow.json;
src/common/tools/lhc_worktree.py; AGENTS.md and delivery protocols;
matching generated package files; scoped tests and plugin version manifests.
Do not touch broker/proxy/consumer lifecycle, unrelated WIP or old PRs.

Checkpoint: v1.7.22 source and build config; 697 passed/6 skipped full offline suite; no Codex/Work sessions. Production install pending final merge and Herder release lease.
