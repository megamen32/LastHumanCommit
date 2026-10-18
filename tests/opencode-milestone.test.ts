import {expect,test} from "bun:test"
import {mkdtemp,readdir,readFile,writeFile,rm} from "node:fs/promises"
import {join} from "node:path"
import plugin from "../plugins/last-human-commit/opencode/lhc-v2"

async function fixture(run:(hooks:Map<string,Function>,root:string,state:()=>Promise<any>,emit:(type:string)=>void)=>Promise<void>){
 const root=await mkdtemp(join(import.meta.dir,"../.tmp/native-milestone-"))
 Bun.spawnSync(["git","init","-q",root])
 const hooks=new Map<string,Function>(),queue:any[]=[];let wake:Function|undefined,closed=false
 const ctx:any={session:{get:async()=>({data:{location:{directory:root}}}),hook:async(n:string,f:Function)=>{hooks.set(n,f)}},
  tool:{hook:async(n:string,f:Function)=>{hooks.set(n,f)}},event:{subscribe:({signal}:any)=>({async *[Symbol.asyncIterator](){
   signal.addEventListener("abort",()=>{closed=true;wake?.()},{once:true})
   while(!closed){if(!queue.length)await new Promise(r=>wake=r);if(queue.length)yield queue.shift()}
  }})}}
 const stop=await plugin.setup(ctx)
 const state=async()=>{const dir=join(root,".agents/shared-session/learning");return JSON.parse(await readFile(join(dir,(await readdir(dir)).find(n=>n.endsWith(".json"))!),"utf8"))}
 try{await run(hooks,root,state,(type)=>{queue.push({type,data:{sessionID:"native-ui"}});wake?.()})}
 finally{await stop();await rm(root,{recursive:true,force:true})}
}

test("ordinary OpenCode UI context bootstraps intent, observes generated HTML and preserves pending across compaction",async()=>{
 await fixture(async(hooks,root,state)=>{
  const event={sessionID:"native-ui",system:[],messages:[{role:"user",content:"Build a complete customer dashboard with search, import and mobile navigation"}]}
  await hooks.get("context")!(event)
  await writeFile(join(root,"server.mjs"),'res.end(`<main><input><button>Import</button></main>`)')
  await hooks.get("execute.after")!({sessionID:"native-ui",tool:"bash",status:"completed",result:{content:"saved"}})
  const next={sessionID:"native-ui",system:[],messages:[]}
  await hooks.get("context")!(next)
  expect(JSON.stringify(next.system)).toContain("Zero Knowledge")
  expect((await state()).milestone.status).toBe("pending")
  const compact={sessionID:"native-ui",system:[]};await hooks.get("compaction")!(compact)
  expect(JSON.stringify(compact.system)).toContain("milestone_acceptance")
  expect((await state()).milestone.status).toBe("pending")
 })
})

test.each(["interrupted","failed"])("OpenCode %s retains acceptance without resuming or synthesizing a prompt",async(outcome)=>{
 await fixture(async(hooks,root,state,emit)=>{
  await hooks.get("prompt")!({sessionID:"native-ui",prompt:{text:"Build a complete UI dashboard"}})
  await writeFile(join(root,"index.html"),"<main><button>Import</button></main>")
  await hooks.get("execute.after")!({sessionID:"native-ui",status:"completed",result:{content:"saved"}})
  emit("session.execution."+outcome)
  let s:any
  for(let i=0;i<30;i++){s=await state();if(s.milestone.hold)break;await Bun.sleep(20)}
  expect(s.milestone.hold).toBe(outcome==="interrupted"?"Interrupt":"session.error")
  expect(s.milestone.status).toBe("pending")
  expect(s.business.interval.status).toBe("paused")
  expect(s.milestone.continuation_requested).toBeUndefined()
 })
})

test("OpenCode native tool error stays held; a read-only tester never receives a recruitment debt",async()=>{
 await fixture(async(hooks,root,state)=>{
  await hooks.get("prompt")!({sessionID:"native-ui",prompt:{text:"You are a fresh Zero Knowledge tester. Read-only attempt on the UI dashboard."}})
  await writeFile(join(root,"index.html"),"<main><button>Import</button></main>")
  await hooks.get("execute.after")!({sessionID:"native-ui",status:"error",error:{message:"tool offline"}})
  expect((await state()).milestone.hold).toBe("ToolFailure")
  expect((await state()).milestone.status).toBe("not-required")
 })
})
