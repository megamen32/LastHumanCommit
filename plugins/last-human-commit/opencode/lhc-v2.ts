/**
 * LHC native OpenCode plugin: instructions and time only.
 *
 * OpenCode 1.18.x loads a plugin module as a function export and instantiates
 * every export it finds, so this module keeps exactly one runtime export.
 * `lhc-time-guard.ts` is the importable time-only API built on the same
 * implementation; `install_runtime.py` installs only this file into the
 * OpenCode plugin directory.
 *
 * Scope, by owner decision:
 *   - injects a pointer to the current installed AGENTS.md into the system
 *     context, so the agent reads the rules that are actually in force;
 *   - observes wall time and delivers the canonical time-only reminder;
 *   - re-injects the AGENTS.md pointer and the bounded handoff pointer after
 *     compaction.
 * It never reviews, gates, approves, classifies a diff or reads task content.
 *
 * Every step fails open: a missing AGENTS.md, a missing Python guard or an
 * unexpected OpenCode signature must never break a session.
 */

import { spawn } from "node:child_process"
import { existsSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

/** Structural subset of the OpenCode plugin contract (@opencode-ai/plugin). */
export type LhcPluginInput = {
  client?: {
    session?: {
      get?: (input: { path: { id: string } }) => Promise<{ data?: { parentID?: string } }>
      prompt?: (input: { path: { id: string }; body: { parts: { type: "text"; text: string }[] } }) => Promise<unknown>
    }
  }
  directory?: string
  worktree?: string
  project?: { worktree?: string }
}

/** Structural subset of the OpenCode hook contract. */
export type LhcHooks = {
  event?: (input: { event: { type?: string; properties?: Record<string, unknown> } }) => Promise<void>
  "chat.message"?: (
    input: { sessionID?: string; messageID?: string },
    output: { message?: { id?: string; sessionID?: string }; parts?: unknown[] },
  ) => Promise<void>
  "tool.execute.after"?: (
    input: { tool?: string; sessionID?: string; callID?: string; args?: Record<string, unknown> },
    output: { title?: string; output?: string },
  ) => Promise<void>
  "experimental.chat.system.transform"?: (input: { sessionID?: string }, output: { system?: string[] }) => Promise<void>
  "experimental.session.compacting"?: (
    input: { sessionID?: string },
    output: { context?: string[]; prompt?: string },
  ) => Promise<void>
}

/** Resolved LHC installation and project locations. */
export type LhcPaths = {
  packageRoot: string | null
  projectRoot: string | null
  agentsFile: string | null
  entry: string | null
}

/** The time-only guard: hook surface plus the pending reminder it produced. */
export type LhcTimeGuard = LhcHooks & {
  paths: LhcPaths
  take: (sessionID: string | undefined) => string | null
}

const STATE_RELATIVE = join(".local", "state", "last-human-commit", "opencode.json")
const ENTRY_RELATIVES = [
  join("tools", "lhc_entry.py"),
  join("common", "tools", "lhc_entry.py"),
  join("plugins", "last-human-commit", "tools", "lhc_entry.py"),
  join("src", "common", "tools", "lhc_entry.py"),
]
const PACKAGE_MARKERS = [
  join("tools", "lhc_entry.py"),
  join("common", "tools", "lhc_entry.py"),
  join("plugins", "last-human-commit", "tools", "lhc_entry.py"),
]
const HANDOFF_RELATIVE = join(".agents", "shared-session", "compaction")
const GUARD_TIMEOUT_MS = 5000
const MAX_OUTPUT_CHARS = 262144

function moduleDir(): string {
  try {
    return dirname(fileURLToPath(import.meta.url))
  } catch {
    return ""
  }
}

function readState(): { packageRoot?: string } | null {
  try {
    const override = process.env.LHC_OPENCODE_STATE
    const file = override ? resolve(override) : join(homedir(), STATE_RELATIVE)
    const parsed: unknown = JSON.parse(readFileSync(file, "utf8"))
    if (!parsed || typeof parsed !== "object") return null
    return parsed as { packageRoot?: string }
  } catch {
    return null
  }
}

function absolute(value: string): string | null {
  try {
    return resolve(value)
  } catch {
    return null
  }
}

/** Every directory that may hold the installed LHC package, best first. */
function candidateRoots(context: LhcPluginInput = {}): string[] {
  const roots: string[] = []
  const add = (value: unknown) => {
    if (typeof value !== "string") return
    const trimmed = value.trim()
    if (!trimmed) return
    const next = absolute(trimmed)
    if (next && !roots.includes(next)) roots.push(next)
  }
  add(process.env.LHC_PLUGIN_ROOT)
  add(process.env.LHC_OPENCODE_PACKAGE_ROOT)
  const here = moduleDir()
  if (here) {
    add(join(here, ".."))
    add(here)
  }
  add(readState()?.packageRoot)
  add(context.directory)
  add(context.worktree)
  add(context.project?.worktree)
  return roots
}

function isPackageRoot(directory: string): boolean {
  return PACKAGE_MARKERS.some((relative) => existsSync(join(directory, relative)))
}

/** The installed LHC package root, or null when it cannot be located. */
function resolvePackageRoot(context: LhcPluginInput = {}): string | null {
  for (const root of candidateRoots(context)) {
    if (isPackageRoot(root)) return root
  }
  return null
}

/** The OpenCode project directory, or null when it cannot be located. */
function resolveProjectRoot(context: LhcPluginInput = {}): string | null {
  for (const value of [context.directory, context.worktree, context.project?.worktree]) {
    if (typeof value !== "string" || !value.trim()) continue
    const next = absolute(value.trim())
    if (next && existsSync(next)) return next
  }
  return null
}

/** Package root, project root, installed AGENTS.md and the Python guard entry. */
function resolveLhcPaths(context: LhcPluginInput = {}): LhcPaths {
  const packageRoot = resolvePackageRoot(context)
  const projectRoot = resolveProjectRoot(context)
  let entry: string | null = null
  let agentsFile: string | null = null
  if (packageRoot) {
    entry = ENTRY_RELATIVES.map((relative) => join(packageRoot, relative)).find((file) => existsSync(file)) ?? null
    const packaged = join(packageRoot, "AGENTS.md")
    if (existsSync(packaged)) agentsFile = packaged
  }
  if (!agentsFile && projectRoot) {
    const projectAgents = join(projectRoot, "AGENTS.md")
    if (existsSync(projectAgents)) agentsFile = projectAgents
  }
  return { packageRoot, projectRoot, agentsFile, entry }
}

/** Extract the reminder the Python guard printed, or null when there is none. */
function extractReminder(raw: string): string | null {
  const lines = raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const line = lines[index]
    if (!line.startsWith("{")) continue
    try {
      const parsed: unknown = JSON.parse(line)
      if (!parsed || typeof parsed !== "object") continue
      const context = (parsed as { hookSpecificOutput?: { additionalContext?: unknown } }).hookSpecificOutput
        ?.additionalContext
      if (typeof context === "string" && context.trim()) return context.trim()
    } catch {
      // Not a JSON line; keep looking.
    }
  }
  return null
}

