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
): Promise<GuardResult> {
  try {
    const process = Bun.spawn(
      ["python3", guard, "hook", "--runtime", "opencode", "--event", event],
      { stdin: "pipe", stdout: "pipe", stderr: "ignore" },
    )
    process.stdin.write(
      JSON.stringify({ cwd: directory, hook_event_name: event, session_id: sessionID }),
    )
    process.stdin.end()
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("LHC guard timeout")), 1000),
    )
    const output = await Promise.race([new Response(process.stdout).text(), timeout])
    if ((await process.exited) !== 0 || !output.trim()) return {}
    const parsed = JSON.parse(output)
    return typeof parsed === "object" && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

export const LastHumanCommitTimeGuard = async ({ directory }: { directory: string }) => ({
  "chat.message": async (
    input: { sessionID?: string },
    output: { parts: Array<Record<string, unknown>> },
  ) => {
    const { prompt } = await check(directory, "chat.message", input.sessionID)
    if (prompt) output.parts.push({ type: "text", text: prompt, synthetic: true })
  },
  "tool.execute.after": async (
    input: { sessionID?: string },
    output: { output: string },
  ) => {
    const { prompt } = await check(directory, "tool.execute.after", input.sessionID)
    if (prompt) output.output = `${output.output}\n\n${prompt}`
  },
  "experimental.session.compacting": async (
    input: { sessionID: string },
    output: { context: string[] },
  ) => {
    const { handoff } = await check(directory, "PreCompact", input.sessionID)
    if (handoff) output.context.push(handoff)
  },
  "experimental.compaction.autocontinue": async (
    input: { sessionID: string },
    _output: { enabled: boolean },
  ) => {
    await check(directory, "PostCompact", input.sessionID)
  },
})
