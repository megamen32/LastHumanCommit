const guard =
  process.env.LHC_TIME_GUARD ??
  `${import.meta.dir}/../tools/lhc_time_guard.py`

async function check(directory: string, event: string): Promise<string> {
  try {
    const process = Bun.spawn(
      ["python3", guard, "hook", "--runtime", "opencode", "--event", event],
      { stdin: "pipe", stdout: "pipe", stderr: "ignore" },
    )
    process.stdin.write(JSON.stringify({ cwd: directory, hook_event_name: event }))
    process.stdin.end()
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("LHC guard timeout")), 1000),
    )
    const output = await Promise.race([new Response(process.stdout).text(), timeout])
    if ((await process.exited) !== 0 || !output.trim()) return ""
    const parsed = JSON.parse(output)
    return typeof parsed.prompt === "string" ? parsed.prompt : ""
  } catch {
    return ""
  }
}

export const LastHumanCommitTimeGuard = async ({ directory }: { directory: string }) => ({
  "chat.message": async (_input: unknown, output: { parts: Array<Record<string, unknown>> }) => {
    const prompt = await check(directory, "chat.message")
    if (prompt) output.parts.push({ type: "text", text: prompt, synthetic: true })
  },
  "tool.execute.after": async (
    _input: unknown,
    output: { output: string },
  ) => {
    const prompt = await check(directory, "tool.execute.after")
    if (prompt) output.output = `${output.output}\n\n${prompt}`
  },
})
