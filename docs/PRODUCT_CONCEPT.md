# Last Human Commit: product concept

Last Human Commit (LHC) gives AI coding agents a work method for turning a
person's intent into a verified change in the project's configured shared
development history. Its finish line is a result someone can use, supported by
evidence from the real consumer path and delivered through the project's
permitted integration route.

LHC defines how the work is understood, planned, executed, checked and handed
into that history. It does not own the product backlog, decide what work a
project should request, or launch a particular harness or agent session; those
belong to the project and the surrounding harness/session system.

## One lifecycle, at different depths

Quick and Full describe how much decision work a task needs, not separate
protocols or different destinations. Both follow this lifecycle:

<!-- lhc-workflow-step:outcome -->
### Start with human intent

Recover the requested result and its latest corrections. Name who benefits,
what changes, what failed before, and where the result can be tried.

<!-- lhc-workflow-step:route -->
### Choose the shortest responsible route

Use current project evidence to choose the smallest route that can prove the
result. Work directly when the path is clear; investigate or compare options
when an unresolved choice could materially change the outcome or cost.

<!-- lhc-workflow-step:execute -->
### Do the work with the right boundaries

Make the needed change while preserving other active work, data and ownership.
Plan small work in roughly 15-minute pieces when decomposition helps; this is a
planning target, separate from reporting checkpoints and execution limits.

<!-- lhc-workflow-step:verify -->
### Verify the real result

Check the claim at the actual consumer path, fix failures within the owned
scope, and keep source checks, deployment, consumer behavior and acceptance as
separate evidence.

<!-- lhc-workflow-step:deliver -->
### Deliver into shared history

Use the project's configured integration and publication route. Report what is
verified, what remains unverified, and any exact external blocker; a commit or
review alone is not the user result.

Quick is the direct, proportionate route when the outcome and implementation
path are clear. Full adds deeper independent research, a working-to-ideal-to-
YAGNI plan, a quota-aware council and bounded dispatch for large or uncertain
work. When a material product, architecture or migration choice remains, the
decision method in `templates/FULL_CYCLE.md` is a conditional depth inside Full,
not another lifecycle. Skip that comparison when one route is already clear.

The Full depth track is adaptive: use the parts that resolve the task's
uncertainty and risk, and keep the five lifecycle stages as the shared spine.
It is not a required checklist for every Full task.

<!-- lhc-full-depth-step:research -->
### Research current code

Read the current project code and relevant constraints before choosing how to
change it. Research is deeper when the task is large or uncertain.

<!-- lhc-full-depth-step:working-solution -->
### Build a working solution

Describe the complete route that solves the requested result with the evidence
available now.

<!-- lhc-full-depth-step:ideal-version -->
### Consider the ideal version

Identify what a more complete version would improve and why that benefit
matters to the person using the result.

<!-- lhc-full-depth-step:yagni-minimum -->
### Choose the useful minimum with YAGNI

Keep the essential value of the ideal version and defer additions that do not
help prove or deliver this task's result.

<!-- lhc-full-depth-step:frontier-council -->
### Challenge unresolved choices

When materially different routes remain, use independent challenge or a
quota-aware council to surface trade-offs and stronger alternatives. Skip this
step when current evidence already makes the responsible route clear.

<!-- lhc-full-depth-step:small-pieces -->
### Split useful work into small pieces

When decomposition helps, shape pieces that can usually be completed in about
15 minutes, with a clear owner and checkable result.

<!-- lhc-full-depth-step:worker-dispatch -->
### Dispatch bounded Worker tasks

Use parallel Workers for independent, well-bounded work when it reduces total
time or improves evidence; keep one owner for each shared resource.

<!-- lhc-full-depth-step:review-manual-test -->
### Review and manually test

Review the implementation and exercise the relevant user scenario manually;
automated checks alone do not prove the consumer result.

<!-- lhc-full-depth-step:shared-history -->
### Push and integrate into shared history

Use the configured route to push or open a PR, then merge into the project's
shared development history when that route permits it.

## The boundary of the method

The project's own roadmap/backlog determines which work is wanted and owns its
priority. The active harness and session system determine how an agent is
launched, what tools it has and which approval policy applies. LHC works within
those boundaries and does not replace them.
