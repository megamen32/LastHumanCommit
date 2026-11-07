import json,os,sys,subprocess,tempfile,shutil,socket,threading,hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).parent
CALLS=[]; OBS=[];phase={'submitted':False,'complete':False}
host=socket.gethostname()
def rpc_result(name,a):
 if name=='session_info':
  terminal=phase['complete'];busy=phase['submitted'] and not terminal
  return {'session':{'id':a['sessionId'],'harness':a['harness'],'hostId':host,'status':'running' if busy else 'idle','model':'fixture-model','cwd':str(run),'meta':{'nativeLastTurn':{'turnId':'turn-consumer-1','status':'inProgress' if busy else 'completed'}}}}
 if name=='deliver':
  phase['submitted']=True
  return {'ok':True,'admitted':True,'delivery':'accepted','inputId':a['inputId'],'turnId':'turn-consumer-1','sessionId':a['sessionId'],'harness':a['harness']}
 if name=='resume_after':
  if a.get('action')=='wait':
   owner=a['owner'];dep=a['dependencies'][0]
   ownerkey=json.dumps([owner['harness'],owner['sessionId']],separators=(',',':'))
   waitid='wait_'+hashlib.sha256(json.dumps([ownerkey,a['requestId']],separators=(',',':')).encode()).hexdigest()[:32]
   phase['wait']={'id':waitid,'owner':owner,'dependencies':a['dependencies'],'dependencyTurns':{json.dumps([dep['harness'],dep['sessionId']],separators=(',',':')):'turn-consumer-1'},'scheduledAt':'2026-11-07T16:00:00Z','reason':None}
  return {'wait':dict(phase['wait'],state='resumed' if phase['complete'] else 'waiting')}
 return {'ok':True,'sessions':[]}
