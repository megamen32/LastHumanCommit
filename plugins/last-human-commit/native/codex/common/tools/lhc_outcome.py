#!/usr/bin/env python3
"""Task outcome in the existing session state. No network, permissions or scheduler.

Classification is a conservative hint. A native independent review supplies the
semantic comparison; this helper never interprets a tool receipt as business PASS.
"""
import argparse
import copy
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
import shlex
import os
from urllib.parse import unquote, urlsplit

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import lhc_milestone as native

STAGES = ('technical', 'deploy', 'consumer', 'publication', 'integration')
VERIFICATION_KINDS = ('standard', 'source-publication')
ENGINEERING = {'quickfix', 'fullcycle'}
RU_INSTALL = r'установ(?:и|ить)\s+(?!(?:что|факт\w*|статус\w*|причин\w*)\b)\w+'
REPAIR = re.compile(r'\b(?:fix|repair|implement|build|create|write|add|make|configure|deploy|install|update|change)\b|исправ|почин|реализ|созда|сделай|обнов|' + RU_INSTALL + r'|развер', re.I)
TEST = re.compile(r'\b(?:test|tester|testing|try|verify)\b|тестиров|проверь|протестир', re.I)
RESEARCH = re.compile(r'\b(?:research|review|audit|inspect|explain|investigate|read.only)\b|исслед|ревью|аудит|объясни|прочитай', re.I)
ACTIONABLE_UNKNOWN = re.compile(r'^\s*(?:please\s+)?(?:ensure|resolve|refactor|optimize|migrate|обеспечь|перенеси|проведи)\b', re.I)
HOLD = {'Interrupt', 'SessionEnd', 'PermissionRequest', 'session.error', 'ToolFailure'}
NO_DELEGATION = re.compile(r"не\s+делегируй|не\s+нанимай|\b(?:do not|don't|never)\s+delegate\b|\bno\s+delegation\b", re.I)
HERDER_ENVELOPE = re.compile(
    r'<agent-herder-(?:coordination|repo-peers)\b[^>]*>.*?</agent-herder-(?:coordination|repo-peers)\s*>',
    re.I | re.S,
)
HERDER_ORIGIN_PROLOG = re.compile(
    r'^\s*(?:🤖 Сообщение от ИИ через Agent Herder\s*\r?\n)?'
    r'<agent-herder-origin version="1" kind="agent-relay" transport="(?:new_or_resume|deliver)"\s*/>\s*\r?\n(?:\r?\n)?',
    re.I,
)
LEGACY_HERDER_RELAY_PREFIX = re.compile(r'^\s*🤖 Сообщение от ИИ через Agent Herder\s*\r?\n+', re.I)
HERDER_DEFERRED_ITEM = re.compile(
    r'^- id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}) :: (.*)$', re.I,
)
CODEX_SESSION_UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
HERDER_RELAY_ATTRIBUTION = re.compile(
    r'^\s*🤖\s+(?:Codex\s+SID\b[^\r\n]*|'
    r'Codex\s+(?P<codex_sid>' + CODEX_SESSION_UUID + r')\s+·\s+'
    r'https://agent\.bezrabotnyi\.com/#/session/codex%3A(?P=codex_sid)|'
    r'Сообщение от AI-сессии\b[^\r\n]*(?:\r?\nОтправитель неизвестен: сессия не указана\.)?|'
    r'Сообщение от ИИ через Agent Herder[^\r\n]*)'
    r'\s*\r?\n(?:\r?\n)?', re.I,
)
EXPECTATION_CHANGE = re.compile(
    r'^\s*the\b[^.?!\n]{0,120}\b(?:must|should|needs to)\s+(?:be|return)\s+'
    r'[^.?!\n]{1,120}\b(?:rather than|instead of)\b', re.I,
)
CORRECTION_HEADER = re.compile(r'^\s*correction\s*:\s*', re.I)
EXPECTATION_VALUE = re.compile(
    r'^\s*the\b[^.?!\n]{0,120}\b(?:must|should|needs to)\s+(?:be|return)\s+'
    r'(.+?)\s+(?:rather than|instead of)\s+.+?[.!?]?\s*$', re.I,
)


def expectation_text(value):
    """Strip one explicit bounded correction label for expectation parsing."""
    return CORRECTION_HEADER.sub('', value, count=1)


def bounded_self_check(outcome):
    # A leaf assignment can finish without claiming the parent's independent
    # milestone acceptance. A scope restriction never removes remote stages.
    scope = '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])
    independent = re.search(r'independent\s+(?:review|acceptance|verification|check|test)|независим.{0,25}(?:при[её]м|ревью|review|проверк|тест)', scope, re.I)
    return (outcome['task_class'] == 'quickfix' and outcome.get('delegation_prohibited') and not independent
            and all(outcome['stages'][s]['status'] == 'not-applicable'
                    for s in ('deploy', 'publication', 'integration')))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def positive_intent(goal):
    # Bounded clause handling, never a permission parser. Preserve raw scope;
    # the Lead confirms the hypothesis against the actual native user source.
    goal = re.sub(r'исправление[^.?!\n]*не\s+входит[^.?!\n]*', '', goal, flags=re.I)
    return re.sub(r"\b(?:do not|don't|never|no code changes)[^.?!\n]*|не (?:меняй|редактируй|создавай|деплой|исправляй)[^.?!\n]*", '', goal, flags=re.I)


def semantic_scope(goal):
    # OpenCode may quote the prompt; Herder coordination and relay prologs are
    # transport metadata. Raw input remains preserved as source evidence.
    scope = HERDER_ENVELOPE.sub('', goal).strip()
    deferred = _deferred_messages(scope)
    if deferred is None:
        scope = _strip_relay_attribution(scope)
    else:
        messages, remainder = deferred
        scope = '\n\n'.join(text for text in
                             [_strip_relay_attribution(message) for message in messages] +
                             [_strip_relay_attribution(remainder)] if text)
    if scope.startswith('"') and scope.endswith('"'):
        scope = scope[1:-1]
    return scope.strip()


def _deferred_messages(prompt):
    """Parse only Agent Herder's exact leading deferred-message frame."""
    lines = prompt.splitlines()
    if not lines or lines[0] != '<agent-herder-deferred>':
        return None
    try:
        close = lines.index('</agent-herder-deferred>', 1)
    except ValueError:
        return None
    messages = []
    current = None
    for line in lines[1:close]:
        item = HERDER_DEFERRED_ITEM.fullmatch(line)
        if line.startswith('- id=') and not item:
            return None
        if item:
            if current is not None:
                messages.append('\n'.join(current))
            current = [item.group(2)]
        elif current is not None:
            current.append(line)
        else:
            return None
    if current is None:
        return None
    messages.append('\n'.join(current))
    return messages, '\n'.join(lines[close + 1:]).lstrip('\n')


def _strip_relay_attribution(text):
    text = HERDER_ORIGIN_PROLOG.sub('', text, count=1).strip()
    text = HERDER_RELAY_ATTRIBUTION.sub('', text, count=1).strip()
    text = LEGACY_HERDER_RELAY_PREFIX.sub('', text, count=1).strip()
    return text


def source_origin(prompt, scope_prompt=''):
    """Classify explicit relay attribution only; unmarked sources stay unknown."""
    raw_scope = HERDER_ENVELOPE.sub('', prompt).strip() if isinstance(prompt, str) else ''
    safe_scope = scope_prompt.strip() if isinstance(scope_prompt, str) else ''
    for value in (raw_scope, safe_scope):
        deferred = _deferred_messages(value)
        candidates = [value] if deferred is None else [*deferred[0], deferred[1]]
        if any(HERDER_ORIGIN_PROLOG.match(candidate) or HERDER_RELAY_ATTRIBUTION.match(candidate) or
               LEGACY_HERDER_RELAY_PREFIX.match(candidate) for candidate in candidates):
            return 'agent-relay'
    return 'unknown'


def scope_source_with_origin(source):
    """Annotate a copy without rewriting the original raw prompt."""
    result = dict(source)
    origin = source_origin(result.get('prompt', ''), result.get('scope_prompt', ''))
    if result.get('origin') == 'agent-relay' or origin == 'agent-relay':
        result['origin'] = 'agent-relay'
    else:
        result['origin'] = 'unknown'
    if isinstance(result.get('scope_prompt'), str):
        result['scope_prompt'] = semantic_scope(result['scope_prompt'])
    return result


def _verified_native_assignment_source(business):
    """Expose only a receipt-bound child dispatch as a typed scope source."""
    source = business.get('native_assignment_source')
    identity = business.get('native_identity')
    assignment = identity.get('assignment') if isinstance(identity, dict) else None
    prompt = source.get('prompt') if isinstance(source, dict) else None
    if (not isinstance(source, dict) or source.get('source_kind') != 'native-parent-dispatch' or
            not isinstance(identity, dict) or identity.get('verified') is not True or
            not isinstance(assignment, dict) or assignment.get('status') != 'bound' or
            not isinstance(prompt, str) or not prompt.strip() or
            source.get('origin') != 'agent-relay' or
            source.get('source') != ('native-parent-dispatch:' + str(identity.get('parent_native_id')) + ':' +
                                     str(identity.get('dispatch_call_id')) + ':' + str(assignment.get('prompt_sha256'))) or
            source.get('parent_native_id') != identity.get('parent_native_id') or
            source.get('child_native_id') != identity.get('native_id') or
            source.get('dispatch_call_id') != identity.get('dispatch_call_id') or
            source.get('parent_journal_path') != identity.get('parent_journal_path') or
            source.get('child_journal_path') != identity.get('journal_path') or
            source.get('prompt_sha256') != assignment.get('prompt_sha256') or
            prompt != assignment.get('prompt') or
            hashlib.sha256(prompt.encode()).hexdigest() != assignment.get('prompt_sha256')):
        return None
    return scope_source_with_origin(source)


def classify(goal):
    intent = positive_intent(semantic_scope(goal))
    # A leading status request scopes the whole prompt, even if it names a
    # task class in the requested status value.
    status_request = re.search(
        r'^\s*(?:read.only\s+)?(?:status\b|what is\b|what.s\b|how is\b|when\b|'
        r'how is (?:the )?(?:task|work|progress) progressing\b|(?:give|send|provide) (?:me )?(?:a )?(?:progress|feedback) update\b|'
        r'статус|как дела|когда|какая версия|как продвигается (?:задача|работа)|дай обратную связь по прогрессу)',
        intent,
        re.I,
    )
    later_intent = intent[status_request.end():] if status_request else ''
    later_intent = re.sub(r'\b(?:progress|feedback)\s+update\b', '', later_intent, flags=re.I)
    if status_request and not (REPAIR.search(later_intent) or TEST.search(later_intent)):
        return 'status'
    # Explicit assignment header scopes the work; engineering terms below it
    # can describe the subject being reviewed, rather than authorize execution.
    header = re.search(r'(?:^|[.!?\n])\s*RESEARCH\s+ONLY\s*:', intent, re.I)
    if header and not REPAIR.search(intent[:header.start()]):
        return 'research'
    if EXPECTATION_CHANGE.search(expectation_text(intent)):
        return 'quickfix'
    # The declaration is a class hint only when it stands as an affirmative
    # clause. Do not let a literal fixture label or a negated mention override
    # the task's actual intent.
    declaration = re.search(
        r'(?:^|[.!?;]\s+|\n)\s*(?<![\"\'`])LHC\s+fullcycle\s+'
        r'с\s+видимым\s+бизнес-результатом\b'
        r'(?=\s*(?:[.;,]|$))',
        intent,
        re.I,
    )
    if declaration:
        prefix = intent[:declaration.start()].lower()
        context = re.search(r'(?:literal|fixture|example|quoted|строк[аеу]|литерал|пример|цитат)[^.!?\n:]*:\s*$', prefix, re.I)
        if not context:
            return 'fullcycle'
    if REPAIR.search(intent):
        # Scope and risk override lexical hints like "fix": a risky repair,
        # feature, architecture decision, or change across several boundaries
        # is a fullcycle even when phrased as one assigned leaf.
        broad = re.search(
            r'\b(?:full|entire|complete|all|new feature|feature|architecture|redesign|risky|'
            r'multiple|several|cross.cut(?:ting)?)\b|'
            r'весь|целиком|полностью|нов(?:ая|ую) функцию|архитектур|нескольк.{0,30}(?:сервис|модул|репозитор)|'
            r'широк.{0,25}(?:измен|риск|охват)|рискованн.{0,20}(?:ремонт|исправ)', intent, re.I)
        small = re.search(r'\b(?:fix|repair|small|minor|typo|bounded)\b|исправ|почин|мелк|опечат|ограниченн.{0,20}(?:исправ|измен)', intent, re.I)
        return 'quickfix' if small and not broad else 'fullcycle'
    if TEST.search(intent):
        return 'testing'
    if RESEARCH.search(intent):
        return 'research'
    return 'unknown'


