# Native LHC delta acceptance

Date: 2026-10-28. Root confirmed the v1.6.2 hook trust repair and explicitly authorized two bounded checks. Both ran against the new synthetic fixture with normal user config, the requested `gpt-6-luna` argument, native JSON output, `RUST_LOG=codex_core::hooks=debug`, and stdin closed via `/dev/null`. Stdout and stderr are preserved separately in `native-luna-delta-repair-*` and `native-luna-delta-status-*`.

## Repair check

- Prompt asked naturally to fix the $50.00 free-shipping boundary and verify it. It contained no LHC or plan hint.
- Native thread ID from `thread.started`: `01a182ef-5e9c-7841-afc2-98bdfc27872e`.
- Before the edit, the assistant spontaneously said it would save a short plan and bind it to the current session. It created `plans/free-shipping-boundary/` with graph, Markdown, HTML, and one leaf `L01`. The leaf records `harness=codex`, `affected_files=["shipping.py"]`, and `session=01a182ef-5e9c-7841-afc2-98bdfc27872e`, matching the native thread. `model` is null and the leaf remains `in_progress`.
- The assistant changed `shipping.py`. An independent `python3 -m unittest -v` run passed all three boundary cases: 49.99, 50.00, and 50.01. Run-specific `git diff --check` is clean; fixture Git status shows only the intended tracked change plus plan/learning/probe artifacts.
- The native repair process ended with wrapper exit 124 before `turn.completed`; no final assistant completion message arrived. The plan leaf therefore remains genuinely in progress and is not marked complete by this tester. Empty `.probe` and `.write-probe` files and `.agents/shared-session/learning/*` were left intact as artifacts of that interrupted run.
- `AgentMemory.memory_recall` failed with a tool approval-required response under `approval=never`; the native turn continued with context-mode and local fixture inspection. This did not result in a silent memory fallback.

## Status-only check

- A separate fresh ephemeral thread returned a short status without changing files or launching tests. Native thread ID: `01a182f4-4998-7482-91cc-79b03c588e4c`; turn completed with exit 0.
- It reported the existing plan as in progress and made no new task. Before and after, the fixture contained exactly one `plan.json` and one leaf. Its response said it had not run checks in that status request, which matches the read-only prompt.

## Continuation and final readback

The first repair attempt's timeout and `in_progress` leaf were preserved. After Root authorized one bounded continuation, a new native thread continued the existing task with normal user config, `danger-full-access`, `gpt-6-luna`, and closed stdin. It did not create another plan. Thread ID: `01a182f8-73c2-7553-a0d8-c4332b5172cf`.

The native assistant rebound the existing `L01` leaf to that thread, ran the boundary checks, marked the leaf `done`, rebuilt the plan graph and projections, and completed the native turn with exit 0. Independent readback confirms one plan and one leaf, matching `done` statuses in the leaf and graph, the leaf session equal to the continuation thread, and `plan.html`/`plan.md` present. The leaf's `progress_events` records that 49.99 remains paid and 50.00/50.01 qualify. Its separate `model`, `result`, and `finished_at` fields remain null.

The fixture function passes all three independent tests; `git diff --check` is clean. Commit `8e2621bf338a0ecc2427d7c12bb8bc0fbe86fc00` changes only `shipping.py`. Fixture `HEAD`, tracking `origin/main`, and the local bare remote's `main` all match that commit. Plan, learning, and empty probe artifacts remain uncommitted in the disposable fixture; no external Git remote was used.

The status-only check completed in thread `01a182f4-4998-7482-91cc-79b03c588e4c` before continuation. It observed the existing plan as in progress at that time and created no additional plan. Native JSON for both checks did not emit an explicit resolved model/provider field or a dedicated hook event; `RUST_LOG` stderr contained only the CLI stdin notice. The selected native CLI argument was `gpt-6-luna` under the normal ChatGPT login/config. Root's delegated native hook-list readback confirmed the installed current hooks were trusted and enabled. The two authorized delta checks are **PASS**: automatic plan creation, actual-thread leaf binding, verified repair, and a status-only request with no new task are evidenced. The separate peer-relay/human-cancellation criterion remains unverified in this campaign; no relay or synthetic STOP was sent.
