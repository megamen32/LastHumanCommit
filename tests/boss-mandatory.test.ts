// LHC:COVERS plugins/last-human-commit/opencode/lhc-boss-v2.ts
import { expect, test, spyOn } from "bun:test"
import * as os from "node:os"
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { join, resolve } from "node:path"
import plugin from "../plugins/last-human-commit/opencode/lhc-boss-v2"

test("Boss audits run with optional workflow flags off and inject all prose", async () => {
  const sandboxRoot = resolve(import.meta.dir, "../.tmp")
  mkdirSync(sandboxRoot, { recursive: true })
  const home = mkdtempSync(join(sandboxRoot, "boss-mandatory-"))
  const previous = { HOME: process.env.HOME, LHC_VERBOSE_WORKFLOW: process.env.LHC_VERBOSE_WORKFLOW,
    LHC_STRICT_WORKFLOW: process.env.LHC_STRICT_WORKFLOW }
  const originalInterval = globalThis.setInterval
  const originalClearInterval = globalThis.clearInterval
  const homeSpy = spyOn(os, "homedir").mockReturnValue(home)
  const originalNow = Date.now
  const hooks = new Map<string, (event: any) => unknown>()
  const created: any[] = [], prompted: any[] = [], injected: any[] = []
  let tick: (() => void) | undefined
  let now = 1000
  let close: (() => Promise<void> | void) | undefined
  let watchdog: ReturnType<typeof setTimeout> | undefined
  let finish!: () => void
  const delivered = new Promise<void>(resolve => { finish = resolve })
  const prose = ["Ты отменил явно выбранное пользователем правило.", "Оставь обязательный аудит Boss. " + "Подробное объяснение. ".repeat(500)]
  try {
    process.env.HOME = home
    process.env.LHC_VERBOSE_WORKFLOW = "0"
    process.env.LHC_STRICT_WORKFLOW = "0"
    const stateDir = join(home, ".local/state/last-human-commit")
    const packageRoot = join(home, "package")
    mkdirSync(stateDir, { recursive: true })
    mkdirSync(join(packageRoot, "common/agents"), { recursive: true })
    const role = readFileSync(resolve(import.meta.dir, "../src/common/agents/Boss.md"), "utf8")
    writeFileSync(join(packageRoot, "common/agents/Boss.md"), role)
    writeFileSync(join(stateDir, "opencode.json"), JSON.stringify({ packageRoot }))
    Date.now = () => now
    globalThis.setInterval = ((callback: () => void, delay: number) => {
      expect(delay).toBe(60_000)
      tick = callback
      return 271828 as any
    }) as typeof setInterval
    globalThis.clearInterval = ((handle: any) => {
      if (handle !== 271828) originalClearInterval(handle)
    }) as typeof clearInterval
    const ctx = {
      session: {
        hook: async (name: string, callback: (e: any) => unknown) => {
          hooks.set(name, callback)
          return { dispose() { hooks.delete(name) } }
        },
        get: async () => ({ id: "parent", model: { providerID: "fixture", id: "native-model" } }),
        context: async ({ sessionID }: any) => sessionID === "parent" ? [
          { info: { role: "user" }, parts: [{ type: "text", text: "Сделай работающий результат." }] },
          { info: { role: "assistant" }, parts: [{ type: "text", text: "Проверяю те же тесты снова." }] }
        ] : prose.map(text => ({ info: { role: "assistant" }, parts: [{ type: "text", text }] })),
        create: async (args: any) => { created.push(args); return { id: "boss-child" } },
        switchModel: async ({ model }: any) => { expect(model).toEqual({ providerID: "fixture", id: "native-model" }) },
        prompt: async (args: any) => {
          prompted.push(args)
          await hooks.get("prompt")?.({ sessionID: args.sessionID })
          const context = { sessionID: args.sessionID, system: [] as any[], tools: { read: {}, bash: {} } }
          await hooks.get("context")?.(context)
          expect(context.system[0].text).toBe(role)
          expect(Object.keys(context.tools)).toEqual(["read"])
        },
        wait: async () => {},
        interrupt: async () => {},
        synthetic: async (args: any) => { injected.push(args); finish() }
      },
      event: { async *subscribe() {} }
    }
    close = await plugin.setup(ctx)
    expect(tick).toBeDefined()
    await hooks.get("prompt")?.({ sessionID: "parent" })
    now += 29 * 60_000
    tick!()
    expect(created.length).toBe(0)
    now += 60_000
    tick!()
    await Promise.race([delivered, new Promise<void>((_, reject) => {
      watchdog = setTimeout(() => reject(new Error("scheduled Boss did not inject feedback")), 2000)
    })])
    expect(created.length).toBe(1)
    expect(created[0].parentID).toBe("parent")
    expect(prompted[0].text).toContain("Доступный журнал сессии файлом:")
    expect(injected).toEqual([{ sessionID: "parent", delivery: "steer", resume: false,
      text: prose.join("\n\n") }])
    tick!()
    expect(created.length).toBe(1)
  } finally {
    if (watchdog) clearTimeout(watchdog)
    if (close) await close()
    homeSpy.mockRestore()
    Date.now = originalNow
    globalThis.setInterval = originalInterval
    globalThis.clearInterval = originalClearInterval
    for (const [name, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[name]
      else process.env[name] = value
    }
    rmSync(home, { recursive: true, force: true })
  }
})
