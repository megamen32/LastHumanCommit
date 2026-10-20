#!/usr/bin/env python3
"""Task outcome in the existing session state. No network, permissions or scheduler.

Classification is a conservative hint. A native independent review supplies the
semantic comparison; this helper never interprets a tool receipt as business PASS.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
import shlex
import os
from urllib.parse import urlsplit

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import lhc_milestone as native

STAGES = ('technical', 'deploy', 'consumer', 'publication', 'integration')
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
    # OpenCode may quote the prompt; Herder coordination markup is metadata.
    # Raw input remains preserved in the native state as source evidence.
    scope = HERDER_ENVELOPE.sub('', goal).strip()
    if scope.startswith('"') and scope.endswith('"'):
        scope = scope[1:-1]
    return scope.strip()


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
        broad = re.search(r'\b(?:full|entire|complete|all)\b|весь|целиком|полностью', intent, re.I)
        small = re.search(r'\b(?:fix|repair|small|minor|typo)\b|исправ|почин|мелк|опечат', intent, re.I)
        return 'quickfix' if small and not broad else 'fullcycle'
    if TEST.search(intent):
        return 'testing'
    if RESEARCH.search(intent):
        return 'research'
    return 'unknown'


NEGATIVE_LIST = r'(?:no|without|do not|без)\s+(?:(?:deploy|push|publish|merge)\s*(?:[,/]\s*(?:(?:and|or|и|или)\s+)?|(?:and|or|и|или)\s+))*'
EXCLUSIONS = {
    'deploy': NEGATIVE_LIST + r'deploy\b|(?:no|without|do not)\s+(?:\w+\s+)?deploy|без\s*(?:push/)?deploy|не\s+(?:деплой|выкладывай)',
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


def product_paths(outcome, cwd):
    paths = outcome.get('owned_paths', [])
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
        paths = [p for p in paths if (cwd / p).resolve() != (cwd / 'FEEDBACK.md').resolve()]
    return paths


def scope_revision(outcome, cwd):
    # Explicit owned product only; clocks/receipts cannot manufacture progress.
    paths = product_paths(outcome, cwd)
    return digest([(p, native.file_hash(cwd, p)) for p in paths])


def remote_binding(cwd, remote):
    value = native.git(cwd, 'remote', 'get-url', remote).decode().strip()
    # Keep credentials out of state/logs. Only resolved GitHub repository IDs
    # are supported for automatic upstream-main close, not arbitrary remotes.
    match = re.fullmatch(r'(?:https://github.com/|git@github.com:)([\w.-]+/[\w.-]+?)(?:\.git)?', value)
    return match.group(1) if match else None


def main_permission(source, quote, repository, branch):
    if not source or not quote or quote not in source['prompt'] or not repository:
        return False
    owner, repo = repository.split('/')
    acronym = ''.join(c for c in repo if c.isupper())
    # A caller cannot strip "Do not" from a native sentence and submit its
    # affirmative tail as consent. Ambiguous clauses stay owner-handoff.
    clauses = re.split(r'[.!?;\n]', source['prompt'])
    clause = next((text for text in clauses if quote.rstrip('.!?;') in text), '')
    return bool(re.search(r'(?<![\w.-])' + re.escape(owner) + r'(?![\w.])', quote, re.I)
                and (re.search(r'(?<![\w.-])' + re.escape(repo) + r'(?![\w.-])', quote, re.I)
                     or (len(acronym) > 1 and re.search(r'(?<![A-Z0-9])' + re.escape(acronym) + r'(?![A-Z0-9])', quote)))
                and re.search(r'allow|permit|разреш|можно', quote, re.I)
                and re.search(r'merge|интегр|слия|сливай', quote, re.I)
                and re.search(r'(?:\binto\s+|\bto\s+|\bв\s+|\bна\s+)(?:branch\s+)?[`\'"]?' + re.escape(branch) + r'(?![\w/-]|\.[\w/-])', quote, re.I)
                and clause and not re.search(r"do not|don't|never|forbidden|not allowed|not permitted|\bno\b|\bне\b|нельзя|запрещ", clause, re.I))


def verdict(outcome, state):
    if outcome['task_class'] == 'status':
        return 'complete'
    # Interrupt preserves the stop hold; it does not identify who stopped it.
    if state.get('native_entry', {}).get('finish_hold') not in {None, 'SessionEnd'}:
        return 'blocked'
    if outcome.get('question', {}).get('phase') not in {None, 'answered'}:
        return 'blocked'
    if state.get('business', {}).get('running_jobs'):
        return 'running'
    if outcome.get('blockers'):
        return 'blocked'
    if not outcome.get('contract_confirmed'):
        return 'pending'
    if any(s['status'] not in {'complete', 'not-applicable'} for s in outcome['stages'].values()):
        return 'pending'
    if outcome['stages']['integration']['status'] == 'complete' and not outcome.get('integration_policy'):
        return 'pending'  # Unknown target/ownership never defaults to main.
    policy = outcome.get('integration_policy')
    if policy and outcome['stages']['integration']['status'] != 'not-applicable':
        if not policy.get('target_scope_confirmed') or not policy.get('repository') or remote_binding(Path(outcome['cwd']), policy['remote']) != policy['repository']:
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
    prompt = semantic_scope(str(event.get('prompt') or '')) if name == 'UserPromptSubmit' and not event.get('_lhc_control_prompt') else ''
    human = bool(prompt and not prompt.startswith('🤖'))
    if not outcome and goal:
        kind = classify(goal)
        target = next(iter(native.URL.findall(goal)), 'project:' + str(cwd))
        expected = re.split(r'\b(?:verify|expected|check that)\b|проверь|ожидаем', semantic_scope(goal), maxsplit=1, flags=re.I)[-1].strip()
        outcome = business['outcome'] = {
            'id': digest([session, raw_goal]), 'owner': {'harness': business.get('runtime'), 'session_id': session},
            'original_goal': raw_goal, 'latest_correction': goal, 'task_class': kind,
            'started_at': now.isoformat(), 'cwd': str(cwd), 'native_source': business.get('transcript_path'), 'contract_confirmed': kind == 'status',
            'evidence_after': now.isoformat(),
            'delegation_prohibited': bool(NO_DELEGATION.search(goal)),
            'canary': {'scenario': goal[:512], 'target': target, 'expected': expected[:512], 'status': 'pending'},
            'owned_paths': [], 'stages': applicable(kind, goal), 'used_continuations': [],
            'class_confirmed': False, 'scope_sources': list(business.get('execution_context', {}).get('direct_user_messages', [])),
            'actionable': kind in ENGINEERING | {'testing', 'research'} or bool(ACTIONABLE_UNKNOWN.search(goal)),
            'sources': [], 'product_verdict': 'not-tested', 'blockers': [],
        }
    if not outcome:
        return None
    if human and prompt != semantic_scope(outcome['original_goal']):
        if NO_DELEGATION.search(prompt):
            outcome['delegation_prohibited'] = True
        # Read-only/status/peer updates cannot erase a previously accepted repair.
        kind = classify(prompt)
        actionable_correction = (kind in ENGINEERING | {'testing', 'research'}
                                 or bool(ACTIONABLE_UNKNOWN.search(prompt))
                                 or bool(EXPECTATION_CHANGE.search(expectation_text(prompt))))
        if actionable_correction:
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
                    if outcome['stages'][stage]['status'] != row['status']:
                        outcome['stages'][stage] = row
            urls = native.URL.findall(prompt)
            if urls:
                outcome['canary']['target'] = urls[0]
                outcome['stage_claims'] = {}
        # A direct revocation can be just "Do not deploy anything", without
        # another repair verb. Apply only that exclusion, preserving the repair.
        for stage, pattern in EXCLUSIONS.items():
            if match := re.search(pattern, prompt, re.I):
                outcome['stages'][stage] = {'status': 'not-applicable', 'basis': 'latest-scope:' + match.group(), 'evidence': []}
        if actionable_correction:
            for source in business.get('execution_context', {}).get('direct_user_messages', []):
                if source.get('source') not in {r.get('source') for r in outcome.get('scope_sources', [])}:
                    outcome.setdefault('scope_sources', []).append(source)
        if actionable_correction and prompt not in outcome.get('corrections', []):
            outcome.setdefault('corrections', []).append(prompt)
            outcome['contract_confirmed'] = False
            outcome['canary']['status'] = 'pending'
            outcome['evidence_after'] = now.isoformat()
            for row in outcome['stages'].values():
                if row['status'] == 'complete':
                    row['status'] = 'pending'
    revision = scope_revision(outcome, cwd)
    if outcome.get('revision') and revision != outcome['revision']:
        outcome['evidence_after'] = now.isoformat()
        outcome['canary']['status'] = 'pending'
        # Evidence from an old owned revision cannot accept the new code.
        for row in outcome['stages'].values():
            if row['status'] == 'complete':
                row['status'] = 'pending'
    outcome['revision'] = revision
    if name == 'PostToolUse':
        observe_job_progress(outcome, business, event, cwd)
        observe_question(outcome, event)
    if name in {'PostToolUse', 'PostToolUseFailure'}:
        observe_contract_rejection(outcome, event, name)
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


def observe_contract_rejection(outcome, event, event_name):
    args = event.get('tool_input') or event.get('arguments') or {}
    command = args.get('cmd') or args.get('command') or '' if isinstance(args, dict) else ''
    try:
        words = shlex.split(str(command))
    except ValueError:
        return
    tool_index = next((i for i, word in enumerate(words)
                       if Path(word).name == 'lhc_outcome.py'), None)
    if tool_index is None:
        return
    subcommand = next((word for word in words[tool_index + 1:] if word in {'contract', 'review'}), None)
    if subcommand is None:
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
    same_cwd = not isinstance(args, dict) or not args.get('workdir') or Path(args['workdir']).resolve() == cwd
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
                    'Engineering milestones require existing independent source-backed review via review --manifest. ')
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
            '. Next stage: ' + str(stage) + '.' + contract_guidance + ' ' + review_route +
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
    route.add_argument('--native-reviewer', metavar='CODEX_SESSION_ID', help='read an existing independent Codex research reviewer via a byte-verified native assignment window; never create/resume it')
    review.add_argument('--comparison-quote', help='bind an unchanged own research source-finding passage to the confirmed expectation; source filename/readback required, self-check only')
    question = sub.add_parser('question')
    question.add_argument('--message', required=True)
    sub.add_parser('status')
    args = parser.parse_args()
    cwd = args.cwd.resolve()
    path = guard.learning_path(cwd, args.runtime, args.session_id)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        outcome = state['business']['outcome']
        if args.command == 'contract':
            outcome.pop('contract_rejection', None)
            source = next((r for r in outcome.get('scope_sources', []) if r.get('source') == args.scope_source), None)
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
                          'ownership': args.integration_ownership, 'source': args.scope_source,
                          'release_owner': args.release_owner,
                          'repository': remote_binding(cwd, args.integration_remote),
                          'permission_quote': args.integration_permission_quote}
                policy['main_permission_confirmed'] = main_permission(source, args.integration_permission_quote, policy['repository'], policy['branch'])
                policy['target_scope_confirmed'] = args.integration_branch in source['prompt'] or policy['main_permission_confirmed']
            if args.task_class and args.task_class != outcome['task_class']:
                if not source:
                    raise ValueError('class correction requires an exact original/latest native user source')
                if outcome.get('class_confirmed') and outcome['task_class'] in ENGINEERING and args.task_class not in ENGINEERING:
                    raise ValueError('status/read-only cannot cancel confirmed repair; an explicit new assignment needs its own lineage')
                outcome.setdefault('class_history', []).append({'class': outcome['task_class'], 'source': args.scope_source})
                outcome['task_class'] = args.task_class
                outcome['stages'] = applicable(args.task_class, source['prompt'])
            for stage in args.not_applicable:
                if not source or stage not in EXCLUSIONS or not re.search(EXCLUSIONS[stage], source['prompt'], re.I):
                    raise ValueError('N/A needs explicit original/latest scope, not missing access')
                outcome['stages'][stage] = {'status': 'not-applicable', 'basis': args.scope_source, 'evidence': []}
            for stage in args.require_stage:
                outcome['stages'][stage] = {'status': 'pending', 'basis': 'confirmed-applicability', 'evidence': []}
            outcome['class_confirmed'] = True
            for item in args.owned_path:
                (cwd / item).resolve().relative_to(cwd)
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
            from lhc_outcome_review import equivalent_target
            previous = outcome['canary']
            same_canary = (all(canary[k] == previous[k] for k in ('scenario', 'expected')) and
                           equivalent_target(previous['target'], canary['target'], cwd,
                                             '\n'.join([outcome['original_goal'], *outcome.get('corrections', [])])))
            changed = not same_canary or args.owned_path != outcome['owned_paths'] or args.coverage != outcome.get('coverage', []) or claims != outcome.get('stage_claims', {}) or policy != outcome.get('integration_policy')
            if not changed:
                canary['status'] = previous['status']
            outcome.update(canary=canary, owned_paths=args.owned_path, coverage=args.coverage, contract_confirmed=True, stage_claims=claims)
            if policy:
                outcome['integration_policy'] = policy
                if policy['branch'] not in {'main', 'master'}:
                    outcome['release_handoff'] = {'status': 'pending-dev-delivery', 'owner': policy.get('release_owner') or 'upstream owner', 'target': 'upstream main'}
            if changed:
                outcome['evidence_after'] = datetime.now().astimezone().isoformat()
                for stage in outcome['stages'].values():
                    if stage['status'] == 'complete':
                        stage['status'] = 'pending'
            outcome['revision'] = scope_revision(outcome, cwd)
        elif args.command == 'review':
            from lhc_outcome_review import accept_review, native_self_manifest, native_reviewer_manifest
            manifest = (native_self_manifest(outcome, cwd, args.runtime, args.session_id) if args.native_self else
                        native_reviewer_manifest(outcome, cwd, args.native_reviewer) if args.native_reviewer else args.manifest)
            accept_review(outcome, state, manifest, cwd, args.session_id, args.comparison_quote)
        elif args.command == 'question':
            result = question_plan(outcome, args.message)
        outcome['finish_verdict'] = verdict(outcome, state)
        guard.write_state(path, state)
        print(json.dumps(result if args.command == 'question' else outcome, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('LHC outcome: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
