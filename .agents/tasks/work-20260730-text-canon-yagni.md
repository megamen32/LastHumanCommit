# Text-first LastHumanCommit canon

Outcome: LastHumanCommit remains a simple copy-paste text canon. Agent Fleet or
another external adapter owns installation, synchronization, scheduling, and
harness-specific deployment.

Acceptance:
- The full-cycle path requires research, three plans in the order ultimate,
  normal, YAGNI MVP, and explicit human selection before implementation.
- Short, obvious bugfix, and emergency paths stay fast.
- Full cycle requires bounded subagents and records model-class guidance.
- Planning documents the three WSFF program-design views.
- A tested commit gets a Russian mobile review summary and a 30-minute
  deploy-eligibility handoff to an external scheduler.
- Core instructions work by copy-paste without requiring an installer or
  runtime service.
- Every confirmed repository defect is resolved, removed with retired legacy
  surfaces, or retained with an explicit external owner.

Workflow: explore -> advise -> human-select -> work -> review -> commit

started (UTC+3): 2026-07-30T18:22:32+03:00
Executor: L
PID: 294519
Harness: codex
session identifier: current Codex task
Next action: commit the reviewed text-only rewrite, reconcile origin history,
then record the final commit and review handoff.

## Notes

- User selected YAGNI and rejected synchronization/installation machinery in
  this repository.
- Preserve existing dirty work and never read or stage `.env`.
- Reconcile the remote-only README commit without adopting its stale content.
- Red: the new validator first failed because `CANON.md` was absent.
- Green: `python3 tests/validate.py` passes nine text contracts;
  `git diff --check` passes.
- Removed installer, rendered entries, installer tests, versioned runtime
  surface, and obsolete install plans. This closes installer boundary, parser,
  path-rendering, release-state, entry-drift, and README bootstrap defects in
  this repository; Agent Fleet owns any future adapter implementation.
- Unified `todo -> work -> done`, fixed bug retention language, and ignored
  `.env` without reading it.
- Reviewer and Critic requested stronger literal checks, handoff cancellation
  wording, audit disposition, and origin reconciliation; these corrections are
  integrated. Only `.agents/bugs/git-divergence.md` remains open until merge.
