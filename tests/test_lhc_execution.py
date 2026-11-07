"""Execution receipts, exact native joins and the real HTTP MCP protocol."""
import copy
import importlib
import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))


def assignment():
    return {'schema_version': 1, 'attempt_id': 'attempt-1', 'executor_kind': 'session',
            'lead': {'host_id': 'test-host', 'harness': 'codex', 'session_id': 'lead'},
            'executor': {'host_id': 'test-host', 'harness': 'codex', 'session_id': 'worker'},
            'parent': None, 'state': 'assigned', 'dispatch': None, 'wake': None,
            'observed_runtime': None, 'events': []}


class Harness:
    def __init__(self, a=None):
        self.assignment = a or assignment()
        self.saved = []

    def persist(self, state, receipt):
        self.saved.append((state, copy.deepcopy(receipt)))
        self.assignment = dict(self.assignment, state=state, **receipt)
        return copy.deepcopy(self.assignment)


@pytest.fixture
def endpoint():
    calls = []
    responses = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append((body, dict(self.headers)))
            assert self.headers['Authorization'] == 'Bearer fixture-token'
            if body['method'] == 'initialize':
                result = {'protocolVersion': '2025-11-25', 'capabilities': {}, 'serverInfo': {'name': 'fixture', 'version': '1'}}
            elif body['method'].startswith('notifications/'):
                self.send_response(204); self.end_headers(); return
            else:
                assert self.headers['Mcp-Session-Id'] == 'fixture-session'
                params = body['params']; name = params['name']
                result = responses[name](params['arguments'])
                result = {'content': [{'type': 'text', 'text': json.dumps(result)}]}
            payload = 'data: ' + json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': result}) + '\n\n'
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Mcp-Session-Id', 'fixture-session'); self.end_headers()
            self.wfile.write(payload.encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    yield f'http://127.0.0.1:{server.server_port}/mcp', calls, responses
    server.shutdown(); server.server_close(); thread.join()


def configure(endpoint):
    _, _, responses = endpoint
    responses['deliver'] = lambda args: {'ok': True, 'delivery': 'accepted', 'admitted': True,
        'inputId': args['inputId'], 'turnId': 'turn-1', 'sessionId': 'worker', 'harness': 'codex'}
    responses['session_info'] = lambda args: {'session': {'id': args['sessionId'], 'harness': 'codex',
        'hostId': 'test-host', 'status': 'running', 'model': 'actual-model', 'cwd': '/actual/worktree',
        'meta': {'nativeLastTurn': {'turnId': 'turn-1', 'status': 'inProgress'}}}}
    responses['resume_after'] = lambda args: {'wait': fixture_wait(args)}


def fixture_wait(args, *, state='waiting', turn='turn-1'):
    import hashlib
    owner = args.get('owner') or {'harness': 'codex', 'sessionId': 'lead'}
    key = json.dumps([json.dumps([owner['harness'], owner['sessionId']], separators=(',', ':')),
                      args.get('requestId')], separators=(',', ':'))
    return {'id': args.get('waitId') or 'wait_' + hashlib.sha256(key.encode()).hexdigest()[:32],
            'owner': owner, 'state': state,
            'dependencies': [{'harness': 'codex', 'sessionId': 'worker'}],
            'dependencyTurns': {'["codex","worker"]': turn}}


def client(endpoint):
    return importlib.import_module('lhc_execution_transport').HerderMcpClient(
        url=endpoint[0], token='fixture-token', host_id='test-host')


def test_real_http_dispatch_registers_exact_durable_wake(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); harness = Harness()
    result = execution.dispatch_assignment(harness.assignment, 'one task', transport=client(endpoint), persist=harness.persist)
    assert [s for s, _ in harness.saved] == ['dispatching', 'submitted', 'running', 'running', 'running']
    assert harness.saved[0][1]['dispatch']['status'] == 'dispatching'
    assert result['wake']['state'] == 'waiting'
    assert result['wake']['turn_id'] == 'turn-1'
    assert result['observed_runtime']['model'] == 'actual-model'
    calls = [b['params']['name'] for b, _ in endpoint[1] if b['method'] == 'tools/call']
    assert calls == ['deliver', 'session_info', 'resume_after']
    deliver = endpoint[1][2][0]['params']['arguments']
    assert deliver['create'] == 'never' and deliver['activation'] == 'always'
    assert deliver['sourceHarness'] == 'codex' and deliver['sourceSessionId'] == 'lead'


def test_unknown_and_crash_intent_are_never_replayed(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); endpoint[2]['deliver'] = lambda args: {'admissionUnknown': True, 'delivery': 'unknown'}
    harness = Harness(); transport = client(endpoint)
    result = execution.dispatch_assignment(harness.assignment, 'task', transport=transport, persist=harness.persist)
    assert result['state'] == 'delivery_unknown'
    count = len(endpoint[1])
    assert execution.dispatch_assignment(result, 'task', transport=transport, persist=harness.persist) == result
    assert len(endpoint[1]) == count
    crashed = assignment(); crashed['state'] = 'dispatching'; crashed['dispatch'] = {'request_id': 'old'}
    result = execution.dispatch_assignment(crashed, 'task', transport=transport, persist=Harness(crashed).persist)
    assert result['state'] == 'delivery_unknown' and len(endpoint[1]) == count


def test_quota_and_missing_turn_do_not_schedule(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); endpoint[2]['deliver'] = lambda args: {'ok': False, 'delivery': 'not_attempted', 'error': 'codex_quota_guard'}
    h = Harness(); result = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert result['state'] == 'blocked' and result['dispatch']['reason'] == 'codex_quota_guard'
    configure(endpoint); endpoint[2]['deliver'] = lambda args: {'ok': True, 'delivery': 'accepted', 'inputId': args['inputId']}
    h = Harness(); result = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert result['state'] == 'submitted' and result['wake']['reason'] == 'dispatch_turn_unavailable'


def test_other_turn_never_becomes_running_or_wake(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    endpoint[2]['session_info'] = lambda _: {'session': {'id': 'worker', 'harness': 'codex', 'hostId': 'test-host',
        'status': 'running', 'meta': {'nativeLastTurn': {'turnId': 'foreign-turn', 'status': 'inProgress'}}}}
    h = Harness(); result = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert result['state'] == 'submitted' and result['wake']['reason'] == 'native_turn_mismatch'
    assert not any(b.get('params', {}).get('name') == 'resume_after' for b, _ in endpoint[1])


def test_self_and_cross_host_do_not_send(endpoint):
    execution = importlib.import_module('lhc_execution')
    a = assignment(); a['executor_kind'] = 'self'; a['executor'] = dict(a['lead'])
    h = Harness(a); result = execution.dispatch_assignment(a, 'task', transport=client(endpoint), persist=h.persist)
    assert result['state'] == 'assigned' and endpoint[1] == []
    a = assignment(); a['executor']['host_id'] = 'remote'
    result = execution.dispatch_assignment(a, 'task', transport=client(endpoint), persist=Harness(a).persist)
    assert result['state'] == 'blocked' and result['dispatch']['reason'] == 'cross_host_join_unsupported'
    assert endpoint[1] == []


def test_reconcile_exact_completion_keeps_admission_and_reads_blocked_wake(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); h = Harness(); transport = client(endpoint)
    a = execution.dispatch_assignment(h.assignment, 'task', transport=transport, persist=h.persist)
    endpoint[2]['resume_after'] = lambda args: {'wait': dict(fixture_wait(args, state='delivery_blocked'), reason='quota')}
    endpoint[2]['session_info'] = lambda args: {'session': {'id': 'worker', 'harness': 'codex', 'hostId': 'test-host',
        'status': 'idle', 'meta': {'nativeLastTurn': {'turnId': 'turn-1', 'status': 'completed'}}}}
    result = execution.reconcile_assignment(a, transport=transport, persist=h.persist)
    assert result['state'] == 'result_ready'
    assert result['wake']['state'] == 'delivery_blocked' and result['wake']['reason'] == 'codex_quota_guard'
    assert result['dispatch']['turn_id'] == 'turn-1'
    assert result['observed_runtime']['state'] == 'completed'
    assert result['state'] != 'accepted'


def test_stale_observer_is_not_runtime_proof(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); h = Harness()
    def stale(*args, **kwargs):
        return {'state': 'running', 'source': 'native_verified', 'observed_at': '2000-01-01T00:00:00Z', 'turn_id': 'turn-1'}
    result = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist, observer=stale)
    assert result['state'] == 'submitted' and result['wake']['reason'] == 'native_observation_unavailable'


def test_wrong_wait_turn_is_cancelled_without_stopping_worker(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    def wait(args):
        if args['action'] == 'cancel':
            return {'wait': {'id': args['waitId'], 'state': 'cancelled'}}
        return {'wait': fixture_wait(args, turn='foreign-turn')}
    endpoint[2]['resume_after'] = wait
    h = Harness(); result = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert result['wake']['reason'] == 'wake_turn_mismatch'
    actions = [b['params']['arguments'].get('action') for b, _ in endpoint[1] if b.get('params', {}).get('name') == 'resume_after']
    assert actions == ['wait', 'cancel']


def test_existing_protected_fingerprint_credentials(tmp_path):
    mod = importlib.import_module('lhc_execution_transport')
    import hashlib
    token = 'existing:token'
    (tmp_path / 'herder.env').write_text('AGENT_HERDER_HTTP_TOKEN=sha256:' + hashlib.sha256(token.encode()).hexdigest()[:16] + '\n')
    (tmp_path / 'secrets.json').write_text(json.dumps({'secrets': {'AGENT_HERDER_HTTP_TOKEN': token}}))
    for p in tmp_path.iterdir(): p.chmod(0o600)
    assert mod.existing_token({}, tmp_path) == token
    (tmp_path / 'herder.env').chmod(0o644)
    with pytest.raises(mod.TransportError, match='credential_unverified'):
        mod.existing_token({}, tmp_path)


def test_non_loopback_endpoint_is_not_used(endpoint):
    mod = importlib.import_module('lhc_execution_transport')
    with pytest.raises(mod.TransportError, match='loopback_endpoint_required'):
        mod.HerderMcpClient(url='http://example.com/mcp', token='secret')


def test_unknown_wake_registration_never_replays(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    transport = client(endpoint)
    original = transport.call
    attempts = []
    def call(name, args):
        if name == 'resume_after':
            attempts.append(args)
            raise TimeoutError('injected uncertain registration')
        return original(name, args)
    transport.call = call
    h = Harness(); a = execution.dispatch_assignment(h.assignment, 'task', transport=transport, persist=h.persist)
    assert a['wake']['state'] == 'delivery_unknown'
    execution.reconcile_assignment(a, transport=transport, persist=h.persist)
    assert [args['action'] for args in attempts] == ['wait', 'status']


def test_public_receipt_omits_private_payload(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    endpoint[2]['deliver'] = lambda args: {'ok': False, 'delivery': 'not_attempted',
        'error': 'quota refused: sensitive detail', 'messages': ['secret-text'], 'environment': {'TOKEN': 'secret'}}
    h = Harness(); a = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert a['dispatch']['reason'] == 'codex_quota_guard'
    assert 'secret' not in json.dumps(a)


def test_assigned_reconcile_observes_availability_separately_from_old_completion(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    endpoint[2]['session_info'] = lambda args: {'session': {'id': 'worker', 'harness': 'codex', 'hostId': 'test-host',
        'status': 'idle', 'meta': {'nativeLastTurn': {'turnId': 'old-turn', 'status': 'completed'}}}}
    h = Harness(); a = execution.reconcile_assignment(h.assignment, transport=client(endpoint), persist=h.persist)
    assert a['state'] == 'assigned' and a['observed_runtime']['state'] == 'idle'
    assert a['observed_runtime']['turn_id'] == 'old-turn'
    assert a.get('dispatch') is None


def test_unknown_registration_recovers_exact_wait_read_only(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); transport = client(endpoint); original = transport.call
    actions = []
    def call(name, args):
        if name == 'resume_after':
            actions.append(args['action'])
            if args['action'] == 'wait':
                raise TimeoutError('lost response after durable registration')
            return {'wait': fixture_wait(args, state='waiting')}
        return original(name, args)
    transport.call = call
    h = Harness(); a = execution.dispatch_assignment(h.assignment, 'task', transport=transport, persist=h.persist)
    assert a['wake']['state'] == 'delivery_unknown' and a['wake']['wait_id'].startswith('wait_')
    a = execution.reconcile_assignment(a, transport=transport, persist=h.persist)
    assert a['wake']['state'] == 'waiting'
    assert actions == ['wait', 'status']


def test_foreign_wait_status_cannot_update_this_assignment(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); h = Harness(); transport = client(endpoint)
    a = execution.dispatch_assignment(h.assignment, 'task', transport=transport, persist=h.persist)
    endpoint[2]['resume_after'] = lambda args: {'wait': dict(fixture_wait(args, state='resumed'), owner={'harness': 'codex', 'sessionId': 'foreign'})}
    a = execution.reconcile_assignment(a, transport=transport, persist=h.persist)
    assert a['wake']['state'] == 'unknown' and a['wake']['reason'] == 'wake_identity_unverified'


def test_current_native_turn_overrides_old_terminal_turn(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    endpoint[2]['session_info'] = lambda args: {'session': {'id': 'worker', 'harness': 'codex', 'hostId': 'test-host',
        'status': 'running', 'meta': {'activeTurnId': 'turn-1',
            'nativeLastTurn': {'turnId': 'old-turn', 'status': 'completed'}}}}
    h = Harness(); a = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert a['state'] == 'running' and a['observed_runtime']['turn_id'] == 'turn-1'
    assert a['wake']['state'] == 'waiting'


def test_old_unknown_wait_record_is_read_by_existing_request_key(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint); h = Harness(); transport = client(endpoint)
    a = execution.dispatch_assignment(h.assignment, 'task', transport=transport, persist=h.persist)
    a['wake'].update(wait_id=None, state='delivery_unknown')
    endpoint[2]['resume_after'] = lambda args: {'wait': fixture_wait(args)}
    before = len(endpoint[1])
    a = execution.reconcile_assignment(a, transport=transport, persist=h.persist)
    assert a['wake']['state'] == 'waiting' and a['wake']['wait_id'].startswith('wait_')
    actions = [b['params']['arguments'].get('action') for b, _ in endpoint[1][before:] if b.get('params', {}).get('name') == 'resume_after']
    assert actions == ['status']


def test_actual_herder_human_stop_message_retains_stop_reason(endpoint):
    execution = importlib.import_module('lhc_execution')
    configure(endpoint)
    endpoint[2]['deliver'] = lambda args: {'ok': False, 'delivery': 'not_attempted',
        'error': 'Чат явно остановлен. Автопродолжение заблокировано; требуется новое сообщение человека или явное продолжение.'}
    h = Harness(); a = execution.dispatch_assignment(h.assignment, 'task', transport=client(endpoint), persist=h.persist)
    assert a['state'] == 'blocked' and a['dispatch']['reason'] == 'human_stop'
    assert not any(b.get('params', {}).get('name') == 'resume_after' for b, _ in endpoint[1])
