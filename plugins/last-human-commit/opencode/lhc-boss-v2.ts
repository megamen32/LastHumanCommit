/**
 * LHC Boss: native OpenCode 2 plugin, using the parent's provider and auth.
 * No OpenAI/Codex calls, review gate, or independent agent runtime.
 */
import { readFileSync, existsSync, mkdtempSync, writeFileSync, rmSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import { join } from "node:path"

const PERIOD = 30 * 60_000
const TIMEOUT = 120_000
const BOSS_TITLE = "LHC Boss"
type AnyRecord = Record<string,any>
type State = { generation:number; elapsed:number; started:number|null; reviewed:number; busy:boolean }
const sessionId = (event:AnyRecord):string =>
  String(event?.data?.sessionID ?? event?.data?.sessionId ?? event?.data?.session?.id ??
    event?.properties?.sessionID ?? event?.properties?.sessionId ?? "")
const role = (message:AnyRecord):string =>
  String(message?.info?.role ?? message?.role ?? "")
const asText = (message:AnyRecord):string => (Array.isArray(message.parts) ? message.parts : [])
  .map((part:AnyRecord) => {
    if (part.type === "text") return String(part.text ?? "")
    if (part.type === "tool") return "TOOL "+String(part.tool??"")+" "+
      JSON.stringify({input:part.state?.input,output:part.state?.output,error:part.state?.error})
    return ""
  }).filter(Boolean).join("\n")
const assistantText = (messages:AnyRecord[]):string => {
  for (let i=messages.length-1;i>=0;i--) {
    if (role(messages[i]) !== "assistant") continue
    const text=asText(messages[i]).trim()
    if (text) return text
  }
  return ""
}
// All user-visible prose from the Boss's independent session, not merely the
// final message. Reasoning and tool I/O do not masquerade as his words.
export function bossSpokenText(messages:AnyRecord[]):string {
  return messages.filter(m=>role(m)==="assistant").flatMap(m=>
    (Array.isArray(m.parts)?m.parts:[])
      .filter((part:AnyRecord)=>part.type==="text" && part.ignored!==true && part.synthetic!==true)
      .map((part:AnyRecord)=>String(part.text??""))
  ).filter(text=>text.trim()).join("\n\n")
}
function currentModel(session:AnyRecord,messages:AnyRecord[]) {
  const values=[session.model,...messages.slice().reverse().map(m=>m.info?.model??m.model)]
  for (const m of values)
    if (typeof m?.providerID==="string" && typeof m?.id==="string")
      return {providerID:m.providerID,id:m.id,...(m.variant?{variant:m.variant}:{})}
}
function loadBoss():string {
  const file=join(homedir(),".local/state/last-human-commit/opencode.json")
  try {
    const state=JSON.parse(readFileSync(file,"utf8"))
    if (typeof state.packageRoot !== "string") return ""
    return readFileSync(join(state.packageRoot,"common/agents/Boss.md"),"utf8")
  } catch { return "" }
}
function activeMs(state:State):number {
  return state.elapsed+(state.started===null?0:Math.max(0,Date.now()-state.started))
}

export default {
  id:"last-human-commit-boss",
  async setup(ctx:any) {
    const instructions=loadBoss()
    if (!instructions) {
      console.warn("LHC Boss: role file not installed; skipped")
      return ()=>{}
    }
    const states=new Map<string,State>(), children=new Set<string>()
    const controller=new AbortController(), regs:any[]=[]
    function current(id:string):State {
      let result=states.get(id)
      if (!result) {
        result={generation:0,elapsed:0,started:null,reviewed:0,busy:false}
        states.set(id,result)
      }
      return result
    }
    function start(id:string) {
      if (children.has(id)) return
      const state=current(id)
      if (state.started===null)state.started=Date.now()
    }
    function finish(id:string) {
      const state=states.get(id)
      if (!state || state.started===null)return
      state.elapsed=Math.max(state.elapsed,activeMs(state))
      state.started=null
    }
    regs.push(await ctx.session.hook("prompt",(event:any)=>{
      const id=String(event?.sessionID??"")
      if (!id || children.has(id))return
      const state=current(id)
      state.generation++
      state.elapsed=0
      state.reviewed=0
      state.started=Date.now()
    }))
    regs.push(await ctx.session.hook("context",(event:any)=>{
      if (!children.has(String(event?.sessionID??"")))return
      event.system.push({type:"text",text:instructions})
      for (const tool of Object.keys(event.tools??{}))
        if (!["read","grep","glob","list"].includes(tool.toLowerCase())) delete event.tools[tool]
    }))
    async function runBoss(parentID:string,state:State) {
      if (state.busy || state.started===null)return
      state.busy=true
      state.reviewed=activeMs(state)
      const generation=state.generation
      let temporary="", child=""
      try {
        const session=await ctx.session.get({sessionID:parentID})
        if (session.parentID || String(session.title??"").startsWith(BOSS_TITLE))return
        const messages:Array<AnyRecord>=Array.from(await ctx.session.context({sessionID:parentID}))
        const users=messages.filter(m=>role(m)==="user" && m.info?.synthetic!==true)
        if (!users.length)return
        const last=assistantText(messages)
        const model=currentModel(session,messages)
        if (!last || !model)return
        temporary=mkdtempSync(join(tmpdir(),"lhc-boss-"))
        const file=join(temporary,"session.json")
        writeFileSync(file,JSON.stringify({sessionID:parentID,historySource:"OpenCode session.context",historyComplete:false,messages},null,2),{mode:0o600})
        const prompt=[
          "Исходная задача:\n"+asText(users[0]).slice(0,10000),
          "Последняя прямая коррекция:\n"+asText(users[users.length-1]).slice(0,10000),
          "Последний видимый ответ:\n"+last.slice(-12000),
          "Доступный журнал сессии файлом: "+file,
          "Если историю до compaction не видно, не выдумывай её.",
          "Это разговор с исполнителем. Скажи ему своими словами всё, что считаешь важным, без формата или ограничения объёма."
        ].join("\n\n")
        const created=await ctx.session.create({parentID,title:BOSS_TITLE+" / "+parentID.slice(-8)})
        child=String(created.id??created.sessionID??"")
        if (!child)throw new Error("No child session ID")
        children.add(child)
        await ctx.session.switchModel({sessionID:child,model})
        await ctx.session.prompt({sessionID:child,text:prompt})
        let timer:any
        try {
          await Promise.race([
            ctx.session.wait({sessionID:child}),
            new Promise((_resolve,reject)=>{timer=setTimeout(()=>reject(new Error("Boss timeout")),TIMEOUT)})
          ])
        } finally {clearTimeout(timer)}
        const answer=Array.from(await ctx.session.context({sessionID:child}))
        const advice=bossSpokenText(answer)
        if (!advice.trim() || state.generation!==generation || state.started===null || controller.signal.aborted)return
        // Inject the Boss's whole answer, without parsing, rewriting, truncation,
        // or a mandatory machine-readable response shape.
        await ctx.session.synthetic({
          sessionID:parentID,
          delivery:"steer",
          resume:false,
          text:advice
        })
      } catch (error) {
        console.warn("LHC Boss skipped for "+parentID+": "+String(error))
        if (child)await ctx.session.interrupt({sessionID:child,resume:false}).catch(()=>{})
      } finally {
        if (temporary)rmSync(temporary,{recursive:true,force:true})
        state.busy=false
      }
    }
    const interval=setInterval(()=>{
      for (const [id,state] of states)
        if (state.started!==null && !state.busy && activeMs(state)-state.reviewed>=PERIOD)
          void runBoss(id,state)
    },60_000)
    void (async()=>{
      try {
        for await (const event of ctx.event.subscribe({
          types:["session.execution.started","session.execution.succeeded","session.execution.failed",
            "session.execution.interrupted","session.step.started","session.idle","session.deleted"],
          signal:controller.signal
        })) {
          const id=sessionId(event)
          if (!id || children.has(id))continue
          if (["session.execution.started","session.step.started"].includes(event.type))start(id)
          if (["session.execution.succeeded","session.execution.failed","session.execution.interrupted","session.idle"].includes(event.type))finish(id)
          if (event.type==="session.deleted")states.delete(id)
        }
      } catch (error) {
        if (!controller.signal.aborted)console.warn("LHC Boss event stream unavailable: "+String(error))
      }
    })()
    return async()=>{
      controller.abort()
      clearInterval(interval)
      for (const reg of regs)await reg.dispose()
    }
  }
}
