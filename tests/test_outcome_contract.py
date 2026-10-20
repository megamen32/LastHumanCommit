"""Ordinary task completion must retain its real canary, including non-UI work.

These regressions exercise the native entry subprocess; no installed runtime,
external services or fabricated acceptance are involved.
"""
import subprocess

import pytest

from test_native_milestone_gate import invoke, setup, state


@pytest.mark.parametrize("goal", [
    "Fix the small API bug: GET /totals returns 500 for an empty cart. "
    "Verify that a real HTTP request returns 200 and total 0.",
    "Implement the CSV export CLI. Verify a real invocation exports two rows "
    "and preserves Cyrillic names.",
])
def test_non_ui_task_cannot_finish_with_only_technical_tests(tmp_path, goal):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt=goal)
    (tmp_path / "service.py").write_text("def total(): return 0\n")
    invoke(tmp_path, "PostToolUse", tool_name="exec_command",
           tool_input={"cmd": "python3 -m pytest -q"},
           tool_response={"exit_code": 0, "stdout": "1 passed"})
    result = invoke(tmp_path, "Stop", last_assistant_message="Unit tests pass; done.")
    assert result.get("decision") == "block", (result, state(tmp_path)["milestone"])


def test_read_only_testing_cannot_finish_without_assigned_scenario(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    invoke(tmp_path, "UserPromptSubmit", prompt=(
        "You are a fresh Zero Knowledge tester. Do not modify code. "
        "Test checkout with an empty basket and a two-item basket on the running "
        "website at https://demo.test/checkout. Record actual actions and results."))
    result = invoke(tmp_path, "Stop", last_assistant_message="Read-only testing; no edits needed.")
    assert result.get("decision") == "block", (result, state(tmp_path)["milestone"])


def test_pending_acceptance_can_continue_again_after_real_progress(tmp_path):
    setup(tmp_path)
    assert invoke(tmp_path, "Stop").get("decision") == "block"
    # A duplicate Stop without progress must stay bounded.
    assert invoke(tmp_path, "Stop", stop_hook_active=True).get("decision") != "block"
    # The original task still lacks independent acceptance after a real edit.
    (tmp_path / "dashboard.html").write_text(
        "<main><input type=search><button>Import CSV</button><nav>Reports</nav></main>")
    invoke(tmp_path, "PostToolUse", tool_name="exec_command",
           tool_input={"cmd": "python3 repair_import.py"},
           tool_response={"exit_code": 0, "stdout": "Import control repaired"})
    result = invoke(tmp_path, "Stop", turn_id="two", stop_hook_active=False,
                    last_assistant_message="Import repaired; the task is complete.")
    assert result.get("decision") == "block", (result, state(tmp_path)["milestone"])

# The following are source fixtures, not independent product/native acceptance.
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTCOME = ROOT / 'src/common/tools/lhc_outcome.py'
sys.path.insert(0, str(OUTCOME.parent))


def cli(root, *args, ok=True):
    result = subprocess.run([sys.executable, str(OUTCOME), '--cwd', str(root), '--runtime', 'codex',
                             '--session-id', 'leader', *args], capture_output=True, text=True,
                            env={**os.environ, 'HOME': str(root / 'native-home'),
                                 'CODEX_HOME': str(root / 'native-home/.codex')})
    assert (result.returncode == 0) == ok, result.stderr
    return json.loads(result.stdout) if result.returncode == 0 else result.stderr


def anchored(root, goal='Fix the small total CLI. Verify the empty basket returns 0.', coverage=()):
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / 'total.py').write_text('print(0)\n')
    (root / 'test_total.py').write_text(
        "import unittest, subprocess, sys\nclass TotalTest(unittest.TestCase):\n"
        " def test_empty(self): self.assertEqual(subprocess.check_output([sys.executable, 'total.py']).strip(), b'0')\n")
    invoke(root, 'UserPromptSubmit', prompt=goal)
    args = ['contract', '--scenario', 'Empty basket total', '--target', 'python3 total.py', '--expected', '0']
    if state(root)['business']['outcome']['task_class'] in {'quickfix', 'fullcycle'}:
        args += ['--owned-path', 'total.py']
    if state(root)['business']['outcome']['task_class'] == 'fullcycle':
        for stage, target, expected in [('deploy', 'https://demo.test/version', 'v2'),
                                        ('publication', 'https://github.com/owned/project/pull/1', 'a' * 40),
                                        ('integration', 'https://github.com/owned/project/pull/1', 'b' * 40)]:
            args += ['--stage-target', stage + '=' + target, '--stage-expected', stage + '=' + expected]
    for item in coverage:
        args += ['--coverage', item]
    return cli(root, *args)


def review_export(root, outcome, *, product='pass', stage_names=('technical', 'consumer'),
                  sid='reviewer', target=None, command=None, revision=None, coverage=None, compared=True,
                  coverage_compared=True, consumer_workdir=None, raw_final=None, bad_deploy=False):
    now = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    native_path = root / 'native-home/.codex/sessions' / (sid + '.jsonl')
    native_path.parent.mkdir(parents=True, exist_ok=True)
    commands = {'technical': 'python3 -m unittest discover -q', 'consumer': 'python3 total.py',
                'deploy': 'curl https://demo.test/version',
                'publication': 'gh pr view https://github.com/owned/project/pull/1 --json url,state,headRefOid',
                'integration': 'gh pr view https://github.com/owned/project/pull/1 --json url,state,mergedAt,mergeCommit'}
    rows = [{'type': 'session_meta', 'payload': {'id': sid, 'cwd': str(root), 'timestamp': now}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
             'content': [{'text': 'Independent review of outcome ' + outcome['id'] + ': compare actual operation/target/revision/results. Original scope: ' + outcome['original_goal']}]}}]
    report = {'outcome_id': outcome['id'], 'revision': revision or outcome['revision'],
              'target': target or outcome['canary']['target'], 'scenario': outcome['canary']['scenario'],
              'expected': outcome['canary']['expected'], 'assignment_verdict': 'complete',
              'product_verdict': product, 'comparison': 'Observed CLI output compared with empty basket requirement.',
              'coverage': coverage or {}, 'stages': {}}
    for index, stage in enumerate(stage_names):
        cmd = command if stage == 'consumer' and command else commands[stage]
        # Actually run local technical/consumer commands for this fixture; remote
        # stage rows below are deliberately fake and never release acceptance.
        if stage in {'technical', 'consumer'}:
            completed = subprocess.run(cmd.split(), cwd=consumer_workdir if stage == 'consumer' and consumer_workdir else root, capture_output=True, text=True)
            output = completed.stdout + completed.stderr
        else:
            # Explicit native-format fixtures, NOT live release receipts. Unlike
            # a generic nonempty string, the readback binds target and version.
            output = json.dumps({'version': 'v2'} if stage == 'deploy' else
                                {'url': 'https://github.com/owned/project/pull/1', 'state': 'OPEN', 'headRefOid': 'a' * 40, 'baseRefName': 'main'} if stage == 'publication' else
                                {'url': 'https://github.com/owned/project/pull/1', 'state': 'MERGED', 'mergedAt': now, 'mergeCommit': {'oid': 'b' * 40}, 'baseRefName': 'main'})
            if stage == 'deploy' and bad_deploy:
                cmd = 'git rev-parse HEAD'
                proc = subprocess.run(cmd.split(), cwd=root, capture_output=True, text=True)
                output = proc.stdout + proc.stderr
        call = 'call-' + str(index)
        rows += [{'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command',
                  'call_id': call, 'arguments': json.dumps({'cmd': cmd, **({'workdir': str(consumer_workdir)} if stage == 'consumer' and consumer_workdir else {})})}},
                 {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': call, 'output': output}}]
        report['stages'][stage] = {'evidence_calls': [call], 'observed': output.strip()}
        if compared:
            report['stages'][stage]['expected'] = outcome['canary']['expected'] if stage == 'consumer' else 'Successful ' + stage + ' readback for this scope'
            if stage in outcome.get('stage_claims', {}):
                report['stages'][stage].update(outcome['stage_claims'][stage])
    if coverage_compared and coverage:
        consumer = report['stages']['consumer']
        report['coverage'] = {item: {'verdict': verdict, 'expected': outcome['canary']['expected'],
                                    'observed': consumer['observed'], 'evidence_calls': consumer['evidence_calls']}
                              for item, verdict in coverage.items()}
    rows.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final',
                 'content': [{'text': raw_final if raw_final is not None else 'Compared the actual observed CLI behavior.\nLHC_OUTCOME_REVIEW ' + json.dumps(report)}]}})
    for row in rows:
        row['timestamp'] = now
    native_path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
    export = root / (sid + '-export.jsonl'); export.write_bytes(native_path.read_bytes())
    manifest = root / (sid + '.manifest.json')
    manifest.write_text(json.dumps({'format': 'agent-herder-transcript-manifest-v1', 'target': {
        'path': str(export), 'harness': 'codex', 'complete': True, 'sessionId': sid,
        'source': {'kind': 'native-file', 'location': str(native_path)}}}))
    return manifest


def test_real_cli_and_independent_native_review_can_close_quickfix(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome)
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['canary']['status'] == 'complete'
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'


def test_general_comparison_cannot_close_uncompared_stage_claims(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome, compared=False)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_truthful_original_raw_review_can_close_without_json_certificate(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome, raw_final='No defects found. Ran focused tests and python3 total.py; output 0 matched the expected empty basket total 0.')
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'


def test_existing_reviewer_fresh_raw_report_uses_current_assignment_not_session_birth(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome, raw_final='No defects found. Focused tests passed; python3 total.py output 0 matched empty basket total 0.')
    data = json.loads(manifest.read_text()); location = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in location.read_text().splitlines()]
    now = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    for row in rows:
        row['timestamp'] = now
    rows[0]['payload']['timestamp'] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rows.insert(1, {'timestamp': rows[0]['payload']['timestamp'], 'type': 'response_item', 'payload': {
        'type': 'message', 'role': 'user', 'content': [{'text': 'Earlier bounded research assignment.'}]}})
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
    location.write_text(raw); Path(data['target']['path']).write_text(raw)
    assert cli(tmp_path, 'review', '--manifest', str(manifest))['finish_verdict'] == 'complete'


