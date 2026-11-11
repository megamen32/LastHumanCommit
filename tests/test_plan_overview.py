# LHC:COVERS src/common/tools/lhc_plan_json.py src/common/tools/lhc_plan_mcp.py src/common/tools/lhc_entry.py src/common/skills/plan/SKILL.md src/common/skills/last-human-commit/SKILL.md
import json
import os
from pathlib import Path
import subprocess
import sys

from _inprocess import load_module

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'src/common/tools'
mcp = load_module(TOOLS / 'lhc_plan_mcp.py', name='plan_overview_mcp')
entry = load_module(TOOLS / 'lhc_entry.py', name='plan_overview_entry')


def fixture_plan(tmp_path, flat=False):
    plan = tmp_path / 'plan'
    (plan / 'leaves').mkdir(parents=True)
    (plan / 'plan.json').write_text(json.dumps({'title': 'Release plan', 'goal': 'Deliver working hooks', 'summary': 'First restore; then verify; finally release.'}))
    rows = [
        {'id': 'M01', 'kind': 'milestone', 'label': 'Restore hooks', 'status': 'queued'},
        {'id': 'L01', 'parent': 'M01', 'label': 'Repair', 'status': 'done', 'result': 'Repaired'},
        {'id': 'M02', 'kind': 'milestone', 'label': 'Verify hooks', 'status': 'queued'},
        {'id': 'L02', 'parent': 'M02', 'label': 'Check', 'status': 'running', 'progress_events': [{'note': 'Current evidence'}]},
        {'id': 'M03', 'kind': 'milestone', 'label': 'Release package', 'status': 'queued'},
    ]
    if flat:
        rows = [{'id': 'L01', 'label': 'Flat task', 'status': 'running', 'progress_events': [{'note': 'Flat note'}]}]
    for row in rows:
        (plan / 'leaves' / (row['id'] + '.json')).write_text(json.dumps(row))
    return plan


def contents(plan):
    return {p.relative_to(plan): p.read_bytes() for p in plan.rglob('*') if p.is_file()}


