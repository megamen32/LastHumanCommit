import {expect,test} from "bun:test"
import {mkdtemp,readFile,readdir,rm} from "node:fs/promises"
import {join} from "node:path"
import plugin from "../plugins/last-human-commit/opencode/lhc-v2"

test.each(["succeeded","failed","interrupted"])("native V2 receives original prompt, injects LHC and pauses after %s",async(outcome)=>{
 const root=await mkdtemp(join(import.meta.dir,"../.tmp/v2-test-"))
 Bun.spawnSync(["git","init","-q",root])
 const hooks=new Map<string,Function>(),queue:any[]=[];let wake:Function|undefined,aborted=false
 const ctx:any={location:{directory:"/must-not-be-used"},session:{
  get:async()=>({data:{location:{directory:root}}}),hook:async(name:string,fn:Function)=>{hooks.set("session:"+name,fn)}},
  tool:{hook:async(name:string,fn:Function)=>{hooks.set("tool:"+name,fn)}},
  event:{subscribe:({signal}:any)=>({async *[Symbol.asyncIterator](){
   signal.addEventListener("abort",()=>{aborted=true;wake?.()},{once:true})
   while(!aborted){if(!queue.length)await new Promise(r=>wake=r);if(queue.length)yield queue.shift()}
  }})}}
 let stop:any
 try{
  expect(plugin.id).toBe("last-human-commit")
  stop=await plugin.setup(ctx)
  const event={sessionID:"ses_lhc_v2_test",prompt:{text:"Исправь переносы по краям имени"}}
  await hooks.get("session:prompt")!(event)
  expect(event.prompt.text).toBe("Исправь переносы по краям имени")
  const context={sessionID:event.sessionID,system:[],messages:[]}
  await hooks.get("session:context")!(context)
  expect(JSON.stringify(context.system)).toContain("AGENTS.md")
  const dir=join(root,".agents/shared-session/learning")
  const file=(await readdir(dir)).find(n=>n.endsWith(".json"))!
  let state=JSON.parse(await readFile(join(dir,file),"utf8"))
  expect(state.business.original_prompt).toBe(event.prompt.text)
  queue.push({type:"session.execution."+outcome,data:{sessionID:event.sessionID},location:{directory:root}});wake?.()
  for(let i=0;i<30;i++){state=JSON.parse(await readFile(join(dir,file),"utf8"));if(state.business.interval.status==="paused")break;await Bun.sleep(30)}
  expect(state.business.interval.status).toBe("paused")
  expect(state.business.last_review).toBeNull()
 }finally{await stop?.();await rm(root,{recursive:true,force:true})}
})
