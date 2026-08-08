# OpenCode adapter instructions

Native profiles are Markdown files under the configured OpenCode agents
directory. The installed profile contains the complete role prompt at startup;
it must not spend a turn rereading `src/common/agents/<Role>.md`.

Before every child call, load `templates/subagent.md` for the compact assignment,
assigned task-file boundary, Worker continuity, fresh gates, and cheapest-
sufficient model rules.

For ordinary missing information use AskHuman. For a secret or password use
AskSecret/SSS only when attested; require opaque registered-agent handoff and
reject plaintext or base64 fallback.

Keep core roles unchanged. This adapter owns profile frontmatter, native
permissions, and harness-specific resume metadata. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
