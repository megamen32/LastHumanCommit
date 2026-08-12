# Worker research protocol

Use only for `Worker(mode=research)`. Research is read-only and exists to find
the cheapest route to the next real business proof.

## Method

Prefer the installed `worker-research` skill as the executable procedure. Its
tool order is normative:

1. Search the project-local reusable code map and check hit freshness.
2. Use `rg --files` and targeted `rg -n -C` as the default source-of-truth
   search. Trace the actual production consumer path before nearby
   abstractions, beginning at the real consumer.
3. Use context-mode to process large outputs without flooding the Worker
   context; do not treat its index as the durable canonical project map.
4. Use an existing Graphify graph only for genuinely multi-hop architecture or
   ownership questions; verify decisive edges with current source and do not
   build a graph for a simple lookup.
5. Find the existing mechanism, first real blocker, and cheapest discriminating
   probe. Stop once L can implement directly or assign a coherent lane.

Upsert verified, likely-to-recur production paths, ownership, configuration,
test paths, decisions, and failure shields into
`.agents/shared-session/knowledge/code-map.json`. The map is bounded and
rewritable by stable key, not append-only. Never store secrets, raw logs,
temporary status, or guesses as verified facts.

Persist research when handoff, recovery, reuse, or the cost of rediscovery
justifies it. Use a named file under `.agents/shared-session/results/<task-id>/`
when a durable result is valuable, and an ignored search journal only when the
search history itself has reuse value. No elapsed-time threshold by itself
requires a file or Git commit. Chat may carry the complete compact answer when
that is cheaper and recoverable enough.

At every 20 active minutes report progress, business delta, blocker, whether the
route remains shortest, and the smallest next probe. The expected total range
may exceed 20 minutes. The checkpoint does not end the Worker; remain available
for L to continue, redirect, or resume.

Ask L at every decision boundary that needs its broader user/session context.
Send evidence, recommendation, proposed default, parallel-safe work, and the
exact blocked action through a non-blocking parent transport when available;
continue safe independent research while waiting.

Return `READY_TO_IMPLEMENT`, `PROGRESS`, `NEEDS_MORE_RESEARCH`, or `BLOCKED`,
with decisive evidence, production path, existing mechanism, checked/excluded
hypotheses, reused/updated code-map keys, unknowns that affect the decision, and
the cheapest next action. Do not write code, mutate configuration, deploy, or
produce an unrelated architecture essay.
