# LHC shared-session and durable handoff abstraction

Status: complete
Original user request: Добавить в LHC абстракцию shared session и будущего мини-инструмента LHC: видеть параллельные сессии/воркеров в директории, их активные и недавно изменённые файлы, иметь start/stop hooks, создавать и изменять task-файлы, проверять после каждого завершённого ответа перевод задачи в done и через настоящий human-request tool уведомлять человека с последним сообщением harness, сохранять долгий research в persistent-файле, дать file-first fallback при падении MCP и продолжать одного постоянного Overseer, читающего общий файл сообщений/состояния пользователя.
Objective: Описать runtime-agnostic, file-first контракт shared session/LHC без подключения существующих внешних hooks или MCP.
Business canary: Два агента в одной рабочей директории видят друг друга и свои task/file claims; завершившийся ответ без `done` порождает распознаваемый human-request; research дольше 10 минут и состояние Overseer остаются читаемыми после перезапуска MCP.
Confirmed scope: `docs/shared-session-abstraction.md`, ссылка/краткое правило в README, общий Overseer-контракт и прямые runtime/adapters references, task template/validator alignment only where needed.
Explicit exclusions: no external MCP implementation, no hook installation, no scheduler/daemon, no changes under `~/.claude`, no Agent Herder changes, no deployment/restart, no extra security/validation hardening unless separately requested.
Acceptance proof: document defines durable paths, lifecycle operations, hook events, fallback behavior, response-stop human notification, >10-minute research persistence, worker/file visibility, and persistent Overseer continuation; existing validator passes.
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
Initial estimate (minimum / maximum active minutes): 20 / 45
Estimate revisions: none
Stop when: abstraction is documented, source-of-truth paths are explicit, and validation passes.
Abandon/rethink when: the contract requires an unverified Agent Plugin 1.0 API or external runtime mutation; record the seam instead.
Forbidden without explicit user authorization: installation, daemon/scheduler, external hook/config changes, deployment, restart, ACL/secret/PII changes, or production MCP rollout.

## Execution — append-only

- UTC+3: 2026-08-10
  Slice: file-first shared-session abstraction and persistent Overseer correction
  Mode: implement: feature
  Owner: L
  Estimate (minimum / maximum; maximum <=20): 20 / 20
  Paths: docs/shared-session-abstraction.md, README.md, common Overseer/Lead/templates/adapters references
  Acceptance check: documentation and validator pass
  Result: DONE
  Business delta: durable handoff and human-request behavior become explicit
  Evidence: existing `~/.claude/hooks/shared_session_register.sh` found; no LHC shared-session contract found
  Next: none for this documentation slice

## Result

Summary: Added the adapter-neutral, file-first shared-session abstraction and
corrected Overseer continuation semantics across common instructions, routers,
templates, and harness adapter templates.
Business canary evidence: The contract defines worker/file visibility, task
create/update/complete, response-stop human notification, durable >10-minute
research, parent handoff fallback, and persistent Overseer state.
Tests/checks: `python3 tests/validate.py`; `tests/test_task_states.sh`; router
byte identity; `git diff --check`.
Review: External `/home/roomhacker/.claude` hooks and Agent Herder were inspected
read-only and not changed.
Workspace/branch at finish: primary checkout, `main`; foreign changes preserved.
Commit (only if created): none
Unresolved: Future MCP/Agent Plugin adapter and native response-stop hook remain
separate implementation work.
