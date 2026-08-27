# Harness session identity canary

Status: in progress
Original user request: Test whether each Agent Herder harness can ask a subagent to report its own native session, and whether L can record that session in the task file after creation.
Objective: Compare self-reported native session identity with Agent Herder's observed session identity for every active harness.
Business canary: Codex, Hermes, and OpenCode each produce an attributable session identity; L records the returned identity in this file without guessing.
Confirmed scope: live Agent Herder web control plane at `127.0.0.1:18787` and this task file only.
Explicit exclusions: no source changes, no Hermes core changes, no deployment, no restart, no edits by canary agents.
Acceptance proof: One recorded result per active harness and an explicit verdict about whether L can write the identity after agent creation.
Cycle: short
Harness: Agent Herder
PID: current Codex orchestration process (not yet captured)
Agent session: Herder-observed identity recorded in per-harness results below
Agent session (Herder-observed): pending per harness
Agent self-report (optional): pending per harness
PID status: alive
Last PID signal (UTC+3): 2026-08-09
Last task-file transition (UTC+3): todo
Lifecycle provenance: recorded at task creation
Last task-file mtime observed (UTC+3): 2026-08-09 02:10:43 +0300 (last write observed)
Current stage: research
Current owner: L
Started at (UTC+3): 2026-08-09
Initial estimate (minimum / maximum active minutes): 10 / 20

## Test protocol

1. Ask a subagent through each active harness to return its own native session ID.
2. Read the session identity observed by Agent Herder.
3. L appends both values here; no identity is inferred from the parent task.

## Results — append-only

### Codex

- Herder-created session: `019fe2ff-90c8-7661-a114-205541799a0a`
- Herder observed: `codex`, `idle`, `/home/roomhacker/agents-projects/LastHumanCommit`
- Agent self-report: `SELF_REPORTED_HARNESS=Codex`, `SELF_REPORTED_SESSION=not_visible`
- Verdict: Herder can provide the native session ID to L; the Codex child cannot see it in its own prompt.

### OpenCode

- Herder-created session: `ses_01c5f1de2ffezEgndu4n2WsYWj`
- Herder observed: `opencode`, `idle`, `/home/roomhacker/agents-projects/LastHumanCommit`
- Agent self-report: `SELF_REPORTED_HARNESS=opencode`, `SELF_REPORTED_SESSION=unknown-not-visible`
- Verdict: Herder can provide the native session ID to L; the OpenCode child cannot see it in its own prompt.

### Hermes

- Existing Herder session used: `agent:main:telegram:group:-1004360838692:9`
- Herder observed: `hermes`, `idle`
- Delivery without queue/steer: `ok: true`
- Queue delivery: rejected because the Hermes MCP `messages_send` adapter has no queue or steer control.
- Agent self-report: no response containing `SELF_REPORTED_*` after 56 seconds.
- Verdict: session identity canary is unproven for Hermes; the live adapter delivered the message but did not expose a self-report in the Herder details.

### L task-write test

L wrote every Herder-observed session identity into this same task file after the create/delivery operation. L did not invent a child-reported identity. The test therefore proves that `Agent/session` is not needed as a guessed field: Herder's observed native session belongs in the task, while the child self-report is separate evidence when available.

Status: blocked — Hermes self-report remains unproven.

Cleanup: OpenCode canary stopped successfully. Codex had no active turn when
stop was requested and therefore required no stop action. The existing Hermes
session was not stopped.
