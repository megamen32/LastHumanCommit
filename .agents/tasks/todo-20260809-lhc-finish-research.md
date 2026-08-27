# Explorer package: finish and test seams

Status: todo
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-09 05:04:17 +0300 (last write observed, not start)

Role: Explorer
Goal: Identify exact current LHC seams for stale/abandoned work review, final commit/push/clean-worktree closure, test classification/default selection, and integration with the existing private-to-public tool.
Allowed paths: `/home/roomhacker/agents-projects/LastHumanCommit/src`, `/home/roomhacker/agents-projects/LastHumanCommit/templates`, `/home/roomhacker/agents-projects/LastHumanCommit/tests`, `/home/roomhacker/agents-projects/LastHumanCommit/README.md`, `/home/roomhacker/agents-projects/git-private2public/README.md`, `/home/roomhacker/agents-projects/git-private2public/git_private2public.py`, and their tests.
Excluded paths: all mutation, deployment, credentials, live calls, Docker, source changes, and unrelated repositories.
Acceptance check: Return exact file/line evidence, current gaps, and one bounded recommendation per seam; no implementation.
Budget: 5 / 12 / 20 active minutes; model: gpt-5.4-mini; reasoning: low; relative cost: low.
Stop: after evidence is sufficient or an unknown dependency appears.

## Detailed evidence and result

### Evidence (Explorer, 2026-08-09)

- Stale/abandoned work review: `src/common/protocols/SHARED_WORKTREE.md:41-67` is the current seam. It requires inspecting status/diffs/untracked files/mtime, treats recent foreign edits as active, and explicitly says older foreign edits remain foreign; it forbids silently staging/committing them. `src/common/profiles/Test.md:33-34` separately says unresolved `todo-*`/`work-*` files must retain their exact blocker. Gap: no procedure or command/result schema identifies stale task files, reconciles them with git ownership, or authorizes closing them; “older” is a warning, not a review decision. Recommendation: add a bounded stale-review checklist/output to the task/release handoff, preserving ownership and requiring explicit user selection for closure.

- Final commit/push/clean closure: `src/common/protocols/SHARED_WORKTREE.md:46-60` defines pre-stage inspection and prohibits destructive cleanup (`git clean`, reset, restore, rollback, force-push). `src/common/protocols/SHARED_WORKTREE.md:62-67` limits final integration to reviewed task-owned paths. `src/common/agents/Lead.md:153-157,179-193` only says commit reviewed task-owned work “when appropriate,” send the release handoff, and claim delivery only with fresh evidence. `templates/RELEASE_HANDOFF.md:15-18,30-32,58` records commit/artifact, tests, and revalidation fields. Gap: there is no explicit final push command/authorization boundary, no required `git status --short` clean-closure evidence, and no defined handling of remaining foreign dirty paths beyond reporting. Recommendation: make release handoff require commit identity (if created), push decision/result, final status, and explicit blocker for any non-clean checkout; keep destructive cleanup/user authorization separate.

- Test taxonomy/default selection: `src/common/profiles/Test.md:18-26` gives preference order blackbox > integration > unit, requires unit Red-first/Green-last, a <30s per-test limit, and names `E2E`, `FAST`, `SMOKE`, and opt-in `TEST4TEST`; it also requires one all-tests command and says fast-only is opt-in. `README.md:125-131` exposes validation commands but does not define taxonomy or default selection. `tests/validate.py:203-211` validates only Tester wording, while `tests/validate.py:314-320` validates Full-cycle ordering. Gap: taxonomy is prose only; no canonical marker/config, default command, inclusion/exclusion rule, or enforcement that default selection reaches the real canary. The “E2E(long)” example also sits beside “Any Test must be complete <30s,” with no resolution for long E2E tests. Recommendation: define one canonical test command plus explicit default/opt-in taxonomy and state that static/unit/integration success cannot satisfy the Full Tester gate.

- Mandatory zero-context live Tester seam: `src/common/agents/Lead.md:147-152` requires a fresh Tester in `only-new` mode on the actual user-facing surface before fresh Critic; `src/common/agents/Tester.md:3-6,8-13,15-18,22-44` defines the Tester as final independent real-user testing, mandatory `only-new` for Full, fresh task-file-only context, end-to-end main-job attempt, real surfaces (BrowserOS/Playwright same flow, `agent-device`, actual app, fresh CLI), verdicts including `STOP_MISSING_REAL_SURFACE`, and rejection of unit/process/log/source-only proof. `templates/FULL_CYCLE.md:108-116` repeats Tester-before-Critic ordering. `tests/validate.py:195-211,320` checks wording and ordering. Gap: validation proves documentation text only; no harness seam dispatches a zero-context Tester or proves a live computer-surface canary, and no test can substitute for that requirement. Recommendation: retain this as a runtime release gate with explicit surface/tool, journey, observed state, and verdict evidence; fail closed as `STOP_MISSING_REAL_SURFACE` when unavailable.

- Existing git-private2public integration: within allowed LHC paths, `rg` found no `git-private2public`, `publish`, or `guard` references. The separate tool exposes `publish`/`scan`/`hook`/`guard` CLI commands at `../git-private2public/git_private2public.py:1142-1182`; publishing scans the sanitized result and refuses violations before pushing at `../git-private2public/git_private2public.py:568-605`, then pushes branches/tags at `:611-624`. Its README documents history scanning and the distinction between `guard` and auto-publish `hook` at `../git-private2public/README.md:74-130,174-180`. Gap: LHC has no declared integration point, ordering, or acceptance evidence connecting final commit/push closure to guard/publish; enabling either hook is an external repo/config action outside this package. Recommendation: document an optional, explicit release integration seam (scan-only before LHC commit/push; publish only with user authorization), without copying or forking the tool.

### Result

Current documentation has a strong normative Full-cycle Tester requirement, but enforcement is static and the requested live, zero-context, actual-computer canary remains a runtime/harness responsibility. The highest-value next probe is the Lead/harness release path: verify it can instantiate a fresh Tester, expose the actual user-facing surface, append evidence to the same task file, and block Critic/release when the surface or canary is unavailable. Separately, add explicit stale-review, final status/push receipt, test-default, and optional git-private2public integration contracts before claiming complete closure.
