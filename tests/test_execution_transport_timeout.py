"""Delivery may outlast a metadata read; a timeout authorizes one guarded retry."""
import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/common/tools'))
from lhc_execution_transport import HerderMcpClient, TransportError
from lhc_execution import dispatch_assignment


@pytest.fixture
def delayed_http():
    calls = []
    delays = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            method, params = request['method'], request.get('params', {})
            operation = params['name'] if method == 'tools/call' else method
            calls.append((operation, params))
            time.sleep(delays.get(operation, 0))
            if method.startswith('notifications/'):
                self.send_response(204)
                self.end_headers()
                return
            result = ({'protocolVersion': '2025-11-25', 'capabilities': {},
                       'serverInfo': {'name': 'isolated-deadline-fixture', 'version': '1'}}
                      if method == 'initialize' else
                      {'delivery': 'accepted', 'inputId': params.get('arguments', {}).get('inputId'),
                       'turnId': 'fixture-turn', 'sessionId': 'worker', 'harness': 'codex'})
            payload = json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Expected when the caller's deadline expired.

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    client = HerderMcpClient(url=f'http://127.0.0.1:{server.server_port}/mcp',
                            token='isolated-fixture-token', host_id='test-host', timeout=0.10)
    # Inject the delivery budget independently of read/init. On the old client
    # this budget is ignored, reproducing the actual premature HTTP timeout.
    client.deliver_timeout = 0.80
    yield client, delays, calls
    server.shutdown()
    server.server_close()
    thread.join()


def test_delayed_delivery_uses_its_own_budget_and_sends_once(delayed_http):
    client, delays, calls = delayed_http
    delays['deliver'] = 0.30
    result = client.call('deliver', {'inputId': 'one-input'})
    assert result['delivery'] == 'accepted' and result['inputId'] == 'one-input'
    assert [operation for operation, _ in calls] == ['initialize', 'notifications/initialized', 'deliver']


@pytest.mark.parametrize('operation', ['initialize', 'session_info', 'resume_after'])
def test_read_and_init_keep_the_short_budget(delayed_http, operation):
    client, delays, calls = delayed_http
    delays[operation] = 0.30
    with pytest.raises(TransportError) as failure:
        client.call('session_info' if operation == 'initialize' else operation, {})
    assert failure.value.submitted is (operation != 'initialize')
    assert sum(name == operation for name, _ in calls) == 1
    assert not any(name == 'deliver' for name, _ in calls)


def test_genuine_delivery_timeout_gets_one_guarded_retry_then_stops(delayed_http):
    client, delays, calls = delayed_http
    client.deliver_timeout = 0.10
    delays['deliver'] = 0.30
    saved = {'attempt_id': 'isolated-attempt', 'executor_kind': 'session', 'state': 'assigned',
             'lead': {'host_id': 'test-host', 'harness': 'codex', 'session_id': 'lead'},
             'executor': {'host_id': 'test-host', 'harness': 'codex', 'session_id': 'worker'}}

    def persist(state, receipt):
        saved.update(state=state, **receipt)
        return copy.deepcopy(saved)

    result = dispatch_assignment(copy.deepcopy(saved), 'isolated test', transport=client, persist=persist)
    assert result['state'] == 'delivery_unknown'
    assert result['dispatch']['status'] == 'unknown'
    assert result['dispatch']['reason'] == 'herder_transport_unavailable'
    # ACTION_POLICY: the timeout gets exactly one guarded retry under the same
    # request id; a second UNKNOWN is final and further calls stay reads.
    retried = dispatch_assignment(result, 'isolated test', transport=client, persist=persist)
    assert retried['state'] == 'delivery_unknown'
    assert retried['dispatch'].get('retries') == 1
    assert retried['dispatch']['request_id'] == result['dispatch']['request_id']
    final = dispatch_assignment(retried, 'isolated test', transport=client, persist=persist)
    assert final == retried
    assert [operation for operation, _ in calls].count('deliver') == 2


def test_delivery_budget_defaults_and_constructor_override():
    client = HerderMcpClient(token='isolated-fixture-token')
    assert client.timeout == 10
    assert client.deliver_timeout == 60
    configured = HerderMcpClient(token='isolated-fixture-token', timeout=0.10, deliver_timeout=0.80)
    assert configured.timeout == 0.10 and configured.deliver_timeout == 0.80
