# Restore Harness/PID task lifecycle identity

Status: complete
Original user request: Restore the early task metadata that records harness and PID so a task can be distinguished between dead work and an agent that finished without moving the task file.
Objective: Make runtime identity and lifecycle signals explicit in the canonical task template and routing instructions.
Business canary: An active task card exposes Harness, PID, Herder-observed Agent session, optional agent self-report, PID status, the last PID signal, and the last task-file transition.
Confirmed scope: `AGENTS.md`, `CLAUDE.md`, the canonical task template, and its validator.
Explicit exclusions: No runtime services, adapters, Fleet, Hermes source, or existing historical task files.
Acceptance proof: Static validator checks the lifecycle fields in the canonical template.
Cycle: short
Harness: codex
PID: current Codex orchestration process (not captured by this text-only canary)
Agent session (Herder-observed): current task
Agent self-report (optional): not tested in this historical task
PID status: completed
Last PID signal (UTC+3): 2026-08-09
Last task-file transition (UTC+3): done
Current stage: release
Current owner: L
Started at (UTC+3): 2026-08-09
Initial estimate (minimum / maximum active minutes): 5 / 15

## Result

Added explicit Harness/PID/agent-session identity and lifecycle signal fields.
The canon now distinguishes a stale task-file transition from a dead or
unobservable runtime instead of inferring liveness from `todo-*` or `work-*`.