@pytest.mark.parametrize('source_format', ['function-call', 'command-started'])
def test_old_calls_under_fresh_raw_final_cannot_accept_new_owned_revision(tmp_path, source_format):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome, raw_final='No defects found. Focused tests passed; python3 total.py output 0 matched empty basket total 0.')
    (tmp_path / 'total.py').write_text('print(99)\n'); invoke(tmp_path, 'PostToolUse')
    data = json.loads(manifest.read_text()); location = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in location.read_text().splitlines()]
    old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    fresh = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    for row in rows:
        row['timestamp'] = old if row['payload'].get('type') in {'function_call', 'function_call_output'} else fresh
    rows = [rows[0], *rows[2:-1], rows[1], rows[-1]]
    if source_format == 'command-started':
        calls = {row['payload']['call_id']: row['payload'] for row in rows if row['payload'].get('type') == 'function_call'}
        started, completed = [], []
        for row in rows:
            p = row['payload']
            if p.get('type') != 'function_call_output':
                continue
            args = json.loads(calls[p['call_id']]['arguments'])
            item = {'type': 'CommandExecution', 'id': p['call_id'], 'command': ['/bin/bash', '-lc', args['cmd']], 'cwd': str(tmp_path)}
            started.append({'timestamp': old, 'type': 'event_msg', 'payload': {'type': 'item_started', 'item': item}})
            completed.append({'timestamp': fresh, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {**item, 'exit_code': 0, 'aggregated_output': p['output']}}})
        rows = [rows[0], *started, rows[-2], *completed, rows[-1]]
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
    location.write_text(raw); Path(data['target']['path']).write_text(raw)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_git_metadata_does_not_prove_deployment(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    manifest = review_export(tmp_path, outcome, stage_names=('technical', 'deploy'), bad_deploy=True)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['stages']['deploy']['status'] == 'pending'


@pytest.mark.parametrize('actual_action,other_session', [(False, False), (True, False), (True, True)])
def test_login_only_browser_open_does_not_complete_checkout(tmp_path, actual_action, other_session):
    anchored(tmp_path, 'Only test checkout. Do not edit code. Report observed failures.', ('empty basket',))
    outcome = cli(tmp_path, 'contract', '--scenario', 'Checkout an empty basket', '--target', 'https://demo.test/checkout',
                  '--expected', 'total 0', '--coverage', 'empty basket')
    manifest = review_export(tmp_path, outcome, stage_names=('consumer',), coverage={'empty basket': 'passed'})
    data = json.loads(manifest.read_text()); location = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in location.read_text().splitlines()]
    for row in rows:
        p = row['payload']
        if p.get('type') == 'function_call':
            p.update(name='mcp__browser__open', arguments=json.dumps({'url': outcome['canary']['target'], 'session': 'A', 'namespace': 'qa'}))
        elif p.get('type') == 'function_call_output':
            p['output'] = 'Sign in. Password required. Checkout was never attempted.'
    if actual_action:
        for call, name, args, output in [('action', 'mcp__browser__click', {'ref': 'empty-checkout'}, 'Checkout submitted'),
                                         ('result', 'mcp__browser__snapshot', {}, 'Empty basket total 0')]:
            args.update(session='B' if other_session else 'A', namespace='qa')
            stamp = rows[-1]['timestamp']
            rows.insert(-1, {'timestamp': stamp, 'type': 'response_item', 'payload': {'type': 'function_call', 'name': name, 'call_id': call, 'arguments': json.dumps(args)}})
            rows.insert(-1, {'timestamp': stamp, 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': call, 'output': output}})
        text = rows[-1]['payload']['content'][0]['text']; prefix, body = text.split('LHC_OUTCOME_REVIEW ', 1)
        report = json.loads(body); report['stages']['consumer']['evidence_calls'] += ['action', 'result']
        report['stages']['consumer']['observed'] = 'Submitted empty checkout, snapshot showed total 0'
        report['coverage']['empty basket'].update(evidence_calls=['call-0', 'action', 'result'], observed='Submitted empty checkout, total 0')
        rows[-1]['payload']['content'][0]['text'] = prefix + 'LHC_OUTCOME_REVIEW ' + json.dumps(report)
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
    location.write_text(raw); Path(data['target']['path']).write_text(raw)
    accepted = actual_action and not other_session
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=accepted)
    assert cli(tmp_path, 'status')['finish_verdict'] == ('complete' if accepted else 'pending')


def test_other_checkout_output_cannot_accept_owned_cli(tmp_path):
    anchored(tmp_path)
    (tmp_path / 'total.py').write_text('print(99)\n')
    invoke(tmp_path, 'PostToolUse')
    outcome = cli(tmp_path, 'status')
    other = tmp_path / 'other'; other.mkdir(); (other / 'total.py').write_text('print(0)\n')
    manifest = review_export(tmp_path, outcome, consumer_workdir=other)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_bare_latest_no_deploy_correction_preserves_repair_and_removes_deploy(tmp_path):
    anchored(tmp_path, 'Implement the complete CLI and deploy it.')
    before = state(tmp_path)
    invoke(tmp_path, 'UserPromptSubmit', prompt='Do not deploy anything.')
    after = cli(tmp_path, 'status')
    assert after['task_class'] == 'fullcycle'
    assert after['stages']['deploy']['status'] == 'not-applicable'
    assert after['stages']['technical']['status'] == 'pending'
    assert after['id'] == before['business']['outcome']['id']


@pytest.mark.parametrize('mutation', ['echo', 'wrong-target', 'old-revision', 'own-pass', 'pytest-only'])
def test_refs_and_receipts_do_not_accept_wrong_consumer_result(tmp_path, mutation):
    outcome = anchored(tmp_path)
    args = {'command': 'echo 0'} if mutation == 'echo' else {'target': 'https://wrong.test/totals'} if mutation == 'wrong-target' else {'revision': 'old'} if mutation == 'old-revision' else {'sid': 'leader'} if mutation == 'own-pass' else {'command': 'python3 -m pytest -q'}
    manifest = review_export(tmp_path, outcome, **args)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_testing_assignment_can_complete_with_a_product_defect(tmp_path):
    outcome = anchored(tmp_path, 'You are a tester. Do not edit code. Test empty basket total.', ('empty basket',))
    (tmp_path / 'total.py').write_text('print(99)\n')
    manifest = review_export(tmp_path, outcome, product='changes-required', stage_names=('consumer',), coverage={'empty basket': 'defect'})
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['product_verdict'] == 'changes-required'
    assert result['stages']['deploy']['status'] == 'not-applicable'
    assert result['stages']['technical']['status'] == 'not-applicable'


def test_testing_coverage_labels_without_per_claim_observations_cannot_close(tmp_path):
    outcome = anchored(tmp_path, 'You are a tester. Do not edit code. Test empty basket total.', ('empty basket',))
    manifest = review_export(tmp_path, outcome, product='changes-required', stage_names=('consumer',),
                             coverage={'empty basket': 'defect'}, coverage_compared=False)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_test_and_fix_is_engineering_and_status_does_not_erase_it(tmp_path):
    anchored(tmp_path, 'Test and fix checkout. Verify empty basket total.')
    before = state(tmp_path)['business']['outcome']
    invoke(tmp_path, 'UserPromptSubmit', prompt='Read-only status: explain progress, do not edit code.')
    after = state(tmp_path)['business']['outcome']
    assert after['task_class'] == before['task_class'] == 'quickfix'
    assert after['original_goal'] == before['original_goal']
    assert after['stages']['technical']['status'] == 'pending'


def test_continuation_ignores_call_turn_unrelated_wip_and_a_b_a(tmp_path):
    anchored(tmp_path)
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    (tmp_path / 'foreign.py').write_text('foreign WIP\n')
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_call_id='new-call',
           tool_input={'cmd': 'git status'}, tool_response={'exit_code': 0})
    assert invoke(tmp_path, 'Stop', turn_id='new-turn').get('decision') != 'block'
    (tmp_path / 'total.py').write_text('print(1)\n')
    invoke(tmp_path, 'PostToolUse')
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    (tmp_path / 'total.py').write_text('print(0)\n')
    invoke(tmp_path, 'PostToolUse')
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'


def test_owned_delta_invalidates_previous_close_and_compact_keeps_canary(tmp_path):
    outcome = anchored(tmp_path)
    cli(tmp_path, 'review', '--manifest', str(review_export(tmp_path, outcome)))
    (tmp_path / 'total.py').write_text('print(1)\n')
    invoke(tmp_path, 'PostToolUse')
    invoke(tmp_path, 'PreCompact'); invoke(tmp_path, 'PostCompact')
    restored = invoke(tmp_path, 'SessionStart', source='compact')
    assert 'Empty basket total' in str(restored)
    assert state(tmp_path)['business']['outcome']['finish_verdict'] == 'pending'


