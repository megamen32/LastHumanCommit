---
name: model-availability
description: Check existing model catalogs, read-only subscription quotas and assignment capabilities before council, delegation or focus acceptance; the allowed tier list governs those assignments while the route table is installation-specific evidence; never infer availability from a model name or telemetry status.
---

# Available routes, not guessed capacity

Use existing Agent Herder `list_models` and `model_quotas` first. Read their live
schemas; retain source, checked_at, relevant raw numeric fields, period/unit/reset
and the selected route in existing task evidence. This is observation, not a
reservation: other clients can spend quota after the read. No new MCP or scheduler.

For each candidate separate catalog presence, auth state, subscription quota,
required tools/vision/context, requested model and actual native execution model.
`reported` means telemetry arrived, not eligible. Unknown is not available. A
catalog entry or a model name in a prompt does not attest successful execution.

The allowed tiers govern every assignment: tier `fast` is `glm-5.3-flash` and
`minimax-3.1-flash`, tier `frontier` is `gpt-6-luna`, `glm-5.3` and
`gpt-6.1-sol`. This list applies wherever a model is chosen for council,
delegation or focus acceptance.

User-approved routes for this installation (recheck live catalog):

| Tier | Harness | Exact subscription route |
| --- | --- | --- |
| frontier | codex | `gpt-6.1-sol` |
| frontier | opencode | `zai-coding-plan/glm-5.3` |
| fast | opencode | `minimax-coding-plan/MiniMax-M3.1-Flash` |

The table is this installation's historical route evidence for reaching those
models; it is not the authority on which models are allowed. A route that is
missing today is a blocker to report, never a licence to pick a model outside
the allowed tiers.

Do not silently substitute OmniRoute, PAYG, a cheaper model, a credit pack or an
unapproved fallback. Set explicit route/fallback policy in the existing dispatch.
Preserve native session/job IDs; inspect an accepted or UNKNOWN outcome instead of
launching another job. HumanStop, permission and auth boundaries still apply.

## Read the right pool and units

- GLM CREDIT_LIMIT uses credits, not tokens/calls. Inspect every applicable text
  window: weekly remaining 0 blocks despite a free short window. Keep `unit` and
  `number` (observed unit3/number5 = five hours; unit6/number1 = one week); unknown
  shapes stay unknown. `percentage` here is used, not remaining.
- MiniMax general/text `current_interval_remaining_percent` and
  `current_weekly_remaining_percent` are remaining: zero in either applicable
  window means exhausted. The separate video pool neither blocks nor funds text.
  Counts 0/0 do not override reported percentages. Preserve numeric status enums
  without inventing undocumented meanings. `remains_time` is milliseconds.
- Codex usedPercent is used, windowDurationMins is minutes, resetsAt is Unix
  seconds. A missing secondary window is unknown, not zero used. Inspect relevant
  buckets and account limit flags together; contradictory data is not eligibility.

Take a fresh read before a dispatch batch and after meaningful waiting, a known
reset or a provider failure. A reset timestamp does not make an old zero snapshot
positive. Missing reset remains unknown; do not invent now+window or poll in an
LLM loop. Reuse a still-relevant snapshot within one immediate batch, recording
its age rather than claiming a provider-guaranteed TTL.

## Existing native/direct fallback when Herder is unavailable

Use documented read-only provider/native mechanisms with existing protected auth;
never print keys, bearer headers, cookies or full auth/config files.

- Codex App Server `account/rateLimits/read` (not a new inference turn).
- Z.AI official usage query: GET `https://api.z.ai/api/monitor/usage/quota/limit`.
- MiniMax documented `mmx quota` or GET `https://www.minimax.io/v1/token_plan/remains`
  with existing subscription auth. Do not send a one-token messages probe: it is
  inference and may consume paid credit packs after subscription exhaustion.

On a read failure make at most one appropriate documented fallback read; then
record unknown and continue independent work. Do not refresh auth, buy capacity,
change billing or wake manually stopped sessions to measure quota.

Three eligible models may provide useful diversity; two are a valid two-model
council. One can provide a fresh adversarial review, not multimodel acceptance;
zero leaves the required model gate pending. Preserve alternatives and dissent.
A blocked model delays its assignment, not all independent implementation work.
