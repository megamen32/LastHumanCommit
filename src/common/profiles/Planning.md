# Cost-aware planning

Use this profile for every task. Keep Direct, Short, and Emergency work fast.

Every task record has an initial estimate as optimistic / likely / pessimistic
active minutes. It is immutable. Append each revision with its trigger and
evidence instead of replacing the initial estimate.

Choose the next action by `Least Cost-to-Canary`: maximize expected movement of
the business canary while minimizing tokens, time, tool calls, subagents, and
user interruptions. Stop when the canary passes. Do not spend budget on
unrequested hardening, audits, rollback, backup, or cleanup.
A producer whose output has no current business-path consumer has zero canary
delta and must not be added.

For every task record, state `stop_when`, `abandon_when`, and
`forbidden_without_explicit_user_request`. A restart, breaking change,
destructive action, deployment, or rollback is an authorization boundary, not a
task class: ask one short question when that exact action becomes necessary.

For every candidate plan and selected child package, record:

- outcome, allowed scope, acceptance proof, and separately runnable check;
- model, reasoning effort, provider or quota bucket;
- active minutes as `optimistic / likely / pessimistic`;
- `relative cost` as low, medium, or high, plus tool overhead and uncertainty.

Waiting for a child is not Lead inference cost. Sum parallel child budgets for
quota cost; use the critical path for wall-clock. Do not invent a currency
price when a subscription or provider limit is unknown.

Split a cheap-child package before assignment when it has an unmade
architecture decision, more than one independent acceptance gate, an unknown
dependency, no isolated check, or more than 20 likely active minutes. Use a
strong short adviser only when splitting loses necessary context or leaves a
real architecture decision.

Before creating a child, L writes its role, goal, known facts, allowed and
excluded paths, acceptance check, selected model and budget, stop conditions,
and report contract into its assigned `todo-*.md`. The child receives only that
task-file path, reads no parent conversation, appends its detailed result to
the same file, and returns only TL;DR to L. Select the lowest sufficient model
class; bounded Worker packages normally use `5.4-mini`. Do not inherit L's
model by default. Escalate only after `NEEDS_REDECOMPOSITION` or concrete
acceptance evidence shows a capability gap. Load the selected harness adapter's
`subagent_instructions_template` before creating the child. Use a no-history
child only when the harness demonstrably supports it; otherwise record the
limitation and do not claim model-routing or fresh-context proof.

A child returns `NEEDS_REDECOMPOSITION` before wandering when scope must change,
the second independent hypothesis fails, another unknown dependency appears,
the pessimistic budget is exceeded, or an answer from Lead would change the
architecture. L treats that result as a planning signal, re-researches, and
splits or escalates the package.

When a child result is the next join point, L records one wake no sooner than
10 minutes and ends its turn. The result itself may wake L earlier. Waiting by
polling, prompting for an immediate result, changing a timeout, or opening a
new result-seeking branch has zero canary delta and is forbidden.

If an Explorer's accepted result yields a bounded implementation in the same
owned scope, L reassigns that exact child `Worker <same-task-file-path>`. The
same file records both role passes; a second Worker for the same evidence is
forbidden. Use a separate Reviewer only for independent review.
