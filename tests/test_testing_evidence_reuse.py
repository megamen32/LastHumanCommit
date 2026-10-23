"""Native format fixtures only; never product acceptance."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_outcome_review as review

from _inprocess_lane import anchored_outcome, outcome_cli


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


def test_unexecuted_shell_control_flow_cannot_supply_browser_evidence(tmp_path):
    from lhc_testing_reuse import browser_sources
    command_text = (
        'if false; then\n'
        'agent-browser --session own open https://example.test/login\n'
        'agent-browser --session own click @e1\n'
        'agent-browser --session own snapshot -i\n'
        'fi')
    output = 'https://example.test/login\n✓ Done\nCabinet list'
    call_value, output = browser_sources([call(command_text, 'conditional-journey', output)], tmp_path)[0]
    assert not call_value.get('_browser_ops')
    assert not review.browser_journey(['conditional-journey'],
        {'conditional-journey': (call_value, output)}, 'https://example.test')


@pytest.mark.parametrize('function_header', ['journey() {', 'journey(){'])
def test_uninvoked_shell_function_cannot_supply_browser_evidence(tmp_path, function_header):
    from lhc_testing_reuse import browser_sources
    command_text = (
        function_header+'\n'
        'agent-browser --session own open https://example.test/login\n'
        'agent-browser --session own click @e1\n'
        'agent-browser --session own snapshot -i\n'
        '}\n'
        'printf result')
    output = 'https://example.test/login\n✓ Done\nCabinet list'
    call_value, output = browser_sources([call(command_text, 'function-journey', output)], tmp_path)[0]
    assert not call_value.get('_browser_ops')
    assert not review.browser_journey(['function-journey'],
        {'function-journey': (call_value, output)}, 'https://example.test')


@pytest.mark.parametrize('tools_relative', ['tools', 'native/codex/tools'])
def test_packaged_review_can_resolve_reuse_helper(tmp_path, tools_relative):
    package = Path(__file__).resolve().parents[1] / 'plugins/last-human-commit'
    tool_directory = package / tools_relative
    code = (
        'import importlib.util, sys; '
        f'sys.path.insert(0, {str(tool_directory)!r}); '
        'import lhc_outcome_review; '
        'assert importlib.util.find_spec("lhc_testing_reuse") is not None')
    result = subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


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


def reuse_fixture(root, monkeypatch, live=False):
    """Small own-native source, with a report preceding coverage registration.

    ``live`` contracts the outcome through the real CLI, so the saved session
    state and the native transcript describe one and the same contract and the
    reuse binding can be driven by the explicit review command.
    """
    from datetime import datetime, timedelta, timezone
    import lhc_outcome as outcomes
    goal = ('Read-only testing: test cabinet switching on https://example.test; '
            'report actual defects.')
    if live:
        outcome = anchored_outcome(root, goal=goal, coverage=('cabinet switching',),
                                    canary=('Switch cabinets', 'https://example.test',
                                            'Cabinet switches and failures are reported'))
        # The saved contract time is the floor for the original native source
        # calls, so the transcript is stamped after the real CLI contract.
        base = datetime.fromisoformat(outcome['evidence_after'])
        original = json.loads(json.dumps(outcome)); original['coverage'] = []
        original['evidence_after'] = base.isoformat()
        report_at = (base + timedelta(seconds=3)).isoformat()
        authorization_at = (base + timedelta(seconds=4)).isoformat()
    else:
        outcome = anchored_outcome(root, goal=goal, coverage=('cabinet switching',))
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
        report_at = (start-timedelta(minutes=3)).isoformat()
        authorization_at = (start+timedelta(seconds=1)).isoformat()
    rows = []
    def add(payload, stamp=None, kind='response_item'):
        rows.append({'type':kind,'timestamp':stamp or report_at,'payload':payload})
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
    add({'type':'message','role':'assistant','phase':'final','content':[{'text':'Cabinet switching works. Product defect found: Lead not found.'}]})
    auth_index=len(rows)
    authorization='Reuse already performed testing checks for LHC self-check without replay or fictitious PASS.'
    add({'type':'message','role':'user','content':[{'text':authorization}]},authorization_at)
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


@pytest.mark.parametrize('product_edit_state', ['none', 'committed', 'staged', 'unstaged'])
@pytest.mark.parametrize('later_report_refresh', [False, True])
@pytest.mark.parametrize('report_changed', [False, True])
@pytest.mark.parametrize('baseline_present', [False, True])
def test_historical_revision_difference_needs_report_only_git_delta(tmp_path,monkeypatch,product_edit_state,later_report_refresh,report_changed,baseline_present):
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
    if report_changed:
        (tmp_path/report_path).write_text('actual testing feedback')
    if product_edit_state != 'none':
        (tmp_path/'total.py').write_text('changed product')
    if report_changed:
        git('add',report_path)
    if product_edit_state in {'committed','staged'}:
        git('add','total.py')
    if product_edit_state == 'committed':
        git('commit','-qm','fixture report and product changes')
    elif report_changed:
        git('commit','--only','-m','fixture report-only change','--',report_path)
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
    if not baseline_present:
        binding.pop('baseline_commit')
        binding.pop('baseline_call')
    source.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    if later_report_refresh:
        from datetime import datetime, timedelta
        outcome['evidence_after']=(datetime.fromisoformat(rows[binding['authorization_index']]['timestamp'])+timedelta(minutes=2)).isoformat()
    evidence_after=outcome['evidence_after']
    original_bytes=source.read_bytes()
    if not baseline_present:
        with pytest.raises(ValueError,match='baseline'):
            review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
    elif product_edit_state != 'none':
        with pytest.raises(ValueError,match='product changed'):
            review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
    else:
        review.accept_review(outcome,{},manifest,tmp_path,'leader',testing_reuse=binding)
        if report_changed:
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


def test_explicit_review_command_routes_the_reuse_binding_into_the_live_outcome(tmp_path,monkeypatch):
    """The reuse binding is reachable by the agent through the explicit command.

    The in-process tests call accept_review directly; this proves the CLI
    actually reads --testing-reuse-bindings and that the reuse is what closes
    the consumer stage.
    """
    outcome,manifest,binding,source=reuse_fixture(tmp_path,monkeypatch,live=True)
    bindings=tmp_path/'reuse-bindings.json'
    bindings.write_text(json.dumps(binding))
    # Without the explicit binding the same own-native source cannot close:
    # the reuse grant is the only route to the original consumer evidence.
    rejected=outcome_cli(tmp_path,'review','--manifest',str(manifest),ok=False)
    assert 'assigned coverage needs its actual native consumer observations' in rejected, rejected
    result=outcome_cli(tmp_path,'review','--manifest',str(manifest),
                        '--testing-reuse-bindings',str(bindings))
    assert result['finish_verdict']=='complete'
    assert result['verification_level']=='self-check'
    assert result['product_verdict']=='changes-required'
    assert result['testing_reuse_binding']['current_product_acceptance'] is False
    assert result['testing_reuse_binding']['contract_call']=='contract'
