"""Explicit historical testing bindings; no shell execution or PASS certificates.

Bindings contain original native IDs and unchanged quotations, not replacement
observations. Only the existing own testing assignment can consume them.
"""
import ast
import json
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit


def url_matches(value, target):
    try:
        actual, wanted = urlsplit(value), urlsplit(target)
        if any(p.username or p.password for p in (actual, wanted)):
            return False
        origin = lambda p: (p.scheme, p.hostname, p.port or (443 if p.scheme == 'https' else 80))
        return (actual.scheme in {'https', 'http'} and origin(actual) == origin(wanted)
                and (wanted.path in {'', '/'} and not wanted.query and not wanted.fragment or value == target))
    except ValueError:
        return False


def literal_wrapper(body):
    """Recognize just the recorded argv-forwarding wrapper, never interpret code."""
    try:
        tree = ast.parse(body)
        base = ast.literal_eval(tree.body[1].value)
        if not isinstance(base, list) or not base or not all(isinstance(x, str) for x in base) or Path(base[0]).name != 'agent-browser':
            return None
        template = ast.parse("import os, subprocess, sys\nbase=" + repr(base) +
            "\nos.environ.pop('AGENT_BROWSER_AUTO_CONNECT',None)\nsys.exit(subprocess.run(base+sys.argv[1:]).returncode)\n")
        return base if ast.dump(tree) == ast.dump(template) else None
    except (ValueError, SyntaxError, IndexError, AttributeError, TypeError):
        return None


def browser_sources(observations, cwd):
    """Annotate copies with supported argv; original IDs/arguments/output stay exact.

    Only newline-separated literal commands and the exact cat heredoc wrapper
    are supported. Heredoc content, shell substitution and compound lines never
    become operations. No synthetic child calls or outputs are generated.
    """
    from lhc_outcome_review import command, local_native_path
    wrappers, result = {}, []
    for call, output in observations:
        copy = dict(call); operations = []
        args = call.get('arguments') or '{}'
        try:
            args = json.loads(args) if isinstance(args, str) else args
            directory = local_native_path(args.get('workdir') or args.get('cwd') or call.get('_native_cwd') or cwd)
            directory = (cwd / directory).resolve()
            directory.relative_to(cwd)
            text = args.get('cmd') or args.get('command') or ''
        except (ValueError, TypeError, AttributeError):
            result.append((copy, output)); continue
        # Only native shell command records, never functions.exec source strings.
        if call.get('name') not in {'exec_command', 'shell_command', 'bash'}:
            result.append((copy, output)); continue
        lines = text.splitlines(); index = 0; unsafe_shell = False
        while index < len(lines):
            line = lines[index]; index += 1
            creation = re.fullmatch(r"cat > ([\w./-]+\.py) <<'([A-Za-z_]+)'", line)
            if creation:
                end = next((i for i in range(index, len(lines)) if lines[i] == creation[2]), len(lines))
                path = (directory / creation[1]).resolve()
                wrappers.pop(path, None)
                base = literal_wrapper('\n'.join(lines[index:end]))
                if base and path.is_relative_to(cwd) and end < len(lines):
                    wrappers[path] = (base, call.get('call_id'))
                index = end + 1; continue
            if '<<' in line:
                # Unsupported heredoc: skip its body, then resume literal lines.
                match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
                if not match:
                    break
                index = next((i + 1 for i in range(index, len(lines)) if lines[i] == match[1]), len(lines))
                continue
            try:
                lexer = shlex.shlex(line, posix=True, punctuation_chars=';&|<>')
                lexer.whitespace_split = True
                tokens = list(lexer)
            except ValueError:
                break  # Never treat lines inside a quoted multiline value as commands.
            # We cannot attribute output to one command inside shell control
            # flow, pipelines, redirections, or a compound command. Fail closed
            # for the complete native call, including earlier literal lines.
            control_words = {'if','then','elif','else','fi','for','while','until',
                             'select','do','done','case','esac','function'}
            if any((token and set(token) <= set(';&|<>(){}!')) or token in control_words
                   for token in tokens):
                unsafe_shell = True
                break
            _, words = command({'arguments': json.dumps({'cmd': line})})
            if not words or any(token in line for token in ('$(', '`', '${')):
                continue
            wrapper_call = None
            if re.fullmatch(r'python(?:3(?:\.\d+)?)?', Path(words[0]).name) and len(words) > 1:
                wrapper = wrappers.get((directory / words[1]).resolve())
                if not wrapper:
                    continue
                base, wrapper_call = wrapper
                words = base + words[2:]
            if Path(words[0]).name != 'agent-browser':
                # A write or unknown command mentioning a wrapper invalidates it.
                for path in list(wrappers):
                    if str(path) in line or path.name in line:
                        wrappers.pop(path)
                continue
            rest, context = words[1:], {}
            while len(rest) >= 2 and rest[0].startswith('--'):
                context[rest[0]] = rest[1]; rest = rest[2:]
            if not rest or not context.get('--session'):
                continue
            operations.append({'argv': rest, 'context': (context.get('--session'), context.get('--namespace')),
                               'wrapper_call': wrapper_call})
        copy['_browser_ops'] = [] if unsafe_shell else operations
        result.append((copy, output))
    return result


