import {fileURLToPath} from "node:url"
import {isAbsolute} from "node:path"

// OpenCode V2 uses the same canonical native entry/goal/checkpoint as Codex.
// Avoid a second, stale TypeScript paraphrase of the LHC business contract.
const root=fileURLToPath(new URL("../",import.meta.url)).replace(/\/$/,"")
type Hook=(event:any)=>Promise<void>
type Context={
 location:{directory:string},
 session:{get:(args:{sessionID:string})=>Promise<any>;hook:(name:string,callback:Hook)=>Promise<unknown>},
 tool:{hook:(name:string,callback:Hook)=>Promise<unknown>},
 event:{subscribe:(args:{signal:AbortSignal})=>AsyncIterable<any>}
}
function text(result:any):string{
 const value=result?.hookSpecificOutput?.additionalContext??result?.prompt??result?.systemMessage
 return typeof value==="string"?value:""
}
export default {
 id:"last-human-commit",
 async setup(ctx:Context){
  const controller=new AbortController()
  const observed=new Set<string>()
  const pending=new Map<string,string>()
  const chains=new Map<string,Promise<any>>()
  let stopped=false
  async function invoke(sessionID:string,event:string,prompt?:string,details:Record<string,unknown>={}):Promise<any>{
   if(stopped || !sessionID)return {}
   const previous=chains.get(sessionID)??Promise.resolve()
   const operation=previous.catch(()=>{}).then(async()=>{
    let child:ReturnType<typeof Bun.spawn>|undefined,timer:ReturnType<typeof setTimeout>|undefined
    try{
     const result=await ctx.session.get({sessionID})
     const info=result?.data??result
     const directory=info?.location?.directory
     if(typeof directory!=="string" || !isAbsolute(directory))return {}
     observed.add(sessionID)
     if(observed.size>512)observed.delete(observed.values().next().value!)
     child=Bun.spawn(["python3",root+"/tools/lhc_entry.py","--runtime","opencode","--event",event],
       {stdin:"pipe",stdout:"pipe",stderr:"ignore"})
     child.stdin.write(JSON.stringify({...details,cwd:directory,session_id:sessionID,prompt}));child.stdin.end()
     const output=await Promise.race([new Response(child.stdout).text(),new Promise<never>((_,reject)=>{
      timer=setTimeout(()=>reject(new Error("LHC native entry timeout")),5000)
     })])
     if(await child.exited!==0 || !output.trim())return {}
     return JSON.parse(output)
    }catch{return {}}finally{if(timer)clearTimeout(timer);if(child&&child.exitCode===null)child.kill()}
   })
   chains.set(sessionID,operation)
   try{return await operation}finally{if(chains.get(sessionID)===operation)chains.delete(sessionID)}
  }
  function retain(id:string,result:any){
   const value=text(result)
   if(value.trim())pending.set(id,value)
   if(pending.size>512)pending.delete(pending.keys().next().value!)
  }
  const safe=(fn:Hook):Hook=>async event=>{try{await fn(event)}catch{/* Never veto a user action. */}}
  await ctx.session.hook("prompt",safe(async event=>{
   retain(event.sessionID,await invoke(event.sessionID,"UserPromptSubmit",event.prompt?.text))
  }))
  await ctx.session.hook("context",safe(async event=>{
   // Existing threads bootstrap here without a SessionStart event.
   const result=await invoke(event.sessionID,"PreToolUse",undefined,{messages:event.messages,model_boundary:true})
   if(!Array.isArray(event.system))return
   const notices=[pending.get(event.sessionID),text(result)].filter((x):x is string=>typeof x==="string"&&!!x.trim())
   for(const notice of new Set(notices))event.system.push({type:"text",text:notice})
   pending.delete(event.sessionID)
  }))
  await ctx.session.hook("compaction",safe(async event=>{
   const result=await invoke(event.sessionID,"PreCompact",undefined,{messages:event.messages})
   if(!Array.isArray(event.system))return
   const sections=[pending.get(event.sessionID),result?.handoff,text(result)].filter((x):x is string=>typeof x==="string"&&!!x.trim())
   const handoff=[...new Set(sections)].join("\n\n")
   if(handoff)event.system.push({type:"text",text:handoff})
   pending.delete(event.sessionID)
  }))
  await ctx.tool.hook("execute.before",safe(async event=>{await invoke(event.sessionID,"PreToolUse",undefined,{tool_name:event.tool,tool_input:event.input})}))
  await ctx.tool.hook("execute.after",safe(async event=>{
   retain(event.sessionID,await invoke(event.sessionID,event.status==="error"?"ToolFailure":"PostToolUse",undefined,
    {tool_name:event.tool,tool_input:event.input,tool_response:event.result,error:event.error}))
  }))
  const events=(async()=>{
   try{
    for await(const event of ctx.event.subscribe({signal:controller.signal})){
     if(stopped)break
     const data=event.data??event.properties??{}
     const id=data.sessionID
     if(!id || !observed.has(id))continue
     let native:string|undefined
     if(event.type==="session.execution.succeeded")native="Stop"
     else if(event.type==="session.execution.failed")native="session.error"
     else if(event.type==="session.execution.interrupted")native="Interrupt"
     else if(event.type==="session.execution.started")native="PreToolUse"
     else if(event.type==="session.status"){
      if(data.status?.type==="idle" || data.status?.type==="retry")native="session.idle"
      else if(data.status?.type==="busy")native="PreToolUse"
     }else if(event.type==="permission.asked")native="PermissionRequest"
     else if(event.type==="permission.replied"&&data.reply!=="reject")native="permission.replied"
     else if(event.type==="session.idle"||event.type==="session.error")native=event.type
     else if(["session.compacted","session.compaction.ended"].includes(event.type))native="PostCompact"
     if(native)retain(id,await invoke(id,native))
    }
   }catch{/* No synthetic continuation or daemon. */}
  })()
  return async()=>{
   stopped=true;controller.abort();await events
   await Promise.allSettled(chains.values());observed.clear();pending.clear()
  }
 }
}