/**
 * Run the canonical time-only guard and return its reminder.
 * Resolves to null when Python, the guard or the output is unavailable.
 */
function runTimeGuard(
  entry: string,
  options: { cwd: string; sessionID: string; runtime?: string; toolInput?: unknown },
): Promise<string | null> {
  const runtime = options.runtime ?? "opencode"
  return new Promise((resolvePromise) => {
    let settled = false
    const finish = (value: string | null) => {
      if (settled) return
      settled = true
      resolvePromise(value)
    }
    let child: ReturnType<typeof spawn>
    try {
      child = spawn(
        "python3",
        [entry, "--event", "PostToolUse", "--heartbeat-only", "--runtime", runtime],
        { cwd: options.cwd, stdio: ["pipe", "pipe", "ignore"] },
      )
    } catch {
      finish(null)
      return
    }
    const timer = setTimeout(() => {
      try {
        child.kill("SIGKILL")
      } catch {
        // The process is already gone.
      }
      finish(null)
    }, GUARD_TIMEOUT_MS)
    if (typeof timer.unref === "function") timer.unref()
    let out = ""
    child.stdout?.setEncoding("utf8")
    child.stdout?.on("data", (chunk: string) => {
      out += chunk
      if (out.length > MAX_OUTPUT_CHARS) {
        try {
          child.kill("SIGKILL")
        } catch {
          // The process is already gone.
        }
      }
    })
    child.on("error", () => {
      clearTimeout(timer)
      finish(null)
    })
    child.on("close", () => {
      clearTimeout(timer)
      finish(extractReminder(out))
    })
    try {
      // The payload carries the tool arguments whenever the plugin knows them:
      // without tool_input the hook sees no written path and never rebuilds
      // the plan, the promise Codex, Claude and Zcode already keep.
      const payload: Record<string, unknown> = { cwd: options.cwd, session_id: options.sessionID }
      if (options.toolInput !== undefined) payload.tool_input = options.toolInput
      child.stdin?.end(JSON.stringify(payload))
    } catch {
      // A guard without stdin reports nothing; that is a fail-open outcome.
    }
  })
}

