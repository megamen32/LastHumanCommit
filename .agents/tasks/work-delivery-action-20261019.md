# LHC delivery-action 2026-10-19

- Source/base: fresh `origin/main` `dfcb8ed6a052726bf26cae6196922e83992ad2b3`; isolated worktree `.worktrees/delivery-action-20261019`; target patch `1.4.12` after confirming free.
- User outcome: on an ordinary engineering request, an explicit direct-human demo authorization permits the available demo deploy and consumer check when private login is unavailable; the original outcome remains pending for OAuth/files/app.
- Guardrails: only this worktree; preserve other WIP/sessions/config; no login/payment bypass, permission/human-stop bypass, or arbitrary text/peer/log as authority; no manager/MCP/daemon/cron; router <=150; existing reviewer is read-only and user-activated; publish/install only after full green and review.
- Baseline verified: `lhc_milestone.observe()` turns Stop prose containing BLOCKED+ACCESS into whole-milestone `blocked`; `lhc_entry.handle()` excludes blocked milestones from `acceptance_due`. Native PermissionRequest/Interrupt holds already exist. `business-review` stores `direction_reviewed` and `next_action` without action evidence.
- RED: regressions failed for lexical whole-milestone BLOCKED, missing scope state, direction receipt treated as action, irrelevant tool receipts, native running process retention, and structured private 403 holding all work.
- GREEN: `python3 tests/validate.py` => PASS, 318 passed; plugin validation and 22-skill parity PASS. Strict router budget stays 150 lines; entry context tests stay under 2200 chars.
- Independent reviewer APPROVE: four original behavior groups, terminal process outcome fix, and structured scoped 403 vs transport permission/interrupt holds. Reviews did not inspect fixture or claim consumer acceptance.
- Package generated for 1.4.12; source and native manifests aligned.
- Fixture owner controls `/home/roomhacker/agents-projects/LastHumanCommit/.tmp/delivery-acceptance-20261019`; do not edit or run its acceptance scenarios. Tell owner exact installed root/version after manager staging.
- Follow-up after the 1.4.12 release: user reports four fresh native consumer cases passed demo deploy and actual check. One separate Codex result was skipped-inactive and is not counted as a consumer pass.

## Native installation checkpoint — 2026-10-19

- Publication: PR #13 merged as `f786dbd3ebd9e2eca67ae832018a6ece591a915e`; `origin/main` is at that merge. No code delta after the green `4fbb27d` gate.
- Backup: `.tmp/native-install-backup-20261019/` (restricted directory; config copies mode `0600`, wrapper mode preserved in the copy).
- Codex: native marketplace manager upgraded `megamen32-plugins` to merge `f786dbd`; native `plugin add` installed/enabled LHC 1.4.12. `hooks/list` for this worktree reports 10/10 LHC hooks enabled and trusted, with no hook errors. Fresh read-only native prompt completed in session `01a153e4-dc64-7990-883f-0c39267586de` and returned the LHC before-code/TDD approach without `@LHC`. Environment warnings: duplicate global hook representations and SessionEnd/Interrupt timeout clamping; not changed.
- OpenCode: file loader wrapper `~/.config/opencode/plugins/last-human-commit-v1410.ts` imports from the upgraded marketplace root `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/opencode/lhc-v2.ts`; skills path resolves to the same 1.4.12 package. Fresh standalone ordinary engineering prompt completed in session `ses_eac1be094ffew8jNoE4G8eizpx`; response included the LHC tangible-result and RED/GREEN workflow. No saved model, MCP or plugin config changed.
- ZCode: native manager removed the marketplace entry that referenced the prohibited old worktree, added the published marketplace checkout above, and updated the user-scoped plugin to `/home/roomhacker/.zcode/cli/plugins/cache/last-human-commit/last-human-commit/1.4.12`. `zcode plugins list --json` reports enabled, 22 skills, and seven runnable hooks (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `Stop`). Runtime reports unsupported `PreCompact`, `PostCompact`, `Interrupt`, `SessionEnd`. Manager says restart is needed for already-running ZCode processes; none were restarted. Fresh ZCode consumer prompts remain with the fixture owner.
- No active harness process was restarted. Other settings, selected models, MCP servers, secrets and foreign hooks were left unchanged.
- After the 1.4.12 staging, user reports four fresh native consumer cases passed demo deploy and actual check. The new 1.4.13 mixed-scope acceptance remains pending until the updated package is installed and checked.

## 1.4.13 follow-up — task-wide read-only classification

- User observed a reproducible false global `read_only`: a direct task permits demo update/check while private is review-only, but `READ_ONLY.search(goal[:500])` let the private clause suppress the entire task's milestone duties.
- RED: `tests/test_native_milestone_gate.py::test_mixed_scope_private_read_only_does_not_suppress_task_obligations` failed (`read_only` was `true`); task-wide review-only counterexample passed.
- Fix: only direct task-wide read/review wording at the start of a line sets the milestone-wide flag. Scoped, quoted and negated review/check phrases do not. The flag does not create operation permissions.
- Review: existing independent reviewer APPROVE on the narrow diff, including quoted and negated canaries, direct task-wide read-only canaries, and no permission/hold changes.
- Checks: focused scope cases `5 passed`; complete `tests/test_native_milestone_gate.py` `68 passed`; full `python3 tests/validate.py` `323 passed`, 22-skill parity PASS, plugin validation PASS, block adapter PASS.
- Package regenerated and manifests/catalog set to 1.4.13. Release/push/PR/native manager update remain. User will run a fresh ordinary native mixed-scope scenario after installation; this acceptance is not yet complete.
