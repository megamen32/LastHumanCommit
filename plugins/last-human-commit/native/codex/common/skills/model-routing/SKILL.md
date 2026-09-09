---
name: model-routing
description: Choose and improve model assignments for Lead, executors and independent verification using task difficulty, actual capabilities, acceptance evidence and total cost.
---

# Model allocation is a feedback loop

Use for initial allocation, material re-decomposition, a capability failure or
reviewing which model assignments actually worked. Do not perform a full model
market survey before every task.

## Resolve the actual options

Start from the active harness's available model catalog, recent verified results,
quota/rate limits and required capabilities (tools, vision, context, structured
output, latency). `../../config/model-routing.example.json` supplies the user's
four configurable classes: frontier, fable, sonnet, haiku. Its examples are aliases,
not verified API names or fixed benchmark rankings.

Lead and difficult decision/decomposition work use the strongest suitable
available model. A weak orchestrator supervising strong workers is not the default.
Do not equate frontier with a price, a brand or an unattested model ID.

## Allocate an assignment, not a role stereotype

Understand the node's uncertainty, context, tool requirements, error consequences,
acceptance check and likely rework. Resolve architectural choices with the strong
Lead/Adviser before sending a bounded implementation to an economical model.

Choose the least expected total-cost model that can reliably meet this assignment.
Total cost includes decision-making, context transfer, tools, retries, repairs,
review and user testing. If prices or usage are unavailable, use an explicit
qualitative comparison rather than invented currency figures. Quota, latency and
cash price can favor different choices.

Start a genuinely hard task on a strong model; do not require a sacrificial cheap
attempt. Conversely, do not copy the Lead's model into every child. Tester and
Reviewer are assigned by needed capability, not a blanket economy tier. Preserve
adequate testing even if it is the largest cost in the task.

## Confirm and adapt

Record requested class/model and actual model when the harness attests it. Missing
model selection is a capability limit, not evidence that the requested model ran.
Use the best suitable available route; if capability is essential and missing,
return that exact blocker. Do not silently substitute an incapable model.

After acceptance or failure, diagnose whether the cause was model capability,
bad decomposition, missing context, product complexity or tool/environment error.
Change model, context, method or slice accordingly; escalating the model alone is
not always the repair. Reassign through Lead and Overseer at material route changes.

## Learn from completed work

Keep compact, retrievable assignment outcomes with task family, capability needs,
actual model/harness, accepted result, repair count and attested usage where known.
Prefer existing task evidence/learning index; do not create a second metrics service.
Use comparable accepted tasks to adjust routing hints, recording uncertainty and
sample size. One lucky success is not a universal promotion. Tool outages are not
model reasoning failures. Re-evaluate on relevant model/harness changes.

Output: model assignment + short suitability reason + attested limitations +
acceptance evidence to feed the next allocation. No fixed cheap-token quota.
