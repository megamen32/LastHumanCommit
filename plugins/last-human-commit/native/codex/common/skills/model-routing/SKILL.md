---
name: model-routing
description: Choose and improve model assignments for Lead, executors and independent verification using task difficulty, actual capabilities, acceptance evidence and total cost.
---

# Model allocation is a feedback loop

Use for initial allocation, material re-decomposition, a capability failure or
reviewing which model assignments actually worked. Do not perform a full model
market survey before every task.


## Existing Herder is the execution path

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

For this user's server-100 installation the desired model routes are:

| Model | Harness | Model selection |
| --- | --- | --- |
| GPT-6.1 Sol | codex | `gpt-6.1-sol` (existing native ChatGPT login) |
| GPT-6 Luna | opencode | `omniroute/cx/gpt-6-luna` |
| MiniMax 3.1 Preview | opencode | `omniroute/minimax/MiniMax-M3.1-Flash-Preview` |
| GLM 5.3 Flash | opencode | `omniroute/zc/glm-5.3-flash` |
| GLM 5.3 | opencode | `omniroute/zc/glm-5.3` |

These are installation routing hints, not fixed role assignments or quality
rankings. Resolve current availability/limits. The previous direct Codex Sol
canary succeeded while `omniroute/cx/gpt-6.1-sol` returned a provider error;
check before reusing that failed route. The catalog alone is not execution proof.
On a known pre-submission failure choose an available route explicitly; on an
unknown accepted outcome query the same session/receipt, never duplicate the job.
Do not silently replace Sol with a cheaper model. `openai/*` API availability is
not proof of ChatGPT subscription access; do not switch billing routes silently.

OpenChamber Auto is a separate per-message classifier for messages sent through
OpenChamber. It does not choose this task's Herder model and does not govern
OpenCode CLI/API children. Both can coexist; keep explicit Herder choices rather
than hoping Auto will rewrite them. Auto does not replace LHC's goal, review or
milestone acceptance. Do not add a second supervisor or silently enable auto-
accept permissions while configuring model routing.

## Resolve the actual options

Start from the active harness's available model catalog, recent verified results,
quota/rate limits and required capabilities (tools, vision, context, structured
output, latency). `../../config/model-routing.example.json` supplies historical illustrative
classes: frontier, fable, sonnet, haiku. Its examples are aliases,
not verified API names or fixed benchmark rankings.

Lead and difficult decision/decomposition work use the strongest suitable
available model. A weak orchestrator supervising strong workers is not the default.
Do not equate frontier with a price, a brand or an unattested model ID.

## Allocate an assignment, not a role stereotype

For a delegated bounded assignment, select the least capable available model
that reliably completes it, preferring fast inexpensive executors. Decompose difficult
work until routine pieces can be assigned economically; do not default every
child to Lead's model or a frontier tier. Lead retains global understanding,
resolves uncertainty, schedules dependencies/parallelism, and verifies results.

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
