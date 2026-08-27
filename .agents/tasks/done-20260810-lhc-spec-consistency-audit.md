# LHC core specification consistency audit

Status: complete
Original user request: Пройти по всей нормативной спецификации LHC без plugins, найти несоответствия между документами и ничего самостоятельно не исправлять; сообщить найденные конфликты, чтобы пользователь дал правила устранения.
Objective: Audit core routers, README, docs, src/common, templates, adapters, skills, and tests while excluding plugin directories, generated files, and historical task records.
Business canary: Пользователь получает точный список конфликтов с файлами/строками и без самовольных изменений спецификации.
Confirmed scope: core specification only; read-only inspection.
Explicit exclusions: no fixes, no plugin audit, no deployment, no runtime changes.
Acceptance proof: contradiction list separated into hard conflicts and gaps/ambiguities.
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
Current stage: research
Current owner: L
Initial estimate (minimum / maximum active minutes): 10 / 30
Estimate revisions: none
Stop when: core contradictions are reported with evidence and no source file is changed.
Abandon/rethink when: plugin/runtime scope is required to prove a core contradiction.
Forbidden without explicit user authorization: any specification edit or plugin/runtime change.

## Findings

Reported hard conflicts: one-task-file versus separate result/handoff files;
read-only Worker versus >10-minute commit gate; L-only task ownership versus
shared task_create/task_update; task status grammar; Adviser timing and scope;
and Tester cadence/scope. Reported gaps: background Overseer scheduling,
missing common Overseer veto wording for unsolicited security work, and unclear
base versus opt-in safety boundaries.

No specification source was changed during the audit.
