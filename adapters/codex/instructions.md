# Codex adapter instructions

These are optional Codex integration details, not a core role. A configured
profile embeds the complete role prompt; use file fallback only when native
profile delivery is absent.

Before every child call, load `templates/subagent.md`. It requires
`fork_context: false`, compact explicit business context, the cheapest sufficient
model, a 20-minute reporting checkpoint, and a real wait/join when the result is
required. Include a task/result path only when durable handoff is worth its cost.

One Codex V1/V2 wait window is absolute and monotonic:
`deadline = monotonicNow() + 1800000 ms`. On each target-specific wait, mailbox
wake, or `timed_out`, inspect authoritative status, compute
`remainingMs = deadline - monotonicNow()`, and wait only with `remainingMs`.
Never reset that window.

At window expiry, preserve the child and make one control decision from its
checkpoint/status. Continue or redirect with `send_input`, then start another
join window when the child result remains required and continuation is
least-cost. Never call `close_agent`, create a replacement, or send the final
answer solely because 20 minutes, a timeout, or one wait window elapsed.

For ordinary missing information use AskHuman. For a secret or password route
through AskSecret/SSS only when attested. The only acceptable handoff is an
opaque registered-agent SSS path; reject plaintext and base64 fallback.

Do not claim model selection, fresh-context isolation, wait, or resume support
until a live child event proves it. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
