"""Known child provenance never becomes standalone bootstrap proof."""
import json
import pytest
from test_outcome_bootstrap import fresh, contract

@pytest.mark.parametrize('source', [
    {'subagent': {'thread_spawn': {'parent_thread_id': 'known-parent', 'depth': 1}}},
    {'subagent': {'agent_path': '/known-child'}},
    {'subagent': {'other': 'review'}},
])
def test_nested_child_provenance_cannot_be_promoted_to_standalone(fresh, source):
    root, journal, state_path = fresh
    rows = journal.read_text().splitlines()
    header = json.loads(rows[0])
    header['payload']['source'] = source
    journal.write_text(json.dumps(header) + '\n' + '\n'.join(rows[1:]) + '\n')
    result = contract(root, kind='testing')
    assert result.returncode != 0, 'known nested child source was verified as standalone'
    assert not state_path.exists()


def test_existing_verified_child_identity_route_remains_supported(fresh):
    import lhc_native_identity as identity
    root, journal, state_path = fresh
    parent_id, child_id, call_id, agent_path = 'fixture-parent', 'fixture-child', 'spawn-call', '/fixture-child'
    parent = journal.parent / (parent_id + '.jsonl')
    child = journal.parent / (child_id + '.jsonl')
    parent_rows = [
        {'type': 'session_meta', 'payload': {'id': parent_id, 'cwd': str(root)}},
        {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'spawn_agent', 'call_id': call_id}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': call_id, 'output': '{"status":"success"}'}},
        {'type': 'event_msg', 'payload': {'type': 'item_completed', 'thread_id': parent_id,
            'item': {'type': 'SubAgentActivity', 'kind': 'started', 'agent_thread_id': child_id,
                     'agent_path': agent_path, 'id': call_id}}},
    ]
    parent.write_text(''.join(json.dumps(row) + '\n' for row in parent_rows))
    child.write_text(json.dumps({'type': 'session_meta', 'payload': {
        'id': child_id, 'cwd': str(root), 'parent_thread_id': parent_id, 'session_id': parent_id,
        'agent_path': agent_path, 'originator': 'agent-herder',
        'source': {'subagent': {'thread_spawn': {'parent_thread_id': parent_id}}}}}) + '\n')
    result = identity.resolve_child_identity(identity.composite_session_id(parent_id, child_id),
        parent, child, observed_native_cwd=str(root))
    assert result['verified'] and result['parent_native_id'] == parent_id
    assert result['dispatch_call_id'] == call_id
