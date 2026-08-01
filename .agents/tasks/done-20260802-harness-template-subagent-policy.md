# Harness template subagent policy

Status: complete
Original user request: add per-harness template instructions; Codex must create
subagents without forking history; all harnesses should choose the lowest
sufficient working model class to save tokens.
Objective: provide one common cheapest-sufficient policy plus harness-specific
template overlays, with an explicit Codex fresh-context rule.
Business canary: validation fails if the common policy is absent, if Codex
templates permit history forks, or if adapters cannot carry their own overlay.
Confirmed scope: LHC source templates, harness adapters, documentation, and
focused validation.
Explicit exclusions: no global rollout, no provider/key changes, no Graphify
rebuild, and no unrelated harness installation work.
Acceptance: common and Codex-specific contracts are inspectable, tested, and
committed without touching `graphify-out/`.
Initial estimate (optimistic / likely / pessimistic active minutes): 15 / 30 / 45.
Estimate revisions (append-only; trigger and evidence): none.
Cycle: short
Workflow: inspect adapter/template architecture, add red contract, implement the
smallest overlay mechanism, validate, independently audit, commit.
Current stage: YAGNI

## Work

Current: complete.
Next: none inside confirmed scope.
Blocked by: none.
Evidence: see the red/green and independent gate history below.

## Evidence and gate history

- Red: `python3 tests/validate.py` failed because Codex lacked
  `subagent_instructions_template`.
- Red: validation then failed because adapter instructions did not load
  `templates/subagent.md`.
- Green: validator, task-state regression, marker adapter test, Hermes `4/4`,
  `py_compile`, and `git diff --check`.
- Live Codex proof: Overseer `019fbfab-2c94-7523-ad25-65bb1f0474d6` and Critic
  `019fbfab-290a-7a01-9617-d43caff57a58` were created with
  `fork_context:false`, explicit raw context and Task Cards,
  `gpt-5.6-luna`, and low reasoning. Both returned independent role reports.
- Initial gates: Overseer `STOP_SCOPE_DRIFT` and Critic `RETHINK` because they
  mistook the pre-existing `graphify-out/` and roadmap M5.5 for current scope
  and had not recognized their own calls as live Codex proof.
- Factual response: `graphify-out/` predates the task and remains untouched;
  latest user P0 is source templates, not all-harness runtime implementation;
  manifests keep runtime capabilities evidence-gated.
- Final gates: Overseer `APPROVE`; Critic `PASS`; no blocking questions.

## Result

- Every adapter manifest names its own `templates/subagent.md`.
- All harness templates require the lowest sufficient working model class,
  explicit Task Cards, no default inheritance of L's model, and evidence-based
  escalation.
- Codex always uses `fork_context: false`, passes needed context explicitly,
  and refuses a history-forked fallback.
- Lead and Planning load the selected adapter template before child creation.
- README separates source policy from fleet/runtime capability proof.
- Unresolved: global rollout is outside this task; capability status remains
  unchanged until installation-specific evidence exists.