class HTTP(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  method=req.get('method');p=req.get('params',{})
  if method=='initialize':result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'consumer-own-fixture','version':'1'}}
  elif method=='tools/call':
   CALLS.append({'name':p['name'],'arguments':p.get('arguments',{})})
   value=rpc_result(p['name'],p.get('arguments',{}))
   result={'content':[{'type':'text','text':json.dumps(value)}],'structuredContent':value}
  else:result={}
  payload=json.dumps({'jsonrpc':'2.0','id':req.get('id'),'result':result}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
def cli(*args):
 cmd=[sys.executable,str(tools/'lhc_plan_json.py'),*map(str,args)]
 cp=subprocess.run(cmd,cwd=run,env=env,capture_output=True,text=True,timeout=20)
 row={'argv':cmd,'code':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr};OBS.append(row);print(args[0],cp.returncode,flush=True);return row
with tempfile.TemporaryDirectory(prefix='lhc-L06-') as temp:
 run=Path(temp);pkg=run/'package';shutil.copytree(ROOT/'plugins/last-human-commit/native/codex',pkg);tools=pkg/'common/tools'
 env=dict(os.environ,XDG_STATE_HOME=str(run/'state'),LHC_PLAN_MIRROR_CONFIG=str(run/'absent.json'))
 for k in ['CODEX_THREAD_ID','CLAUDE_SESSION_ID','OPENCODE_SESSION_ID','LHC_MCP_ACTOR_CONTEXT','PYTHONPATH']:env.pop(k,None)
 server=ThreadingHTTPServer(('127.0.0.1',0),HTTP);threading.Thread(target=server.serve_forever,daemon=True).start()
 env.update(AGENT_HERDER_HTTP_URL='http://127.0.0.1:'+str(server.server_port)+'/mcp',AGENT_HERDER_HTTP_TOKEN='fixture-token')
 plan=run/'plan';(plan/'leaves').mkdir(parents=True);(plan/'plan.json').write_text(json.dumps({'title':'Consumer distinct session journey','slots':1}))
 for id,deps in [('L01',[]),('L02',['L01'])]:(plan/'leaves'/f'{id}.json').write_text(json.dumps({'id':id,'label':'Fixture work '+id,'status':'queued','depends_on':deps}))
 ref=lambda id:{'host_id':host,'harness':'codex','session_id':id}
 assignment={'schema_version':1,'attempt_id':'consumer-L06-1','executor_kind':'session','lead':ref('lead'),'executor':ref('worker'),'parent':None,'state':'assigned'}
 cli('assign-leaf',plan,'L01','--assignment',json.dumps(assignment),'--actor',json.dumps(ref('author')))
 cli('dispatch-leaf',plan,'L01','--attempt-id','consumer-L06-1','--message','Disposable fixture only. Prepare result for next dependent task.')
 cli('dispatch-leaf',plan,'L01','--attempt-id','consumer-L06-1','--message','Disposable fixture only. Prepare result for next dependent task.')
 phase['complete']=True
 cli('reconcile-leaf',plan,'L01','--attempt-id','consumer-L06-1')
 assignment2=dict(assignment,attempt_id='consumer-L06-2',executor=ref('worker2'))
 cli('assign-leaf',plan,'L02','--assignment',json.dumps(assignment2))
 cli('dispatch-leaf',plan,'L02','--attempt-id','consumer-L06-2','--message','Run dependent fixture task only after acceptance.')
 cli('accept-leaf',plan,'L01','--attempt-id','consumer-L06-1','--result','Isolated fixture result inspected; dependent task may proceed.')
 cli('show',plan)
 phase.update(submitted=False,complete=False)
 cli('dispatch-leaf',plan,'L02','--attempt-id','consumer-L06-2','--message','Run dependent fixture task only after acceptance.')
 proc=subprocess.Popen([sys.executable,str(tools/'lhc_plan_mcp.py')],cwd=run,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 def mcp(method,params=None,id=1):
  req={'jsonrpc':'2.0','method':method}
  if params is not None:req['params']=params
  if id is not None:req['id']=id
  proc.stdin.write(json.dumps(req)+'\n');proc.stdin.flush()
  if id is None:return None
  resp=json.loads(proc.stdout.readline());OBS.append({'rpc':req,'response':resp});return resp
 mcp('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'fresh-consumer','version':'1'}})
 mcp('notifications/initialized',id=None)
 listed=mcp('tools/list',{},2)
 (OUT/'mcp-tools-list-final.json').write_text(json.dumps(listed,indent=2))
 print('MCP_TOOLS',[x['name'] for x in listed['result']['tools']])
 mcp('tools/call',{'name':'show_plan','arguments':{'plan_dir':str(plan)}},3)
 proc.terminate();proc.wait(timeout=5)
 saved={p.name:json.loads(p.read_text()) for p in (plan/'leaves').glob('*.json')}
 server.shutdown()
 (OUT/'observations-final.json').write_text(json.dumps({'commands':OBS,'fixture_calls':CALLS,'leaves':saved},ensure_ascii=False,indent=2))
 print('COUNTS',len(OBS),[x['name'] for x in CALLS])
 command_rows=[x for x in OBS if 'argv' in x]
 parsed=lambda row:json.JSONDecoder().raw_decode(row['stdout'])[0]
 dispatched=[x for x in command_rows if x['argv'][2]=='dispatch-leaf' and x['code']==0]
 reconciled=next(x for x in command_rows if x['argv'][2]=='reconcile-leaf')
 refusal=next(x for x in command_rows if x['argv'][2]=='dispatch-leaf' and x['code']!=0)
 text=OBS[-1]['response']['result']['structuredContent']['stdout']
 checks={
  'author_distinct_from_lead_and_worker':saved['L01.json']['assignment']['events'][0]['actor']['session_id']=='author',
  'exact_turn_running':parsed(dispatched[0])['state']=='running',
  'wake_captured_admitted_turn':parsed(dispatched[0])['wake']['captured_turn_id']=='turn-consumer-1',
  'wake_resumed_on_reconcile':parsed(reconciled)['wake']['state']=='resumed',
  'completion_requires_acceptance':parsed(reconciled)['state']=='result_ready' and saved['L01.json']['status']=='done',
  'dependency_refused_before_acceptance':'dependencies_unmet' in refusal['stderr'],
  'duplicate_dispatch_not_resent':len([x for x in CALLS if x['name']=='deliver' and x['arguments']['sessionId']=='worker'])==1,
  'dependent_dispatch_after_acceptance':parsed(dispatched[-1])['state']=='running' and saved['L02.json']['assignment']['state']=='running',
  'active_assignment_not_offered_as_next':'Next: L02' not in text,
  'running_runtime_visible':'runtime' in text.lower() and 'running' in text.lower(),
  'continuation_state_visible':'wake' in text.lower() and 'waiting' in text.lower(),
  'admission_visible':'admission' in text.lower() or 'dispatchable' in text.lower(),
 }
 summary={'verdict':'PASS' if all(checks.values()) else 'FAIL','candidate':'d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487','checks':checks,'mcp_show_after_L02_dispatch':text,'fixture_only':True}
 (OUT/'acceptance-final.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 print(json.dumps(summary,ensure_ascii=False))
 if not all(checks.values()):sys.exit(1)
