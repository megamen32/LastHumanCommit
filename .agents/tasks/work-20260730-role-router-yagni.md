# Portable role router YAGNI correction

State: work
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

Current: regression contracts are red because `CLAUDE.md` is absent.
Next: replace the duplicated canon with the selected router and Lead workflow.
Blocked by: none.
Evidence: `python3 tests/validate.py` -> `FAIL: missing text contract:
CLAUDE.md`.

## Result

Summary:
Tests:
Review:
Commit:
Unresolved:
