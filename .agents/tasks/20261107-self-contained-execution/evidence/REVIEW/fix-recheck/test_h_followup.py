"""Independent local fixture checks; these are not native consumer acceptance."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parent
TOOLS=ROOT/'H-b7510c3/src/common/tools'
sys.path.insert(0,str(TOOLS))
import lhc_plan_json as plans
import lhc_plan_control as control
import lhc_outcome as outcomes
import lhc_time_guard as guard


def stamp(): return datetime.now(timezone.utc).isoformat()

def cli(tool,*args,ok=True):
    result=subprocess.run([sys.executable,str(TOOLS/(tool+'.py')),*map(str,args)],capture_output=True,text=True,timeout=20)
    assert (result.returncode==0)==ok,result.stderr
    return json.loads(result.stdout) if ok else result.stderr

@pytest.fixture
def case(tmp_path,monkeypatch):
    subprocess.run(['git','init','--quiet',str(tmp_path)],check=True)
    home=tmp_path/'fixture-native-format'
    monkeypatch.setenv('CODEX_HOME',str(home))
    journal=home/'sessions/fixture-lead.jsonl'; journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({'type':'session_meta','payload':{'id':'fixture-lead','cwd':str(tmp_path),'timestamp':stamp()}})+'\n')
    plan=tmp_path/'.agents/tasks/independent-B'
    (plan/'leaves').mkdir(parents=True)
    metadata={'goal':'Correct new CLI B so it prints thirteen','business_result':'B produces 13',
        'acceptance_scenarios':['Run B and observe 13'],'slots':1}
    (plan/'plan.json').write_text(json.dumps(metadata))
    (plan/'leaves/L1.json').write_text(json.dumps({'id':'L1','label':'Repair new B','status':'queued'}))
    old={'id':'fixture-A','task_class':'quickfix','contract_confirmed':True,'original_goal':'Repair old CLI A',
        'latest_correction':'Repair old CLI A','owner':{'harness':'codex','session_id':'fixture-lead'},
        'cwd':str(tmp_path),'native_source':str(journal),'started_at':(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat(),
        'canary':{'scenario':'Old A','target':'python3 old.py','expected':'41','status':'complete'},
        'owned_paths':[],'sources':[],'coverage':[],
        'stages':{key:{'status':'complete' if key in {'technical','consumer'} else 'not-applicable'} for key in outcomes.STAGES}}
    assert outcomes.verdict(old,{'business':{'outcome':old}})=='complete'
    path=guard.learning_path(tmp_path,'codex','fixture-lead'); assert path.is_relative_to(tmp_path)
    guard.write_state(path,{'business':{'outcome':copy.deepcopy(old)}})
    return tmp_path,plan,path,old


def activate(plan):
    return cli('lhc_plan_json','activate',plan,'L1','--session','fixture-lead','--harness','codex')


def write_real_local_review(root,confirmed):
    """Synthetic native-format identity, actual local test/canary outputs, no RPC."""
    rows=[{'type':'session_meta','timestamp':stamp(),'payload':{'id':'fixture-reviewer','cwd':str(root),'timestamp':stamp()}},
        {'type':'response_item','timestamp':stamp(),'payload':{'type':'message','role':'user','content':[{'text':
            'Independent review of outcome '+confirmed['id']+'. Original scope: '+confirmed['original_goal']+
            '. Current confirmed B contract: '+json.dumps(confirmed['canary'])}]}}]
    report={'outcome_id':confirmed['id'],'revision':confirmed['revision'],'target':confirmed['canary']['target'],
        'scenario':confirmed['canary']['scenario'],'expected':confirmed['canary']['expected'],
        'assignment_verdict':'complete','product_verdict':'pass','comparison':'Actual B printed 13, matching 6 + 7.','coverage':{},'stages':{}}
    for stage,command in [('technical','python3 -m unittest discover -q'),('consumer','python3 total.py')]:
        run=subprocess.run(command.split(),cwd=root,capture_output=True,text=True,timeout=10)
        assert run.returncode==0,run.stderr
        output=run.stdout+run.stderr
        if stage=='consumer': assert output.strip()=='13'
        call='independent-'+stage
        rows.extend([{'type':'response_item','timestamp':stamp(),'payload':{'type':'function_call','name':'exec_command',
            'call_id':call,'arguments':json.dumps({'cmd':command,'workdir':str(root)})}},
            {'type':'response_item','timestamp':stamp(),'payload':{'type':'function_call_output','call_id':call,'output':output}}])
        report['stages'][stage]={'evidence_calls':[call],'observed':output.strip(),
            'expected':'13' if stage=='consumer' else 'Successful technical readback for this scope'}
    rows.append({'type':'response_item','timestamp':stamp(),'payload':{'type':'message','role':'assistant','phase':'final',
        'content':[{'text':'Compared actual B CLI output with the current contract.\nLHC_OUTCOME_REVIEW '+json.dumps(report)}]}})
    native=root/'fixture-native-format/sessions/fixture-reviewer.jsonl'
    native.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    export=root/'review-export.jsonl';export.write_bytes(native.read_bytes())
    manifest=root/'review-manifest.json'
    manifest.write_text(json.dumps({'format':'agent-herder-transcript-manifest-v1','target':{'path':str(export),
        'harness':'codex','complete':True,'sessionId':'fixture-reviewer','source':{'kind':'native-file','location':str(native)}}}))
    return manifest


def test_positive_B_contract_actual_work_review_and_repeat_activation(case):
    root,plan,path,old=case
    assert activate(plan)['goal_binding']['goal_status']!='accepted'
    args=['--cwd',root,'--runtime','codex','--session-id','fixture-lead']
    confirmed=cli('lhc_outcome',*args,'contract','--scenario','New B computes six plus seven',
        '--target','python3 total.py','--expected','13','--owned-path','total.py')
    assert confirmed['stages']['technical']['status']=='pending'
    assert confirmed['stages']['consumer']['status']=='pending'
    assert control.resolve_control(plan)['goal_status']=='unaccepted'
    (root/'total.py').write_text('print(6 + 7)\n')
    (root/'test_total.py').write_text('import unittest, subprocess, sys\nclass B(unittest.TestCase):\n def test_B(self): self.assertEqual(subprocess.check_output([sys.executable,"total.py"]).strip(),b"13")\n')
    # Refresh the ordinary contract's owned-byte revision after implementation.
    confirmed=cli('lhc_outcome',*args,'contract','--scenario','New B computes six plus seven',
        '--target','python3 total.py','--expected','13','--owned-path','total.py')
    reviewed=cli('lhc_outcome',*args,'review','--manifest',write_real_local_review(root,confirmed))
    assert reviewed['finish_verdict']=='complete',reviewed
    assert control.resolve_control(plan)['goal_status']=='accepted'
    before=copy.deepcopy(reviewed['plan_binding']); history=copy.deepcopy(reviewed['plan_binding_history'])
    assert activate(plan)['goal_binding']['goal_status']=='accepted'
    saved=guard.load_state(path)['business']['outcome']
    assert saved['plan_binding']==before and saved['plan_binding_history']==history
    assert any(row['outcome']['canary']==old['canary'] for row in history)
    metadata=json.loads((plan/'plan.json').read_text())
    (plan/'plan.json').write_text(json.dumps({**metadata,'current_progress':'B reviewed','slots':4,'updated_at':stamp()}))
    assert activate(plan)['goal_binding']['goal_status']=='accepted'
    assert guard.load_state(path)['business']['outcome']['plan_binding']==before
    print('B: unaccepted -> contract pending -> actual local work/review -> accepted -> repeat/progress accepted; old A retained')

@pytest.mark.parametrize('field,value',[
    ('business_result','New user result'),('business_results',['One','Two']),
    ('acceptance_scenarios',['New acceptance']),('acceptance_scenario','New alias acceptance'),
    ('acceptance','New legacy acceptance'),('scope',['new/file']),('constraints',['must retain data'])])
def test_every_scope_field_invalidates(field,value):
    before={'goal':'Same summary','business_result':'Original user result','acceptance_scenarios':['Original acceptance']}
    assert control.plan_scope(before)!=control.plan_scope({**before,field:value})


def test_singular_alias_dedup_and_progress_stability():
    base={'goal':'B','acceptance_scenarios':['Run B','Reload B']}
    alias={'goal':'B','acceptance_scenario':'Run B','acceptance_scenarios':['Run B','Reload B']}
    assert control.plan_scope(base)==control.plan_scope(alias)
    assert control.plan_scope({'acceptance_scenario':'Run B'})==control.plan_scope({'acceptance_scenarios':['Run B']})
    for field,value in [('current_progress','New note'),('updated_at',stamp()),('slots',8),('estimate_policy',{'leaf_cap_minutes':30})]:
        assert control.plan_scope(base)==control.plan_scope({**base,field:value})

@pytest.mark.parametrize('hold',['HumanStop','permission_declined','codex_quota_guard'])
def test_binding_preserves_native_hold(case,hold):
    root,plan,path,old=case
    state=guard.load_state(path);state['native_entry']={'finish_hold':hold};guard.write_state(path,state)
    assert activate(plan)['goal_binding']['goal_status']!='accepted'
    saved=guard.load_state(path)
    assert saved['native_entry']['finish_hold']==hold
    assert outcomes.verdict(saved['business']['outcome'],saved)=='blocked'


def test_missing_status_is_read_only_and_does_not_bootstrap(tmp_path,monkeypatch):
    subprocess.run(['git','init','--quiet',str(tmp_path)],check=True)
    monkeypatch.setenv('CODEX_HOME',str(tmp_path/'missing-native-format'))
    before={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    error=cli('lhc_outcome','--cwd',tmp_path,'--runtime','codex','--session-id','fresh-fixture','status',ok=False)
    assert 'no LHC session state' in error
    after={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert after==before,'readonly status created or changed fixture state'
    print('missing outcome status: explicit error, no files created or changed; bootstrap remains pending')
