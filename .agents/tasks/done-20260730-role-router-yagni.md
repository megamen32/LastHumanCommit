# Portable role router YAGNI correction

State: done
Outcome: `AGENTS.md == CLAUDE.md` routes every agent to one independently
loadable role, while `Lead.md` alone owns the full workflow and timed
self-resume.
Acceptance:
- Remove `CANON.md` and every normative dependency on it.
- Route known role names to their role files without loading unrelated prompts.
- Fail closed for an explicitly declared subagent with a missing or unknown
  role; only a root agent defaults to `Lead`.
- Keep Direct, Short, Full, and Emergency classification in the router.
- Restore the complete model alias map.
- Make L arm and handle the 30-minute wake without assigning the work to Agent
  Fleet or an external scheduler.
- Remove the invented Web/credentials rule.
- Record, but do not implement, future harness-specific template markers.
- Review the whole repository and close every confirmed stale contract.
Estimate: 60-90 minutes
Cycle: full
Workflow: explore -> advise -> human-select -> work -> review -> commit

## Decision

Research: current tree, git history, official Codex subagent documentation, and
the local `agent-resume` contract.
Plans: Ultimate perfect totally ideal; Normal; YAGNI MVP.
Human selection: YAGNI MVP with a mandatory role router for every agent.
Selected-plan WSFF: role call tree, file-tree diff, and routing/resume
signatures were shown before implementation.

## Work

Current: complete.
Next: none.
Blocked by: none.
Evidence: red `FAIL: missing text contract: CLAUDE.md`; green
`PASS: 7 router roles and YAGNI text contracts`; `git diff --check` and
`cmp -s AGENTS.md CLAUDE.md` pass.

## Result

Summary: Replaced the duplicated LHC instructions with a portable role router, moved the
full workflow and timed self-resume to L, restored every original model alias,
and removed invented ownership and Web rules.
Tests: `python3 tests/validate.py`; `git diff --check`;
`cmp -s AGENTS.md CLAUDE.md`.
Review: Reviewer blockers for the minimum copy set and deploy idempotency were
corrected. Whole-repository stale-reference audit completed.
Commit: final implementation commit containing this completed task.
Unresolved: No live 30-minute wake/deploy drill; no deploy target exists in this
text-only repository. Future harness-specific template markers remain Proposed.
