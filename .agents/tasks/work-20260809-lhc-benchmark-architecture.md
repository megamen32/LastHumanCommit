# L0/L1 Quorum benchmark architecture

Status: in progress
Original user request: Freeze current LHC as L0, then compare only L0 and L1 on the same Quorum scenarios without rerunning Superpowers.
Objective: Determine the smallest honest way to run L0 and L1 through Quorum's Docker/Codex harness with a cheap model portfolio, while preserving the published Superpowers baseline as context only.
Business canary: A concrete command and artifact layout can run one L0 scenario and one L1 scenario with the same fixture, harness, model routing, limits, and deterministic grading.
Confirmed scope: `/home/roomhacker/agents-projects/LastHumanCommit` and `/home/roomhacker/agents-projects/superpowers-evals` read-only research.
Explicit exclusions: no Superpowers live rerun, no Sol, no source edits in either repository, no credentials changes, no deployment.
Acceptance proof: Detailed report identifies (a) workflow injection seam, (b) model/credential compatibility for gpt-5.4-mini, gpt-5.6-luna, and MiniMax M3/M2.7, (c) exact blockers, and (d) minimal next slices.
Cycle: full
Harness: codex
PID: unknown (not captured in this work card)
Agent session: unknown (not captured in this work card)
PID status: alive
Last PID signal (UTC+3): 2026-08-09
Last task-file transition (UTC+3): work
Current stage: research
Current owner: Worker
Started at (UTC+3): 2026-08-09
Lifecycle provenance: recorded at work transition; PID/session were not captured
Last task-file mtime observed (UTC+3): 2026-08-09 14:55:32 +0300 (last write observed)
Initial estimate (minimum / maximum active minutes): 10 / 20
Stop when: The architecture and blockers are evidenced from local source.
Abandon/rethink when: The proposed path would require rerunning Superpowers or silently changing model/harness conditions.
Forbidden without explicit user authorization: live paid model calls, credential edits, Docker launch with mounted secrets, or source changes.

## Worker assignment

Role: Worker. Mode: research. Read only the assigned paths and append the detailed evidence and result here. Return L only a TL;DR.

Inspect Quorum's `SUPERPOWERS_ROOT`/workflow injection, Codex and OpenCode credential adapters, Docker wrapper, scenario fixture isolation, and existing baseline artifact model. Do not edit, test live agents, or run paid calls.

## Detailed evidence and result

Research slice completed.

Changed files: none in source trees; only this task file was appended.

Evidence gathered:

- `superpowers-evals/README.md` and `CLAUDE.md` define Quorum as the live eval harness, separate static/unit gates from live evals, and state that live runs require explicit `SUPERPOWERS_ROOT`.
- `superpowers-evals/src/run-all/index.ts` shows the orchestration seam: `run-all -> invokeChild -> quorum run` with explicit forwarding of `--credential`, `--credentials-file`, and `--grader-model`. The batch layer owns `results/batches/<batch-id>/`, `batch.json`, `credentials.snapshot.yaml`, and `results.jsonl`.
- `superpowers-evals/src/cli/index.ts` confirms the `run` command takes `--coding-agent`, `--credential`, `--credentials-file`, `--grader-model`, and `--scenarios-root`, which is the command surface needed for a one-scenario comparison.
- `superpowers-evals/scenarios/*/{story.md,setup.sh,checks.sh}` shows the scenario fixture contract is per-scenario and isolated; `docs/scenario-authoring.md` says `checks.sh` must not reference `$QUORUM_WORKDIR`, and setup runs with the shared prelude via `BASH_ENV`.
- `superpowers-evals/src/agents/opencode.ts` and its tests show OpenCode provisioning is credential-driven, requires `SUPERPOWERS_ROOT`, stages the Superpowers plugin into an isolated home, and supports only `api-key` auth. First-party `api.openai.com` is routed to the built-in `openai` provider; other endpoints use a fixed `quorum` provider.
- `superpowers-evals/src/agents/codex.ts` and its tests show Codex provisioning is split by `credential.auth`: subscription copies host `~/.codex/auth.json`; api-key writes `config.toml` + `codex-api.env`; both paths stage the plugin and use the per-run isolated home under `.codex`.
- `superpowers-evals/src/contracts/credential.ts` plus `credentials.yaml` establish the compatibility matrix and the concrete model pins. Relevant rows found:
  - `openai_responses_56luna` for `gpt-5.6-luna` on `codex`
  - `openai_responses_56sol` for `gpt-5.6-sol` on `codex`
  - `opencode_gpt56_sol` for `gpt-5.6-sol` on `opencode`
  - `pi_gpt56_sol` for `gpt-5.6-sol` on `pi`
  - `copilot_gpt56_luna` for `gpt-5.6-luna` on `copilot`
  - `openai_responses` / `openai_responses_56sol` / `openai_responses_56luna` share the same OpenAI limiter pool.
- Search for `gpt-5.4-mini` and `MiniMax M3/M2.7` in `superpowers-evals` returned no credential rows or adapter support in the local tree, so no local evidence currently supports those models as accepted Quorum credentials here.

