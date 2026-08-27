# LHC copy-and-commit task snapshots and dead-Worker resume roadmap

Status: in progress
Original user request: Не делать `git mv` между `todo-*`, `work-*`, `done-*`; делать copy и commit, сохранять все три snapshots, считать состояние по последнему committed snapshot, а тест смерти сабагента и продолжения следующим Worker добавить в Roadmap.
Objective: Обновить lifecycle contract и добавить roadmap item для resume-after-worker-death regression.
Business canary: следующий Worker продолжает с committed `work-*`, а `done-*` — отдельная финальная копия; исходные snapshots остаются доступны.
Confirmed scope: AGENTS/CLAUDE, README, Lead/docs/templates/Test profile/task template, ROADMAP, validator.
Explicit exclusions: no runtime resume implementation, no deployment/restart, no unrelated task migration.
Acceptance proof: core checks pass and Roadmap contains the dead-Worker resume test.
Cycle: short
Harness: codex
PID: current Lead orchestration process
Agent session: current task
PID status: completed
Last PID signal (UTC+3): 2026-08-11
Last task-file transition (UTC+3): done
Started at (UTC+3): 2026-08-11
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-11
Current stage: release
Current owner: L
Initial estimate (minimum / maximum active minutes): 10 / 20
Estimate revisions: none
Stop when: lifecycle docs and Roadmap are updated and checks pass.
Abandon/rethink when: snapshot semantics conflict with an unreviewed runtime consumer.
Forbidden without explicit user authorization: runtime resume implementation, deployment, restart, destructive task migration.

## Result

Changed lifecycle semantics from rename to copy+commit snapshots and added the
Roadmap regression for Worker death/resume. No runtime resume test was
implemented in this slice.