NEGATIVE_LIST = r'(?:no|without|do not|без)\s+(?:(?:deploy|push|publish|merge)\s*(?:[,/]\s*(?:(?:and|or|и|или)\s+)?|(?:and|or|и|или)\s+))*'
EXCLUSIONS = {
    'deploy': (NEGATIVE_LIST + r'deploy\b|(?:no|without|do not)\s+(?:\w+\s+)?deploy|без\s*(?:push/)?deploy|не\s+(?:деплой|выкладывай)'
               r'|(?:no|without|do not)\s+[^.!?\n]{0,100}\b(?:deployment|runtime\s+actions?)\b'),
    'publication': NEGATIVE_LIST + r'(?:push|publish)\b|не\s+публику',
    'integration': NEGATIVE_LIST + r'(?:main\s+)?merge\b|external.repo|PR.only|внешн.{0,30}репозит|не\s+(?:merge|слива)',
}


def applicable(kind, goal):
    intent = positive_intent(goal)
    needed = list(STAGES) if kind == 'fullcycle' else (['technical', 'consumer'] if kind == 'quickfix' else ['consumer'] if kind in {'testing', 'research', 'unknown'} else [])
    if kind in ENGINEERING:
        if re.search(r'\b(?:deploy|install|rollout)\b|развер|выкат|' + RU_INSTALL, intent, re.I):
            needed += ['deploy']
        if re.search(r'\b(?:push|publish|PR|commit|merge)\b|опублику|коммит|слия', intent, re.I):
            needed += ['publication']
        if re.search(r'\bmerge\b|слей|слия', intent, re.I):
            needed += ['integration']
    stages = {stage: {'status': 'pending' if stage in needed else 'not-applicable',
                      'basis': 'task-class:' + kind, 'evidence': []} for stage in STAGES}
    for stage, pattern in EXCLUSIONS.items():
        if match := re.search(pattern, goal, re.I):
            stages[stage] = {'status': 'not-applicable', 'basis': 'original-scope:' + match.group(), 'evidence': []}
    return stages


def product_root_path(outcome, cwd):
    """Resolve product files separately from the immutable native session root."""
    return Path(outcome.get('product_root') or cwd).resolve()


def _brief_path(prompt):
    paths = re.findall(r'(?<![\w./-])/(?:[^\s`"\'<>]+/)?\.agents/tasks/briefs/[^\s`"\'<>]+\.md', prompt)
    return paths[0] if len(paths) == 1 else None


def _brief_read_assignment(outcome, source, root, paths):
    """Bind one standalone brief read to the exact native assignment."""
    sid = outcome.get('owner', {}).get('session_id')
    source_id = source.get('source', '')
    prefix = 'native-user-prompt:' + str(sid) + ':'
    prompt = source.get('scope_prompt') or source.get('prompt', '')
    brief = _brief_path(prompt)
    if not sid or not brief or not source_id.startswith(prefix) or not outcome.get('native_source'):
        return False
    location = Path(outcome['native_source']).resolve()
    sessions = (Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions').resolve()
    try:
        location.relative_to(sessions)
    except ValueError:
        return False
    wanted = source_id[len(prefix):]
    session_root = Path(outcome.get('cwd', '/unknown')).resolve()
    source_index = None
    source_matches = 0
    candidate = None
    meta_seen = False
    try:
        with location.open('rb') as stream:
            for index, raw in enumerate(stream):
                if len(raw) > native.MAX_BYTES or not raw.endswith(b'\n'):
                    return False
                row = json.loads(raw)
                payload = row.get('payload') or {}
                if row.get('type') == 'session_meta':
                    if (payload.get('id') != sid or
                            Path(payload.get('cwd', '/unknown')).resolve() != session_root):
                        return False
                    meta_seen = True
                elif row.get('type') == 'response_item' and payload.get('type') == 'message' and payload.get('role') == 'user':
                    text = native.content(payload.get('content'))
                    metadata = payload.get('internal_chat_message_metadata_passthrough') or {}
                    turn = payload.get('turn_id') or payload.get('turnId') or metadata.get('turn_id') or 'current'
                    digest = hashlib.sha256(text.strip().encode()).hexdigest()[:12]
                    if (wanted == f'{turn}:{digest}' and text.strip()[:2048] == source.get('prompt', '').strip()
                            and semantic_scope(text) == prompt.strip()):
                        source_index = index
                        source_matches += 1
                elif source_index is not None and row.get('type') == 'event_msg' and payload.get('type') == 'item_completed':
                    item = payload.get('item') or {}
                    if (item.get('type') != 'CommandExecution' or
                            Path(brief).name not in str(item.get('command') or '')):
                        continue
                    if item.get('exit_code') != 0:
                        return False
                    command = item.get('command') or []
                    if (len(command) != 3 or Path(command[0]).name not in {'bash', 'sh'} or
                            command[1] not in {'-c', '-lc'}):
                        return False
                    try:
                        words = shlex.split(command[2])
                        if len(words) == 2 and words[0] == 'cat':
                            file_arg = words[1]
                        elif (len(words) == 4 and words[:2] == ['sed', '-n'] and
                              re.fullmatch(r'1,[1-9][0-9]*p', words[2])):
                            file_arg = words[3]
                        else:
                            return False
                        if not re.fullmatch(r'[A-Za-z0-9_./-]+', file_arg) or file_arg.startswith('-'):
                            return False
                        uri = urlsplit(item.get('cwd') or '')
                        workdir = unquote(uri.path) if uri.scheme == 'file' and uri.netloc in {'', 'localhost'} else str(item.get('cwd') or '')
                        directory = Path(workdir)
                        if not directory.is_absolute():
                            directory = session_root / directory
                        if directory.resolve() != session_root or (directory.resolve() / file_arg).resolve() != Path(brief).resolve():
                            return False
                    except (ValueError, IndexError, TypeError):
                        return False
                    output = item.get('aggregated_output') or ''
                    if not output:
                        return False
                    candidate = output
                    break
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    if not meta_seen or source_index is None or source_matches != 1 or candidate is None:
        return False
    task = re.search(r'parallel-([a-z0-9]+)\.md$', Path(brief).name, re.I)
    if not task:
        return False
    lines = candidate.splitlines()
    if (not lines or not lines[0].startswith('# ') or
            not re.search(r'(?<!\w)' + re.escape(task.group(1)) + r'(?!\w)', lines[0][2:], re.I)):
        return False
    root_rows = [line for line in lines if line.strip().startswith('Canonical checkout:')]
    if len(root_rows) != 1 or root_rows[0].strip() != 'Canonical checkout: ' + str(root):
        return False
    path_headers = [i for i, line in enumerate(lines) if line.strip() == 'Exclusive writable paths:']
    if len(path_headers) != 1:
        return False
    assigned = []
    for line in lines[path_headers[0] + 1:]:
        if not line.strip():
            break
        match = re.fullmatch(r'\s*-\s+(.+?)\s*', line)
        if not match:
            break
        assigned.append(match.group(1))
    normalized_assigned = set()
    try:
        for path in assigned:
            try:
                normalized_assigned.add((root / path).resolve().relative_to(root).as_posix())
            except ValueError:
                continue
        normalized_requested = {(root / path).resolve().relative_to(root).as_posix() for path in paths}
    except (OSError, ValueError):
        return False
    return bool(normalized_assigned and normalized_requested.issubset(normalized_assigned))


def _project_name_mentions(prompt, repository):
    """Return true only for an affirmative, unquoted full repository name."""
    if not isinstance(prompt, str) or not isinstance(repository, str) or repository.count('/') != 1:
        return False
    name = repository.split('/', 1)[1].removesuffix('.git')
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name)
    variants = {name, spaced}
    pattern = re.compile(r'(?<![\w])(?:' + '|'.join(
        re.escape(value).replace(r'\ ', r'\s+') for value in sorted(variants, key=len, reverse=True)
    ) + r')(?![\w])', re.I)
    # Quotes and fenced/code examples cannot establish a direct project assignment.
    clean = re.sub(r'```.*?```|`[^`\n]*`|"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|\'[^\'\n]*\'', ' ', prompt, flags=re.S)
    mentions = list(pattern.finditer(clean))
    if not mentions:
        return False
    for match in mentions:
        clause = re.split(r'[.!?;\n]', clean[:match.start()])[-1]
        if re.search(r"\b(?:do not|don't|never|not|without|no|preserve|avoid)\b|\b(?:не|нельзя|запрещ|сохрани|не трогай)\b", clause, re.I):
            return False
    return True


def _repository_mentioned(prompt, repository):
    """Match a repository name neutrally, including in a negated sentence."""
    if not isinstance(prompt, str) or not isinstance(repository, str) or repository.count('/') != 1:
        return False
    name = repository.split('/', 1)[1].removesuffix('.git')
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name)
    variants = {name, spaced}
    name_pattern = r'(?<![\w])(?:' + '|'.join(
        re.escape(value).replace(r'\ ', r'\s+') for value in sorted(variants, key=len, reverse=True)
    ) + r')(?![\w])'
    full_pattern = r'(?<![\w.-])' + re.escape(repository) + r'(?![\w.-])'
    return bool(re.search(name_pattern, prompt, re.I) or re.search(full_pattern, prompt, re.I))


