"""Native format fixtures only; never product acceptance."""
import json
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_outcome_review as review


def call(cmd, ident='operation', output='observed', index=2):
    return ({'name': 'exec_command', 'call_id': ident, 'arguments': json.dumps({'cmd': cmd}),
             '_source_index': index, '_source_time': '2026-10-20T14:00:00Z'}, output)


def test_source_bound_newline_browser_journey(tmp_path):
    from lhc_testing_reuse import browser_sources
    ops = [call('agent-browser --session own --namespace qa open https://example.test/login', 'open', 'https://example.test/login'),
           call('agent-browser --session own --namespace qa click @e1\nagent-browser --session own --namespace qa snapshot -i', 'action', '✓ Done\nCabinet')]
    ops = browser_sources(ops, tmp_path)
    assert review.real_observation(*ops[0], 'https://example.test', 'consumer', 'testing', tmp_path)
    assert review.browser_journey(['open', 'action'], dict((c['call_id'], (c,o)) for c,o in ops), 'https://example.test')


@pytest.mark.parametrize('fault', ['wrong-origin', 'no-action', 'wrong-session', 'echo'])
def test_browser_source_shields(tmp_path, fault):
    from lhc_testing_reuse import browser_sources
    origin = 'https://example.test.evil' if fault == 'wrong-origin' else 'https://example.test'
    session = 'foreign' if fault == 'wrong-session' else 'own'
    action = 'snapshot -i' if fault == 'no-action' else 'click @e1'
    prefix = 'echo ' if fault == 'echo' else ''
    ops = browser_sources([call(f'agent-browser --session own open {origin}/login', 'open', origin),
        call(f'{prefix}agent-browser --session {session} {action}\nagent-browser --session {session} snapshot -i', 'action')], tmp_path)
    assert not review.browser_journey(['open', 'action'], {c['call_id']:(c,o) for c,o in ops}, 'https://example.test')


def test_literal_wrapper_requires_original_creation(tmp_path):
    from lhc_testing_reuse import browser_sources
    base = ['agent-browser','--session','own','--namespace','qa','--profile',str(tmp_path/'profile'),'--auto-connect','false','--headed','false']
    creation = "cat > browser.py <<'PY'\nimport os, subprocess, sys\nbase="+repr(base)+"\nos.environ.pop('AGENT_BROWSER_AUTO_CONNECT',None)\nsys.exit(subprocess.run(base+sys.argv[1:]).returncode)\nPY\n"
    operation = call('python3 browser.py open https://example.test/login', 'open')
    for source, valid in [(creation, True),(creation.replace('sys.argv[1:]', "['click','evil']"),False)]:
        ops = browser_sources([call(source,'creation'),operation],tmp_path)
        assert review.real_observation(*ops[-1], 'https://example.test','consumer','testing',tmp_path) is valid
    assert not review.real_observation(*browser_sources([operation],tmp_path)[0], 'https://example.test','consumer','testing',tmp_path)


