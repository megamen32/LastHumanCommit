# Herder quota QUICKFIX — source candidate, 2026-10-19

Owner: Codex `01a155c7-a3a1-7d33-817f-8e7419dd152d`, server-100. Assigned worktree `/home/roomhacker/agents-projects/agent-herder/.worktrees/lhc-quota-readonly-20261019`, branch `lhc/lhc-quota-readonly-20261019`, base `11a3be0c9177a5c4b0999986a517c1c04f5f4c22`. Scoped commit **`13379b669ff1b4ad52f8a4e60b88dea11bbd187c`** pushed, remote branch SHA verified equal; draft [PR #10](https://github.com/megamen32/agent-herder/pull/10). No children/reviewers, restart, deployment or merge. Canonical Herder checkout/WIP untouched. Assigned source worktree is clean; this report is an owned untracked handoff artifact in LHC, left for its coordinator.

Result for council callers: observed MiniMax text/general zero now produces `quota_exhausted`; video allowance does not block or enable text. GLM/Codex period metadata survives the existing `model_quotas` path. Existing MiniMax launch preflight no longer spends inference to inspect quota. This is a candidate awaiting coordinator review and activation, not installed-runtime acceptance.

## Exact patch boundary

- `src/model-quota.ts`: provider-specific text mapping. MiniMax checks general or the exact text-model row; either interval/weekly zero exhausts, positive percentages in both windows report telemetry. Counts 0/0, unknown scopes, status enums alone, missing windows and malformed responses remain unknown. Numeric status enums are preserved without inferred meaning. GLM CREDIT_LIMIT/TOKENS_LIMIT drive text state; TIME_LIMIT remains visible but cannot block text. Codex checks both windows and does not treat flags alone or `allowed=false` as positive evidence. Exact safe telemetry whitelist retains GLM `number`, Codex period/reset/allowed/null windows; credential-shaped/unlisted payload keys and arbitrary provider error messages stay excluded.
- `src/web/quota-lens.ts`: retain existing flattened Codex fields and add `primary_window_seconds`, `primary_reset_at`, `secondary_window_seconds`, `secondary_reset_s`, `secondary_reset_at`, `allowed`, plus whitelisted `primary_window`/`secondary_window`. Unix seconds stay seconds; absent windows remain null. No new auth/refresh.
- `src/automation/minimax-quota-preflight.ts`: minimal Q3 adapter imports the existing shared MiniMax read-only quota function. GET `https://www.minimax.io/v1/token_plan/remains`, protected existing Bearer credential, no body; removes messages POST. Keeps exact-model guard, single in-flight slot, finite cache and deadline/abort. A reported positive snapshot maps to the pre-existing `available` telemetry value; unknown remains unknown. Controller/named-session/fallback logic untouched.
- Relevant tests only: `tests/model-quota.test.ts`, `tests/quota-lens.test.ts`, `tests/minimax-quota-preflight.test.ts`.

No new MCP, scheduler, manager, auth, model call, permission, or global setting. Snapshot is not a reservation and cannot prevent concurrent spending. Existing controller behavior allowing unknown preflight to proceed to its native admission path remains unchanged; this patch does not grant fallback or billing permissions.

## RED → GREEN evidence

Before production edits, `node_modules/.bin/vitest run tests/model-quota.test.ts` produced **3 failed / 4 passed**: observed general interval0/weekly69 misclassified reported, GLM lost number and tool-only zero blocked text, Codex secondary100 ignored. Separate preflight regression produced **1 failed / 5 passed**, showing actual messages POST versus expected read-only allowance GET. Logs `.tmp/quota-fix/red.log` and `red-preflight.log` in assigned worktree.

After patch:

```sh
npm run build
node_modules/.bin/tsc --noEmit
node_modules/.bin/vitest run tests/model-quota.test.ts tests/minimax-quota-preflight.test.ts tests/quota-lens.test.ts tests/named-session.test.ts tests/session-tools-dto.test.ts tests/automation-launch-policy.test.ts tests/project-launch-dispatch.test.ts
git diff --check
```

Build/typecheck/diff check succeeded; **7 test files, 91 tests passed**. Existing tests/timeouts were not relaxed. Synthetic old MiniMax fixture now includes explicit window percentages; protected-file fixture explicitly labels its text limit. The former inference message-text heuristic is replaced by a negative test: a message-only quota assertion on allowance GET is unknown; verified numeric quota codes remain covered. First named-session test attempt lacked this worktree's `dist`; build supplied it, then all cross-process/admission/idempotency tests passed. Build has the existing Vite chunk-size warning.

Negative coverage: interval/weekly zero, video zero, video-only/unknown scope, 0/0 count placeholders, unknown numeric enums, missing window/credential, invalid percentages, auth401/403, generic429, provider500/code, invalid JSON/null/list, timeout, expired reset without positive refresh, Codex allowed-only/limit-false-only, seconds versus milliseconds, secondary saturation and null secondary. Existing dispatch tests retain pre-admission fallback, HumanStop and unknown native admission/no replay protections.

## Actual read-only canary

`node .tmp/quota-fix/live-canary.mjs` imported the built candidate `dist/model-quota.js`; evidence `.tmp/quota-fix/live-canary.json` and `herder-snapshot.json`.

- At **20:12:44–45 UTC**, candidate GLM direct GET returned exhausted weekly credits and preserved actual `unit3/number5`, `unit6/number1`, reset `1792778782999` milliseconds.
- MiniMax used the actual existing singleton `model_quotas` snapshot from **20:12:42 UTC**, injected into candidate fetch without another provider request. The service's dynamically loaded MiniMax credential was absent from its startup `/proc` environment; no credential discovery or new auth was attempted. General interval **97% remaining**, weekly **69%**, start `1792440000000`, end/reset `1792454400000` milliseconds: candidate **reported**. The prompt's 99% and prior 20:00 UTC reset were historical; the fresh window ends **20 October 00:00 UTC / 03:00 MSK**. No claim that the installed old normalizer is fixed.
- Candidate Codex existing-auth direct GET returned primary **35% used**, **604800 seconds** window, reset Unix **1792874442 seconds**, allowed=true, secondary=null; all preserved.
- Mutating only general interval remaining to **0** in that actual MiniMax payload, offline, returned **quota_exhausted**. Original observed interval0/weekly69 regression also passed.
- Canary asserted only the existing GLM quota GET, MiniMax allowance GET/read-only MCP snapshot and Codex usage GET; request bodies absent. **Zero inference requests**. No claims about token reservation, model capability or actual council execution.

Next action belongs to coordinator: independent review of commit `13379b6`, then integration/activation only when authorized and safe for active native tasks. Full runtime delivery and live launch consumer check remain pending at that release boundary.

## Review follow-ups and actual release provenance — 20:31 UTC

The sections above retain the original source handoff. B1 redaction correction was pushed as `14f5f23bb7246cb92b97a89d39c943b92d00f1d5`: string `code` is numeric-only, 9 new regressions; all 100 relevant tests/build/tsc and compiled redaction canary passed.

**B2 candidate now pushed: `d3c2be632aa5d67048c9d661e17e8bd0e28dcc89`**, draft [PR12](https://github.com/megamen32/agent-herder/pull/12), branch `lhc/lhc-quota-freshness-20261019` in the same assigned worktree, based on published main `f9564681a8ddf51cb3fa338df562545386f03611`. Follow-up review branch was needed because PR10 had already been squash-merged by another session. Canonical checkout and foreign WIP remain untouched. A single evidence handoff was admitted natively to that delivery owner (`inputId=quota-b2-ready-d3c2be6-20261019`, turn `01a155dc-bf8e-73a0-ba9e-7466162303c5`); no repeated send or wake was performed.

Exact B2 patch: only `src/model-quota.ts`, `src/automation/minimax-quota-preflight.ts`, `tests/model-quota.test.ts`, `tests/minimax-quota-preflight.test.ts`. Normalizer exposes optional `validUntilMs` from the earliest known applicable text interval/weekly deadline; video deadlines are ignored. It evaluates positive response freshness after GET completion and returns `unknown` / `quota_snapshot_expired` for already expired responses. Preflight bounds positive cache by the earlier of provider deadline and existing finite TTL, rereads at the exact reset, checks after await and avoids cache reuse on clock rollback. Null/missing deadlines remain absent metadata; milliseconds are not guessed from seconds. Negative/exhausted snapshots never become positive by timer. Controller, fallback, HumanStop and native admission paths remain unchanged.

RED: original B2 fake-clock reproductions produced **3 failed /11 passed** before source fix (`.tmp/quota-fix/red-freshness.log`). GREEN: same 7-suite command above now **111 passed**, `npm run build`, `tsc --noEmit`, `git diff --check` succeeded. Extra checks cover interval/weekly exact reset, TTL, fresh expired GET, slow GET crossing reset, seconds/ms/null and clock rollback. Built `dist` preflight independently reproduces first available at10000, reread/unknown at12000, fresh reader40000 unknown with the same expired payload; injected GET only, default network forbidden, zero inference. Evidence: `.tmp/quota-fix/green-freshness.log`, `build-freshness.log`, `typecheck-freshness.log`. B2 is **source candidate only**, awaiting independent review; this worker did no merge/restart/deployment.

### PR10 merge/restart provenance (verified receipts, not assumptions)

- GitHub PR10: head `14f5f23`, actor **megamen32**, merged **2026-10-19T20:20:30Z /23:20:30 MSK**, squash `f9564681a8ddf51cb3fa338df562545386f03611`.
- Native session **`01a15561-ffaf-7380-836b-32659c5a07d7`**, turn **`01a155cd-abeb-7a30-80bd-a8b46b9b94a3`**, latest user prompt: «утсанови сейчас про лимиты например в omniroute или в openchamber там они уже умеют».
- Its native command receipt `exec-d17ae72b-74e0-4de7-9434-885cb46a71af`: `gh pr merge 10 --squash`, exit0, completed **20:20:31.645Z**. Main reflog then fast-forwarded at **23:20:46 MSK**.
- Its restart receipt `exec-deccf786-eaff-40cd-8095-6344955c0f97`: `systemctl --user restart agent-herder.service` plus show, exit0, completed **20:21:36.203Z /23:21:36 MSK**, returned MainPID1629444, active/running, NRestarts0. This proves that session's action, not present runtime identity or complete consumer acceptance.
- Native source `/home/roomhacker/.codex/sessions/2026/10/19/rollout-2026-10-19T21-17-28-01a15561-ffaf-7380-836b-32659c5a07d7.jsonl`; two scoped receipts saved in `.tmp/quota-fix/pr10-native-audit.json`. Identifies a separate delivery owner and user prompt; it does not establish that this worker's independent-review hold was lifted. No rollback or policy/permission changes made.

## Reviewed release and installed consumer proof — 20:47 UTC

**Quota quickfix is now installed in the existing roomhacker Herder singleton.** The candidate/pending statements above describe earlier stages. This scoped release was explicitly assigned to this worker after independent exact-SHA B2 review; no global workflow/permission/auth/billing changes, no new daemon/MCP/cron and no Airlock changes.

### Source, gates and installation

- Read `herder-quota-freshness-review-20261019.md` in full: independent **SCOPED GREEN** for exact `d3c2be632aa5d67048c9d661e17e8bd0e28dcc89`, 20 mock checks plus typecheck, no blockers. It was source review, not an installed receipt.
- Fresh GitHub main was `f956468`, PR12 exact head remained `d3c2be6`, mergeable/CLEAN. No status checks were reported; branch-protection API returned unprotected and effective branch rules returned `[]`. Reviewed built-candidate B2 canary was rerun without network/inference.
- Marked PR12 ready, then merged using `gh pr merge 12 --squash --match-head-commit d3c2be632aa5d67048c9d661e17e8bd0e28dcc89`, without force/automerge. GitHub receipt: **20:43:05 UTC**, merge **`fe2e7790b9485a78c4eb6a206622de1b32352217`**, actor megamen32. Canonical existing main fast-forwarded to this SHA. All four reviewed files match candidate SHA byte-for-byte; only these four paths were integrated.
- Built via ordinary `npm run build` in the existing canonical checkout; production build succeeded. Actual generated delta was exactly `dist/model-quota.js`, `dist/model-quota.d.ts`, `dist/automation/minimax-quota-preflight.js`; the two JS files matched reviewed candidate build hashes. Repeated the same seven suites against merged canonical source: **111 tests passed**. `git diff --check` passed. No dependency installation or package-lock changes.
- Rollback artifact saved before build at `/home/roomhacker/agents-projects/agent-herder/.tmp/quota-release-20261019-2043/rollback-dist`; prior source `f956468`. No rollback was executed.
- One standard `systemctl --user restart agent-herder.service` at **20:45:00 UTC /23:45:00 MSK**. Previous control-plane PID1629444 → **PID2019621**, active/running, NRestarts0. Installed source and `origin/main` both **fe2e779**.
- Installed SHA256: `dist/model-quota.js` **42c1d5d7d41731605aeda0ad285fccb4e54b673241b4712d15c5906463534f5f**; `dist/automation/minimax-quota-preflight.js` **0d5a343d2f9a528a46da73ad9558c8dddfdf0d5625d7d3fd8bd5c64e6506fc76**. The compiled preflight contains neither `anthropic/v1/messages` nor `max_tokens`.

### Native execution preservation and WIP

Verified service `KillMode=control-group`, `CanReload=no`, no stop propagation/dependent units; service cgroup contained only main control-plane PID1629444. Codex managed app-server PID79966 and other native executors were in separate scopes. Shutdown code calls ZCode checkpoint/dispose; its `close()` ends stdin and can SIGTERM the owned transport even in a separate scope, so cgroup separation alone was not treated as sufficient.

Identified the sole owned ZCode transport **PID1631460**, PPID1629444, independent `agent-herder-zcode-app-server-9e3e2983.scope`; it had **no child execution processes**, and two fresh `list_agents(harness=zcode,status=running)` reads were complete with **zero running ZCode sessions**. A final executable guard required unchanged main PID, only that PID in the service cgroup, no stop propagation, no owned-ZCode children, and all47 observed native process start identities still unchanged before restart. Thus only the verified idle owned ZCode transport was disposed; active native session executions were not restarted.

After activation **46 external native PIDs retained identical PID/start ticks**, including both Codex app-servers and the OpenCode daemon **PID4145783**. The only exited pre-snapshot process was the anticipated idle ZCode transport1631460. Before/after exact session reads preserved **all13 observed running session IDs** (12 Codex,1 OpenCode); running sessions continued or completed normally, none of the13 became stopped/error. The list endpoint was limited, so this is an explicit observed set rather than a claimed complete global session census. Native PID proof is separate.

Three sessions reported newer turns on reread. Their old native turns were independently confirmed `task_complete` **before restart**: Exmanager turn01a155db… at20:44:10.869Z, Airlock-admin turn01a155b2… at20:27:42.748Z, Airlock-internal turn01a155ac… at20:34:14.694Z. Remaining same-turn reads showed inProgress/completed rather than aborted. This worker did not send, resume or cancel any native business turn for verification.

Preserved hashes of foreign `package-lock.json`, both untracked OpenCode release integration JS files and `src/rag-search.ts`. Canonical checkout still contains that unrelated package-lock/report/integration WIP; it is **not called clean**. No reset/stash/delete/rebase of foreign work. All assigned worktree source was clean after release.

### Actual singleton and installed-dist canaries

Existing MCP `model_quotas({})` through the actual singleton at **20:45:23.872–24.479 UTC**:

| Provider | Installed actual response |
| --- | --- |
| GLM | quota_exhausted; CREDIT_LIMIT `unit3/number5` and `unit6/number1` preserved, weekly remaining0, reset1792778782999ms |
| MiniMax | reported telemetry; general interval93%/weekly68% remaining, video100% separate; **`validUntilMs=1792454400000`**, equal to minimum applicable interval/weekly reset, i.e.20 October00:00UTC/03:00MSK |
| Codex | reported, primary36% used; **604800seconds**, Unix reset **1792874442seconds**, allowed=true, secondary=null |

Before restart the singleton response lacked validUntilMs; after restart it supplied it, proving the loaded normalizer changed. Response fields, installed artifact hashes and managed PID/source identity jointly establish activation; HTTP200 or build alone was not acceptance.

Imported the **installed canonical dist** for the offline B2 canary with default network forbidden: now10000→available; now12000→new injected GET and unknown; fresh reader40000→unknown/quota_snapshot_expired, validUntilMs11000 retained. All injected requests asserted allowance GET/no body. Actual MCP quota path uses the existing GLM/MiniMax/Codex read-only GETs; **no quota inference/model turn was called**. Snapshot is still telemetry, not reservation/capability proof.

Evidence in assigned worktree `.tmp/quota-fix/`: `release-acceptance.json`, `release-preflight.json`, `restart-guard.json`, `native-processes-before.json`, `native-processes-after.json`, `active-sessions-before.json`, `active-session-preservation.json`, `previous-turn-terminal-proof.json`, `quota-before-restart.json`, `quota-after-restart.json`, `canonical-preserve-hashes.json`, `canonical-wip-before.patch`. Canonical build/test logs: `.tmp/quota-release-20261019-2043/build.log` and `merged-tests.log`.

**This scoped quota release and its real singleton consumer check are complete.** This does not claim unrelated council/model capability or full LHC/other-project milestones.
