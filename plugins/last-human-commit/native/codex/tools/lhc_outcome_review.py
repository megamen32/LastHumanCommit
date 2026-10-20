"""Bounded native source floor for an existing independent semantic review.

This is not a universal meaning/permission checker. The reviewer compares the
actual operation, target, revision and expected result. Native provenance and
real tool observations are checked here; review truth remains independently
reviewable in its unmodified transcript, not a writer-authored PASS certificate.
"""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

import lhc_milestone as native
from lhc_outcome import ENGINEERING, STAGES, scope_revision, remote_binding, product_paths, product_root_path, digest

# The package entrypoints keep their primary tool directory first. Append the
# canonical shared tools directory so review-only helpers resolve in both
# generated plugin layouts without shadowing their local outcome module.
_REVIEW_PATH = Path(__file__).resolve()
_SHARED_TOOL_DIRS = [_REVIEW_PATH.parent]
_SHARED_TOOL_DIRS += [parent / 'common' / 'tools' for parent in _REVIEW_PATH.parents]
for _shared_tools in _SHARED_TOOL_DIRS:
    if (_shared_tools / 'lhc_testing_reuse.py').is_file() and str(_shared_tools) not in sys.path:
        sys.path.append(str(_shared_tools))

MARKER = 'LHC_OUTCOME_REVIEW '


def opencode_native_export(cwd, sid):
    """Existing native CLI, no inference, credentials/config edits or server install."""
    try:
        result = subprocess.run(['opencode', 'session', 'export', '--standalone', sid],
                                cwd=cwd, capture_output=True, timeout=20)
    except subprocess.TimeoutExpired as error:
        raise ValueError('native OpenCode export unavailable; preserve pending') from error
    if result.returncode or len(result.stdout) > native.MAX_BYTES:
        raise ValueError('native OpenCode export unavailable or outside bounded source window')
    exported = json.loads(result.stdout)
    info = exported['info']
    if info.get('id') != sid or Path((info.get('location') or {}).get('directory', '/unknown')).resolve() != cwd:
        raise ValueError('native export identity/project mismatch')
    messages = []
    for message in exported['messages']:
        role = message.get('type')
        if role not in {'user', 'assistant'}:
            continue
        parts = [{'type': 'text', 'text': message['text']}] if role == 'user' else []
        for part in message.get('content', []):
            if part.get('type') == 'text':
                parts.append({'type': 'text', 'text': part['text']})
            elif part.get('type') == 'tool':
                state, timing = part.get('state') or {}, part.get('time') or {}
                parts.append({'type': 'tool', 'tool': part['name'], 'callID': part['id'], 'state': {
                    'status': state.get('status'), 'input': state.get('input'), 'output': native.content(state.get('content')),
                    'time': {'start': timing.get('ran') or timing.get('created'), 'end': timing.get('completed')}}})
        # Preserve original text and calls; hidden reasoning is not feedback.
        messages.append({'info': {'id': message['id'], 'sessionID': sid, 'role': role,
                                  'time': message.get('time', {})}, 'parts': parts})
    return info, messages


def native_self_manifest(outcome, cwd, runtime, owner, state=None):
    from lhc_outcome import bounded_self_check
    if outcome['owner'] != {'harness': runtime, 'session_id': owner} or not (outcome['task_class'] in {'testing', 'research'} or bounded_self_check(outcome)):
        raise ValueError('native self-check closes only its own bounded assignment, never fullcycle/parent acceptance')
    archive = cwd / '.tmp/lhc-native-self'
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    if runtime == 'codex':
        import lhc_native_identity as identity
        home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
        try:
            identity_info = _resolve_native_actor(owner, None, [], cwd, runtime=runtime)
        except (OSError, ValueError):
            raise ValueError('own native Codex source unavailable/ambiguous; preserve pending')
        path = Path(identity_info['journal_path']).resolve()
        if identity_info.get('parent_native_id'):
            if Path(identity_info.get('native_cwd', '/unknown')).resolve() != cwd.resolve():
                raise ValueError('verified child native cwd differs from the owned product root; preserve pending')
            assignment = identity_info.get('assignment') or {}
            if (assignment.get('status') != 'bound' or
                    assignment.get('prompt', '').find(outcome.get('original_goal', '\0')) < 0 or
                    not all(text in assignment.get('prompt', '') for text in outcome.get('corrections', []))):
                raise ValueError('verified parent dispatch is missing the exact current bounded assignment; preserve pending')
            source = {'kind': 'native-file', 'location': str(path),
                      'dispatch_binding': _dispatch_binding(identity_info, owner)}
        else:
            source = {'kind': 'native-file', 'location': str(path)}
        owner = identity_info.get('native_id') or owner
    elif runtime == 'opencode':
        info, messages = opencode_native_export(cwd, owner)
        path = archive / (runtime + '-' + owner + '.json')
        path.write_text(json.dumps(messages, ensure_ascii=False)); path.chmod(0o600)
        source = {'kind': 'native-cli', 'location': 'opencode:session-export:' + owner,
                  'cwd': str(cwd), 'model': info.get('model')}
    else:
        raise ValueError('native self-export unsupported in this runtime; preserve pending/observer boundary')
    manifest = archive / (runtime + '-' + owner + '.manifest.json')
    manifest.write_text(json.dumps({'format': 'agent-herder-transcript-manifest-v1', 'exporter': 'existing-native-self-route',
        'target': {'path': str(path), 'harness': runtime, 'sessionId': owner, 'complete': runtime == 'codex', 'source': source}}))
    manifest.chmod(0o600)
    return manifest


def codex_window(source):
    """Verify a bounded, contiguous native tail; retain physical source indexes."""
    location = Path(source['location'])
    start, end, first = (source.get(key) for key in ('start_byte', 'end_byte', 'start_line'))
    if any(type(value) is not int for value in (start, end, first)) or not 0 < start < end:
        raise ValueError('invalid native source window')
    with location.open('rb') as stream:
        header = stream.readline(native.MAX_BYTES + 1)
        header_end = stream.tell()
        if len(header) + end - start > native.MAX_BYTES or end != os.fstat(stream.fileno()).st_size:
            raise ValueError('native window oversized or source advanced; refresh its snapshot, not its assessment')
        stream.seek(start - 1)
        if stream.read(1) != b'\n' or start < len(header):
            raise ValueError('native window must begin on an original line boundary')
        stream.seek(0); remaining, lines = start, 0
        while remaining:
            chunk = stream.read(min(remaining, 65536))
            if not chunk:
                raise ValueError('native source changed during snapshot')
            lines += chunk.count(b'\n'); remaining -= len(chunk)
        if lines != first:
            raise ValueError('native original line index mismatch')
        body = stream.read(end - start)
        if not body.endswith(b'\n') or end != location.stat().st_size:
            raise ValueError('native source is incomplete/advanced; preserve pending')
    indexes = [0] + [first + i for i, line in enumerate(body.splitlines()) if line.strip()]
    return header + body, indexes


def native_reviewer_manifest(outcome, cwd, reviewer, state=None):
    """Read one EXISTING Codex reviewer; never create, resume or impersonate it."""
    from lhc_outcome import review_assignment_kind
    if outcome['task_class'] not in ENGINEERING | {'research'}:
        raise ValueError('native reviewer route is bounded engineering/research only')
    home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
    candidates = list((home / 'sessions').rglob('*' + reviewer + '*.jsonl'))
    if len(candidates) != 1:
        raise ValueError('existing native reviewer unavailable/ambiguous')
    location = candidates[0].resolve(); start = None; context = None; dispatch_binding = None
    saw_outcome_id = False
    saw_current_goal = False
    with location.open('rb') as stream:
        header = stream.readline(native.MAX_BYTES + 1)
        header_end = stream.tell()
        if json.loads(header).get('payload', {}).get('id') != reviewer:
            raise ValueError('native reviewer identity mismatch')
        index = 1
        while True:
            offset = stream.tell(); line = stream.readline(native.MAX_BYTES + 1)
            if not line:
                end = offset; break
            if len(line) > native.MAX_BYTES or not line.endswith(b'\n'):
                raise ValueError('native reviewer has an oversized/incomplete record')
            row = json.loads(line); payload = row.get('payload', {})
            if row.get('type') == 'turn_context':
                context = (offset, index)
            if row.get('type') == 'response_item' and payload.get('role') == 'user':
                text = native.content(payload.get('content'))
                saw_outcome_id = saw_outcome_id or outcome['id'] in text
                saw_current_goal = saw_current_goal or outcome['original_goal'] in text
                if start is None and review_assignment_kind(outcome, text, product_root_path(outcome, cwd)):
                    start = context or (offset, index)
            index += 1
    if not start and state is not None:
        import lhc_native_identity as identity
        try:
            header = identity.read_native_header(location)
            if header.get('parent_thread_id'):
                logical_id = identity.composite_session_id(header['parent_thread_id'], header['native_id'])
                resolved = _resolve_native_actor(logical_id, location, [], cwd, runtime='codex')
                assignment = resolved.get('assignment') or {}
                if (assignment.get('status') == 'bound' and
                        review_assignment_kind(outcome, assignment.get('prompt', ''), product_root_path(outcome, cwd))):
                    start = context or (header_end, 1)
                    dispatch_binding = _dispatch_binding(resolved, logical_id)
        except (OSError, ValueError):
            # Only a verified native parent dispatch can substitute for a user row.
            pass
    if not start:
        if saw_outcome_id and not saw_current_goal:
            detail = f"reviewer assignment names active outcome id {outcome['id']} but omits the full current task goal"
        elif saw_current_goal and not saw_outcome_id:
            detail = f"reviewer assignment includes the current task goal but omits active outcome id {outcome['id']}"
        elif saw_current_goal and saw_outcome_id:
            detail = f"reviewer mentions active outcome id {outcome['id']} and the current task goal, but not together in one native assignment"
        else:
            detail = f"existing reviewer has no native assignment for active outcome {outcome['id']} and its full current task goal"
        action = ("No reviewer evidence was accepted. Keep this outcome pending. Add a fresh user assignment in the existing reviewer "
                  "session binding its outcome id and current review subject digest, with readable exact product root, scenario, and expected "
                  "result; legacy assignments must include the full current goal and corrections. Keep exact owned paths and current scope. "
                  "The digest identifies the subject only; it is not permission.")
        raise ValueError(f'{detail}. {action}')
    source = {'kind': 'native-file-window', 'location': str(location),
              'start_byte': start[0], 'end_byte': end, 'start_line': start[1]}
    if dispatch_binding:
        source['dispatch_binding'] = dispatch_binding
    raw, _ = codex_window(source)
    archive = cwd / '.tmp/lhc-native-review'; archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    stem = 'codex-' + reviewer + '-' + digest(source)
    snapshot = archive / (stem + '.jsonl')
    if snapshot.exists() and snapshot.read_bytes() != raw:
        raise ValueError('native snapshot changed; never overwrite original evidence')
    snapshot.write_bytes(raw); snapshot.chmod(0o600)
    manifest = archive / (stem + '.manifest.json')
    manifest.write_text(json.dumps({'format': 'agent-herder-transcript-manifest-v1', 'exporter': 'existing-native-review-route',
        'target': {'path': str(snapshot), 'harness': 'codex', 'sessionId': reviewer, 'complete': True, 'source': source}}))
    manifest.chmod(0o600)
    return manifest


