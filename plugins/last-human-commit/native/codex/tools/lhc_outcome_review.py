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

import lhc_milestone as native
from lhc_outcome import ENGINEERING, STAGES, scope_revision

MARKER = 'LHC_OUTCOME_REVIEW '


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
        finals = [row.get('timestamp') for row in rows if row.get('type') == 'response_item'
                  and row.get('payload', {}).get('role') == 'assistant' and row['payload'].get('phase') != 'commentary']
        result[0]['reviewed_at'] = next((stamp for stamp in reversed(finals) if stamp), result[0].get('timestamp'))
    elif target.get('harness') == 'opencode':
        result = native.opencode_transcript(target, raw)
        finals = [(message.get('info') or message).get('time', {}).get('completed') for message in json.loads(raw)
                  if (message.get('info') or message).get('role') == 'assistant']
        stamp = next((value for value in reversed(finals) if value), None)
        if stamp:
            from datetime import datetime, timezone
            result[0]['reviewed_at'] = datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
    else:
        raise ValueError('native review format unsupported; use existing independent Codex/OpenCode reviewer')
    if (result[0].get('id') or result[0].get('session_id')) != target.get('sessionId'):
        raise ValueError('native reviewer identity mismatch')
    return result


def command(call):
    args = call.get('arguments') or call.get('input') or '{}'
    try:
        args = json.loads(args) if isinstance(args, str) else args
    except ValueError:
        return '', []
    text = str(args.get('cmd') or args.get('command') or args.get('url') or '')
    try:
        words = shlex.split(text)
        if words and Path(words[0]).name in {'bash', 'sh', 'zsh'}:
            index = next((i for i, w in enumerate(words) if w in {'-c', '-lc'}), None)
            return command(dict(arguments=json.dumps({'cmd': words[index + 1]}))) if index is not None else ('', [])
    except (ValueError, IndexError):
        return '', []
    # Quoted commands, echo+receipt and compound shell output are not real
    # consumer observations. Unknown tool formats need review of a supported
    # native source, never an invented receipt.
    if words and Path(words[0]).name in {'echo', 'printf', 'cat', 'pwd', 'ls', 'rg', 'grep', 'true'}:
        return '', []
    if any(w in {';', '&&', '||', '|'} for w in words):
        return '', []
    return text, words


def real_observation(call, output, target, stage, task_class=None, cwd=None, expected=None):
    args = call.get('arguments') or call.get('input') or '{}'
    try:
        args = json.loads(args) if isinstance(args, str) else args
        directory = Path(args.get('workdir') or args.get('cwd') or cwd)
        directory = (cwd / directory).resolve() if not directory.is_absolute() else directory.resolve()
        directory.relative_to(cwd)
        # Relative CLI targets are bound to the canary project root. A second
        # checkout with the same filename is not the assigned product.
        if stage == 'consumer' and not target.startswith(('http://', 'https://')) and directory != cwd:
            return False
    except (ValueError, TypeError, AttributeError):
        return False
    text, words = command(call)
    name = str(call.get('name', '')).casefold()
    if not output.strip():
        return False
    if stage == 'technical':
        return bool(words and (Path(words[0]).name == 'pytest' or words[:2] in [['go', 'test'], ['cargo', 'test'], ['bun', 'test'], ['npm', 'test']] or (Path(words[0]).name in {'python', 'python3'} and words[1:3] in [['-m', 'pytest'], ['-m', 'unittest']])))
    if stage == 'consumer':
        if task_class == 'research':
            try:
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
        expected = shlex.split(target)
        return bool(expected and words[:len(expected)] == expected and not re.search(r'pytest|\btest\b', text))
    # Readbacks are stage-specific and contract-bound, never arbitrary Git
    # metadata or a reviewer mutation. Unknown formats need the existing review
    # path plus a supported readback, not a guessed deployment certificate.
    if not expected or not text or not words:
        return False
    if stage == 'publication' and words[:2] == ['git', 'ls-remote']:
        return words[:len(shlex.split(target))] == shlex.split(target) and any(
            line.split()[:1] == [expected] and len(line.split()) > 1 and line.split()[1].startswith('refs/heads/')
            for line in output.splitlines()) and bool(re.fullmatch('[0-9a-f]{40,64}', expected))
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
    browser = [(call, output) for ref in refs for call, output in [by_call[ref]]
               if 'browser' in str(call.get('name', '')).casefold() or 'agent-browser' in command(call)[0]]
    if not browser:
        return True  # CLI/API has its own exact target floor.
    names = [str(call.get('name', '')).casefold() + ' ' + command(call)[0] for call, _ in browser]
    actions = [i for i, name in enumerate(names) if re.search(r'click|fill|type|press|select|submit', name)]
    return bool(actions and any(i > actions[0] and re.search(r'snapshot|screenshot|evaluate|extract|get.text', name)
                                and browser[i][1].strip() for i, name in enumerate(names)))


