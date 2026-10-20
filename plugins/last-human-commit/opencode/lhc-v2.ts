/**
 * Compatibility export for older OpenCode v2 configs.
 * OpenCode has no supported SessionStart instruction callback in this adapter;
 * project AGENTS.md remains the harness-owned instruction source.
 */
export default {
 id:"last-human-commit",
 async setup(_context: unknown){ return async()=>{} }
}
