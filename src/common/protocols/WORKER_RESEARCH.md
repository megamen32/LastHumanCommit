# Worker research protocol

Use only for `Worker(mode=research)`. This protocol is read-only.

## Goal

Reduce uncertainty until L can choose a route and split implementation into
concrete <=20-minute slices. Find the existing mechanism before proposing new
infrastructure.

## Method

1. Read the raw task objective, canary, scope, exclusions, and known evidence.
2. Locate the actual user path, owning files/symbols/config, interfaces,
   dependencies, and failure boundary.
3. Verify assumptions with the smallest useful probes. Prefer repository and
   live source-of-truth evidence over speculation.
4. Identify reuse, contradictions, unknowns, and the exact fact blocking a
   confident implementation package.
5. Propose an execution graph of independent slices. Every slice has one owner,
   owned paths, one acceptance check, dependencies/join point, and maximum <=20
   active minutes.

A whole plan may exceed one hour only as an understood graph of such slices. If
one unresolved block still appears to exceed one hour, return
`NEEDS_MORE_RESEARCH` and the next bounded probe; do not disguise uncertainty as
a long implementation estimate.

## Return

Return one of `READY_FOR_PLAN`, `READY_TO_IMPLEMENT`, `NEEDS_MORE_RESEARCH`, or
`BLOCKED`, followed by:

- decisive findings with `path:line`, symbol, command result, or dated source;
- existing mechanism and real canary blocker;
- checked and excluded hypotheses;
- unknowns;
- proposed <=20-minute slices and dependencies;
- recommended next probe or lane.

Do not write code, edit configuration, deploy, commit, or produce an architecture
essay unrelated to the decision.
