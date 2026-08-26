# ZCode adapter instructions

Prefer the project-or-agent profile mechanism when configured: materialize the
complete canonical role under `~/.zcode/agents/<role>.md` with the supported YAML
frontmatter and full role prompt. ZCode has no include directive, so the child
must not spend a turn rereading `src/common/agents/<Role>.md`. Otherwise use the
marker-preserving `AGENTS.md` block.

ZCode dispatches children through its `Agent` tool. When an active `PreToolUse`
guard forbids an explicit `model` key, select the model in profile frontmatter.
Never fork parent history; rely on the fresh-context boundary.

Before every child call, load `templates/subagent.md` for compact business
context, the optional durable task/result boundary, Worker continuity,
checkpoint/join control, and cheapest-sufficient role profile.

For missing information ask the user one compact question. Secrets are not
work: read a password or token directly from an environment variable, `.env`,
or a secret file in one step; never build secret handoff infrastructure.

A SessionStart hook (`hooks/lhc_time_start.sh`) writes the durable time anchor
`.agents/shared-session/time/zcode-<session-id>.json` from the real start
clock; TIME_CONTROL start anchors cite that file.

Do not promise scheduled resume until proven. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
