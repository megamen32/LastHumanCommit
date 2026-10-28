# Native LHC acceptance preflight

Date: 2026-10-28. Scope: native Codex CLI/plugin readiness and a disposable consumer fixture. No LastHumanCommit implementation, tests, or other testers' reports were read.

## Native route and plugin state

- Native CLI is `codex-cli 0.162.1`; `codex login status` reports an existing ChatGPT login. No auth file or secret value was read.
- Safe config fields show default model `gpt-6.1-sol`, no top-level `model_provider`, and no profile selected by the preflight command. The preflight explicitly selected `gpt-6-luna` and did not request OSS, a local provider, or a custom profile. This is the intended native ChatGPT path, but the timed-out invocation did not prove which model/provider actually answered.
- Native `codex plugin list --marketplace megamen32-plugins --json` reports `last-human-commit@megamen32-plugins` v1.6.1 as `installed=true`, `enabled=true`, source `local`; the registered marketplace is the existing local `megamen32-plugins` checkout. The same read reports no other marketplace candidates for this filter.
- The native manifest path exists at `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/native/codex/.codex-plugin/plugin.json`; only its path was checked, not its contents.
- Existing native config has ten enabled LHC hook states: `interrupt`, `permission_request`, `post_compact`, `post_tool_use`, `pre_compact`, `pre_tool_use`, `session_end`, `session_start`, `stop`, `user_prompt_submit`. No config was changed and hook-trust bypass was not used.
- Unfiltered `codex plugin list --json` yielded no output within 15 seconds and was stopped. The filtered native plugin-manager read above succeeded.
- This proves plugin-manager installation and enabled state, not runtime hook execution or injected instructions.

## Model availability and bounded probe

- Agent Herder `list_models` and `model_quotas` did not return; Lead reports those same MCP reads already waited at least 60 seconds before timeout. No retry was made.
- One native app-server `account/rateLimits/read` attempt did not yield a correlated usable result; only an asynchronous/empty result was observed. Quota remains unknown; no second read was made.
- Before Lead's steer, one ephemeral read-only `codex exec -m gpt-6-luna --json` observation probe was started in the fixture. The outer command returned after 30.3 seconds with no output. The nested command had `capture_output=True`, and its `functions.exec_command` session handle was not recorded, so its stderr and later timeout output are unavailable. The tester's own rollout contains the call at 2026-10-28T14:05:55.585Z and the blank return at 2026-10-28T14:06:25.957Z; no separate ephemeral child session record was found. A later process listing showed no matching process. The delay source (global MCP startup, auth, or another local wait) therefore remains unknown; shared daemon logs were not read, and the same observation prompt was not replayed.
- Treat the route/inference outcome as unknown. This probe proves neither Luna execution nor runtime injection. Existing ChatGPT login and a selected model name alone do not prove Luna availability. The post-install engineering acceptance remains pending and must not be reported as passed.

## Disposable fixture

- Path: `.agents/tasks/20261028-lhc-execution-audit/consumer-tests/native-luna-fixture-20261028/`.
- It is a new minimal Git repository on `main`, not a copy of LastHumanCommit. `eligibility.py` contains the intentional `age > 18` off-by-one bug; its standard-library regression suite checks 17, 18, and 19. Baseline run: 2 pass, 1 expected failure (`is_adult(18)` returns false).
- Baseline is committed and the fixture is clean at `6ae1f1a`. Its local `origin` is a bare repository inside the owned `consumer-tests/` path; the bare `main` points to the same commit (`6ae1f1ab6ea79bd29e476aabf837c3a214d4e28e`). This makes any fixture-only commit/push local; no external remote action occurred.

## Remaining evidence

A post-release native turn must still prove the actual selected execution model and native LHC injection from its own session events/assistant output, then perform the ordinary bug-fix request and verify the regression. Follow-up status/peer-relay behavior is not proven by this preflight. Do not report the preflight as an acceptance pass.

## Post-install readback

After a peer reported the install, a fresh filtered native plugin-manager read independently returned `last-human-commit@megamen32-plugins` version `1.6.2`, `installed=true`, `enabled=true`, source `local`, at the existing native Codex path. The disposable fixture's Git root is the fixture itself; it has no fixture-local `AGENTS.md` and its README is neutral. The fixture origin remains the local bare repository under `consumer-tests/`. This readback is not a Lead release signal and no final repair run was started.
