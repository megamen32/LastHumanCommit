import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'F/src/common/tools'))
import lhc_plan_control as control
import lhc_plan_json as plans
import lhc_outcome as outcome_module
import lhc_time_guard as guard

def completed_goal_a(root):
    return {'id': 'goal-A', 'task_class': 'research', 'contract_confirmed': True,
            'original_goal': 'Explain the old configuration A',
            'latest_correction': 'Explain the old configuration A',
            'owner': {'session_id': 'review-fixture-lead', 'harness': 'codex'}, 'cwd': str(root),
            'canary': {'scenario': 'Read configuration A', 'target': 'project:A', 'expected': 'Explain A'},
            'stages': {key: {'status': 'complete' if key == 'technical' else 'not-applicable'}
                for key in ('technical', 'deploy', 'consumer', 'publication', 'integration')}}

def setup(tmp_path, monkeypatch):
    subprocess.run(['git', 'init', '--quiet', str(tmp_path)], check=True)
    (tmp_path / '.agents').mkdir()
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    monkeypatch.setenv('LHC_PLAN_MIRROR_CONFIG', str(tmp_path / 'absent'))
    monkeypatch.delenv('CODEX_THREAD_ID', raising=False)
    plan = tmp_path / '.agents/tasks/goal-B'
    (plan / 'leaves').mkdir(parents=True)
    (plan / 'plan.json').write_text(json.dumps({'goal': 'Build and deploy a new application B',
        'deliverable': 'implementation', 'business_result': 'B serves users',
        'acceptance_scenarios': ['B responds to a real request']}))
    (plan / 'leaves/L1.json').write_text(json.dumps({'id': 'L1', 'status': 'done',
        'session': 'review-fixture-lead', 'harness': 'codex'}))
    plans.record_session_plan('review-fixture-lead', plan, 'L1')
    return plan

def test_completed_goal_a_does_not_accept_different_plan_b(tmp_path, monkeypatch):
    plan = setup(tmp_path, monkeypatch)
    outcome = completed_goal_a(tmp_path)
    state = {'business': {'outcome': outcome}}
    assert outcome_module.verdict(outcome, state) == 'complete'
    path = guard.learning_path(tmp_path, 'codex', 'review-fixture-lead')
    assert path.is_relative_to(tmp_path)
    guard.write_state(path, state)
    result = control.bind_session_plan(plan, 'review-fixture-lead', tmp_path, 'codex')
    print('bind goal A to B:', json.dumps(result))
    assert result['goal_status'] != 'accepted', 'completed research A accepted implementation goal B'

def test_current_acceptance_scenarios_and_business_result_invalidate_scope():
    first = {'goal': 'Deliver product', 'deliverable': 'implementation',
        'business_result': 'Handle one request', 'acceptance_scenarios': ['one request succeeds']}
    changed = {**first, 'business_result': 'Handle all tenants without losing data',
        'acceptance_scenarios': ['tenant isolation and failover succeed']}
    assert control.plan_scope(first) != control.plan_scope(changed), 'canonical acceptance fields omitted from fingerprint'

def test_changed_snapshot_scope_cannot_reuse_accepted_projection():
    spec = importlib.util.spec_from_file_location('review_v_catalog', ROOT / 'V/src/common/tools/lhc_plan_catalog.py')
    catalog = importlib.util.module_from_spec(spec); spec.loader.exec_module(catalog)
    from datetime import datetime, timezone
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    doc = {'goal': 'Original goal A', 'tasks': [{'id': 'L1', 'status': 'done'}],
        'goal_control': {'goal_status': 'accepted', 'fingerprint': 'a'*64,
            'source': {'kind': 'native_outcome', 'session_id': 'old-lead', 'outcome_id': 'A',
                'source_fingerprint': 'b'*64}}}
    doc['goal'] = 'A new, unverified goal B'
    entry = {'snapshot': {'project': 'test', 'name': 'plan', 'document': doc,
        'last_file_event': now.isoformat()}}
    result = catalog.summarize(entry, now)
    print('changed projection:', result['state'], result['goal_status'], result['stage'])
    assert result['goal_status'] != 'accepted', 'opaque cached fields accept changed snapshot goal'