def _native_user_source_record(outcome, source):
    """Return one exact native user prompt and its immutable journal coordinates."""
    sid = outcome.get('owner', {}).get('session_id')
    source_id = source.get('source', '')
    prefix = f'native-user-prompt:{sid}:'
    if not sid or not source_id.startswith(prefix) or not outcome.get('native_source'):
        return None
    parts = source_id[len(prefix):].rsplit(':', 1)
    if len(parts) != 2 or not re.fullmatch(r'[0-9a-f]{12}', parts[1]):
        return None
    location = Path(outcome['native_source']).resolve()
    sessions = (Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions').resolve()
    try:
        location.relative_to(sessions)
        expected_cwd = Path(outcome.get('cwd', '')).resolve(strict=True)
    except (OSError, ValueError):
        return None
    matches = []
    user_rows = []
    meta_seen = False
    try:
        with location.open('rb') as stream:
            for index, raw in enumerate(stream):
                if index > 50000 or len(raw) > native.MAX_BYTES or not raw.endswith(b'\n'):
                    return None
                row = json.loads(raw)
                payload = row.get('payload') or {}
                if row.get('type') == 'session_meta':
                    if payload.get('id') != sid or Path(payload.get('cwd', '')).resolve() != expected_cwd:
                        return None
                    meta_seen = True
                    continue
                if (row.get('type') != 'response_item' or payload.get('type') != 'message' or
                        payload.get('role') != 'user'):
                    continue
                text = native.content(payload.get('content'))
                metadata = payload.get('internal_chat_message_metadata_passthrough') or {}
                turn = payload.get('turn_id') or payload.get('turnId') or metadata.get('turn_id') or 'current'
                digest_value = hashlib.sha256(text.strip().encode()).hexdigest()[:12]
                user_rows.append({'index': index, 'at': row.get('timestamp'), 'turn_id': str(turn), 'prompt': text})
                saved_scope = source.get('scope_prompt')
                scope_matches = (semantic_scope(text) == saved_scope if isinstance(saved_scope, str) and saved_scope
                                 else text.strip()[:2048] == str(source.get('prompt', '')).strip())
                if (parts[0] == str(turn) and parts[1] == digest_value and
                        text.strip()[:2048] == str(source.get('prompt', '')).strip() and
                        scope_matches):
                    matches.append({'index': index, 'at': row.get('timestamp'), 'turn_id': str(turn),
                                    'prompt': text, 'sha256': hashlib.sha256(text.strip().encode()).hexdigest()})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    if (not meta_seen or len(matches) != 1 or source.get('origin') == 'agent-relay' or
            source_origin(source.get('prompt', ''), source.get('scope_prompt', '')) == 'agent-relay' or
            source_origin(matches[0]['prompt']) == 'agent-relay'):
        return None
    record = matches[0]
    record['later_user_messages'] = [row for row in user_rows if row['index'] > record['index']]
    return record


def _native_user_source_matches(outcome, source):
    """Revalidate one exact current native user prompt from the session journal."""
    return _native_user_source_record(outcome, source) is not None


def _valid_publication_manifest(repo_root, manifest_path, reviewer_id, *, outcome_id, candidate,
                                published_commit=None, ref=None, report_kind):
    try:
        manifest_path = Path(manifest_path).resolve(strict=True)
        archive = (repo_root / '.tmp/lhc-native-review').resolve(strict=True)
        manifest_path.relative_to(archive)
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        target = manifest['target']
        source_path = Path(target['source']['location']).resolve(strict=True)
        sessions = (Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions').resolve()
        source_path.relative_to(sessions)
        snapshot_path = Path(target['path']).resolve(strict=True)
        snapshot_path.relative_to(archive)
        if (manifest.get('format') != 'agent-herder-transcript-manifest-v1' or
                target.get('harness') != 'codex' or target.get('sessionId') != reviewer_id or
                target.get('complete') is not True or target.get('source', {}).get('kind') not in {'native-file', 'native-file-window'}):
            return False
        if target.get('source', {}).get('kind') == 'native-file':
            snapshot = snapshot_path.read_bytes()
            with source_path.open('rb') as stream:
                source_prefix = stream.read(len(snapshot))
                if source_prefix != snapshot:
                    return False
        else:
            source = target['source']
            start, end, first_line = (source.get(key) for key in ('start_byte', 'end_byte', 'start_line'))
            if any(type(value) is not int for value in (start, end, first_line)) or not 0 < start < end:
                return False
            with source_path.open('rb') as stream:
                header = stream.readline(native.MAX_BYTES + 1)
                if not header.endswith(b'\n') or len(header) + end - start > native.MAX_BYTES:
                    return False
                stream.seek(start - 1)
                if stream.read(1) != b'\n':
                    return False
                stream.seek(0)
                prefix = stream.read(start)
                if prefix.count(b'\n') != first_line:
                    return False
                stream.seek(start)
                body = stream.read(end - start)
                if len(body) != end - start or not body.endswith(b'\n'):
                    return False
                snapshot = snapshot_path.read_bytes()
                if snapshot != header + body:
                    return False
        rows = [json.loads(line) for line in snapshot.splitlines() if line.strip()]
        if not rows or rows[0].get('type') != 'session_meta':
            return False
        header = rows[0].get('payload') or {}
        if (header.get('id') != reviewer_id or Path(header.get('cwd', '')).resolve() != repo_root):
            return False
        user_texts, assistant_texts = [], []
        for row in rows:
            payload = row.get('payload') or {}
            if row.get('type') != 'response_item' or payload.get('type') != 'message':
                continue
            text = native.content(payload.get('content'))
            if payload.get('role') == 'user':
                user_texts.append(text)
            elif payload.get('role') == 'assistant' and payload.get('phase') not in {'analysis', 'commentary'}:
                assistant_texts.append(text)
        bound_assignment = any(outcome_id in text and candidate in text and str(repo_root) in text
                               for text in user_texts)
        source_ready_report = any(
            'APPROVE BOUNDED' in text and 'source-ready' in text and
            outcome_id in text and candidate in text for text in assistant_texts)
        publication_report = any(
            'APPROVE BOUNDED' in text and 'source-published' in text and
            isinstance(published_commit, str) and published_commit in text and
            isinstance(ref, str) and ref in text for text in assistant_texts)
        required_report = (source_ready_report if report_kind == 'source-ready' else
                           publication_report if report_kind == 'source-published' else False)
        if not (bound_assignment and required_report):
            return False
        with source_path.open('rb') as stream:
            for index, raw in enumerate(stream):
                if index > 100 or len(raw) > native.MAX_BYTES:
                    return False
                row = json.loads(raw)
                payload = row.get('payload') or {}
                if row.get('type') == 'session_meta':
                    return (payload.get('id') == reviewer_id and
                            Path(payload.get('cwd', '')).resolve() == repo_root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False
    return False


def _verified_historical_source_publication(saved, root):
    """Verify immutable historical source-publication identity, not current PASS."""
    publication = saved.get('source_publication') or {}
    repository = publication.get('repository')
    remote = publication.get('remote')
    candidate = publication.get('candidate_fingerprint')
    owned_files = publication.get('owned_files')
    base = publication.get('base')
    head = publication.get('candidate_head')
    commit = publication.get('published_commit')
    ref = publication.get('ref')
    if (saved.get('verification_kind') != 'source-publication' or
            publication.get('schema') != 'lhc-source-publication-v1' or
            publication.get('root') != str(root) or not isinstance(repository, str) or
            not re.fullmatch(r'[^/\s]+/[^/\s]+', repository) or
            remote not in {'origin'} or publication.get('branch') != 'main' or ref != 'refs/heads/main' or
            not re.fullmatch(r'[0-9a-f]{40,64}', str(base)) or
            not re.fullmatch(r'[0-9a-f]{40,64}', str(head)) or
            not re.fullmatch(r'[0-9a-f]{40,64}', str(commit)) or
            not isinstance(owned_files, dict) or not owned_files or
            any(not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts or
                not name or not re.fullmatch(r'[0-9a-f]{64}', str(digest))
                for name, digest in owned_files.items()) or
            not re.fullmatch(r'[0-9a-f]{64}', str(candidate))):
        return None
    candidate_body = {key: publication[key] for key in (
        'root', 'repository', 'remote', 'branch', 'ref', 'base', 'candidate_head',
        'owned_files', 'permission_source', 'permission_quote')}
    full_body_candidate = hashlib.sha256(
        json.dumps(candidate_body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    content_body = {key: publication[key] for key in ('root', 'candidate_head', 'owned_files')}
    content_candidate = hashlib.sha256(
        json.dumps(content_body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if candidate not in {full_body_candidate, content_candidate}:
        return None
    from lhc_source_publication import historical_publication_commit_matches
    if not historical_publication_commit_matches(publication, root):
        return None
    if (saved.get('product_verdict') != 'source-published' or
            (saved.get('integration_policy') or {}).get('repository') != repository or
            (saved.get('integration_policy') or {}).get('remote') != remote or
            (saved.get('integration_policy') or {}).get('branch') != 'main'):
        return None
    readiness = publication.get('readiness') or {}
    paths = set(owned_files)
    if (set(readiness.get('read_calls', [])) != paths or
            set(readiness.get('hash_calls', [])) != paths):
        return None
    publication_receipt = publication.get('publication_evidence') or {}
    if (publication_receipt.get('base') != base or publication_receipt.get('commit') != commit or
            publication_receipt.get('ref') != ref or not publication_receipt.get('publisher_call') or
            not publication_receipt.get('readback_call')):
        return None
    if publication.get('published_commit') != commit:
        return None
    stages = saved.get('stages') or {}
    technical_rows = [row for row in (stages.get('technical') or {}).get('evidence', [])
                      if isinstance(row, dict) and row.get('verification_level') == 'independent-source-review' and
                      row.get('source_candidate') == candidate and
                      set((row.get('source_readiness') or {}).get('read_calls', {})) == paths and
                      set((row.get('source_readiness') or {}).get('hash_calls', {})) == paths]
    publication_rows = [row for row in (stages.get('publication') or {}).get('evidence', [])
                        if isinstance(row, dict) and row.get('verification_level') == 'source-publication-readback' and
                        row.get('published_commit') == commit and row.get('ref') == ref and
                        row.get('expected') == 'candidate:' + candidate]
    owner_id = (saved.get('owner') or {}).get('session_id')
    for technical in technical_rows:
        for published in publication_rows:
            if (not technical.get('reviewer') or technical.get('reviewer') == owner_id or
                    not published.get('reviewer') or published.get('reviewer') == owner_id or
                    technical.get('revision') != published.get('revision') or
                    published.get('publisher_call') != publication_receipt.get('publisher_call') or
                    publication_receipt.get('readback_call') not in published.get('calls', [])):
                continue
            if (not _valid_publication_manifest(
                    root, technical.get('manifest'), technical['reviewer'], outcome_id=saved.get('id'),
                    candidate=candidate, report_kind='source-ready') or
                    not _valid_publication_manifest(
                        root, published.get('manifest'), published['reviewer'], outcome_id=saved.get('id'),
                        candidate=candidate, published_commit=commit, ref=ref,
                        report_kind='source-published')):
                continue
            return {'repository': repository, 'remote': remote, 'root': str(root),
                    'candidate': candidate, 'candidate_head': head, 'base': base,
                    'owned_files': dict(owned_files), 'published_commit': commit, 'ref': ref,
                    'source_id': publication.get('permission_source'),
                    'technical_reviewer_id': technical.get('reviewer'),
                    'publication_reviewer_id': published.get('reviewer'),
                    'technical_manifest': technical.get('manifest'),
                    'publication_manifest': published.get('manifest')}
    return None


def _accepted_source_publication_binding(root):
    """Find one immutable, independently reviewed publication identity at root."""
    learning = root / '.agents/shared-session/learning'
    try:
        files = sorted(learning.glob('*.json'))
        if not files or len(files) > 256:
            return None
        matches = []
        for path in files:
            if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
                return None
            state = json.loads(path.read_text(encoding='utf-8'))
            saved = (state.get('business') or {}).get('outcome') or {}
            identity = _verified_historical_source_publication(saved, root)
            if identity:
                matches.append((identity['repository'], identity['remote']))
        # Repeated accepted receipts for one identity are equivalent; conflicting
        # repository or remote bindings remain ambiguous and fail closed.
        identities = set(matches)
        return next(iter(identities)) if len(identities) == 1 else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _metadata_project_root_mapping(outcome, source, root, paths, requested_root=None):
    if (not isinstance(source, dict) or source.get('origin') == 'agent-relay' or
            classify(source.get('scope_prompt') or source.get('prompt', '')) not in ENGINEERING or
            not _native_user_source_matches(outcome, source)):
        return False
    native_root = Path(outcome.get('cwd', '')).resolve(strict=True)
    try:
        requested_root = requested_root or root
        if (requested_root.parent != native_root or requested_root.is_symlink() or
                requested_root.resolve(strict=True) != root or root.parent != native_root):
            return False
        resolved = root.resolve(strict=True)
        if resolved.parent != native_root:
            return False
        remote = 'origin'
        binding = _accepted_source_publication_binding(resolved)
        if not binding:
            return False
        repository, proof_remote = binding
        project_name = repository.split('/', 1)[1].removesuffix('.git')
        normalized_name = re.sub(r'[^a-z0-9]', '', project_name.lower())
        aliases = []
        for child in native_root.iterdir():
            child_name = re.sub(r'[^a-z0-9]', '', child.name.lower())
            if child_name == normalized_name:
                aliases.append(child)
                if child.is_symlink() or child.resolve(strict=True) != resolved:
                    return False
        if aliases != [root] and not (len(aliases) == 1 and aliases[0] == root):
            return False
        if (remote != proof_remote or remote_binding(resolved, remote) != repository or
                Path(native.git(resolved, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != resolved or
                not _project_name_mentions(source.get('scope_prompt') or source.get('prompt', ''), repository)):
            return False
        # Bind only paths explicitly owned by the current parent task. The accepted
        # publication's old file list is identity evidence, never current ownership.
        prefix = root.name + '/'
        existing_mapping = (
            Path(outcome.get('product_root', '')).resolve() == resolved and
            outcome.get('product_root_source') == source.get('source')
        )
        owned = set()
        for item in outcome.get('owned_paths', []):
            value = Path(item)
            if value.is_absolute() or '..' in value.parts:
                continue
            text = value.as_posix()
            if text.startswith(prefix):
                owned.add(text[len(prefix):])
            elif existing_mapping:
                # A prior successful binding stores only product-relative paths.
                # Reuse that exact binding after revalidating its source, root,
                # repository identity, containment, and current ownership set.
                owned.add(text)
        requested = set()
        for item in paths:
            value = Path(item)
            if value.is_absolute() or '..' in value.parts:
                return False
            text = value.as_posix()
            relative = text[len(prefix):] if text.startswith(prefix) else text
            if not relative or relative.startswith('../'):
                return False
            candidate = resolved / relative
            candidate.resolve(strict=False).relative_to(resolved)
            cursor = resolved
            for part in Path(relative).parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    return False
            requested.add(relative)
        return bool(requested) and requested.issubset(owned)
    except (OSError, ValueError, TypeError):
        return False


def product_root_scope_allowed(outcome, source, root, paths):
    if not source or not isinstance(root, Path) or not root.is_absolute() or not paths:
        return False
    requested_root = root
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            return False
        for path in paths:
            (root / path).resolve().relative_to(root)
    except (OSError, ValueError):
        return False
    prompt = source.get('scope_prompt') or source.get('prompt', '')
    def names_path(value):
        return bool(re.search(r'(?<![\w./-])' + re.escape(str(value)) + r'(?![\w./-])', prompt))
    relative = [(root / path).resolve().relative_to(root).as_posix() for path in paths]
    direct = names_path(root) and all(names_path(path) or names_path(rel) for path, rel in zip(paths, relative))
    return direct or _brief_read_assignment(outcome, source, root, paths) or _metadata_project_root_mapping(
        outcome, source, root, paths, requested_root)


def product_paths(outcome, cwd):
    root = product_root_path(outcome, cwd)
    paths = outcome.get('owned_paths', [])
    for path in paths:
        try:
            (root / Path(path)).resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError('owned path resolves outside product root') from exc
    scope = '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])
    mentions = list(re.finditer(r'\bFEEDBACK\.md\b', scope, re.I))
    report = bool(mentions)
    for mention in mentions:
        # Every occurrence must be an observation-output directive. An earlier
        # product mention or ambiguous role conservatively retains the hash.
        prefix = re.split(r'[;!?\n]|\.(?=\s|$)', scope[:mention.start()])[-1]
        output = re.search(r'(?:сохран\w*|запиш\w*|save|record|keep)\s+[^.?!\n]{0,180}(?:результат|отзыв|наблюден|feedback|observations|results)[^.?!\n]{0,180}$', prefix, re.I)
        # The report can refer back to the explicitly named results: the real
        # request says "сообщи фактический результат ... сохрани их в FEEDBACK.md".
        output = output or re.search(r'\bсообщи\s+фактический\s+результат\s+и\s+ограничения\s+пользователю,\s+а\s+также\s+сохрани\s+их\s+в\s*$', prefix, re.I)
        report &= bool(output)
    # The explicitly requested observation report is evidence, not a new code
    # revision. Keep ownership, but writing feedback must not invalidate the
    # very native observations it records. A product edit retains its barrier.
    if report:
        paths = [p for p in paths if (root / p).resolve() != (root / 'FEEDBACK.md').resolve()]
    return paths


def scope_revision(outcome, cwd):
    # Explicit owned product only; clocks/receipts cannot manufacture progress.
    paths = product_paths(outcome, cwd)
    root = product_root_path(outcome, cwd)
    return digest([(p, native.file_hash(root, p)) for p in paths])


def remote_binding(cwd, remote):
    value = native.git(cwd, 'remote', 'get-url', remote).decode().strip()
    # Keep credentials out of state/logs. Only resolved GitHub repository IDs
    # are supported for automatic upstream-main close, not arbitrary remotes.
    match = re.fullmatch(r'(?:https://github.com/|git@github.com:)([\w.-]+/[\w.-]+?)(?:\.git)?', value)
    return match.group(1) if match else None


def _universal_project_main_permission(text, repository, branch):
    if branch != 'main' or not repository or 'airlock' in repository.casefold():
        return False
    segments = re.split(r'[.!?;\n]|,\s*(?:а|но|but|however)\b', text, flags=re.I)
    scope_pattern = re.compile(
        r'(?:для\s+всех\s+проект(?:ов|а)\s*,?\s*кроме\s+airlock\b|'
        r'all\s+projects?\s+except\s+airlock\b)', re.I)
    merge_pattern = re.compile(r'(?:\bmerge\b|мерж|слия|интегр)[^.!?;\n]{0,48}(?<![\w/-])main(?![\w/-])', re.I)
    for segment in segments:
        scope = scope_pattern.search(segment)
        merge = merge_pattern.search(segment)
        permission = re.search(r'allow|permit|authori[sz]|разреш|позвол', segment, re.I)
        secretary_only = re.search(r'(?:only|только)\s+(?:for\s+|для\s+)?(?:the\s+)?секретар|(?:only|только)\s+(?:for\s+|для\s+)?secretar', segment, re.I)
        if not (scope and merge and permission) or secretary_only:
            continue
        # Keep the universal scope close to the authorized merge action in the
        # same clause. A grant for tests or deployment cannot float across clauses.
        if abs(scope.start() - merge.start()) <= 100 and abs(permission.start() - merge.start()) <= 160:
            return True
    return False


def main_permission(source, quote, repository, branch):
    """Check one unchanged native quote; universal text needs explicit project scope."""
    if (not isinstance(source, dict) or not isinstance(source.get('prompt'), str) or
            not isinstance(quote, str) or not quote or not repository or
            source['prompt'].count(quote) != 1):
        return False
    clauses = re.split(r'[.!?;\n]', source['prompt'])
    comparison_quote = quote.rstrip('.!?;')
    clause = next((text for text in clauses if comparison_quote and comparison_quote in text), '')
    if not clause or re.search(r"do not|don't|never|forbidden|not allowed|not permitted|\bno\b|\bне\b|нельзя|запрещ", clause, re.I):
        return False
    if re.search(
            r'\b(?:only|только)\s+(?:if|when|after|once|until|unless|provided|for\s+the|для)\b|'
            r'\b(?:if|unless|provided\s+that|subject\s+to|pending|upon|until)\b|'
            r'\b(?:при\s+условии|если|при\s+согласовании|после\s+(?:моего\s+)?(?:одобрения|согласования|подтверждения|разрешения))\b|'
            r'\b(?:only|только)\s+(?:for\s+)?(?:the\s+)?(?:secretary|секретар)',
            clause, re.I):
        return False
    quote_index = source['prompt'].find(quote)
    before = source['prompt'][:quote_index].rstrip()
    after = source['prompt'][quote_index + len(quote):].lstrip()
    if ((before[-1:] in {'"', "'", '“', '‘', '`'}) or
            (after[:1] in {'"', "'", '”', '’', '`'})):
        return False
    owner, repo = repository.split('/', 1) if '/' in repository else ('', '')
    acronym = ''.join(c for c in repo if c.isupper())
    legacy_identity = bool(owner and repo and
                          re.search(r'(?<![\w.-])' + re.escape(owner) + r'(?![\w.])', quote, re.I) and
                          (re.search(r'(?<![\w.-])' + re.escape(repo) + r'(?![\w.-])', quote, re.I) or
                           (len(acronym) > 1 and re.search(r'(?<![A-Z0-9])' + re.escape(acronym) + r'(?![A-Z0-9])', quote))))
    legacy = bool(legacy_identity and re.search(r'allow|permit|authori[sz]|разреш|можно', quote, re.I) and
                  re.search(r'merge|интегр|слия|сливай|мерж', quote, re.I) and
                  re.search(r'(?:\binto\s+|\bto\s+|\bв\s+|\bна\s+)(?:branch\s+)?[`\'"]?' + re.escape(branch) + r'(?![\w/-]|\.[\w/-])', quote, re.I))
    return legacy or _universal_project_main_permission(quote, repository, branch)


def _permission_revoked_later(record, repository, branch):
    rows = list(record.get('later_user_messages', []))
    same_source_suffix = record.get('same_source_suffix')
    if isinstance(same_source_suffix, str) and same_source_suffix.strip():
        # This is a derived slice of the exact same native user prompt. The
        # original source index/hash/time remain the permission provenance.
        rows.insert(0, {'prompt': same_source_suffix})
    for later in rows:
        prompt = later.get('prompt', '')
        if source_origin(prompt) == 'agent-relay':
            continue
        prompt = HERDER_ENVELOPE.sub('', prompt)
        deferred = _deferred_messages(prompt)
        if deferred:
            prompt = deferred[1]
        if re.search(r'^\s*(?:i\s+revoke|i\s+withdraw|i\s+cancel)[^.!?\n]{0,100}\bpermission\b|^\s*(?:отзываю|отменяю)[^.!?\n]{0,100}разреш', prompt, re.I):
            return True
        direct_merge_denial = re.search(
            r'^\s*(?:(?:please|kindly|thank\s+you|thanks|пожалуйста|спасибо)\s*[,!.]?\s*)*'
            r'(?:do\s+not|don.t|never|no)\s+(?:(?:allow|permit)\s+)?merge\b|'
            r'^\s*(?:(?:please|kindly|thank\s+you|thanks|пожалуйста|спасибо)\s*[,!.]?\s*)*'
            r'не\s+(?:мержи|сливай|интегрируй)|'
            r'^\s*(?:(?:please|kindly|thank\s+you|thanks|пожалуйста|спасибо)\s*[,!.]?\s*)*'
            r'запрещаю\s+(?:мержить|сливать|интегрировать)',
            prompt, re.I)
        if not direct_merge_denial:
            continue
        denial_clause = re.split(r'[.!?\n]', prompt[direct_merge_denial.start():], maxsplit=1)[0]
        if re.search(r'\b(?:if|unless|provided|when|once)\b|если|при\s+условии|когда', denial_clause, re.I):
            continue
        project_mentioned = _repository_mentioned(prompt, repository)
        branch_mentioned = (branch in {'main', 'master'} and
                            bool(re.search(r'(?<![\w/-])' + re.escape(branch) + r'(?![\w/-])', prompt, re.I)))
        universal_mentioned = bool(re.search(r'for\s+all\s+projects|для\s+всех\s+проект', prompt, re.I))
        airlock_only = ('airlock' in prompt.casefold() and not project_mentioned and not universal_mentioned)
        if (project_mentioned or branch_mentioned or universal_mentioned) and not airlock_only:
            return True
    return False


def _permission_suffix_is_limited(suffix):
    """Reject an explicit condition or narrowed actor attached after a grant."""
    if not isinstance(suffix, str):
        return True
    text = suffix.strip()
    return bool(re.search(
        r'\b(?:only|только)\s+(?:if|when|after|once|until|unless|provided)\b|'
        r'\b(?:if|unless|provided\s+that|subject\s+to|pending|upon|until)\b.{0,100}'
        r'\b(?:approval|permission|consent|authorization|authorisation|одобрени\w*|разрешени\w*|'
        r'подтверждени\w*|согласовани\w*)\b|'
        r'\b(?:after|upon|до|после)\b.{0,80}\b(?:approval|permission|consent|authorization|'
        r'одобрени\w*|разрешени\w*|подтверждени\w*|согласовани\w*)\b|'
        r'\b(?:only|только)\s+(?:for\s+)?(?:the\s+)?(?:secretary|секретар)', text, re.I))


def resolve_main_permission_source(outcome, quote, repository, branch, state=None):
    """Resolve exactly one native source carrying the permission quote and bind its bytes."""
    if not quote or not repository or not isinstance(outcome.get('scope_sources'), list):
        return None
    if state and ((state.get('native_entry') or {}).get('finish_hold') not in {None, 'SessionEnd'} or
                  (outcome.get('question') or {}).get('phase') not in {None, 'answered'}):
        return None
    candidates = []
    for source in outcome.get('scope_sources', []):
        record = _native_user_source_record(outcome, source)
        if not record:
            continue
        direct_prompt = HERDER_ENVELOPE.sub('', record['prompt'])
        deferred = _deferred_messages(direct_prompt)
        if deferred:
            messages, direct_prompt = deferred
            if any(quote in message for message in messages):
                continue
        if direct_prompt.count(quote) != 1 or not main_permission({'prompt': direct_prompt}, quote, repository, branch):
            continue
        quote_end = direct_prompt.index(quote) + len(quote)
        same_message_suffix = direct_prompt[quote_end:]
        if _permission_suffix_is_limited(same_message_suffix):
            continue
        same_message_suffix = same_message_suffix.lstrip(' \t\r\n.!?,;:')
        permission_record = {**record, 'same_source_suffix': same_message_suffix}
        if _permission_revoked_later(permission_record, repository, branch):
            continue
        universal = _universal_project_main_permission(quote, repository, branch)
        candidates.append({'source': source['source'], 'quote': quote,
                           'sha256': record['sha256'], 'index': record['index'],
                           'at': record['at'], 'turn_id': record['turn_id'],
                           'kind': 'project-universal' if universal else 'exact-repository'})
    unique = {candidate['source']: candidate for candidate in candidates}
    return next(iter(unique.values())) if len(unique) == 1 else None


def _permission_binding_valid(outcome, state):
    policy = outcome.get('integration_policy') or {}
    if policy.get('branch') not in {'main', 'master'} or not policy.get('main_permission_confirmed'):
        return True
    source_id = policy.get('permission_source')
    source = next((row for row in outcome.get('scope_sources', []) if row.get('source') == source_id), None)
    record = _native_user_source_record(outcome, source) if source else None
    same_source_suffix = ''
    permission_quote = policy.get('permission_quote')
    direct_prompt = HERDER_ENVELOPE.sub('', record['prompt']) if record else ''
    if isinstance(permission_quote, str) and direct_prompt.count(permission_quote) == 1:
        same_source_suffix = direct_prompt.split(permission_quote, 1)[1]
    if not record or any((record.get('sha256') != policy.get('permission_source_sha256'),
                          record.get('index') != policy.get('permission_source_index'),
                          record.get('at') != policy.get('permission_source_at'),
                          _permission_suffix_is_limited(same_source_suffix),
                          _permission_revoked_later({**record, 'same_source_suffix':
                                                      same_source_suffix.lstrip(' \t\r\n.!?,;:')},
                                                     policy.get('repository', ''), policy.get('branch', '')),
                          not main_permission({'prompt': record['prompt']}, policy.get('permission_quote'),
                                              policy.get('repository'), policy.get('branch')))):
        return False
    if (policy.get('ownership') != 'owned' or
            remote_binding(product_root_path(outcome, Path(outcome.get('cwd') or '.')), policy.get('remote')) != policy.get('repository')):
        return False
    if state and ((state.get('native_entry') or {}).get('finish_hold') not in {None, 'SessionEnd'} or
                  (outcome.get('question') or {}).get('phase') not in {None, 'answered'}):
        return False
    if policy.get('permission_kind') == 'project-universal':
        project_source_id = policy.get('project_source') or policy.get('source')
        project_source = next((row for row in outcome.get('scope_sources', [])
                               if row.get('source') == project_source_id), None)
        root = product_root_path(outcome, Path(outcome.get('cwd') or '.'))
        paths = outcome.get('owned_paths', [])
        scope_outcome = outcome
        if root != Path(outcome.get('cwd') or '.').resolve():
            if outcome.get('product_root_source') != project_source_id:
                return False
            try:
                current_owned = []
                for item in paths:
                    value = Path(item)
                    if value.is_absolute() or '..' in value.parts:
                        return False
                    current_owned.append(root.name + '/' + value.as_posix())
                scope_outcome = {**outcome, 'owned_paths': current_owned}
            except (OSError, ValueError):
                return False
        if not project_source or not product_root_scope_allowed(scope_outcome, project_source, root, paths):
            return False
    return True


def verdict(outcome, state):
    if outcome['task_class'] == 'status':
        return 'complete'
    # Interrupt preserves the stop hold; it does not identify who stopped it.
    if (state.get('native_entry') or {}).get('finish_hold') not in {None, 'SessionEnd'}:
        return 'blocked'
    if outcome.get('question', {}).get('phase') not in {None, 'answered'}:
        return 'blocked'
    if state.get('business', {}).get('running_jobs'):
        return 'running'
    if outcome.get('blockers'):
        return 'blocked'
    if not _permission_binding_valid(outcome, state):
        return 'pending'
    if not outcome.get('contract_confirmed'):
        return 'pending'
    if any(s['status'] not in {'complete', 'not-applicable'} for s in outcome['stages'].values()):
        return 'pending'
    if outcome['stages']['integration']['status'] == 'complete' and not outcome.get('integration_policy'):
        return 'pending'  # Unknown target/ownership never defaults to main.
    policy = outcome.get('integration_policy')
    if policy and outcome['stages']['integration']['status'] != 'not-applicable':
        if not policy.get('target_scope_confirmed') or not policy.get('repository') or remote_binding(product_root_path(outcome, Path(outcome['cwd'])), policy['remote']) != policy['repository']:
            return 'pending'
        if policy['branch'] in {'main', 'master'} and not policy.get('main_permission_confirmed'):
            return 'pending'
    milestone = state.get('milestone') or {}
    if native.pending(milestone):
        return 'pending'
    return 'complete'


def observe(state, event, name, cwd, session, now):
    business = state.setdefault('business', {})
    raw_goal = native.first_goal(event, state)
    goal = semantic_scope(raw_goal)
    submitted = event.get('prompt')
    if (not business.get('outcome') and name == 'UserPromptSubmit' and isinstance(submitted, str)
            and not event.get('_lhc_control_prompt') and not submitted.startswith('🤖')
            and semantic_scope(submitted).startswith(semantic_scope(
                business.get('original_prompt_full') or business.get('original_prompt') or submitted))):
        raw_goal = submitted
        goal = semantic_scope(submitted)
    outcome = business.get('outcome')
    had_existing_outcome = outcome is not None
    source_identity = None
    accepted_source_snapshot = None
    if outcome and outcome.get('verification_kind') == 'source-publication':
        try:
            source_root = product_root_path(outcome, Path(cwd))
            source_identity = _verified_historical_source_publication(outcome, source_root)
        except (OSError, ValueError, TypeError):
            source_identity = None
        if (source_identity and outcome.get('finish_verdict') == 'complete' and
                (outcome.get('stages') or {}).get('technical', {}).get('status') == 'complete' and
                (outcome.get('stages') or {}).get('publication', {}).get('status') == 'complete'):
            accepted_source_snapshot = copy.deepcopy(outcome)
    previous_stage_fingerprints = outcome.get('stage_fingerprints') if outcome else None
    legacy_fingerprints = bool(outcome and 'stage_fingerprints' not in outcome)
    substantive_scope_change = False
    direct_scope_change = False
    raw_submitted = str(event.get('prompt') or '') if name == 'UserPromptSubmit' and not event.get('_lhc_control_prompt') else ''
    prompt_origin = source_origin(raw_submitted)
    prompt = semantic_scope(raw_submitted)
    # Unmarked role=user input keeps the legacy scope-update behavior, but its
    # stored origin remains unknown and never becomes a human-auth claim.
    processable_user_update = bool(prompt and not prompt.startswith('🤖') and prompt_origin != 'agent-relay')
    if not outcome and goal:
        kind = classify(goal)
        target = next(iter(native.URL.findall(goal)), 'project:' + str(cwd))
        expected = re.split(r'\b(?:verify|expected|check that)\b|проверь|ожидаем', semantic_scope(goal), maxsplit=1, flags=re.I)[-1].strip()
        assignment_source = _verified_native_assignment_source(business)
        scope_sources = [scope_source_with_origin(row)
                         for row in business.get('execution_context', {}).get('direct_user_messages', [])]
        if assignment_source and assignment_source.get('source') not in {row.get('source') for row in scope_sources}:
            scope_sources.append(assignment_source)
        outcome = business['outcome'] = {
            'id': digest([session, raw_goal]), 'owner': {'harness': business.get('runtime'), 'session_id': session},
            'original_goal': raw_goal, 'latest_correction': goal, 'task_class': kind,
            'started_at': now.isoformat(), 'cwd': str(cwd), 'native_source': business.get('transcript_path'), 'contract_confirmed': kind == 'status',
            'evidence_after': now.isoformat(),
            'delegation_prohibited': bool(NO_DELEGATION.search(goal)),
            'canary': {'scenario': goal[:512], 'target': target, 'expected': expected[:512], 'status': 'pending'},
            'owned_paths': [], 'stages': applicable(kind, goal), 'used_continuations': [],
            'class_confirmed': False, 'scope_sources': scope_sources,
            'actionable': kind in ENGINEERING | {'testing', 'research'} or bool(ACTIONABLE_UNKNOWN.search(goal)),
            'sources': [], 'product_verdict': 'not-tested', 'blockers': [],
        }
    if not outcome:
        return None
    if processable_user_update and prompt != semantic_scope(outcome['original_goal']):
        if NO_DELEGATION.search(prompt):
            outcome['delegation_prohibited'] = True
        # Read-only/status/peer updates cannot erase a previously accepted repair.
        kind = classify(prompt)
        actionable_correction = (kind in ENGINEERING | {'testing', 'research'}
                                 or bool(ACTIONABLE_UNKNOWN.search(prompt))
                                 or bool(EXPECTATION_CHANGE.search(expectation_text(prompt))))
        known_scope = {semantic_scope(str(value)) for value in [
            outcome.get('original_goal'), outcome.get('latest_correction'),
            *outcome.get('corrections', []),
            *(source.get('scope_prompt') or source.get('prompt', '')
              for source in outcome.get('scope_sources', [])),
        ] if value}
        if prompt in known_scope:
            actionable_correction = False
        if actionable_correction:
            direct_scope_change = True
            outcome['latest_correction'] = prompt
        if actionable_correction and re.search(r'\b(?:branch|upstream|integration|main|megamen32-dev)\b|ветк|интеграц', prompt, re.I):
            outcome.pop('integration_policy', None)
            outcome.pop('release_handoff', None)
        if kind in ENGINEERING | {'testing', 'research'} or ACTIONABLE_UNKNOWN.search(prompt) or EXPECTATION_CHANGE.search(expectation_text(prompt)):
            outcome['actionable'] = True
        if kind == 'unknown' and ACTIONABLE_UNKNOWN.search(prompt) and outcome['task_class'] == 'status':
            outcome['task_class'] = 'unknown'
            outcome['stages'] = applicable('unknown', prompt)
        expectation = EXPECTATION_VALUE.search(expectation_text(prompt))
        if expectation:
            if outcome['task_class'] in {'status', 'unknown'}:
                outcome['task_class'] = 'quickfix'
                outcome['stages'] = applicable('quickfix', prompt)
            outcome['canary']['expected'] = expectation.group(1).strip().rstrip('.!?')
        if kind in ENGINEERING or (kind == 'testing' and outcome['task_class'] in {'status', 'unknown'}):
            old_class = outcome['task_class']
            outcome['task_class'] = 'fullcycle' if old_class == 'fullcycle' else kind
            proposed = applicable(outcome['task_class'], prompt)
            for stage, row in proposed.items():
                # New requirements accumulate. Explicit latest exclusions apply
                # only to their operation, never cancel the whole repair.
                if row['status'] == 'pending' or row['basis'].startswith('original-scope:'):
                    current = outcome['stages'][stage]
                    if current['status'] == 'complete' and row['status'] == 'pending':
                        # Applicability additions do not replace a previously
                        # accepted row; semantic fingerprints below invalidate
                        # only stages whose actual contract changed.
                        continue
                    if current['status'] != row['status']:
                        outcome['stages'][stage] = row
            urls = native.URL.findall(prompt)
            if urls:
                outcome['canary']['target'] = urls[0]
                outcome['stage_claims'] = {}
        # A direct revocation can be just "Do not deploy anything", without
        # another repair verb. Apply only that exclusion, preserving the repair.
        for stage, pattern in EXCLUSIONS.items():
            if match := re.search(pattern, prompt, re.I):
                direct_scope_change = True
                outcome['stages'][stage] = {'status': 'not-applicable', 'basis': 'latest-scope:' + match.group(), 'evidence': []}
        if actionable_correction:
            for source in business.get('execution_context', {}).get('direct_user_messages', []):
                if source.get('source') not in {r.get('source') for r in outcome.get('scope_sources', [])}:
                    outcome.setdefault('scope_sources', []).append(scope_source_with_origin(source))
        if actionable_correction and prompt not in outcome.get('corrections', []):
            outcome.setdefault('corrections', []).append(prompt)
            outcome['contract_confirmed'] = False
            substantive_scope_change = True
    revision = scope_revision(outcome, cwd)
    if outcome.get('revision') and revision != outcome['revision']:
        outcome['evidence_after'] = now.isoformat()
        outcome['canary']['status'] = 'pending'
        # A changed candidate is a strict global floor for every stage.
        previous_stage_fingerprints = None
        substantive_scope_change = True
    outcome['revision'] = revision
    if legacy_fingerprints and had_existing_outcome and not substantive_scope_change:
        # An inert event (including a marked relay) must not rewrite historical
        # acceptance or move its floor merely because this version adds hashes.
        invalidated = set()
    else:
        invalidated = invalidate_changed_stage_evidence(outcome, previous_stage_fingerprints)
    if invalidated:
        outcome['evidence_after'] = now.isoformat()
    if 'consumer' in invalidated:
        outcome['canary']['status'] = 'pending'
    if name == 'PostToolUse':
        observe_job_progress(outcome, business, event, cwd)
        observe_question(outcome, event)
    if name in {'PostToolUse', 'PostToolUseFailure'}:
        observe_contract_rejection(outcome, event, name, session=session, cwd=cwd,
                                   runtime=business.get('runtime'))

    if source_identity and not direct_scope_change:
        if accepted_source_snapshot:
            for field in ('question', 'contract_rejection', 'blockers'):
                if outcome.get(field) != accepted_source_snapshot.get(field):
                    accepted_source_snapshot[field] = copy.deepcopy(outcome.get(field))
            accepted_source_snapshot['finish_verdict'] = verdict(accepted_source_snapshot, state)
            business['outcome'] = accepted_source_snapshot
            return accepted_source_snapshot

        # A prior observe may already have reopened the immutable published
        # candidate after working-tree bytes changed. Recover only when the
        # original accepted stage fingerprints still describe this exact scope.
        source_meta = outcome.get('source_publication') or {}
        stages = outcome.get('stages') or {}
        technical_evidence = next((row for row in (stages.get('technical') or {}).get('evidence', [])
                                   if row.get('verification_level') == 'independent-source-review' and
                                   row.get('source_candidate') == source_identity['candidate']), None)
        publication_evidence = next((row for row in (stages.get('publication') or {}).get('evidence', [])
                                     if row.get('verification_level') == 'source-publication-readback' and
                                     row.get('published_commit') == source_identity['published_commit'] and
                                     row.get('ref') == source_identity['ref']), None)
        historical_revision = (technical_evidence or {}).get('revision')
        historical_pair = bool(
            technical_evidence and publication_evidence and historical_revision and
            publication_evidence.get('revision') == historical_revision and
            outcome.get('owned_paths') and set(outcome['owned_paths']) == set(source_identity['owned_files']) and
            source_meta.get('candidate_fingerprint') == source_identity['candidate'] and
            str(product_root_path(outcome, Path(cwd))) == source_identity['root'])
        if historical_pair:
            comparison = copy.deepcopy(outcome)
            comparison['revision'] = historical_revision
            historical_fingerprints = stage_contract_fingerprints(comparison)
            technical_matches = technical_evidence.get('contract_fingerprint') == historical_fingerprints['technical']
            publication_matches = publication_evidence.get('contract_fingerprint') == historical_fingerprints['publication']
            integration_ok = stages.get('integration', {}).get('status') == 'not-applicable'
            integration_row = next((row for row in (stages.get('integration') or {}).get('evidence', [])
                                    if row.get('verification_level') == 'source-publication-readback' and
                                    row.get('published_commit') == source_identity['published_commit'] and
                                    row.get('ref') == source_identity['ref'] and
                                    (row.get('manifest'), row.get('reviewer')) ==
                                    (source_identity['publication_manifest'],
                                     source_identity['publication_reviewer_id'])), None)
            if stages.get('integration', {}).get('status') != 'not-applicable':
                integration_ok = bool(integration_row and
                                       integration_row.get('contract_fingerprint') == historical_fingerprints['integration'])
            if technical_matches and publication_matches and integration_ok:
                outcome['revision'] = historical_revision
                outcome['stage_fingerprints'] = historical_fingerprints
                stages['technical']['status'] = 'complete'
                stages['publication']['status'] = 'complete'
                if integration_ok and stages.get('integration', {}).get('status') != 'not-applicable':
                    stages['integration']['status'] = 'complete'
                outcome['canary']['status'] = 'complete'
                outcome['product_verdict'] = 'source-published'
    outcome['finish_verdict'] = verdict(outcome, state)
    return outcome


def next_stage(outcome):
    return next((s for s in STAGES if outcome['stages'][s]['status'] == 'pending'), None)


def fingerprint(outcome, milestone=None):
    return digest([outcome['id'], outcome['revision'], outcome.get('latest_correction'), next_stage(outcome), outcome['canary'],
                   [(k, v['status'], v['basis']) for k, v in sorted(outcome['stages'].items())],
                   outcome.get('question', {}).get('answer_ref'), sorted(outcome.get('finished_jobs', [])),
                   (milestone or {}).get('surface_key') if not outcome.get('owned_paths') else None])


def contract_scope_fingerprint(outcome):
    return digest([outcome['id'], outcome.get('latest_correction'), outcome.get('task_class'),
                   [(key, row['status'], row['basis']) for key, row in sorted(outcome['stages'].items())]])


def review_subject(outcome):
    """Return the deterministic, non-authorizing digest for a current review assignment."""
    policy = outcome.get('integration_policy') or {}
    def applicability(row):
        basis = str(row.get('basis') or '')
        if basis.startswith('source-publication:'):
            basis = 'source-publication'
        elif basis.startswith('task-class:'):
            basis = basis
        elif basis.startswith('original-scope:') or basis.startswith('latest-scope:'):
            basis = basis.split(':', 1)[0] + ':' + basis.split(':', 1)[1]
        return (row.get('status') == 'not-applicable', basis)

    semantic = {
        'format': 'lhc-review-subject-v1',
        'outcome_id': outcome.get('id'),
        'original_goal': outcome.get('original_goal'),
        'corrections': outcome.get('corrections', []),
        'task_class': outcome.get('task_class'),
        'product_root': str(product_root_path(outcome, Path(outcome.get('cwd') or '.'))),
        'owned_paths': outcome.get('owned_paths', []),
        'revision': outcome.get('revision'),
        'candidate': source_candidate_semantics(outcome),
        'canary': {key: outcome.get('canary', {}).get(key) for key in ('scenario', 'target', 'expected')},
        'coverage': outcome.get('coverage', []),
        'stage_claims': outcome.get('stage_claims', {}),
        'verification_kind': outcome.get('verification_kind', 'standard'),
        'policy': {key: policy.get(key) for key in ('remote', 'branch', 'ownership', 'repository')},
        'stages': {key: applicability(row)
                   for key, row in sorted(outcome.get('stages', {}).items())},
    }
    return 'lhc-review-subject-v1:' + digest(semantic)


def source_candidate_semantics(outcome):
    """Content/root identity without permission source references or destination policy."""
    source = outcome.get('source_publication') or {}
    if not source:
        return None
    return {'root': source.get('root'), 'candidate_head': source.get('candidate_head'),
            'owned_files': source.get('owned_files')}


def review_assignment_kind(outcome, text, product_root=None, *, allow_bound_dispatch=False):
    """Shared native assignment predicate; the digest is a subject ID, never authority."""
    if not isinstance(text, str):
        return None
    if outcome.get('id') not in text:
        if not allow_bound_dispatch or outcome.get('original_goal') not in text or not all(
                correction in text for correction in outcome.get('corrections', [])):
            return None
        return 'bound-dispatch'
    if outcome.get('original_goal') in text and all(
            correction in text for correction in outcome.get('corrections', [])):
        return 'legacy'
    canary = outcome.get('canary', {})
    root = str(product_root or product_root_path(outcome, Path(outcome.get('cwd') or '.')))
    readable = (root, canary.get('scenario'), canary.get('expected'))
    if review_subject(outcome) in text and all(value and value in text for value in readable):
        return 'digest'
    return None


STAGE_DEPENDENCIES = {
    'technical': ('technical', 'consumer', 'deploy', 'publication', 'integration'),
    'consumer': ('consumer',),
    'deploy': ('deploy', 'consumer'),
    'publication': ('publication', 'integration'),
    'integration': ('integration',),
}


def _correction_domains(outcome):
    consumer, broad = [], []
    for correction in outcome.get('corrections', []):
        value = semantic_scope(str(correction)).strip()
        if EXPECTATION_VALUE.search(expectation_text(value)):
            consumer.append(value)
        elif re.match(r'^\s*(?:evidence\s+)?(?:format|manifest|receipt|citation|source[- ]ref)\s+correction\s*:', value, re.I):
            # A typed evidence-shape repair does not alter the product contract.
            continue
        else:
            # Unknown substantive changes conservatively bind every stage.
            broad.append(value)
    return consumer, broad


def stage_contract_fingerprints(outcome):
    """Fingerprint only stage semantics; omit clocks, transport and source references."""
    claims = outcome.get('stage_claims', {})
    canary = outcome.get('canary', {})
    consumer_corrections, broad_corrections = _correction_domains(outcome)
    root = str(product_root_path(outcome, Path(outcome.get('cwd') or '.')))
    from lhc_outcome_review import project_matches, target_identity
    def target_semantics(value):
        if not value:
            return value
        if project_matches(value, Path(root)):
            return ('project', root)
        identity = target_identity(value, Path(root))
        return identity or value
    base = {'goal': outcome.get('original_goal'), 'corrections': broad_corrections,
            'class': outcome.get('task_class'), 'root': root, 'paths': outcome.get('owned_paths', []),
            'revision': outcome.get('revision'), 'kind': outcome.get('verification_kind', 'standard'),
            'candidate': source_candidate_semantics(outcome)}
    fields = {}
    fields['technical'] = {**base, 'coverage': outcome.get('coverage', [])}
    if outcome.get('verification_kind') == 'source-publication':
        fields['technical'].update({key: canary.get(key) for key in ('scenario', 'target', 'expected')})
    fields['consumer'] = {**base, 'scenario': canary.get('scenario'), 'target': target_semantics(canary.get('target')),
                          'expected': canary.get('expected'), 'coverage': outcome.get('coverage', []),
                          'corrections': [*broad_corrections, *consumer_corrections]}
    fields['deploy'] = {**base, 'claim': claims.get('deploy')}
    fields['publication'] = {**base, 'claim': claims.get('publication'),
                             'remote': (outcome.get('integration_policy') or {}).get('remote'),
                             'branch': (outcome.get('integration_policy') or {}).get('branch')}
    if outcome.get('verification_kind') == 'source-publication':
        fields['publication'].update({key: canary.get(key) for key in ('scenario', 'target', 'expected')})
        fields['publication']['corrections'] = [*broad_corrections, *consumer_corrections]
    fields['integration'] = {**base, 'claim': claims.get('integration'),
                             'remote': (outcome.get('integration_policy') or {}).get('remote'),
                             'branch': (outcome.get('integration_policy') or {}).get('branch'),
                             'ownership': (outcome.get('integration_policy') or {}).get('ownership')}
    return {stage: digest(fields[stage]) for stage in STAGES}


def invalidate_changed_stage_evidence(outcome, previous):
    current = stage_contract_fingerprints(outcome)
    if not isinstance(previous, dict) or set(previous) != set(STAGES):
        # Legacy complete rows have no trustworthy semantic binding. Preserve
        # evidence bytes but require a fresh stage-specific assessment.
        for row in outcome.get('stages', {}).values():
            if row.get('status') == 'complete':
                row['status'] = 'pending'
        outcome['stage_fingerprints'] = current
        return set(STAGES)
    changed = {stage for stage in STAGES if previous.get(stage) != current[stage]}
    invalidated = {dependent for stage in changed for dependent in STAGE_DEPENDENCIES[stage]}
    for stage in invalidated:
        row = outcome.get('stages', {}).get(stage, {})
        if row.get('status') == 'complete':
            row['status'] = 'pending'
    outcome['stage_fingerprints'] = current
    return invalidated


def contract_rejection_action(error):
    if 'research file target must name the scoped in-project source, not the requested report output' in error:
        return ('Use the exact in-project source path actually inspected as the research source/target; '
                'list the requested report path separately as an owned deliverable, never as source evidence.')
    if 'engineering contract requires explicit owned paths' in error:
        return 'Add --owned-path for each file the task actually owns; do not list unrelated outputs.'
    if 'canary must be concrete' in error:
        return 'Supply the concrete scenario, real target, and observable expected result.'
    if 'class correction requires an exact original/latest native user source' in error:
        return 'Use the exact native user source reference shown in scope_sources as --scope-source.'
    if 'stage readback needs both target and expected' in error:
        return 'Provide both --stage-target and --stage-expected for each claimed stage.'
    if 'N/A needs explicit original/latest scope' in error:
        return 'Remove the unsupported N/A claim or cite a native user scope that explicitly excludes that stage.'
    return 'Correct only the rejected contract field named above; do not retry the unchanged command.'


def outcome_error_text(value):
    if isinstance(value, str):
        parts = [value]
    elif isinstance(value, dict):
        parts = []
        for key in ('stderr', 'error', 'output', 'stdout'):
            item = value.get(key)
            if isinstance(item, str):
                parts.append(item)
        parts.extend(outcome_error_text(value[key]) for key in ('structuredContent', 'result')
                     if isinstance(value.get(key), (dict, str)))
        content = value.get('content')
        if isinstance(content, list):
            parts.extend(block.get('text', '') for block in content
                         if isinstance(block, dict) and isinstance(block.get('text'), str))
    else:
        return ''
    for part in parts:
        for line in part.splitlines():
            marker = line.find('LHC outcome:')
            if marker >= 0:
                return line[marker:].strip()[:4096]
            marker = line.find('research file target must name the scoped in-project source, not the requested report output')
            if marker >= 0:
                return line[marker:].strip()[:4096]
    return ''


def observe_contract_rejection(outcome, event, event_name, *, session, cwd, runtime):
    owner = outcome.get('owner') or {}
    observer_root = Path(cwd).resolve()
    outcome_root = Path(outcome.get('cwd', '/unknown')).resolve()
    if (owner.get('session_id') != session or owner.get('harness') != runtime or
            observer_root != outcome_root or owner.get('harness') not in {'codex', 'opencode', 'zcode', 'claude'}):
        return
    args = event.get('tool_input') or event.get('arguments') or {}
    command = args.get('cmd') or args.get('command') or '' if isinstance(args, dict) else ''
    try:
        lexer = shlex.shlex(str(command), posix=True, punctuation_chars=';&|><')
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return
    if (not words or not re.fullmatch(r'python(?:3(?:\.\d+)?)?', Path(words[0]).name) or
            any(word in {';', '&&', '||', '|', '>', '>>', '<'} or '$(' in word or '`' in word
                for word in words)):
        return
    tool_index = 1
    if tool_index < len(words) and words[tool_index] == '-B':
        tool_index += 1
    if tool_index >= len(words) or Path(words[tool_index]).name != 'lhc_outcome.py':
        return
    options = {}
    index = tool_index + 1
    while index < len(words):
        token = words[index]
        if token not in {'--cwd', '--runtime', '--session-id'} or index + 1 >= len(words):
            break
        if token in options:
            return
        options[token] = words[index + 1]
        index += 2
    if (set(options) not in ({'--runtime', '--session-id'}, {'--cwd', '--runtime', '--session-id'}) or index >= len(words) or
            words[index] not in {'contract', 'review'}):
        return
    command_cwd = options.get('--cwd')
    if command_cwd is None:
        command_cwd = args.get('workdir') or args.get('cwd') or event.get('cwd')
    if not isinstance(command_cwd, str) or not command_cwd.strip():
        return
    if command_cwd.startswith('file://'):
        uri = urlsplit(command_cwd)
        if uri.netloc not in {'', 'localhost'} or uri.query or uri.fragment:
            return
        command_cwd = unquote(uri.path)
    try:
        command_root = Path(command_cwd).expanduser().resolve()
    except (OSError, RuntimeError):
        return
    if (options['--session-id'] != owner.get('session_id') or
            options['--runtime'] != owner.get('harness') or command_root != outcome_root):
        return
    response = event.get('tool_response') or {}
    if event_name == 'PostToolUse' and isinstance(response, dict) and response.get('exit_code') == 0:
        outcome.pop('contract_rejection', None)
        return
    exact = outcome_error_text(response) or outcome_error_text(event.get('error'))
    if not exact:
        return
    outcome['contract_rejection'] = {
        'scope_fingerprint': contract_scope_fingerprint(outcome),
        'source': str(event.get('tool_call_id') or event.get('call_id') or 'native-review-attempt'),
        'exact_error': exact,
        'corrective_action': contract_rejection_action(exact),
    }


def observe_job_progress(outcome, business, event, cwd):
    watched = outcome.setdefault('watched_jobs', {})
    operations = {'technical': {'build', 'build-start', 'test', 'verify'},
                  'deploy': {'deploy', 'deployment', 'rollout'}}.get(next_stage(outcome), set())
    args = event.get('tool_input') or {}
    allowed_roots = {Path(cwd).resolve(), product_root_path(outcome, cwd)}
    same_cwd = not isinstance(args, dict) or not args.get('workdir') or Path(args['workdir']).resolve() in allowed_roots
    if same_cwd:
        for job_id, job in business.get('running_jobs', {}).items():
            if job.get('operation') in operations:
                watched.setdefault(job_id, digest([job_id, job.get('operation'), job.get('target'), outcome['revision']]))
    response = event.get('tool_response') or {}
    if not isinstance(response, dict):
        return
    job_id = str(response.get('job_id') or response.get('jobId') or response.get('session_id') or '')
    if job_id in watched and job_id not in business.get('running_jobs', {}) and (
            response.get('exit_code') == 0 or response.get('status') in {'completed', 'succeeded', 'success'}):
        finished = outcome.setdefault('finished_jobs', [])
        if watched[job_id] not in finished:
            finished.append(watched[job_id])


def reminder(outcome, tool):
    review_route = ('Research leaf: verify the assigned source and deliver the requested report '
                    'and raw expected/observed commentary before close bookkeeping. Use the documented review --native-self route; '
                    'level self-check, not independent parent product acceptance. '
                    "Use each command's --help; no helper implementation research unless assigned. "
                    'FEEDBACK alone is not a visible assistant assessment. Respect no-code limits: no scratch scripts. '
                    'On rejection, one supported reread or pending exact-error handoff; no helper debugging or session-storage inspection. '
                    if outcome['task_class'] == 'research' else
                    'Own bounded assignment: finish actual tests/CLI or assigned coverage and native transcript self-check '
                    '(review --native-self; Herder export_transcript → review --manifest also available). '
                    'First write raw expected/observed as a separate commentary message and preserve FEEDBACK; '
                    'level self-check, not independent parent product acceptance. '
                    if bounded_self_check(outcome) or outcome['task_class'] in {'testing', 'research'} else
                    'Optional outcome-ledger review import: review --manifest may record provenance; missing ledger/manifest is not a delivery veto. Preserve actual findings and verify any concrete defect. ')
    if outcome.get('delegation_prohibited'):
        review_route += ('Explicit no-delegation: do not create, launch or resume reviewer/tester sessions. '
                         'If independent acceptance remains required, hand ready results to the assigned coordinator; '
                         'do not hire a reviewer to close state. ')
    review_route += ('Integrate only into an explicitly selected permitted target (contract --integration-branch/remote/ownership); '
                     'Airlock: megamen32-dev; external/shared upstream main is never auto-merged. Completed dev delivery '
                     'does not require Oleg final main merge: release_handoff awaiting-owner is separate. ')
    stage = next_stage(outcome)
    rejection = outcome.get('contract_rejection') or {}
    if (rejection and rejection.get('scope_fingerprint') == contract_scope_fingerprint(outcome)):
        contract_guidance = (' Contract rejection (exact): ' + rejection.get('exact_error', '') +
                             ' Corrective action: ' + rejection.get('corrective_action',
                             'Correct only the rejected field; do not retry unchanged.'))
    elif outcome.get('contract_confirmed'):
        if stage:
            claim = outcome.get('stage_claims', {}).get(stage, {})
            target = claim.get('target', outcome['canary']['target'])
            expected = claim.get('expected', outcome['canary']['expected'])
            contract_guidance = (f' Contract confirmed. Next stage={stage}; perform the assigned {stage} action '
                                 f'for scenario {outcome["canary"]["scenario"]!r} at target {target!r}; '
                                 f'compare with expected {expected!r}. Preserve existing permissions and gates.')
        else:
            contract_guidance = (' Contract confirmed and no technical stage remains; continue the existing pending '
                                 'milestone, acceptance, or recorded blocker. Do not restate the contract.')
    elif outcome.get('contract_request_fingerprint') == contract_scope_fingerprint(outcome):
        contract_guidance = (' The unchanged task contract was already requested; resume from the existing request '
                             'without restating the scenario or owned paths.')
    else:
        contract_guidance = (' confirm the concrete contract once: provide the scenario, target, expected result, and owned paths with '
                             'python3 ' + shlex.quote(str(tool)) + ' --cwd ' + shlex.quote(outcome['cwd']) +
                             ' --runtime ' + outcome['owner']['harness'] + ' --session-id ' +
                             shlex.quote(outcome['owner']['session_id']) + ' contract --help; then perform actual work.')
    return ('LHC outcome: ' + outcome['task_class'] + '; ' + outcome['finish_verdict'] +
            '. Canary: ' + json.dumps(outcome['canary'], ensure_ascii=False) +
            '. Review subject: ' + review_subject(outcome) + ' (subject binding only; not permission).' +
            ' Next stage: ' + str(stage) + '.' + contract_guidance + ' ' + review_route +
            'Refs, echo, pytest and own PASS do not replace the original canary. Testing may complete with product=changes-required; '
            'do not hire nested testers. Never bypass human stop/permission. Human question: question --message; '
            'existing bound request → Notify card → sent receipt → canonical answer; receipt != answer. '
            'Keep unfinished work pending with exact next action/blocker, without infinite retries.')


def question_plan(outcome, message):
    if re.search(r'Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]+', message, re.I):
        raise ValueError('secret values belong in the existing AskSecret flow, never question text')
    identity = digest([outcome['id'], message, outcome['owner']])
    old = outcome.get('question')
    if old and (old.get('phase') != 'answered' or old.get('identity') == identity):
        return {'action': 'inspect-existing-request', 'question': old}
    question = outcome['question'] = {'identity': identity, 'phase': 'prepared', 'message': message}
    configured = os.environ.get('ASK_HUMAN_URL') or os.environ.get('LHC_ASKHUMAN_MCP_URL')
    if configured:
        url = urlsplit(configured)
        if url.scheme in {'http', 'https'} and url.netloc and not (url.username or url.password or url.query or url.fragment):
            question['http_endpoint'] = configured.rstrip('/') if os.environ.get('ASK_HUMAN_URL') else url._replace(path='/v1/human-requests').geturl()
    return {'action': 'bound-question', 'identity': identity,
            'binding': {'tool': 'human_request_create', 'arguments': {'kind': 'user',
                'harness': outcome['owner']['harness'], 'sessionId': outcome['owner']['session_id'],
                'cwd': outcome['cwd'], 'marker': identity, 'message': message}},
            'delivery': {'tool': 'noticeplace_ask_human', 'request_id': '<binding.request_id>',
                         'harness': outcome['owner']['harness'], 'session_id': outcome['owner']['session_id'],
                         'cwd': outcome['cwd'], 'message': message},
            'result': {'tool': 'noticeplace_question_result', 'request_id': '<same request_id>'},
            'policy': 'Persist binding before delivery; inspect accepted/UNKNOWN, never replay. Missing actors/project is a scoped blocker; no invented incident. Delivery != answer != permission.'}


def http_question_operation(name, args, question):
    """Known direct HTTP read/write route, never a schema emitted by echo.

    The endpoint comes from existing configuration before the attempt. Unknown
    clients/wrappers cannot establish delivery; the native MCP path still works.
    """
    endpoint = question.get('http_endpoint')
    if not endpoint or name not in {'exec_command', 'Bash', 'shell_exec'}:
        return None
    text = str(args.get('cmd') or args.get('command') or '')
    if any(char in text for char in ('\n', ';', '|', '`', '$(', '&&', '>', '<')):
        return None
    try:
        words = shlex.split(text)
    except ValueError:
        return None
    if not words or Path(words[0]).name != 'curl' or any(
            word in {'-w', '--write-out', '-K', '--config', '-L', '--location', '--next', '--resolve', '--connect-to', '-k', '--insecure'}
            or word.startswith(('--write-out=', '--config=', '--resolve=', '--connect-to=')) for word in words):
        return None
    if any(word.startswith(('-w', '-K', '-k', '-L')) or (re.fullmatch(r'-[a-zA-Z]+', word) and set(word[1:]) & set('wKkL')) for word in words[1:]):
        return None
    urls = [word for word in words if word.startswith(('http://', 'https://'))]
    if len(urls) != 1:
        return None
    method = next((words[i + 1] for i, word in enumerate(words[:-1]) if word in {'-X', '--request'}), None)
    method = method or next((word[2:] for word in words if word.startswith('-X') and len(word) > 2), None)
    method = method or ('POST' if any(word in {'-d', '--data', '--data-binary', '--data-raw', '--json'} for word in words) else 'GET')
    if urls[0] == endpoint and method.upper() == 'POST':
        return 'delivery'
    if urls[0] == endpoint + '/' + str(question.get('request_id')) + '/result' and method.upper() == 'GET':
        return 'answer'
    return None


def observe_question(outcome, event):
    question = outcome.get('question')
    if not question:
        return
    name = str(event.get('tool_name', '')).split('__')[-1]
    args = event.get('tool_input') or {}
    response = event.get('tool_response') or {}
    if not isinstance(args, dict) or not isinstance(response, dict):
        return
    data = response.get('structuredContent') or response
    if 'content' in data:
        try:
            data = json.loads(native.content(data['content']))
        except (ValueError, TypeError):
            return
    elif isinstance(data.get('stdout') or data.get('output'), str):
        try:
            data = json.loads(data.get('stdout') or data['output'])
        except (ValueError, TypeError):
            return
    if not isinstance(data, dict):
        return
    source = 'native-tool:' + str(event.get('tool_call_id') or event.get('call_id') or name)
    http_operation = http_question_operation(name, args, question)
    if name == 'human_request_create':
        binding = data.get('binding') or {}
        target = binding.get('native_target') or {}
        if (args.get('marker') == question['identity'] and target.get('session_id') == outcome['owner']['session_id']
                and target.get('harness') == outcome['owner']['harness'] and target.get('cwd') == outcome['cwd']
                and binding.get('request_id')):
            if question.get('request_id') not in {None, binding['request_id']}:
                question['binding_conflict'] = True
                return
            question.update(request_id=binding['request_id'], binding_ref=source)
            if question['phase'] == 'prepared':
                question['phase'] = 'bound'
    elif (args.get('request_id') or data.get('request_id')) == question.get('request_id') and question.get('request_id'):
        if name == 'noticeplace_ask_human' or (http_operation == 'delivery' and data.get('schema') == 'ask_human.response.v1'):
            # Only an actual sent receipt; queued/uncertain is still pending.
            # HTTP carries provider receipt; MCP returns the verified card status
            # and exact native target, but strips the provider message ID.
            target = data.get('native') or {
                'harness': data.get('native_harness'), 'session_id': data.get('native_session_id'), 'cwd': data.get('native_cwd')}
            same_target = (target.get('session_id') == outcome['owner']['session_id'] and
                           target.get('harness') == outcome['owner']['harness'] and target.get('cwd') == outcome['cwd'])
            if data.get('request_id') != question['request_id'] or not same_target:
                return
            telegram = data.get('telegram') or {}
            if (data.get('schema') == 'ask_human.response.v1' and telegram.get('status') == 'sent'
                    and isinstance(telegram.get('message_id'), int) and telegram['message_id'] > 0):
                if question['phase'] != 'answered':
                    question.update(phase='delivered', delivery_ref=source)
            elif data.get('card') == 'sent' and same_target:
                if question['phase'] != 'answered':
                    question.update(phase='delivered', delivery_ref=source, provider_message_ref='not-exposed-by-MCP')
        elif name == 'noticeplace_question_result' or (http_operation == 'answer' and data.get('schema') == 'ask_human.result.v1'):
            target = data.get('native') or {}
            if (data.get('schema') == 'ask_human.result.v1' and data.get('request_id') == question['request_id']
                    and data.get('state') == 'resolved' and data.get('kind') == 'user' and data.get('result_ref')
                    and target.get('session_id') == outcome['owner']['session_id']
                    and target.get('harness') == outcome['owner']['harness'] and target.get('cwd') == outcome['cwd']):
                question.update(phase='answered', answer_ref=data['result_ref'], canonical_source=source)
            # Answer availability is not an auth grant and does not accept work.


def main():
    import lhc_time_guard as guard
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', type=Path, default=Path.cwd())
    parser.add_argument('--runtime', choices=('codex', 'opencode', 'zcode', 'claude'), required=True)
    parser.add_argument('--session-id', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    contract = sub.add_parser('contract')
    for field in ('scenario', 'target', 'expected'):
        contract.add_argument('--' + field, required=True)
    contract.add_argument('--task-class', choices=('quickfix', 'fullcycle', 'testing', 'research', 'status'))
    contract.add_argument('--scope-source', help='exact native user source reference for a semantic class correction')
    contract.add_argument('--verification-kind', choices=VERIFICATION_KINDS, default='standard',
                          help='source-publication binds native source readiness and exact Git publication evidence')
    contract.add_argument('--product-root', type=Path, help='explicit product checkout; --cwd remains the native session-state root')
    contract.add_argument('--require-stage', action='append', choices=STAGES, default=[])
    contract.add_argument('--not-applicable', action='append', choices=STAGES, default=[])
    contract.add_argument('--owned-path', action='append', default=[])
    contract.add_argument('--coverage', action='append', default=[])
    contract.add_argument('--integration-branch')
    contract.add_argument('--integration-remote')
    contract.add_argument('--integration-ownership', choices=('owned', 'shared', 'external'))
    contract.add_argument('--integration-permission-quote', help='unchanged affirmative native user scope for this repository merge; not write access/ownership')
    contract.add_argument('--release-owner', help='human owner of later upstream integration, not this dev delivery')
    contract.add_argument('--stage-target', action='append', default=[], metavar='STAGE=TARGET')
    contract.add_argument('--stage-expected', action='append', default=[], metavar='STAGE=EXPECTED')
    review = sub.add_parser('review')
    route = review.add_mutually_exclusive_group(required=True)
    route.add_argument('--manifest', type=Path)
    route.add_argument('--native-self', action='store_true', help='read this own native Codex/OpenCode source without depending on Herder export CWD')
    route.add_argument('--native-reviewer', metavar='CODEX_SESSION_ID', help='read an existing independent bounded Codex engineering/research reviewer via its native assignment window; never create/resume it')
    review.add_argument('--testing-reuse-bindings', type=Path, help='explicit original native contract/user/report/per-coverage source bindings for own historical testing; never a PASS receipt')
    review.add_argument('--comparison-quote', help='bind an unchanged own research source-finding passage to the confirmed expectation; source filename/readback required, self-check only')
    question = sub.add_parser('question')
    question.add_argument('--message', required=True)
    sub.add_parser('status')
    args = parser.parse_args()
    cwd = args.cwd.resolve()
    path = guard.learning_path(cwd, args.runtime, args.session_id)
    if not path.is_file():
        raise ValueError(f'no LHC session state for {args.runtime}/{args.session_id} from session root {cwd}; no state was created')
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        outcome = (state.get('business') or {}).get('outcome')
        if not isinstance(outcome, dict):
            raise ValueError(f'no LHC outcome for native session {args.session_id} at {path}; session root is {cwd}')
        expected_session_root = Path(outcome.get('cwd', '/unknown')).resolve()
        if expected_session_root != cwd:
            raise ValueError(f'LHC state for native session {args.session_id} is bound to session root {expected_session_root}; --cwd {cwd} is not that root')
        if args.command == 'contract':
            if (args.task_class or outcome.get('task_class')) == 'testing' and not args.coverage:
                raise ValueError('testing contract requires at least one explicit --coverage claim before confirming the consumer task; add the assigned scenario coverage now (no contract or evidence floor was changed)')
            previous_stage_fingerprints = outcome.get('stage_fingerprints')
            outcome.pop('contract_rejection', None)
            scope_source_id = args.scope_source or outcome.get('product_root_source')
            source = next((r for r in outcome.get('scope_sources', []) if r.get('source') == scope_source_id), None)
            source_scope = (source.get('scope_prompt') or semantic_scope(source.get('prompt', ''))) if source else ''
            semantic_source = {**source, 'prompt': source_scope} if source else None
            prior_product_root = product_root_path(outcome, cwd)
            product_root = (args.product_root or prior_product_root).resolve()
            if product_root != cwd and not product_root_scope_allowed(outcome, source, product_root, args.owned_path):
                raise ValueError('external product root needs the exact native assignment and its original successful brief read, with every owned path inside that root')
            candidate_outcome = {**outcome, 'product_root': str(product_root), 'owned_paths': args.owned_path}
            product_paths(candidate_outcome, cwd)
            policy = outcome.get('integration_policy')
            if any((args.integration_branch, args.integration_remote, args.integration_ownership, args.release_owner, args.integration_permission_quote)):
                if not source or not all((args.integration_branch, args.integration_remote, args.integration_ownership)):
                    raise ValueError('integration needs explicit branch/remote/ownership and native scope source; unknown is not main')
                if not re.fullmatch(r'[\w][\w./-]*', args.integration_branch) or '..' in args.integration_branch:
                    raise ValueError('invalid integration branch')
                if args.integration_branch in {'main', 'master'} and args.integration_ownership != 'owned':
                    raise ValueError('external/shared upstream main is owner-only, never automated integration')
                if args.release_owner and args.integration_branch in {'main', 'master'}:
                    raise ValueError('release handoff needs a separate permitted dev target')
                policy = {'branch': args.integration_branch, 'remote': args.integration_remote,
                          'ownership': args.integration_ownership, 'source': scope_source_id,
                          'project_source': scope_source_id,
                          'release_owner': args.release_owner,
                          'repository': remote_binding(product_root, args.integration_remote),
                          'permission_quote': args.integration_permission_quote}
                permission = resolve_main_permission_source(
                    outcome, args.integration_permission_quote, policy['repository'], policy['branch'], state)
                if permission and permission['kind'] == 'project-universal':
                    # A universal quote is usable only for the exact current project
                    # scope and explicitly owned files, never as a workspace allowlist.
                    if (args.integration_ownership != 'owned' or
                            not product_root_scope_allowed(outcome, source, product_root, args.owned_path)):
                        permission = None
                policy['main_permission_confirmed'] = bool(permission and args.integration_ownership == 'owned')
                policy['permission_source'] = permission['source'] if permission else None
                policy['permission_source_sha256'] = permission['sha256'] if permission else None
                policy['permission_source_index'] = permission['index'] if permission else None
                policy['permission_source_at'] = permission['at'] if permission else None
                policy['permission_kind'] = permission['kind'] if permission else None
                policy['target_scope_confirmed'] = args.integration_branch in source_scope or policy['main_permission_confirmed']
            if args.task_class and args.task_class != outcome['task_class']:
                if not source:
                    raise ValueError('class correction requires an exact original/latest native user source')
                if outcome.get('class_confirmed') and outcome['task_class'] in ENGINEERING and args.task_class not in ENGINEERING:
                    raise ValueError('status/read-only cannot cancel confirmed repair; an explicit new assignment needs its own lineage')
                outcome.setdefault('class_history', []).append({'class': outcome['task_class'], 'source': scope_source_id})
                outcome['task_class'] = args.task_class
                outcome['stages'] = applicable(args.task_class, source_scope)
            for stage in args.not_applicable:
                if not source or stage not in EXCLUSIONS or not re.search(EXCLUSIONS[stage], source_scope, re.I):
                    raise ValueError('N/A needs explicit original/latest scope, not missing access')
                outcome['stages'][stage] = {'status': 'not-applicable', 'basis': scope_source_id, 'evidence': []}
            for stage in args.require_stage:
                current_stage = outcome.get('stages', {}).get(stage, {})
                if current_stage.get('status') != 'complete':
                    outcome['stages'][stage] = {'status': 'pending', 'basis': 'confirmed-applicability', 'evidence': []}
            outcome['class_confirmed'] = True
            if outcome['task_class'] in ENGINEERING and not args.owned_path:
                raise ValueError('engineering contract requires explicit owned paths')
            if any(not str(getattr(args, field)).strip() for field in ('scenario', 'target', 'expected')):
                raise ValueError('canary must be concrete')
            canary = {'scenario': args.scenario, 'target': args.target, 'expected': args.expected, 'status': 'pending'}
            claims = {} if args.stage_target or args.stage_expected else outcome.get('stage_claims', {}).copy()
            for field, entries in [('target', args.stage_target), ('expected', args.stage_expected)]:
                for entry in entries:
                    stage, value = entry.split('=', 1)
                    if stage not in {'deploy', 'publication', 'integration'} or not value.strip():
                        raise ValueError('stage target/expected must bind deploy/publication/integration')
                    claims.setdefault(stage, {})[field] = value
            if any(set(row) != {'target', 'expected'} for row in claims.values()):
                raise ValueError('stage readback needs both target and expected')
            prior_verification_kind = outcome.get('verification_kind', 'standard')
            prior_source_publication = outcome.get('source_publication')
            source_publication = None
            if args.verification_kind == 'source-publication':
                from lhc_source_publication import capture_contract
                if not args.scope_source or not source:
                    raise ValueError('source-publication needs an exact current native --scope-source')
                if outcome['task_class'] not in ENGINEERING or not args.owned_path:
                    raise ValueError('source-publication is bounded engineering work with explicit owned paths')
                if canary['target'] != 'project:' + str(product_root):
                    raise ValueError('source-publication requires the explicit plain project:<root> target')
                policy = policy or outcome.get('integration_policy')
                if not policy or not all((policy.get('remote'), policy.get('branch'), policy.get('ownership'))):
                    raise ValueError('source-publication needs explicit current remote, branch, and ownership')
                if policy.get('repository') != remote_binding(product_root, policy['remote']):
                    raise ValueError('source-publication repository binding is missing or changed')
                pub_claim = claims.get('publication', {})
                source_publication = capture_contract(
                    outcome, source, product_root, args.owned_path, policy['remote'], policy['branch'],
                    policy['repository'], canary['target'], pub_claim.get('target'),
                    pub_claim.get('expected'), product_root_scope_allowed,
                )
                if policy['ownership'] != 'owned' and policy['branch'] in {'main', 'master'}:
                    raise ValueError('source-publication to shared/external main remains owner-only')
                source_applicable = applicable(outcome['task_class'], source_scope)
                if source_applicable['deploy']['status'] == 'pending':
                    raise ValueError('source-publication cannot omit deployment still required by the current native scope')
                for stage in ('deploy', 'integration'):
                    row = source_applicable[stage]
                    if row['status'] == 'not-applicable':
                        outcome['stages'][stage] = row
                candidate_expected = 'candidate:' + source_publication['candidate_fingerprint']
                claims.setdefault('publication', {})['expected'] = candidate_expected
                if outcome['stages']['integration']['status'] == 'pending':
                    if (policy['ownership'] != 'owned' or
                            (policy['branch'] in {'main', 'master'} and not policy.get('main_permission_confirmed'))):
                        raise ValueError('source integration retains the existing main permission and ownership gates')
                    integration_claim = claims.get('integration')
                    if integration_claim and integration_claim.get('target') != pub_claim.get('target'):
                        raise ValueError('source-publication integration must bind the exact same verified ref')
                    claims['integration'] = {'target': pub_claim['target'], 'expected': candidate_expected}
                # Only the explicitly source-only native scope may omit an app consumer.
                outcome['stages']['consumer'] = {
                    'status': 'not-applicable',
                    'basis': 'source-publication:' + scope_source_id,
                    'evidence': [],
                }
                outcome['source_publication'] = source_publication
            else:
                outcome.pop('source_publication', None)
            outcome['verification_kind'] = args.verification_kind
            from lhc_outcome_review import equivalent_target
            previous = outcome['canary']
            same_canary = (all(canary[k] == previous[k] for k in ('scenario', 'expected')) and
                           equivalent_target(previous['target'], canary['target'], product_root,
                                             '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])))
            changed = (not same_canary or args.owned_path != outcome['owned_paths'] or
                       args.coverage != outcome.get('coverage', []) or claims != outcome.get('stage_claims', {}) or
                       policy != outcome.get('integration_policy') or product_root != prior_product_root or
                       prior_verification_kind != args.verification_kind or
                       (source_publication and source_publication != prior_source_publication))
            canary['status'] = previous['status']
            outcome.update(canary=canary, owned_paths=args.owned_path, coverage=args.coverage, contract_confirmed=True, stage_claims=claims)
            if product_root != cwd:
                outcome['product_root'] = str(product_root)
                outcome['product_root_source'] = scope_source_id
            else:
                outcome.pop('product_root', None)
                outcome.pop('product_root_source', None)
            if policy:
                outcome['integration_policy'] = policy
                if policy['branch'] not in {'main', 'master'}:
                    outcome['release_handoff'] = {'status': 'pending-dev-delivery', 'owner': policy.get('release_owner') or 'upstream owner', 'target': 'upstream main'}
            outcome['revision'] = scope_revision(outcome, cwd)
            invalidated = invalidate_changed_stage_evidence(outcome, previous_stage_fingerprints)
            if invalidated:
                outcome['evidence_after'] = datetime.now().astimezone().isoformat()
            if 'consumer' in invalidated:
                outcome['canary']['status'] = 'pending'
        elif args.command == 'review':
            from lhc_outcome_review import accept_review, native_self_manifest, native_reviewer_manifest
            if not _permission_binding_valid(outcome, state):
                raise ValueError('main integration permission source is missing, changed, revoked, or not bound to the current owned project')
            manifest = (native_self_manifest(outcome, cwd, args.runtime, args.session_id, state=state) if args.native_self else
                        native_reviewer_manifest(outcome, cwd, args.native_reviewer, state=state) if args.native_reviewer else args.manifest)
            accept_review(outcome, state, manifest, cwd, args.session_id, args.comparison_quote,
                          json.loads(native.read(args.testing_reuse_bindings)) if args.testing_reuse_bindings else None)
        elif args.command == 'question':
            result = question_plan(outcome, args.message)
        if args.command == 'status':
            outcome['review_subject'] = review_subject(outcome)
        outcome['finish_verdict'] = verdict(outcome, state)
        guard.write_state(path, state)
        print(json.dumps(result if args.command == 'question' else outcome, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('LHC outcome: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
