import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
TOOLS=Path(os.environ.get('REVIEW_TOOLS') or ROOT/'assembled-slices/src/common/tools')
sys.path.insert(0,str(TOOLS))
import lhc_plan_json as plans
import lhc_plan_control as control
import lhc_outcome as outcome_module
import lhc_time_guard as guard
import lhc_plan_publish as publication
import lhc_plan_catalog as catalog


def old_outcome(root):
    return {'id':'goal-A','task_class':'research','contract_confirmed':True,
        'original_goal':'Explain configuration A','latest_correction':'Explain configuration A',
        'owner':{'harness':'codex','session_id':'fixture-lead'},'cwd':str(root),
        'canary':{'scenario':'Read A','target':'project:A','expected':'Explain A'},
        'stages':{key:{'status':'complete' if key=='technical' else 'not-applicable'}
        for key in ('technical','deploy','consumer','publication','integration')}}


def test_activate_does_not_accept_old_goal_for_new_work(tmp_path):
    subprocess.run(['git','init','--quiet',str(tmp_path)],check=True)
    (tmp_path/'.agents').mkdir()
    plan=tmp_path/'.agents/tasks/new-goal-B'
    (plan/'leaves').mkdir(parents=True)
    (plan/'plan.json').write_text(json.dumps({'title':'Goal B','goal':'Build application B','slots':1}))
    (plan/'leaves/L1.json').write_text(json.dumps({'id':'L1','status':'queued','label':'Implement B'}))
    outcome=old_outcome(tmp_path)
    state={'business':{'outcome':outcome}}
    assert outcome_module.verdict(outcome,state)=='complete'
    path=guard.learning_path(tmp_path,'codex','fixture-lead')
    assert path.is_relative_to(tmp_path)
    guard.write_state(path,state)
    result=subprocess.run([sys.executable,str(TOOLS/'lhc_plan_json.py'),'activate',str(plan),'L1',
        '--session','fixture-lead','--harness','codex'],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    payload=json.loads(result.stdout)
    print('actual CLI activate:',json.dumps(payload,ensure_ascii=False))
    assert payload['goal_binding']['goal_status']!='accepted','activate accepted goal B before its first implementation step'


def test_changed_business_contract_rejects_prior_acceptance(tmp_path):
    first={'goal':'Deliver product','business_result':'Handle one request',
        'acceptance_scenarios':['one request succeeds']}
    outcome=old_outcome(tmp_path)
    outcome['finish_verdict']='complete'
    outcome['plan_binding']=control.binding(first,outcome,tmp_path,accepted=True)
    assert control.evaluate(first,[],outcome,plan_dir=tmp_path)['goal_status']=='accepted'
    revised={**first,'business_result':'Handle every tenant without data loss',
        'acceptance_scenarios':['tenant isolation and failover succeed']}
    view=control.evaluate(revised,[],outcome,plan_dir=tmp_path)
    print('changed acceptance contract:',view['goal_status'])
    assert view['goal_status']!='accepted','new business acceptance uses old evidence without rebinding'


def test_public_roundtrip_preserves_safe_goal_status():
    from datetime import datetime,timezone
    now=datetime(2026,11,7,tzinfo=timezone.utc)
    projection={'goal_status':'accepted','fingerprint':'source-scope-fingerprint',
        'source':{'kind':'native_outcome','session_id':'fixture-lead','outcome_id':'goal-A',
            'source_fingerprint':'source-evidence-fingerprint'}}
    doc={'schema_version':2,'title':'Accepted fixture','goal':'Original goal A',
        'goal_control':projection,'tasks':[{'id':'L1','status':'done'}]}
    before=catalog.summarize({'snapshot':{'project':'test','name':'fixture','document':doc,
        'last_file_event':now.isoformat()}},now)
    public=publication.public_document(doc)
    after=catalog.summarize({'snapshot':{'project':'test','name':'fixture','document':public,
        'last_file_event':now.isoformat()}},now)
    print('public roundtrip:',before['state'],before['goal_status'],'->',after['state'],after['goal_status'])
    assert after['goal_status']==before['goal_status'],'public_document strips newly added goal control'
