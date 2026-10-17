import {fileURLToPath} from "node:url"
import {isAbsolute} from "node:path"

// Native OpenCode 2.x entrypoint. The business rules/state remain the same Python
// implementation as V1/Codex; returning a V1 hook dictionary is not a V2 plugin.
const root=fileURLToPath(new URL("../",import.meta.url)).replace(/\/$/,"")
const entry=`LHC engineering workflow: ${root}/AGENTS.md. Read that router once for an engineering task; no slash command or setup interview. Preserve the user's tangible outcome and corrections. Three-pass design, hourly direction review, 120-minute learning and blind feedback only at major milestones remain in force.`
type Hook=(event:any)=>Promise<void>
type Context={
 location:{directory:string},
 session:{get:(args:{sessionID:string})=>Promise<any>;hook:(name:string,callback:Hook)=>Promise<unknown>},
 tool:{hook:(name:string,callback:Hook)=>Promise<unknown>},
 event:{subscribe:(args:{signal:AbortSignal})=>AsyncIterable<any>}
}

export default {
 id:"last-human-commit",
 async setup(ctx:Context){
  const controller=new AbortController()
  const observed=new Set<string>()
  const pending=new Map<string,string>()
  const chains=new Map<string,Promise<any>>()
  let stopped=false
  async function invoke(sessionID:string,event:string,prompt?:string):Promise<any>{
   if(stopped || !sessionID)return {}
   // Native callbacks can arrive simultaneously; retain lifecycle order per session.
   const previous=chains.get(sessionID)??Promise.resolve()
   const operation=previous.catch(()=>{}).then(async()=>{
    let child:ReturnType<typeof Bun.spawn>|undefined,timer:ReturnType<typeof setTimeout>|undefined
    try{
     const result=await ctx.session.get({sessionID})
     const info=result?.data??result
     const directory=info?.location?.directory
     // Never record a different session against the server's home/default project.
     if(typeof directory!=="string" || !isAbsolute(directory))return {}
     observed.add(sessionID)
     if(observed.size>512)observed.delete(observed.values().next().value!)
     child=Bun.spawn(["python3",`${root}/tools/lhc_time_guard.py`,"hook","--runtime","opencode","--event",event,
       ...(["PreCompact","PostCompact"].includes(event)?[]:["--session-only"])],
       {stdin:"pipe",stdout:"pipe",stderr:"ignore"})
     child.stdin.write(JSON.stringify({cwd:directory,session_id:sessionID,prompt}));child.stdin.end()
     const output=await Promise.race([new Response(child.stdout).text(),new Promise<never>((_,reject)=>{
      timer=setTimeout(()=>reject(new Error("LHC guard timeout")),5000)
     })])
     if(await child.exited!==0 || !output.trim())return {}
     return JSON.parse(output)
    }catch{return {}}finally{if(timer)clearTimeout(timer);if(child && child.exitCode===null)child.kill()}
   })
   chains.set(sessionID,operation)
   try{return await operation}finally{if(chains.get(sessionID)===operation)chains.delete(sessionID)}
  }
  function retain(id:string,result:any){
   const value=result?.prompt
   if(typeof value==="string" && value.trim())pending.set(id,value)
   if(pending.size>512)pending.delete(pending.keys().next().value!)
  }
  const safe=(fn:Hook):Hook=>async event=>{try{await fn(event)}catch{/* Advice must not block the user's operation. */}}
  await ctx.session.hook("prompt",safe(async event=>{
   // Do not alter durable user text. Context injection happens at model dispatch.
   retain(event.sessionID,await invoke(event.sessionID,"chat.message",event.prompt?.text))
  }))
  await ctx.session.hook("context",safe(async event=>{
   const result=await invoke(event.sessionID,"tool.execute.after")
   if(!Array.isArray(event.system))return
   event.system.push({type:"text",text:entry})
   const notices=[pending.get(event.sessionID),result?.prompt].filter((x):x is string=>typeof x==="string"&&!!x.trim())
   for(const text of new Set(notices))event.system.push({type:"text",text})
   pending.delete(event.sessionID)
  }))
  await ctx.session.hook("compaction",safe(async event=>{
   const result=await invoke(event.sessionID,"PreCompact")
   if(!Array.isArray(event.system))return
   event.system.push({type:"text",text:entry})
   const notice=[pending.get(event.sessionID),result?.handoff??result?.prompt].filter(Boolean).join("\n\n")
   if(notice)event.system.push({type:"text",text:notice})
   pending.delete(event.sessionID)
  }))
  await ctx.tool.hook("execute.before",safe(async event=>{await invoke(event.sessionID,"tool.execute.before")}))
  await ctx.tool.hook("execute.after",safe(async event=>{
   retain(event.sessionID,await invoke(event.sessionID,"tool.execute.after"))
  }))
  const events=(async()=>{
   try{
    for await(const event of ctx.event.subscribe({signal:controller.signal})){
     if(stopped)break
     const data=event.data??event.properties??{}
     const id=data.sessionID
     // A location-scoped plugin sees global events. Only observe sessions whose
     // actual operations this instance intercepted; never wake or touch others.
     if(!id || !observed.has(id))continue
     let native:string|undefined
     if(["session.execution.succeeded","session.execution.failed","session.execution.interrupted"].includes(event.type))native="session.idle"
     else if(event.type==="session.execution.started")native="tool.execute.before"
     else if(event.type==="session.status"){
      if(data.status?.type==="idle" || data.status?.type==="retry")native="session.idle"
      else if(data.status?.type==="busy")native="tool.execute.before"
     }else if(["session.idle","session.error","permission.asked"].includes(event.type))native=event.type
     else if(event.type==="permission.replied" && data.reply!=="reject")native=event.type
     else if(["session.compacted","session.compaction.ended"].includes(event.type))native="PostCompact"
     if(native)retain(id,await invoke(id,native))
    }
   }catch{/* The next native hook still performs control; no synthetic continuation. */}
  })()
  return async()=>{
   stopped=true;controller.abort();await events
   await Promise.allSettled(chains.values());observed.clear();pending.clear()
  }
 }
}
