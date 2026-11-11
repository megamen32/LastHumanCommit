---
name: model-routing
description: Choose a suitable available model and native execution route for the actual assignment.
---

# Model routing

Use LhcPlan `list_models` for the configured assignments and the live catalog. The classes are `fast`, `middle` and `frontier`; resolve the chosen class to an exact available model ID. `model-availability` covers quota and account limits.

| Work | Starting class |
| --- | --- |
| Reading, search, mechanical edits and a well-specified small change | fast |
| Bounded implementation with a clear check | middle |
| Architecture, difficult diagnosis or a consequential unresolved choice | frontier |

Choose by the assignment's capabilities, likely rework, latency and cost. A failed cheap attempt may justify a stronger model, better context or a smaller task. Missing prices stay unknown. Keep planned model and cost estimates separate from observed execution and billed usage.

## Native execution

Prefer the active harness's supported subagents. When Herder is the selected route, use its existing `new_or_resume`, or `create_session` followed by its message transport. Read the live schema and pass the actual model, canonical cwd and stable assignment name. Preserve the same `inputId` for a delivery retry.

Use the real native source session for `sourceSessionId` and `sourceHarness` when required. A fresh independent assignment gets a distinct name; an ongoing Worker can be resumed with its useful context. Keep the user's selected parent model and account unchanged when choosing a child's model.

The assignment includes the goal, role, relevant facts, owned paths, dependencies, output and check. Use fresh context for a genuinely independent review or first-contact test. Ordinary Workers benefit from the previous decisions and attempts. A Worker delegates further only when the Lead has assigned a useful separate scope.

After an uncertain dispatch, inspect that session or receipt before sending another job. Record requested and observed model identities separately. Native quota, permission and stop decisions apply to the operation.

## Plan fields

Each leaf's `tier` is `fast|middle|frontier` and `complexity` is `S|M|L`. S is routine, M is a bounded implementation, L is a difficult or consequential choice. A missing capability can justify a different eligible tier.

Record the planned model in `plan.json.default_model` or a leaf's explicit `model`. Explicit leaf choices take precedence. Estimates and a known tariff can produce a provisional cost; they do not establish actual billed spend. `../../config/model-routing.example.json` provides configuration examples, not live availability.

Save reusable assignment outcomes in the existing task or learning record when they will improve future choices. Diagnose a tool outage as a tool outage rather than automatically downgrading a model.
