/**
 * Compatibility export for older OpenCode configs.
 *
 * Lifecycle gates are no longer registered from native prompt/tool hooks.
 * OpenCode has no supported SessionStart instruction callback in this adapter;
 * project AGENTS.md remains the harness-owned instruction source.
 */
export const LastHumanCommitTimeGuard = async (_context: { directory: string }) => ({})
