---
name: planning
description: Lead-owned business-first procedure for choosing the least-cost route to the next real canary.
---

# Planning

Use only when planning can materially reduce wrong-path or coordination cost.

## Three-pass design

When choosing a design, use `working solution -> ideal version -> 80%-value MVP`
even when there is only one practical approach. The architecture-design skill owns
the detailed method. An obvious tiny fix needs only a short pass, not a new form.
The 80% target concerns useful value, never incomplete implementation or silently
missing mandatory requirements.

## Procedure

Begin with current user inputs, project state and applicable verified product
and LHC learning from existing indexes. Verify freshness and use prior results
before redesign. Use `$architecture-design` for architectural decisions, risky
assumptions and the end-to-end path before substantial implementation.

1. Record the latest business outcome and accepted MVP Definition of Done.
2. Trace the actual production consumer path.
3. State the shortest real canary and cheapest sufficient proof.
4. Rank direct Lead work and delegation by wall-clock, scarce quota, handoff,
   retry, human interruption, and wrong-path cost.
5. Load `$task-decomposition` and `$decompose-and-dispatch` when parallel or
   multi-cycle work remains. Use `$model-routing` for actual model selection;
   hard decisions use the strongest suitable model before bounded execution.
6. Treat every 20 active minutes as a progress and route checkpoint, not an
   agent lifetime limit.
7. Give every declared work cycle an immutable minimum/maximum estimate and run
   the business time guard at observable checkpoints; report every crossed hour
   and original-maximum overrun.
   Derive that range from per-leaf work/proof and specific uncertainty. Show
   available slots and actual parallel dispatch; sum effort separately from
   capacity-respecting critical-path duration, with joins/testing/waits explicit.
   Twenty minutes is a checkpoint, not a task size; no unexplained doubled buffer.
8. Obtain the initial independent Overseer audit. Full includes coherent
   technical review and a fresh independent Tester; extra governance needs
   concrete risk-reduction value. Routine technical choices belong to Lead.
9. When a human route choice is useful, present exactly two genuinely different
   approaches. For each, use `working solution -> ideal version -> 80%-value MVP`:
   establish how it works, improve that design, then keep the smallest complete
   version with roughly 80% of the useful result. Implement that third version;
   state its retained value, deferred scope, cost and real acceptance check.
   This is one design sequence, not three builds or approval rounds. If the user
   requests the reasoning behind the plan, show the three passes in one plan.

## Do not

- Three design passes are not three selectable alternatives or approval rounds.
- When alternatives actually matter, apply the same sequence within each approach.
- Do not forbid Lead implementation when it is cheaper.
- Do not replace a route decision with a larger estimate.
