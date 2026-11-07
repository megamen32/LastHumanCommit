"""Explicit LHC assignment dispatch through the existing Herder authority.

No scheduler or retry loop lives here. ``persist(state, receipt_envelope)`` must
atomically save the current attempt (normally plan_json.transition_leaf).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from lhc_execution_transport import HerderMcpClient, TransportError


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ref(value):
    if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or not value[k].strip()
                                         for k in ('host_id', 'harness', 'session_id')):
        raise ValueError('exact_assignment_ref_required')
    return value


def _assignment(value):
    if not isinstance(value, dict) or not value.get('attempt_id'):
        raise ValueError('explicit_assignment_attempt_required')
    _ref(value.get('lead')); _ref(value.get('executor'))
    if value.get('executor_kind') not in ('self', 'session', 'subagent'):
        raise ValueError('executor_kind_required')
    if value['executor_kind'] == 'subagent':
        _ref(value.get('parent'))
    return value


def _saved(persist, assignment, state, **receipt):
    result = persist(state, receipt)
    if isinstance(result, dict) and isinstance(result.get('assignment'), dict):
        return result['assignment']
    if isinstance(result, dict) and result.get('attempt_id') == assignment['attempt_id']:
        return result
    raise ValueError('persist_must_return_saved_assignment')


def _wake(reason, at, *, state='blocked', wait_id=None, turn_id=None):
    return {'wait_id': wait_id, 'state': state, 'reason': reason, 'next_at': None,
            'observed_at': at, 'turn_id': turn_id, 'captured_turn_id': turn_id}


def _reason(value, fallback='native_delivery_blocked'):
    """Only fixed codes cross into a plan that may be publicly published."""
    if not isinstance(value, str):
        return fallback
    for code, pattern in [('codex_quota_guard', r'quota'), ('human_stop', r'human.?stop|manual.?stop'),
                          ('permission_declined', r'permission|approval'), ('scope_declined', r'scope|intake')]:
        if re.search(pattern, value, re.I):
            return code
    return value if re.fullmatch(r'[a-z][a-z0-9_]{0,95}', value) else fallback


def _public_receipt(receipt):
    fields = ('status', 'delivery', 'ok', 'admitted', 'notSubmitted', 'inputId', 'turnId', 'sessionId', 'harness')
    projection = {key: receipt[key] for key in fields if key in receipt and isinstance(receipt[key], (str, bool))}
    if receipt.get('reason') or receipt.get('error'):
        projection['reason'] = _reason(receipt.get('reason') or receipt.get('error'))
    return projection


def observe_native(transport, executor, *, now=_now):
    """Only a fresh, exact native read may produce runtime observations."""
    response = transport.call('session_info', {'detail': 'agent', 'view': 'compact',
        'hostId': executor['host_id'], 'harness': executor['harness'], 'sessionId': executor['session_id']})
    session = response.get('session')
    if not isinstance(session, dict) or any(session.get(native) != executor[key] for key, native in
            [('host_id', 'hostId'), ('harness', 'harness'), ('session_id', 'id')]):
        raise ValueError('native_identity_unverified')
    turn = session.get('meta', {}).get('nativeLastTurn') or {}
    state = turn.get('status')
    if state in ('completed', 'failed', 'cancelled', 'interrupted'):
        runtime_state = state
    elif state in ('inProgress', 'running', 'in_progress') and session.get('status') == 'running':
        runtime_state = 'running'
    else:
        runtime_state = 'unknown'
    return {'state': runtime_state, 'observed_at': now(), 'source': 'native_verified',
            'turn_id': turn.get('turnId'), 'model': session.get('model'), 'worktree': session.get('cwd')}


def _observation(transport, a, observer, now):
    # Custom observers are trusted adapters, never model-supplied fields. Enforce
    # exact freshness even when the adapter was injected by an embedding caller.
    runtime = (observer or observe_native)(transport, a['executor'], now=now)
    if not isinstance(runtime, dict) or runtime.get('source') != 'native_verified':
        raise ValueError('native_observation_required')
    try:
        at = datetime.fromisoformat(runtime['observed_at'].replace('Z', '+00:00'))
        current = datetime.fromisoformat(now().replace('Z', '+00:00'))
        if not (0 <= (current - at).total_seconds() <= 30):
            raise ValueError('native_observation_stale')
    except (KeyError, TypeError):
        raise ValueError('native_observation_stale') from None
    return runtime


def _join(a, transport, persist, runtime, now):
    turn_id = a['dispatch'].get('turn_id')
    if (a.get('wake') or {}).get('wait_id') or (a.get('wake') or {}).get('request_id'):
        return a
    # Persist before registration: after an interrupted registration reconcile
    # reads status using the known request id, it never creates a second wait.
    wait_request = a['dispatch']['request_id'] + ':completion'
    pending = _wake('registration_in_progress', now(), state='registering', turn_id=turn_id)
    pending['request_id'] = wait_request
    a = _saved(persist, a, a['state'], wake=pending)
    try:
        response = transport.call('resume_after', {'action': 'wait',
            'owner': {'harness': a['lead']['harness'], 'sessionId': a['lead']['session_id']},
            'dependencies': [{'harness': a['executor']['harness'], 'sessionId': a['executor']['session_id']}],
            'requestId': wait_request,
            'message': 'LHC assignment ' + a['attempt_id'] + ': read the current goal and native receipt, accept the result, then dispatch ready work.'})
        wait = response.get('wait', {})
        key = json.dumps([a['executor']['harness'], a['executor']['session_id']], separators=(',', ':'))
        captured = wait.get('dependencyTurns', {}).get(key)
        owner = {'harness': a['lead']['harness'], 'sessionId': a['lead']['session_id']}
        if captured != turn_id or wait.get('owner') != owner or not wait.get('id'):
            # A later turn must never cause this assignment's lead wake. Cancel
            # only the just-created mismatching wait, never a native execution.
            if wait.get('id'):
                transport.call('resume_after', {'action': 'cancel', 'waitId': wait['id'],
                    'owner': {'harness': a['lead']['harness'], 'sessionId': a['lead']['session_id']}})
            wake = _wake('wake_turn_mismatch', now())
        else:
            wake = _wake(_reason(wait.get('reason'), None), now(), state=wait.get('state', 'unknown'),
                wait_id=wait.get('id'), turn_id=captured)
            wake['next_at'] = wait.get('scheduledAt')
        wake['request_id'] = wait_request
    except Exception:
        wake = _wake('wake_registration_unknown', now(), state='delivery_unknown', turn_id=turn_id)
        wake['request_id'] = wait_request
    return _saved(persist, a, a['state'], wake=wake)


def dispatch_assignment(assignment, message, *, transport=None, persist, observer=None, now=_now):
    a = _assignment(assignment)
    if a['executor_kind'] == 'self':
        if a['executor'] != a['lead']:
            raise ValueError('self_assignment_ref_mismatch')
        return a
    if a.get('state') == 'dispatching':
        dispatch = dict(a.get('dispatch') or {}, status='unknown', reason='dispatch_interrupted', observed_at=now())
        return _saved(persist, a, 'delivery_unknown', dispatch=dispatch)
    if a.get('state') != 'assigned':
        return a
    if not isinstance(message, str) or not message.strip():
        raise ValueError('nonempty_assignment_message_required')
    transport = transport or HerderMcpClient()
    identity = {'attempt_id': a['attempt_id'], 'lead': a['lead'], 'executor': a['executor']}
    request_id = 'lhc:' + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    dispatch = {'request_id': request_id, 'status': 'dispatching', 'observed_at': now(), 'turn_id': None,
                'reason': None, 'receipt': None}
    if a['lead']['host_id'] != a['executor']['host_id'] or a['lead']['host_id'] != transport.host_id:
        dispatch.update(status='blocked', reason='cross_host_join_unsupported')
        return _saved(persist, a, 'blocked', dispatch=dispatch)
    if a['lead'] == a['executor']:
        dispatch.update(status='blocked', reason='self_dependency_unsupported')
        return _saved(persist, a, 'blocked', dispatch=dispatch)
    a = _saved(persist, a, 'dispatching', dispatch=dispatch)
    try:
        receipt = transport.call('deliver', {'hostId': a['executor']['host_id'],
            'harness': a['executor']['harness'], 'sessionId': a['executor']['session_id'],
            'inputId': request_id, 'message': message, 'create': 'never', 'activation': 'always', 'mode': 'queue'})
    except TransportError as error:
        dispatch.update(status='unknown' if error.submitted else 'blocked', reason=error.reason, observed_at=now())
        return _saved(persist, a, 'delivery_unknown' if error.submitted else 'blocked', dispatch=dispatch)
    except Exception:
        dispatch.update(status='unknown', reason='dispatch_outcome_unknown', observed_at=now())
        return _saved(persist, a, 'delivery_unknown', dispatch=dispatch)
    dispatch.update(receipt=_public_receipt(receipt), observed_at=now())
    if receipt.get('isError') or receipt.get('admissionUnknown') or receipt.get('delivery') == 'unknown':
        dispatch.update(status='unknown', reason='native_admission_unknown')
        return _saved(persist, a, 'delivery_unknown', dispatch=dispatch)
    if receipt.get('delivery') in ('not_attempted', 'not_found', 'skipped_inactive') or receipt.get('notSubmitted'):
        dispatch.update(status='blocked', reason=_reason(receipt.get('error') or receipt.get('reason') or receipt.get('delivery')))
        return _saved(persist, a, 'blocked', dispatch=dispatch)
    if receipt.get('delivery') not in ('accepted', 'accepted_unconfirmed', 'completed', 'accepted_failed'):
        dispatch.update(status='unknown', reason='native_admission_unconfirmed')
        return _saved(persist, a, 'delivery_unknown', dispatch=dispatch)
    # Exact input correlation is mandatory for a turn claim. Admission without
    # turn correlation remains submitted and cannot bind the latest native turn.
    correlated = (receipt.get('inputId') == request_id and receipt.get('sessionId') == a['executor']['session_id']
                  and receipt.get('harness') == a['executor']['harness'])
    dispatch.update(status='accepted', turn_id=receipt.get('turnId') if correlated else None)
    a = _saved(persist, a, 'submitted', dispatch=dispatch)
    if not dispatch['turn_id']:
        return _saved(persist, a, 'submitted', wake=_wake('dispatch_turn_unavailable', now()))
    return reconcile_assignment(a, transport=transport, persist=persist, observer=observer, now=now)


def reconcile_assignment(assignment, *, transport=None, persist, observer=None, now=_now):
    a = _assignment(assignment)
    if a.get('state') == 'dispatching':
        return dispatch_assignment(a, '', transport=transport, persist=persist, observer=observer, now=now)
    if a.get('state') in ('assigned', 'accepted', 'cancelled', 'delivery_unknown', 'blocked'):
        return a
    transport = transport or HerderMcpClient()
    wake = a.get('wake') or {}
    if wake.get('wait_id'):
        try:
            response = transport.call('resume_after', {'action': 'status', 'waitId': wake['wait_id']})
            wait = response.get('wait') or {}
            wake = dict(wake, state=wait.get('state', 'unknown'), reason=_reason(wait.get('reason'), None), observed_at=now())
            a = _saved(persist, a, a['state'], wake=wake)
        except Exception:
            a = _saved(persist, a, a['state'], wake=dict(wake, state='unknown', reason='wake_status_unavailable', observed_at=now()))
    turn_id = (a.get('dispatch') or {}).get('turn_id')
    if not turn_id:
        return a
    try:
        runtime = _observation(transport, a, observer, now)
    except Exception:
        return _saved(persist, a, a['state'], wake=_wake('native_observation_unavailable', now())) if not wake.get('wait_id') else a
    if runtime.get('turn_id') != turn_id:
        return _saved(persist, a, a['state'], wake=_wake('native_turn_mismatch', now())) if not wake.get('wait_id') else a
    if runtime['state'] == 'running':
        a = _saved(persist, a, 'running', observed_runtime=runtime)
    elif runtime['state'] in ('completed', 'failed', 'cancelled', 'interrupted'):
        a = _saved(persist, a, 'result_ready', observed_runtime=runtime)
    else:
        return a
    if wake.get('state') in ('registering', 'delivery_unknown') and not wake.get('wait_id'):
        return a  # uncertain registration is read/reconciled, never replayed
    return _join(a, transport, persist, runtime, now)


def _leaf_context(plan_dir, leaf_id, attempt_id, actor, expected_hash):
    """Bind a bridge call to one CAS-protected canonical assignment."""
    import lhc_plan_json
    if not isinstance(leaf_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', leaf_id):
        raise ValueError('invalid_leaf_id')
    path = Path(plan_dir) / 'leaves' / (leaf_id + '.json')
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    if expected_hash and digest != expected_hash:
        raise ValueError('leaf_changed')
    a = json.loads(before).get('assignment')
    if not isinstance(a, dict) or a.get('attempt_id') != attempt_id:
        raise ValueError('assignment_attempt_mismatch')
    def persist(state, receipt):
        nonlocal digest
        result = lhc_plan_json.transition_leaf(plan_dir, leaf_id, attempt_id, state,
                    receipt=receipt, actor=actor, expected_hash=digest)
        digest = result['sha256']
        return result
    return a, persist


def dispatch_leaf(plan_dir, leaf_id, attempt_id, message, *, actor=None, expected_hash=None,
                  transport=None, observer=None, now=_now):
    a, persist = _leaf_context(plan_dir, leaf_id, attempt_id, actor, expected_hash)
    return dispatch_assignment(a, message, transport=transport, persist=persist, observer=observer, now=now)


def reconcile_leaf(plan_dir, leaf_id, attempt_id, *, actor=None, expected_hash=None,
                   transport=None, observer=None, now=_now):
    a, persist = _leaf_context(plan_dir, leaf_id, attempt_id, actor, expected_hash)
    return reconcile_assignment(a, transport=transport, persist=persist, observer=observer, now=now)
