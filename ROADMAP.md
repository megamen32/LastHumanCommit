# Roadmap

Priority order: top first.

## M1 — Clear reusable LHC

Status: done

- [x] M1.1 Keep core instructions short.
- [x] M1.2 Add lazy roles, profiles, and protocols.
- [x] M1.3 Add file-based task tracking.
- [x] M1.4 Add roadmap and out-of-roadmap priority gate.
- [x] M1.5 Keep copy-paste available as the base interface.

## M2 — Explicit marker-block adapter

Status: done

The built-in helper is intentionally not a universal installer. It manages one
explicit marker block in one explicit file and preserves all other project text.

- [x] M2.1 Keep `src/common/` for shared instructions and `templates/` for all records.
- [x] M2.2 Add explicit `init`, `apply`, `check`, and `remove-block` commands.
- [x] M2.3 Preserve text outside one complete marker pair; fail closed otherwise.
- [x] M2.4 Add dependency-free behavioral regression tests.

## M3 — Text-first human/agent workflow

Status: done

- [x] M3.1 Classify direct, short, full, and emergency work.
- [x] M3.2 Require research and human selection among three plans for full work.
- [x] M3.3 Add WSFF planning views and model-class guidance.
- [x] M3.4 Add Russian mobile commit review and timed release handoff.
- [x] M3.5 Make the LHC core copy-paste portable and internally consistent.

## M4 — Portable role router correction

Status: done

- [x] M4.1 Replace `CANON.md` with byte-identical `AGENTS.md` and `CLAUDE.md`.
- [x] M4.2 Route every known role to one independently loadable prompt.
- [x] M4.3 Restore the full provider/model role map.
- [x] M4.4 Make L own revalidation and explicit human-authorized deployment; silence never deploys.
- [x] M4.5 Complete an outcome-and-affected-scope contract review and close
  stale contracts within that boundary.

## M5 — Modular harness adapters

Status: in progress

- [x] M5.1 Keep role/protocol semantics in the capability-first core and define
  the adapter manifest and evidence states.
- [x] M5.2 Move the Hermes integration under `adapters/hermes/plugin/` and
  preserve it as an external plugin rather than a Hermes source change.
- [x] M5.3 Add opt-in Codex, OpenCode, and Claude Code adapter contracts with
  optional harness-specific instructions.
- [x] M5.4 Reinstall and verify Hermes from the canonical adapter path, then
  update the remote plugin without breaking the existing user config.
- [ ] M5.5 Add live child proof for each native adapter before marking its
  model, role, fresh-context, or resume capability `proven`.
- [x] M5.6 Keep adapter overlays additive; do not create subtractive
  `Agents Capable Start/End` variants of the portable LHC instructions.
- [x] M5.7 Make the non-Hermes self-improve record event-triggered by user correction, material route failure, or repeated friction. Hermes retains its native loop.
- [x] M5.8 Default to the primary checkout, keep authorized worktrees under project-local `.worktrees/`, preserve foreign edits, and never silently include them in the current task commit.

- [x] M5.9 Add the ZCode adapter without per-child task files.
- [x] M5.10 Preserve Tester, Hermes LHC profile, AskHuman, and fail-closed
  AskSecret/SSS contracts through the orchestrator-first merge.

## M6 — Outcome-first workflow contract

Status: done

- [x] M6.1 Make real outcome proof and selected scope the public authoring gate;
  forbid unsolicited secondary hardening or broad review unless user-confirmed
  or strictly required for the shortest safe business canary.
- [x] M6.2 Prove the aligned contract in LHC roles, profiles, templates,
  validation, applied project markers, and the installed version before making
  any runtime deployment claim. Plan selection is recorded in
  `.agents/tasks/done-20260801-outcome-first-lhc.md`.

## M7 — Business-first least-cost execution

Status: done and installed as `e49eeeb`

- [x] M7.1 Put the accepted business claim, actual production consumer path,
  shortest real canary, and cheapest sufficient proof before role/process
  routing.
- [x] M7.2 Let Lead research and implement directly when delegation costs more
  than the next proof; make all governance roles risk-triggered.
- [x] M7.3 Make every 20 active minutes a Worker reporting/control checkpoint,
  not a lifetime limit, and require real wait/join for required children.
- [x] M7.4 Replace mandatory snapshot/research artifacts with compact,
  cost-triggered state and persistence.
- [x] M7.5 Enforce semantic ordering and forbid the old unconditional gates in
  regression validation. The motivating audit is
  `docs/business-first-error-audit.md`.

## M8 — Lead feedback and business time control

Status: done and installed as `53e883d`

- [x] M8.1 Make Worker ask Lead at context-dependent decision boundaries with a
  recommendation/default while continuing safe independent work through a
  proven non-blocking parent transport.
- [x] M8.2 Require an immutable minimum/maximum estimate for each declared work
  cycle and an hourly Lead report of real closed tasks, business delta,
  completed files, blockers, gates/instructions, and next route.
- [x] M8.3 Add dependency-free `lhc_time_guard.py` with persistent idempotent
  crossed-hour, original-maximum overrun, and estimate-mutation events.
- [x] M8.4 Validate, commit, and install the updated source on the Fleet; keep
  native hook/wake claims adapter-dependent until physically attested.

## Proposed

- [ ] Add a lifecycle regression for a dead Worker: create and commit `todo-*`,
  copy/commit `work-*` with partial research and active-file metadata, simulate
  Worker death, then start the next Worker from the committed `work-*` snapshot
  without redoing completed research; verify `done-*` is a copied final snapshot,
  all predecessors remain, and the latest committed snapshot determines state.
- [x] Add a generic Agent Fleet versioned-directory rollout action: accept a
  committed payload plus per-host router/project/plugin overrides, preview the
  exact target matrix, preserve marker-external text, switch `current`
  atomically, retain rollback receipts, and verify full-tree digests. Keep it
  generic rather than adding an LHC-specific API branch. Implemented as
  Agent Fleet's `$lhc-rollout` skill over the generic skill-sync API.
- [ ] Run a held-out local benchmark: strong Lead alone; Lead plus one cheap
  Worker; Lead plus parallel cheap Workers; cheap Worker alone; and a
  full-history expensive fork control. Measure accepted tasks, end-to-end
  proof, scarce-quota use, wall-clock, human interventions, retries,
  wandering time, rework, and estimate error.
- [ ] Calibrate estimate ranges from completed task cards. The objective is
  accepted tasks per scarce quota without moving rework to the human.
- [ ] Turn the current hand-tuned role map into an evaluated router: begin with
  an explainable rule matrix by task, risk, scope, tools, and quota bucket;
  compare it with cheap-first cascades, classifiers, contextual bandits, and
  LLM routing only on held-out work. Keep the static map until a candidate wins
  on final task outcome and human rework, not cost alone.
- [ ] Record available subscription/API quota buckets, reset times,
  concurrency, and relative burn rates. This is future measurement data, not a
  scheduler or runtime service in the LHC core.
- [ ] Re-test Codex custom-agent routing before adding harness-specific Codex
  project profiles. On the current CLI, a custom `agent_type` is rejected as
  unknown and a prompt can answer without spawning a child. Require a real
  child event that proves role, actual model, fresh-context boundary, and
  returned result before claiming `gpt-5.4-mini` or any other model is routable.