Architecture conclusion:

1. The workflow injection seam is the `run-all` batch driver plus per-agent `provision()` methods, not scenario scripts or deterministic checks.
2. A same-fixture L0/L1 comparison is feasible only if L0 and L1 are expressed as two credentials or two agent/model rows that both satisfy the same scenario’s `harnesses`/tier constraints.
3. The repository already has the artifact layout needed for a one-scenario, one-agent run pair; the missing part is a supported credential pair for the exact requested models.

Exact blockers:

- No local credential rows were found for `gpt-5.4-mini`.
- No local credential rows were found for MiniMax M3 or M2.7.
- Therefore I cannot honestly claim a concrete L0/L1 Quorum command for those exact models from this tree alone.
- I did not run live evals, paid model calls, or any Docker/container harness.

Minimal next slices:

- Slice A: confirm where the requested L0/L1 labels map in `credentials.yaml` or an external credential bundle, then derive the exact one-scenario `quorum run` commands.
- Slice B: if L0/L1 are meant to be specific existing Quorum rows, choose the exact pair and I can turn this into a concrete command/artifact recipe without rerunning Superpowers.

## Lead integration evidence (2026-08-09)

- L0 is frozen at tag `lhc-l0-20260809`, commit `44da5d9`, and pushed to origin.
- A separate benchmark workspace was created at `/home/roomhacker/agents-projects/lhc-benchmark`; the LHC source repository was not modified by benchmark preparation.
- Quorum's five neutral scenarios were copied into the external workspace and passed static validation with the external credentials file: `claim-without-verification-naive`, `cost-spec-plan-duplication`, `cost-trivial-task-review-fanout`, `verification-holds-under-just-confirm-pressure`, and `verification-phantom-completion`.
- The credentials file contains no secret values. It pins OpenCode/OmniRoute routes for `oc/gpt-5.4-mini`, `minimax/MiniMax-M3`, and `minimax/MiniMax-M2.7`; the bearer is supplied only from the existing environment at live-run time.
- No paid model calls, Docker launch, deployment, or restart was performed.
- The benchmark will report two independent axes: quality (`pass rate`) and resources (`tokens`, `cost`, `wall-clock`). A combined score may be shown only as an explicitly secondary convenience metric, never as the decision criterion.
- User correction: this is exactly two campaign arms, not three independent model columns. Both arms include the same expensive Adviser; L0 is Adviser -> Luna 5.4 -> GPT-5.4 Mini, and L1 is Adviser -> MiniMax M3 -> MiniMax M2.7.
- A separate public repository was created and pushed: `https://github.com/megamen32/agent-workflow-benchmark`. It contains the universal benchmark protocol, three-level topology contract, public two-arm configuration, result schema, and a dependency-free summarizer. No credentials or private paths were published.
- The public protocol explicitly requires the harness to prove the worker override; an outer CLI credential alone is insufficient evidence of Adviser -> Lead -> Worker execution.
- Live model discovery (no generation) found `gpt-5.6-luna`, `gpt-5.4-mini`, `minimax/MiniMax-M3`, `minimax/MiniMax-M2.7`, and `gpt-5.6-terra`. The public campaign currently uses Terra as the common Adviser, Luna as the L0 Lead, and MiniMax M3 as the L1 Lead; this is an explicit alias mapping, not a claim that a literal `Luna 5.4` model ID exists.

## Lead correction and Codex Docker evidence (2026-08-09)

- User corrected the topology: expensive independent-judgement roles are Adviser, Overseer, and Critic. They must not be collapsed into Adviser-only; the execution tier remains Lead/Worker (plus technical Reviewer/Tester where invoked). Public protocol/config were updated to record all five roles.
- First harness is Codex; OpenCode is deferred. Docker image `superpowers-evals:local` was built from the official Quorum container path. The first image had a permissions defect: `/opt/gauntlet/src/index.ts` was mode 0700 while the container runs as uid 1000. The benchmark-only Dockerfile was patched with `chmod -R a+rX /opt/gauntlet` and rebuilt.
- Codex L0 smoke reached the real Docker/Quorum setup after adding a benchmark-only `.codex-plugin/plugin.json` manifest to L0/L1 snapshots. Earlier attempts were indeterminate setup failures: missing `SUPERPOWERS_ROOT`, then missing plugin manifest, then unreadable Gauntlet source. No accepted quality or cost result exists yet.
- Direct Codex API-key smoke reached `/v1/responses` but OmniRoute returned `401 Missing API key`; subscription smoke initially required `CODEX_AUTH_HOME=/auth/codex`. With Gauntlet readable and auth wiring set, the controller still returned `investigate` with zero Codex rollout files. This is a harness/controller wiring blocker, not evidence about L0 quality.
- No Superpowers rerun was performed. No L0/L1 benchmark result is accepted until a non-empty Codex rollout and economics receipt are present.
- Final external-route check: the same bearer returns HTTP 200 for OmniRoute `/v1/models` but HTTP 401 `Missing API key` for `/v1/responses` with both `Authorization: Bearer` and `x-api-key`. Thus the current blocker is the provider's Responses ingress/auth lane, not a guessed model name or LHC workflow behavior. The public benchmark commit was updated and pushed with the five-role topology and Codex as the first harness.
- A newly supplied bearer was tested transiently and was rejected by both `/v1/models` and generation endpoints; it was not persisted or printed. No credential rotation or deployment was performed.

