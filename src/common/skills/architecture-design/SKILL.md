---
name: architecture-design
description: Design a working solution when boundaries, data ownership or costly assumptions remain uncertain; test pivotal choices, independently challenge the design, then simplify into complete outcomes and dispatchable tasks.
---

# Design a working solution, then make it smaller

Use for a selected architecture task or when a wrong structural choice would
make implementation expensive to redo. A clear bounded change can proceed through
the existing implementation route. Scale design effort to the uncertainty that
could change the solution; do not fill out stages merely because this skill exists.

## Recover current inputs and applicable learning

Begin with the latest objective and corrections, actual project state and
constraints, and relevant tested lessons, skills and outcomes from the existing
indexes. Retrieve the few records that could change this decision before
redesigning; do not scan the full history or load every skill. Verify freshness
against current source, runtime and user intent. Keep project facts, proposed
product improvements and reusable LHC method changes distinct. Prior guidance is
evidence to assess, not authority over the current request.

## Establish what must work

Start with the accepted user outcome and the actual consumer path. Describe a
coherent solution that can achieve it before distributing implementation tasks.
Identify the properties that matter for this use: observable behavior, boundaries,
data ownership and lifecycle, integration contracts, and relevant failure behavior.
Distinguish required properties from desirable extensions. An ideal target helps
expose dependencies; it does not authorize features outside the selected scope.

Trace existing components and constraints before introducing new ones. State the
costly assumptions: which wrong choice would force a migration, invalidate an
interface or prevent the user from reaching the goal? Compare practical alternatives
against those properties and the cost of changing course. Preserve a useful
existing design when evidence supports it.

## Buy evidence before expensive implementation

For each pivotal uncertainty, choose the smallest probe whose possible results
would change the decision. State the question, observable result and resulting
choice before running it. Use a contract experiment, representative data sample,
failure reproduction or focused prototype as appropriate. Stop a probe when the
decision is sufficiently supported; an open-ended technology survey is not progress.

Build an early executable skeleton across the real entry point, consequential
boundaries and observable result before investing in broad implementation. It may
exercise a narrow case, but must reach the actual integration at issue. Label
simulated dependencies and remaining gaps; a mock-only path cannot settle a real
integration risk. This skeleton is architecture evidence, not completion of the
accepted product scope. Keep or discard prototype code according to its fitness.

## Challenge the decision and the improved synthesis

Use a fresh independent challenger through `../challenge-decision/SKILL.md` with
the raw objective, constraints, proposed design and probe evidence. Ask for
counterexamples and better alternatives, not endorsement. For difficult competing
approaches where additional independent reasoning can change the choice, use
`../council/SKILL.md`.

Revise or synthesize the design using substantive findings. Have the independent
challenge address the resulting design and any new assumptions; approval of its
ingredients does not establish that their combination works. Resolve decisive
disagreement with a targeted check when possible. Record remaining uncertainty
and the condition that would reopen the decision. Stop designing when pivotal
choices have adequate evidence for the next investment, not when all uncertainty
has disappeared. Routine engineering choices remain with Lead.

## Simplify into complete outcomes, then dispatch

Derive a practical design from the working target. Build a YAGNI ladder whose
rungs are complete, observable user outcomes, each adding justified value or a
required property. Remove speculative flexibility, duplicate layers and optional
features before cutting behavior needed for the accepted outcome. Record what
was discarded and why. A smaller rung is an intermediate delivery unless it
already meets the user's selected scope; never rename partial work as completion.

Use `../decompose-and-dispatch/SKILL.md` to turn the next complete outcome into
coherent measurable tasks with owned paths/resources, acceptance checks, dependencies,
and estimates explained by work, proof and uncertainty. Use
`../model-routing/SKILL.md` for suitable actual models. Resolve shared contracts
before parallel mutation. Show which ready tasks actually run together under
available capacity and which must wait; a drawn DAG is not a dispatch receipt.
Verify the combined result at joins. No universal stage count, task duration or
mandatory batch size follows from this method.

## Learn from the working result

Verify the outcome through `../user-testing/SKILL.md`. Compare the real behavior
with the properties and assumptions that drove the design. Preserve both feedback
loops: project/product defects return to an in-scope repair, regression check and
fresh real-use attempt; reusable friction or successful methods in LHC itself
return through `../improve-workflow/SKILL.md` and the active SELF_IMPROVE protocol.
Verify a method change independently and check its next applicable reuse before
claiming durable improvement. Pending reuse stays pending; do not invent it.

Repair the smallest failing boundary and revisit the architecture only when
evidence warrants it. Keep the selected design, decisive evidence, deferred
choices and next delivery in the existing task record; a separate architecture
dossier is optional. Make validated learning retrievable through the existing
index. Feed changed assumptions back into task boundaries and model allocation
before further dispatch.