def test_cli_and_mcp_show_full_saved_overview_read_only(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    plan = fixture_plan(tmp_path)
    before = contents(plan)
    cli = subprocess.run([sys.executable, str(TOOLS / 'lhc_plan_json.py'), 'show', str(plan), '--current', 'L02'], capture_output=True, text=True, env=os.environ.copy())
    assert cli.returncode == 0, cli.stderr
    result = mcp.show_plan({'plan_dir': str(plan), 'current': ['L02']})
    assert not result['isError']
    for text in (cli.stdout, result['content'][0]['text']):
        for expected in ('Release plan', 'Deliver working hooks', 'First restore; then verify; finally release.',
                         'M01 «Restore hooks» — done', 'M02 «Verify hooks» — running', 'M03 «Release package» — queued',
                         'Now:', 'Current evidence', 'Done:', 'Repaired'):
            assert expected in text
        assert text.index('M01 «Restore hooks»') < text.index('M02 «Verify hooks»') < text.index('M03 «Release package»') < text.index('Done:')
    assert contents(plan) == before


def test_flat_plan_remains_compatible(tmp_path):
    plan = fixture_plan(tmp_path, flat=True)
    result = mcp.show_plan({'plan_dir': str(plan), 'current': ['L01']})
    assert not result['isError']
    text = result['content'][0]['text']
    assert 'Flat task' in text and 'Flat note' in text


def test_resume_prioritizes_current_before_long_overview(tmp_path, monkeypatch):
    plan = fixture_plan(tmp_path)
    metadata = json.loads((plan / 'plan.json').read_text())
    metadata['summary'] = 'Long saved overview ' * 140
    (plan / 'plan.json').write_text(json.dumps(metadata))
    monkeypatch.setattr(entry, '_plan_entry', lambda *args: {'continuation': {'plan': str(plan), 'leaf': 'L02'}})
    monkeypatch.setattr(entry, '_goal_frontier_context', lambda event: None)
    text = entry.plan_resume_context({'session_id': 'session'}, ROOT)
    assert len(text) <= 4000
    assert 'Now: L02' in text and 'Current evidence' in text


def test_show_reports_saved_blocker(tmp_path):
    plan = fixture_plan(tmp_path, flat=True)
    path = plan / 'leaves/L01.json'
    row = json.loads(path.read_text())
    row.update(status='blocked', blocker='Waiting for review')
    path.write_text(json.dumps(row))
    text = mcp.show_plan({'plan_dir': str(plan)})['content'][0]['text']
    assert 'Blocked:' in text and 'Waiting for review' in text


def test_skill_routes_overall_status_to_read_only_show():
    plan_skill = (ROOT / 'src/common/skills/plan/SKILL.md').read_text()
    main_skill = (ROOT / 'src/common/skills/last-human-commit/SKILL.md').read_text()
    description = plan_skill.split('---')[1]
    assert "Optional short plan" in description
    assert "plan" in main_skill.lower() and "optional" in main_skill.lower()
    assert 'optional' in plan_skill.lower() and 'telemetry' in plan_skill.lower()
    assert 'optional' in plan_skill.lower()


def test_status_hints_find_indexed_blocked_and_completed_plans(tmp_path, monkeypatch):
    pj = load_module(TOOLS / 'lhc_plan_json.py', name='plan_overview_index')
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    repo = tmp_path / 'repo'
    (repo / '.git').mkdir(parents=True)
    unrelated = repo / '.agents/tasks/unrelated'
    (unrelated / 'leaves').mkdir(parents=True)
    (unrelated / 'plan.json').write_text('{}')
    (unrelated / 'leaves/U.json').write_text(json.dumps({'id': 'U', 'status': 'running', 'session': 'another'}))
    for status in ('blocked', 'done'):
        base = tmp_path / status
        base.mkdir()
        plan = fixture_plan(base, flat=True)
        leaf_file = plan / 'leaves/L01.json'
        leaf = json.loads(leaf_file.read_text())
        leaf.update(status=status, session='session-' + status, blocker='Waiting for review')
        leaf_file.write_text(json.dumps(leaf))
        pj.record_session_plan('session-' + status, plan, 'L01')
        before = contents(plan)
        event = {'cwd': str(repo), 'session_id': 'session-' + status}
        found = entry._plan_entry(event, ROOT)
        assert found['continuation'] is None
        assert found['status_plans'] == [str(plan)]
        prompt = entry._plan_context(found)
        assert str(plan) in prompt and 'show_plan' in prompt
        hook = subprocess.run([sys.executable, str(TOOLS / 'lhc_entry.py'), '--root', str(ROOT),
                               '--event', 'UserPromptSubmit', '--plan-entry'],
                              input=json.dumps(event), capture_output=True, text=True, env=os.environ.copy())
        assert hook.returncode == 0
        hook_text = json.loads(hook.stdout)['hookSpecificOutput']['additionalContext']
        assert str(plan) in hook_text and 'show_plan' in hook_text
        resume = entry.plan_resume_context(event, ROOT)
        assert str(plan) in resume and 'Release plan' in resume
        assert 'unrelated' not in resume
        shown = mcp.show_plan({'plan_dir': str(plan)})['content'][0]['text']
        assert 'Flat task' in shown
        if status == 'blocked':
            assert 'Waiting for review' in shown
        assert contents(plan) == before


def test_multiple_bound_plans_are_ambiguous_even_with_active_leaf(tmp_path, monkeypatch):
    pj = load_module(TOOLS / 'lhc_plan_json.py', name='plan_overview_index_ambiguous')
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    repo = tmp_path / 'repo'
    (repo / '.git').mkdir(parents=True)
    plans = []
    for status in ('done', 'running'):
        base = tmp_path / status
        base.mkdir()
        plan = fixture_plan(base, flat=True)
        leaf_file = plan / 'leaves/L01.json'
        leaf = json.loads(leaf_file.read_text())
        leaf.update(status=status, session='same-session')
        leaf_file.write_text(json.dumps(leaf))
        pj.record_session_plan('same-session', plan, 'L01')
        plans.append(str(plan))
    event = {'cwd': str(repo), 'session_id': 'same-session'}
    found = entry._plan_entry(event, ROOT)
    assert found['continuation']['plan'] == plans[1]  # continuation behavior remains
    assert set(found['status_plans']) == set(plans)
    for text in (entry._plan_context(found), entry.plan_resume_context(event, ROOT)):
        assert all(plan in text for plan in plans)
        assert 'автоматически' in text
        assert 'Now:' not in text