def test_bound_question_is_single_and_delivery_is_not_answer(tmp_path):
    anchored(tmp_path)
    first = cli(tmp_path, 'question', '--message', 'Какой тестовый аккаунт использовать?')
    second = cli(tmp_path, 'question', '--message', 'Какой тестовый аккаунт использовать?')
    assert first['binding']['tool'] == 'human_request_create'
    assert first['delivery']['tool'] == 'noticeplace_ask_human'
    assert second['action'] == 'inspect-existing-request'
    q = state(tmp_path)['business']['outcome']['question']
    invoke(tmp_path, 'PostToolUse', tool_name='human_request_create', tool_input={'marker': q['identity']},
           tool_response={'binding': {'request_id': 'request-one', 'native_target': {
               'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}}})
    for status in ['queued', 'uncertain']:
        invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_ask_human', tool_input={'request_id': 'request-one'},
               tool_response={'request_id': 'request-one', 'status': status, 'message_id': 'not-sent'})
        assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_ask_human', tool_input={'request_id': 'request-one'},
           tool_response={'request_id': 'request-one', 'card': 'sent', 'native': {
               'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'delivered'
    assert cli(tmp_path, 'status')['finish_verdict'] == 'blocked'
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_question_result', tool_input={'request_id': 'another'},
           tool_response={'schema': 'ask_human.result.v1', 'request_id': 'another', 'state': 'resolved', 'kind': 'user', 'result_ref': 'foreign-answer', 'native': {'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'delivered'
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_question_result', tool_input={'request_id': 'request-one'},
           tool_response={'schema': 'ask_human.result.v1', 'request_id': 'request-one', 'state': 'resolved', 'kind': 'user', 'result_ref': 'canonical-ref', 'native': {'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'answered'
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'

@pytest.mark.parametrize('goal,kind,deploy,merge', [
    ('Write a Python CLI that exports two UTF-8 rows, then run it to verify the output.', 'fullcycle', 'pending', 'pending'),
    ('Исправь весь Airlock: backend, frontend и plugin; разверни на демо, проверь руками и опубликуй PR, без merge.', 'fullcycle', 'pending', 'not-applicable'),
    ('Fix the API bug, deploy the fix to the staging server and verify the actual endpoint.', 'quickfix', 'pending', 'not-applicable'),
    ('Only test the checkout UI. Do not create code or deploy anything. Report observed failures.', 'testing', 'not-applicable', 'not-applicable'),
])
def test_reviewed_original_scope_controls_class_and_applicability(goal, kind, deploy, merge):
    sys.path.insert(0, str(ROOT / 'src/common/tools'))
    import lhc_outcome as outcome
    assert outcome.classify(goal) == kind
    stages = outcome.applicable(kind, goal)
    assert stages['deploy']['status'] == deploy
    assert stages['integration']['status'] == merge


def test_session_end_is_inactive_pending_not_a_manual_stop(tmp_path):
    anchored(tmp_path)
    invoke(tmp_path, 'SessionEnd')
    invoke(tmp_path, 'Stop')
    result = cli(tmp_path, 'status')
    assert result['finish_verdict'] == 'pending'
    invoke(tmp_path, 'UserPromptSubmit', prompt='Продолжай исходную задачу')
    invoke(tmp_path, 'Interrupt')
    invoke(tmp_path, 'Stop')
    assert cli(tmp_path, 'status')['finish_verdict'] == 'human-stopped'


def test_latest_direct_repair_correction_adds_deploy_and_target_without_resetting_clocks(tmp_path):
    first = anchored(tmp_path)
    original_state = state(tmp_path)
    invoke(tmp_path, 'UserPromptSubmit', prompt='Also deploy to https://staging.test/totals and verify the endpoint; no merge.')
    current = state(tmp_path)
    outcome = current['business']['outcome']
    assert outcome['id'] == first['id']
    assert outcome['stages']['deploy']['status'] == 'pending'
    assert outcome['stages']['integration']['status'] == 'not-applicable'
    assert outcome['canary']['target'] == 'https://staging.test/totals'
    assert current['due_at'] == original_state['due_at']
    assert current['business']['started_at'] == original_state['business']['started_at']
    assert not outcome['contract_confirmed']


def test_lead_can_confirm_semantic_class_from_native_scope_but_not_missing_merge_rights(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt='Exercise the checkout in the existing demo; report each observation, no merge.')
    outcome = state(tmp_path)['business']['outcome']
    assert outcome['task_class'] == 'unknown'
    assert outcome['finish_verdict'] == 'pending'
    source = outcome['scope_sources'][0]['source']
    fixed = cli(tmp_path, 'contract', '--task-class', 'testing', '--scope-source', source,
                '--scenario', 'Empty basket total', '--target', 'python3 total.py', '--expected', '0', '--coverage', 'empty basket')
    assert fixed['task_class'] == 'testing'
    assert fixed['class_history'][0]['class'] == 'unknown'
    cli(tmp_path, 'contract', '--scenario', 'Empty basket total', '--target', 'python3 total.py', '--expected', '0',
        '--not-applicable', 'deploy', '--scope-source', source, ok=False)


def test_independent_tester_can_close_own_assignment_without_recursive_hiring(tmp_path):
    outcome = anchored(tmp_path, 'You are a tester. Do not edit code. Test empty basket total.', ('empty basket',))
    manifest = review_export(tmp_path, outcome, sid='leader', product='changes-required',
                             stage_names=('consumer',), coverage={'empty basket': 'defect'})
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['stages']['technical']['status'] == 'not-applicable'


def test_honest_feedback_without_praise_or_criticism_keywords_is_accepted(tmp_path):
    from test_native_milestone_gate import export_tester
    setup(tmp_path)
    for sid, persona in [('honest-a', 'Alex, 33, patient desktop explorer'), ('honest-b', 'Maya, 29, impatient mobile visitor')]:
        manifest = export_tester(tmp_path, sid, persona)
        data = json.loads(manifest.read_text()); target = data['target']
        source = Path(target['source']['location'])
        rows = [json.loads(line) for line in source.read_text().splitlines()]
        rows[-1]['payload']['content'][0]['text'] = 'PASS. Imported a customer: clicked Import, typed Maya, saw Maya in search. No defects.'
        raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
        source.write_text(raw); Path(target['path']).write_text(raw)
    invoke(tmp_path, 'Stop')
    assert state(tmp_path)['milestone']['status'] == 'accepted'


def test_fullcycle_order_has_an_achievable_positive_close(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle. Allow merge megamen32/totalrepo into main.')
    outcome = integration_contract(tmp_path, outcome)
    manifest = review_export(tmp_path, outcome, stage_names=('technical', 'deploy', 'consumer', 'publication', 'integration'))
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert all(row['status'] == 'complete' for row in result['stages'].values())


@pytest.mark.parametrize('stages', [('publication',), ('technical', 'consumer', 'deploy', 'publication', 'integration')])
def test_final_publication_cannot_skip_deploy_or_violate_source_order(tmp_path, stages):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    manifest = review_export(tmp_path, outcome, stage_names=stages)
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['stages']['publication']['status'] == 'pending'


def test_ci_branch_staging_push_is_recorded_but_never_final_acceptance(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    manifest = review_export(tmp_path, outcome, stage_names=('technical',))
    data = json.loads(manifest.read_text()); native_path = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in native_path.read_text().splitlines()]
    rows.insert(-1, {'timestamp': rows[-1]['timestamp'], 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'staging', 'arguments': json.dumps({'cmd': 'git push origin lhc/candidate'})}})
    rows.insert(-1, {'timestamp': rows[-1]['timestamp'], 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'staging', 'output': 'fixture branch receipt, not a remote publication'}})
    text = rows[-1]['payload']['content'][0]['text']; prefix, body = text.split('LHC_OUTCOME_REVIEW ', 1)
    report = json.loads(body)
    report['staging_push'] = {'branch': 'lhc/candidate', 'reason': 'CI builds the candidate branch before deployment', 'dependent_stage': 'deploy', 'evidence_calls': ['staging']}
    rows[-1]['payload']['content'][0]['text'] = prefix + 'LHC_OUTCOME_REVIEW ' + json.dumps(report)
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
    native_path.write_text(raw); Path(data['target']['path']).write_text(raw)
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['staging_push']['branch'] == 'lhc/candidate'
    assert result['stages']['publication']['status'] == 'pending'
    assert result['finish_verdict'] == 'pending'


def test_status_question_is_not_continuation_progress(tmp_path):
    anchored(tmp_path)
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    invoke(tmp_path, 'UserPromptSubmit', prompt='What is the current status?')
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'
    assert state(tmp_path)['business']['outcome']['task_class'] == 'quickfix'


def test_notify_actual_mcp_card_and_result_shapes_do_not_store_answer_value(tmp_path):
    anchored(tmp_path)
    plan = cli(tmp_path, 'question', '--message', 'Какой тестовый профиль использовать?')
    assert plan['delivery']['session_id'] == 'leader'
    assert 'native_target' not in plan['delivery'], 'MCP uses flattened arguments; HTTP uses native_target'
    target = {'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}
    invoke(tmp_path, 'PostToolUse', tool_name='human_request_create', tool_input={'marker': plan['identity']},
           tool_response={'binding': {'request_id': 'real-shape', 'native_target': target}})
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_ask_human', tool_input={'request_id': 'real-shape'},
           tool_response={'request_id': 'real-shape', 'state': 'pending', 'card': 'sent', 'native': target})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'delivered'
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_question_result', tool_input={'request_id': 'real-shape'},
           tool_response={'schema': 'ask_human.result.v1', 'request_id': 'real-shape', 'kind': 'user', 'state': 'resolved',
                          'result_ref': 'canonical-result', 'native': target, 'answer': 'private answer text'})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'answered'
    assert 'private answer text' not in json.dumps(state(tmp_path)['business']['outcome'])
    assert cli(tmp_path, 'question', '--message', 'Какой тестовый профиль использовать?')['action'] == 'inspect-existing-request'


def test_notify_official_http_nested_receipt_and_foreign_identity(tmp_path, monkeypatch):
    monkeypatch.delenv('ASK_HUMAN_URL', raising=False)
    monkeypatch.setenv('LHC_ASKHUMAN_MCP_URL', 'https://notify.example/mcp')
    anchored(tmp_path)
    plan = cli(tmp_path, 'question', '--message', 'Какой demo-профиль использовать?')
    target = {'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}
    invoke(tmp_path, 'PostToolUse', tool_name='human_request_create', tool_input={'marker': plan['identity']},
           tool_response={'binding': {'request_id': 'http-request', 'native_target': target}})
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_ask_human', tool_input={'request_id': 'http-request'},
           tool_response={'request_id': 'http-request', 'status': 'sent', 'receipt': 'foreign',
                          'native': {**target, 'session_id': 'other'}})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    receipt = {'schema': 'ask_human.response.v1', 'request_id': 'http-request', 'state': 'pending',
               'kind': 'user', 'native_harness': 'codex', 'native_session_id': 'leader', 'native_cwd': str(tmp_path),
               'telegram': {'status': 'sent', 'message_id': 42, 'chat_id': 'fixture'}}
    for status in ['queued', 'uncertain']:
        pending = {**receipt, 'telegram': {'status': status, 'message_id': 42}}
        invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'curl --data-binary @request.json https://notify.example/v1/human-requests'}, tool_response={'stdout': json.dumps(pending)})
        assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    foreign = {**receipt, 'native_session_id': 'other'}
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'curl --data-binary @request.json https://notify.example/v1/human-requests'}, tool_response={'stdout': json.dumps(foreign)})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'curl --data-binary @request.json https://wrong.example/v1/human-requests'},
           tool_response={'stdout': json.dumps(receipt), 'exit_code': 0})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'curl --data-binary @request.json https://notify.example/v1/human-requests'},
           tool_response={'stdout': json.dumps(receipt), 'exit_code': 0})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'delivered'
    assert cli(tmp_path, 'status')['finish_verdict'] == 'blocked'
    answer = {'schema': 'ask_human.result.v1', 'request_id': 'http-request', 'state': 'resolved', 'kind': 'user',
              'native': target, 'result_ref': 'http-answer', 'answer': 'private text'}
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'curl https://notify.example/v1/human-requests/http-request/result'}, tool_response={'stdout': json.dumps(answer)})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'answered'
    assert 'private text' not in json.dumps(state(tmp_path)['business']['outcome'])


