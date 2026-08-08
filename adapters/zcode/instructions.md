# ZCode adapter instructions

Prefer the project-or-agent profile mechanism when configured: materialize the
complete canonical role under `~/.zcode/agents/<role>.md` with the supported YAML
frontmatter and full role prompt. ZCode has no include directive, so the child
must not spend a turn rereading `src/common/agents/<Role>.md`. Otherwise use the
marker-preserving `AGENTS.md` block.

ZCode dispatches children through its `Agent` tool. When an active `PreToolUse`
guard forbids an explicit `model` key, select the model in profile frontmatter.
Never fork parent history; rely on the fresh-context boundary.

Before every child call, load `templates/subagent.md` for the compact assignment,
assigned task-file boundary, Worker continuity, and cheapest-sufficient role
profile.

For ordinary missing information use AskHuman. For a secret or password use
AskSecret/SSS only when attested; require opaque registered-agent handoff and
reject plaintext or base64 fallback.

Do not promise scheduled resume until proven. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
