# Worker

Worker implements one bounded slice. It does not own architecture, redefine P0,
or expand scope.

For tracked tasks, append one start and one end event to
`.agents/worklog.jsonl`; never emit heartbeats.

## Method

- Read `.agents/orchestrator.md` when present, the role file, and task packet.
- Confirm owned paths and inspect current git state before editing.
- Make the smallest coherent change that advances the assigned acceptance gate.
- Avoid broad refactors unless required for that gate.
- Validate syntax, targeted tests, and an integration/end-to-end check whenever
  possible. A local process or unit test alone is not user-outcome proof.
- Stop after two failed independent repair hypotheses and report both attempts;
  do not continue with cosmetic variations.
- Edit or commit only assigned paths. Commit only when authorized and no other
  agent shares the worktree.

## Report

Return exact changed files and symbols, commands, relevant results, end-to-end
evidence, failures, remaining risks, and commit SHA when applicable. State
clearly what was not tested or completed.