def _dispatch_binding(resolved, logical_id):
    assignment = resolved.get('assignment') or {}
    return {'logical_id': logical_id, 'call_id': resolved.get('dispatch_call_id'),
            'parent_journal_path': resolved.get('parent_journal_path'),
            'parent_state_path': resolved.get('parent_state_path'),
            'observed_at': assignment.get('observed_at'),
            'prompt_sha256': assignment.get('prompt_sha256'),
            'native_id': resolved.get('native_id'),
            'parent_native_id': resolved.get('parent_native_id'),
            'native_cwd': resolved.get('native_cwd')}


def _resolve_native_actor(logical_id, journal_path, records, cwd, runtime='codex'):
    import lhc_native_identity as identity
    if not journal_path:
        native_id = logical_id.rsplit(':subagent:', 1)[-1]
        journal_path = identity.find_native_journal(native_id)
    if ':subagent:' in logical_id:
        header = identity.read_native_header(journal_path)
        import lhc_time_guard as guard
        event = {'session_id': header.get('parent_thread_id'), 'agent_id': header.get('native_id'),
                 'transcript_path': str(journal_path)}
        resolved = guard.resolve_native_child_assignment(event, logical_id, runtime,
                                                         Path(header['native_cwd']))
        if not resolved.get('verified'):
            raise ValueError(resolved.get('reason') or 'native parent dispatch is unverified')
        return resolved
    return identity.resolve_standalone_identity(logical_id, journal_path, observed_native_cwd=str(cwd))


def _verified_session_relation(outcome, state, meta, manifest_path, cwd):
    """Resolve both native actors before deciding self, parent/child, or independent."""
    import lhc_native_identity as identity
    manifest = json.loads(native.read(manifest_path))
    harness = manifest.get('target', {}).get('harness')
    if harness == 'opencode':
        # OpenCode's supported native CLI export is re-read and compared by
        # load_review; it has no Codex parent/child identity graph.
        reviewer = (harness, meta.get('id') or meta.get('session_id'), str(Path(meta.get('cwd', '/unknown')).resolve()))
        task_owner = (outcome['owner'].get('harness'), outcome['owner'].get('session_id'),
                      str(Path(outcome.get('cwd', '/unknown')).resolve()))
        if reviewer[1] == task_owner[1] and reviewer != task_owner:
            raise ValueError('native session id overlaps but its verified project identity differs')
        return 'self' if reviewer == task_owner else 'independent'
    if harness != 'codex':
        raise ValueError('native reviewer identity is unavailable for this harness; preserve pending')
    source = manifest.get('target', {}).get('source') or {}
    if source.get('kind') not in {'native-file', 'native-file-window'}:
        raise ValueError('reviewer native journal reference is unavailable; preserve pending')
    reviewer_path = source.get('location')
    owner_path = outcome.get('native_source')
    try:
        owner_identity = _resolve_native_actor(outcome['owner']['session_id'], owner_path, [], cwd, harness)
    except (OSError, ValueError) as error:
        raise ValueError('owner native journal identity is unavailable; preserve pending') from error
    try:
        reviewer_header = identity.read_native_header(reviewer_path)
        if reviewer_header.get('parent_thread_id'):
            reviewer_logical_id = identity.composite_session_id(
                reviewer_header['parent_thread_id'], reviewer_header['native_id'])
            reviewer_identity = _resolve_native_actor(reviewer_logical_id, reviewer_path, [], cwd, harness)
        else:
            reviewer_identity = identity.resolve_standalone_identity(
                reviewer_header['native_id'], reviewer_path,
                observed_native_cwd=str(reviewer_header['native_cwd']))
    except (OSError, ValueError) as error:
        raise ValueError('review must be independent; reviewer native identity is unavailable or ambiguous') from error
    return identity.classify_session_relation(owner_identity, reviewer_identity)


def _verify_current_actor(outcome, state, owner, cwd):
    if outcome['owner'].get('harness') == 'opencode':
        if owner != outcome['owner'].get('session_id') or Path(outcome.get('cwd', '/unknown')).resolve() != cwd.resolve():
            raise ValueError('current review actor is not bound to the owning native session')
        return
    try:
        owner_identity = _resolve_native_actor(
            outcome['owner']['session_id'], outcome.get('native_source'),
            [], cwd, outcome['owner'].get('harness', 'codex'))
        current_identity = _resolve_native_actor(
            owner, None, [], cwd, outcome['owner'].get('harness', 'codex'))
        relation = __import__('lhc_native_identity').classify_session_relation(owner_identity, current_identity)
    except (OSError, ValueError) as error:
        raise ValueError('current review actor is not bound to the owning native session') from error
    if relation != 'self':
        raise ValueError('current review actor is not the exact owning native session')


