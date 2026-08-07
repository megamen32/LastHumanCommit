# Merge orchestrator-first variant

Status: complete

Original request: merge the useful parts of the supplied ChatGPT
`orchestrator-first` version into LastHumanCommit.

Objective: improve orchestrator-first routing, bounded Worker research and
implementation modes, and validation without regressing the existing
AskHuman/AskSecret/SSS contract, Hermes LHC profile rollout, Tester role, or
the mandatory-initial plus 30-minute-triggered Overseer policy.

Business canary: the active LHC instruction sources pass validation; Codex and
Hermes retain the required human-request contracts and Hermes profile bundle;
Worker mode rules are explicit and bounded.

Scope: AGENTS/CLAUDE role routing, Lead/Worker/Planning contracts, worker
protocols, adapter task templates, validator, and directly related docs.

Exclusions: no Hermes source changes, no Fleet deployment, no removal of
AskHuman/AskSecret/SSS, no unrelated runtime or service changes.

Initial estimate: minimum 20 / maximum 45 active minutes.

Result: complete. Worker research/implement protocols, bounded slices, and
orchestrator-first routing are merged; Explorer is removed; Tester, Hermes LHC,
Fleet installation boundary, and AskHuman/AskSecret/SSS contracts remain.
Overseer is mandatory once per task before implementation, with later audits
limited by the 30-minute trigger rule.

Evidence: `python3 tests/validate.py`; Hermes plugin pytest (5 passed);
`tests/test_task_states.sh`; `tests/test_block_adapter.sh`; `git diff --check`.
