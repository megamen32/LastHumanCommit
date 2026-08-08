# Self-improve retrospective

This protocol is triggered only when at least one concrete event occurred:

- the user corrected LHC's behavior or instruction interpretation;
- the route materially failed, exceeded its maximum, or required RETHINK;
- the same friction, command failure, or missing capability repeated;
- the user explicitly requested a retrospective.

Ordinary successful tasks add nothing. This is a compact evidence record, not a
second planning cycle and not permission to expand the user's task.

Hermes is excluded: its native post-response memory/skill review and `/learn`
flow own this concern. Do not run a duplicate LHC loop through Hermes.

## Record

Before the final answer on a triggered non-Hermes task, append one entry under
12 lines to `.agents/last-human-commit/self-improve.md`; if project writing is
unsafe, put the same compact entry in the root task record.

Record only:

1. observable friction;
2. the owning instruction and smallest proposed correction;
3. missing skill/MCP/tool, if any;
4. repeated operation/error count and evidence;
5. state: `fixed now`, `Proposed`, `needs human decision`, or `not actionable`.

Compare recent entries first. Update an existing fingerprint rather than
creating a duplicate. Do not silently rewrite LHC, install tools, or expand
scope from this protocol.
