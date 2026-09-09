# Self-improve evolution loop

## Start with applicable learning

At cycle start, review the latest user inputs and current project state, then
retrieve relevant verified lessons from existing project and LHC indexes. Check
their conditions and freshness before reusing them; record only decisive applied
lessons or rejected stale assumptions in the current task. No full-history scan,
duplicate memory store or forced retrospective is required. Respect the active
harness's memory-write policy and existing storage owner.

## Two improvement loops

Product improvement: observed user problem → in-scope repair → regression check
→ fresh real use → update relevant project knowledge. Optional product expansion
stays Proposed unless selected. Use user-testing/focus-groups for real evidence.

LHC improvement: repeated method friction or useful success → change at the owning
skill/tool/instruction → independent verification → retrievable publication within
actual authority → next applicable reuse. Product success does not by itself prove
the method improved. The next cycle consumes applicable outcomes of both loops.

Run this procedure at the next observable work boundary, including between tool
calls inside a long slice, when any trigger occurs:

- 120 wall-clock minutes have elapsed during unfinished work since the previous
  completed checkpoint (or objective/session start). New cycles and compaction
  never restart this timer. An idle agent checks on resumption; do not wake it.

- the user corrected LHC's behavior or instruction interpretation;
- the route materially failed, substantially exceeded its maximum, or required RETHINK;
- the same friction, command failure, or missing capability repeated;
- the user explicitly requested a retrospective;
- a method produced a reusable, unexpectedly effective result.

Short ordinary successful tasks add nothing. This is a compact evidence record plus a
bounded patch loop, not a second planning cycle and not permission to expand the
user's task.

At every cycle completion, and at meaningful failure or handoff, inspect whether
there is a substantive signal. For one, use `../skills/improve-workflow/SKILL.md`. No signal
means no ritual entry. The outcome is a retrievable change with evidence and
later applicable reuse, not merely a growing journal.

Hermes uses its native post-response memory/skill review and `/learn` as the
storage/execution owner, but is not exempt from the mandatory cadence. Invoke
and verify that owner when due; do not add a duplicate memory system.
For a changed method, verify the native owner actually saved and retrieved the improvement; a native
hook alone does not prove learning occurred.

## Mandatory checkpoint, bounded to useful work

The Overseer demands business results. Learning is a corrective tool, never a
deliverable substituted for the accepted outcome or justification for CONTINUE.
Every maximum overrun still requires an immediate route decision; substantial
overrun means that decision's bounded continuation also misses its limit or the
accepted delivery forecast is no longer credible. Do not wait two hours after
an earlier trigger.

First compare the original accepted outcome, cumulative elapsed time and total
forecast with demonstrated user results. Name repeated operations, self-caused
rework and remaining blockers. Select at most one useful method correction;
prefer removing a redundant step or changing the next action over adding rules.
Budget this inspection to five minutes. Safe shutdown, rollback and delivery of
already accepted work may complete before the checkpoint; do not interrupt them
or start another feature to evade the checkpoint.

If a concrete signal exists, apply one authorized owning-method change, verify
it with the original failure or closest reproducible check, and record its path
and evidence in the existing task or session guard (a task card is optional).
Delegate a larger unrelated repair as Proposed
with an owner and next check; it must not consume the product task indefinitely.
If there is no useful correction, record a short evidence-backed no-change
decision. A timer mandates inspection, not fabricated learning or unnecessary
edits. Repeated no-change despite the same failure is a failed checkpoint.

The guard's explicit acknowledgement records observation, method change or
justified no-change, verification and next route. Emitting a notification,
writing a retrospective, restarting a cycle, or promising future improvement
does not close it. A due checkpoint stays due until acknowledged; never report
verification or later reuse that did not happen. This checkpoint does not grant
new memory-write, publication, destructive-action or deployment authority.

## Record

At a triggered checkpoint, use the existing task record or session guard for a
compact entry. No task card or separate learning journal is required. Existing
native learning stores remain their own owners; preserve memory permissions.

Record only:

1. observable friction;
2. the owning instruction and the minimal proposed patch: the exact file and
   replacement text or diff, or the evidence-backed reason no change is useful;
3. missing skill/MCP/tool, if any;
4. repeated operation/error count and evidence;
5. verification canary: the smallest real check that proves the patch helps
   (one repo validator, one real-surface check, or one Arena arm for
   workflow-level claims);
6. state: `fixed now`, `Proposed`, `needs human decision`, or `not actionable`.

Compare recent entries first. Update an existing fingerprint rather than
creating a duplicate.

## Apply — reviewed commits

Authorized local workflow improvements can be implemented and tested without a
new human coordination cycle. Keep the scope and evidence in the current task,
or use a dedicated self-evolve task when the change is unrelated to the accepted
outcome. Preserve user policy and active-harness permissions; changing a method
never grants new publication, deployment or destructive authority.

Close the loop:

1. collect entries in `Proposed` state;
2. apply the minimal patch set to the owning source files;
3. run the repo validators and each patch's verification canary;
4. land the whole step as exactly one reviewed commit per evolution step and
   record the retrievable skill/tool location and successful verification;
5. at the next applicable task, retrieve and reuse the change, record the outcome
   in the same entry, then mark it `fixed now`; distinguish `verified, awaiting
   reuse` from proven reusable learning. Refine or retire ineffective methods.

Bound the loop like an evaluator-optimizer: at most three refinement iterations
per patch, quality floor = the verification canary passes. A patch that still
fails its canary after three iterations is reverted and marked
`needs human decision`. Repeated errors with the same fingerprint become one
guard line in the owning instruction instead of a new entry.
