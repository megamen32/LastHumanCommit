# LHC finish, clean-worktree, and test-risk gates

Status: in progress
Original user request: Make Last Human Commit finish abandoned work reliably: after a path has been untouched for more than 30 minutes, review it as owned code, ensure the repository is never left dirty at task completion, require commit plus push as the completion boundary, and integrate private-to-public secret protection and test-oriented safeguards. Define safe, integration, and material/expensive test classes, including tests excluded from ordinary runs. User correction: the Full-cycle finish must include a fresh zero-context Tester that uses the real computer/user-facing surface as a live canary; static tests are not enough and Tester is the final user gate.
Objective: Deliver an LHC workflow and validation contract that detects abandoned work, performs mandatory final review, and closes only after a clean pushed repository or an explicit human wait; add the requested private-to-public and test-gate integration where the repository supports it.
Business canary: A controlled fixture with stale foreign changes and a failing or passing test set reaches a fresh zero-context live Tester canary on the real user-facing surface, then an explicit reviewed commit, push confirmation, and clean worktree; unsafe/expensive tests remain excluded from the default suite and are callable by named opt-in gates.
Confirmed scope: `/home/roomhacker/agents-projects/LastHumanCommit`, its role/protocol/template/validation/test files, and existing local private-to-public/test tooling only where the integration seam is evidenced.
Explicit exclusions: no deployment, no credentials or permission changes, no destructive cleanup of unrelated work, no live paid calls, no production database or external service tests, and no publication of private content.
Acceptance proof: focused red/green regressions; independent review and critic evidence; final product-surface test; commit and push receipt; final `git status` clean and remote tip matches local tip, or a direct user-approved wait if an external blocker remains.
Cycle: full
Harness: codex
PID: unknown (legacy work card; not captured)
Agent session: unknown (legacy work card; not captured)
PID status: unknown (legacy work card)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was work-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-09 05:03:15 +0300 (last write observed, not start)
Initial estimate (optimistic / likely / pessimistic active minutes): 45 / 90 / 150
Estimate revisions: 2026-08-09 user correction added mandatory zero-context live Tester as final product-surface gate; research scope unchanged, acceptance and likely integration effort increased; evidence: user message in current task.
Current stage: research and plan selection
Current owner: Lead
Stop when: selected contract is implemented, reviewed, tested, pushed, and the worktree is clean.
Abandon/rethink when: the required private-to-public or test gate cannot be integrated without violating source-ownership or security policy.

## Research contract

Inspect the current finish/commit/push instructions, task-state semantics, validation tests, and local private-to-public/test tooling. Treat changes older than 30 minutes as abandoned candidates only after a read-only ownership review; never erase them automatically.

## Evidence

Pending.
