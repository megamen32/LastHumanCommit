"""The ordinary public contract starts only its verified pending native goal."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_time_guard as guard


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    monkeypatch.setenv('CODEX_HOME', str(tmp_path / 'native-home/.codex'))
    monkeypatch.setenv('CODEX_THREAD_ID', 'bootstrap-owner')
    monkeypatch.setenv('LHC_PLAN_MIRROR_CONFIG', str(tmp_path / 'no-mirror'))
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    monkeypatch.delenv('LHC_MCP_ACTOR_CONTEXT', raising=False)
    journal = tmp_path / 'native-home/.codex/sessions/bootstrap-owner.jsonl'
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({'type': 'session_meta', 'payload': {
        'id': 'bootstrap-owner', 'cwd': str(tmp_path)}}) + '\n' + json.dumps({
        'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
        'content': [{'type': 'input_text', 'text': 'Verify the local total CLI for the assigned empty basket.'}]}}) + '\n')
    return tmp_path, journal, guard.learning_path(tmp_path, 'codex', 'bootstrap-owner')


def run(root, command, *extra, session='bootstrap-owner', runtime='codex'):
    return subprocess.run([sys.executable, str(TOOLS / 'lhc_outcome.py'), '--cwd', str(root),
                           '--runtime', runtime, '--session-id', session, command, *map(str, extra)],
                          capture_output=True, text=True, timeout=20)


def contract(root, *, kind='quickfix', **kw):
    args = ['--task-class', kind, '--scenario', 'Empty basket total',
            '--target', 'python3 total.py', '--expected', '0']
    if kind in {'quickfix', 'fullcycle'}:
        args += ['--owned-path', 'total.py']
    if kind == 'testing':
        args += ['--coverage', 'empty basket']
    return run(root, 'contract', *args, **kw)


@pytest.mark.parametrize('timer_exists', [False, True])
def test_public_contract_bootstraps_without_hidden_hook_or_state_seed(fresh, timer_exists):
    root, journal, state_path = fresh
    (root / 'total.py').write_text('print(0)\n')
    assert not state_path.exists()
    if timer_exists:
        # Simulate an existing ordinary time-only observation, not a business outcome.
        guard.native_heartbeat(root, 'codex', 'bootstrap-owner')
    before = copy.deepcopy(guard.load_state(state_path))
    result = contract(root)
    assert result.returncode == 0, result.stderr
    outcome = json.loads(result.stdout)
    assert outcome['finish_verdict'] == 'pending'
    assert outcome['owner'] == {'harness': 'codex', 'session_id': 'bootstrap-owner'}
    assert outcome['cwd'] == str(root) and outcome['native_source'] == str(journal)
    assert outcome['product_verdict'] == 'not-tested'
    assert not outcome.get('sources') and not outcome.get('plan_binding')
    assert all(row['status'] in {'pending', 'not-applicable'} for row in outcome['stages'].values())
    saved = guard.load_state(state_path)
    assert 'native_entry' not in saved and 'milestone' not in saved
    if before:
        assert saved['native_heartbeat'] == before['native_heartbeat']
    assert contract(root).returncode == 0
    repeated = guard.load_state(state_path)['business']['outcome']
    for key in ('id', 'started_at', 'evidence_after', 'bootstrap', 'stages'):
        assert repeated[key] == outcome[key]


def test_status_never_creates_state(fresh):
    root, journal, state_path = fresh
    assert run(root, 'status').returncode == 1
    assert not state_path.exists() and not state_path.with_suffix('.lock').exists()


@pytest.mark.parametrize('failure', ['missing-current', 'foreign-session', 'wrong-cwd',
    'wrong-runtime', 'subagent', 'missing-journal', 'missing-input', 'missing-class', 'status-class', 'invalid-contract'])
def test_rejected_bootstrap_never_writes_an_outcome(fresh, monkeypatch, failure):
    root, journal, state_path = fresh
    (root / 'total.py').write_text('print(0)\n')
    target = root
    kw = {}
    if failure == 'missing-current':
        monkeypatch.delenv('CODEX_THREAD_ID')
    elif failure == 'foreign-session':
        monkeypatch.setenv('CODEX_THREAD_ID', 'another-owner')
    elif failure == 'wrong-cwd':
        target = root / 'other'
        target.mkdir()
    elif failure == 'wrong-runtime':
        kw['runtime'] = 'opencode'
    elif failure == 'subagent':
        rows = journal.read_text().splitlines()
        header = json.loads(rows[0])
        header['payload']['parent_thread_id'] = 'unverified-parent'
        journal.write_text(json.dumps(header) + '\n' + '\n'.join(rows[1:]) + '\n')
    elif failure == 'missing-journal':
        journal.unlink()
    elif failure == 'missing-input':
        journal.write_text(journal.read_text().splitlines()[0] + '\n')
    if failure == 'missing-class':
        result = run(target, 'contract', '--scenario', 'Check', '--target', 'project:' + str(root), '--expected', 'Result')
    elif failure == 'invalid-contract':
        result = run(target, 'contract', '--task-class', 'quickfix', '--scenario', 'Check',
                     '--target', 'project:' + str(root), '--expected', 'Result')  # no owned path
    else:
        result = contract(target, kind='status' if failure == 'status-class' else 'quickfix', **kw)
    assert result.returncode != 0
    for runtime in ('codex', 'opencode'):
        path = guard.learning_path(target, runtime, 'bootstrap-owner')
        assert not path.exists(), result.stdout


@pytest.mark.parametrize('hold', ['HumanStop', 'SessionEnd', 'permission_declined'])
def test_bootstrap_cannot_reopen_held_or_closed_timer_state(fresh, hold):
    root, journal, state_path = fresh
    guard.native_heartbeat(root, 'codex', 'bootstrap-owner')
    state = guard.load_state(state_path)
    state['native_entry'] = {'finish_hold': hold}
    guard.write_state(state_path, state)
    before = state_path.read_bytes()
    assert contract(root).returncode != 0
    assert state_path.read_bytes() == before


def test_existing_outcome_identity_mismatch_is_not_reset(fresh):
    root, journal, state_path = fresh
    (root / 'total.py').write_text('print(0)\n')
    assert contract(root).returncode == 0
    state = guard.load_state(state_path)
    state['business']['outcome']['owner']['session_id'] = 'foreign-owner'
    guard.write_state(state_path, state)
    before = state_path.read_bytes()
    assert contract(root).returncode != 0
    assert state_path.read_bytes() == before


def test_public_contract_work_review_with_no_manual_outcome_seed(fresh):
    from _inprocess_lane import review_export_manifest
    root, journal, state_path = fresh
    (root / 'total.py').write_text('print(0)\n')
    (root / 'test_total.py').write_text(
        'import unittest, subprocess, sys\nclass Totals(unittest.TestCase):\n'
        ' def test_total(self): self.assertEqual(subprocess.check_output([sys.executable, "total.py"]).strip(), b"0")\n')
    confirmed = contract(root)
    assert confirmed.returncode == 0, confirmed.stderr
    outcome = json.loads(confirmed.stdout)
    assert outcome['finish_verdict'] == 'pending'
    manifest = review_export_manifest(root, outcome)
    reviewed = run(root, 'review', '--manifest', manifest)
    assert reviewed.returncode == 0, reviewed.stderr
    accepted = json.loads(reviewed.stdout)
    assert accepted['finish_verdict'] == 'complete'
    assert accepted['verification_level'] == 'independent-review'
    assert contract(root).returncode == 0
    again = json.loads(run(root, 'status').stdout)
    for key in ('id', 'started_at', 'evidence_after', 'stages', 'bootstrap'):
        assert again[key] == accepted[key]


@pytest.mark.parametrize('kind', ['testing', 'research', 'fullcycle'])
def test_explicit_classes_bootstrap_only_pending(fresh, kind):
    root, journal, state_path = fresh
    (root / 'total.py').write_text('print(0)\n')
    result = contract(root, kind=kind)
    assert result.returncode == 0, result.stderr
    outcome = json.loads(result.stdout)
    assert outcome['task_class'] == kind and outcome['finish_verdict'] == 'pending'
    assert outcome['bootstrap']['scope_origin'] == 'unknown'
    assert not outcome['scope_sources']  # the CLI declaration is not native human authorization
    assert outcome['stages']['consumer']['status'] == 'pending'
    if kind == 'fullcycle':
        assert all(row['status'] == 'pending' for row in outcome['stages'].values())


def test_existing_time_and_input_lineage_survive_bootstrap_and_next_checkpoint(fresh):
    from argparse import Namespace
    root, journal, state_path = fresh
    guard.native_heartbeat(root, 'codex', 'bootstrap-owner')
    state = guard.load_state(state_path)
    state['business'] = {'runtime': 'codex', 'original_prompt': 'Original bounded request',
                         'latest_prompt': 'Latest bounded correction', 'transcript_path': str(journal)}
    original_clock = {key: value for key, value in state.items() if key != 'business'}
    guard.write_state(state_path, state)
    result = contract(root, kind='testing')
    assert result.returncode == 0, result.stderr
    saved = guard.load_state(state_path)
    assert saved['business']['original_prompt'] == 'Original bounded request'
    assert saved['business']['outcome']['original_goal'] == 'Original bounded request'
    assert saved['business']['outcome']['latest_correction'] == 'Latest bounded correction'
    assert {key: saved[key] for key in original_clock} == original_clock
    # Explicit startup creates the clock fields the next ordinary hook expects,
    # while making no claim that a native hook already ran.
    checkpoint = guard.learning_checkpoint(Namespace(runtime='codex', now=None), root, 'bootstrap-owner')
    assert checkpoint['state'] == str(state_path)


def test_fresh_contract_preserves_actual_native_input_not_canary_text(fresh):
    root, journal, state_path = fresh
    result = contract(root, kind='testing')
    assert result.returncode == 0, result.stderr
    outcome = json.loads(result.stdout)
    assert outcome['original_goal'] == 'Verify the local total CLI for the assigned empty basket.'
    assert outcome['original_goal'] != outcome['canary']['scenario']
    assert outcome['bootstrap']['native_input']['journal_path'] == str(journal)
    assert outcome['bootstrap']['scope_origin'] == 'unknown'


@pytest.mark.parametrize('fact', ['timer-runtime', 'timer-session', 'prior-native-id'])
def test_conflicting_existing_native_facts_are_not_repaired_by_bootstrap(fresh, fact):
    root, journal, state_path = fresh
    guard.native_heartbeat(root, 'codex', 'bootstrap-owner')
    state = guard.load_state(state_path)
    if fact == 'timer-runtime':
        state['native_heartbeat']['runtime'] = 'opencode'
    elif fact == 'timer-session':
        state['native_heartbeat']['session_id'] = 'another-owner'
    else:
        state['business'] = {'native_identity': {'verified': True, 'native_id': 'another-owner',
            'logical_session_id': 'bootstrap-owner', 'native_cwd': str(root)}}
    guard.write_state(state_path, state)
    before = state_path.read_bytes()
    result = contract(root, kind='testing')
    assert result.returncode != 0, 'conflicting native state was silently adopted'
    assert state_path.read_bytes() == before


def test_incomplete_prior_identity_stays_unknown_without_fabricated_repair(fresh):
    root, journal, state_path = fresh
    guard.native_heartbeat(root, 'codex', 'bootstrap-owner')
    state = guard.load_state(state_path)
    unknown = {'verified': False, 'native_id': None, 'reason': 'historical identity unavailable'}
    state['business'] = {'native_identity': unknown.copy()}
    guard.write_state(state_path, state)
    result = contract(root, kind='testing')
    assert result.returncode == 0, result.stderr
    saved = guard.load_state(state_path)
    assert saved['business']['native_identity'] == unknown
    assert saved['business']['outcome']['finish_verdict'] == 'pending'
