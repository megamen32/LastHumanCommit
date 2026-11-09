"""Real local mirror HTTP and package bytes; no live service or real credentials."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request

ROOT=Path(__file__).resolve().parent
SNAPSHOT=ROOT/'I-2bd0f54'
TOOLS=SNAPSHOT/'src/common/tools'
sys.path.insert(0,str(TOOLS))
import lhc_plan_json as plans
import lhc_plan_control as control
import lhc_plan_mirror as mirror
import lhc_time_guard as guard

PRIVATE='INDEPENDENT-FIXTURE-PRIVATE-PAYLOAD'

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))


def test_real_http_public_roundtrip_private_exclusion_and_cache_refresh(tmp_path):
    subprocess.run(['git','init','--quiet',str(tmp_path)],check=True)
    plan=tmp_path/'.agents/tasks/public-fixture'
    write(plan/'plan.json',{'title':'Independent fixture','goal':'Verify local B','slots':1})
    write(plan/'leaves/L1.json',{'id':'L1','label':'Fixture step','status':'done','session':'fixture-lead','harness':'codex'})
    outcome={'id':'fixture-goal','task_class':'quickfix','contract_confirmed':True,
        'owner':{'harness':'codex','session_id':'fixture-lead'},'original_goal':'Verify local B','latest_correction':'Verify local B',
        'canary':{'scenario':'Local B','target':'python3 total.py','expected':'13','status':'pending'},
        'stages':{key:{'status':'pending' if key in {'technical','consumer'} else 'not-applicable'}
            for key in ('technical','deploy','consumer','publication','integration')},
        'plan_binding_history':[{'private_payload':PRIVATE}]}
    metadata,rows=control.read_plan(plan)
    outcome['plan_binding']=control.binding(metadata,outcome,plan)
    control.record_decision(metadata,rows,outcome,{},plan,{'decision':'need_fact','action_kind':'research',
        'action':'Inspect local fixture','owner':'fixture-lead','evidence':PRIVATE,'uncertainty':'Fixture only'})
    path=guard.learning_path(tmp_path,'codex','fixture-lead');assert path.is_relative_to(tmp_path)
    guard.write_state(path,{'business':{'outcome':outcome}})
    native_view=plans.goal_control(plan)
    assert native_view['decision']['evidence']==PRIVATE
    token=tmp_path/'fixture-token';token.write_text('f'*32);token.chmod(0o600)
    dashboard=tmp_path/'fixture-dashboard';dashboard.write_text('d'*32);dashboard.chmod(0o600)
    server_cfg={'listen':'127.0.0.1','port':0,'data_dir':str(tmp_path/'replica'),'webroot':str(tmp_path/'web'),
        'base_url':'https://independent.fixture','token_file':str(token),'dashboard_key_file':str(dashboard)}
    server=mirror.make_server(server_cfg)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    endpoint='http://127.0.0.1:'+str(server.server_address[1])
    client=tmp_path/'client.json'
    write(client,{'mode':'mirror','data_dir':str(tmp_path/'client'),'base_url':server_cfg['base_url'],
        'endpoint':endpoint,'token_file':str(token),'roots':[str(plan.parent)],'timeout_seconds':5})
    def upload_and_read():
        captured=mirror.capture(plan)
        assert PRIVATE not in json.dumps(captured['pending'])
        mirror.sync(plan,mirror.config(client))
        with urllib.request.urlopen(endpoint+'/dashboard/'+'d'*32+'/',timeout=5) as response:
            html=response.read().decode()
        entries=list((tmp_path/'replica').glob('*.json'))
        stored=[json.loads(p.read_text()) for p in entries if json.loads(p.read_text()).get('snapshot')]
        assert len(stored)==1
        assert PRIVATE not in json.dumps(stored)+html
        return captured,stored[0],html
    try:
        mirror.register(plan,client)
        first,stored,page=upload_and_read()
        assert stored['snapshot']['document']['goal_control']['goal_status']=='unaccepted'
        assert 'data-state="awaiting"' in page
        before_stamp=mirror.source_stamp(plan);before_fingerprint=mirror.fingerprint(plan)
        state=guard.load_state(path);current=state['business']['outcome']
        current['frontier_decision']['evidence']=PRIVATE+'-changed-private'
        for stage in ('technical','consumer'):current['stages'][stage]['status']='complete'
        current['plan_binding']['acceptance_fingerprint']=control.evidence_fingerprint(current)
        guard.write_state(path,state)
        assert mirror.source_stamp(plan)!=before_stamp
        assert mirror.fingerprint(plan)!=before_fingerprint
        second,stored,page=upload_and_read()
        assert second['seq']>first['seq']
        assert stored['snapshot']['document']['goal_control']['goal_status']=='accepted'
        assert 'data-state="completed"' in page
        # An already cached completed dashboard is invalidated by a new native state.
        current['plan_replacement']={'plan_dir':str(plan),'replacement_plan_dir':str(tmp_path/'.agents/tasks/replacement'),
            'source_ref':'synthetic fixture replacement','plan_scope':control.plan_scope(metadata),'outcome_id':current['id']}
        guard.write_state(path,state)
        third,stored,page=upload_and_read()
        assert third['seq']>second['seq']
        assert stored['snapshot']['document']['goal_control']['goal_status']=='superseded'
        assert 'data-state="superseded"' in page
        print('actual loopback capture/sync/replica/dashboard: unaccepted -> accepted -> superseded; private payload absent; cache refreshed')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        assert not thread.is_alive()


def test_package_copies_include_control_and_handoff_with_exact_source_bytes():
    source=(SNAPSHOT/'scripts/publish_package.py').read_text()
    tree=ast.parse(source)
    copies=None
    replacements=None
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOOL_COPIES' for t in node.targets):
            copies=ast.literal_eval(node.value)
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COMMON' for t in node.targets):
            replacements=ast.literal_eval(node.value)
    assert {'lhc_handoff.py','lhc_plan_control.py'}<=set(copies)
    checked=[]
    for tool in ('lhc_handoff.py','lhc_plan_control.py','lhc_plan_publish.py','lhc_plan_mirror.py','lhc_plan_mcp.py'):
        expected=(TOOLS/tool).read_bytes()
        for folder in ('common/tools','tools','native/codex/common/tools','native/codex/tools'):
            path=SNAPSHOT/'plugins/last-human-commit'/folder/tool
            projected=expected
            if folder.endswith('common/tools'):
                for old,new in replacements: projected=projected.replace(old,new)
            assert path.read_bytes()==projected,str(path)
            checked.append(str(path.relative_to(SNAPSHOT)))
    assert (SNAPSHOT/'VERSION').read_text().strip()=='1.18.0'
    print('package parity:',len(checked),'exact tool copies, control/handoff in publisher, VERSION=1.18.0')
