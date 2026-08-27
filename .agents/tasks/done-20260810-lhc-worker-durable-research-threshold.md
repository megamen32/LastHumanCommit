# LHC Worker durable research after three minutes

Status: complete
Original user request: Сабагенты должны после трёх минут базовой ориентации писать результат исследования в persistent-файл, а не оставлять подробный результат только в чате, чтобы мёртвый harness не уничтожил полезный контекст и Lead мог читать файл без загрузки всей сессии.
Objective: Изменить shared-session и Worker abstraction: 3 минуты — предел ориентации; затем query и подробный ответ обязательны в durable research file, чат содержит только короткий TL;DR/ссылку.
Business canary: После остановки/смерти harness Lead открывает указанный research-файл и получает полный вопрос, доказательства, ответ и blocker без чтения полной истории сессии.
Confirmed scope: `docs/shared-session-abstraction.md`, `src/common/agents/Worker.md`, `src/common/protocols/WORKER_RESEARCH.md`, adapter subagent templates, this task card.
Explicit exclusions: no MCP/hook installation, no Agent Herder changes, no runtime service, no deployment/restart, no extra security/validation work.
Acceptance proof: all text contracts say 3-minute threshold and file-first detailed research; existing tests pass.
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
Initial estimate (minimum / maximum active minutes): 10 / 25
Estimate revisions: none
Stop when: threshold and file-first handoff are documented and checks pass.
Abandon/rethink when: the requested behavior requires an unavailable harness hook; record that adapter gap instead.
Forbidden without explicit user authorization: external hook/MCP installation, service changes, deployment, restart, security/validation hardening.

## Result

Summary: Changed the research persistence threshold from 10 minutes to 3 active
minutes after basic orientation. Worker/common protocols and every adapter
template now require detailed file-first research with only TL;DR/link in chat.
Business canary evidence: A dead harness leaves the exact query and detailed
answer in `.agents/shared-session/research/<task-id>/` for Lead recovery.
Tests/checks: `python3 tests/validate.py`; `tests/test_task_states.sh`; `git diff --check`.
Unresolved: runtime MCP/hook implementation remains a separate task.
