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

The LHC change/record procedure is triggered only when at least one concrete event occurred:

- the user corrected LHC's behavior or instruction interpretation;
- the route materially failed, exceeded its maximum, or required RETHINK;
- the same friction, command failure, or missing capability repeated;
- the user explicitly requested a retrospective;
- a method produced a reusable, unexpectedly effective result.

Ordinary successful tasks add nothing. This is a compact evidence record plus a
bounded patch loop, not a second planning cycle and not permission to expand the
user's task.

At meaningful completion, failure or handoff, consider whether there is a
substantive signal. For one, use `../skills/improve-workflow/SKILL.md`. No signal
means no ritual entry. The outcome is a retrievable change with evidence and
later applicable reuse, not merely a growing journal.

Hermes is excluded: its native post-response memory/skill review and `/learn`
flow own this concern. Do not run a duplicate LHC loop through Hermes.
Verify the native owner actually saved and retrieved the improvement; a native
hook alone does not prove learning occurred.

## Record

Before the final answer on a triggered non-Hermes task, append one entry under
12 lines to `.agents/last-human-commit/self-improve.md`; if project writing is
unsafe, put the same compact entry in the root task record.

Record only:

1. observable friction;
2. the owning instruction and the minimal proposed patch: the exact file and
   replacement text or diff. An entry without a patch is state `not actionable`;
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
