# LHC named search/result artifacts and Git ignore boundary

Status: complete
Original user request: Журнал поиска и финальный результат должны быть двумя разными файлами в разных папках. Search-файл должен называться `search-<что-описывает-задачу>.md` и попадать в `.gitignore`. Result-файл должен называться `result-<что-описывает-документ>.md`, быть tracked и после исследования дольше 10 минут обязательно коммититься.
Objective: Исправить shared-session paths, naming и Git ignore semantics без объединения search journal с final result.
Business canary: Lead находит search journal в ignored search tree, открывает named tracked result в results tree, а долгий результат не может исчезнуть из Git commit.
Confirmed scope: `.gitignore`, shared-session abstraction, Worker research protocol, Worker/adapters, this task card.
Explicit exclusions: no runtime MCP/hook installation, no deployment/restart, no unrelated cleanup.
Acceptance proof: docs use separate named paths, Git ignores only search tree, result tree remains trackable, validators pass.
Cycle: short
Harness: codex
PID: current Lead orchestration process
Agent session: current task
PID status: alive
Last PID signal (UTC+3): 2026-08-10
Last task-file transition (UTC+3): work
Started at (UTC+3): 2026-08-10
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-10
Current stage: implementation
Current owner: L
Initial estimate (minimum / maximum active minutes): 5 / 15
Estimate revisions: none
Stop when: named paths, Git ignore rule, commit gate, and checks are correct.
Abandon/rethink when: path ownership conflicts with an existing project ignore policy.
Forbidden without explicit user authorization: external hook/MCP install, deployment, restart, security/validation expansion.

## Result

Summary: Separated ignored named `search-<task-slug>.md` journals from tracked
named `result-<result-slug>.md` files in different shared-session trees and added
the Git ignore rule for the search tree.
Business canary evidence: search history remains bulk-analyzable without entering
normal commits, while the final result is named, tracked, and commit-required
after 10 active minutes.
Tests/checks: `python3 tests/validate.py`; `tests/test_task_states.sh`;
`git diff --check`; `git check-ignore` confirmed the search path.
Unresolved: none for this documentation slice; runtime enforcement remains a
future adapter task.
