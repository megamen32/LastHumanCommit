# LHC single `.agents/` state root

Status: complete
Original user request: LHC сам не должен плодить отдельные корни вроде `.lhc`, `.at` и других папок; все инструкции должны использовать один `.agents/` root и его подпапки.
Objective: Убрать из нормативных инструкций top-level `.at`/`.lhc` и закрепить `.agents/` как единственный project-local agent-state root.
Business canary: Новый агент создаёт только `.agents/` и нужные подпапки, а не дополнительные top-level hidden roots.
Confirmed scope: routers, shared-session docs, Worker/Code rules, `.agents/at/`, validator.
Explicit exclusions: no deletion of unrelated tool directories, no external runtime changes, no deployment/restart.
Acceptance proof: no active instruction asks for top-level `.at`/`.lhc`; `.agents/at/README.md` exists; validators pass.
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
Stop when: source instructions and validator enforce the single-root rule.
Abandon/rethink when: a loader requires an external manifest directory; document it rather than multiplying project state roots.
Forbidden without explicit user authorization: external hook/MCP install, deployment, restart, unrelated cleanup.

## Result

Summary: Consolidated the normative LHC state model under one `.agents/` root,
moved Agent Tools documentation to `.agents/at/`, removed the created top-level
`.at/`, and explicitly prohibited top-level `.at`/`.lhc` creation.
Business canary evidence: future agents have one discoverable state root and no
instruction directs them to create extra hidden roots.
Tests/checks: `python3 tests/validate.py`; `tests/test_task_states.sh`;
`git diff --check`; router byte identity; no top-level `.at`.
Unresolved: external loader-owned manifest directories remain outside this
project-local state rule.
