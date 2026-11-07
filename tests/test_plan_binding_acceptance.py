"""A plan's acceptance must come from its own confirmed contract and review."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_plan_control as control
import lhc_plan_json as plans
import lhc_outcome as outcomes
import lhc_time_guard as guard


@pytest.fixture
def case(tmp_path, monkeypatch):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    monkeypatch.setenv('LHC_PLAN_MIRROR_CONFIG', str(tmp_path / 'no-mirror'))
    monkeypatch.setenv('CODEX_HOME', str(tmp_path / 'native-home/.codex'))
    monkeypatch.delenv('CODEX_THREAD_ID', raising=False)
    monkeypatch.delenv('LHC_MCP_ACTOR_CONTEXT', raising=False)
    plan = tmp_path / '.agents/tasks/plan-B'
    (plan / 'leaves').mkdir(parents=True)
    metadata = {'goal': 'Fix the new total CLI', 'deliverable': 'implementation',
                'business_result': 'Empty basket returns zero',
                'acceptance_scenarios': ['Run the new total CLI']}
    (plan / 'plan.json').write_text(json.dumps(metadata))
    (plan / 'leaves/L1.json').write_text(json.dumps({'id': 'L1', 'label': 'Fix B', 'status': 'queued'}))
    journal = tmp_path / 'native-home/.codex/sessions/leader.jsonl'
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 'leader', 'cwd': str(tmp_path)}}) + '\n')
    old = {'id': 'goal-A', 'task_class': 'quickfix', 'contract_confirmed': True,
           'original_goal': 'Fix the old total CLI', 'latest_correction': 'Fix the old total CLI',
           'owner': {'harness': 'codex', 'session_id': 'leader'}, 'cwd': str(tmp_path),
           'native_source': str(journal), 'started_at': (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
           'canary': {'scenario': 'Old output', 'target': 'python3 old.py', 'expected': 'A', 'status': 'complete'},
           'owned_paths': [], 'sources': [], 'coverage': [],
           'stages': {key: {'status': 'complete' if key in {'technical', 'consumer'} else 'not-applicable'}
                      for key in outcomes.STAGES}}
    assert outcomes.verdict(old, {'business': {'outcome': old}}) == 'complete'
    state_path = guard.learning_path(tmp_path, 'codex', 'leader')
    guard.write_state(state_path, {'business': {'outcome': copy.deepcopy(old)}})
    return tmp_path, plan, state_path, old


def cli(tool, *args):
    run = subprocess.run([sys.executable, str(TOOLS / (tool + '.py')), *map(str, args)],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def activate(plan):
    return cli('lhc_plan_json', 'activate', plan, 'L1', '--session', 'leader', '--harness', 'codex')


def test_activation_never_adopts_complete_A_acceptance(case):
    root, plan, path, old = case
    result = activate(plan)
    assert result['goal_binding']['goal_status'] != 'accepted'
    saved = guard.load_state(path)['business']['outcome']
    assert saved['original_goal'] == old['original_goal']
    assert saved['canary'] == old['canary'] and saved['stages'] == old['stages']
    assert not saved['plan_binding'].get('acceptance_fingerprint')
    again = activate(plan)
    assert again['goal_binding']['goal_status'] != 'accepted'
    assert guard.load_state(path)['business']['outcome'].get('plan_binding_history') == saved.get('plan_binding_history')


@pytest.mark.parametrize('field,value', [
    ('business_result', 'All tenants succeed without data loss'),
    ('business_results', ['All tenants succeed', 'No data loss']),
    ('acceptance_scenarios', ['All tenants survive failover']),
    ('acceptance_scenario', 'All tenants survive failover'),
])
def test_canonical_requirement_change_invalidates_acceptance(case, field, value):
    root, plan, path, old = case
    first = plans.plan_metadata(plan)
    old['finish_verdict'] = 'complete'
    old['plan_binding'] = control.binding(first, old, plan, accepted=True)
    assert control.evaluate(first, [], old, plan_dir=plan)['goal_status'] == 'accepted'
    changed = {**first, field: value}
    assert control.plan_scope(first) != control.plan_scope(changed)
    assert control.evaluate(changed, [], old, plan_dir=plan)['goal_status'] != 'accepted'


def test_operational_progress_and_same_binding_keep_acceptance(case):
    root, plan, path, old = case
    activate(plan)
    state = guard.load_state(path)
    outcome = state['business']['outcome']
    metadata = plans.plan_metadata(plan)
    outcome['plan_binding'] = control.binding(metadata, outcome, plan, accepted=True)
    outcome['finish_verdict'] = 'complete'
    guard.write_state(path, state)
    before = copy.deepcopy(outcome['plan_binding'])
    changed = {**metadata, 'current_progress': 'Half done', 'updated_at': '2026-11-08T00:00:00Z',
               'slots': 8, 'estimate_policy': {'leaf_cap_minutes': 30, 'reason': 'fixture'}}
    assert control.plan_scope(changed) == control.plan_scope(metadata)
    (plan / 'plan.json').write_text(json.dumps(changed))
    assert activate(plan)['goal_binding']['goal_status'] == 'accepted'
    assert guard.load_state(path)['business']['outcome']['plan_binding'] == before


def test_contract_work_review_accepts_B_without_manual_rebind(case):
    from _inprocess_lane import review_export_manifest
    root, plan, path, old = case
    (root / 'total.py').write_text('print(0)\n')
    (root / 'test_total.py').write_text(
        'import unittest, subprocess, sys\nclass Totals(unittest.TestCase):\n'
        ' def test_total(self): self.assertEqual(subprocess.check_output([sys.executable, "total.py"]).strip(), b"0")\n')
    assert activate(plan)['goal_binding']['goal_status'] != 'accepted'
    args = ['--cwd', root, '--runtime', 'codex', '--session-id', 'leader']
    confirmed = cli('lhc_outcome', *args, 'contract', '--scenario', 'New empty basket',
                    '--target', 'python3 total.py', '--expected', '0', '--owned-path', 'total.py')
    assert confirmed['canary']['scenario'] == 'New empty basket'
    assert confirmed['stages']['technical']['status'] == 'pending'
    assert control.resolve_control(plan)['goal_status'] == 'unaccepted'
    manifest = review_export_manifest(root, confirmed)
    reviewed = cli('lhc_outcome', *args, 'review', '--manifest', manifest)
    assert reviewed['finish_verdict'] == 'complete'
    assert reviewed['verification_level'] == 'independent-review'
    assert control.resolve_control(plan)['goal_status'] == 'accepted'
    assert activate(plan)['goal_binding']['goal_status'] == 'accepted'
    # The previous outcome evidence remains identifiable after contract B.
    history = reviewed['plan_binding_history']
    assert any(row['outcome']['canary'] == old['canary'] for row in history)


def test_other_plan_activation_retains_A_binding_until_normal_contract(case):
    root, plan, path, old = case
    first = root / '.agents/tasks/plan-A'
    (first / 'leaves').mkdir(parents=True)
    metadata = {'goal': old['original_goal'], 'deliverable': 'implementation'}
    (first / 'plan.json').write_text(json.dumps(metadata))
    (first / 'leaves/A.json').write_text(json.dumps(
        {'id': 'A', 'status': 'done', 'session': 'leader', 'harness': 'codex'}))
    old['finish_verdict'] = 'complete'
    accepted_A = control.binding(metadata, old, first, accepted=True)
    old['plan_binding'] = copy.deepcopy(accepted_A)
    guard.write_state(path, {'business': {'outcome': old}})
    assert activate(plan)['goal_binding']['goal_status'] == 'unknown'
    saved = guard.load_state(path)['business']['outcome']
    assert saved['plan_binding'] == accepted_A
    assert saved['plan_binding_request']['plan_dir'] == str(plan)
    assert control.resolve_control(first)['goal_status'] == 'accepted'
    assert control.resolve_control(plan)['goal_status'] == 'unknown'
    activate(plan)
    assert len(guard.load_state(path)['business']['outcome']['plan_binding_history']) == 1


def test_schema_aliases_normalize_and_human_stop_survives_binding(case):
    root, plan, path, old = case
    assert control.plan_scope({'acceptance_scenario': 'Run B'}) == control.plan_scope(
        {'acceptance_scenarios': ['Run B']})
    state = guard.load_state(path)
    state['native_entry'] = {'finish_hold': 'HumanStop'}
    guard.write_state(path, state)
    assert activate(plan)['goal_binding']['goal_status'] != 'accepted'
    saved = guard.load_state(path)
    assert saved['native_entry']['finish_hold'] == 'HumanStop'
    assert outcomes.verdict(saved['business']['outcome'], saved) == 'blocked'
