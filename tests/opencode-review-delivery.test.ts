import {expect,test} from "bun:test"
import {mkdtemp,readdir,readFile,rm} from "node:fs/promises"
import {join} from "node:path"
import plugin from "../plugins/last-human-commit/opencode/lhc-v2"

async function scenario(fn:(hooks:Map<string,Function>,root:string)=>Promise<void>){
 const root=await mkdtemp(join(import.meta.dir,"../.tmp/opencode-delivery-"))
 const init=Bun.spawnSync(["git","init","-q",root]);expect(init.exitCode).toBe(0)
 const hooks=new Map<string,Function>();let notify:Function|undefined,stopped=false
 const ctx:any={location:{directory:"/irrelevant-home"},session:{
  get:async()=>({data:{location:{directory:root}}}),
  hook:async(k:string,v:Function)=>{hooks.set("session:"+k,v)}
 },tool:{hook:async(k:string,v:Function)=>{hooks.set("tool:"+k,v)}},event:{
  subscribe:({signal}:any)=>({async *[Symbol.asyncIterator](){
    signal.addEventListener("abort",()=>{stopped=true;notify?.()},{once:true})
    while(!stopped)await new Promise(r=>notify=r)
  }})
 }}
 const stop=await plugin.setup(ctx)
 try{await fn(hooks,root)}finally{await stop();await rm(root,{recursive:true,force:true})}
}
function system(e:any){return (e.system??[]).map((x:any)=>String(x.text??"")).join("\n")}

test("ordinary native OpenCode prompt receives business-first and no redundant review receipts",async()=>{
 await scenario(async hooks=>{
  const id="ses_open_lhc_delivery"
  const prompt={sessionID:id,prompt:{text:"Исправь причину ошибки, затем проверь реально установленный результат."}}
  await hooks.get("session:prompt")!(prompt)
  expect(prompt.prompt.text).toContain("Исправь причину")
  const event={sessionID:id,system:[],messages:[]}
  await hooks.get("session:context")!(event)
  const v=system(event)
  for(const term of ["раньше", "после", "RED", "GREEN", "80%", "Zero Knowledge", "Ошибка в receipt", "ближайший рабочий", "ревью"]){
   expect(v.toLowerCase()).toContain(term.toLowerCase())
  }
  expect(v).not.toContain("releases/1.4.4")
 })
})

test("native OpenCode compaction preserves original goal and late correction even without task card",async()=>{
 await scenario(async(hooks,root)=>{
  const id="ses_open_lhc_compact"
  const original="Клиент должен увидеть исправленный отчёт, не цепочку SHA квитанций"
  const correction="Последняя поправка: сохрани импорт CSV; не трогай базу продакшена"
  await hooks.get("session:prompt")!({sessionID:id,prompt:{text:original}})
  await hooks.get("session:prompt")!({sessionID:id,prompt:{text:correction}})
  const compact={sessionID:id,system:[]}
  await hooks.get("session:compaction")!(compact)
  const s=system(compact)
  expect(s).toContain(original)
  expect(s).toContain(correction)
  expect(s).toContain("REVIEW_TO_DELIVERY")
  const info={sessionID:id,system:[],messages:[]}
  await hooks.get("session:context")!(info)
  expect(system(info)).toContain(original)
  expect(system(info)).toContain(correction)
  const dir=join(root,".agents/shared-session/learning")
  const state=JSON.parse(await readFile(join(dir,(await readdir(dir)).find(x=>x.endsWith(".json"))!),"utf8"))
  expect(state.business.original_prompt).toBe(original)
  expect(state.business.latest_prompt).toBe(correction)
 })
})

test("resumed OpenCode thread without a fresh prompt still bootstraps the installed contract",async()=>{
 await scenario(async hooks=>{
  const event={sessionID:"ses_open_old_thread",system:[],messages:[]}
  await hooks.get("session:context")!(event)
  const v=system(event)
  expect(v).toContain("Ошибка в receipt")
  expect(v).toContain("REVIEW_TO_DELIVERY.md")
 })
})
