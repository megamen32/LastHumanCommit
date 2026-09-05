# Material-decision cycle

Use this view only when a material product, architecture, migration, or
expensive-wrong-path choice remains after the real production path is known.
Full is not a synonym for long, important, polished, or release-bound work.

## Business claim

Latest user outcome:
Current inputs / constraints / applicable verified product and LHC learning:
Accepted MVP / Definition of Done:
Exact real user/business canary:
Cheapest sufficient proof:
Actual production consumer path:
Confirmed scope:
Explicit exclusions:
Current blocker:
Initial minimum / maximum active minutes:
Cycle estimates (each named route/canary/review/rollout):
Time-guard state:

## Least-cost route

Smallest reversible change that moves the canary:
Why direct Lead work or delegation is cheaper:
Chosen model/agent and why it is sufficient:
First 20-minute reporting checkpoint:
Stop when:
Redirect when:

## Material options — only when a route choice matters

Record exactly two genuinely different approaches. For each, compress the
ideal/full route to normal and then to the YAGNI/Pareto MVP. Present the two
compressed variants; never invent a third option to fill a template. Skip this
comparison when one route is already obvious and reversible.

For each option:

- business result delivered now;
- time/cost to first canary;
- reuse and migration economics;
- wrong-path and rollback cost;
- consciously omitted quality dimensions;
- exact proof and smallest execution route.

Overseer consult trigger, if any:
Initial independent Overseer audit / operational decision:
Decision under active-harness policy:
Dependency lanes / owned resources / integration joins:
Canonical branch / worktree / immutable base / owner for isolated lanes:
Decision model / executor models / suitability and fallback reasons:
Per-leaf minimum/maximum / basis / specific uncertainty:
Actual concurrent lanes / available slots / reasons for serialization:
Summed effort versus capacity-respecting critical path (show arithmetic):
External waits / evidence or unknown:

Do not derive task size from the 20-minute checkpoint. The total follows the
dependency and capacity plan, not a broad global buffer.

## Delivery order

1. Trace the actual consumer call chain.
   For architecture, use architecture-design: review inputs, probe pivotal risks,
   verify early end-to-end integration and challenge the improved synthesis.
2. Obtain the initial independent Overseer audit, then implement the thinnest
   working vertical on that path.
3. Run the real canary as early as safely possible.
4. Fix only the first claim-blocking failure.
5. Run proportional direct-regression checks.
6. Run one coherent technical review, then the mandatory fresh independent Tester
   on the changed real user journey. Repair in-scope findings, recheck technical
   behavior and repeat affected real use until accepted. Lead's own canary and
   unit tests cannot replace this Full gate.
7. Use focus groups when diverse goals add value or were requested; close their
   repair/retest loop while deferring subjective feature preferences. Extra
   hardening or proof must justify its cost for the accepted claim.

Every 20 active minutes is a reporting checkpoint, not a Worker lifetime limit.
The Worker reports progress, business delta, blocker, and the shortest next
action. Prefer continuing, redirecting, or resuming the same Worker. Cancellation
is exceptional.

Use the harness wait/join tool for required children. Do not complete the task
while a required child is non-terminal.

Workers ask L at each decision boundary through a non-blocking parent transport
when available, include recommendation/proposed default, and continue safe
independent work while waiting. L owns and promptly returns the decision.

At every crossed wall-clock hour while active, run `lhc_time_guard.py` and report
real tasks closed, business delta, completed files, planned versus actual time,
blockers, delaying gates/instructions, time-control evidence, and the shortest
next route. Crossing a cycle maximum emits the full overrun diagnostic.

## Result

Business result:
Claim strength actually proven:
Source/test evidence:
Deployment state:
Real canary evidence:
Tree clean / pushed / deployed:
Optional deferred hardening/findings:
Current workspace/branch:
Commit (each completed step):