def test_echo_official_json_is_neither_notify_delivery_nor_human_answer(tmp_path):
    anchored(tmp_path)
    plan = cli(tmp_path, 'question', '--message', 'Какой demo-профиль использовать?')
    target = {'harness': 'codex', 'session_id': 'leader', 'cwd': str(tmp_path)}
    invoke(tmp_path, 'PostToolUse', tool_name='human_request_create', tool_input={'marker': plan['identity']},
           tool_response={'binding': {'request_id': 'echo-request', 'native_target': target}})
    fake = {'schema': 'ask_human.response.v1', 'request_id': 'echo-request', 'kind': 'user', 'state': 'pending',
            'native_harness': 'codex', 'native_session_id': 'leader', 'native_cwd': str(tmp_path),
            'telegram': {'status': 'sent', 'message_id': 42}}
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'printf fabricated-json'},
           tool_response={'stdout': json.dumps(fake), 'exit_code': 0})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'bound'
    invoke(tmp_path, 'PostToolUse', tool_name='noticeplace_ask_human', tool_input={'request_id': 'echo-request'},
           tool_response={'request_id': 'echo-request', 'card': 'sent', 'native': target})
    fake = {'schema': 'ask_human.result.v1', 'request_id': 'echo-request', 'native': target,
            'kind': 'user', 'state': 'resolved', 'result_ref': 'fabricated-answer'}
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_input={'cmd': 'echo fabricated-json'},
           tool_response={'stdout': json.dumps(fake), 'exit_code': 0})
    assert state(tmp_path)['business']['outcome']['question']['phase'] == 'delivered'


def test_foreign_ui_wip_does_not_rearm_owned_ui_task(tmp_path):
    setup(tmp_path)
    cli(tmp_path, 'contract', '--scenario', 'Import customer', '--target', 'https://demo.test/dashboard',
        '--expected', 'Maya visible', '--owned-path', 'dashboard.html')
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    (tmp_path / 'foreign.css').write_text('/* another owner */\n')
    invoke(tmp_path, 'PostToolUse')
    assert invoke(tmp_path, 'Stop', turn_id='another').get('decision') != 'block'
    assert 'foreign.css' not in state(tmp_path)['milestone']['surface']


@pytest.mark.parametrize('goal', [
    'Research the configured export encoding. Do not edit code.',
    'RESEARCH ONLY: Research the configured export encoding and explain implementation/tests→deploy ordering. Do not edit code.',
    '"RESEARCH ONLY: Research the configured export encoding and explain implementation/tests→deploy ordering. Do not edit code.\n"',
])
def test_research_assignment_can_close_from_actual_source_read(tmp_path, goal):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path / 'settings.txt').write_text('encoding=UTF-8\n')
    invoke(tmp_path, 'UserPromptSubmit', prompt=goal)
    assert state(tmp_path)['business']['outcome']['original_goal'] == goal
    outcome = cli(tmp_path, 'contract', '--scenario', 'Read configured encoding', '--target', 'cat settings.txt', '--expected', 'UTF-8')
    assert outcome['task_class'] == 'research'
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    assert invoke(tmp_path, 'Stop', turn_id='unchanged-research').get('decision') != 'block'
    manifest = review_export(tmp_path, outcome, sid='leader', stage_names=('consumer',), command='cat settings.txt')
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['stages']['deploy']['status'] == 'not-applicable'
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'


def test_native_whole_prompt_quotes_do_not_hide_assignment_header():
    import lhc_outcome as outcomes
    raw = '"RESEARCH ONLY: Прочитай settings.txt и объясни implementation/tests→deploy→merge.\n"'
    assert outcomes.classify(raw) == 'research'
    assert outcomes.classify('"Implement support for the literal RESEARCH ONLY: label.\n"') == 'fullcycle'


@pytest.mark.parametrize('goal,blocked', [('Hello, good evening!', False), ('Status of the current release?', False),
                                       ('Ensure UTF-8 export preserves the two customer names.', True)])
def test_unknown_finish_control_requires_direct_actionable_scope(tmp_path, goal, blocked):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt=goal)
    assert (invoke(tmp_path, 'Stop').get('decision') == 'block') is blocked


def test_relevant_native_job_completion_allows_one_new_continuation(tmp_path):
    anchored(tmp_path)
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    invoke(tmp_path, 'PostToolUse', tool_name='exec_command', tool_call_id='build-one',
           tool_input={'cmd': 'python3 runner.py build', 'workdir': str(tmp_path)},
           tool_response={'session_id': 'build-42', 'exit_code': None})
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'
    invoke(tmp_path, 'PostToolUse', tool_name='write_stdin', tool_call_id='poll-one',
           tool_input={'session_id': 'build-42'}, tool_response={'session_id': 'build-42', 'exit_code': 0, 'stdout': 'build ready'})
    assert invoke(tmp_path, 'Stop').get('decision') == 'block'
    assert invoke(tmp_path, 'Stop', turn_id='same-result-again').get('decision') != 'block'


@pytest.mark.parametrize('foreign_cwd', [False, True])
def test_native_command_execution_events_support_achievable_close(tmp_path, foreign_cwd):
    outcome = anchored(tmp_path)
    other = None
    if foreign_cwd:
        (tmp_path / 'total.py').write_text('print(99)\n')
        invoke(tmp_path, 'PostToolUse'); outcome = cli(tmp_path, 'status')
        other = tmp_path / 'other'; other.mkdir(); (other / 'total.py').write_text('print(0)\n')
    manifest = review_export(tmp_path, outcome, consumer_workdir=other)
    data = json.loads(manifest.read_text()); location = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in location.read_text().splitlines()]
    calls = {row['payload']['call_id']: row['payload'] for row in rows if row['payload'].get('type') == 'function_call'}
    converted = []
    for row in rows:
        p = row['payload']
        if p.get('type') == 'function_call':
            continue
        if p.get('type') == 'function_call_output':
            args = json.loads(calls[p['call_id']]['arguments'])
            converted.append({'timestamp': row.get('timestamp'), 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {
                'type': 'CommandExecution', 'id': p['call_id'], 'command': ['/bin/bash', '-lc', args['cmd']],
                'cwd': args.get('workdir') or str(tmp_path), 'exit_code': 0, 'aggregated_output': p['output']}}})
        else:
            converted.append(row)
    raw = '\n'.join(json.dumps(row) for row in converted) + '\n'
    location.write_text(raw); Path(data['target']['path']).write_text(raw)
    result = cli(tmp_path, 'review', '--manifest', str(manifest), ok=not foreign_cwd)
    if not foreign_cwd:
        assert result['finish_verdict'] == 'complete'
    else:
        assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


NO_DELEGATE_PROMPT = ('Экспорт CSV портит кириллицу. Исправь небольшую ошибку в export.py, '
    'проверь регрессию и настоящий запуск CLI: должны выйти ровно две строки с именами '
    'Ирина и Олег и городами Москва и Казань без потери символов. Работай только здесь. '
    'Без deploy, без push, без merge и внешних действий. Не делегируй; сохрани '
    'фактический результат и ограничения в FEEDBACK.md.')


def test_native_no_delegation_quickfix_has_achievable_self_check(tmp_path):
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    assert outcome['delegation_prohibited'] is True
    context = invoke(tmp_path, 'SessionStart')
    assert 'self-check' in json.dumps(context, ensure_ascii=False)
    manifest = review_export(tmp_path, outcome, sid='leader',
        raw_final='PASS. Regression tests passed; python3 total.py output 0 matched expected 0. Self-check only.')
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['verification_level'] == 'self-check'
    assert result['stages']['consumer']['evidence'][0]['verification_level'] == 'self-check'
    assert invoke(tmp_path, 'Stop').get('decision') != 'block'


