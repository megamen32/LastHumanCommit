"""Bootstrap boundaries on exact source, isolated fixture journals only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parent
TOOLS=ROOT/'H-8a34499/src/common/tools'
sys.path.insert(0,str(TOOLS))
import lhc_time_guard as guard

PROMPT='🤖 Agent relay fixture. Inspect only fixture.py; return the finding to Lead. No publish permission.\nKeep exact Unicode: ё.'

@pytest.fixture
def case(tmp_path,monkeypatch):
    subprocess.run(['git','init','--quiet',str(tmp_path)],check=True)
    home=tmp_path/'own-native-format'
    monkeypatch.setenv('CODEX_HOME',str(home))
    monkeypatch.setenv('CODEX_THREAD_ID','independent-bootstrap-owner')
    journal=home/'sessions/independent-bootstrap-owner.jsonl'
    journal.parent.mkdir(parents=True)
    rows=[{'type':'session_meta','payload':{'id':'independent-bootstrap-owner','cwd':str(tmp_path)}},
        {'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':PROMPT}]}}]
    journal.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
    path=guard.learning_path(tmp_path,'codex','independent-bootstrap-owner')
    assert path.is_relative_to(tmp_path)
    return tmp_path,journal,path,rows


def invoke(root,command='contract',kind='quickfix',extra=(),runtime='codex',sid='independent-bootstrap-owner'):
    args=[sys.executable,str(TOOLS/'lhc_outcome.py'),'--cwd',str(root),'--runtime',runtime,'--session-id',sid,command]
    if command=='contract':
        args+=['--task-class',kind,'--scenario','Fixture result','--target','python3 fixture.py','--expected','ok']
        if kind in {'quickfix','fullcycle'}:args+=['--owned-path','fixture.py']
        if kind=='testing':args+=['--coverage','fixture-only']
    return subprocess.run(args+list(extra),capture_output=True,text=True,timeout=15)


def rewrite(journal,rows):journal.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))


def test_nested_child_header_cannot_bootstrap_as_standalone(case):
    root,journal,path,rows=case
    rows[0]['payload']['source']={'subagent':{'thread_spawn':{'parent_thread_id':'unverified-fixture-parent','depth':1}}}
    rewrite(journal,rows)
    result=invoke(root)
    print('nested child result:',result.returncode,result.stdout[:350],result.stderr)
    assert result.returncode!=0,'child header was promoted to verified standalone identity'
    assert not path.exists()

@pytest.mark.parametrize('kind',['quickfix','fullcycle','testing','research'])
def test_bootstrap_pending_unknown_origin_and_repeat_stable(case,kind):
    root,journal,path,rows=case
    result=invoke(root,kind=kind);assert result.returncode==0,result.stderr
    outcome=json.loads(result.stdout)
    assert outcome['finish_verdict']=='pending' and outcome['product_verdict']=='not-tested'
    assert outcome['original_goal']==PROMPT and outcome['latest_correction']==PROMPT
    assert outcome['bootstrap']['scope_origin']=='unknown'
    assert not outcome['scope_sources'] and not outcome['sources'] and not outcome.get('integration_policy')
    expected=set(('technical','deploy','consumer','publication','integration')) if kind=='fullcycle' else {'technical','consumer'} if kind=='quickfix' else {'consumer'}
    assert {k for k,v in outcome['stages'].items() if v['status']=='pending'}==expected
    assert all(v['status'] in {'pending','not-applicable'} and not v['evidence'] for v in outcome['stages'].values())
    source=outcome['bootstrap']['native_input'];raw=journal.read_bytes()
    assert source['sha256']==hashlib.sha256(PROMPT.encode()).hexdigest()
    row=json.loads(raw[source['byte_offset']:].splitlines()[0]);assert row['payload']['role']=='user'
    saved=guard.load_state(path);assert 'native_entry' not in saved and 'milestone' not in saved
    repeated=invoke(root,kind=kind);assert repeated.returncode==0,repeated.stderr
    after=json.loads(repeated.stdout)
    for key in ('id','started_at','evidence_after','bootstrap','stages'):assert after[key]==outcome[key]


def test_readonly_missing_status_no_state_no_lock(case):
    root,journal,path,rows=case
    before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result=invoke(root,command='status');assert result.returncode!=0
    assert not path.exists() and not path.with_suffix('.lock').exists()
    assert {str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}==before

@pytest.mark.parametrize('variant',['no-env','foreign-id','wrong-runtime','wrong-cwd','top-child','missing-input','huge-input','invalid-contract'])
def test_unverified_or_invalid_bootstrap_fails_closed(case,monkeypatch,variant):
    root,journal,path,rows=case
    target=root;kwargs={}
    if variant=='no-env':monkeypatch.delenv('CODEX_THREAD_ID')
    if variant=='foreign-id':kwargs['sid']='foreign-fixture'
    if variant=='wrong-runtime':kwargs['runtime']='opencode'
    if variant=='wrong-cwd':target=root/'other';target.mkdir()
    if variant=='top-child':rows[0]['payload']['parent_thread_id']='unknown-parent';rewrite(journal,rows)
    if variant=='missing-input':rewrite(journal,rows[:1])
    if variant=='huge-input':rows[1]['payload']['content'][0]['text']='x'*(65536+1);rewrite(journal,rows)
    if variant=='invalid-contract':kwargs['extra']=['--integration-branch','main']
    result=invoke(target,**kwargs);assert result.returncode!=0,result.stdout
    assert not path.exists()

@pytest.mark.parametrize('hold',['HumanStop','SessionEnd','permission_declined','codex_quota_guard'])
def test_existing_timer_holds_and_closed_state_preserved(case,hold):
    root,journal,path,rows=case
    guard.native_heartbeat(root,'codex','independent-bootstrap-owner')
    state=guard.load_state(path);state['native_entry']={'finish_hold':hold};guard.write_state(path,state)
    before=path.read_bytes()
    assert invoke(root).returncode!=0
    assert path.read_bytes()==before


def test_time_and_input_history_are_preserved(case):
    root,journal,path,rows=case
    guard.native_heartbeat(root,'codex','independent-bootstrap-owner')
    state=guard.load_state(path)
    state['started_at']='2026-11-01T00:00:00+00:00';state['due_at']='2026-11-01T02:00:00+00:00'
    state['business']={'runtime':'codex','transcript_path':str(journal),'original_prompt_full':'Original captured fixture scope',
        'latest_prompt_full':'Later captured correction'}
    guard.write_state(path,state);before=copy.deepcopy(state)
    result=invoke(root);assert result.returncode==0,result.stderr
    saved=guard.load_state(path)
    assert saved['native_heartbeat']==before['native_heartbeat']
    for key in ('started_at','due_at'):assert saved[key]==before[key]
    outcome=saved['business']['outcome']
    assert outcome['original_goal']=='Original captured fixture scope'
    assert outcome['latest_correction']=='Later captured correction'
    assert saved['business']['original_prompt_full']==before['business']['original_prompt_full']
    assert outcome['bootstrap']['native_input'] is None
