#!/usr/bin/env python3
"""Local authoritative plans; asynchronous, rebuildable, one-way HTTP mirror.

Only watch/once use the network. register/mark/revise never contact a server.
Source: plan.json + leaves/*.json. Local history: .lhc-publication/. Derived:
pending snapshot, server replica, HTML, dashboard. No uploaded code is executed.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import hmac
import html
import ipaddress
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sys
import threading
import time
import urllib.request
import urllib.error

import lhc_plan_json as leaves
import lhc_plan_publish as pub
import lhc_plan_transport as transport

CONFIG = Path.home() / '.config/lhc/plan-mirror/client.json'
MAX_BYTES = 8 * 1024 * 1024
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}')


def read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def config(path):
    path = Path(path).expanduser().resolve()
    value = read(path)
    if not isinstance(value, dict):
        raise ValueError('configuration must be a JSON object')
    return value


def directory(plan):
    if Path(plan).name == 'plan.graph.json':
        # Explicit legacy sources stay read-only; history cannot collide with
        # a native plan's .lhc-publication in the same directory.
        path = Path(plan).resolve()
        return path.parent / ('.lhc-graph-publication-' + hashlib.sha256(str(path).encode()).hexdigest()[:16])
    return Path(plan) / pub.STATE_DIR


def worktree_root(plan):
    """Return the nearest explicit Git worktree containing this plan source."""
    path = Path(plan).expanduser().resolve()
    start = path.parent if path.name == 'plan.graph.json' else path
    for candidate in (start, *start.parents):
        marker = candidate / '.git'
        if marker.is_dir() or marker.is_file():
            return candidate
    return None


def binding(plan, explicit=None):
    """Persisted plan binding wins over defaults; override is optional."""
    saved = read(directory(plan) / 'mirror.json', {})
    if explicit:
        return Path(explicit).expanduser().resolve()
    if saved.get('config'):
        return Path(saved['config'])
    candidate = Path(os.environ.get('LHC_PLAN_MIRROR_CONFIG', CONFIG)).expanduser()
    if candidate.is_file():
        cfg = config(candidate)
        path = Path(plan).resolve()
        if str(path) in cfg.get('plans', []) or any(
                Path(root).expanduser().resolve() in path.parents or Path(root).expanduser().resolve() == path
                for root in cfg.get('roots', [])):
            return candidate.resolve()
    return None


def register(plan, config_path):
    """Local registration and identity only. Never render, sleep or use network."""
    plan = Path(plan).resolve()
    config_path = Path(config_path).expanduser().resolve()
    cfg = config(config_path)
    local = Path(cfg['data_dir']).expanduser()
    with leaves.file_lock(local / 'registry.lock'):
        registry = read(local / 'registry.json', {'machine': secrets.token_hex(16), 'plans': {}})
        owner = registry['machine'] + '-' + hashlib.sha256(str(plan).encode()).hexdigest()[:24]
        if registry['plans'].get(str(plan)) != owner:
            registry['plans'][str(plan)] = owner
            pub.atomic(local / 'registry.json', registry)
    with leaves.file_lock(directory(plan) / 'publish.lock'):
        state = read(directory(plan) / 'state.json')
        if state is None:
            identity = secrets.token_hex(12)
            state = {'identity': identity, 'project': pub.project_slug(plan.parent if plan.name == 'plan.graph.json' else plan),
                     'name': time.strftime('plan-%Y%m%d-%H%M-') + identity,
                     'config': str(config_path), 'autopublish': False}
            pub.atomic(directory(plan) / 'state.json', state)
        saved = read(directory(plan) / 'mirror.json', {})
        if saved and saved.get('owner') != owner:
            raise ValueError('local mirror owner conflict; use original registered source')
        # 1.5.52 clients do not know mirror.json. Their automatic legacy
        # publisher returns before config/network when this flag is false.
        # Preserve the URL, original config and history for migrations.
        if state.get('autopublish'):
            state['autopublish'] = False
            pub.atomic(directory(plan) / 'state.json', state)
        link = {'config': str(config_path), 'owner': owner}
        worktree = worktree_root(plan)
        if worktree:
            link['worktree'] = str(worktree)
        if saved.get('activations'):
            link['activations'] = saved['activations']
        if saved != link:
            pub.atomic(directory(plan) / 'mirror.json', link)
    return {'url': cfg['base_url'].rstrip('/') + '/' + state['project'] + '/' + state['name'] + '/', 'owner': owner}


def mark(plan, config_path=None):
    """Cheap local CLI hook. Observer detects file bytes independently."""
    path = binding(plan, config_path)
    if path is None:
        return False
    if not (directory(plan) / 'mirror.json').exists():
        register(plan, path)
    # No network, renderer or publication lock on ordinary writes.
    pub.atomic(directory(plan) / 'dirty.json', {'at': pub.now()})
    return True


def fingerprint(plan):
    plan = Path(plan)
    graph_source = plan.name == 'plan.graph.json'
    paths = [plan] if graph_source else [plan / 'plan.json', *sorted((plan / 'leaves').glob('*.json'))]
    if not paths[0].is_file() or (not graph_source and len(paths) < 2):
        raise ValueError('source temporarily absent; preserving last good snapshot')
    result = []
    # Presentation migration: old unchanged source must be captured once too.
    result.append(('plan_origin_schema', 1))
    origin = plan / '.lhc-publication/plan-origin.json'
    if not graph_source and origin.is_file():
        paths.append(origin)
    for path in paths:
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise ValueError('unsafe or oversized source')
        result.append((str(path.name if graph_source else path.relative_to(plan)), hashlib.sha256(path.read_bytes()).hexdigest()))
    return pub.digest(result)


def observe(document, observed, stamp):
    for task in document['tasks']:
        previous = observed.get(task['id'], {})
        completed = list(previous.get('completed', []))
        if task.get('status') == 'done':
            fact = {k: task[k] for k in ('actual_minutes', 'started_at', 'finished_at') if k in task}
            if fact and fact not in completed:
                completed.append(fact)
        observed[task['id']] = {'task': task, 'completed': completed,
                               'last_seen': previous.get('last_seen', stamp) if previous.get('task') == task else stamp}
    return observed


def capture(plan, *, reason=None):
    """Transactionally save latest pending state + local immutable revisions."""
    plan = Path(plan)
    dest = directory(plan)
    with leaves.file_lock(dest / 'publish.lock'):
        graph_source = plan.name == 'plan.graph.json'
        with nullcontext() if graph_source else leaves.file_lock(plan / '.lhc-leaves.lock'):
            if not graph_source:
                leaves.ensure_plan_origin(plan)
            before = fingerprint(plan)
            document = valid_document(read(plan)) if graph_source else pub.public_document(leaves.build_document(plan))
            if before != fingerprint(plan):
                raise ValueError('files changed during capture; retry after debounce')
        old = read(dest / 'mirror-state.json', {})
        if old.get('source_hash') == before and not reason:
            return old
        if not graph_source:
            graph = leaves.build_graph(plan)
            import lhc_grid
            with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink):
                lhc_grid.main(['render', str(graph), '--out-dir', str(plan)])
        stamp = pub.now()
        observed = observe(document, read(dest / 'observed.json', {}), stamp)
        pub.atomic(dest / 'observed.json', observed)
        revisions = pub.load_revisions(dest)
        if not revisions:
            pub.freeze(dest, document, 'Исходный план', observed)
        elif reason:
            pub.freeze(dest, document, reason, observed)
        state = read(dest / 'state.json')
        link = read(dest / 'mirror.json')
        snapshot = {'schema_version': 1, 'owner': link['owner'],
                    **{k: state[k] for k in ('identity', 'project', 'name')},
                    'seq': old.get('seq', 0) + 1, 'last_file_event': stamp if old.get('source_hash') != before else old.get('last_file_event'),
                    'document': document, 'revisions': pub.load_revisions(dest), 'observed': observed}
        result = {**old, 'source_hash': before, 'seq': snapshot['seq'], 'pending': snapshot,
                  'last_file_event': snapshot['last_file_event'], 'error': None}
        # One atomic durable latest snapshot includes the entire revision history.
        pub.atomic(dest / 'mirror-state.json', result)
        return result


def activate(plan, leaf_id, *, config_path=None, session=None, harness=None,
             owner=None, note=None):
    """Bind one explicitly selected leaf to this local session and observer."""
    plan = Path(plan).expanduser().resolve()
    if not plan.is_dir() or not (plan / 'plan.json').is_file() or not (plan / 'leaves').is_dir():
        raise ValueError('activate requires one selected plan directory with plan.json and leaves/')
    session = session or os.environ.get('CODEX_THREAD_ID', '')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,200}', session or ''):
        raise ValueError('provide the actual session id with CODEX_THREAD_ID or --session')
    harness = harness or ('codex' if os.environ.get('CODEX_THREAD_ID') else '')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,40}', harness or ''):
        raise ValueError('provide the actual harness with --harness')
    owner = owner or os.environ.get('USER') or os.environ.get('USERNAME') or ''
    if not owner.strip():
        raise ValueError('provide the actual owner with --owner')
    root = worktree_root(plan)
    if root is None:
        raise ValueError('selected plan is not inside a Git worktree; refusing to guess its workspace')
    leaf_path = plan / 'leaves' / (leaf_id + '.json')
    leaf = read(leaf_path)
    if not isinstance(leaf, dict) or leaf.get('id') != leaf_id:
        raise ValueError('selected leaf does not exist in this plan')
    if leaf.get('status') in {'done', 'deferred', 'blocked', 'waiting'}:
        raise ValueError('selected leaf is not ready to start; resolve its recorded state first')

    config_path = Path(config_path or os.environ.get('LHC_PLAN_MIRROR_CONFIG', CONFIG)).expanduser().resolve()
    # The local plan lifecycle must remain usable when mirror configuration is
    # absent. Registration is an optional projection; it is never the source of
    # truth and never a prerequisite for starting work.
    link = register(plan, config_path) if config_path.is_file() else None
    if link:
        capture(plan)  # Freeze the selected plan's baseline before changing the leaf.
    stamp = pub.now()
    active = {'session': session, 'harness': harness, 'owner': owner.strip(),
              'worktree': str(root), 'leaf_id': leaf_id, 'updated_at': stamp}
    if link:
        sidecar = directory(plan) / 'mirror.json'
        with leaves.file_lock(directory(plan) / 'publish.lock'):
            saved = read(sidecar, {})
            activations = saved.get('activations', {})
            activations[leaf_id] = active
            saved['activations'] = activations
            pub.atomic(sidecar, saved)
    leaves.update_leaf(plan, leaf_id,
                       {'status': 'running', 'session': session, 'harness': harness,
                        'owner': owner.strip()},
                       note=note or 'Начал работу в текущей сессии')
    if link:
        capture(plan)
    return {'plan': str(plan), 'leaf_id': leaf_id, 'status': 'running',
            'session': session, 'harness': harness, 'owner': owner.strip(),
            'worktree': str(root), 'url': link['url'] if link else None,
            'sync': 'pending' if link else 'local-only'}


def local_publish(plan, config_path=None, reason=None):
    path = binding(plan, config_path)
    if path is None:
        return None
    result = register(plan, path)
    capture(plan, reason=reason)
    return {**result, 'local': True, 'sync': 'pending'}


def discover(cfg):
    local = Path(cfg['data_dir']).expanduser()
    plans = set(read(local / 'registry.json', {}).get('plans', {}))
    plans.update(str(Path(p).expanduser().resolve()) for p in cfg.get('plans', []))
    for source in cfg.get('graph_sources', []):
        path = Path(source).expanduser()
        if not path.is_absolute() or path.name != 'plan.graph.json':
            raise ValueError('graph_sources requires absolute plan.graph.json paths')
        plans.add(str(path.resolve()))
    # Explicit roots only, bounded depth, no symlink traversal or home scan.
    for root in cfg.get('roots', []):
        root = Path(root).expanduser().resolve()
        if root == Path.home() or root == Path('/'):
            raise ValueError('home/filesystem discovery is forbidden; select plan directories')
        for current, dirs, files in os.walk(root, followlinks=False):
            rel = Path(current).relative_to(root)
            dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(current) / d).is_symlink()] if len(rel.parts) < 3 else []
            if 'plan.json' in files and (Path(current) / 'leaves').is_dir():
                plans.add(str(Path(current).resolve()))
                dirs[:] = []
    if len(plans) > 1000:
        raise ValueError('registered plan limit exceeded')
    return sorted(plans)


def secret(path):
    value = Path(path).expanduser().read_text().strip()
    if len(value) < 24 or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('protected token must be at least 24 URL-safe characters')
    return value


def sync(plan, cfg):
    """Only observer calls this. The server can disappear without local loss."""
    dest = directory(plan)
    state = read(dest / 'mirror-state.json', {})
    if not state.get('pending'):
        return
    data = pub.encoded(state['pending']).encode()
    if len(data) > MAX_BYTES:
        raise ValueError('snapshot size limit exceeded')
    req = urllib.request.Request(cfg['endpoint'].rstrip('/') + '/v1/snapshots', data=data,
                                 headers={'Authorization': 'Bearer ' + secret(cfg['token_file']), 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=min(10, max(.1, cfg.get('timeout_seconds', 3)))) as response:
        receipt = json.loads(response.read(MAX_BYTES))
    if receipt.get('seq') != state['seq'] or receipt.get('identity') != state['pending']['identity']:
        raise ValueError('unexpected server receipt')
    with leaves.file_lock(dest / 'publish.lock'):
        latest = read(dest / 'mirror-state.json')
        latest.update(last_successful_sync=pub.now(), server_receipt=receipt, error=None)
        pub.atomic(dest / 'mirror-state.json', latest)


def record_error(plan, error):
    dest = directory(plan)
    with leaves.file_lock(dest / 'publish.lock'):
        state = read(dest / 'mirror-state.json', {})
        # Do not persist remote bodies (may include credentials or proxy details).
        state['error'] = ('HTTP 409: конфликт владельца, последовательности или неизменяемой истории; зеркало не перезаписано'
                          if isinstance(error, urllib.error.HTTPError) and error.code == 409
                          else type(error).__name__ + ': синхронизация или источник недоступны')
        pub.atomic(dest / 'mirror-state.json', state)


def run_observer(config_path, once=False):
    cfg = config(config_path)
    seen, retries, attempted, sent, capture_retries = {}, {}, {}, {}, {}
    local = Path(cfg['data_dir']).expanduser()
    # A second observer must not race sequence generation or network receipts.
    import fcntl
    local.mkdir(parents=True, exist_ok=True)
    with (local / 'observer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            cfg = config(config_path)
            for plan in discover(cfg):
                try:
                    register(plan, config_path)
                    current = fingerprint(plan)
                    previous, since = seen.get(plan, (None, time.monotonic()))
                    if current != previous:
                        seen[plan] = (current, time.monotonic())
                        since = time.monotonic()
                    capture_deadline, capture_failures = capture_retries.get(plan, (0, 0))
                    if current != previous:
                        capture_deadline, capture_failures = 0, 0
                    if once or (attempted.get(plan) != current and time.monotonic() >= capture_deadline and time.monotonic() - since >= max(.05, cfg.get('debounce_seconds', 1))):
                        try:
                            capture(plan)
                            attempted[plan] = fingerprint(plan)
                            seen[plan] = (attempted[plan], time.monotonic())
                            capture_retries[plan] = (0, 0)
                        except (ValueError, OSError) as error:
                            capture_retries[plan] = (time.monotonic() + min(60, 2 ** min(capture_failures, 6)), capture_failures + 1)
                            record_error(plan, error)
                            continue
                    if capture_retries.get(plan, (0, 0))[1]:
                        # A replay of the previous good snapshot must not clear
                        # the current source error while capture is retrying.
                        continue
                    state = read(directory(plan) / 'mirror-state.json', {})
                    deadline, failures = retries.get(plan, (0, 0))
                    if not failures and state.get('seq') != sent.get(plan):
                        deadline = 0
                    if time.monotonic() >= deadline:
                        try:
                            sync(plan, cfg)
                            sent[plan] = state.get('seq')
                            retries[plan] = (time.monotonic() + 30, 0)
                        except Exception as error:
                            retries[plan] = (time.monotonic() + min(60, 2 ** min(failures, 6)), failures + 1)
                            record_error(plan, error)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    record_error(plan, error)
            if once:
                return
            time.sleep(max(.05, cfg.get('poll_seconds', 1)))


def valid_document(value):
    if not isinstance(value, dict) or not isinstance(value.get('tasks'), list) or not 1 <= len(value['tasks']) <= 1000:
        raise ValueError('invalid document')
    if not all(isinstance(task, dict) for task in value['tasks']):
        raise ValueError('invalid task object')
    clean = pub.public_document(value)
    if 'plan_origin' in clean:
        leaves.validate_plan_origin(clean['plan_origin'])
    for task in clean['tasks']:
        if not isinstance(task.get('id'), str) or not IDENT.fullmatch(task['id']):
            raise ValueError('invalid task identity')
        leaves.task_from_leaf(task, Path(task['id'] + '.json'))
    # Renderer parser verifies dependencies, IDs, slots and cycles. No paths
    # from the upload are ever opened. public_document is a second allowlist.
    import lhc_grid
    graph = lhc_grid.parse_graph_json(pub.schedule_document(clean))
    graph.resolve_dependencies()
    ids = [task['id'] for task in clean['tasks']]
    if len(set(ids)) != len(ids) or any(not IDENT.fullmatch(i) for i in ids):
        raise ValueError('invalid task identities')
    return clean


def validate_snapshot(value):
    required = {'schema_version', 'owner', 'project', 'name', 'identity', 'seq', 'last_file_event', 'document', 'revisions', 'observed'}
    if not isinstance(value, dict) or set(value) != required or value['schema_version'] != 1:
        raise ValueError('invalid snapshot schema')
    for key in ('owner', 'project', 'name', 'identity'):
        if not isinstance(value[key], str) or not IDENT.fullmatch(value[key]):
            raise ValueError('unsafe identifier')
    if type(value['seq']) is not int or value['seq'] < 1 or not pub.timestamp(value['last_file_event']):
        raise ValueError('invalid sequence/event')
    value['document'] = valid_document(value['document'])
    revisions = value['revisions']
    if not isinstance(revisions, list) or not 1 <= len(revisions) <= 1000:
        raise ValueError('invalid revisions')
    for number, rev in enumerate(revisions, 1):
        if not isinstance(rev, dict) or set(rev) - {'id', 'reason', 'created_at', 'document', 'observed'} or rev['id'] != f'r{number:03}' or not pub.timestamp(rev['created_at']):
            raise ValueError('invalid revision')
        rev['reason'] = pub.safe_text(rev['reason'])
        rev['document'] = valid_document(rev['document'])
        rev['observed'] = clean_observed(rev.get('observed', {}))
    value['observed'] = clean_observed(value['observed'])
    return value


def clean_observed(value):
    if not isinstance(value, dict) or len(value) > 5000:
        raise ValueError('invalid observed history')
    result = {}
    for identity, item in value.items():
        if not IDENT.fullmatch(identity) or not isinstance(item, dict) or not isinstance(item.get('task'), dict):
            raise ValueError('invalid observed task')
        task = pub.public_document({'tasks': [item['task']]})['tasks'][0]
        if item.get('last_seen') is not None and not pub.timestamp(item['last_seen']):
            raise ValueError('invalid last seen timestamp')
        facts = []
        for fact in item.get('completed', []):
            if not isinstance(fact, dict):
                raise ValueError('invalid completed fact')
            facts.append({k: pub.safe_text(v) if isinstance(v, str) else v for k, v in fact.items()
                          if k in {'actual_minutes', 'started_at', 'finished_at'}})
        result[identity] = {'task': task, 'last_seen': item.get('last_seen'), 'completed': facts}
    return result


class Conflict(ValueError):
    pass


class Replica:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = Path(cfg['data_dir']).expanduser()
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.renderer = pub.digest({name: Path(pub.__file__).with_name(name).read_text()
                                    for name in ('lhc_plan_publish.py', 'lhc_plan_transport.py', 'lhc_grid.py', 'lhc_plan_ui.py')})

    def entries(self):
        return [read(p) for p in self.data.glob('*.json')]

    def render(self, entry):
        snapshot = entry['snapshot']
        revisions = snapshot['revisions']
        doc, observed = snapshot['document'], snapshot['observed']
        version = pub.digest({'snapshot': snapshot, 'renderer': self.renderer})
        files = {}
        for i, rev in enumerate(revisions):
            files[rev['id'] + '.html'] = pub.page(revisions[0]['document'], rev['document'], rev['document'], revisions[:i+1], rev['id'], rev['created_at'], False, observed=rev.get('observed'))
            files['view-' + rev['id'] + '.html'] = pub.page(revisions[0]['document'], rev['document'], rev['document'], revisions, rev['id'], rev['created_at'], False, observed=rev.get('observed'))
        files['index.html'] = pub.page(revisions[0]['document'], doc, doc, revisions, revisions[-1]['id'], snapshot['last_file_event'], True, version, observed)
        files['version.json'] = pub.encoded({'version': version, 'updated_at': snapshot['last_file_event'], 'revision': revisions[-1]['id'], 'server_receipt': entry['receipt']})
        # Preserve already published immutable HTML, including a legacy renderer.
        target = Path(self.cfg['webroot']) / snapshot['project'] / snapshot['name']
        if target.is_symlink() and (target / '.lhc-owner').read_text() == snapshot['identity']:
            for name in files:
                if re.fullmatch(r'r[0-9]+\.html', name) and (target / name).is_file():
                    files[name] = (target / name).read_bytes().decode('utf-8')
        transport.deploy(self.cfg['webroot'], snapshot['project'], snapshot['name'], snapshot['identity'], version, files)

    def ingest(self, snapshot):
        snapshot = validate_snapshot(snapshot)
        with self.lock, leaves.file_lock(self.data / 'ingest.lock'):
            path = self.data / (snapshot['identity'] + '.json')
            previous = read(path)
            for entry in self.entries():
                old = entry['snapshot']
                if old['identity'] == snapshot['identity'] or (old['project'], old['name']) == (snapshot['project'], snapshot['name']):
                    if any(old[k] != snapshot[k] for k in ('identity', 'owner', 'project', 'name')):
                        raise Conflict('source owner or URL conflict')
            if previous:
                old = previous['snapshot']
                if snapshot['seq'] < old['seq']:
                    raise Conflict('stale sequence')
                if snapshot['seq'] == old['seq']:
                    if pub.digest(snapshot) != pub.digest(old):
                        raise Conflict('sequence reused for different data')
                    target = Path(self.cfg['webroot']) / old['project'] / old['name']
                    required_files = ['index.html', 'version.json', *[prefix + r['id'] + '.html' for r in old['revisions'] for prefix in ('', 'view-')]]
                    if not previous.get('rendered', True) or not all((target / name).is_file() for name in required_files):
                        self.render(previous)
                        previous['rendered'] = True
                        pub.atomic(path, previous)
                    return previous['receipt']
                if snapshot['revisions'][:len(old['revisions'])] != old['revisions']:
                    raise Conflict('immutable revisions changed')
                for identity, observed in old['observed'].items():
                    new = snapshot['observed'].get(identity)
                    if not new or any(fact not in new['completed'] for fact in observed['completed']):
                        raise Conflict('observed completed facts removed')
            receipt = {'identity': snapshot['identity'], 'seq': snapshot['seq'], 'received_at': pub.now(),
                       'url': self.cfg['base_url'].rstrip('/') + '/' + snapshot['project'] + '/' + snapshot['name'] + '/'}
            entry = {'snapshot': snapshot, 'receipt': receipt, 'rendered': False}
            # Commit sequence ownership before derived rendering. A process
            # crash after replacing HTML must never make an older seq current.
            pub.atomic(path, entry)
            self.render(entry)
            entry['rendered'] = True
            pub.atomic(path, entry)
            return receipt

    def dashboard(self):
        entries = sorted(self.entries(), key=lambda x: pub.timestamp(x['snapshot']['last_file_event']), reverse=True)
        esc = lambda s: html.escape(str(s), quote=True)
        groups = {}
        counts = {'active': 0, 'blocked': 0, 'completed': 0}
        for entry in entries:
            snap, receipt = entry['snapshot'], entry['receipt']
            age = time.time() - pub.timestamp(snap['last_file_event']).timestamp()
            statuses = [t.get('status') for t in snap['document']['tasks']]
            state = ('completed' if statuses and all(s == 'done' for s in statuses)
                     else 'blocked' if any(s in {'blocked', 'waiting'} for s in statuses) else 'active')
            counts[state] += 1
            label = {'active': 'В плане: в работе', 'blocked': 'В плане: заблокировано',
                     'completed': 'В плане: завершено'}[state]
            freshness = 'данные устарели' if age > 300 else 'свежие данные'
            title = snap['document'].get('title') or snap['name']
            # Routes come from validated stable identifiers, never a client-supplied URL.
            url = '/' + snap['project'] + '/' + snap['name'] + '/'
            revision = snap['revisions'][-1]['id']
            groups.setdefault(snap['project'], []).append(
                f'<article data-state="{state}" data-search="{esc(snap["project"] + " " + title + " " + snap["name"])}">'
                f'<div class="plan-heading"><h3><a href="{url}">{esc(title)}</a></h3>'
                f'<span class="state {state}">{label}</span></div>'
                f'<p class="meta">Событие файла: <time>{esc(snap["last_file_event"])}</time> · {freshness}<br>'
                f'Приём сервером: <time>{esc(receipt["received_at"])}</time></p>'
                f'<a class="revision" href="{url}view-{revision}.html">Ревизия {revision}</a></article>')
        sections = ''.join(f'<section class="project"><h2>{esc(project)} <span>{len(rows)} пл.</span></h2>'
                           + ''.join(rows) + '</section>' for project, rows in groups.items())
        summary = (f'<div id="totals">Проектов: <b>{len(groups)}</b> · Планов: <b>{len(entries)}</b>'
                   f'<span>В работе: {counts["active"]} · Заблокировано: {counts["blocked"]} · Завершено: {counts["completed"]}</span></div>')
        empty = '<p class="empty">Пока нет синхронизированных планов. Они появятся после первой успешной синхронизации источника.</p>' if not entries else ''
        return '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Проекты и планы · LHC</title>
<style>
*{box-sizing:border-box}body{font:15px/1.5 system-ui,sans-serif;background:#f5f6f8;color:#202938;max-width:1080px;margin:auto;padding:32px 24px}header{margin-bottom:24px}.brand{color:#657087;font-size:12px;letter-spacing:.14em}h1{font-size:32px;line-height:1.2;margin:8px 0 12px}h2{font-size:20px;margin:28px 0 10px;overflow-wrap:anywhere}h2 span{font-size:13px;font-weight:400;color:#657087}h3{font-size:17px;margin:0;overflow-wrap:anywhere}a{color:#255fa5;text-decoration:none}a:hover{text-decoration:underline}p{overflow-wrap:anywhere}.intro,.meta,#connection{color:#657087}.intro{max-width:780px}#totals{font-size:17px;margin-bottom:20px}#totals span{display:block;color:#657087;font-size:14px;margin-top:5px}.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:center}input,select{font:inherit;padding:10px 12px;border:1px solid #bbc5d3;border-radius:8px;background:white;color:inherit}input{width:min(100%,420px)}label{display:flex;gap:8px;align-items:center}article{background:white;border:1px solid #dce1e8;border-radius:10px;padding:16px 20px;margin-bottom:8px}.plan-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px}.state{font-size:12px;white-space:nowrap;border-radius:5px;padding:3px 8px;background:#edf2f9;color:#315b8c}.blocked{background:#fff3df;color:#805912}.completed{background:#eaf3ef;color:#38664c}.meta{font-size:12px;margin:8px 0}.revision{font-size:12px}.empty{padding:24px;background:white;border:1px dashed #bbc5d3;border-radius:10px}[hidden]{display:none!important}#connection{font-size:13px;min-height:20px}#signin{font-weight:600}input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid #255fa5;outline-offset:3px}@media(max-width:600px){body{padding:20px 14px}h1{font-size:27px}.plan-heading{display:block}.state{display:inline-block;margin-top:8px}article{padding:14px}.toolbar,label,input,select{width:100%}label{flex-wrap:wrap}}
</style></head><body><header><div class="brand">LAST HUMAN COMMIT</div><h1>Проекты и планы</h1><p class="intro">Все планы, принятые этим зеркалом. Проекты и планы упорядочены по последнему изменению исходного файла. Статус сообщает план. Живость агента: неизвестна.</p></header>
<div class="toolbar"><label for="search">Поиск <input id="search" type="search" placeholder="Проект или план" autocomplete="off"></label><label for="scope">Показывать <select id="scope"><option value="all">Все</option><option value="active">В работе</option></select></label></div>
<p id="connection" role="status" aria-live="polite">Последний известный снимок</p><a id="signin" href="/" hidden>Войти снова через SSO</a>
<main data-lhc-catalog="1">''' + summary + sections + empty + '''</main><p id="no-matches" class="empty" hidden>По этому запросу планов нет. Измените поиск или выберите «Все».</p><script>
const search=document.getElementById('search'),scope=document.getElementById('scope');
function filter(){let visible=0;const query=search.value.trim().toLocaleLowerCase('ru');document.querySelectorAll('.project').forEach(group=>{let count=0;group.querySelectorAll('article').forEach(row=>{row.hidden=!(row.dataset.search.toLocaleLowerCase('ru').includes(query)&&(scope.value==='all'||row.dataset.state!=='completed'));if(!row.hidden)count++;});group.hidden=count===0;visible+=count;});document.getElementById('no-matches').hidden=visible>0||!document.querySelector('article');}
search.addEventListener('input',filter);scope.addEventListener('change',filter);
let refreshing=false;
async function refresh(){if(refreshing)return;refreshing=true;const badge=document.getElementById('connection'),signin=document.getElementById('signin');try{const r=await fetch(location.href,{cache:'no-store',redirect:'manual'});if(r.status===401||r.status===403||r.status===0||r.type==='opaqueredirect'||r.status>=300&&r.status<400){signin.hidden=false;badge.textContent='Требуется вход · сохранён последний известный список';return;}if(!r.ok)throw Error();const doc=new DOMParser().parseFromString(await r.text(),'text/html');const next=doc.querySelector('main[data-lhc-catalog="1"]');if(!next){signin.hidden=false;badge.textContent='Требуется вход · сохранён последний известный список';return;}const y=window.scrollY;document.querySelector('main').replaceWith(next);filter();window.scrollTo(0,y);signin.hidden=true;badge.textContent='Связь есть · список проверен '+new Date().toLocaleTimeString();}catch(e){badge.textContent='Нет связи · сохранён последний известный список';}finally{refreshing=false;}}
if(/^https?:$/.test(location.protocol))setInterval(refresh,12000);
</script></body></html>'''


def make_server(cfg):
    replica = Replica(cfg)
    write_token = secret(cfg['token_file'])
    sso_enabled = cfg.get('sso_enabled') is True
    dashboard_key = secret(cfg['dashboard_key_file']) if cfg.get('dashboard_key_file') else None
    for entry in replica.entries():
        replica.render(entry)
        if not entry.get('rendered', True):
            entry['rendered'] = True
            pub.atomic(replica.data / (entry['snapshot']['identity'] + '.json'), entry)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log Bearer tokens or dashboard capability URLs.

        def reply(self, status, value, content_type='application/json'):
            data = (pub.encoded(value) if content_type == 'application/json' else value).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + write_token)

        def proxy_authorized(self):
            try:
                loopback = ipaddress.ip_address(self.client_address[0]).is_loopback
            except ValueError:
                loopback = False
            return (sso_enabled and loopback
                    and self.headers.get_all('X-LHC-SSO-Verified') == ['1'])

        def do_GET(self):
            if self.path == '/health':
                self.reply(200, {'status': 'ok'})
            elif self.path == '/v1/status' and self.authorized():
                self.reply(200, {'plans': [e['receipt'] for e in replica.entries()]})
            elif self.path == '/' and sso_enabled:
                if sso_enabled and not self.proxy_authorized():
                    self.reply(401, {'error': 'SSO authentication required'})
                else:
                    self.reply(200, replica.dashboard(), 'text/html')
            elif (dashboard_key is not None
                  and hmac.compare_digest(self.path, '/dashboard/' + dashboard_key + '/')):
                self.reply(200, replica.dashboard(), 'text/html')
            else:
                self.reply(404, {'error': 'not found'})

        def do_POST(self):
            if self.path != '/v1/snapshots':
                return self.reply(404, {'error': 'not found'})
            if not self.authorized():
                return self.reply(401, {'error': 'authentication required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BYTES or self.headers.get('Transfer-Encoding'):
                    return self.reply(413, {'error': 'invalid payload size'})
                self.connection.settimeout(10)
                data = self.rfile.read(length)
                snapshot = json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
                self.reply(200, replica.ingest(snapshot))
            except Conflict:
                self.reply(409, {'error': 'source/sequence/history conflict; inspect local sync status'})
            except (ValueError, KeyError, TypeError, OSError, RecursionError):
                self.reply(400, {'error': 'invalid source snapshot'})

    server = ThreadingHTTPServer((cfg.get('listen', '127.0.0.1'), int(cfg.get('port', 8769))), Handler)
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('serve', 'watch', 'once', 'register', 'status'):
        cmd = commands.add_parser(name)
        if name == 'register':
            cmd.add_argument('plan_dir', type=Path)
        cmd.add_argument('--config', type=Path, default=CONFIG)
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            make_server(config(args.config)).serve_forever()
        elif args.command in {'watch', 'once'}:
            run_observer(args.config, once=args.command == 'once')
        elif args.command == 'register':
            print(pub.encoded(register(args.plan_dir, args.config)), end='')
        else:
            cfg = config(args.config)
            print(pub.encoded({'plans': [{'plan': p, **{k: v for k, v in read(directory(p) / 'mirror-state.json', {}).items() if k != 'pending'}} for p in discover(cfg)]}), end='')
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print('LHC: проверьте локальный config и status наблюдателя', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
