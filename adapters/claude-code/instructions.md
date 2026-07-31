# Claude Code adapter instructions

Use the Claude Code surface's native role/profile mechanism when one is
configured. Otherwise the marker-preserving `CLAUDE.md` block is the portable
fallback. The adapter must keep the complete role context in the child prompt
and must not overwrite project-owned text outside the marker pair.

Do not promise scheduled resume until the active Claude surface exposes and
verifies its cron or scheduled-task transport.
