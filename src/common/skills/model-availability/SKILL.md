---
name: model-availability
description: Read the existing model catalog and quota telemetry before allocating work that depends on them.
---

# Model availability

Call LhcPlan `list_models`; it combines configured assignments with Herder's `list_models` and `model_quotas` when available. Use those native tools directly for raw fields. Keep catalog presence, authentication, quota and required capabilities separate.

For council, Adviser or frontier work, the configured reserve is 20% of each applicable provider window. Below that reserve, use an eligible cheaper route or continue independent work unless the user explicitly changes the choice. An unavailable quota reading is unknown, not a claim of spare capacity. Reuse a recent reading within the same dispatch batch; refresh after a meaningful wait, reset or provider failure.

## Units

- Z.AI/GLM `percentage` reports used share. 100% means exhausted. Check all applicable text windows; weekly exhaustion still matters when the short window is free. CREDIT_LIMIT is credits, not tokens. Retain `unit` and `number` for the reported period.
- MiniMax `current_interval_remaining_percent` and `current_weekly_remaining_percent` report remaining share; use the tighter applicable text window. Video is a separate pool. `remains_time` is milliseconds.
- Codex `usedPercent` reports used share, `windowDurationMins` is minutes and `resetsAt` is Unix seconds. Missing windows remain unknown.

Retain the source and time of a reading. A reset timestamp by itself does not prove that a previously exhausted pool recovered.

## Configured route examples

These installation examples need confirmation against the current catalog:

| Tier | Harness | Route |
| --- | --- | --- |
| frontier | codex | `gpt-6.1-sol` |
| middle | opencode | `zai-coding-plan/glm-5.3` |
| fast | opencode | `minimax-coding-plan/MiniMax-M3.1-Flash` |

Keep the user's account, provider and billing choice. A missing route is not a reason to silently switch to PAYG, buy capacity or use another account.

## When Herder is unavailable

Use an existing documented read-only source with its protected authentication:

- Codex app-server: `account/rateLimits/read`.
- Z.AI: GET `https://api.z.ai/api/monitor/usage/quota/limit`.
- MiniMax: `mmx quota` or GET `https://www.minimax.io/v1/token_plan/remains`.

A model inference probe may consume paid capacity and is not a quota read. If the supported reading fails, retain the unknown state and continue work that does not depend on it. Report an essential missing capability to the Lead.
