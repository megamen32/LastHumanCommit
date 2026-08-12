# Business-first cost-aware planning

Load only when planning adds more decision value than implementation delay.
Simple and clear work does not need a planning artifact.

## Decision order

1. State the user's current business outcome and accepted Definition of Done.
2. Trace the actual production consumer path enough to identify the next change.
3. Name the shortest safe business canary and cheapest sufficient proof.
4. Choose direct Lead work or delegation by total expected cost.
5. Add governance only for a concrete risk whose expected loss exceeds gate
   cost.

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
or resume the same Worker, ask Overseer for a genuinely valuable route verdict,
or exceptionally cancel for active harm/conflict/stuck state.

A task maximum overrun requires an evidence-based route decision. Do not merely
increase the estimate. Continue only for one concrete shortest action with a
credible canary delta; otherwise change route, return to the accepted MVP, or ask
the user for a necessary business choice. Estimate overrun alone is never
authority to kill an agent.

## Least cost-to-canary

Rank actions by expected real canary movement against wall-clock, scarce-model
tokens, handoff/context cost, process maintenance, retries, human interruption,
and wrong-path risk.

Lead acts directly when delegation costs more than the next proof. Delegate
when a lower-cost Worker can sustain useful work, independent parallelism pays,
specialized capability is needed, or isolation has concrete review value. Use
the lowest sufficient model and resume the same Worker when its context remains
valuable.

Decompose only at real ownership, dependency, or acceptance boundaries. A
coherent Worker assignment may exceed 20 minutes; checkpoint it every 20. Do not
split one vertical fix into artificial research, implementation, review, and
task-card repair slices merely to satisfy a timer.

Persist a task/result artifact only when recovery, handoff, reuse, audit, or
rediscovery cost justifies it. Keep it compact and current. No elapsed-time
threshold requires a file or commit.

## Two compressed approaches

When a real human route decision remains, propose exactly two genuinely
different approaches. Do not make ideal, normal, and MVP three selectable
plans. For each approach perform one internal compression: `ideal/full -> normal
-> YAGNI/Pareto MVP`.

1. sketch the ideal/full route;
2. reduce it to a normal sufficient route;
3. remove every element not required by the accepted claim, current canary, or
   essential boundary to produce the YAGNI/Pareto MVP.

Show the human only the two compressed MVP routes with their discarded scope,
advantages, disadvantages, minimum/maximum active time, dependencies, and real
canary. Recommend the least-cost YAGNI/Pareto route by default. Skip the two-
approach presentation entirely when one route is already obvious and reversible.

Load `$task-decomposition` when work still spans parallel or multiple cycles.
Decompose into the smallest independent business-verifiable leaves; maximize
parallelism only where dependencies, decisions, and writes do not conflict.
