# OpenCode adapter instructions

Native profiles are Markdown files under the configured OpenCode agents
directory. The installed profile contains the complete role prompt at startup;
it must not spend a turn rereading `src/common/agents/<Role>.md`.

The native LHC plugin (`plugins/last-human-commit/opencode/lhc-v2.ts`) is
registered by `scripts/install_runtime.py` into the OpenCode plugin directory.
It injects a pointer to the current installed `AGENTS.md` into the system
context, reports the time-only reminders produced by
`common/tools/lhc_time_guard.py` at tool and idle boundaries, and re-injects the
`AGENTS.md` and the bounded `current-handoff.md` pointers after compaction. It
does not review, gate, approve or evaluate a diff, and it never blocks a turn.
If the plugin is not loaded, say activation is unverified instead of assuming
it.

Before every child call, load `templates/subagent.md` for compact business
context, the optional durable task/result boundary, Worker continuity,
checkpoint/join control, and cheapest-sufficient model rules.

For missing information ask the user one compact question. Secrets are not
work: read a password or token directly from an environment variable, `.env`,
or a secret file in one step; never build secret handoff infrastructure.

Keep core role semantics unchanged. This adapter owns profile frontmatter, native
permissions, and harness-specific resume metadata. Before L's final answer, run
`SELF_IMPROVE.md` only when its trigger occurred.
