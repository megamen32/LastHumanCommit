# ZCode

Use the supported project or agent profile under `~/.zcode/agents/<role>.md`. It contains the complete role and YAML frontmatter; ZCode has no include directive. The marked `AGENTS.md` block is the portable fallback.

Children use the native `Agent` tool. When the active interface requires model selection in profile frontmatter, set it there instead of passing an unsupported model key. Use the fresh context needed for an independent review and preserve useful context for ordinary continuation.

`templates/subagent.md` covers the assignment. SessionStart loads instructions; the legacy `hooks/lhc_time_start.sh` is inert. Time-only PostToolUse reminders start at their first observed tool boundary, not at a reconstructed historical task start.
