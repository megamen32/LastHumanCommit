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

SessionStart loads instructions only; the legacy `hooks/lhc_time_start.sh` is inert.
Time-only PostToolUse reminders track their first tool boundary in the existing
learning state. The Lead records the actual task start and estimates separately.

Do not promise scheduled resume until proven. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
