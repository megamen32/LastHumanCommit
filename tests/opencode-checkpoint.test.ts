import {test, expect} from "bun:test";
import {mkdtemp, readFile, readdir, rm} from "node:fs/promises";
import {join} from "node:path";
import {LastHumanCommitTimeGuard} from "../plugins/last-human-commit/opencode/lhc-time-guard.ts";

test("native plugin is active by default, records user goal and pauses on idle", async()=>{
 const cwd=await mkdtemp(join(import.meta.dir,"..",".tmp","opencode-fixture-"));
 const process=Bun.spawn(["git","init","-q",cwd]);expect(await process.exited).toBe(0);
 const prior=Bun.env.LHC_TIME_GUARD_ENABLED;delete Bun.env.LHC_TIME_GUARD_ENABLED;
 try {
  const plugin=await LastHumanCommitTimeGuard({directory:cwd});
  const output={parts:[{type:"text",text:"Use the existing report; no dashboard rewrite"}]};
  await plugin["chat.message"]({sessionID:"native-opencode-fixture"},output);
  const dir=join(cwd,".agents/shared-session/learning");
  const file=(await readdir(dir)).find(x=>x.endsWith(".json"))!;
  const state=JSON.parse(await readFile(join(dir,file),"utf8"));
  expect(state.business.original_prompt).toBe("Use the existing report; no dashboard rewrite");
  expect(state.business.interval.status).toBe("running");
  await plugin.event({event:{type:"permission.asked",properties:{sessionID:"native-opencode-fixture"}}});
  expect(JSON.parse(await readFile(join(dir,file),"utf8")).business.interval.status).toBe("paused");
  await plugin.event({event:{type:"permission.replied",properties:{sessionID:"native-opencode-fixture",reply:"once"}}});
  expect(JSON.parse(await readFile(join(dir,file),"utf8")).business.interval.status).toBe("running");
  await plugin.event({event:{type:"session.idle",properties:{sessionID:"native-opencode-fixture"}}});
  const paused=JSON.parse(await readFile(join(dir,file),"utf8"));
  expect(paused.business.interval.status).toBe("paused");
 } finally {
  if(prior!==undefined)Bun.env.LHC_TIME_GUARD_ENABLED=prior;
  await rm(cwd,{recursive:true,force:true});
 }
});
