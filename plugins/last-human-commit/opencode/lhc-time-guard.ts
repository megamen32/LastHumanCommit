/**
 * Time-only LHC guard for OpenCode.
 *
 * This module is the importable time-only API: it locates the installed LHC
 * package, runs the canonical Python time guard and hands the resulting
 * reminder back to the caller. It observes wall time only and never reviews,
 * gates, approves or classifies anything.
 *
 * The implementation lives in `lhc-v2.ts` because OpenCode 1.18.x instantiates
 * every export of a plugin module and rejects a module with more than one
 * runtime export. Keeping the shared code in the plugin file lets
 * `install_runtime.py` install a single plugin file; this module re-exports
 * that implementation for direct use and for tests.
 *
 * Do not copy this file into an OpenCode plugin directory: OpenCode would
 * register each of its exports as a separate plugin instance.
 */

import plugin from "./lhc-v2.ts"

type LhcPluginInput = {
  directory?: string
  worktree?: string
  project?: { worktree?: string }
}

type LhcPaths = {
  packageRoot: string | null
  projectRoot: string | null
  agentsFile: string | null
  entry: string | null
}

type LhcTimeGuard = {
  paths: LhcPaths
  take: (sessionID: string | undefined) => string | null
  event?: (input: { event: { type?: string; properties?: Record<string, unknown> } }) => Promise<void>
  "chat.message"?: (
    input: { sessionID?: string; messageID?: string },
    output: { message?: { id?: string; sessionID?: string }; parts?: unknown[] },
  ) => Promise<void>
  "tool.execute.after"?: (
    input: { tool?: string; sessionID?: string; callID?: string },
    output: { title?: string; output?: string },
  ) => Promise<void>
}

/**
 * Build the time-only guard for one OpenCode project.
 * Resolves to a guard whose hooks observe the wall clock and nothing else.
 */
export const LastHumanCommitTimeGuard = async (context: LhcPluginInput = {}): Promise<LhcTimeGuard> =>
  plugin.LastHumanCommitTimeGuard(context)

/** Resolve the installed LHC package, project root, AGENTS.md and guard entry. */
export const resolveLhcPaths = (context: LhcPluginInput = {}): LhcPaths => plugin.resolveLhcPaths(context)

/** Locate the installed LHC package root, or null when it cannot be found. */
export const resolvePackageRoot = (context: LhcPluginInput = {}): string | null =>
  plugin.resolvePackageRoot(context)

/** Locate the OpenCode project directory, or null when it cannot be found. */
export const resolveProjectRoot = (context: LhcPluginInput = {}): string | null =>
  plugin.resolveProjectRoot(context)

/**
 * Run the canonical time-only guard and return its reminder.
 * Resolves to null when Python, the guard or the output is unavailable.
 */
export const runTimeGuard = (
  entry: string,
  options: { cwd: string; sessionID: string; runtime?: string },
): Promise<string | null> => plugin.runTimeGuard(entry, options)

export default LastHumanCommitTimeGuard
