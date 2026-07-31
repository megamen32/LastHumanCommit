# Roadmap

Priority order: top first.

## M1 — Clear reusable canon

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
- [x] M3.5 Make the core canon copy-paste portable and internally consistent.

## M4 — Portable role router correction

Status: done

- [x] M4.1 Replace `CANON.md` with byte-identical `AGENTS.md` and `CLAUDE.md`.
- [x] M4.2 Route every known role to one independently loadable prompt.
- [x] M4.3 Restore the full provider/model role map.
- [x] M4.4 Make L own timed self-resume, revalidation, and deployment.
- [x] M4.5 Complete a whole-repository review and close stale contracts.

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
  `Agents Capable Start/End` variants of the portable canon.

## Proposed

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
  scheduler or runtime service in the core canon.
- [ ] Re-test Codex custom-agent routing before adding harness-specific Codex
  project profiles. On the current CLI, a custom `agent_type` is rejected as
  unknown and a prompt can answer without spawning a child. Require a real
  child event that proves role, actual model, fresh-context boundary, and
  returned result before claiming `gpt-5.4-mini` or any other model is routable.
