from pathlib import Path
import sys, json, os
sys.path.insert(0,str(Path('plugins/last-human-commit/native/codex/tools').resolve()))
import lhc_plan_json as pj
from lhc_readiness import evaluate
base=Path('.agents/tasks/20261107-lhc-execution-control/evidence/L05R/green-native-package');base.mkdir(parents=True,exist_ok=True)
os.environ['XDG_STATE_HOME']=str((base/'state').resolve());os.environ['LHC_PLAN_MIRROR_CONFIG']=str((base/'absent').resolve());os.environ.pop('CODEX_THREAD_ID',None)
results=[]
for case,rows,target in [('inherited-unfinished',[{'id':'P','status':'queued'},{'id':'M','kind':'milestone','status':'queued','depends_on':['P']},{'id':'C','status':'queued','parent':'M'}],'C'),('milestone-completed',[{'id':'M','kind':'milestone','status':'queued'},{'id':'C','status':'done','parent':'M'},{'id':'N','status':'queued','depends_on':['M']}],'N')]:
 plan=base/case;(plan/'leaves').mkdir(parents=True,exist_ok=True);(plan/'plan.json').write_text(json.dumps({'title':case,'slots':4}))
 for row in rows:(plan/'leaves'/(row['id']+'.json')).write_text(json.dumps({'label':row['id'],**row}))
 lead={'host_id':'test-host','harness':'codex','session_id':'lead'};a={'schema_version':1,'attempt_id':case,'executor_kind':'session','lead':lead,'executor':{**lead,'session_id':'worker'},'state':'assigned'}
 pj.assign_leaf(plan,target,a)
 pj.transition_leaf(plan,target,case,'assigned',receipt={'observed_runtime':{'state':'idle','source':'native_verified','observed_at':pj.assignments.now()}})
 raw=pj.collect_leaves(plan);expanded,_=pj.split_milestones(pj.collect_leaves(plan))
 row={'case':case,'raw':evaluate(raw,4)['by_id'][target],'expanded':evaluate(expanded,4)['by_id'][target]}
 try:
  result=pj.admit_leaf(plan,target,case,{'dispatch':{'request_id':case,'status':'dispatching'}});row['admission_result']=result['assignment']['state']
 except Exception as e:row['admission_error']=str(e)
 results.append(row)
print(json.dumps(results,indent=2));(base/'milestone-repro.json').write_text(json.dumps(results,indent=2)+'\n')
