# Codex adapter instructions

These are optional Codex integration details, not a core role. When a configured
profile embeds the complete role prompt, do not ask the child to read the role
file again. Use file fallback only when native profile delivery is absent.

Before every child call, load `templates/subagent.md`. It requires
`fork_context: false`, explicit compact assignment context, the root-task read-
only boundary, and the cheapest sufficient working model. A Codex surface that
cannot honor no-history must not create a history-forked substitute.

Codex wait-agent joins are governed by one fail-closed contract in Codex V1 and
Codex V2: the wait timeout is observational only, and the fixed absolute
30-minute join deadline is exactly `timeout_ms: 1800000` (1800000 ms). A timeout, mailbox wake,
dead PID observation, or missing completion signal does not decide lifecycle;
missing completion signal alone is not evidence of dead or unknown. Preserve the
child until an authoritative terminal status is recorded or explicit
cancellation is authorized and recorded. Never call `close_agent` on timeout and
never create a replacement on timeout.

Join mechanics are absolute and monotonic. Establish one deadline once per
join: `deadline = monotonicNow() + 1800000 ms`. Codex V1 target-specific wait
and Codex V2 mailbox wake are distinct wake mechanisms, but use the same
absolute deadline. On every mailbox wake or `timed_out` result, re-check the
target child status; if non-terminal, compute
`remainingMs = deadline - monotonicNow()` and wait only with `remainingMs`.
Never reset/restart the full 1800000 after a wake or timeout. At `remainingMs <=
0`, return `join-deadline-expired` with child preserved; do not close_agent,
infer dead/unknown, or create a replacement.

For ordinary missing information use AskHuman. For a secret or password route
through AskSecret/SSS only when attested. The only acceptable handoff is an opaque registered-agent SSS path; reject plaintext and base64 fallback.

Do not claim model selection, fresh-context isolation, or resume support until a
live child event proves it. Before L's final answer, run `SELF_IMPROVE.md` only
when its trigger occurred.