/**
 * Ask the canonical Stop gate whether this idle session still has untouched plan
 * leaves. Resolves to the reason text, or null when the stop stands.
 */
function runStopGate(entry: string, options: { cwd: string; sessionID: string }): Promise<string | null> {
  return new Promise((resolvePromise) => {
    let settled = false
    const finish = (value: string | null) => {
      if (settled) return
      settled = true
      resolvePromise(value)
    }
    let child: ReturnType<typeof spawn>
    try {
      child = spawn("python3", [entry, "--event", "Stop", "--stop-gate", "--runtime", "opencode"],
        { cwd: options.cwd, stdio: ["pipe", "pipe", "ignore"] })
    } catch {
      finish(null)
      return
    }
    const timer = setTimeout(() => {
      try { child.kill("SIGKILL") } catch { /* already gone */ }
      finish(null)
    }, GUARD_TIMEOUT_MS)
    if (typeof timer.unref === "function") timer.unref()
    let out = ""
    child.stdout?.setEncoding("utf8")
    child.stdout?.on("data", (chunk: string) => { if (out.length < MAX_OUTPUT_CHARS) out += chunk })
    child.on("error", () => { clearTimeout(timer); finish(null) })
    child.on("close", () => {
      clearTimeout(timer)
      try {
        const parsed = JSON.parse(out)
        finish(parsed?.decision === "block" && typeof parsed.reason === "string" ? parsed.reason : null)
      } catch {
        finish(null)
      }
    })
    try {
      child.stdin?.end(JSON.stringify({ cwd: options.cwd, session_id: options.sessionID }))
    } catch { /* fail open */ }
  })
}

/** The bounded session handoff written by the compaction protocol, if any. */
function handoffFile(projectRoot: string | null, sessionID: string): string | null {
  if (!projectRoot || !sessionID) return null
  const file = join(projectRoot, HANDOFF_RELATIVE, sessionID, "current-handoff.md")
  return existsSync(file) ? file : null
}

/**
 * Time-only guard: observes the wall clock and reports what to call.
 * It never reviews, gates or evaluates anything.
 */
const LastHumanCommitTimeGuard = async (context: LhcPluginInput = {}): Promise<LhcTimeGuard> => {
  const paths = resolveLhcPaths(context)
  const pending = new Map<string, string>()
  const running = new Set<string>()

  const observe = async (sessionID: string, toolInput?: unknown) => {
    if (!sessionID || !paths.entry || !paths.projectRoot) return
    if (running.has(sessionID)) return
    running.add(sessionID)
    try {
      const reminder = await runTimeGuard(paths.entry, { cwd: paths.projectRoot, sessionID, toolInput })
      if (reminder) pending.set(sessionID, reminder)
    } catch {
      // A missing or failing guard must not disturb the session.
    } finally {
      running.delete(sessionID)
    }
  }

  const take = (sessionID: string | undefined): string | null => {
    if (!sessionID) return null
    const reminder = pending.get(sessionID)
    if (!reminder) return null
    pending.delete(sessionID)
    return reminder
  }

  return {
    paths,
    take,
    event: async (input) => {
      try {
        const type = input?.event?.type
        if (type !== "session.idle" && type !== "session.created" && type !== "session.compacted") return
        const sessionID = input?.event?.properties?.sessionID
        if (typeof sessionID !== "string") return
        await observe(sessionID)
      } catch {
        // Fail open: an event handler must never break the session.
      }
    },
    "tool.execute.after": async (input) => {
      try {
        const sessionID = input?.sessionID
        if (typeof sessionID !== "string") return
        await observe(sessionID, input?.args)
      } catch {
        // Fail open: a tool boundary must never break the session.
      }
    },
    "chat.message": async (input, output) => {
      try {
        const reminder = take(input?.sessionID)
        if (!reminder) return
        const parts = output?.parts
        if (!Array.isArray(parts)) return
        const message = output?.message
        const messageID = typeof message?.id === "string" ? message.id : (input?.messageID ?? "")
        const sessionID = typeof message?.sessionID === "string" ? message.sessionID : (input?.sessionID ?? "")
        parts.push({
          id: `lhc_${sessionID}_${messageID}_${parts.length}`,
          sessionID,
          messageID,
          type: "text",
          text: reminder,
          synthetic: true,
        })
      } catch {
        // Fail open: an undeliverable reminder is not a session failure.
      }
    },
  }
}

