# Claude Code adapter instructions

Use the native role/profile mechanism when configured. Otherwise the marker-
preserving `CLAUDE.md` block is the portable fallback. Keep the complete role
context in the child prompt and never overwrite project-owned text outside the
marker pair.

Before every child call, load `templates/subagent.md` for compact business
context, the optional durable task/result boundary, Worker continuity,
checkpoint/join control, and cheapest-sufficient model rules.

For missing information ask the user one compact question. Secrets are not
work: read a password or token directly from an environment variable, `.env`,
or a secret file in one step; never build secret handoff infrastructure.

Do not promise scheduled resume until the active surface proves it. Before L's
final answer, run `SELF_IMPROVE.md` only when its trigger occurred.
