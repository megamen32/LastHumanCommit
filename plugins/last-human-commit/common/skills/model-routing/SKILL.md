---
name: model-routing
description: Choose and improve model assignments for Lead, executors and independent verification using task difficulty, actual capabilities, acceptance evidence and total cost.
---

# Model allocation is a feedback loop

Use for initial allocation, material re-decomposition, a capability failure or
reviewing which model assignments actually worked. Do not perform a full model
market survey before every task.


## Existing native and Herder execution paths

Use supported native subagents when the active harness provides them and the task
calls for delegation. Keep the human-selected model/settings, bounded ownership
and independent context. Resolve actual child identity from native receipts;
transport labels and an intended dispatch are not completed execution. Do not
build another orchestrator or rewrite the parent/global model to choose a child.
Use the existing Herder route below when it is the available or selected route.

Use the already connected Agent Herder MCP: no new tool, delegation wrapper,
router agent or role×model profile matrix. Role, model and harness are separate
choices. Before a multi-model dispatch read the current Herder tool schema; use
`new_or_resume` to launch/deliver once, or `create_session` then its existing
message transport. Pass explicit `model`, absolute canonical `cwd` and a stable
assignment `name`; reuse the same `inputId` on delivery retries. Never change
the parent's or global model merely to set a child's model.

Source/parent identity comes from the native current-session context, never from
a guessed last-active session. Supply `sourceSessionId`/`sourceHarness` for a
real continuation/replacement when the schema calls for it; do not invent them
or treat source metadata as proof of an OpenCode-native child relationship.
Respect manual Stop. A fresh independent assignment has a unique stable name;
`new_or_resume` must not reuse a previous tester's discussion as Zero Knowledge.
Do not set `humanRequested=true` for autonomous retries or delegation.

The message contains the current canonical role, bounded task, tangible result,
needed inputs, scope/permissions and the actual acceptance check. Worker and
technical Reviewer can read the relevant source. A fresh Zero Knowledge tester
receives only a realistic persona/goal, product entrypoint and permitted demo
access: no parent chat, implementation/task-card answers or prior verdicts.
A different model alone is not an independent context. All children remain
parts of the original goal and budget; dispatch does not reset the parent clock.

Before dispatch apply `../model-availability/SKILL.md`: existing Herder
`model_quotas` + `list_models`, with separate availability/auth/quota/tool/vision
and actual-model evidence. Its preferred direct subscription routes supersede
historical OmniRoute hints. No automatic paid/weak fallback; pass an explicit
allowed fallback policy, never change parent/global models or credentials.

These historical routing notes do not expand the explicit tier allowlist above.
Resolve an allowed tier to exact live catalog IDs and attest the actual model
before dispatch. Never substitute a model outside the allowed tiers, or an Auto
route, when an allowed route is missing. On an unknown accepted outcome query the
same session or receipt; never duplicate the job. OpenAI API availability does
not prove subscription access and does not authorize a billing-route change.

OpenChamber Auto is a separate per-message classifier for messages sent through
OpenChamber. It does not choose this task's Herder model and does not govern
OpenCode CLI/API children. Both can coexist; keep explicit Herder choices rather
than hoping Auto will rewrite them. Auto does not replace LHC's goal, review or
milestone acceptance. Do not add a second supervisor or silently enable auto-
accept permissions while configuring model routing.

## Resolve the actual options

Start from the active harness's available model catalog, recent verified results,
quota/rate limits and required capabilities (tools, vision, context, structured
output, latency). `../../config/model-routing.example.json` supplies the allowed
tiers: `fast` (glm-5.3-flash, minimax-3.1-flash) and `frontier` (gpt-6-luna,
glm-5.3, gpt-6.1-sol). Its examples are aliases, not verified API names or
fixed benchmark rankings.

The human-selected Lead session coordinates only; it does not execute source, shell,
checks or delivery actions. Workers, Advisers, Reviewers and Testers may use only
the allowed tiers: `fast` (glm-5.3-flash, minimax-3.1-flash) and `frontier`
(gpt-6-luna, glm-5.3, gpt-6.1-sol). Resolve the chosen model to the exact
currently available catalog ID and verify attested model/capability before
dispatch. No silent fallback to a model outside the allowed tiers, to another
provider/model, or to an Auto route. If no allowed route is available, report the
blocker. Historical labels and catalog rankings cannot override this explicit
allowlist.

## Allocate an assignment, not a role stereotype

The Lead decomposes and routes every execution step, including small tasks. Select
within the allowed families by current capability; do not substitute an unlisted model.
The Lead retains global understanding, resolves decisions, schedules dependencies and
parallelism, and collects results. A Worker owns its assigned leaf and never recruits.

Prefer zero-knowledge executors: a fresh context for each independent subtask,
with only its self-contained contract, necessary inputs, file locations,
constraints and acceptance check. Zero-knowledge means no inherited parent chat
or unrelated project history; it does not mean disabled reasoning, missing
essential facts, or a provider privacy feature. Supply the relevant facts instead
of forcing a cheap model to rediscover them. Reuse context within the same bounded
task when it avoids proven rework; broader context reuse needs a concrete total-cost
benefit, not habit. Treat smaller prompts as an economy preference, not a verified
price saving without actual usage evidence.

Understand the node's uncertainty, context, tool requirements, error consequences,
acceptance check and likely rework. Resolve architectural choices through allowed-model advisers before assigning a
bounded implementation Worker.

Choose the least expected total-cost model that can reliably meet this assignment.
Total cost includes decision-making, context transfer, tools, retries, repairs,
review and user testing. If prices or usage are unavailable, use an explicit
qualitative comparison rather than invented currency figures. Quota, latency and
cash price can favor different choices.

Assign hard tasks, advisers, Reviewers and Testers only within the allowed tiers,
selecting by required capability. Never run sacrificial attempts or silently
substitute. Preserve checks needed to support the claim, even when they are the
largest task cost.

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

Include the parent outcome/canary reference and bounded child acceptance in the
assignment. A child result never closes the parent delivery stages or resets
60/120 clocks. An already assigned executor/reviewer/tester does not hire recursively.
