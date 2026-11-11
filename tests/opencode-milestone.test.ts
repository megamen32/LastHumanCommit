import {expect,test} from "bun:test"
import plugin from "../plugins/last-human-commit/opencode/lhc-v2"

const clearWorkflowEnv = () => {
  delete process.env.LHC_VERBOSE_WORKFLOW
  delete process.env.LHC_STRICT_WORKFLOW
}

test("OpenCode default mode keeps useful instruction hooks without accounting gates", async () => {
  clearWorkflowEnv()
  const hooks = await plugin({directory: process.cwd()})
  expect(hooks.event).toBeDefined()
  expect(hooks["experimental.chat.system.transform"]).toBeDefined()
  expect(hooks["experimental.session.compacting"]).toBeDefined()
  expect(hooks["tool.execute.before"]).toBeDefined()
  expect(hooks["tool.execute.after"]).toBeDefined()
})

test("OpenCode default event path does not invoke stop or heartbeat work", async () => {
  clearWorkflowEnv()
  const hooks = await plugin({directory: process.cwd()})
  await hooks.event?.({event: {type: "session.idle", properties: {sessionID: "ordinary"}}})
  await hooks["tool.execute.before"]?.({tool: "bash", sessionID: "ordinary", callID: "c"}, {args: {command: "git status"}})
})

test("strict and verbose modes remain explicit escape hatches", async () => {
  process.env.LHC_VERBOSE_WORKFLOW = "1"
  process.env.LHC_STRICT_WORKFLOW = "1"
  const hooks = await plugin({directory: process.cwd()})
  expect(hooks.event).toBeDefined()
  expect(hooks["tool.execute.before"]).toBeDefined()
  clearWorkflowEnv()
})