def browser_journey(refs, by_call, target):
    contexts = {}
    for ref, (call, output) in by_call.items():
        if ref not in refs:
            continue
        for operation in call.get('_browser_ops', []):
            args, key = operation['argv'], tuple(operation['context'])
            action = args[0]
            urls = re.findall(r'https?://[^\s\"<>\\]+', output)
            # Actual navigation/readback must confirm the origin, not merely
            # contain a URL literal inside an eval script or command argument.
            if action == 'open' and len(args) == 2:
                contexts[key] = {'target': url_matches(args[1], target) and any(url_matches(u, target) for u in urls), 'acted': False}
            elif args[:2] == ['get', 'url']:
                contexts[key] = {'target': any(url_matches(u, target) for u in urls), 'acted': contexts.get(key, {}).get('acted', False)}
            current = contexts.get(key, {})
            if not current.get('target') or not output.strip():
                continue
            acts = action in {'click','fill','type','press','select','submit'} or args[:2] == ['mouse','wheel']
            if acts and '✗' not in output and '✓ Done' in output:
                current['acted'] = True
            elif current.get('acted') and (action in {'snapshot','screenshot','eval','evaluate'} or args[:2] == ['get','text']):
                return True
    return False


def prepare(outcome, meta, observations, owner, binding, cwd):
    """Verify original contract and direct native authorization; return local floor.

    Revision differences are historical report-only bindings, never acceptance
    of a newer product revision. The normal current scope hash check still runs.
    """
    import lhc_milestone as native
    from lhc_outcome_review import command
    if outcome['task_class'] != 'testing' or outcome['owner']['session_id'] != owner or meta.get('id') != owner:
        raise ValueError('testing reuse is own testing self-check only')
    if any(outcome['stages'][s]['status'] != 'not-applicable' for s in ('technical','deploy','publication','integration')):
        raise ValueError('testing reuse cannot close engineering/remote stages')
    calls = {c.get('call_id'): (c,o) for c,o in observations}
    contract_call, output = calls.get(binding.get('contract_call'), ({}, ''))
    args = json.loads(contract_call.get('arguments') or '{}')
    # The output must be an actual native outcome contract invocation, not cat/echo.
    lines = (args.get('cmd') or '').splitlines()
    contract_words = []
    for line in lines:
        # Existing initial command used a trailing git status query on the same
        # line. Recognize only this leading CLI invocation; never parse the tail.
        lexer = shlex.shlex(line, posix=True, punctuation_chars=';&|<>')
        lexer.whitespace_split = True
        words = []
        try:
            for token in lexer:
                if token == ';':
                    break
                if token and set(token) <= set(';&|<>'):
                    words = []; break
                words.append(token)
        except ValueError:
            continue
        if len(words) > 2 and re.fullmatch(r'python(?:3)?', Path(words[0]).name) and Path(words[1]).name == 'lhc_outcome.py' and 'contract' in words:
            contract_words = words; break
    if not contract_words or contract_call.get('_exit_code', 0) != 0:
        raise ValueError('reuse needs original native contract call')
    original, _ = json.JSONDecoder().raw_decode(output)
    for key in ('id','owner','task_class','original_goal','owned_paths','stage_claims','integration_policy'):
        if original.get(key) != outcome.get(key):
            raise ValueError('reuse changes more than coverage metadata: ' + key)
    if any(original['stages'][s]['status'] != outcome['stages'][s]['status'] for s in original['stages']):
        raise ValueError('reuse changed stage applicability')
    if not original.get('contract_confirmed') or original.get('coverage') or not outcome.get('coverage'):
        raise ValueError('reuse only binds coverage added to an already confirmed contract')
    if any(original['canary'][key] != outcome['canary'][key] for key in ('scenario','target','expected')):
        raise ValueError('reuse original canary mismatch')
    for key, value in (('--session-id',owner),('--cwd',str(cwd)),('--runtime',outcome['owner']['harness'])):
        if key not in contract_words or contract_words[contract_words.index(key)+1] != value:
            raise ValueError('original contract invocation identity mismatch')
    authorizations = [a for a in meta['assignments'] if a['index'] == binding.get('authorization_index')]
    quote = binding.get('authorization_quote')
    if len(authorizations) != 1 or not quote or quote.strip() != authorizations[0]['text'].strip():
        raise ValueError('reuse requires exact direct native user authorization')
    # Scope is explicit input backed by the original user bytes, not inferred
    # permission from a tool result or a saved prompt.
    if not re.match(r'\s*(?:Reuse already performed testing|Продолжай:\s*привяжи уже выполненные проверки)', quote, re.I):
        raise ValueError('native user quote does not bind existing testing reuse')
    assessments = [r for r in meta['own_reports'] if r['index'] == binding.get('assessment_index')]
    if len(assessments) != 1:
        raise ValueError('reuse needs original native assessment index')
    # A later report refresh does not revoke this exact native reuse grant.
    if (authorizations[0]['index'] <= max(contract_call['_source_index'], assessments[0]['index'])
            or native.timestamp(authorizations[0]['at']) < max(
                native.timestamp(original['evidence_after']), native.timestamp(assessments[0]['at']))):
        raise ValueError('reuse authorization predates original contract or assessment')
    baseline = binding.get('baseline_commit','')
    reports = set(original['owned_paths'])
    historical_report_route = bool(reports) and all(
        p.startswith('.agents/tasks/') and p.endswith('.md') for p in reports)
    if historical_report_route and not baseline:
        raise ValueError('historical testing report reuse requires exact native Git baseline')
    if baseline or original['revision'] != outcome['revision']:
        baseline_call, baseline_output = calls.get(binding.get('baseline_call'), ({},''))
        if not re.fullmatch('[0-9a-f]{8,40}',baseline) or baseline not in baseline_output:
            raise ValueError('historical revision requires exact native Git baseline')
        if baseline_call.get('_source_index', -1) >= contract_call.get('_source_index', -1):
            raise ValueError('native Git baseline must precede original contract')
        # No arbitrary string in a file/echo is a native Git baseline.
        raw_cmd = json.loads(baseline_call.get('arguments') or '{}').get('cmd','')
        if not re.search(r'(?:^|[;\n])\s*git (?:log|rev-parse)\b',raw_cmd):
            raise ValueError('historical baseline must be an actual native Git read')
        if not reports or any(not p.startswith('.agents/tasks/') or not p.endswith('.md') for p in reports):
            raise ValueError('revision exception only covers exact owned testing reports')
        changed = set(native.git(cwd,'diff','-z',baseline,'HEAD','--name-only').decode().split('\0'))
        changed.update(native.git(cwd,'diff','-z','--name-only').decode().split('\0'))
        changed.update(native.git(cwd,'diff','-z','--cached','--name-only').decode().split('\0'))
        changed.discard('')
        if changed - reports:
            raise ValueError('product changed since historical testing baseline')
        if original['revision'] != outcome['revision'] and not changed:
            raise ValueError('historical report revision changed without a report-only Git delta')
    return original


