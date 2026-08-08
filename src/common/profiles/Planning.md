# Cost-aware planning

Use for every non-Direct task.

## Estimates

Record UTC+3 start and one immutable initial `minimum / maximum active minutes`
range. Do not add optimistic/likely/pessimistic variants. Append a revision only
when new evidence changes the route, with old/new range and one-line reason. At
each Worker return compare elapsed work and business delta with the current
maximum. An overrun requires a fresh Overseer verdict; increasing the number
alone never authorizes the same route.

## Decomposition

L orchestrates; Workers search and implement. Every Worker assignment has one
mode, one acceptance gate, and maximum <=20 active minutes. Split it first when
it contains an unresolved architecture/interface decision, unknown dependency,
multiple gates, overlapping write ownership, no independent check, or a larger
maximum.

A whole plan may exceed 60 minutes only as a known graph of <=20-minute slices
with explicit dependencies and joins. A single unresolved block above 60
minutes means more `Worker(mode=research)`, not one long assignment.

Parallelize independent write sets and stable contracts. Sum parallel quota cost
but use the critical path for wall-clock. Never parallelize overlaps or
unresolved shared interfaces.

## Least Cost-to-Canary

Choose the next action by real expected canary movement against scarce-model
tokens, wall-clock, tool overhead, retries, and human interruptions. Strong
models make short decisions; the lowest sufficient Worker model searches,
edits, and runs checks. Do not inherit L's model by default. Record model or
quota only when it affects cost, capability, or recovery.

Before a child call load the harness `subagent_instructions_template` and send a
compact package: role/mode, root task path, goal, decisive evidence,
allowed/excluded paths, one acceptance check, minimum/maximum estimate, stop
conditions, and return format. The child appends detailed evidence and its
result to the assigned task file and returns only TL;DR; it does not create a
second task file.

Resume the same Worker from research into its implementation lane when proven
supported; otherwise pass the compact Research section to a fresh Worker.
Overseer, Reviewer, Tester, and Critic are independent gates and start fresh as
required by their roles.

A Worker returns `NEEDS_REDECOMPOSITION` before a vague/oversized package and
`NEEDS_RETHINK` on maximum overrun, two failed hypotheses, or a new architecture
decision.