def reuse_fixture(root, monkeypatch):
    """Small own-native source, with a report preceding coverage registration."""
    import test_outcome_contract as fixtures
    from datetime import datetime, timedelta, timezone
    import lhc_outcome as outcomes
    outcome = fixtures.anchored(root, goal='Read-only testing: test cabinet switching on https://example.test; report actual defects.')
    outcome['canary'].update(target='https://example.test', scenario='Switch cabinets', expected='Cabinet switches and failures are reported')
    outcome['coverage'] = ['cabinet switching']
    outcome['owned_paths'] = []
    outcome['revision'] = outcomes.scope_revision(outcome, root)
    original = json.loads(json.dumps(outcome)); original['coverage'] = []
    start = datetime.now(timezone.utc)
    original['evidence_after'] = (start-timedelta(minutes=5)).isoformat()
    outcome['evidence_after'] = start.isoformat()
    outcome['started_at'] = (start-timedelta(minutes=6)).isoformat()
    original['started_at'] = outcome['started_at']
    rows = []
    def add(payload, stamp=None, kind='response_item'):
        rows.append({'type':kind,'timestamp':stamp or (start-timedelta(minutes=3)).isoformat(),'payload':payload})
    add({'id':'leader','cwd':str(root)},kind='session_meta')
    add({'type':'message','role':'user','content':[{'text':outcome['original_goal']}]})
    def operation(ident, cmd, output):
        add({'type':'function_call','name':'exec_command','call_id':ident,'arguments':json.dumps({'cmd':cmd,'workdir':str(root)})})
        add({'type':'function_call_output','call_id':ident,'output':output})
    operation('contract', 'python3 /source/lhc_outcome.py --cwd '+str(root)+' --runtime codex --session-id leader contract --scenario x',json.dumps(original))
    operation('open','agent-browser --session own open https://example.test/login','https://example.test/login')
    operation('action','agent-browser --session own click @e1\nagent-browser --session own snapshot -i','✓ Done\nCabinet demo2')
    operation('defect','agent-browser --session own open https://example.test/chat','https://example.test/chat\nLead not found')
    report_index=len(rows)
    add({'type':'message','role':'assistant','phase':'final','content':[{'text':'Cabinet switching works. Product defect: Lead not found.'}]})
    auth_index=len(rows)
    authorization='Reuse already performed testing checks for LHC self-check without replay or fictitious PASS.'
    add({'type':'message','role':'user','content':[{'text':authorization}]},(start+timedelta(seconds=1)).isoformat())
    native = root/'native-home/.codex/sessions/leader.jsonl';native.parent.mkdir(parents=True,exist_ok=True)
    native.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    manifest=root/'reuse.manifest.json'
    manifest.write_text(json.dumps({'format':'agent-herder-transcript-manifest-v1','target':{'path':str(native),
        'harness':'codex','sessionId':'leader','complete':True,'source':{'kind':'native-file','location':str(native)}}}))
    monkeypatch.setenv('CODEX_HOME',str(root/'native-home/.codex'))
    binding={'contract_call':'contract','authorization_index':auth_index,'authorization_quote':authorization,
        'assessment_index':report_index,'coverage':[{'item':'cabinet switching','verdict':'passed',
        'quote':'Cabinet switching works.','observed':'Cabinet demo2','calls':['open','action']}],
        'defect':{'quote':'Lead not found','calls':['defect']}}
    return outcome,manifest,binding,native


def test_reuse_closes_only_own_testing_at_original_source_times(tmp_path, monkeypatch):
    from lhc_outcome import verdict
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch)
    original_bytes=source.read_bytes();after=outcome['evidence_after']
    review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
    assert outcome['verification_level']=='self-check'
    assert outcome['product_verdict']=='changes-required'
    assert outcome['canary']['status']=='complete'
    assert verdict(outcome,{})=='complete'
    assert outcome['coverage_evidence']['cabinet switching']['verdict']=='passed'
    assert outcome['evidence_after']==after and source.read_bytes()==original_bytes
    assert outcome['testing_reuse_binding']['current_product_acceptance'] is False


@pytest.mark.parametrize('fault',['tamper','no-original','wrong-canary','wrong-origin','no-action','no-authorization','no-coverage-output','changed-revision','engineering'])
def test_reuse_failure_shields_leave_outcome_unchanged(tmp_path,monkeypatch,fault):
    import copy
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch)
    if fault=='tamper':
        export=tmp_path/'tampered.jsonl';export.write_bytes(source.read_bytes().replace(b'Cabinet demo2',b'Cabinet demo3'))
        data=json.loads(manifest.read_text());data['target']['path']=str(export);manifest.write_text(json.dumps(data))
    elif fault=='no-original':binding['contract_call']='open'
    elif fault=='wrong-canary':outcome['canary']['expected']='New requirement'
    elif fault=='no-authorization':binding['authorization_index']=1
    elif fault=='no-coverage-output':binding['coverage'][0]['observed']='Never observed'
    elif fault=='changed-revision':outcome['revision']='different'
    elif fault=='engineering':outcome['task_class']='quickfix'
    elif fault in {'wrong-origin','no-action'}:
        raw=source.read_bytes()
        raw=raw.replace(b'agent-browser --session own open https://example.test/login',b'agent-browser --session own open https://evil.test/login') if fault=='wrong-origin' else raw.replace(b'click @e1',b'snapshot -i')
        source.write_bytes(raw)
    before=copy.deepcopy(outcome)
    with pytest.raises((ValueError,KeyError)):
        review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
    assert outcome==before


