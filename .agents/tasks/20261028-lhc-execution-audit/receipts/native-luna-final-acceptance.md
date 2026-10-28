# Native Luna fixture result

Date: 2026-10-28. Lead release signal received before this run. Scope stayed within the disposable fixture and native receipt paths. No implementation, source tests, or reports from other agents were read.

## Invocation and evidence

- Native CLI: `codex-cli 0.162.1`; requested model argument: `gpt-6-luna`; sandbox: `workspace-write`; execution: `--ephemeral --json`.
- Invocation used `--ignore-user-config` plus `-c 'plugins."last-human-commit@megamen32-plugins".enabled=true'`. The installed v1.6.2 plugin was independently confirmed installed/enabled/local immediately before the run. The prior native login-status check reported ChatGPT; this invocation returned a completed assistant turn.
- Process handle `8521` completed with exit 0. Native JSON event `thread.started` supplied actual thread ID `01a182e4-562c-7182-9319-5c53d8129f19`; the turn completed. The event stream did not expose a resolved model/provider field or a hook event.
- Stdout and stderr are preserved separately in `native-luna-final-stdout.jsonl` and `native-luna-final-stderr.log`. Stderr contains only `Reading additional input from stdin...`; it did not prevent this turn from completing.
- The assistant explicitly reported that no LHC runtime hook was available. Its turn made one file change and reported running the three fixture tests. No plan/leaf was created in the fixture.

## Consumer readback

- Independent `python3 -m unittest -v`: all 3 tests pass, including the age-18 boundary regression.
- `git diff --check`: clean. Fixture Git status shows only `M eligibility.py`; no plan files exist under fixture `.agents/`.
- The function behavior is fixed, but automatic LHC plan creation and session-bound leaf acceptance failed. Since this invocation used `--ignore-user-config`, the installed marketplace registration/trust state may not have reached the runtime; that is a plausible cause, not proven by the available events. The native event stream does not attest to hook execution.

## Acceptance status

`CHANGES_REQUIRED` for the requested default LHC behavior. The user-level fixture fix is verified. Runtime hook injection, resolved `gpt-6-luna` provider identity, a model-created plan/leaf bound to the emitted thread ID, a status-only no-new-task follow-up, and native peer-relay cancellation behavior remain unproven. The bounded preflight had no response and was not replayed. No further native inference was started in this run.

Lead later reported a verified trust-path mismatch: current global hook trust entries name the old `hooks/hooks.json`, while the installed v1.6.2 manifest registers `com.openai/hooks/hooks.json`; matching current trust entries are absent. This is a Lead-provided diagnosis, not a second independent source inspection. No trust or global configuration was changed by this tester. Preserve this failed run as RED until the runtime path is repaired and a fresh authorized acceptance proves injection.
