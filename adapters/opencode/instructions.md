# OpenCode adapter instructions

Native profiles are Markdown files under the configured OpenCode agents
directory. The installed profile contains the complete role prompt at startup;
it must not spend a turn rereading `src/common/agents/<Role>.md`.

Before every child call, load `templates/subagent.md` for compact business
context, the optional durable task/result boundary, Worker continuity,
checkpoint/join control, and cheapest-sufficient model rules.

For ordinary missing information use AskHuman. For a secret or password use
AskSecret/SSS only when attested; require opaque registered-agent handoff and
reject plaintext or base64 fallback.

Keep core role semantics unchanged. This adapter owns profile frontmatter, native
permissions, and harness-specific resume metadata. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
