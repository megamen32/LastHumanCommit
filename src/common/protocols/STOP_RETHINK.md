# Control checkpoint / redirect / rethink

Use this protocol when evidence suggests the current route may no longer be the
least-cost path to the user's accepted canary.

## Triggers

- task maximum exceeded without proportional business delta;
- two failed hypotheses or repeated fix/review cycles;
- production-path evidence contradicts the chosen implementation surface;
- the user repeats that the same P0 still fails;
- material scope or consequential authority is required;
- process, hardening, lifecycle repair, or proof strength grows without moving
  the accepted claim;
- a 20-minute Worker checkpoint reports uncertainty or a shorter route.

A trigger requires a control decision, not automatic cancellation or replacement.
Repeated failures, material drift and maximum overruns call for one concrete
route correction, with a fresh read-only Overseer when useful. Advice is never
a prerequisite or a permission receipt. Continue useful authorized work; do not
replace a removable blocker with another report or unchanged repeated check.
Use `REDECOMPOSE`, `CHANGE_MODEL`, `REFRESH_CONTEXT` or `COUNCIL` when the evidence
points to task boundaries, model suitability, degraded context or an unresolved
decision respectively. Ordinary technical choices remain Lead-owned.

## Decision

1. Restate the latest accepted result and proof strength.
2. Record actual business delta and total cost spent.
3. Identify whether one shortest continuation is credibly canary-reaching.
4. Prefer redirecting or resuming the same Worker when its context remains
   useful.
5. Change route, cut back to the accepted MVP, or ask one necessary business
   question when continuation is not justified.

Every 20 active minutes is a control checkpoint, not a Worker lifetime limit.
The Worker reports progress, business delta, blocker, and the shortest next
action. Cancellation is exceptional and allowed only for active harm,
conflicting writes, an obsolete duplicate, explicit user direction, or an
unrecoverably stuck child.

`STOP_SCOPE_DRIFT` applies only to concrete action outside the latest accepted
scope. Preserve evidence and stop that action; do not let stale P0s, old task
sections, or optional findings block current in-scope business work.

The user-facing rethink contains the blocker, evidence, original estimate versus
actual cost, business delta, genuinely different in-scope routes, and L's
shortest recommendation. Do not silently continue the failed route by changing
the estimate or terminology.

On supported Codex installations, a trusted enabled async PostToolUse hook
launches the existing Overseer at a due 30-minute boundary. It sees bounded
native user messages, raw actions/results, candidate plans and previous advice.
It returns one action/owner with `continue`, `redirect`, `wait_external` or
`need_fact`. A healthy build, genuine wait or requested audit may continue;
unknown progress is not no progress. The Lead acts/assigns that step or cites
an observed fact for rejecting it. The next review checks actual subsequent
behavior. No second review of the reviewer, new hold or gate is created.
Native new input/Interrupt/Stop/SessionEnd invalidate stale work. No idle wakeup.
Other harnesses retain the manual method, not an automatic-execution claim.
