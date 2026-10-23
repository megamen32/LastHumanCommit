# Business-first cost-aware planning

Use this profile to choose an efficient route for a Lead-owned plan. Every
authorized development task has a plan before implementation; simple bounded
work may need only one short leaf and minimal research. Read-only questions,
investigations and status requests do not need a development plan.

## Decision order

First retrieve current inputs and applicable verified product/LHC learning from
their existing owners. Confirm freshness against the project; stale lessons do
not override new instructions. For architecture, use
`../skills/architecture-design/SKILL.md` before allocating implementation.

1. State the user's current business outcome and accepted Definition of Done.
2. Trace the actual production consumer path enough to identify the next change.
3. Name the shortest safe business canary and cheapest sufficient proof.
4. Explicitly select quickfix or fullcycle from actual scope and risk; an
   assigned leaf does not select the parent's mode or own the plan.
5. Create and present the plan before implementation, without waiting for a
   second approval when execution is authorized.
6. Use `../skills/model-routing/SKILL.md` and
   `../skills/decompose-and-dispatch/SKILL.md` to assign every task to an allowed
   Worker: fast tier glm-5.3-flash or minimax-3.1-flash, frontier tier gpt-6-luna,
   glm-5.3 or gpt-6.1-sol, resolved to an exact live
   catalog ID. The Lead coordinates only and never executes. No silent fallback.
7. Consult the Overseer when a concrete blocker or route uncertainty would benefit
   from independent advice. Add technical review and fresh independent testing when
   the change’s risk and claim justify their cost.

Do not plan a horizontal layer before the first vertical user path. A plan is
successful when it reduces wrong-path risk or coordinates useful parallel work;
its completeness is not a product result.

## Estimates and checkpoints

Load `../protocols/TIME_CONTROL.md`. Every declared work cycle has its own
immutable minimum / maximum estimate before execution. Record UTC+3 start and
do not add optimistic/likely/pessimistic variants. Tiny commands may share one
coherent enclosing-cycle estimate; estimates are for control, not ceremony.

Call `../tools/lhc_time_guard.py` at cycle start and every observable
checkpoint. At every crossed wall-clock hour while the task remains active, L
reports closed real tasks, business delta, completed files, planned versus
actual time, blockers, delaying gates/instructions, control evidence, and the
shortest next route.

Every 20 active minutes is a control checkpoint, not a Worker lifetime limit.
The Worker reports progress, business delta, blocker, and the shortest next
action. The expected total range may exceed 20 minutes. L may continue, redirect
or resume the same Worker, ask the Overseer for useful route advice,
or exceptionally cancel for active harm/conflict/stuck state.

A task maximum overrun requires an evidence-based route decision. Do not merely
increase the estimate. Continue only for one concrete shortest action with a
credible canary delta; otherwise change route, return to the accepted MVP, or ask
the user for a necessary business choice. Estimate overrun alone is never
authority to kill an agent.

## Least cost-to-canary

Derive the task estimate from coherent leaves, never from the checkpoint period.
Each leaf records min/max, work/proof basis and the uncertainty between bounds.
Show actual parallel waves, available slots and why any ready work is serialized.
Sum leaf effort separately from the capacity-respecting critical path; list
integration, review, real testing and external waits explicitly. The reported
total needs its arithmetic, not an arbitrary broad range or doubled buffer.
If an unknown makes a range wide, use the cheapest probe to narrow it before
allocating a long implementation lane.

Rank actions by expected real canary movement against wall-clock, scarce-model
tokens, handoff/context cost, process maintenance, retries, human interruption,
and wrong-path risk.

The Lead never executes directly. Assign every inspection, edit, check and delivery
step to a Worker, even when small. Use only the allowed tiers — fast tier
glm-5.3-flash or minimax-3.1-flash, frontier tier gpt-6-luna, glm-5.3 or
gpt-6.1-sol — resolved to exact live catalog IDs before dispatch; do not silently
substitute.
Resume the same Worker when its context remains valuable. An assigned leaf does not
recursively hire.
Decompose only at real ownership, dependency, or acceptance boundaries. A
coherent Worker assignment may exceed 20 minutes; checkpoint it every 20. Do not
split one vertical fix into artificial research, implementation, review, and
task-card repair slices merely to satisfy a timer.

Persist a task/result artifact only when recovery, handoff, reuse, audit, or
rediscovery cost justifies it. Keep it compact and current. No elapsed-time
threshold requires a file or commit.
For delegated work, however, the canonical assignment, progress, decision/blocker
and result receipt are always written under the owning task directory as defined
by `../protocols/ORCHESTRATION_RECORDS.md`; routine chat updates are not their
durable record.
The Lead retains plan decisions and may name exactly one Artifact Writer to
write task/progress/graph/HTML/Markdown from verified Lead decisions. Execution
Workers own only their assigned result/progress files. Keep the plan-file writer
exclusive until the Artifact Writer hands back the revision for Lead review.

## Two compressed approaches

Routine technical route selection belongs to Lead. Use Adviser or
`../skills/council/SKILL.md` when an allowed-model adviser can resolve an expensive
uncertainty. Challenge the final synthesis and verify decisive
claims; consensus alone is not acceptance. Ask the human only for a missing
business fact, preference or authority that changes the decision.

For each design use `working solution -> ideal version -> 80%-value MVP`:

1. outline an ordinary complete working solution from current inputs;
2. improve that solution to its ideal version and identify the value and cost;
3. keep the smallest fully working version retaining about 80% of the useful
   result, with an explicit acceptance check and consciously deferred improvements.

Implement the third version by default. These are three design passes, not three
implementations or approval rounds. An 80%-value target does not permit missing
already accepted mandatory outcomes; the percentage is a planning orientation,
not a measurement of completion.

When a real human route decision remains, propose exactly two genuinely different approaches.
Apply the same three-pass sequence within each and explain the recommended minimum,
discarded scope, advantages, disadvantages, cost and real canary. Recommend the least-cost YAGNI
route that retains the needed result. Skip the two-approach presentation when one
route is obvious; the design method still applies briefly to that single solution.

Load `$task-decomposition` when work still spans parallel or multiple cycles.
Decompose into the smallest independent business-verifiable leaves; maximize
parallelism only where dependencies, decisions, and writes do not conflict.
