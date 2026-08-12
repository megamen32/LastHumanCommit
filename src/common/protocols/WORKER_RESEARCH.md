# Worker research protocol

Use only for `Worker(mode=research)`. Research is read-only and exists to find
the cheapest route to the next real business proof.

## Method

1. Read the latest user outcome, accepted proof strength, scope, exclusions, and
   known evidence.
2. Trace the actual production consumer path and owning files/symbols/config
   before inspecting nearby abstractions or proposed architecture.
3. Find the existing mechanism, first real blocker, and cheapest discriminating
   probe.
4. Stop once L can implement directly or assign a coherent execution lane. Do
   not continue toward repository completeness.
5. Recommend the shortest vertical action and proof, plus only decision-relevant
   unknowns.

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
hypotheses, unknowns that affect the decision, and the cheapest next action. Do
not write code, mutate configuration, deploy, or produce an unrelated
architecture essay.
