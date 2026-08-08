# Merge unified corrected LHC

Status: complete

Original user request: аккуратно слить unified corrected ZIP поверх текущего
main и запушить.

Objective: adopt the corrected orchestrator-first LHC contract while preserving
all existing task receipts, AskHuman/AskSecret/SSS, Hermes LHC, Fleet boundary,
Tester, ZCode, and the 30-minute event policy.

Business canary: ZIP checks pass from inside the resulting checkout; AGENTS and
CLAUDE are identical; AskHuman is required and named correctly; task history is
preserved; main can be merged and pushed.

Scope: tracked source changes from the supplied ZIP, except task-file deletion;
restore `human.ask_user.v1.yaml` to required `AskHuman`.

Exclusions: no runtime deployment, no Hermes source changes, no deletion of
existing `.agents/tasks/`, no changes to Fleet repository.

Initial estimate: minimum 15 / maximum 30 active minutes.

Result: complete. Unified corrected source was merged without deleting task
history. `AskHuman` is required and named correctly. Child task-file append plus
TL;DR contract was restored; Tester, Hermes LHC, SSS, ZCode, and Fleet boundary
remain. Rollback remains user-authorized only.

Evidence: validator, task-state, block-adapter, and Hermes plugin tests pass;
AGENTS.md and CLAUDE.md are byte-identical; Code.md retains the expected SHA.
