"""Regression coverage for semantic evidence reuse and short review subjects."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
import lhc_outcome as outcomes


def sample_outcome():
    return {
        'id': 'outcome-1', 'original_goal': 'Repair export and verify two rows',
        'corrections': [], 'task_class': 'fullcycle', 'cwd': '/tmp/product',
        'product_root': '/tmp/product', 'owned_paths': ['export.py'], 'revision': 'rev-1',
        'canary': {'scenario': 'Export two rows', 'target': 'project:/tmp/product', 'expected': '2 rows'},
        'coverage': ['unicode'], 'stage_claims': {}, 'verification_kind': 'standard',
        'integration_policy': {'remote': 'origin', 'branch': 'main', 'ownership': 'owned'},
        'stages': {stage: {'status': 'complete', 'basis': 'confirmed', 'evidence': [{'manifest': 'old'}]}
                   for stage in outcomes.STAGES},
    }


def test_review_subject_is_stable_for_admin_metadata_but_binds_current_scope():
    outcome = sample_outcome()
    subject = outcomes.review_subject(outcome)
    metadata_only = deepcopy(outcome)
    metadata_only['reviewed_at'] = 'later'
    metadata_only['source_ref'] = 'another transport receipt'
    assert outcomes.review_subject(metadata_only) == subject

    changed = deepcopy(outcome)
    changed['canary']['expected'] = '3 rows'
    assert outcomes.review_subject(changed) != subject

    source_ref_change = deepcopy(outcome)
    source_ref_change['stages']['consumer']['status'] = 'not-applicable'
    source_ref_change['stages']['consumer']['basis'] = 'source-publication:native-user-prompt:other-ref'
    source_ref_change['stages']['deploy']['status'] = 'not-applicable'
    source_ref_change['stages']['deploy']['basis'] = 'source-publication:native-user-prompt:other-ref'
    source_ref_change['stages']['publication']['status'] = 'complete'
    # Another source reference for the same source-publication applicability
    # is metadata; permission is revalidated separately at publication time.
    source_ref_change['verification_kind'] = 'source-publication'
    before = deepcopy(source_ref_change)
    before['stages']['consumer']['basis'] = 'source-publication:native-user-prompt:first-ref'
    before['stages']['deploy']['basis'] = 'source-publication:native-user-prompt:first-ref'
    assert outcomes.review_subject(before) == outcomes.review_subject(source_ref_change)


def test_short_subject_carries_current_corrections_without_literal_duplication():
    outcome = sample_outcome()
    outcome['corrections'] = ['The export result must be 3 rather than 2.']
    # The assignment carries the resolved product root, exactly as the live
    # reviewer compares it.
    root = str(outcomes.product_root_path(outcome, Path(outcome['cwd'])))
    short = ('Outcome ' + outcome['id'] + ' ' + outcomes.review_subject(outcome) + ' ' +
             root + ' ' + outcome['canary']['scenario'] + ' ' + outcome['canary']['expected'])
    assert outcomes.review_assignment_kind(outcome, short) == 'digest'
    assert outcomes.review_assignment_kind(outcome, 'Outcome ' + outcome['id'] + ' ' + outcome['original_goal']) is None


def test_stage_fingerprints_invalidate_only_changed_claim_and_dependents():
    outcome = sample_outcome()
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['stage_claims'] = {'deploy': {'target': 'deploy status', 'expected': 'ready'}}
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert invalidated == {'deploy', 'consumer'}
    assert outcome['stages']['technical']['status'] == 'complete'
    assert outcome['stages']['publication']['status'] == 'complete'
    assert outcome['stages']['integration']['status'] == 'complete'
    assert outcome['stages']['deploy']['status'] == 'pending'
    assert outcome['stages']['consumer']['status'] == 'pending'


def test_candidate_revision_change_invalidates_every_candidate_bound_stage():
    outcome = sample_outcome()
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['revision'] = 'rev-2'
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert invalidated == set(outcomes.STAGES)
    assert all(row['status'] == 'pending' for row in outcome['stages'].values())


def test_remote_change_reopens_publication_and_integration_but_keeps_source_readiness():
    outcome = sample_outcome()
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['integration_policy']['remote'] = 'upstream'
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert invalidated == {'publication', 'integration'}
    assert outcome['stages']['technical']['status'] == 'complete'
    assert outcome['stages']['consumer']['status'] == 'complete'


def test_consumer_expectation_change_preserves_independent_technical_acceptance():
    outcome = sample_outcome()
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['corrections'] = ['The export result must be 3 rather than 2.']
    outcome['canary']['expected'] = '3 rows'
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert invalidated == {'consumer'}
    assert outcome['stages']['technical']['status'] == 'complete'
    assert outcome['stages']['publication']['status'] == 'complete'
    assert outcome['stages']['consumer']['status'] == 'pending'


def test_observe_consumer_correction_preserves_accepted_unaffected_stage_proofs(tmp_path):
    root = tmp_path / 'product'
    root.mkdir()
    (root / 'export.py').write_text('print(2)\n')
    outcome = sample_outcome()
    outcome.update(cwd=str(root), product_root=str(root), owned_paths=['export.py'],
                   task_class='fullcycle', original_goal='Implement export and verify the result.')
    outcome['canary'].update(target='project:' + str(root), expected='2 rows')
    for row in outcome['stages'].values():
        row.update(status='complete', evidence=[{'manifest': 'accepted-original', 'reviewer': 'independent', 'at': 'original-time'}])
    outcome['revision'] = outcomes.scope_revision(outcome, root)
    outcome['stage_fingerprints'] = outcomes.stage_contract_fingerprints(outcome)
    before = deepcopy(outcome['stages'])
    state = {'business': {'outcome': outcome, 'runtime': 'codex', 'original_prompt': outcome['original_goal'],
                          'execution_context': {'direct_user_messages': []}}}
    now = datetime.now(timezone.utc)
    result = outcomes.observe(state, {'prompt': 'The export result must be 3 rather than 2.'},
                              'UserPromptSubmit', root, 'owner', now)
    assert result['canary']['expected'] == '3'
    assert result['contract_confirmed'] is False
    assert result['stages']['consumer']['status'] == 'pending'
    for stage in ('technical', 'deploy', 'publication', 'integration'):
        assert result['stages'][stage] == before[stage]


def test_typed_evidence_format_correction_preserves_accepted_stage_rows():
    outcome = sample_outcome()
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['corrections'] = ['Evidence format correction: render the same accepted read calls as JSON.']
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert invalidated == set()
    assert all(row['status'] == 'complete' for row in outcome['stages'].values())


def test_source_publication_canary_contract_reopens_technical_and_publication():
    outcome = sample_outcome()
    outcome['verification_kind'] = 'source-publication'
    outcome['source_publication'] = {'candidate_fingerprint': 'candidate-1'}
    previous = outcomes.stage_contract_fingerprints(outcome)
    outcome['canary']['expected'] = 'candidate-2'
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, previous)
    assert 'technical' in invalidated and 'publication' in invalidated
    assert outcome['stages']['technical']['status'] == 'pending'
    assert outcome['stages']['publication']['status'] == 'pending'


def test_old_unfingerprinted_complete_rows_are_never_migrated_as_current_pass():
    outcome = sample_outcome()
    invalidated = outcomes.invalidate_changed_stage_evidence(outcome, None)
    assert invalidated == set(outcomes.STAGES)
    assert all(row['status'] == 'pending' for row in outcome['stages'].values())
    assert all(row['evidence'] == [{'manifest': 'old'}] for row in outcome['stages'].values())


def test_repeated_require_stage_preserves_same_fingerprinted_acceptance(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_outcome_contract import anchored, cli
    import lhc_time_guard as guard

    outcome = anchored(tmp_path)
    path = guard.learning_path(tmp_path, 'codex', 'leader')
    state = guard.load_state(path)
    row = state['business']['outcome']['stages']['technical']
    row.update(status='complete', basis='independently accepted',
               evidence=[{'manifest': 'accepted-native-review', 'reviewer': 'independent',
                          'at': 'original-review-time', 'calls': ['call-1']}])
    state['business']['outcome']['stage_fingerprints'] = outcomes.stage_contract_fingerprints(
        state['business']['outcome'])
    accepted = deepcopy(row)
    guard.write_state(path, state)

    cli(tmp_path, 'contract', '--scenario', 'Empty basket total', '--target', 'python3 total.py',
        '--expected', '0', '--owned-path', 'total.py', '--require-stage', 'technical')
    after = guard.load_state(path)['business']['outcome']['stages']['technical']
    assert after == accepted


def test_repeated_require_stage_still_invalidates_changed_semantics(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_outcome_contract import anchored, cli
    import lhc_time_guard as guard

    anchored(tmp_path)
    path = guard.learning_path(tmp_path, 'codex', 'leader')
    state = guard.load_state(path)
    outcome = state['business']['outcome']
    outcome['stages']['technical'].update(status='complete', evidence=[{'manifest': 'old-proof'}])
    outcome['stage_fingerprints'] = outcomes.stage_contract_fingerprints(outcome)
    guard.write_state(path, state)

    cli(tmp_path, 'contract', '--scenario', 'Empty basket total', '--target', 'python3 total.py',
        '--expected', '0', '--owned-path', 'total.py', '--coverage', 'changed-coverage',
        '--require-stage', 'technical')
    after = guard.load_state(path)['business']['outcome']['stages']['technical']
    assert after['status'] == 'pending'
    assert after['evidence'] == [{'manifest': 'old-proof'}]


def test_short_native_assignment_is_used_by_discovery_and_acceptance(tmp_path, monkeypatch):
    # Reuse the established native transcript fixture; no product or provider
    # action is performed by this source-level regression.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_outcome_contract import cli, review_export, semantic_research_fixture, state
    outcome, _, _, _ = semantic_research_fixture(tmp_path)
    assert cli(tmp_path, 'status')['review_subject'] == outcomes.review_subject(outcome)
    manifest = review_export(
        tmp_path, outcome, sid='reviewer', stage_names=('consumer',), command='cat settings.txt',
        raw_final='Expected: ' + outcome['canary']['expected'] + '. Observed: settings.txt contains encoding=UTF-8. No defects found.')
    source = tmp_path / 'native-home/.codex/sessions/reviewer.jsonl'
    rows = [__import__('json').loads(line) for line in source.read_text().splitlines()]
    rows[1]['payload']['content'] = [{'text': (
        'Review outcome ' + outcome['id'] + '\nReview subject: ' + outcomes.review_subject(outcome) +
        '\nProduct root: ' + str(tmp_path) + '\nScenario: ' + outcome['canary']['scenario'] +
        '\nExpected: ' + outcome['canary']['expected'] + '\nOwned paths: settings.txt') }]
    source.write_text('\n'.join(__import__('json').dumps(row) for row in rows) + '\n')
    export = tmp_path / 'reviewer-export.jsonl'
    export.write_bytes(source.read_bytes())
    data = __import__('json').loads(manifest.read_text())
    data['target']['source']['location'] = str(source)
    export.write_bytes(source.read_bytes())
    manifest.write_text(__import__('json').dumps(data))
    monkeypatch.setenv('CODEX_HOME', str(tmp_path / 'native-home/.codex'))
    before = state(tmp_path)
    result = cli(tmp_path, 'review', '--native-reviewer', 'reviewer')
    assert result['finish_verdict'] == 'complete'
    assert result['review_assessment']['reviewer'] == 'reviewer'
    assert state(tmp_path)['business']['outcome']['stages']['consumer']['status'] == 'complete'


@pytest.mark.parametrize('include_context', [True, False])
def test_child_reviewer_uses_verified_parent_dispatch_without_fake_user_row(tmp_path, monkeypatch, include_context):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_native_subagent_identity import (AGENT_PATH, CHILD, PARENT, parent_rows,
        session_header, write_jsonl)
    from test_outcome_contract import review_export, semantic_research_fixture, state as load_state
    import lhc_native_identity as identity
    import lhc_outcome_review as reviews
    import lhc_time_guard as guard

    home = tmp_path / 'native-home/.codex'
    sessions = home / 'sessions'
    sessions.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('CODEX_HOME', str(home))
    parent_path = write_jsonl(sessions / ('parent-' + PARENT + '.jsonl'), parent_rows())
    outcome, _, _, _ = semantic_research_fixture(tmp_path)
    stamp = datetime.now(timezone.utc)
    assignment = ('Review outcome ' + outcome['id'] + '\nReview subject: ' + outcomes.review_subject(outcome) +
                  '\nProduct root: ' + str(tmp_path) + '\nScenario: ' + outcome['canary']['scenario'] +
                  '\nExpected: ' + outcome['canary']['expected'] + '\nOwned paths: settings.txt')
    parent_records = parent_rows(cwd=str(tmp_path))
    for row in parent_records:
        row['timestamp'] = (stamp - timedelta(seconds=2 if row['type'] == 'session_meta' else
                                               1 if row['payload'].get('type') == 'function_call' else
                                               0 if row['payload'].get('type') == 'item_completed' else -0.5)).isoformat()
    parent_path = write_jsonl(sessions / ('parent-' + PARENT + '.jsonl'), parent_records)
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_path, tool_name='spawn_agent', tool_call_id='call-1',
        tool_input={'message': assignment}, observed_at=(stamp - timedelta(seconds=1.5)).isoformat())
    report_final = ('Expected: ' + outcome['canary']['expected'] + '. Observed: settings.txt contains encoding=UTF-8. No defects found.')
    native_manifest = review_export(tmp_path, outcome, sid=CHILD, stage_names=('consumer',),
                                    command='cat settings.txt', raw_final=report_final)
    data = __import__('json').loads(native_manifest.read_text())
    child_path = Path(data['target']['source']['location'])
    rows = [__import__('json').loads(line) for line in child_path.read_text().splitlines()]
    prefix = [session_header(CHILD, parent=PARENT, cwd=str(tmp_path), agent_path=AGENT_PATH)]
    if include_context:
        prefix.append({'type': 'turn_context', 'timestamp': stamp.isoformat(),
                       'payload': {'model': 'gpt-6.1-sol', 'cwd': str(tmp_path)}})
    rows = prefix + rows[2:]
    for row in rows[2:]:
        row['timestamp'] = (stamp + timedelta(seconds=1 if row['payload'].get('type') != 'message' else 2)).isoformat()
    child_path.write_text('\n'.join(__import__('json').dumps(row) for row in rows) + '\n')
    Path(data['target']['path']).write_bytes(child_path.read_bytes())
    native_manifest.write_text(__import__('json').dumps(data))
    state = load_state(tmp_path)
    parent_state_path = guard.learning_path(tmp_path, 'codex', PARENT)
    parent_state_path.parent.mkdir(parents=True, exist_ok=True)
    parent_state_path.write_text(__import__('json').dumps({'business': {'native_dispatches': [captured]}}))
    manifest = reviews.native_reviewer_manifest(outcome, tmp_path, CHILD, state=state)
    meta, _, _ = reviews.load_review(manifest, state=state)
    assert meta['assignments'] == []
    assert meta['dispatch_assignments'][0]['source_kind'] == 'native-parent-dispatch'
    assert meta['dispatch_assignments'][0]['text'] == assignment
    assert meta['dispatch_assignments'][0]['at'] == captured['observed_at']
    assert reviews.accept_review(outcome, state, manifest, tmp_path, 'leader') is None
    assert outcome['stages']['consumer']['status'] == 'complete'
    assert outcome['stages']['consumer']['evidence'][0]['reviewer'] == CHILD


@pytest.mark.parametrize('later_report', [
    'Thanks, the test report is saved.',
    'Latest assessment: the tests failed; consumer/install pending.',
])
@pytest.mark.parametrize('duplicate_assignment', [False, True])
@pytest.mark.parametrize('technical_before_report', [True, False])
def test_technical_only_native_assessment_survives_duplicate_assignment_and_later_report(
        tmp_path, monkeypatch, later_report, duplicate_assignment, technical_before_report):
    import json
    import sys
    from copy import deepcopy
    from datetime import datetime, timezone, timedelta
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_outcome_contract import anchored, review_export, state as load_state
    import lhc_outcome_review as reviews

    outcome = anchored(tmp_path)
    manifest = review_export(
        tmp_path, outcome, sid='reviewer', stage_names=('technical',),
        raw_final='PARTIAL: Technical tests PASS; consumer/install pending.')
    data = json.loads(manifest.read_text())
    source = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    first_assignment = deepcopy(rows[1])
    assessment_row = deepcopy(rows[-1])
    tool_rows = rows[2:-1]
    duplicate_row = deepcopy(first_assignment)
    acknowledgment = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                     'phase': 'final', 'content': [{'text': later_report}]}}
    stamp = datetime.now(timezone.utc) + timedelta(seconds=2)
    timeline = [rows[0], first_assignment]
    if technical_before_report:
        timeline.extend(tool_rows)
    if duplicate_assignment:
        timeline.append(duplicate_row)
    timeline.append(assessment_row)
    if not technical_before_report:
        timeline.extend(tool_rows)
    timeline.append(acknowledgment)
    for index, row in enumerate(timeline):
        row['timestamp'] = (stamp + timedelta(seconds=index)).isoformat()
    source.write_text(''.join(json.dumps(row) + '\n' for row in timeline))
    Path(data['target']['path']).write_bytes(source.read_bytes())
    manifest.write_text(json.dumps(data))
    monkeypatch.setenv('CODEX_HOME', str(tmp_path / 'native-home/.codex'))

    state = load_state(tmp_path)
    outcome = state['business']['outcome']
    native_manifest = reviews.native_reviewer_manifest(outcome, tmp_path, 'reviewer', state=state)
    meta, _, observations = reviews.load_review(native_manifest, state=state)
    assessment = next(row for row in meta['own_reports'] if 'Technical tests PASS' in row['text'])
    assert len(observations) == 1
    if not technical_before_report:
        assert observations[0][0]['_source_index'] > assessment['index']
        assert not reviews.own_assessment(outcome, assessment['text'], observations, tmp_path,
                                          assessment_index=assessment['index'])
        with pytest.raises(ValueError):
            reviews.accept_review(outcome, state, native_manifest, tmp_path, 'leader')
        return
    assert observations[0][0]['_source_index'] < assessment['index']

    before_negative = deepcopy(state)
    if 'tests failed' in later_report:
        selected = {}
        original_raw_review = reviews.raw_review
        def capture_selected_final(*args, **kwargs):
            selected['text'] = args[1]
            return original_raw_review(*args, **kwargs)
        monkeypatch.setattr(reviews, 'raw_review', capture_selected_final)
        with pytest.raises(ValueError):
            reviews.accept_review(outcome, state, native_manifest, tmp_path, 'leader')
        assert selected['text'] == later_report
        assert state == before_negative
        return

    reviews.accept_review(outcome, state, native_manifest, tmp_path, 'leader')
    accepted = state['business']['outcome']
    assert accepted['review_assessment'] == {
        'reviewer': 'reviewer', 'index': assessment['index'], 'at': assessment['at']}
    assert accepted['stages']['technical']['status'] == 'complete'
    assert accepted['stages']['technical']['evidence'][0]['calls'] == [observations[0][0]['call_id']]
    assert accepted['stages']['consumer']['status'] == 'pending'
    assert accepted['canary']['status'] == 'pending'


def test_quick_child_native_self_review_reads_only_verified_parent_dispatch_state(tmp_path, monkeypatch):
    import json
    import os
    import subprocess
    from datetime import datetime, timezone, timedelta
    from test_native_subagent_identity import (AGENT_PATH, CHILD, PARENT, parent_rows,
        session_header, write_jsonl)
    from test_outcome_contract import anchored, review_export
    import lhc_native_identity as identity
    import lhc_outcome_review as reviews
    import lhc_time_guard as guard

    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    goal = 'Fix the small total CLI. Verify the empty basket returns 0. Do not delegate.'
    outcome = anchored(tmp_path, goal)
    logical_id = identity.composite_session_id(PARENT, CHILD)
    state = guard.load_state(guard.learning_path(tmp_path, 'codex', 'leader'))
    outcome = state['business']['outcome']
    outcome['owner']['session_id'] = logical_id
    outcome.pop('native_source', None)
    child_state_path = guard.learning_path(tmp_path, 'codex', logical_id)
    guard.write_state(child_state_path, state)

    home = tmp_path / 'native-home/.codex'
    sessions = home / 'sessions'
    sessions.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('CODEX_HOME', str(home))
    stamp = datetime.now(timezone.utc)
    parent_path = write_jsonl(sessions / ('parent-' + PARENT + '.jsonl'),
                              parent_rows(cwd=str(tmp_path)))
    captured = identity.capture_spawn_intent(
        PARENT, parent_journal_path=parent_path, tool_name='spawn_agent', tool_call_id='call-1',
        tool_input={'message': goal}, observed_at=(stamp - timedelta(seconds=2)).isoformat())
    parent_state_path = guard.learning_path(tmp_path, 'codex', PARENT)
    guard.write_state(parent_state_path, {'business': {'native_dispatches': [captured]}})
    parent_state_bytes = parent_state_path.read_bytes()

    report = review_export(tmp_path, outcome, sid=CHILD, stage_names=('technical', 'consumer'),
                           raw_final='PASS. Focused regression tests passed. python3 total.py output 0 matched expected 0. Self-check only.')
    data = json.loads(report.read_text())
    source_path = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in source_path.read_text().splitlines()]
    rows = [session_header(CHILD, parent=PARENT, cwd=str(tmp_path), agent_path=AGENT_PATH), *rows[2:]]
    for row in rows[1:]:
        row['timestamp'] = (stamp + timedelta(seconds=1)).isoformat()
    source_path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    data['target']['path'] = str(source_path)
    data['target']['source'] = {'kind': 'native-file', 'location': str(source_path)}
    data['target']['sessionId'] = CHILD
    report.write_text(json.dumps(data))

    # Child state intentionally contains neither parent captures nor a saved transcript path.
    child_state = guard.load_state(child_state_path)
    assert 'native_dispatches' not in child_state['business']
    assert 'native_source' not in child_state['business']['outcome']
    manifest = reviews.native_self_manifest(outcome, tmp_path, 'codex', logical_id, state=child_state)
    meta, _, observations = reviews.load_review(manifest, state=child_state)
    assert meta['id'] == CHILD
    assert len(observations) == 2
    manifest_data = json.loads(manifest.read_text())
    assert manifest_data['target']['sessionId'] == CHILD
    assert manifest_data['target']['source']['dispatch_binding']['logical_id'] == logical_id

    result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'src/common/tools/lhc_outcome.py'),
                             '--cwd', str(tmp_path), '--runtime', 'codex', '--session-id', logical_id,
                             'review', '--native-self'], capture_output=True, text=True,
                            env={**os.environ, 'HOME': str(tmp_path / 'native-home'), 'CODEX_HOME': str(home)})
    assert result.returncode == 0, result.stderr
    reviewed = guard.load_state(child_state_path)['business']['outcome']
    assert reviewed['stages']['technical']['status'] == 'complete'
    assert reviewed['stages']['consumer']['status'] == 'complete'
    assert parent_state_path.read_bytes() == parent_state_bytes


def test_quick_child_native_self_without_parent_capture_stays_pending(tmp_path, monkeypatch):
    import json
    from test_native_subagent_identity import (AGENT_PATH, CHILD, PARENT, parent_rows,
        session_header, write_jsonl)
    from test_outcome_contract import anchored
    import lhc_native_identity as identity
    import lhc_outcome_review as reviews
    import lhc_time_guard as guard

    subprocess = __import__('subprocess')
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    outcome = anchored(tmp_path, 'Fix the small total CLI. Verify the empty basket returns 0. Do not delegate.')
    logical_id = identity.composite_session_id(PARENT, CHILD)
    outcome['owner']['session_id'] = logical_id
    home = tmp_path / 'native-home/.codex'; sessions = home / 'sessions'; sessions.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('CODEX_HOME', str(home))
    parent = write_jsonl(sessions / ('parent-' + PARENT + '.jsonl'), parent_rows(cwd=str(tmp_path)))
    child = write_jsonl(sessions / ('child-' + CHILD + '.jsonl'), [
        session_header(CHILD, parent=PARENT, cwd=str(tmp_path), agent_path=AGENT_PATH)])
    guard.write_state(guard.learning_path(tmp_path, 'codex', PARENT), {'business': {'native_dispatches': []}})
    with pytest.raises(ValueError, match='verified parent dispatch'):
        reviews.native_self_manifest(outcome, tmp_path, 'codex', logical_id)


def test_testing_contract_requires_coverage_before_it_changes_evidence_floor(tmp_path):
    import subprocess
    from copy import deepcopy
    from test_native_milestone_gate import invoke
    from test_outcome_contract import cli, state

    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    invoke(tmp_path, 'UserPromptSubmit', prompt=(
        'You are a testing leaf. Do not edit code. Test the empty basket CLI and report its total.'))
    before = deepcopy(state(tmp_path)['business']['outcome'])
    error = cli(tmp_path, 'contract', '--task-class', 'testing',
                '--scenario', 'Empty basket total', '--target', 'python3 total.py',
                '--expected', '0', ok=False)
    assert 'testing contract requires at least one explicit --coverage' in error
    assert state(tmp_path)['business']['outcome'] == before

    fixed = cli(tmp_path, 'contract', '--task-class', 'testing',
                '--scenario', 'Empty basket total', '--target', 'python3 total.py',
                '--expected', '0', '--coverage', 'empty basket total')
    assert fixed['contract_confirmed'] is True
    assert fixed['coverage'] == ['empty basket total']

    source = state(tmp_path)['business']['outcome']['scope_sources'][0]['source']
    corrected = cli(tmp_path, 'contract', '--task-class', 'quickfix', '--scope-source', source,
                    '--scenario', 'Empty basket total', '--target', 'python3 total.py',
                    '--expected', '0', '--owned-path', 'total.py')
    assert corrected['task_class'] == 'quickfix'
    assert corrected['coverage'] == []


def test_testing_without_selected_native_assessment_gets_actionable_error(tmp_path):
    from test_outcome_contract import anchored, cli, review_export

    outcome = anchored(tmp_path, 'You are a testing leaf. Do not edit code. Test empty basket total.',
                       ('empty basket total',))
    review_export(tmp_path, outcome, sid='leader', raw_final='I am still checking the assigned CLI.')
    error = cli(tmp_path, 'review', '--native-self', ok=False)
    assert 'no current native testing assessment was selected' in error
    assert 'stale reviewer' not in error