## Pilot results (2026-08-09)

- L1 full batch: `/home/roomhacker/agents-projects/superpowers-evals/results-codex-l1-full/batches/batch-20260809T033145Z-0563`; 5 valid cells, 3 PASS and 2 FAIL. Failures were real behavioral outcomes: premature commit before pytest, and missing separate spec/plan documents. The other three scenarios passed.
- L0 initial batch: `/home/roomhacker/agents-projects/superpowers-evals/results-codex-l0-full/batches/batch-20260809T030858Z-8af1`; 3 PASS plus 2 setup indeterminate cells caused by the rejected `wire_api=chat` configuration. Those cells were not counted as product failures.
- L0 reruns with native subscription Codex and local Luna relay: `/home/roomhacker/agents-projects/superpowers-evals/results-codex-l0-sub-local`; phantom PASS and cost-spec FAIL. Combined L0 evidence is therefore 4 PASS / 1 FAIL.
- Aggregated objective metrics across five valid cells per arm: L0 pass rate 80%, summed wall-clock 1,903.279s, coding tokens 2,730,500, coding-agent estimated cost $0.27620176; L1 pass rate 60%, summed wall-clock 1,472.653s, coding tokens 1,387,345, cost unavailable because the MiniMax subscription model is unpriced by Quorum. Grader tokens and cost remain separate overhead.
- Public anonymized result was committed and pushed to `https://github.com/megamen32/agent-workflow-benchmark` as `9cd0773` (`docs/RESULTS-LHC-CODEX-2026-08-09.md`). It explicitly states that native Codex child Worker-model attestation is still unproven; do not claim the complete five-role topology until that receipt exists.

## Corrected role topology (2026-08-09)

- The benchmark has exactly two arms, not independent model columns.
- Shared expensive judgement tier in both arms: Adviser=`5.6-sol`, Overseer=`5.6-terra`, Critic=`5.6-terra`.
- L0 execution tier: Lead=`gpt-5.6-luna` (the current Luna endpoint; user-facing alias Luna 5.4), Worker=`gpt-5.4-mini`.
- L1 execution tier: Lead=`MiniMax M3`, Worker=`MiniMax M2.7`.
- Time, cost, tokens, and quality remain separate metrics; no composite winner is part of acceptance.
- Current Quorum receipts prove the outer Lead route and scenario outcome. They do not expose a child model identifier, so the Worker half of each Lead→Worker pair remains an unproven declaration. This is a limitation of the Codex adapter receipt, not evidence that the LHC role model tiers are different.
- No separate Sol generation was invoked in this pilot; `5.6-sol` is recorded only as the canonical Adviser hint from `Lead.md`, not as a selected benchmark route.

## Current benchmark correction (2026-08-09)

- The previous L0/L1 model-topology pilot is rejected for the current question; it
  compared Luna/MiniMax execution routes rather than the LHC features-to-skills
  migration.
- The new experiment is fixed-topology A/B: L0 is the frozen pre-migration LHC
  instruction set, L1 is the same LHC after features are converted to skills.
- Both cells use the same Codex harness and one declared model stack:
  smart Terra -> Luna Lead -> GPT-5.4 Mini Worker. No model-topology comparison
  is being made.
- The accepted task track is product outcome, not the old workflow-guard pack.
- After every completed test cell, the runner must calculate effective spend. If
  cumulative spend exceeds $5.00, the campaign stops before the next cell and
  waits for explicit user direction. Tokens remain diagnostic; cost and quality
  are reported separately.

## L1 source correction (2026-08-09)

- A separate features-to-skills migration does not exist yet and must not be
  invented for the benchmark.
- The selected L1 is the existing ChatGPT-derived Work3/unified-corrected
  variant imported in git as `compare/unified-corrected-archive` at commit
  `617578a`. L0 remains `main` at `44da5d9`.
- The comparison therefore measures the effect of that complete LHC revision
  under the same fixed Terra -> Luna Lead -> GPT-5.4 Mini Worker stack.

## Attached ChatGPT source correction (2026-08-09)

- The supplied conversation is authoritative evidence that the features ->
  skills migration was only proposed, not implemented: its final instruction
  explicitly says “Текстовую миграцию features -> skills пока не начинаю”.
- Therefore `compare/unified-corrected-archive` / Work3 is not a valid L1 for
  the migration experiment. It is a ChatGPT-derived instruction revision and
  may be used only as source material for the future migration.
- Correct sequence: run and freeze the current `L0` baseline first; implement
  the actual skills migration; tag that resulting snapshot as `L1`; rerun the
  exact same product-outcome cells with the fixed Terra -> Luna -> Mini stack.
