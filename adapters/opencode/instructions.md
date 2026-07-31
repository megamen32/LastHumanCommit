# OpenCode adapter instructions

Native profiles are Markdown files under the configured OpenCode agents
directory. The installed profile must contain the complete role prompt at
startup; it must not spend a turn reading `src/common/agents/<Role>.md`.

Keep the core role unchanged. This adapter owns profile frontmatter, native
permissions, and any harness-specific resume/session metadata.

Before L sends its final answer, run the core `SELF_IMPROVE.md` protocol and
persist its compact record.
