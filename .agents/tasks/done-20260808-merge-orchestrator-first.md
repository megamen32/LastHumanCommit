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

## Overseer audit

Run a fresh no-history audit after the merge and before closing this task.
Check that the selected merge satisfies the business canary, preserves
AskHuman/AskSecret/SSS, keeps Hermes LHC separate from Fleet installation, and
does not introduce unnecessary scope. Append the complete verdict here; return
only TL;DR to L.

- Verdict: `CONTINUE`
- Business delta: validator, task-state, block-adapter, Hermes pytest 5/5, and
  diff-check are green.
- Scope check: AskHuman/AskSecret/SSS, Hermes LHC profile, and separate Fleet
  installation boundary are preserved; no unnecessary changes found.
- Next action: close this task after receipt.

### Overseer verdict — 2026-08-08

CONTINUE

Business delta: the selected merge satisfies the canary: `python3 tests/validate.py`, `tests/test_task_states.sh`, `tests/test_block_adapter.sh`, Hermes plugin pytest (5 passed), and `git diff --check` pass; AGENTS/CLAUDE and all five adapter instruction surfaces retain AskHuman plus AskSecret/SSS markers, the Hermes profile bundle is present, and no Explorer role remains.

Avoidable spend: none identified; the 35 changed paths are within the declared routing, Worker/Planning protocol, adapter-template, validator, and directly related documentation scope, with no Hermes source or Fleet deployment changes.

Minimum next action: L may close this task using the recorded merge and verification receipts; no additional research, implementation, security, or deployment work is justified by this audit.