/**
 * The OpenCode plugin entry point.
 *
 * OpenCode 1.18.x contract: `export default async (input, options) => hooks`.
 */
const LastHumanCommitV2 = async (input: LhcPluginInput = {}): Promise<LhcHooks> => {
  let guard: LhcTimeGuard | null = null
  try {
    guard = await LastHumanCommitTimeGuard(input)
  } catch {
    guard = null
  }
  const paths = guard?.paths ?? resolveLhcPaths(input)
  const pointer = paths.agentsFile ? `LHC: read ${paths.agentsFile} for current instructions.` : null
  const already = (lines: string[], needle: string) => lines.some((line) => typeof line === "string" && line.includes(needle))

  const holdStop = async (hookInput: { event?: { type?: string; properties?: Record<string, unknown> } }) => {
    try {
      if (hookInput?.event?.type !== "session.idle") return
      const sessionID = hookInput.event.properties?.sessionID
      if (typeof sessionID !== "string" || !paths.entry || !paths.projectRoot) return
      const session = input.client?.session
      if (!session?.prompt) return
      const info = await session.get?.({ path: { id: sessionID } }).catch(() => undefined)
      if (info?.data?.parentID) return  // a subagent session never carries the plan
      const reason = await runStopGate(paths.entry, { cwd: paths.projectRoot, sessionID })
      if (reason) await session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: reason }] } })
    } catch {
      // Fail open: a stop that cannot be held is simply a stop.
    }
  }

  return {
    event: async (hookInput) => {
      await guard?.event?.(hookInput)
      await holdStop(hookInput)
    },
    "tool.execute.after": guard?.["tool.execute.after"],
    "chat.message": guard?.["chat.message"],
    "experimental.chat.system.transform": async (hookInput, output) => {
      try {
        const system = output?.system
        if (!Array.isArray(system)) return
        if (pointer && !already(system, paths.agentsFile as string)) system.push(pointer)
        const reminder = guard?.take(hookInput?.sessionID)
        if (reminder) system.push(reminder)
      } catch {
        // Fail open: the session continues without the extra context.
      }
    },
    "experimental.session.compacting": async (hookInput, output) => {
      try {
        const context = output?.context
        if (!Array.isArray(context)) return
        if (pointer && !already(context, paths.agentsFile as string)) context.push(pointer)
        const handoff = handoffFile(paths.projectRoot, hookInput?.sessionID ?? "")
        if (handoff) context.push(`LHC: read ${handoff} for the current session handoff before continuing.`)
      } catch {
        // Fail open: compaction continues with its default context.
      }
    },
  }
}

/**
 * The single runtime export of this module.
 *
 * OpenCode 1.18.x instantiates every export of a plugin module, so the public
 * API travels on the default export instead of on separate named exports.
 * `lhc-time-guard.ts` re-exports the time-only part of it.
 */
export default Object.assign(LastHumanCommitV2, {
  id: "last-human-commit",
  LastHumanCommitTimeGuard,
  candidateRoots,
  resolveLhcPaths,
  resolvePackageRoot,
  resolveProjectRoot,
  extractReminder,
  runTimeGuard,
  runStopGate,
  handoffFile,
})
