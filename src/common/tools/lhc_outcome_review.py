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
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

import lhc_milestone as native
from lhc_outcome import ENGINEERING, STAGES, scope_revision, remote_binding, product_paths, digest

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


def native_self_manifest(outcome, cwd, runtime, owner):
    from lhc_outcome import bounded_self_check
    if outcome['owner'] != {'harness': runtime, 'session_id': owner} or not (outcome['task_class'] in {'testing', 'research'} or bounded_self_check(outcome)):
        raise ValueError('native self-check closes only its own bounded assignment, never fullcycle/parent acceptance')
    archive = cwd / '.tmp/lhc-native-self'
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    if runtime == 'codex':
        home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
        candidates = []
        for candidate in (home / 'sessions').rglob('*' + owner + '*.jsonl'):
            raw = native.read(candidate)
            meta, _, _ = native.native_transcript(raw)
            if meta.get('id') == owner and Path(meta.get('cwd', '/unknown')).resolve() == cwd:
                candidates.append(candidate.resolve())
        if len(candidates) != 1:
            raise ValueError('own native Codex source unavailable/ambiguous; preserve pending')
        path = candidates[0]
        source = {'kind': 'native-file', 'location': str(path)}
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


def load_review(path):
    manifest = json.loads(native.read(path))
    if manifest.get('format') != 'agent-herder-transcript-manifest-v1':
        raise ValueError('use the existing native export_transcript manifest')
    target = manifest['target']
    raw = native.read(target['path'])
    if target.get('harness') == 'codex' and target.get('complete'):
        location = Path(target['source']['location']).resolve()
        location.relative_to((Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions').resolve())
        if target['source'].get('kind') != 'native-file' or not native.read(location).startswith(raw):
            raise ValueError('review export differs from native source')
        result = native.native_transcript(raw)
        rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
        result[0]['model'] = list(dict.fromkeys(row['payload']['model'] for row in rows
                                               if row.get('type') == 'turn_context' and row.get('payload', {}).get('model')))
        assignments, call_meta = [], {}
        for index, row in enumerate(rows):
            p = row.get('payload', {})
            if row.get('type') == 'response_item' and p.get('role') == 'user':
                assignments.append({'index': index, 'at': row.get('timestamp'), 'text': native.content(p.get('content'))})
            if p.get('type') in {'function_call', 'custom_tool_call'}:
                call_meta[p.get('call_id')] = (index, row.get('timestamp'))
            item = p.get('item') or {}
            if item.get('type') == 'CommandExecution':
                call_meta.setdefault(item.get('id'), (index, row.get('timestamp')))
        result[0]['assignments'] = assignments
        result[0]['own_reports'] = [{'index': i, 'at': row.get('timestamp'), 'text': native.content(row['payload'].get('content'))}
                                    for i, row in enumerate(rows) if row.get('payload', {}).get('role') == 'assistant'
                                    and native.content(row['payload'].get('content'))]
        result[0]['review_end_index'] = max((i for i, row in enumerate(rows) if row.get('payload', {}).get('role') == 'assistant'
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
    args = call.get('arguments') or call.get('input') or '{}'
    try:
        args = json.loads(args) if isinstance(args, str) else args
        directory = local_native_path(args.get('workdir') or args.get('cwd') or call.get('_native_cwd') or cwd)
        directory = (cwd / directory).resolve() if not directory.is_absolute() else directory.resolve()
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
            return target in words and (bool(words and Path(words[0]).name in {'curl', 'wget', 'agent-browser'}) or 'browser' in name)
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


def raw_review(outcome, final, observations, cwd, comparison_quote=None):
    """Small ordinary-report route; keep original prose as semantic assessment.

    No author PASS/map file and no rewriting the review. Complex unsupported
    prose stays explicit; the same existing reviewer may use the optional JSON
    line, rather than recursively hiring somebody to manufacture a certificate.
    """
    canary = outcome['canary']
    defect, positive = report_result(final)
    if not final.strip() and outcome['task_class'] == 'research':
        raise ValueError('no native assessment yet: send the actual source finding and expected/observed as a separate visible assistant message before review; FEEDBACK alone is not that message. Do not debug helper/session storage; preserve pending if unavailable')
    if not final.strip() or not (positive or defect or outcome['task_class'] == 'research'):
        raise ValueError('raw review must state its actual result; retain the original report')
    stages = {}
    by_call = {call.get('call_id'): (call, output) for call, output in observations if call.get('call_id')}
    resolved = consumer_target(outcome, observations, cwd)
    identity = target_identity(resolved, cwd)
    ordered_cli = (outcome['task_class'] == 'quickfix' and identity and identity[0] == 'python'
                   and all(outcome['stages'][s]['status'] == 'pending' for s in ('technical', 'consumer'))
                   and all(outcome['stages'][s]['status'] == 'not-applicable' for s in ('deploy', 'publication', 'integration')))
    positions = {ref: i for i, ref in enumerate(by_call)}
    technical_at = -1
    for stage in STAGES:
        if outcome['stages'][stage]['status'] != 'pending':
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


def own_assessment(outcome, text, observations, cwd, comparison_quote=None):
    if MARKER in text:
        return True
    defect, positive = report_result(text)
    # Never fall back over newer negative findings, even if unsupported/partial.
    if defect:
        return True
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


def accept_review(outcome, state, path, cwd, owner, comparison_quote=None):
    from lhc_outcome import bounded_self_check
    meta, messages, observations = load_review(path)
    sid = meta.get('id') or meta.get('session_id')
    own_attempt = sid == owner and (outcome['task_class'] in {'testing', 'research'} or bounded_self_check(outcome))
    native_cwd = Path(meta.get('cwd', '/unknown'))
    cross_cwd_research = sid != owner and outcome['task_class'] == 'research' and native_cwd.resolve() != cwd
    if (sid == owner and not own_attempt) or not native_cwd.is_absolute() or (native_cwd.resolve() != cwd and not cross_cwd_research):
        raise ValueError('review must be independent and for this exact project')
    # The existing reviewer can deliberately inspect a bounded case from its
    # original project. Missing tool cwd remains that native original cwd,
    # never silently defaults to the case being accepted.
    observations = [({**call, '_native_cwd': str(native_cwd.resolve())}, output) for call, output in observations]
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
        return negative_binding or own_assessment(outcome, text, observations, cwd, comparison_quote)
    own_report = next((report for report in reversed(meta.get('own_reports', []))
                       if selected_assessment(report)), None) if own_attempt else None
    if comparison_quote and (not own_report or not source_finding_quote(outcome, own_report['text'], observations, cwd, comparison_quote)):
        raise ValueError('comparison quote must bind the current unchanged native source finding; never skip a newer negative assessment')
    if not own_report and own_attempt and outcome['task_class'] == 'research' and any(
            native.timestamp(report['at']) >= native.timestamp(outcome['started_at'])
            and source_finding_quote(outcome, report['text'], observations, cwd, report['text'])
            for report in meta.get('own_reports', [])):
        raise ValueError('fresh source finding needs a semantic comparison binding, not a reread: retain the report and use review --native-self --comparison-quote with its unchanged source-finding passage; self-check only')
    if own_report:
        # Own commentary is available before the final response; source call
        # order still ends at that actual report, never at a later export call.
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
    if (outcome['id'] not in prompt and not own_attempt) or outcome['original_goal'] not in prompt:
        raise ValueError('review assignment must identify the outcome')
    if any(correction not in prompt for correction in outcome.get('corrections', [])):
        raise ValueError('review omits the latest accepted scope corrections')
    assignments = [row for row in meta.get('assignments', []) if outcome['original_goal'] in row['text']
                   and (own_attempt or outcome['id'] in row['text'])]
    if not assignments:
        raise ValueError('native source has no current scope-bound assignment window')
    assignment = max(assignments, key=lambda row: row['index'])
    if cross_cwd_research and str(cwd) not in assignment['text']:
        raise ValueError('independent research assignment must identify the exact target cwd; tool output is not assignment')
    after = max(native.timestamp(outcome.get('evidence_after') or outcome['started_at']),
                native.timestamp(assignment['at'] or outcome['started_at']))
    observations = [(call, output) for call, output in observations
                    if call.get('_source_index') is not None and call['_source_index'] > assignment['index']
                    and call['_source_index'] < meta.get('review_end_index', -1)
                    and call.get('_source_time') and after <= native.timestamp(call['_source_time']) <= native.timestamp(meta.get('reviewed_at') or meta['timestamp'])]
    if scope_revision(outcome, cwd) != outcome['revision']:
        raise ValueError('owned revision changed; refresh the contract and actual evidence before review')
    lines = [line[len(MARKER):] for line in final.splitlines() if line.startswith(MARKER)]
    if comparison_quote and lines:
        raise ValueError('comparison quote binds original research prose, not a structured certificate')
    if len(lines) > 1:
        raise ValueError('ambiguous independent review summaries')
    report = json.loads(lines[0]) if lines else raw_review(outcome, final, observations, cwd, comparison_quote)
    canary = outcome['canary']
    revision = scope_revision(outcome, cwd)
    for key, expected in {'outcome_id': outcome['id'], 'revision': revision,
                          'target': canary['target'], 'scenario': canary['scenario'], 'expected': canary['expected']}.items():
        if report.get(key) != expected:
            raise ValueError('review mismatch: ' + key)
    if report.get('assignment_verdict') != 'complete' or not report.get('comparison'):
        raise ValueError('independent expected/observed comparison required')
    product = report.get('product_verdict')
    if product not in {'pass', 'changes-required'} or (outcome['task_class'] in ENGINEERING and product != 'pass'):
        raise ValueError('product result does not satisfy engineering canary')
    coverage = outcome.get('coverage', [])
    if outcome['task_class'] == 'testing' and not coverage:
        raise ValueError('testing needs explicit assigned coverage')
    by_call = {call.get('call_id'): (call, output) for call, output in observations if call.get('call_id')}
    resolved = consumer_target(outcome, observations, cwd)
    for item in coverage:
        claim = report.get('coverage', {}).get(item)
        if (not isinstance(claim, dict) or claim.get('verdict') not in {'passed', 'defect'}
                or not claim.get('expected') or not claim.get('observed')):
            raise ValueError('each assigned coverage claim needs expected/observed comparison')
        refs = claim.get('evidence_calls') or []
        if not refs or not all(ref in by_call for ref in refs) or not any(
                real_observation(*by_call[ref], resolved, 'consumer', outcome['task_class'], cwd) for ref in refs):
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
        if min(call_order[ref] for ref in refs) <= last_call:
            raise ValueError('source observations violate stage order')
        last_call = max(call_order[ref] for ref in refs)
        claim = outcome.get('stage_claims', {}).get(stage, canary)
        if stage in {'deploy', 'publication', 'integration'} and (stage not in outcome.get('stage_claims', {}) or any(row.get(k) != claim[k] for k in ('target', 'expected'))):
            raise ValueError('remote stage requires its exact contract target/expected readback')
        if stage == 'consumer' and not browser_journey(refs, by_call, canary['target']):
            raise ValueError('browser open/login alone is not the assigned action and result')
        if stage == 'integration' or (stage == 'publication' and outcome.get('integration_policy')):
            policy = outcome.get('integration_policy')
            if not policy:
                raise ValueError('integration target/ownership unresolved; never default to main')
            branch = policy['branch']
            if not policy.get('target_scope_confirmed') or not policy.get('repository') or remote_binding(cwd, policy['remote']) != policy['repository']:
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
            reads = [ref for ref in refs if target_readback(ref) and real_observation(*by_call[ref], claim['target'], stage, outcome['task_class'], cwd, claim['expected'])]
            if not reads:
                raise ValueError('integration readback must prove the configured branch/head')
            if stage == 'integration' and branch not in {'main', 'master'}:
                smoke = [ref for ref in refs if real_observation(*by_call[ref], resolved, 'consumer', outcome['task_class'], cwd)
                         and call_order[ref] > max(call_order[r] for r in reads)]
                if not smoke or not browser_journey(smoke, by_call, canary['target']):
                    raise ValueError('dev integration needs actual integrated smoke after branch readback')
        observed_target = resolved if stage == 'consumer' else claim['target']
        if not any(real_observation(*by_call[ref], observed_target, stage, outcome['task_class'], cwd, claim['expected']) for ref in refs):
            raise ValueError('echo/health/test-only/wrong-target receipt is not the assigned consumer operation')
        completed.add(stage)
    for stage, row in updates.items():
        outcome['stages'][stage].update(status='complete', evidence=[{
            'manifest': str(path.resolve()), 'reviewer': sid, 'revision': revision,
            'native_model': meta.get('model'),
            'consumer_target': resolved if stage == 'consumer' else None,
            'verification_level': 'self-check' if own_attempt else 'independent-review',
            'calls': row['evidence_calls'], 'expected': row['expected'], 'observed': row['observed'],
        }])
    if staging:
        outcome['staging_push'] = {**staging, 'manifest': str(path.resolve()), 'reviewer': sid}
    if comparison_quote:
        outcome['comparison_binding'] = {'quote': comparison_quote, 'reviewer': sid, 'original_index': own_report['index'],
                                         'original_at': own_report['at'], 'verification_level': 'self-check',
                                         'claims': research_comparison_binding(outcome, final, observations, cwd, comparison_quote)}
    outcome.update(product_verdict=product, revision=revision, coverage_evidence=report.get('coverage', {}))
    outcome['verification_level'] = 'self-check' if own_attempt else 'independent-review'
    if outcome.get('release_handoff') and outcome['stages']['integration']['status'] == 'complete':
        outcome['release_handoff']['status'] = 'awaiting-owner'
    outcome['canary']['status'] = 'complete' if 'consumer' in completed else 'pending'
    outcome['sources'] = list(dict.fromkeys([*outcome.get('sources', []), str(path.resolve())]))