def assessment(outcome, meta, observations, binding, original, cwd):
    """Bind original prose and per-case raw outputs, never rewrite the source."""
    from lhc_outcome import scope_revision
    by_call = {c['call_id']:(c,o) for c,o in observations if c.get('call_id')}
    reports = [r for r in meta['own_reports'] if r['index'] == binding.get('assessment_index')]
    if len(reports) != 1:
        raise ValueError('reuse needs original native assessment index')
    report = reports[0]; text = report['text']
    coverage = {}; all_refs = []
    for claim in binding.get('coverage',[]):
        item, refs, quote, observed = (claim.get(k) for k in ('item','calls','quote','observed'))
        if (item not in outcome['coverage'] or item in coverage or claim.get('verdict') not in {'passed','defect'}
                or not quote or quote not in text or not observed or not refs or any(ref not in by_call for ref in refs)
                or not any(observed in by_call[ref][1] for ref in refs)
                or not browser_journey(refs,by_call,outcome['canary']['target'])):
            raise ValueError('coverage binding needs original assessment, raw comparison and target/action/result')
        coverage[item] = {'verdict':claim['verdict'],'expected':outcome['canary']['expected'],
                          'observed':observed,'assessment_quote':quote,'evidence_calls':refs}
        all_refs += refs
    if set(coverage) != set(outcome['coverage']):
        raise ValueError('reuse must bind every assigned coverage item')
    defect = binding.get('defect',{})
    # This small route deliberately preserves an existing defect result. It
    # cannot mint a whole-product PASS from successful individual checks.
    if not defect.get('quote') or defect['quote'] not in text or not defect.get('calls') or any(ref not in by_call for ref in defect['calls']) or not any(defect['quote'] in by_call[ref][1] for ref in defect['calls']):
        raise ValueError('reuse requires original product defect assessment and raw observation')
    all_refs += defect['calls']
    refs = [ref for ref in by_call if ref in all_refs]
    return {'outcome_id':outcome['id'],'revision':scope_revision(outcome,cwd),
            **{k:outcome['canary'][k] for k in ('scenario','target','expected')},
            'assignment_verdict':'complete','product_verdict':'changes-required','comparison':text,
            'coverage':coverage,'stages':{'consumer':{'expected':outcome['canary']['expected'],'observed':text,'evidence_calls':refs}}}, report