def raw_review(outcome, final, observations, cwd):
    """Small ordinary-report route; keep original prose as semantic assessment.

    No author PASS/map file and no rewriting the review. Complex unsupported
    prose stays explicit; the same existing reviewer may use the optional JSON
    line, rather than recursively hiring somebody to manufacture a certificate.
    """
    canary = outcome['canary']
    defect = bool(re.search(r'changes.required|\bfailed\b|\bfailure\b|defect found|ошибк|не соответствует', final, re.I))
    positive = bool(re.search(r'\bPASS\b|no defects|match(?:ed|es)|соответствует|работает', final, re.I))
    if not final.strip() or not (positive or defect or outcome['task_class'] == 'research'):
        raise ValueError('raw review must state its actual result; retain the original report')
    stages = {}
    by_call = {call.get('call_id'): (call, output) for call, output in observations if call.get('call_id')}
    for stage in STAGES:
        if outcome['stages'][stage]['status'] != 'pending':
            continue
        claim = outcome.get('stage_claims', {}).get(stage, canary)
        target, expected = claim['target'], claim['expected']
        refs = [ref for ref, (call, output) in by_call.items()
                if real_observation(call, output, target, stage, outcome['task_class'], cwd, expected)]
        if stage == 'technical' and not re.search(r'test|regression|тест|провер', final, re.I):
            refs = []
        if stage in {'deploy', 'publication', 'integration'} and (expected.casefold() not in final.casefold() or target.casefold() not in final.casefold()):
            refs = []
        if stage == 'consumer':
            # Ordinary prose must actually cover this expected consumer result,
            # not a generic all-PASS sentence over unrelated calls.
            short_target = Path(shlex.split(target)[-1]).name
            if expected.casefold() not in final.casefold() or not any(t.casefold() in final.casefold() for t in (target, short_target)):
                refs = []
            if refs:
                refs += [ref for ref, (call, _) in by_call.items() if 'browser' in str(call.get('name', '')).casefold()]
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


def accept_review(outcome, state, path, cwd, owner):
    meta, messages, observations = load_review(path)
    sid = meta.get('id') or meta.get('session_id')
    own_attempt = sid == owner and outcome['task_class'] in {'testing', 'research'}
    if (sid == owner and not own_attempt) or Path(meta.get('cwd', '/unknown')).resolve() != cwd:
        raise ValueError('review must be independent and for this exact project')
    if native.timestamp(meta.get('reviewed_at') or meta['timestamp']) < native.timestamp(outcome['started_at']):
        raise ValueError('stale reviewer')
    if not outcome.get('contract_confirmed'):
        raise ValueError('confirm the concrete contract first')
    prompt = '\n'.join(text for role, text, _ in messages if role == 'user')
    final = next((text for role, text, phase in reversed(messages) if role == 'assistant' and (phase != 'commentary' or own_attempt)), '')
    if (outcome['id'] not in prompt and not own_attempt) or outcome['original_goal'] not in prompt:
        raise ValueError('review assignment must identify the outcome')
    if any(correction not in prompt for correction in outcome.get('corrections', [])):
        raise ValueError('review omits the latest accepted scope corrections')
    lines = [line[len(MARKER):] for line in final.splitlines() if line.startswith(MARKER)]
    if len(lines) > 1:
        raise ValueError('ambiguous independent review summaries')
    report = json.loads(lines[0]) if lines else raw_review(outcome, final, observations, cwd)
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
    for item in coverage:
        claim = report.get('coverage', {}).get(item)
        if (not isinstance(claim, dict) or claim.get('verdict') not in {'passed', 'defect'}
                or not claim.get('expected') or not claim.get('observed')):
            raise ValueError('each assigned coverage claim needs expected/observed comparison')
        refs = claim.get('evidence_calls') or []
        if not refs or not all(ref in by_call for ref in refs) or not any(
                real_observation(*by_call[ref], canary['target'], 'consumer', outcome['task_class'], cwd) for ref in refs):
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
        if not any(real_observation(*by_call[ref], claim['target'], stage, outcome['task_class'], cwd, claim['expected']) for ref in refs):
            raise ValueError('echo/health/test-only/wrong-target receipt is not the assigned consumer operation')
        completed.add(stage)
    for stage, row in updates.items():
        outcome['stages'][stage].update(status='complete', evidence=[{
            'manifest': str(path.resolve()), 'reviewer': sid, 'revision': revision,
            'calls': row['evidence_calls'], 'expected': row['expected'], 'observed': row['observed'],
        }])
    if staging:
        outcome['staging_push'] = {**staging, 'manifest': str(path.resolve()), 'reviewer': sid}
    outcome.update(product_verdict=product, revision=revision, coverage_evidence=report.get('coverage', {}))
    outcome['canary']['status'] = 'complete' if 'consumer' in completed else 'pending'
    outcome['sources'] = list(dict.fromkeys([*outcome.get('sources', []), str(path.resolve())]))
