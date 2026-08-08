# Claude Code adapter instructions

Use the native role/profile mechanism when configured. Otherwise the marker-
preserving `CLAUDE.md` block is the portable fallback. Keep the complete role
context in the child prompt and never overwrite project-owned text outside the
marker pair.

Before every child call, load `templates/subagent.md` for the compact assignment,
assigned task-file boundary, Worker continuity, and cheapest-sufficient model
rules.

For ordinary missing information use AskHuman. For a secret or password use
AskSecret/SSS only when attested; require the opaque registered-agent handoff and
reject plaintext or base64 fallback. Otherwise report the capability unavailable.

Do not promise scheduled resume until the active surface proves it. Before L's
final answer, run `SELF_IMPROVE.md` only when its trigger occurred.