def _reusable_source_readiness(outcome, state, cwd):
    """Revalidate an earlier accepted exact-candidate read proof without relabeling it."""
    from lhc_outcome import stage_contract_fingerprints
    row = outcome.get('stages', {}).get('technical', {})
    evidence = (row.get('evidence') or [{}])[-1]
    metadata = outcome.get('source_publication') or {}
    if (row.get('status') != 'complete' or evidence.get('verification_level') != 'independent-source-review'
            or evidence.get('contract_fingerprint') != stage_contract_fingerprints(outcome).get('technical')
            or evidence.get('revision') != scope_revision(outcome, cwd)
            or evidence.get('source_candidate') != metadata.get('candidate_fingerprint')
            or not evidence.get('source_readiness') or not evidence.get('manifest')):
        return None
    manifest_path = Path(evidence['manifest'])
    if not manifest_path.is_file():
        return None
    try:
        prior_meta, _, prior_observations = load_review(manifest_path, state=state)
        if _verified_session_relation(outcome, state, prior_meta, manifest_path, cwd) != 'independent':
            return None
        call_ids = set(evidence.get('calls', []))
        exact_calls = [(call, output) for call, output in prior_observations if call.get('call_id') in call_ids]
        from lhc_source_publication import source_readiness
        readiness = source_readiness(metadata, exact_calls, product_root_path(outcome, cwd))
        return readiness if readiness == evidence.get('source_readiness') else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def load_review(path, state=None):
    manifest = json.loads(native.read(path))
    if manifest.get('format') != 'agent-herder-transcript-manifest-v1':
        raise ValueError('use the existing native export_transcript manifest')
    target = manifest['target']
    raw = native.read(target['path'])
    if target.get('harness') == 'codex' and target.get('complete'):
        location = Path(target['source']['location']).resolve()
        location.relative_to((Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions').resolve())
        indexes = None
        source_kind = target['source'].get('kind')
        binding = target['source'].get('dispatch_binding')
        if source_kind == 'native-file-window':
            actual, indexes = codex_window(target['source'])
            if actual != raw:
                raise ValueError('review window differs from original native bytes')
        elif source_kind == 'native-file' and not native.read(location).startswith(raw):
            raise ValueError('review export differs from native source')
        elif source_kind != 'native-file':
            raise ValueError('review export differs from native source')
        if binding:
            import lhc_native_identity as identity
            header = identity.read_native_header(location)
            logical_id = binding.get('logical_id')
            resolved = _resolve_native_actor(logical_id, location, [], Path(header['native_cwd']), 'codex')
            assignment = resolved.get('assignment') or {}
            if (resolved.get('dispatch_call_id') != binding.get('call_id') or
                    assignment.get('status') != 'bound' or
                    assignment.get('observed_at') != binding.get('observed_at') or
                    assignment.get('prompt_sha256') != binding.get('prompt_sha256') or
                    resolved.get('native_id') != binding.get('native_id') or
                    resolved.get('parent_native_id') != binding.get('parent_native_id') or
                    resolved.get('native_cwd') != binding.get('native_cwd') or
                    resolved.get('parent_journal_path') != binding.get('parent_journal_path') or
                    resolved.get('parent_state_path') != binding.get('parent_state_path')):
                raise ValueError('child dispatch assignment no longer matches its exact parent source and receipt')
        result = native.native_transcript(raw)
        rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
        indexes = indexes if indexes is not None else list(range(len(rows)))
        result[0]['model'] = list(dict.fromkeys(row['payload']['model'] for row in rows
                                               if row.get('type') == 'turn_context' and row.get('payload', {}).get('model')))
        assignments, call_meta = [], {}
        for index, row in zip(indexes, rows):
            p = row.get('payload', {})
            if row.get('type') == 'response_item' and p.get('role') == 'user':
                assignments.append({'index': index, 'at': row.get('timestamp'), 'text': native.content(p.get('content'))})
            if p.get('type') in {'function_call', 'custom_tool_call'}:
                call_meta[p.get('call_id')] = (index, row.get('timestamp'))
            item = p.get('item') or {}
            if item.get('type') == 'CommandExecution':
                call_meta.setdefault(item.get('id'), (index, row.get('timestamp')))
        result[0]['assignments'] = assignments
        binding = target['source'].get('dispatch_binding')
        if binding:
            result[0]['dispatch_assignments'] = [{
                'index': None, 'at': binding['observed_at'], 'text': assignment['prompt'],
                'source_call_id': binding['call_id'], 'source_kind': 'native-parent-dispatch'}]
        result[0]['own_reports'] = [{'index': i, 'at': row.get('timestamp'), 'text': native.content(row['payload'].get('content'))}
                                    for i, row in zip(indexes, rows) if row.get('payload', {}).get('role') == 'assistant'
                                    and native.content(row['payload'].get('content'))]
        result[0]['review_end_index'] = max((i for i, row in zip(indexes, rows) if row.get('payload', {}).get('role') == 'assistant'
                                            and row['payload'].get('phase') != 'commentary'), default=-1)
        for call, _ in result[2]:
            call['_source_index'], call['_source_time'] = call_meta.get(call.get('call_id'), (None, None))
        finals = [row.get('timestamp') for row in rows if row.get('type') == 'response_item'
                  and row.get('payload', {}).get('role') == 'assistant' and row['payload'].get('phase') != 'commentary']
        result[0]['reviewed_at'] = next((stamp for stamp in reversed(finals) if stamp), result[0].get('timestamp'))
    elif target.get('harness') == 'opencode':
        if target.get('source', {}).get('kind') == 'native-cli':
            sid = target['sessionId']
            source = target['source']
            if source.get('location') != 'opencode:session-export:' + sid:
                raise ValueError('unsupported native CLI operation')
            cwd = Path(source['cwd']).resolve()
            info, live = opencode_native_export(cwd, sid)
            if not source.get('model') or source['model'] != info.get('model'):
                raise ValueError('native model identity unavailable/changed')
            by_id = {m['info']['id']: m for m in live}
            for message in json.loads(raw):
                actual = by_id.get(message['info']['id'])
                if not actual or any(message['info'].get(k) != actual['info'].get(k) for k in ('id', 'sessionID', 'role')) or message['info']['time']['created'] != actual['info']['time']['created']:
                    raise ValueError('export differs from native CLI source')
                for index, part in enumerate(message['parts']):
                    if part.get('type') == 'text' or part.get('state', {}).get('status') == 'completed':
                        if index >= len(actual['parts']) or part != actual['parts'][index]:
                            raise ValueError('native report/call changed; preserve original source')
            result = native.opencode_messages(info, json.loads(raw))
        else:
            result = native.opencode_transcript(target, raw)
        assignments, call_meta = [], {}
        def iso(milliseconds):
            return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat() if milliseconds else None
        for index, message in enumerate(json.loads(raw)):
            header = message.get('info') or message
            if header.get('role') == 'user':
                assignments.append({'index': index, 'at': iso(header.get('time', {}).get('created')),
                                    'text': native.content(message.get('parts') or message.get('content')) or message.get('text', '')})
            for part in message.get('parts') or []:
                if part.get('type') == 'tool':
                    stamp = (part.get('state') or {}).get('time', {}).get('start') or header.get('time', {}).get('created')
                    call_meta[part.get('callID') or part.get('id')] = (index, iso(stamp))
        result[0]['assignments'] = assignments
        result[0]['own_reports'] = [{'index': i, 'at': iso((m.get('info') or m).get('time', {}).get('completed') or (m.get('info') or m).get('time', {}).get('created')),
                                    'text': native.content(m.get('parts') or m.get('content')) or m.get('text', '')}
                                   for i, m in enumerate(json.loads(raw)) if (m.get('info') or m).get('role') == 'assistant'
                                   and (native.content(m.get('parts') or m.get('content')) or m.get('text', '')).strip()]
        result[0]['review_end_index'] = max((i for i, message in enumerate(json.loads(raw))
                                            if (message.get('info') or message).get('role') == 'assistant'), default=-1)
        for call, _ in result[2]:
            call['_source_index'], call['_source_time'] = call_meta.get(call.get('call_id'), (None, None))
        finals = [(message.get('info') or message).get('time', {}).get('completed') for message in json.loads(raw)
                  if (message.get('info') or message).get('role') == 'assistant']
        stamp = next((value for value in reversed(finals) if value), None)
        if stamp:
            result[0]['reviewed_at'] = datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
    else:
        raise ValueError('native review format unsupported; use existing independent Codex/OpenCode reviewer')
    if (result[0].get('id') or result[0].get('session_id')) != target.get('sessionId'):
        raise ValueError('native reviewer identity mismatch')
    return result


def command(call, allow_source_read=False):
    args = call.get('arguments') or call.get('input') or '{}'
    try:
        args = json.loads(args) if isinstance(args, str) else args
    except ValueError:
        return '', []
    text = str(args.get('cmd') or args.get('command') or args.get('url') or '')
    try:
        words = shlex.split(text)
        lexer = shlex.shlex(text, posix=True, punctuation_chars=';&|<>')
        lexer.whitespace_split = True
        if any(token and set(token) <= set(';&|<>') for token in lexer):
            return '', []
        # The headless browser invocation clears its auto-connect switch
        # explicitly. Normalize only that exact env form for executable checks;
        # `text` remains the unmodified native command for evidence/reporting.
        if (len(words) >= 4 and words[0] in {'env', '/usr/bin/env'}
                and words[1:3] == ['-u', 'AGENT_BROWSER_AUTO_CONNECT']
                and Path(words[3]).name == 'agent-browser'):
            words = words[3:]
        if words and Path(words[0]).name in {'bash', 'sh', 'zsh'}:
            if len(words) != 3 or words[1] not in {'-c', '-lc'}:
                return '', []
            if allow_source_read and words[0] not in {'bash', 'sh', 'zsh', '/bin/bash', '/bin/sh', '/bin/zsh', '/usr/bin/bash', '/usr/bin/sh', '/usr/bin/zsh'}:
                return '', []
            return command(dict(arguments=json.dumps({'cmd': words[2]})), allow_source_read)
    except (ValueError, IndexError):
        return '', []
    # Quoted commands, echo+receipt and compound shell output are not real
    # consumer observations. Unknown tool formats need review of a supported
    # native source, never an invented receipt.
    if words and Path(words[0]).name in {'echo', 'printf', 'cat', 'pwd', 'ls', 'rg', 'grep', 'true'} and not (allow_source_read and words[0] in {'cat', '/bin/cat', '/usr/bin/cat'}):
        return '', []
    if any(w in {';', '&&', '||', '|'} for w in words):
        return '', []
    return text, words


def cli_identity(words, cwd):
    """Known Python argv aliases only; never evaluate shell or user code."""
    if words and re.fullmatch(r'python(?:3(?:\.\d+)?)?', Path(words[0]).name):
        rest = words[1:]
        while rest and rest[0] == '-B':
            rest = rest[1:]
        if rest[:1] == ['-m']:
            return ('python', *rest)
        if not rest or rest[0].startswith('-'):
            return ()
        return ('python', str((cwd / rest[0]).resolve()), *rest[1:])
    return tuple(words)


def target_identity(target, cwd):
    uri = urlsplit(target) if target.startswith('file:') else None
    if uri and (uri.netloc not in {'', 'localhost'} or uri.query or uri.fragment):
        return ()
    expected = [unquote(uri.path)] if uri else shlex.split(target)
    if len(expected) == 1 and (uri or expected[0].endswith('.py')):
        return ('python', str((cwd / expected[0]).resolve()))
    return cli_identity(expected, cwd)


def local_native_path(value):
    value = str(value)
    if not value.startswith('file:'):
        return Path(value)
    uri = urlsplit(value)
    if uri.netloc not in {'', 'localhost'} or uri.query or uri.fragment or not Path(unquote(uri.path)).is_absolute():
        raise ValueError('not a local native file URI')
    return Path(unquote(uri.path))


def cli_matches(words, target, cwd):
    actual = cli_identity(words, cwd)
    wanted = target_identity(target, cwd)
    return bool(wanted and actual[:len(wanted)] == wanted)


def scope_names_script(scope, script, cwd, allow_stem=True):
    # A basename in the goal means the root script, not a nested namesake.
    names = [str(script), script.as_uri()]
    if script.is_relative_to(cwd):
        relative = script.relative_to(cwd).as_posix()
        names += [relative, './' + relative]
        if allow_stem and script.parent == cwd and re.search(r'\bCLI\b|command.line|командн.{0,15}строк|скрипт', scope, re.I):
            names.append(script.stem)
    return bool(re.search(r'(?<![\w./-])(?:' + '|'.join(re.escape(n) for n in names) + r')(?![\w-]|\.[\w/-])', scope, re.I))


def project_matches(target, cwd):
    # An optional display annotation does not select a script or grant scope.
    # Only this exact native cwd is accepted; foreign paths remain foreign.
    exact = 'project:' + str(cwd)
    return (target.startswith('project:') and Path(target[8:]).resolve() == cwd) or (
        target.startswith(exact + ' (') and target.endswith(')') and '\n' not in target)


def equivalent_target(old, new, cwd, scope):
    if old == new:
        return True
    if old.startswith('project:') and new.startswith('project:'):
        return project_matches(old, cwd) and project_matches(new, cwd)
    if old.startswith('project:') or new.startswith('project:'):
        project, target = (old, new) if old.startswith('project:') else (new, old)
        identity = target_identity(target, cwd)
        if not project_matches(project, cwd) or len(identity) != 2 or identity[0] != 'python':
            return False
        script = Path(identity[1])
        return script.is_relative_to(cwd) and scope_names_script(scope, script, cwd)
    return bool(target_identity(old, cwd) and target_identity(old, cwd) == target_identity(new, cwd))


def source_read_path(words, cwd):
    if len(words) == 2 and words[0] in {'cat', '/bin/cat', '/usr/bin/cat'} and not words[1].startswith('-'):
        return (cwd / words[1]).resolve()
    return None


def consumer_target(outcome, observations, cwd):
    target = outcome['canary']['target']
    if not target.startswith('project:'):
        if outcome['task_class'] == 'research' and len(shlex.split(target)) == 1:
            source = (cwd / local_native_path(shlex.split(target)[0])).resolve()
            scope = '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])
            if (source.is_relative_to(cwd) and source.is_file()
                    and scope_names_script(scope, source, cwd, allow_stem=False)
                    and product_paths({**outcome, 'owned_paths': [source.relative_to(cwd).as_posix()]}, cwd)):
                return 'cat ' + shlex.quote(str(source))
            raise ValueError('research file target must name the scoped in-project source, not the requested report output')
        return target
    if not project_matches(target, cwd):
        raise ValueError('project canary belongs to another native cwd')
    scope = '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])
    scripts = set()
    for call, output in observations:
        _, words = command(call, allow_source_read=outcome['task_class'] == 'research')
        if outcome['task_class'] == 'research':
            source = source_read_path(words, cwd)
            if source and source.is_relative_to(cwd) and scope_names_script(scope, source, cwd, allow_stem=False):
                if not product_paths({**outcome, 'owned_paths': [source.relative_to(cwd).as_posix()]}, cwd):
                    continue  # Requested FEEDBACK output is not the researched source.
                target = 'cat ' + shlex.quote(str(source))
                if real_observation(call, output, target, 'consumer', 'research', cwd):
                    scripts.add(target)
            continue
        identity = cli_identity(words, cwd)
        if len(identity) < 2 or identity[0] != 'python' or identity[1].startswith('-'):
            continue
        script = Path(identity[1])
        if not script.is_relative_to(cwd) or not scope_names_script(scope, script, cwd):
            continue
        if real_observation(call, output, str(script), 'consumer', outcome['task_class'], cwd):
            scripts.add(str(script))
    if len(scripts) != 1:
        if outcome['task_class'] == 'research':
            raise ValueError('project research needs one explicitly named in-project source file; use one direct cat read and report its actual expected/observed afterward; not echo/compound or a review loop')
        raise ValueError('project target needs one scope-named native CLI; unsupported/ambiguous source: one direct CLI reread, no echo/compound or review loop')
    selected = scripts.pop()
    if outcome['task_class'] in ENGINEERING:
        if Path(selected) not in {(cwd / p).resolve() for p in product_paths(outcome, cwd)}:
            raise ValueError('project CLI is not the scoped owned product')
    return selected


def real_observation(call, output, target, stage, task_class=None, cwd=None, expected=None):
    if stage == 'consumer' and task_class == 'testing' and '_browser_ops' in call:
        from lhc_testing_reuse import url_matches
        return bool(output.strip() and any(
            op['argv'][:1] == ['open'] and len(op['argv']) == 2 and url_matches(op['argv'][1], target)
            or op['argv'][:2] == ['get', 'url'] and any(url_matches(u, target) for u in re.findall(r'https?://[^\s\"<>\\]+', output))
            for op in call['_browser_ops']))
    args = call.get('arguments') or call.get('input') or '{}'
    try:
        args = json.loads(args) if isinstance(args, str) else args
        directory = local_native_path(args.get('workdir') or args.get('cwd') or call.get('_native_cwd') or cwd)
        native_cwd = Path(call.get('_native_cwd') or cwd)
        directory = (native_cwd / directory).resolve() if not directory.is_absolute() else directory.resolve()
        directory.relative_to(cwd)
        # Relative CLI targets are bound to the canary project root. A second
        # checkout with the same filename is not the assigned product.
        if stage == 'consumer' and not target.startswith(('http://', 'https://')) and directory != cwd:
            return False
    except (ValueError, TypeError, AttributeError):
        return False
    text, words = command(call, allow_source_read=stage == 'consumer' and task_class == 'research')
    name = str(call.get('name', '')).casefold()
    if not output.strip():
        return False
    if stage == 'technical':
        normalized = cli_identity(words, cwd)
        return call.get('_exit_code', 0) == 0 and bool(words and (Path(words[0]).name == 'pytest' or words[:2] in [['go', 'test'], ['cargo', 'test'], ['bun', 'test'], ['npm', 'test']] or normalized[:3] in [('python', '-m', 'pytest'), ('python', '-m', 'unittest')]))
    if stage == 'consumer':
        if task_class == 'research':
            try:
                selected = source_read_path(shlex.split(target), cwd)
                if selected:
                    return source_read_path(words, cwd) == selected
                args = json.loads(call.get('arguments') or '{}')
                cmd = args.get('cmd') or args.get('command') or ''
                return shlex.split(cmd)[:len(shlex.split(target))] == shlex.split(target) and bool(shlex.split(target)) and not re.match(r'^(?:echo|printf)\b', cmd)
            except (ValueError, TypeError):
                return False
        if not text:
            return False
        if target.startswith(('http://', 'https://')):
            # Full URL token, not a host substring in echo, another host or log.
            executable = Path(words[0]).name if words else ''
            native_browser_call = 'browser' in name and executable not in {'env', 'bash', 'sh', 'zsh'}
            return target in words and (executable in {'curl', 'wget', 'agent-browser'} or native_browser_call)
        return (not target.startswith('project:') and cli_matches(words, target, cwd)
                and not re.search(r'pytest|\btest\b', text)
                and (task_class not in ENGINEERING or call.get('_exit_code', 0) == 0))
    # Readbacks are stage-specific and contract-bound, never arbitrary Git
    # metadata or a reviewer mutation. Unknown formats need the existing review
    # path plus a supported readback, not a guessed deployment certificate.
    if not expected or not text or not words:
        return False
    if stage in {'publication', 'integration'} and words[:2] == ['git', 'ls-remote']:
        return words[:len(shlex.split(target))] == shlex.split(target) and any(
            line.split()[:1] == [expected] and len(line.split()) > 1 and line.split()[1].startswith('refs/heads/')
            and line.split()[1] == words[-1] for line in output.splitlines()) and bool(re.fullmatch('[0-9a-f]{40,64}', expected))
    try:
        result = json.loads(output)
    except (ValueError, TypeError):
        return False
    if not isinstance(result, dict):
        return False
    if stage == 'deploy':
        plugin_expected = re.fullmatch(r'plugin:([A-Za-z0-9._-]+)@([A-Za-z0-9._-]+):([A-Za-z0-9._-]+)', expected)
        plugin_command = len(words) >= 3 and Path(words[0]).name == 'codex' and words[1:3] == ['plugin', 'list']
        if plugin_expected or plugin_command:
            if not plugin_expected or not plugin_command:
                return False
            plugin_name, marketplace, version = plugin_expected.groups()
            canonical_target = ['codex', 'plugin', 'list', '--marketplace', marketplace, '--json']
            try:
                if (target != ' '.join(canonical_target) or words != canonical_target or
                        native_cwd.resolve() != Path(cwd).resolve() or directory != Path(cwd).resolve() or
                        result.get('marketplace') not in {None, marketplace}):
                    return False
            except (OSError, TypeError):
                return False
            installed = result.get('installed')
            available = result.get('available')
            if not isinstance(installed, list) or not isinstance(available, list):
                return False
            # Manager IDs may be bare or marketplace-qualified. The explicit
            # expected identity must match exactly one installed record; the
            # display name is required but is not used as a fuzzy alias.
            accepted_ids = {plugin_name, plugin_name + '@' + marketplace}
            matches = [row for row in installed if isinstance(row, dict) and
                       row.get('pluginId') in accepted_ids]
            if len(matches) != 1:
                return False
            row = matches[0]
            return (isinstance(row.get('name'), str) and bool(row['name'].strip()) and
                    row.get('marketplaceName') == marketplace and row.get('version') == version and
                    row.get('installed') is True and row.get('enabled') is True)
        matches = target in words if target.startswith(('http://', 'https://')) else words[:len(shlex.split(target))] == shlex.split(target)
        if not matches or (target.startswith(('http://', 'https://')) and Path(words[0]).name not in {'curl', 'wget'}):
            return False
        def version(value):
            return isinstance(value, dict) and any(
                (key in {'version', 'revision', 'image', 'build', 'tag', 'release'} and str(item) == expected) or version(item)
                for key, item in value.items())
        return version(result)
    if words[:3] != ['gh', 'pr', 'view'] or target not in words or result.get('url') != target:
        return False
    if stage == 'publication':
        return result.get('state') in {'OPEN', 'MERGED'} and result.get('headRefOid') == expected
    return stage == 'integration' and result.get('state') == 'MERGED' and bool(result.get('mergedAt')) and (result.get('mergeCommit') or {}).get('oid') == expected


def browser_journey(refs, by_call, target):
    if any('_browser_ops' in call for call, _ in by_call.values()):
        from lhc_testing_reuse import browser_journey as source_journey
        return source_journey(refs, by_call, target)
    browser = [(call, output) for ref, (call, output) in by_call.items() if ref in refs
               if 'browser' in str(call.get('name', '')).casefold() or 'agent-browser' in command(call)[0]]
    if not browser:
        return True  # CLI/API has its own exact target floor.
    contexts = {}
    for call, output in browser:
        args = call.get('arguments') or call.get('input') or '{}'
        args = json.loads(args) if isinstance(args, str) else args
        text, words = command(call)
        name = str(call.get('name', '')).casefold()
        def field(*names):
            value = next((args[k] for k in names if args.get(k) is not None), None)
            for k in names:
                if '--' + k in words:
                    index = words.index('--' + k)
                    return words[index + 1] if index + 1 < len(words) else None
            return value
        key = (name.rsplit('__', 1)[0], field('session', 'session_id', 'sessionId'),
               field('namespace'), field('tabId', 'pageId', 'targetId'))
        action = name + ' ' + text
        url = args.get('url') or next((word for word in words if word.startswith(('http://', 'https://'))), None)
        if url and re.search(r'open|navigate|goto', action):
            contexts[key] = {'target': url, 'acted': False}
        current = contexts.get(key, {})
        if current.get('target') != target or (url and url != target):
            continue
        if re.search(r'click|fill|type|press|select|submit', action) and output.strip():
            current['acted'] = True
        elif current.get('acted') and re.search(r'snapshot|screenshot|evaluate|extract|get.text', action) and output.strip():
            return True
    return False


def expected_compared(expected, final, observations, defect):
    """Literal prose or bounded CLI data comparison, not a semantic parser."""
    normalize = lambda value: ' '.join(value.casefold().split())
    if normalize(expected) in normalize(final):
        return True
    if not re.search(r'ожид|expected|matched|соответств|ровно|подтвержд', final, re.I):
        return False
    outputs = '\n'.join(output for _, output in observations)
    csv = re.findall(r'(?<![\w,])[\w]+,[\w]+(?![\w,])', expected)
    number_pattern = r'(?<![\w.+-])[-+]?\d+(?:\.\d+)?(?!\w)'
    numbers = re.findall(number_pattern, expected)
    number_in = lambda value, text: re.search(r'(?<![\w.+-])' + re.escape(value) + r'(?!\w|\.\d)', text)
    if not csv and not (numbers and re.search(r'total|сумм|exit|status|статус|код', expected, re.I)):
        return False
    if csv and not all(normalize(value) in normalize(outputs) for value in csv):
        return False
    if numbers and not all(number_in(value, final) for value in numbers):
        return False
    data = re.sub(r'exit\s*[:=]?\s*\d+|код(?:\s+выхода)?\s*[:=]?\s*\d+', '', expected, flags=re.I)
    return defect or all(number_in(value, outputs) for value in re.findall(number_pattern, data))


def report_result(text):
    defect = bool(re.search(r'changes.required|\bfailed\b|\bfailure\b|defect found|ошибк|не соответствует', text, re.I))
    positive = bool(re.search(r'\bPASS(?:ED)?\b|no defects|match(?:ed|es)|соответствует|работает|прош[её]л|прошл[аои]', text, re.I))
    return defect, positive


def _technical_partial_assessment(text):
    """A bounded technical result is partial only when consumer work is explicit as pending."""
    defect, _ = report_result(text)
    technical_pass = re.search(
        r'\btechnical(?:\s+(?:tests?|checks?))?\s*[:=-]?\s*pass(?:ed)?\b', text, re.I)
    consumer_pending = re.search(
        r'\bconsumer\s*/\s*install(?:ation)?\s+(?:is\s+)?pending\b', text, re.I)
    return bool(not defect and technical_pass and consumer_pending)


def _has_successful_technical_call_before(observations, cwd, assessment_index, task_class):
    if type(assessment_index) is not int:
        return False
    return any(
        type(call.get('_source_index')) is int and call['_source_index'] < assessment_index
        and call.get('_source_time')
        and real_observation(call, output, '', 'technical', task_class, cwd)
        for call, output in observations
    )


def source_report_result(text):
    """Accept the bounded source-review rubric without upgrading app PASS."""
    defect, positive = report_result(text)
    explicit_negative = re.search(
        r'\b(?:not\s+approved|cannot\s+approve|do\s+not\s+approve|revise|reject(?:ed)?|'
        r'changes?\s+required|failed|failure|defect(?:s)?\s+(?:found|remain|unresolved))\b|'
        r'ошибк|не\s+одобрен|нужн\w*\s+исправ', text, re.I)
    if defect or explicit_negative:
        return True, False
    if positive:
        return False, True
    bounded = re.search(r'\bAPPROVE\s+BOUNDED\b', text, re.I)
    scope = re.search(r'\bscope\s+(?:is\s+)?(?:covered|confirmed|complete)\b', text, re.I)
    return False, bool(bounded and scope)


def _source_evidence_refs(by_file):
    return sorted({ref for value in by_file.values()
                    for ref in (value if isinstance(value, (list, tuple)) else [value])})


def source_finding_quote(outcome, text, observations, cwd, quote):
    """Explicit own-research semantic binding, never an independent verdict.

    Keep the report unchanged; the quoted passage must name the exact source
    and contain its actual native readback. Meaning is the researcher's stated
    comparison, not an automatic prose/translation parser.
    """
    if outcome['task_class'] != 'research' or not quote or quote not in text:
        return False
    try:
        target = consumer_target(outcome, observations, cwd)
        words = shlex.split(target)
        if not source_read_path(words, cwd) or Path(words[-1]).name.casefold() not in quote.casefold():
            return False
        normalize = lambda value: ' '.join(value.split())
        return any(real_observation(call, output, target, 'consumer', 'research', cwd)
                   and normalize(output) in normalize(quote) for call, output in observations)
    except (ValueError, IndexError):
        return False


def research_comparison_binding(outcome, final, observations, cwd, quote):
    """Typed encoding/report/non-proof claim, not an arbitrary prose alias."""
    if not source_finding_quote(outcome, final, observations, cwd, quote):
        return None
    pipeline = r'implementation\s*/\s*tests\s*(?:→|->|,)\s*deploy(?:ment)?\s*(?:→|->|,|or)\s*merge'
    negative = r'(?:cannot\s+(?:prove|establish|confirm)|does\s+not\s+(?:prove|establish|confirm)|не\s+(?:подтвержд\w*|доказыва\w*))'
    def limits(text):
        return any(not re.search(r'\b(?:but|however|зато|однако|но)\b', line, re.I) and re.search(
            negative + r'[^;\n]{0,80}' + pipeline + '|' + pipeline + r'[^;\n]{0,80}' + negative, line, re.I)
            for line in text.splitlines())
    expected = outcome['canary']['expected']
    # Consume the entire supported predicate, rather than blacklisting charset
    # names. Any extra requirement needs its own comparison; never drop it.
    typed_expected = (r'FEEDBACK\.md\s+(?:quotes|records)\s+the\s+actual\s+(?:export\s+)?encoding\s+'
                      r'and\s+(?:explains|states)\s+that\s+(?:settings(?:\.txt)?|(?:this|the)\s+file)\s+'
                      r'alone\s+cannot\s+(?:prove|establish|confirm)\s+' + pipeline + r'\s+completion\.?')
    if (not re.fullmatch(typed_expected, expected.strip(), re.I)
            or 'feedback.md' not in quote.casefold() or not limits(quote)):
        return None
    target = consumer_target(outcome, observations, cwd)
    reads = [(call['call_id'], output.strip()) for call, output in observations if call.get('call_id')
             and real_observation(call, output, target, 'consumer', 'research', cwd)
             and re.fullmatch(r'encoding=[A-Za-z0-9_.+-]+', output.strip())]
    if len({value for _, value in reads}) != 1:
        return None
    value = reads[0][1]
    source = source_read_path(shlex.split(target), cwd)
    if source.stat().st_size > native.MAX_BYTES or source.read_text().strip() != value:
        return None
    report = cwd / 'FEEDBACK.md'
    if product_paths({**outcome, 'owned_paths': ['FEEDBACK.md']}, cwd):
        return None  # A product document is not the requested observation report.
    report_calls = [call['call_id'] for call, output in observations if call.get('call_id')
                    and real_observation(call, output, 'cat ' + shlex.quote(str(report)), 'consumer', 'research', cwd)
                    and value in output and Path(shlex.split(target)[-1]).name in output and limits(output)]
    if not report_calls:
        return None
    return {'kind': 'encoding-report-delivery-limits', 'source': target, 'value': value,
            'source_calls': [ref for ref, _ in reads], 'report': str(report), 'report_calls': report_calls,
            'canary_hash': digest({k: outcome['canary'][k] for k in ('scenario', 'target', 'expected')})}


def raw_review(outcome, final, observations, cwd, comparison_quote=None, source_readiness_reuse=None):
    """Small ordinary-report route; keep original prose as semantic assessment.

    No author PASS/map file and no rewriting the review. Complex unsupported
    prose stays explicit; the same existing reviewer may use the optional JSON
    line, rather than recursively hiring somebody to manufacture a certificate.
    """
    canary = outcome['canary']
    if outcome.get('verification_kind') == 'source-publication':
        from lhc_source_publication import permission_unchanged, publication_readback, source_readiness
        defect, positive = source_report_result(final)
        if not final.strip() or defect or not positive:
            raise ValueError('source readiness needs the existing reviewer’s explicit current result; preserve pending')
        metadata = outcome.get('source_publication') or {}
        source = next((row for row in outcome.get('scope_sources', [])
                      if row.get('source') == metadata.get('permission_source')), None)
        if not permission_unchanged(metadata, source, outcome.get('corrections', [])):
            raise ValueError('source-publication authorization was revoked or no longer matches the current source')
        reused_readiness = False
        try:
            readiness = source_readiness(metadata, observations, cwd, floor=outcome.get('evidence_after'))
        except ValueError:
            if source_readiness_reuse is None:
                raise
            readiness = source_readiness_reuse
            reused_readiness = True
        read_calls = _source_evidence_refs(readiness['read_calls'])
        hash_calls = _source_evidence_refs(readiness['hash_calls'])
        candidate = 'candidate:' + metadata['candidate_fingerprint']
        stages = {}
        if not reused_readiness:
            stages['technical'] = {
                'target': 'project:' + str(cwd), 'expected': candidate,
                'observed': final, 'evidence_calls': sorted(set(read_calls + hash_calls)),
            }
        product_verdict = 'source-ready'
        try:
            published = publication_readback(metadata, observations, cwd, outcome,
                                             outcome.get('evidence_after'))
            stage_claim = outcome.get('stage_claims', {}).get('publication', {})
            if (published['commit'] in final and metadata['ref'] in final and
                    stage_claim.get('target') == f"git ls-remote {metadata['remote']} {metadata['ref']}"):
                stages['publication'] = {
                    'target': stage_claim['target'], 'expected': candidate,
                    'observed': final, 'evidence_calls': [published['readback_call']],
                }
                if outcome.get('stages', {}).get('integration', {}).get('status') == 'pending':
                    policy = outcome.get('integration_policy') or {}
                    if (policy.get('remote') == metadata['remote'] and
                            policy.get('branch') == metadata['branch'] and
                            policy.get('ownership') == 'owned' and
                            (policy.get('branch') not in {'main', 'master'} or policy.get('main_permission_confirmed'))):
                        stages['integration'] = {
                            'target': stage_claim['target'], 'expected': candidate,
                            'observed': final, 'evidence_calls': [published['readback_call']],
                        }
                product_verdict = 'source-published'
        except (OSError, ValueError, KeyError, TypeError):
            published = None
        return {'outcome_id': outcome['id'], 'revision': scope_revision(outcome, cwd),
                **{key: canary[key] for key in ('target', 'scenario', 'expected')},
                'assignment_verdict': 'complete', 'product_verdict': product_verdict,
                'comparison': final, 'stages': stages, 'coverage': {},
                **({'source_publication': published} if product_verdict == 'source-published' else {}),
                'format': 'original-native-source-review'}
    defect, positive = report_result(final)
    if not final.strip() and outcome['task_class'] == 'research':
        raise ValueError('no native assessment yet: send the actual source finding and expected/observed as a separate visible assistant message before review; FEEDBACK alone is not that message. Do not debug helper/session storage; preserve pending if unavailable')
    if not final.strip() or not (positive or defect or outcome['task_class'] == 'research'):
        raise ValueError('raw review must state its actual result; retain the original report')
    technical_partial = _technical_partial_assessment(final)
    if technical_partial and not any(
            real_observation(call, output, '', 'technical', outcome['task_class'], cwd)
            for call, output in observations):
        raise ValueError('technical partial assessment needs a successful native test command before the report')
    stages = {}
    by_call = {call.get('call_id'): (call, output) for call, output in observations if call.get('call_id')}
    resolved = outcome['canary']['target'] if technical_partial else consumer_target(outcome, observations, cwd)
    identity = target_identity(resolved, cwd)
    ordered_cli = (outcome['task_class'] == 'quickfix' and identity and identity[0] == 'python'
                   and all(outcome['stages'][s]['status'] == 'pending' for s in ('technical', 'consumer'))
                   and all(outcome['stages'][s]['status'] == 'not-applicable' for s in ('deploy', 'publication', 'integration')))
    positions = {ref: i for i, ref in enumerate(by_call)}
    technical_at = -1
    for stage in STAGES:
        if outcome['stages'][stage]['status'] != 'pending':
            continue
        if stage == 'consumer' and technical_partial:
            continue
        claim = outcome.get('stage_claims', {}).get(stage, canary)
        target, expected = claim['target'], claim['expected']
        observed_target = resolved if stage == 'consumer' else target
        refs = [ref for ref, (call, output) in by_call.items()
                if real_observation(call, output, observed_target, stage, outcome['task_class'], cwd, expected)]
        if stage == 'technical' and not re.search(r'test|regression|тест|провер', final, re.I):
            refs = []
        if ordered_cli and stage == 'technical' and refs:
            # Select a current acceptance witness, not every diagnostic run.
            refs = refs[:1]
            technical_at = positions[refs[0]]
        if ordered_cli and stage == 'consumer':
            refs = [ref for ref in refs if positions[ref] > technical_at]
            if not refs:
                raise ValueError('current technical test needs a subsequent real CLI readback; earlier diagnostics are not acceptance witnesses')
        if stage in {'deploy', 'publication', 'integration'} and (expected.casefold() not in final.casefold() or target.casefold() not in final.casefold()):
            refs = []
        if stage == 'consumer':
            # Ordinary prose must actually cover this expected consumer result,
            # not a generic all-PASS sentence over unrelated calls.
            short_target = Path(shlex.split(observed_target)[-1]).name
            binding = research_comparison_binding(outcome, final, observations, cwd, comparison_quote) if comparison_quote else None
            if comparison_quote and not binding:
                raise ValueError('research binding needs the fully supported expectation, actual current source, requested FEEDBACK readback and explicit negative delivery-limit claim before the original assessment; unsupported extra predicates stay pending, do not repeat unchanged reads')
            compared = expected_compared(expected, final, [by_call[ref] for ref in refs], defect) or bool(binding)
            if binding:
                refs += binding['report_calls']
            named = any(t.casefold() in final.casefold() for t in (target, short_target))
            if not compared or not (named or (refs and re.search(r'\bCLI\b', final, re.I))):
                refs = []
            if refs:
                refs += [ref for ref, (call, _) in by_call.items() if 'browser' in str(call.get('name', '')).casefold()]
        if stage == 'integration' and refs and outcome.get('integration_policy', {}).get('branch') not in {None, 'main', 'master'}:
            read_at = max(list(by_call).index(ref) for ref in refs)
            refs += [ref for i, (ref, (call, output)) in enumerate(by_call.items()) if i > read_at
                     and real_observation(call, output, resolved, 'consumer', outcome['task_class'], cwd)]
        if not refs:
            break
        stages[stage] = {'target': target, 'expected': expected, 'observed': final,
                         'evidence_calls': refs}
    consumer = stages.get('consumer', {})
    coverage = {item: {'verdict': 'defect' if defect else 'passed', 'expected': canary['expected'],
                      'observed': final, 'evidence_calls': consumer.get('evidence_calls', [])}
                for item in outcome.get('coverage', []) if item.casefold() in final.casefold()}
    return {'outcome_id': outcome['id'], 'revision': scope_revision(outcome, cwd), **{key: canary[key] for key in ('scenario', 'target', 'expected')},
            'assignment_verdict': 'complete', 'product_verdict': 'changes-required' if defect else 'pass',
            'comparison': final, 'stages': stages, 'coverage': coverage, 'format': 'original-native-prose'}


def own_assessment(outcome, text, observations, cwd, comparison_quote=None, assessment_index=None,
                   source_readiness_reuse=None):
    if outcome.get('verification_kind') == 'source-publication':
        from lhc_source_publication import permission_unchanged, source_readiness
        defect, positive = source_report_result(text)
        if not positive and not defect:
            return False
        if defect:
            # Preserve the latest explicit negative instead of falling back to
            # an earlier positive assessment.
            return True
        metadata = outcome.get('source_publication') or {}
        source = next((row for row in outcome.get('scope_sources', [])
                      if row.get('source') == metadata.get('permission_source')), None)
        if not permission_unchanged(metadata, source, outcome.get('corrections', [])):
            return False
        if source_readiness_reuse is not None:
            return True
        try:
            source_readiness(metadata, observations, cwd,
                             floor=outcome.get('evidence_after'), before=assessment_index)
            return True
        except ValueError:
            return False
    if MARKER in text:
        return True
    defect, positive = report_result(text)
    # Never fall back over newer negative findings, even if unsupported/partial.
    if defect:
        return True
    if _technical_partial_assessment(text):
        return _has_successful_technical_call_before(observations, cwd, assessment_index,
                                                     outcome.get('task_class'))
    if not positive and outcome['task_class'] != 'research':
        return False
    try:
        target = consumer_target(outcome, observations, cwd)
    except ValueError:
        return False
    short_target = Path(shlex.split(target)[-1]).name
    names_consumer = any(name.casefold() in text.casefold() for name in (target, short_target)) or re.search(r'\bCLI\b', text, re.I)
    return bool(names_consumer and (expected_compared(outcome['canary']['expected'], text, observations, False)
                or source_finding_quote(outcome, text, observations, cwd, comparison_quote)))


def accept_review(outcome, state, path, cwd, owner, comparison_quote=None, testing_reuse=None):
    from lhc_outcome import bounded_self_check, review_assignment_kind, stage_contract_fingerprints
    meta, messages, observations = load_review(path, state=state)
    product_cwd = product_root_path(outcome, cwd)
    source_mode = outcome.get('verification_kind') == 'source-publication'
    reuse_original = reuse_report = None
    if testing_reuse is not None:
        from lhc_testing_reuse import prepare
        reuse_original = prepare(outcome, meta, observations, owner, testing_reuse, cwd)
        if comparison_quote:
            raise ValueError('testing reuse cannot bind research comparison')
    sid = meta.get('id') or meta.get('session_id')
    _verify_current_actor(outcome, state, owner, cwd)
    relation = _verified_session_relation(outcome, state, meta, path, cwd)
    own_attempt = (not source_mode and relation == 'self' and
                   (outcome['task_class'] in {'testing', 'research'} or bounded_self_check(outcome)))
    native_cwd = Path(meta.get('cwd', '/unknown'))
    cross_cwd_research = relation == 'independent' and outcome['task_class'] == 'research' and native_cwd.resolve() != cwd
    # Native cwd identifies where the independent reviewer runs, not which
    # product it reviewed. For engineering reviews in a separate native cwd,
    # prove product identity from the exact current native assignment below.
    cross_cwd_product = (relation == 'independent' and outcome['task_class'] in ENGINEERING
                         and native_cwd.resolve() != cwd)
    if (relation != 'independent' and (source_mode or not own_attempt)) or not native_cwd.is_absolute() or (
            native_cwd.resolve() != cwd and not cross_cwd_research and not cross_cwd_product):
        raise ValueError('review must be independent and for this exact project')
    # The existing reviewer can deliberately inspect a bounded case from its
    # original project. Missing tool cwd remains that native original cwd,
    # never silently defaults to the case being accepted.
    observations = [({**call, '_native_cwd': str(native_cwd.resolve())}, output) for call, output in observations]
    source_readiness_reuse = (_reusable_source_readiness(outcome, state, cwd) if source_mode else None)
    if comparison_quote and not (own_attempt and outcome['task_class'] == 'research' and all(
            outcome['stages'][stage]['status'] == 'not-applicable' for stage in STAGES if stage != 'consumer')):
        raise ValueError('comparison quote binds only an own bounded research finding, never parent/independent acceptance')
    # A later progress remark/tool message is not a replacement assessment.
    # Keep the actual report's own source index/time: no freshness extension.
    def selected_assessment(report):
        text = report['text']
        # A bound old passage must not hide a later explicit source correction.
        negative_binding = comparison_quote and outcome['task_class'] == 'research' and re.search(
            r'\b(?:defect|wrong|needs? correction)\b|ошибк|не соответствует', text, re.I)
        return negative_binding or own_assessment(outcome, text, observations, product_cwd,
                                                  comparison_quote, report['index'], source_readiness_reuse)
    independent_engineering_review = relation == 'independent' and outcome['task_class'] in ENGINEERING
    own_report = next((report for report in reversed(meta.get('own_reports', []))
                       if selected_assessment(report)), None) if (
                           own_attempt or outcome['task_class'] == 'research' or independent_engineering_review
                       ) else None
    if comparison_quote and (not own_report or not source_finding_quote(outcome, own_report['text'], observations, product_cwd, comparison_quote)):
        raise ValueError('comparison quote must bind the current unchanged native source finding; never skip a newer negative assessment')
    if not own_report and own_attempt and outcome['task_class'] == 'research' and any(
            native.timestamp(report['at']) >= native.timestamp(outcome['started_at'])
            and source_finding_quote(outcome, report['text'], observations, product_cwd, report['text'])
            for report in meta.get('own_reports', [])):
        raise ValueError('fresh source finding needs a semantic comparison binding, not a reread: retain the report and use review --native-self --comparison-quote with its unchanged source-finding passage; self-check only')
    if not own_report and own_attempt and outcome['task_class'] == 'testing':
        if not outcome.get('coverage'):
            raise ValueError('no current native testing assessment was selected: first confirm the testing contract with explicit --coverage, then report expected/observed for that assigned coverage and its exact native consumer call')
        raise ValueError('no current native testing assessment was selected: write a fresh expected/observed comparison naming the assigned coverage and exact native consumer call, then use review --native-self')
    if testing_reuse is not None:
        matches = [row for row in meta.get('own_reports', []) if row['index'] == testing_reuse.get('assessment_index')]
        if len(matches) != 1:
            raise ValueError('testing reuse requires original native assessment')
        own_report = matches[0]
        from lhc_testing_reuse import browser_sources
        source_ops = browser_sources(observations, product_cwd)
        if any(report_result(row['text'])[0] and any(
                call.get('_browser_ops') and output.strip()
                and own_report['index'] < call.get('_source_index', -1) < row['index']
                for call, output in source_ops)
                for row in meta.get('own_reports', []) if row['index'] > own_report['index']):
            raise ValueError('testing reuse cannot skip a later negative product assessment with new consumer observations')
    if own_report:
        # Preserve the actual assessment before later bookkeeping, including
        # an independent research report; never extend its source-call window.
        meta['review_end_index'] = own_report['index']
        meta['reviewed_at'] = own_report['at']
    if native.timestamp(meta.get('reviewed_at') or meta['timestamp']) < native.timestamp(outcome['started_at']):
        raise ValueError('stale reviewer')
    if not outcome.get('contract_confirmed'):
        raise ValueError('confirm the concrete contract first')
    prompt = '\n'.join(text for role, text, _ in messages if role == 'user')
    final = next((text for role, text, phase in reversed(messages) if role == 'assistant' and (phase != 'commentary' or own_attempt)), '')
    if own_report:
        final = own_report['text']
    all_assignments = [*meta.get('assignments', []), *meta.get('dispatch_assignments', [])]
    bound_assignments = [row for row in all_assignments
                         if review_assignment_kind(outcome, row['text'], product_cwd,
                                                   allow_bound_dispatch=(own_attempt and row.get('source_kind') == 'native-parent-dispatch'))]
    has_current_subject = outcome['original_goal'] in prompt or bool(bound_assignments)
    if (outcome['id'] not in prompt and not own_attempt and not bound_assignments) or not has_current_subject:
        raise ValueError('review assignment must identify the outcome')
    if any(correction not in prompt for correction in outcome.get('corrections', [])) and not any(
            review_assignment_kind(outcome, row['text'], product_cwd,
                                   allow_bound_dispatch=(own_attempt and row.get('source_kind') == 'native-parent-dispatch')) in {'digest', 'bound-dispatch'}
            for row in all_assignments):
        raise ValueError('review omits the latest accepted scope corrections')
    assignments = [row for row in all_assignments
                   if review_assignment_kind(outcome, row['text'], product_cwd,
                                             allow_bound_dispatch=(own_attempt and row.get('source_kind') == 'native-parent-dispatch')) or
                   (own_attempt and outcome['original_goal'] in row['text'])]
    if not assignments:
        raise ValueError('native source has no current scope-bound assignment window')
    # Preserve the original current-subject assignment window. A repeated
    # identical assignment must not strand real calls made after its first
    # occurrence and before the duplicate.
    assignment = min(assignments, key=lambda row: native.timestamp(row.get('at') or outcome['started_at']))
    if cross_cwd_product:
        product_token = re.compile(
            r'(?<![\w./-])' + re.escape(str(product_cwd)) + r'(?:[.!?](?=\s|$)|(?=\s|$))')
        exact_product_assignments = [row for row in assignments
                                     if product_token.search(row['text'])]
        if not exact_product_assignments:
            raise ValueError('product-root native reviewer needs the exact assigned product root in its native assignment')
        assignment = min(exact_product_assignments, key=lambda row: native.timestamp(row.get('at') or outcome['started_at']))
    if cross_cwd_research:
        declared = []
        for literal in re.findall(r'(?:^|[;\n])\s*Target CWD:\s*([^;\n]+)', assignment['text'], re.I):
            path = local_native_path(literal.strip(' `\"\''))
            if not path.is_absolute():
                raise ValueError('research Target CWD must be absolute')
            declared.append(path.resolve())
        if set(declared) != {product_cwd}:
            raise ValueError('independent research assignment needs exact normalized Target CWD; tool output or a neighboring path is not assignment')
    after = max(native.timestamp(reuse_original['evidence_after'] if reuse_original else outcome.get('evidence_after') or outcome['started_at']),
                native.timestamp(assignment['at'] or outcome['started_at']))
    dispatch_assignment = assignment.get('source_kind') == 'native-parent-dispatch'
    observations = [(call, output) for call, output in observations
                    if ((dispatch_assignment and call.get('_source_time') and
                         native.timestamp(assignment['at']) <= native.timestamp(call['_source_time'])) or
                        (not dispatch_assignment and call.get('_source_index') is not None and
                         call['_source_index'] > assignment['index']))
                    and call['_source_index'] < meta.get('review_end_index', -1)
                    and call.get('_source_time') and after <= native.timestamp(call['_source_time']) <= native.timestamp(meta.get('reviewed_at') or meta['timestamp'])]
    if scope_revision(outcome, cwd) != outcome['revision']:
        raise ValueError('owned revision changed; refresh the contract and actual evidence before review')
    if testing_reuse is not None:
        from lhc_testing_reuse import browser_sources, assessment
        observations = browser_sources(observations, product_cwd)
        reuse_report, _ = assessment(outcome, meta, observations, testing_reuse, reuse_original, product_cwd)
    lines = [line[len(MARKER):] for line in final.splitlines() if line.startswith(MARKER)]
    if comparison_quote and lines:
        raise ValueError('comparison quote binds original research prose, not a structured certificate')
    if len(lines) > 1:
        raise ValueError('ambiguous independent review summaries')
    report = (reuse_report if reuse_report is not None else json.loads(lines[0]) if lines else
              raw_review(outcome, final, observations, product_cwd, comparison_quote, source_readiness_reuse))
    source_readiness_result = source_publication_result = None
    if source_mode:
        from lhc_source_publication import permission_unchanged, publication_readback, source_readiness
        metadata = outcome.get('source_publication') or {}
        source = next((row for row in outcome.get('scope_sources', [])
                      if row.get('source') == metadata.get('permission_source')), None)
        if not permission_unchanged(metadata, source, outcome.get('corrections', [])):
            raise ValueError('source-publication permission no longer matches the current source and latest scope')
        if source_readiness_reuse is not None and 'technical' not in (report.get('stages') or {}):
            source_readiness_result = source_readiness_reuse
        else:
            source_readiness_result = source_readiness(
                metadata, observations, product_cwd, floor=outcome.get('evidence_after'),
                before=meta.get('review_end_index'),
            )
        if 'publication' in (report.get('stages') or {}):
            source_publication_result = publication_readback(
                metadata, observations, product_cwd, outcome, outcome.get('evidence_after'),
                before=meta.get('review_end_index'),
            )
            if report.get('source_publication') != source_publication_result:
                raise ValueError('source-publication report does not bind the exact native push and current remote commit')
    canary = outcome['canary']
    revision = scope_revision(outcome, cwd)
    for key, expected in {'outcome_id': outcome['id'], 'revision': revision,
                          'target': canary['target'], 'scenario': canary['scenario'], 'expected': canary['expected']}.items():
        if report.get(key) != expected:
            raise ValueError('review mismatch: ' + key)
    if report.get('assignment_verdict') != 'complete' or not report.get('comparison'):
        raise ValueError('independent expected/observed comparison required')
    product = report.get('product_verdict')
    if source_mode:
        expected_product = 'source-published' if source_publication_result else 'source-ready'
        if product != expected_product or (report.get('stages', {}).get('consumer') is not None):
            raise ValueError('source-only review must distinguish readiness from publication and cannot claim an app consumer result')
    elif product not in {'pass', 'changes-required'} or (outcome['task_class'] in ENGINEERING and product != 'pass'):
        raise ValueError('product result does not satisfy engineering canary')
    coverage = outcome.get('coverage', [])
    if source_mode and coverage:
        raise ValueError('source-publication cannot replace explicit application coverage')
    if outcome['task_class'] == 'testing' and not coverage:
        raise ValueError('testing needs explicit assigned coverage')
    by_call = {call.get('call_id'): (call, output) for call, output in observations if call.get('call_id')}
    technical_partial = _technical_partial_assessment(final)
    resolved = (None if source_mode else
                outcome['canary']['target'] if technical_partial else
                consumer_target(outcome, observations, product_cwd))
    for item in coverage:
        claim = report.get('coverage', {}).get(item)
        if (not isinstance(claim, dict) or claim.get('verdict') not in {'passed', 'defect'}
                or not claim.get('expected') or not claim.get('observed')):
            raise ValueError('each assigned coverage claim needs expected/observed comparison')
        refs = claim.get('evidence_calls') or []
        if not refs or not all(ref in by_call for ref in refs) or not any(
                real_observation(*by_call[ref], resolved, 'consumer', outcome['task_class'], product_cwd) for ref in refs):
            raise ValueError('assigned coverage needs its actual native consumer observations')
        if not browser_journey(refs, by_call, canary['target']):
            raise ValueError('each browser coverage claim needs its action/result observations')
    staging = report.get('staging_push')
    if staging:
        branch = staging.get('branch', '')
        if (branch in {'main', 'master'} or not branch or not staging.get('reason')
                or staging.get('dependent_stage') not in {'technical', 'deploy'}):
            raise ValueError('staging push requires a non-main branch and genuine CI/deploy dependency')
        refs = staging.get('evidence_calls') or []
        def branch_push(ref):
            if ref not in by_call:
                return False
            text, words = command(by_call[ref][0])
            return words[:2] == ['git', 'push'] and branch in words and not any(w in {'main', 'master'} or w.endswith((':main', ':master')) for w in words)
        if not refs or not any(branch_push(ref) for ref in refs):
            raise ValueError('staging exception needs the actual branch push native source')
    updates = report.get('stages') or {}
    if not updates or set(updates) - set(STAGES):
        raise ValueError('review must cover known stages')
    # Validate the entire batch before any transition, including its order.
    completed = {stage for stage, row in outcome['stages'].items() if row['status'] in {'complete', 'not-applicable'}}
    last_call = -1
    call_order = {call.get('call_id'): i for i, (call, _) in enumerate(observations)}
    for stage in STAGES:
        if stage not in updates:
            continue
        if outcome['stages'][stage]['status'] == 'not-applicable':
            raise ValueError('review cannot add an excluded operation')
        prior = set(STAGES[:STAGES.index(stage)])
        if prior - completed:
            raise ValueError('unmet earlier stages: ' + ','.join(sorted(prior - completed)))
        row = updates[stage]
        refs = row.get('evidence_calls') or []
        if not row.get('expected') or not row.get('observed') or not refs or not all(ref in by_call for ref in refs):
            raise ValueError('each stage needs expected/observed comparison and actual native calls')
        source_reused_readback = bool(source_mode and stage == 'integration' and source_publication_result
                                      and refs == [source_publication_result['readback_call']])
        if min(call_order[ref] for ref in refs) <= last_call and not source_reused_readback:
            raise ValueError('source observations violate stage order')
        last_call = max(call_order[ref] for ref in refs)
        claim = outcome.get('stage_claims', {}).get(stage, canary)
        if source_mode and stage == 'technical':
            claim = {'target': 'project:' + str(product_cwd),
                     'expected': 'candidate:' + outcome['source_publication']['candidate_fingerprint']}
        if stage in {'deploy', 'publication', 'integration'} and (stage not in outcome.get('stage_claims', {}) or any(row.get(k) != claim[k] for k in ('target', 'expected'))):
            raise ValueError('remote stage requires its exact contract target/expected readback')
        if source_mode and stage == 'technical':
            if row.get('target') != 'project:' + str(product_cwd) or row.get('expected') != claim['expected']:
                raise ValueError('technical readiness must bind the immutable source candidate and exact project root')
            expected_refs = (set(_source_evidence_refs(source_readiness_result['read_calls'])) |
                             set(_source_evidence_refs(source_readiness_result['hash_calls'])))
            if set(refs) != expected_refs:
                raise ValueError('technical source readiness must cite each owned-file read and matching hash')
        if source_mode and stage == 'publication':
            if (not source_publication_result or source_publication_result['readback_call'] not in refs or
                    row.get('expected') != 'candidate:' + outcome['source_publication']['candidate_fingerprint']):
                raise ValueError('publication needs the native push, exact current branch readback, and candidate blob proof')
        if source_mode and stage == 'integration':
            policy = outcome.get('integration_policy') or {}
            if (not source_publication_result or policy.get('branch') != outcome['source_publication']['branch'] or
                    policy.get('remote') != outcome['source_publication']['remote'] or
                    policy.get('ownership') != 'owned' or
                    (policy.get('branch') in {'main', 'master'} and not policy.get('main_permission_confirmed'))):
                raise ValueError('source integration retains exact existing remote, ownership, and main permission gates')
            if source_publication_result['readback_call'] not in refs:
                raise ValueError('integration needs exact target-branch candidate commit/tree/blob proof')
        if stage == 'consumer' and not browser_journey(refs, by_call, canary['target']):
            raise ValueError('browser open/login alone is not the assigned action and result')
        if stage == 'integration' or (stage == 'publication' and outcome.get('integration_policy') and not source_mode):
            policy = outcome.get('integration_policy')
            if not policy:
                raise ValueError('integration target/ownership unresolved; never default to main')
            branch = policy['branch']
            if not policy.get('target_scope_confirmed') or not policy.get('repository') or remote_binding(product_cwd, policy['remote']) != policy['repository']:
                raise ValueError('integration remote is unresolved or changed; preserve pending')
            if branch in {'main', 'master'} and policy['ownership'] != 'owned':
                raise ValueError('shared/external upstream main is owner-only')
            if branch in {'main', 'master'} and not policy.get('main_permission_confirmed'):
                raise ValueError('owned/write access is not human merge consent for this actual repository')
            def target_readback(ref):
                call, output = by_call[ref]
                _, words = command(call)
                if words[:2] == ['git', 'ls-remote']:
                    return words == ['git', 'ls-remote', policy['remote'], 'refs/heads/' + branch]
                try:
                    return json.loads(output).get('baseRefName') == branch
                except (ValueError, AttributeError):
                    return False
            reads = [ref for ref in refs if target_readback(ref) and real_observation(*by_call[ref], claim['target'], stage, outcome['task_class'], product_cwd, claim['expected'])]
            if not reads:
                raise ValueError('integration readback must prove the configured branch/head')
            if stage == 'integration' and branch not in {'main', 'master'}:
                smoke = [ref for ref in refs if real_observation(*by_call[ref], resolved, 'consumer', outcome['task_class'], product_cwd)
                         and call_order[ref] > max(call_order[r] for r in reads)]
                if not smoke or not browser_journey(smoke, by_call, canary['target']):
                    raise ValueError('dev integration needs actual integrated smoke after branch readback')
        observed_target = resolved if stage == 'consumer' else claim['target']
        if source_mode and stage in {'technical', 'publication', 'integration'}:
            pass  # Specialized source/hash and commit/ref proof was checked above.
        elif not any(real_observation(*by_call[ref], observed_target, stage, outcome['task_class'], product_cwd, claim['expected']) for ref in refs):
            raise ValueError('echo/health/test-only/wrong-target receipt is not the assigned consumer operation')
        completed.add(stage)
    if reuse_original:
        outcome['testing_reuse_binding'] = {
            'contract_call': testing_reuse['contract_call'],
            'authorization_index': testing_reuse['authorization_index'],
            'assessment_index': testing_reuse['assessment_index'],
            'original_evidence_after': reuse_original['evidence_after'],
            'historical_revision': reuse_original['revision'],
            'current_product_acceptance': False,
            'calls': {ref: {'at': by_call[ref][0]['_source_time'], 'index': by_call[ref][0]['_source_index']}
                      for ref in report['stages']['consumer']['evidence_calls']}}
    current_stage_fingerprints = stage_contract_fingerprints(outcome)
    for stage, row in updates.items():
        source_stage_level = ('independent-source-review' if source_mode and stage == 'technical' else
                              'source-publication-readback' if source_mode and stage in {'publication', 'integration'} else None)
        outcome['stages'][stage].update(status='complete', evidence=[{
            'manifest': str(path.resolve()), 'reviewer': sid, 'revision': reuse_original['revision'] if reuse_original else revision,
            'native_model': meta.get('model'),
            'consumer_target': resolved if stage == 'consumer' else None,
            'verification_level': source_stage_level or ('self-check' if own_attempt else 'independent-review'),
            'calls': row['evidence_calls'], 'expected': row['expected'], 'observed': row['observed'],
            'contract_fingerprint': current_stage_fingerprints[stage],
            **({'source_candidate': outcome['source_publication']['candidate_fingerprint'],
                'source_readiness': source_readiness_result} if source_mode and stage == 'technical' else {}),
            **({'published_commit': source_publication_result['commit'],
                'publisher_call': source_publication_result['publisher_call'],
                'ref': source_publication_result['ref']} if source_mode and stage in {'publication', 'integration'} else {}),
        }])
    if staging:
        outcome['staging_push'] = {**staging, 'manifest': str(path.resolve()), 'reviewer': sid}
    if comparison_quote:
        outcome['comparison_binding'] = {'quote': comparison_quote, 'reviewer': sid, 'original_index': own_report['index'],
                                         'original_at': own_report['at'], 'verification_level': 'self-check',
                                         'claims': research_comparison_binding(outcome, final, observations, product_cwd, comparison_quote)}
    if own_report and (outcome['task_class'] == 'research' or
                       _technical_partial_assessment(own_report['text'])):
        outcome['review_assessment'] = {'reviewer': sid, 'index': own_report['index'], 'at': own_report['at']}
    outcome.update(product_verdict=product, revision=revision, coverage_evidence=report.get('coverage', {}))
    outcome['verification_level'] = 'independent-source-review' if source_mode else ('self-check' if own_attempt else 'independent-review')
    if outcome.get('release_handoff') and outcome['stages']['integration']['status'] == 'complete':
        outcome['release_handoff']['status'] = 'awaiting-owner'
    if source_mode:
        required_source_stages = {'technical', 'publication'} | ({'integration'} if outcome['stages']['integration']['status'] == 'pending' else set())
        source_complete = all(stage in completed or outcome['stages'][stage]['status'] == 'complete'
                              for stage in required_source_stages)
        outcome['product_verdict'] = 'source-published' if source_publication_result else 'source-ready'
        outcome['source_publication']['readiness'] = source_readiness_result
        if source_publication_result:
            outcome['source_publication']['published_commit'] = source_publication_result['commit']
            outcome['source_publication']['publication_evidence'] = source_publication_result
        outcome['canary']['status'] = 'complete' if source_complete else 'pending'
    else:
        outcome['canary']['status'] = 'complete' if 'consumer' in completed else 'pending'
    outcome['sources'] = list(dict.fromkeys([*outcome.get('sources', []), str(path.resolve())]))
