const guard =
  process.env.LHC_TIME_GUARD ??
  `${import.meta.dir}/../tools/lhc_time_guard.py`

type GuardResult = {
  prompt?: string
  handoff?: string
  handoff_path?: string
  compaction_count?: number
}

async function check(
  directory: string,
  event: string,
  sessionID?: string,
  prompt?: string,
): Promise<GuardResult> {
  let timer: ReturnType<typeof setTimeout> | undefined
  let child: ReturnType<typeof Bun.spawn> | undefined
  try {
    const process = Bun.spawn(
      ["python3", guard, "hook", "--runtime", "opencode", "--event", event,
        ...(["PreCompact", "PostCompact"].includes(event) ? [] : ["--session-only"])],
      { stdin: "pipe", stdout: "pipe", stderr: "ignore" },
    )
    child = process
    process.stdin.write(
      JSON.stringify({ cwd: directory, hook_event_name: event, session_id: sessionID, prompt }),
    )
    process.stdin.end()
    const timeout = new Promise<never>((_, reject) =>
      timer = setTimeout(() => reject(new Error("LHC guard timeout")), 5000),
    )
    const output = await Promise.race([new Response(process.stdout).text(), timeout])
    if ((await process.exited) !== 0 || !output.trim()) return {}
    const parsed = JSON.parse(output)
    return typeof parsed === "object" && parsed !== null ? parsed : {}
  } catch {
    child?.kill()
    return {}
  } finally {
    if (timer) clearTimeout(timer)
  }
}

// Keep the installed filename/export compatible, but default to a small entry.
// Hourly business and 120m learning checkpoints are enabled by default.
const entered = new Set<string>()
const entry = `LHC: read ${import.meta.dir}/../AGENTS.md for ordinary engineering requests. No slash command or setup interview is required. Keep independent work moving, isolate concurrent writers and integrate verified PRs.`
export const LastHumanCommitTimeGuard = async ({ directory }: { directory: string }) => ({
  event: async ({ event }: { event: { type: string; properties?: { sessionID?: string; reply?: string } } }) => {
    if (["session.idle", "session.error", "permission.asked", "permission.replied"].includes(event.type) && event.properties?.sessionID) {
      if (event.type === "permission.replied" && event.properties.reply === "reject") return
      await check(directory, event.type, event.properties.sessionID)
    }
  },
  "chat.message": async (
    input: { sessionID?: string },
    output: { parts: Array<Record<string, unknown>> },
  ) => {
    const identity = input.sessionID ?? directory
    if (!entered.has(identity)) {
      if (entered.size >= 256) entered.delete(entered.values().next().value!)
      entered.add(identity)
      output.parts.push({ type: "text", text: entry, synthetic: true })
    }
    if (process.env.LHC_TIME_GUARD_ENABLED === "0") return
    const { prompt } = await check(directory, "chat.message", input.sessionID,
      output.parts.filter(part => part.type === "text" && !part.synthetic).map(part => String(part.text ?? "")).join("\n"))
    if (prompt) output.parts.push({ type: "text", text: prompt, synthetic: true })
  },
  "tool.execute.before": async (input: { sessionID?: string }) => {
    if (process.env.LHC_TIME_GUARD_ENABLED !== "0") await check(directory, "tool.execute.before", input.sessionID)
  },
  "tool.execute.after": async (
    input: { sessionID?: string },
    output: { output: string },
  ) => {
    if (process.env.LHC_TIME_GUARD_ENABLED === "0") return
    const { prompt } = await check(directory, "tool.execute.after", input.sessionID)
    if (prompt) output.output = `${output.output}\n\n${prompt}`
  },
  "experimental.session.compacting": async (
    input: { sessionID: string },
    output: { context: string[] },
  ) => {
    output.context.push(entry)
    if (process.env.LHC_TIME_GUARD_ENABLED === "0") return
    const { handoff } = await check(directory, "PreCompact", input.sessionID)
    if (handoff) output.context.push(handoff)
  },
  "experimental.compaction.autocontinue": async (
    input: { sessionID: string },
    _output: { enabled: boolean },
  ) => {
    entered.delete(input.sessionID)
    if (process.env.LHC_TIME_GUARD_ENABLED !== "0") await check(directory, "PostCompact", input.sessionID)
  },
})
