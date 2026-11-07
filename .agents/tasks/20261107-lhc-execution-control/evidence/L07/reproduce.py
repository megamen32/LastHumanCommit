import json,os,sys,socket,subprocess,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[5]
RUN=ROOT/'.tmp/consumer-run'
TOOLS=RUN/'package/common/tools'
OUT=Path(__file__).resolve().parent
LOG=[];CALLS=[]; PHASE={'submitted':False,'complete':False,'mode':'normal'}
HOST=socket.gethostname()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  req=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
  method=req.get('method'); params=req.get('params',{}); name=params.get('name'); a=params.get('arguments',{})
  if method=='initialize':result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'L07-independent-fixture','version':'1'}}
  elif method=='notifications/initialized':self.send_response(202);self.end_headers();return
  elif method=='tools/list':result={'tools':[]}
  elif method=='tools/call':
   CALLS.append({'scenario':PHASE['mode'],'name':name,'arguments':a})
   if name=='session_info':
    sid=a.get('sessionId');running=PHASE['submitted'] and not PHASE['complete'] and sid=='child-executor'
    val={'session':{'id':sid,'sessionId':sid,'hostId':HOST,'harness':'codex','status':'running' if running else 'idle','model':'synthetic-no-LLM','cwd':str(RUN),'parentSessionId':'native-parent' if sid=='child-executor' else None,'meta':{'parentSessionId':'native-parent' if sid=='child-executor' else None,'nativeLastTurn':{'turnId':'L07-turn-1','status':'inProgress' if running else 'completed'}}}}
   elif name=='deliver':
    PHASE['submitted']=True
    val={'ok':True,'admitted':True,'delivery':'accepted','inputId':a.get('inputId'),'turnId':'L07-turn-1','sessionId':a.get('sessionId'),'harness':a.get('harness')}
   elif name=='resume_after':val={'error':'permission denied: synthetic continuation blocked','code':'permission_denied'}
   elif name=='resume_after_status':val={}
   else:val={}
   if name=='deliver' and PHASE['mode']=='unknown':
    CALLS[-1]['fixture_response']='HTTP connection dropped after synthetic admission effect'
    self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
   if name=='deliver' and PHASE['mode']=='quota':val={'ok':False,'admitted':False,'delivery':'not_attempted','reason':'quota exhausted: synthetic provider'}
   result={'content':[{'type':'text','text':json.dumps(val)}],'structuredContent':val}
   if name=='resume_after':result['isError']=True
   CALLS[-1]['fixture_response']=result
  else:result={}
  body=json.dumps({'jsonrpc':'2.0','id':req.get('id'),'result':result}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
SERVER=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=SERVER.serve_forever,daemon=True).start()
ENV=dict(os.environ,AGENT_HERDER_HTTP_URL='http://127.0.0.1:'+str(SERVER.server_port)+'/mcp',AGENT_HERDER_HTTP_TOKEN='fixture-token',XDG_STATE_HOME=str(RUN/'state'),LHC_PLAN_MIRROR_CONFIG=str(RUN/'absent-mirror.json'))
for k in ('CODEX_THREAD_ID','CLAUDE_SESSION_ID','OPENCODE_SESSION_ID','LHC_MCP_ACTOR_CONTEXT'):ENV.pop(k,None)
def cli(*args):
 argv=[sys.executable,str(TOOLS/'lhc_plan_json.py'),*map(str,args)]
 r=subprocess.run(argv,env=ENV,cwd=RUN,capture_output=True,text=True,timeout=15)
 LOG.append({'argv':argv,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(Path(str(args[0])).name,r.returncode);return r
def fresh(name):
 PHASE.update(submitted=False,complete=False,mode=name)
 plan=RUN/(name+'-plan')
 if plan.exists():
  import shutil;shutil.rmtree(plan)
 (plan/'leaves').mkdir(parents=True)
 (plan/'plan.json').write_text(json.dumps({'title':'Synthetic L07 '+name+' child executor acceptance','slots':2}))
 (plan/'leaves/L01.json').write_text(json.dumps({'id':'L01','label':'Child delivers synthetic artifact','status':'queued','depends_on':[]}))
 ref=lambda x:{'host_id':HOST,'harness':'codex','session_id':x}
 assignment={'schema_version':1,'attempt_id':'L07-'+name+'-1','executor_kind':'subagent','lead':ref('lead-controller'),'executor':ref('child-executor'),'parent':ref('native-parent'),'state':'assigned'}
 cli('assign-leaf',plan,'L01','--assignment',json.dumps(assignment));return plan,assignment
SNAPSHOTS={}
plan,a=fresh('normal')
cli('accept-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--result','premature unverified output')
cli('dispatch-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--message','Produce synthetic child output; disposable fixture only.')
SNAPSHOTS['running_blocked_continuation']=json.loads((plan/'leaves/L01.json').read_text())
cli('dispatch-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--message','Same task repeated after submission')
PHASE['complete']=True
cli('reconcile-leaf',plan,'L01','--attempt-id',a['attempt_id'])
SNAPSHOTS['terminal_before_acceptance']=json.loads((plan/'leaves/L01.json').read_text())
cli('accept-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--result','Verified synthetic artifact L07-child-output for exact L07-turn-1; disposable native observation only.')
cli('show',plan)
cli('build-plan',plan)
SNAPSHOTS['accepted']=json.loads((plan/'leaves/L01.json').read_text())
for mode in ('unknown','quota'):
 plan,a=fresh(mode)
 cli('dispatch-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--message','Synthetic '+mode+' delivery fixture')
 cli('dispatch-leaf',plan,'L01','--attempt-id',a['attempt_id'],'--message','Repeat after '+mode+' result')
 cli('reconcile-leaf',plan,'L01','--attempt-id',a['attempt_id'])
 cli('show',plan)
 cli('build-plan',plan)
 SNAPSHOTS[mode]=json.loads((plan/'leaves/L01.json').read_text())
# The public stdio server is a separate staged process, with no repo fallback.
rpcs=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'L07-consumer','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}]
for i,name in enumerate(('normal','unknown','quota'),3):
 rpcs.append({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':'show_plan','arguments':{'plan_dir':str(RUN/(name+'-plan'))}}})
argv=[sys.executable,str(TOOLS/'lhc_plan_mcp.py')]
r=subprocess.run(argv,input=''.join(json.dumps(x)+chr(10) for x in rpcs),env=ENV,cwd=RUN,capture_output=True,text=True,timeout=20)
(OUT/'stdio-surface.json').write_text(json.dumps({'argv':argv,'requests':rpcs,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
(OUT/'observations.json').write_text(json.dumps({'candidate':'5bf8733ba00f7e681823d883688402d113cf478a','processes':LOG,'fixture_calls':CALLS,'snapshots':SNAPSHOTS,'effect_counts':{n:sum(c['name']==n for c in CALLS) for n in ('deliver','resume_after','resume_after_status')}},indent=2))
import shutil
shutil.copytree(RUN/'normal-plan',OUT/'synthetic-renderer-plan',dirs_exist_ok=True)
print('SUMMARY',json.dumps({'processes':len(LOG),'calls':[c['name'] for c in CALLS],'states':{k:v['assignment']['state'] for k,v in SNAPSHOTS.items()},'stdio_exit':r.returncode}))
SERVER.shutdown()
