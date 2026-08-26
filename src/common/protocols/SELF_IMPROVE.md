# Self-improve evolution loop

This protocol is triggered only when at least one concrete event occurred:

- the user corrected LHC's behavior or instruction interpretation;
- the route materially failed, exceeded its maximum, or required RETHINK;
- the same friction, command failure, or missing capability repeated;
- the user explicitly requested a retrospective.

Ordinary successful tasks add nothing. This is a compact evidence record plus a
bounded patch loop, not a second planning cycle and not permission to expand the
user's task.

Hermes is excluded: its native post-response memory/skill review and `/learn`
flow own this concern. Do not run a duplicate LHC loop through Hermes.

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

Proposed patches are never applied silently inline. They land in batches through
a dedicated self-evolve task:

1. collect entries in `Proposed` state;
2. apply the minimal patch set to the owning source files;
3. run the repo validators and each patch's verification canary;
4. land the whole step as exactly one reviewed commit per evolution step and
   move the entries to `fixed now`.

Bound the loop like an evaluator-optimizer: at most three refinement iterations
per patch, quality floor = the verification canary passes. A patch that still
fails its canary after three iterations is reverted and marked
`needs human decision`. Repeated errors with the same fingerprint become one
guard line in the owning instruction instead of a new entry.