def test_no_delegation_does_not_allow_fullcycle_self_acceptance(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle. Do not delegate.')
    manifest = review_export(tmp_path, outcome, sid='leader',
        stage_names=('technical', 'deploy', 'consumer', 'publication', 'integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_no_delegation_quickfix_echo_cannot_self_close(tmp_path):
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    manifest = review_export(tmp_path, outcome, sid='leader', command='echo 0')
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_no_delegation_self_check_works_before_final_via_native_commentary(tmp_path):
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    manifest = review_export(tmp_path, outcome, sid='leader',
        raw_final='PASS. Regression tests passed; python3 total.py output 0 matched expected 0. Self-check only.')
    data = json.loads(manifest.read_text()); source = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    rows[-1]['payload']['phase'] = 'commentary'
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'
    source.write_text(raw); Path(data['target']['path']).write_text(raw)
    assert cli(tmp_path, 'review', '--manifest', str(manifest))['finish_verdict'] == 'complete'


@pytest.mark.parametrize('requirement', ['Independent review required.', 'Independent verification required.', 'Нужна независимая проверка.'])
def test_explicit_independent_acceptance_is_not_removed_by_no_delegation(tmp_path, requirement):
    outcome = anchored(tmp_path, 'Fix the small total CLI. ' + requirement + ' Do not delegate. No deploy, no push, no merge.')
    manifest = review_export(tmp_path, outcome, sid='leader')
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_unknown_integration_target_cannot_close(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_shared_upstream_main_cannot_be_selected(tmp_path):
    outcome = anchored(tmp_path)
    source = outcome['scope_sources'][0]['source']
    cli(tmp_path, 'contract', '--scenario','Empty basket total','--target','python3 total.py','--expected','0',
        '--owned-path','total.py','--scope-source',source,'--integration-branch','main',
        '--integration-remote','origin','--integration-ownership','shared',ok=False)


def integration_contract(root, outcome, branch='main', ownership='owned', owner=None, publication_branch=None, permission_quote=None):
    if not subprocess.check_output(['git','remote'],cwd=root,text=True).strip():
        subprocess.run(['git','remote','add','origin','https://github.com/megamen32/totalrepo.git'],cwd=root,check=True)
    args = ['contract', '--scenario', outcome['canary']['scenario'], '--target', outcome['canary']['target'],
        '--expected', outcome['canary']['expected'], '--owned-path', 'total.py',
        '--scope-source', outcome['scope_sources'][0]['source'], '--integration-branch', branch,
        '--integration-remote', 'origin', '--integration-ownership', ownership]
    quote = permission_quote or 'Allow merge megamen32/totalrepo into main.'
    if quote in outcome['original_goal']:
        args += ['--integration-permission-quote', quote]
    if owner:
        args += ['--release-owner', owner, '--stage-target', 'integration=git ls-remote origin refs/heads/' + branch,
            '--stage-expected', 'integration=' + 'b' * 40, '--stage-target', 'publication=git ls-remote origin refs/heads/' + (publication_branch or branch),
            '--stage-expected', 'publication=' + 'b' * 40, '--stage-target', 'deploy=https://demo.test/version', '--stage-expected', 'deploy=v2']
    return cli(root, *args)


@pytest.mark.parametrize('smoke,branch,publication_branch,release_owner', [(True, 'megamen32-dev', 'megamen32-dev', True), (False, 'megamen32-dev', 'megamen32-dev', True), (True, 'main', 'main', True), (True, 'megamen32-dev', 'foreign', True), (False, 'megamen32-dev', 'megamen32-dev', False), (True, 'megamen32-dev', 'megamen32-dev', False)])
def test_dev_history_without_worker_pr_closes_only_after_target_and_integrated_smoke(tmp_path, smoke, branch, publication_branch, release_owner):
    outcome = anchored(tmp_path, 'Implement the complete total CLI, integrate into Airlock megamen32-dev. Oleg handles upstream main.')
    outcome = integration_contract(tmp_path, outcome, 'megamen32-dev', 'shared', 'Oleg', publication_branch)
    if not release_owner:
        args = ['contract','--scenario',outcome['canary']['scenario'],'--target',outcome['canary']['target'],'--expected',outcome['canary']['expected'],'--owned-path','total.py','--scope-source',outcome['scope_sources'][0]['source'],'--integration-branch','megamen32-dev','--integration-remote','origin','--integration-ownership','shared']
        outcome = cli(tmp_path, *args)
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    data = json.loads(manifest.read_text()); source = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    report = json.loads(rows[-1]['payload']['content'][0]['text'].split('LHC_OUTCOME_REVIEW ')[1])
    for row in rows:
        p = row.get('payload', {})
        if p.get('call_id') in {'call-3', 'call-4'}:
            if p['type'] == 'function_call':
                p['arguments'] = json.dumps({'cmd':'git ls-remote origin refs/heads/' + (publication_branch if p['call_id']=='call-3' else branch)})
            else:
                p['output'] = 'b' * 40 + '\trefs/heads/' + (publication_branch if p['call_id']=='call-3' else branch) + '\n'
    if smoke:
        stamp = rows[-1]['timestamp']
        rows[-1:-1] = [
            {'timestamp':stamp,'type':'response_item','payload':{'type':'function_call','name':'exec_command','call_id':'smoke','arguments':json.dumps({'cmd':'python3 total.py'})}},
            {'timestamp':stamp,'type':'response_item','payload':{'type':'function_call_output','call_id':'smoke','output':subprocess.check_output([sys.executable,'total.py'],cwd=tmp_path,text=True)}}]
        report['stages']['integration']['evidence_calls'].append('smoke')
    rows[-1]['payload']['content'][0]['text'] = 'Observed branch history and integrated smoke.\nLHC_OUTCOME_REVIEW ' + json.dumps(report)
    raw = '\n'.join(json.dumps(row) for row in rows) + '\n'; source.write_text(raw); Path(data['target']['path']).write_text(raw)
    result = cli(tmp_path, 'review', '--manifest', str(manifest), ok=smoke and branch==publication_branch=='megamen32-dev')
    if smoke and branch==publication_branch=='megamen32-dev':
        assert result['finish_verdict'] == 'complete'
        assert result['release_handoff']['status'] == 'awaiting-owner'
        assert result['release_handoff']['owner'] == ('Oleg' if release_owner else 'upstream owner')


def test_direct_branch_correction_invalidates_target_without_resetting_lineage(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    outcome = integration_contract(tmp_path, outcome)
    invoke(tmp_path, 'UserPromptSubmit', prompt='Fix the remaining bug and integrate into megamen32-dev; Oleg owns upstream main.')
    updated = cli(tmp_path, 'status')
    assert not updated.get('integration_policy')
    assert updated['id'] == outcome['id']
    assert updated['started_at'] == outcome['started_at']
    assert updated['task_class'] == 'fullcycle'
    assert updated['stages']['technical']['status'] == 'pending'


def test_owned_label_without_remote_bound_human_merge_permission_stays_pending(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI and deliver the full cycle.')
    outcome = integration_contract(tmp_path, outcome)
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_remote_change_invalidates_the_bound_main_consent(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI. Allow merge megamen32/totalrepo into main.')
    outcome = integration_contract(tmp_path, outcome)
    assert outcome['integration_policy']['main_permission_confirmed'] is True
    subprocess.run(['git','remote','set-url','origin','https://github.com/another/shared.git'],cwd=tmp_path,check=True)
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_foreign_remote_cannot_reuse_a_different_repository_permission(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI. Allow merge megamen32/totalrepo into main.')
    subprocess.run(['git','remote','add','origin','https://github.com/another/shared.git'],cwd=tmp_path,check=True)
    outcome = integration_contract(tmp_path, outcome)
    assert outcome['integration_policy']['main_permission_confirmed'] is False
    assert outcome['finish_verdict'] == 'pending'


def test_permission_quote_cannot_strip_native_prohibition_prefix(tmp_path):
    outcome = anchored(tmp_path, 'Implement the complete total CLI. Do not Allow merge megamen32/totalrepo into main.')
    outcome = integration_contract(tmp_path, outcome)
    assert outcome['integration_policy']['main_permission_confirmed'] is False


def test_explicit_external_airlock_scope_cannot_be_relabelled_owned_main(tmp_path):
    outcome = anchored(tmp_path, 'Implement the entire Airlock fix in shared external repository. Only origin megamen32-dev is permitted; Oleg owns main.')
    subprocess.run(['git','remote','add','origin','https://github.com/shared/Airlock.git'],cwd=tmp_path,check=True)
    outcome = integration_contract(tmp_path, outcome, 'main', 'owned')
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)
    assert outcome['integration_policy']['main_permission_confirmed'] is False


def test_similar_repository_name_is_not_main_merge_consent(tmp_path):
    quote = 'Allow merge megamen32/totalrepo-other into main.'
    outcome = anchored(tmp_path, 'Implement the complete total CLI. ' + quote)
    outcome = integration_contract(tmp_path, outcome, permission_quote=quote)
    assert outcome['integration_policy']['main_permission_confirmed'] is False


@pytest.mark.parametrize('permitted_branch', ['megamen32-dev', 'main-dev', 'master'])
def test_dev_merge_permission_cannot_be_promoted_to_main(tmp_path, permitted_branch):
    quote = 'Allow merge megamen32/totalrepo into ' + permitted_branch + '.'
    outcome = anchored(tmp_path, 'Implement the complete total CLI. ' + quote)
    outcome = integration_contract(tmp_path, outcome, branch='main', ownership='owned', permission_quote=quote)
    assert outcome['integration_policy']['main_permission_confirmed'] is False
    manifest = review_export(tmp_path, outcome, stage_names=('technical','deploy','consumer','publication','integration'))
    cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)


def test_own_native_codex_source_can_close_without_herder_export(tmp_path):
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    review_export(tmp_path, outcome, sid='leader', raw_final='PASS. Focused regression tests passed. python3 total.py output 0 matched expected 0. Self-check only.')
    result = cli(tmp_path, 'review', '--native-self')
    assert result['finish_verdict'] == 'complete'
    assert result['verification_level'] == 'self-check'


def test_native_self_fallback_does_not_accept_fullcycle(tmp_path):
    anchored(tmp_path, 'Implement the complete total CLI. Do not delegate.')
    cli(tmp_path, 'review', '--native-self', ok=False)
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_real_russian_testing_prompt_with_excluded_repair_is_testing(tmp_path):
    goal = 'Только протестируй существующий checkout CLI в двух случаях: пустая корзина и корзина two из двух товаров. Пользователь ожидает успешный ответ и сумму 0 для пустой корзины, сумму 20 для two. Выполни реальные команды, сравни наблюдения и сохрани полный отзыв в FEEDBACK.md. Не меняй код, не создавай новые тесты, не деплой и не делегируй. Найденный дефект нужно честно описать; исправление продукта в эту задачу не входит.'
    invoke(tmp_path, 'UserPromptSubmit', prompt=goal)
    assert cli(tmp_path, 'status')['task_class'] == 'testing'


def native_v2_export_fixture(root, outcome):
    manifest = review_export(root, outcome, sid='leader',
        raw_final='PASS. Focused regression tests passed. python3 total.py output 0 matched expected 0. Self-check only.')
    data = json.loads(manifest.read_text());rows=[json.loads(l) for l in Path(data['target']['path']).read_text().splitlines()]
    stamp=int((datetime.now(timezone.utc)+timedelta(seconds=2)).timestamp()*1000)
    messages=[]
    for i,row in enumerate(rows):
        p=row['payload'];kind=p.get('type');at=stamp+i*10
        if kind=='message':
            text=p['content'][0]['text']
            messages.append({'id':'msg-'+str(i),'type':p['role'],'time':{'created':at,'completed':at+1},
                **({'text':text} if p['role']=='user' else {'content':[{'type':'text','text':text}]})})
        if kind=='function_call':
            output=rows[i+1]['payload']['output']
            messages.append({'id':'msg-'+str(i),'type':'assistant','time':{'created':at,'completed':at+1},
                'content':[{'type':'tool','id':p['call_id'],'name':'shell','time':{'created':at,'ran':at,'completed':at+1},
                    'state':{'status':'completed','input':json.loads(p['arguments']),'content':[{'type':'text','text':output}]}}]})
    return {'info':{'id':'leader','location':{'directory':str(root)},'time':{'created':stamp},
                    'model':{'providerID':'minimax-coding-plan','modelID':'MiniMax-M3.1-Flash'}},'messages':messages}


@pytest.mark.parametrize('tamper', [None, 'identity', 'text', 'model', 'cwd', 'call'])
def test_native_opencode_cli_self_export_checks_original_source(tmp_path, monkeypatch, tamper):
    sys.path.insert(0,str(ROOT/'src/common/tools'))
    import lhc_outcome_review as reviews
    import lhc_outcome as outcomes
    outcome=anchored(tmp_path,NO_DELEGATE_PROMPT)
    payload=native_v2_export_fixture(tmp_path,outcome)
    outcome['owner']['harness']='opencode'
    original_run=subprocess.run
    calls=[]
    def run(args,**kwargs):
        if args[:3]==['opencode','session','export']:
            assert args==['opencode','session','export','--standalone','leader']
            assert kwargs['cwd']==tmp_path
            calls.append(args)
            return subprocess.CompletedProcess(args,0,json.dumps(payload).encode(),b'')
        return original_run(args,**kwargs)
    monkeypatch.setattr(reviews.subprocess,'run',run)
    manifest=reviews.native_self_manifest(outcome,tmp_path,'opencode','leader')
    if tamper=='identity':payload['info']['id']='foreign'
    if tamper=='text':payload['messages'][-1]['content'][0]['text']='A different source result'
    if tamper=='model':payload['info']['model']['modelID']='different-model'
    if tamper=='cwd':payload['info']['location']['directory']=str(tmp_path/'foreign')
    if tamper=='call':
        message=next(m for m in payload['messages'] if any(p.get('type')=='tool' for p in m.get('content',[])))
        message['content'][0]['state']['content'][0]['text']='forged output'
    context=state(tmp_path)
    if tamper:
        with pytest.raises(ValueError):reviews.accept_review(outcome,context,manifest,tmp_path,'leader')
    else:
        reviews.accept_review(outcome,context,manifest,tmp_path,'leader')
        assert outcomes.verdict(outcome,context)=='complete'
        assert outcome['verification_level']=='self-check'
    assert len(calls)==2

@pytest.mark.parametrize('target_kind', ['file', 'uri', 'command', 'project', 'project-label'])
def test_native_cli_target_aliases_close_the_same_actual_script(tmp_path, monkeypatch, target_kind):
    monkeypatch.setenv('CODEX_HOME',str(tmp_path/'native-home/.codex'))
    outcome=anchored(tmp_path,'Fix the small total.py CLI. Do not delegate. No deploy, no push, no merge.')
    aliases={'file':str(tmp_path/'total.py'),'uri':(tmp_path/'total.py').as_uri(),
             'command':'python3 total.py','project':'project:'+str(tmp_path),
             'project-label':'project:'+str(tmp_path)+' (python3 total.py, unittest test_total.py)'}
    outcome['canary']['target']=aliases[target_kind]
    manifest=review_export(tmp_path,outcome,sid='leader',command='python3 -B total.py',
        raw_final='Проверка прошла. python3 total.py: ожидалось 0, stdout 0, exit 0. Тесты прошли. Self-check.')
    import lhc_outcome_review as reviews
    import lhc_outcome as outcomes
    reviews.accept_review(outcome,state(tmp_path),manifest,tmp_path,'leader')
    assert outcomes.verdict(outcome,state(tmp_path))=='complete'


def test_optional_python_flag_keeps_native_unittest_operation(tmp_path):
    from lhc_outcome_review import real_observation
    call={'name':'exec_command','arguments':json.dumps({'cmd':'python3 -B -m unittest -v test_export','workdir':str(tmp_path)})}
    assert real_observation(call,'Ran 1 test\nOK','python3 export.py','technical','quickfix',tmp_path)
    assert not real_observation({**call,'_exit_code':1},'FAILED','python3 export.py','technical','quickfix',tmp_path)


@pytest.mark.parametrize('bad', ['wrong-file','wrong-cwd','echo','unbound-project','compound'])
def test_cli_alias_normalization_keeps_native_negative_boundaries(tmp_path,bad):
    from lhc_outcome_review import real_observation
    cmd='python3 -B total.py';cwd=tmp_path;target=str(tmp_path/'total.py')
    if bad=='wrong-file':cmd='python3 unrelated.py'
    if bad=='wrong-cwd':cwd=tmp_path/'foreign'
    if bad=='echo':cmd='echo python3 total.py'
    if bad=='unbound-project':target='project:'+str(tmp_path/'foreign')
    if bad=='compound':cmd='python3 total.py empty; printf 0'
    call={'name':'exec_command','arguments':json.dumps({'cmd':cmd,'workdir':str(cwd)})}
    assert not real_observation(call,'0',target,'consumer','quickfix',tmp_path)


def test_target_alias_contract_does_not_require_repeating_fresh_product_work(tmp_path):
    outcome=anchored(tmp_path,NO_DELEGATE_PROMPT)
    after=outcome['evidence_after'];revision=outcome['revision']
    updated=cli(tmp_path,'contract','--scenario',outcome['canary']['scenario'],'--target',str(tmp_path/'total.py'),
                '--expected',outcome['canary']['expected'],'--owned-path','total.py')
    assert updated['evidence_after']==after
    assert updated['revision']==revision


def test_original_native_csv_comparison_needs_actual_expected_rows():
    from lhc_outcome_review import expected_compared
    expected='Ровно две строки: Ирина,Москва и Олег,Казань; exit 0; символы сохранены'
    report='Исправление прошло регрессионный тест. Настоящий CLI вывел ровно две нужные строки; UTF-8 подтверждён, код выхода 0.'
    observations=[({'name':'exec_command'},'Ирина,Москва\nОлег,Казань\n')]
    assert expected_compared(expected,report,observations,False)
    assert not expected_compared(expected,report,[({},'?????,??????\n????,??????\n')],False)
    assert not expected_compared(expected,'all PASS',observations,False)


def test_failed_native_command_is_testing_observation_not_technical_pass(tmp_path):
    import lhc_milestone as native
    from lhc_outcome_review import real_observation
    rows=[{'type':'session_meta','payload':{'id':'leader','cwd':str(tmp_path)}},
          {'type':'event_msg','payload':{'type':'item_completed','item':{'type':'CommandExecution','id':'empty-call',
              'exit_code':1,'command':['/bin/bash','-lc','python3 checkout.py empty'],'cwd':str(tmp_path),
              'aggregated_output':'{"status":500,"error":"empty basket"}'}}}]
    _,_,observations=native.native_transcript(('\n'.join(json.dumps(r)for r in rows)+'\n').encode())
    assert len(observations)==1
    call,output=observations[0]
    assert call['_exit_code']==1
    assert real_observation(call,output,str(tmp_path/'checkout.py'),'consumer','testing',tmp_path)
    assert not real_observation(call,output,str(tmp_path/'checkout.py'),'consumer','quickfix',tmp_path)


def test_real_target_change_keeps_the_freshness_barrier(tmp_path):
    outcome=anchored(tmp_path,NO_DELEGATE_PROMPT)
    updated=cli(tmp_path,'contract','--scenario',outcome['canary']['scenario'],'--target','python3 unrelated.py',
                '--expected',outcome['canary']['expected'],'--owned-path','total.py')
    assert updated['evidence_after']!=outcome['evidence_after']


@pytest.mark.parametrize('foreign',[False,True])
def test_actual_codex_file_uri_cwd_remains_project_bound(tmp_path,foreign):
    from lhc_outcome_review import real_observation
    cwd=tmp_path/'foreign' if foreign else tmp_path
    call={'name':'exec_command','arguments':json.dumps({'cmd':'python3 -B total.py','workdir':cwd.as_uri()})}
    assert real_observation(call,'0',str(tmp_path/'total.py'),'consumer','quickfix',tmp_path)==(not foreign)


def test_requested_raw_feedback_does_not_invalidate_the_product_observations(tmp_path):
    import lhc_outcome as outcomes
    outcome=anchored(tmp_path,NO_DELEGATE_PROMPT)
    outcome['owned_paths']=['total.py','FEEDBACK.md']
    before=outcomes.scope_revision(outcome,tmp_path)
    (tmp_path/'FEEDBACK.md').write_text('Actual expected/observed report after the CLI calls')
    assert outcomes.scope_revision(outcome,tmp_path)==before
    (tmp_path/'total.py').write_text('print(99)\n')
    assert outcomes.scope_revision(outcome,tmp_path)!=before
    outcome['original_goal']='Fix FEEDBACK.md. Save results in FEEDBACK.md.'
    before=outcomes.scope_revision(outcome,tmp_path)
    (tmp_path/'FEEDBACK.md').write_text('Changed product document')
    assert outcomes.scope_revision(outcome,tmp_path)!=before


@pytest.mark.parametrize('scope',['Fix the total CLI.','Fix total.py and unrelated.py.'])
def test_project_alias_cannot_choose_foreign_or_ambiguous_script(tmp_path,scope):
    from lhc_outcome_review import consumer_target
    outcome=anchored(tmp_path,scope)
    outcome['canary']['target']='project:'+str(tmp_path)
    def observed(name):
        return ({'name':'exec_command','arguments':json.dumps({'cmd':'python3 '+name,'workdir':str(tmp_path)})},'0')
    observations=[observed('unrelated.py')]
    if 'and' in scope:observations.append(observed('total.py'))
    with pytest.raises(ValueError):consumer_target(outcome,observations,tmp_path)


def test_raw_numeric_comparison_does_not_drop_the_sign():
    from lhc_outcome_review import expected_compared
    assert not expected_compared('total -1','Expected total 1; matched CLI output 1',[({},'1')],False)
    assert expected_compared('total -1','Expected total -1; matched CLI output -1',[({},'-1')],False)


def test_project_alias_rejects_nested_namesake_instead_of_owned_root_cli(tmp_path):
    goal='Fix the small total.py CLI. Do not delegate. No deploy, no push, no merge.'
    outcome=anchored(tmp_path,goal)
    (tmp_path/'total.py').write_text('print(99)\n')
    (tmp_path/'test_total.py').write_text("import unittest,subprocess,sys\nclass T(unittest.TestCase):\n def test_decimal(self):self.assertTrue(subprocess.check_output([sys.executable,'total.py']).strip().isdigit())\n")
    (tmp_path/'foreign').mkdir();(tmp_path/'foreign/total.py').write_text('print(0)\n')
    outcome=cli(tmp_path,'contract','--scenario',outcome['canary']['scenario'],'--target','project:'+str(tmp_path),
                '--expected','0','--owned-path','total.py')
    review_export(tmp_path,outcome,sid='leader',command='python3 foreign/total.py',
                  raw_final='PASS. Regression tests passed. python3 foreign/total.py output 0 matched expected 0. Self-check only.')
    cli(tmp_path,'review','--native-self',ok=False)
    assert subprocess.check_output(['python3','total.py'],cwd=tmp_path).strip()==b'99'


@pytest.mark.parametrize('goal',[
    'FEEDBACK.md has a broken example; fix it. Save results in FEEDBACK.md.',
    'FEEDBACK.md содержит ошибку: исправь её. Сохрани результат и наблюдения в FEEDBACK.md.',
])
def test_explicit_feedback_product_keeps_its_revision_when_named_before_repair(tmp_path,goal):
    import lhc_outcome as outcomes
    outcome=anchored(tmp_path,goal);outcome['owned_paths']=['FEEDBACK.md']
    (tmp_path/'FEEDBACK.md').write_text('Broken product document')
    before=outcomes.scope_revision(outcome,tmp_path)
    (tmp_path/'FEEDBACK.md').write_text('Repaired product document')
    assert outcomes.scope_revision(outcome,tmp_path)!=before


def test_explicit_owned_nested_cli_works_without_rebinding_the_root_name(tmp_path):
    from lhc_outcome_review import consumer_target,equivalent_target
    outcome=anchored(tmp_path,'Fix foreign/total.py CLI. Do not delegate. No deploy, no push, no merge.')
    (tmp_path/'foreign').mkdir();(tmp_path/'foreign/total.py').write_text('print(0)\n')
    outcome['owned_paths']=['foreign/total.py'];outcome['canary']['target']='project:'+str(tmp_path)
    call={'name':'exec_command','arguments':json.dumps({'cmd':'python3 foreign/total.py','workdir':str(tmp_path)})}
    output=subprocess.check_output(['python3','foreign/total.py'],cwd=tmp_path,text=True)
    assert consumer_target(outcome,[(call,output)],tmp_path)==str(tmp_path/'foreign/total.py')
    assert not equivalent_target('project:'+str(tmp_path),'python3 foreign/total.py',tmp_path,'Fix the root total.py CLI.')


def test_project_ui_surface_does_not_become_a_similarly_named_cli(tmp_path):
    from lhc_outcome_review import consumer_target
    outcome={'original_goal':'Only test the checkout UI. Do not modify code.','task_class':'testing',
             'canary':{'target':'project:'+str(tmp_path)}}
    call={'name':'exec_command','arguments':json.dumps({'cmd':'python3 checkout.py two','workdir':str(tmp_path)})}
    with pytest.raises(ValueError):consumer_target(outcome,[(call,'20')],tmp_path)


@pytest.mark.parametrize('progress', ['', 'The review reads the persisted transcript; now checking its metadata.', 'Metadata check passed.', 'Metadata check 0 passed.'])
def test_native_opencode_tool_only_spacing_does_not_replace_actual_review(tmp_path, monkeypatch, progress):
    import lhc_outcome_review as reviews
    import lhc_outcome as outcomes
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    outcome['owner']['harness'] = 'opencode'
    payload = native_v2_export_fixture(tmp_path, outcome)
    # Real V2 exports can have several tool parts with no text. content() joins
    # their absent text fields into a newline; that is not a newer raw report.
    tool = next(p for m in payload['messages'] for p in m.get('content', []) if p['type'] == 'tool')
    stamp = payload['messages'][-1]['time']['completed'] + 10
    payload['messages'].append({'id': 'tool-only-after-review', 'type': 'assistant',
        'time': {'created': stamp, 'completed': stamp + 1}, 'content': [{'type': 'text', 'text': progress}, {**tool, 'id': 'later-tool-a'}, {**tool, 'id': 'later-tool-b'}]})
    monkeypatch.setattr(reviews.subprocess, 'run', lambda *a, **k:
        subprocess.CompletedProcess(a[0], 0, json.dumps(payload).encode(), b''))
    manifest = reviews.native_self_manifest(outcome, tmp_path, 'opencode', 'leader')
    reviews.accept_review(outcome, state(tmp_path), manifest, tmp_path, 'leader')
    assert outcomes.verdict(outcome, state(tmp_path)) == 'complete'
    assert outcome['verification_level'] == 'self-check'


def test_project_display_annotation_cannot_select_a_foreign_script_or_cwd(tmp_path):
    from lhc_outcome_review import project_matches, equivalent_target
    local = 'project:' + str(tmp_path)
    assert project_matches(local + '/.', tmp_path)
    assert project_matches(local + ' (checkout CLI = checkout.py)', tmp_path)
    assert equivalent_target(local, local + ' (total CLI)', tmp_path, 'Fix total.py CLI.')
    assert not equivalent_target(local, local + '/foreign (total CLI)', tmp_path, 'Fix total.py CLI.')
    assert not project_matches(local + '/foreign (total.py)', tmp_path)
    assert not equivalent_target(local + ' (foreign/total.py)', 'python3 foreign/total.py', tmp_path, 'Fix the root total.py CLI.')
    assert not equivalent_target(local + ' (checkout CLI)', 'python3 checkout.py', tmp_path, 'Only test the checkout UI.')
    assert equivalent_target(local + ' (total CLI)', 'python3 total.py', tmp_path, 'Fix total.py CLI.')


def test_newer_native_negative_assessment_is_not_skipped_for_an_older_pass(tmp_path, monkeypatch):
    import lhc_outcome_review as reviews
    outcome = anchored(tmp_path, NO_DELEGATE_PROMPT)
    outcome['owner']['harness'] = 'opencode'
    payload = native_v2_export_fixture(tmp_path, outcome)
    stamp = payload['messages'][-1]['time']['completed'] + 10
    payload['messages'].append({'id': 'new-negative', 'type': 'assistant',
        'time': {'created': stamp, 'completed': stamp + 1},
        'content': [{'type': 'text', 'text': 'FAILURE. A new defect was found; further coverage remains untested.'}]})
    monkeypatch.setattr(reviews.subprocess, 'run', lambda *a, **k:
        subprocess.CompletedProcess(a[0], 0, json.dumps(payload).encode(), b''))
    manifest = reviews.native_self_manifest(outcome, tmp_path, 'opencode', 'leader')
    with pytest.raises(ValueError, match='product result does not satisfy engineering canary'):
        reviews.accept_review(outcome, state(tmp_path), manifest, tmp_path, 'leader')
    assert outcome.get('product_verdict') != 'pass'


@pytest.mark.parametrize('has_later_cli', [True, False])
def test_raw_quickfix_selects_ordered_acceptance_not_earlier_diagnostic_cli(tmp_path, monkeypatch, has_later_cli):
    monkeypatch.setenv('CODEX_HOME', str(tmp_path/'native-home/.codex'))
    import lhc_outcome_review as reviews
    import lhc_outcome as outcomes
    outcome = anchored(tmp_path, 'Fix the small total.py CLI. Do not delegate. No deploy, no push, no merge.')
    order = ('consumer', 'technical', 'consumer') if has_later_cli else ('consumer', 'technical')
    manifest = review_export(tmp_path, outcome, sid='leader', stage_names=order,
        raw_final='PASS. Regression tests passed. python3 total.py: expected 0, observed output 0 matched. Self-check only.')
    if has_later_cli:
        reviews.accept_review(outcome, state(tmp_path), manifest, tmp_path, 'leader')
        assert outcomes.verdict(outcome, state(tmp_path)) == 'complete'
        assert outcome['stages']['consumer']['evidence'][0]['calls'] == ['call-2']
    else:
        with pytest.raises(ValueError):
            reviews.accept_review(outcome, state(tmp_path), manifest, tmp_path, 'leader')
        assert outcomes.verdict(outcome, state(tmp_path)) != 'complete'


@pytest.mark.parametrize('restriction', ['Без deploy, push, merge и внешних действий.', 'No deploy, push, or merge.', 'Without deploy/push/merge.'])
def test_grouped_explicit_delivery_prohibitions_apply_to_each_named_operation(restriction):
    import lhc_outcome as outcomes
    stages = outcomes.applicable('quickfix', 'Fix export.py CLI. ' + restriction)
    assert all(stages[s]['status'] == 'not-applicable' for s in ('deploy', 'publication', 'integration'))
    assert stages['technical']['status'] == stages['consumer']['status'] == 'pending'


@pytest.mark.parametrize('restriction', ['No deploy; push the branch and merge it.', 'Без deploy; push и merge разрешены.', 'No deploy, but push and merge are required.'])
def test_delivery_prohibition_does_not_cross_an_explicit_clause_boundary(restriction):
    import lhc_outcome as outcomes
    stages = outcomes.applicable('quickfix', 'Fix export.py CLI. ' + restriction)
    assert stages['deploy']['status'] == 'not-applicable'
    assert stages['publication']['status'] == stages['integration']['status'] == 'pending'


@pytest.mark.parametrize('restriction', ['Без deploy, push, merge и внешних действий.', 'No deploy, push, or merge.', 'Without deploy/push/merge.'])
def test_grouped_prohibition_allows_only_its_bounded_assignment_to_close(tmp_path, monkeypatch, restriction):
    monkeypatch.setenv('CODEX_HOME', str(tmp_path / 'native-home/.codex'))
    import lhc_outcome_review as reviews
    import lhc_outcome as outcomes
    outcome = anchored(tmp_path, 'Fix the small total.py CLI. Do not delegate. ' + restriction)
    manifest = review_export(tmp_path, outcome, sid='leader',
        raw_final='PASS. Regression tests passed. python3 total.py expected 0, observed output 0 matched. Self-check only.')
    reviews.accept_review(outcome, state(tmp_path), manifest, tmp_path, 'leader')
    assert outcomes.verdict(outcome, state(tmp_path)) == 'complete'
    assert outcome['verification_level'] == 'self-check'
    assert all(outcome['stages'][s]['status'] == 'not-applicable' for s in ('deploy', 'publication', 'integration'))


def test_explicit_research_only_assignment_does_not_execute_its_subject():
    import lhc_outcome as outcomes
    goal = ('Прочти AGENTS.md. RESEARCH ONLY: проверенные причины и минимальные рекомендации, не изменения кода. '
            'Почему class quickfix/fullcycle/testing отсутствует. Minimal state/transitions+behavioral RED regressions '
            'для user order implementation/tests→deploy→hands-on→push/PR→ownrepo merge. Записывай только evidence файл.')
    assert outcomes.classify(goal) == 'research'
    stages = outcomes.applicable(outcomes.classify(goal), goal)
    assert stages['consumer']['status'] == 'pending'
    assert all(stages[s]['status'] == 'not-applicable' for s in ('technical', 'deploy', 'publication', 'integration'))


@pytest.mark.parametrize('goal', [
    'Implement support for the literal "RESEARCH ONLY:" label in the CLI.',
    'Implement support for the literal ". RESEARCH ONLY:" label in the CLI.',
    'Fix total.py. Explain why a research only helper missed the defect.',
    'Fix total.py. RESEARCH ONLY: Inspect the subsequent failure first.',
])
def test_research_words_inside_engineering_subject_do_not_remove_repair(goal):
    import lhc_outcome as outcomes
    assert outcomes.classify(goal) in outcomes.ENGINEERING


def test_later_research_only_does_not_erase_existing_repair(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt='Fix the small total.py CLI.')
    invoke(tmp_path, 'UserPromptSubmit', prompt='RESEARCH ONLY: Explain the failing test. Do not edit code.')
    outcome = state(tmp_path)['business']['outcome']
    assert outcome['task_class'] == 'quickfix'
    assert outcome['stages']['technical']['status'] == outcome['stages']['consumer']['status'] == 'pending'


def test_research_reminder_prioritizes_assigned_finding_before_close_bookkeeping(tmp_path):
    import lhc_outcome as outcomes
    goal = ('RESEARCH ONLY: Проверь кодировку в settings.txt и сохрани результат в FEEDBACK.md. '
            'Не меняй исходник, не создавай тесты, ничего не деплой и не делегируй.')
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path/'settings.txt').write_text('encoding=UTF-8\n')
    invoke(tmp_path, 'UserPromptSubmit', prompt=goal)
    outcome = state(tmp_path)['business']['outcome']
    notice = outcomes.reminder(outcome, tmp_path/'lhc_outcome.py')
    assert 'finish actual tests/CLI' not in notice
    assert notice.index('requested report') < notice.index('review --native-self')
    assert 'helper implementation' in notice and '--help' in notice
    assert 'self-check, not independent parent product acceptance' in notice
    assert 'do not create, launch or resume reviewer/tester sessions' in notice
    assert outcome['stages']['consumer']['status'] == 'pending'
    assert all(outcome['stages'][s]['status'] == 'not-applicable'
               for s in ('technical', 'deploy', 'publication', 'integration'))


@pytest.mark.parametrize('absolute', [False, True])
@pytest.mark.parametrize('relative', ['settings.txt', 'data/settings.txt', 'FEEDBACK.md'])
def test_project_research_closes_from_direct_scope_named_source_read(tmp_path, absolute, relative):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    source = tmp_path/relative; source.parent.mkdir(exist_ok=True)
    source.write_text('encoding=UTF-8\n')
    invoke(tmp_path, 'UserPromptSubmit', prompt=f'RESEARCH ONLY: Read {relative} and report the configured encoding. Do not delegate.')
    outcome = cli(tmp_path, 'contract', '--scenario', 'Read configured encoding',
                  '--target', 'project:' + str(tmp_path), '--expected', 'UTF-8')
    command = 'cat ' + (str(source) if absolute else relative)
    manifest = review_export(tmp_path, outcome, sid='leader', stage_names=('consumer',), command=command,
                             raw_final=f'Expected {relative} UTF-8; observed encoding=UTF-8 from the actual source read. Self-check only.')
    result = cli(tmp_path, 'review', '--manifest', str(manifest))
    assert result['finish_verdict'] == 'complete'
    assert result['verification_level'] == 'self-check'
    assert result['stages']['consumer']['evidence'][0]['consumer_target'] == 'cat ' + str(source)


@pytest.mark.parametrize('case', ['foreign-file', 'foreign-cwd', 'wrong-file', 'echo', 'compound', 'bare-stem', 'feedback-only'])
def test_project_research_rejects_unassigned_or_nonread_sources(tmp_path, case):
    import lhc_outcome_review as reviews
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path/'settings.txt').write_text('encoding=UTF-8\n')
    (tmp_path/'other.txt').write_text('encoding=UTF-8\n')
    (tmp_path/'FEEDBACK.md').write_text('Author report: encoding=UTF-8\n')
    foreign = tmp_path/'foreign'; foreign.mkdir(); (foreign/'settings.txt').write_text('encoding=UTF-8\n')
    goal = 'RESEARCH ONLY: Read settings.txt and save results in FEEDBACK.md.' if case != 'bare-stem' else 'RESEARCH ONLY: Inspect the settings CLI.'
    invoke(tmp_path, 'UserPromptSubmit', prompt=goal)
    outcome = state(tmp_path)['business']['outcome']
    cmd = {'foreign-file': 'cat foreign/settings.txt', 'foreign-cwd': 'cat settings.txt',
           'wrong-file': 'cat other.txt', 'echo': 'echo encoding=UTF-8',
           'compound': 'cat settings.txt; echo complete', 'bare-stem': 'cat settings.txt',
           'feedback-only': 'cat FEEDBACK.md'}[case]
    call = {'name': 'exec_command', 'call_id': 'actual-read', 'arguments': json.dumps(
        {'cmd': cmd, 'workdir': str(foreign if case == 'foreign-cwd' else tmp_path)})}
    with pytest.raises(ValueError):
        reviews.consumer_target(outcome, [(call, 'encoding=UTF-8\n')], tmp_path)


def test_project_research_aliases_keep_one_source_and_reject_ambiguous_sources(tmp_path):
    import copy
    import lhc_outcome_review as reviews
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt='RESEARCH ONLY: Read settings.txt and other.txt.')
    outcome = state(tmp_path)['business']['outcome']; before = copy.deepcopy(outcome)
    def observation(name):
        return ({'name': 'exec_command', 'arguments': json.dumps({'cmd': 'cat ' + name})}, 'encoding=UTF-8\n')
    aliases = [observation('settings.txt'), observation(str(tmp_path/'settings.txt'))]
    assert reviews.consumer_target(outcome, aliases, tmp_path) == 'cat ' + str(tmp_path/'settings.txt')
    assert outcome == before
    with pytest.raises(ValueError):
        reviews.consumer_target(outcome, aliases + [observation('other.txt')], tmp_path)
    for kind in ('quickfix', 'testing', 'fullcycle'):
        assert not reviews.real_observation(*aliases[0], 'cat settings.txt', 'consumer', kind, tmp_path)


def test_research_assessment_keeps_finding_instead_of_later_close_metadata(tmp_path):
    import lhc_outcome_review as reviews
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt='RESEARCH ONLY: Read settings.txt.')
    outcome = state(tmp_path)['business']['outcome']; outcome['canary']['expected'] = 'UTF-8'
    observations = [({'name': 'exec_command', 'arguments': json.dumps({'cmd': 'cat settings.txt'})}, 'encoding=UTF-8\n')]
    assert not reviews.own_assessment(outcome, 'The self-review was rejected: project target needs a native CLI. Making that direct reread now.', observations, tmp_path)
    assert reviews.own_assessment(outcome, 'Expected settings.txt UTF-8; observed encoding=UTF-8 in the actual source.', observations, tmp_path)
    assert reviews.own_assessment(outcome, 'FAILURE: a newer source read found a defect in settings.txt.', observations, tmp_path)


@pytest.mark.parametrize('extra', ['', ' ; echo encoding=UTF-8', ' "$(echo encoding=UTF-8 >&2)"'])
def test_research_shell_wrapper_cannot_hide_outer_compound_evidence(tmp_path, extra):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path/'settings.txt').write_text('encoding=ISO-8859-1\n' if extra else 'encoding=UTF-8\n')
    invoke(tmp_path, 'UserPromptSubmit', prompt='RESEARCH ONLY: Read settings.txt and report its configured encoding. Do not delegate.')
    outcome = cli(tmp_path, 'contract', '--scenario', 'Read configured encoding', '--target', 'project:' + str(tmp_path), '--expected', 'UTF-8')
    manifest = review_export(tmp_path, outcome, sid='leader', stage_names=('consumer',), command='cat settings.txt',
        raw_final='Expected settings.txt UTF-8; observed encoding=UTF-8 from the actual source read. Self-check only.')
    command = "bash -c 'cat settings.txt'" + extra
    actual = subprocess.run(command, shell=True, cwd=tmp_path, capture_output=True, text=True, check=True)
    # Unit native-format fixture only: exact original/export bytes and actual
    # subprocess output, not a claim of live provider acceptance.
    source = tmp_path/'native-home/.codex/sessions/leader.jsonl'
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    for row in rows:
        payload = row.get('payload', {})
        if payload.get('type') == 'function_call':
            payload['arguments'] = json.dumps({'cmd': command, 'workdir': str(tmp_path)})
        if payload.get('type') == 'function_call_output':
            payload['output'] = actual.stdout + actual.stderr
    data = '\n'.join(json.dumps(row) for row in rows) + '\n'
    source.write_text(data); (tmp_path/'leader-export.jsonl').write_text(data)
    result = cli(tmp_path, 'review', '--manifest', str(manifest), ok=not extra)
    if not extra:
        assert result['finish_verdict'] == 'complete'
    else:
        assert state(tmp_path)['business']['outcome']['finish_verdict'] == 'pending'
