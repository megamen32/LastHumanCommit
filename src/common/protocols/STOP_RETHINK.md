# STOP / RETHINK

Use this protocol when the current route is no longer a bounded least-cost path
to the user's canary.

## Triggers

Trigger immediately when any of these occurs:

- the current minimum/maximum estimate is exceeded;
- a proposed Worker assignment exceeds 20 maximum active minutes;
- one unresolved block is estimated above 60 minutes;
- two independent hypotheses or repair slices fail;
- a completed wave produces no real business-canary delta;
- evidence conflicts with the selected architecture;
- the user repeats that P0/P1 still fails;
- scope must expand materially;
- process, framework, safety, observability, or cleanup work grows without user
  progress.

Do not silently revise the estimate and continue. Preserve compact evidence in
the same task file and request a fresh Overseer audit.

## Independent gate authority

The user is the only authority over Overseer and Critic. L invokes them but
cannot prescribe, narrow, rewrite, or override their verdict. Every invocation
is a fresh no-history child with raw user context passed explicitly.

`RETHINK`, `STOP`, `STOP_SCOPE_DRIFT`, `STOP_MISSING_CONTEXT`, or unanswered
questions block further action and completion claims. L may provide new evidence
to a new audit or ask the user; it may not continue the same route by changing
wording.

## Terminal scope drift

`STOP_SCOPE_DRIFT` is terminal for unauthorized expansion beyond the original
request, confirmed scope, exclusions, or failed canary's dependency chain.

1. Preserve evidence without cleaning or changing conflicting work.
2. Report the exact mismatch to L and the user.
3. Record the decision in the same task file with UTC+3 time and evidence.
4. Do not start research, alternatives, implementation, or review outside scope.
5. Resume only after explicit human scope confirmation is stored in the task.

Before plan selection, communicate in Russian. After selection, execution
updates are in English.

## Architectural RETHINK

For non-scope triggers, L may assign bounded `Worker(mode=research)` slices to
find a fundamentally different path inside confirmed scope. There is no Explorer
role.

The user-facing RETHINK contains only:

1. exact blocker and evidence;
2. original estimate versus actual route;
3. why the selected path has not moved the canary;
4. fundamentally different in-scope paths when they really exist;
5. minimum/maximum estimate, risk, and expected result for each;
6. L's recommendation;
7. one question only when human choice is genuinely required.

Do not silently resume the failed path after sending RETHINK.
