# Codex subagent instructions template

Before every `spawn_agent` or resumed Worker call:

Bootstrap the child with exactly `<Role> <absolute-task-file-path>`.

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Every new child starts with `fork_context: false`. Never fork parent history;
  pass only required context explicitly.
- Send one compact assignment: role, Worker mode when applicable, root task path,
  goal, decisive evidence, allowed/excluded paths, one
  acceptance check, minimum/maximum with maximum <=20, stop conditions, and
  compact return format.
- The child reads only the assigned task file, appends detailed evidence
  and its result there, and returns only TL;DR to L. It never creates a second
  task card, report, ledger, or spec file.
- After 3 active minutes of research orientation, write the exact query and
  detailed answer to named files: ignored `.agents/shared-session/search/<task-id>/search-<task-slug>.md`
  and tracked `.agents/shared-session/results/<task-id>/result-<result-slug>.md`;
  chat carries only a compact TL;DR and paths.
- Resume the same Worker from research with `send_input` for its selected
  implementation lane when supported; otherwise pass the compact Research
  section to a fresh Worker.
- Overseer continues the persistent shared-session context; use fresh/no-history
  only for recovery or an explicitly requested independent audit. Critic is a
  fresh no-history child with no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.

Codex V1 and Codex V2 wait-agent joins use the fixed absolute 30-minute join
deadline exactly as `timeout_ms: 1800000` (1800000 ms). The wait timeout is observational
only: a timeout, mailbox wake, dead PID observation, or missing completion
signal does not decide lifecycle, and missing completion signal alone is not
evidence of dead or unknown. Preserve the child until an authoritative terminal
status is recorded or explicit cancellation is authorized and recorded. Never
call `close_agent` on timeout and never create a replacement on timeout.

Join mechanics are absolute and monotonic. Establish one deadline once per
join: `deadline = monotonicNow() + 1800000 ms`. Codex V1 target-specific wait
and Codex V2 mailbox wake are distinct wake mechanisms, but use the same
absolute deadline. On every mailbox wake or `timed_out` result, re-check the
target child status; if non-terminal, compute
`remainingMs = deadline - monotonicNow()` and wait only with `remainingMs`.
Never reset/restart the full 1800000 after a wake or timeout. At `remainingMs <=
0`, return `join-deadline-expired` with child preserved; do not close_agent,
infer dead/unknown, or create a replacement.

If the active Codex surface cannot create a no-history gate child, report the
unsupported boundary instead of using a history-forked substitute.
