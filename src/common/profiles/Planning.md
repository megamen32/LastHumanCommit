# Cost-aware planning

Use this profile for Full work. Keep Direct, Short, and Emergency work fast.

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

Every fresh child receives a Task Card: goal, known facts, allowed and excluded
paths, acceptance check, selected model and budget, stop conditions, and a
short report format. Use a no-history child only when the harness demonstrably
supports it; otherwise record the limitation and do not claim model-routing or
fresh-context proof.

A child returns `NEEDS_REDECOMPOSITION` before wandering when scope must change,
the second independent hypothesis fails, another unknown dependency appears,
the pessimistic budget is exceeded, or an answer from Lead would change the
architecture. L treats that result as a planning signal, re-researches, and
splits or escalates the package.