@pytest.mark.parametrize('later_consumer', [False, True])
def test_reuse_distinguishes_metadata_error_from_new_product_observations(tmp_path,monkeypatch,later_consumer):
    import copy
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch)
    rows=[json.loads(line) for line in source.read_text().splitlines()]
    stamp=rows[-1]['timestamp']
    if later_consumer:
        rows.extend([{'type':'response_item','timestamp':stamp,'payload':{'type':'function_call','name':'exec_command',
            'call_id':'new-product-read','arguments':json.dumps({'cmd':'agent-browser --session own get url'})}},
            {'type':'response_item','timestamp':stamp,'payload':{'type':'function_call_output','call_id':'new-product-read','output':'https://example.test/login'}}])
    rows.append({'type':'response_item','timestamp':stamp,'payload':{'type':'message','role':'assistant','phase':'commentary',
        'content':[{'text':'Cabinet login failed after a new consumer attempt.' if later_consumer else 'Нашёл свою ошибку: до начала проверки я не указал отдельный список coverage.'}]}})
    source.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    before=copy.deepcopy(outcome)
    if later_consumer:
        with pytest.raises(ValueError,match='later negative'):
            review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
        assert outcome==before
    else:
        review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
        assert outcome['product_verdict']=='changes-required'


@pytest.mark.parametrize('script', [
    'echo "example\nagent-browser --session own open https://example.test\n"',
    "cat <<'EXAMPLE'\nagent-browser --session own open https://example.test\nEXAMPLE",
])
def test_quoted_examples_are_never_browser_sources(tmp_path,script):
    from lhc_testing_reuse import browser_sources
    op=browser_sources([call(script,output='https://example.test')],tmp_path)[0]
    assert not review.real_observation(*op,'https://example.test','consumer','testing',tmp_path)


@pytest.mark.parametrize('product_edit', [False, True])
@pytest.mark.parametrize('later_report_refresh', [False, True])
def test_historical_revision_difference_needs_report_only_git_delta(tmp_path,monkeypatch,product_edit,later_report_refresh):
    import subprocess
    import lhc_outcome as outcomes
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch)
    report_path='.agents/tasks/feedback.md'
    (tmp_path/'.agents/tasks').mkdir(parents=True,exist_ok=True)
    (tmp_path/report_path).write_text('before')
    def git(*args):
        return subprocess.check_output(['git','-c','user.name=Fixture','-c','user.email=fixture@example.test',*args],cwd=tmp_path,text=True).strip()
    git('add','total.py',report_path);git('commit','-qm','fixture baseline')
    baseline=git('rev-parse','HEAD')
    outcome['owned_paths']=[report_path]
    old_revision=outcomes.scope_revision(outcome,tmp_path)
    (tmp_path/report_path).write_text('actual testing feedback')
    if product_edit:(tmp_path/'total.py').write_text('changed product')
    git('add',report_path,'total.py');git('commit','-qm','fixture changes')
    outcome['revision']=outcomes.scope_revision(outcome,tmp_path)
    rows=[json.loads(line) for line in source.read_text().splitlines()]
    original=json.loads(rows[3]['payload']['output']);original.update(owned_paths=[report_path],revision=old_revision)
    rows[3]['payload']['output']=json.dumps(original)
    stamp=rows[2]['timestamp']
    rows[2:2]=[{'type':'response_item','timestamp':stamp,'payload':{'type':'function_call','name':'exec_command',
        'call_id':'baseline','arguments':json.dumps({'cmd':'git rev-parse HEAD'})}},
        {'type':'response_item','timestamp':stamp,'payload':{'type':'function_call_output','call_id':'baseline','output':baseline}}]
    binding.update(baseline_commit=baseline,baseline_call='baseline',assessment_index=binding['assessment_index']+2,
                   authorization_index=binding['authorization_index']+2)
    source.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    if later_report_refresh:
        from datetime import datetime, timedelta
        outcome['evidence_after']=(datetime.fromisoformat(rows[binding['authorization_index']]['timestamp'])+timedelta(minutes=2)).isoformat()
    evidence_after=outcome['evidence_after']
    original_bytes=source.read_bytes()
    if product_edit:
        with pytest.raises(ValueError,match='product changed'):
            review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
    else:
        review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
        assert outcome['testing_reuse_binding']['historical_revision']==old_revision
        assert outcome['stages']['consumer']['evidence'][0]['revision']==old_revision
        assert outcome['evidence_after']==evidence_after and source.read_bytes()==original_bytes
        assert outcome['testing_reuse_binding']['calls']['action']['at']==rows[6]['timestamp']


def test_reuse_authorization_must_follow_original_assessment(tmp_path,monkeypatch):
    from datetime import datetime,timedelta
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch)
    rows=[json.loads(line) for line in source.read_text().splitlines()]
    rows[binding['authorization_index']]['timestamp']=(datetime.fromisoformat(rows[binding['assessment_index']]['timestamp'])-timedelta(seconds=1)).isoformat()
    source.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    with pytest.raises(ValueError,match='authorization predates'):
        review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
