#!/usr/bin/env python3
"""Local authoritative plans; asynchronous, rebuildable, one-way HTTP mirror.

Only observers and server maintenance refresh prices over the network.
register/mark/revise and HTTP rendering never fetch prices.
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
import urllib.parse
import urllib.request
import urllib.error

import lhc_directives as directives
import lhc_plan_catalog as catalog
import lhc_plan_json as leaves
import lhc_plan_publish as pub
import lhc_plan_transport as transport

CONFIG = Path.home() / '.config/lhc/plan-mirror/client.json'
MAX_BYTES = 8 * 1024 * 1024
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}')


def catalog_identity():
    """Offline identity and freshness; elapsed age alone must not churn pages."""
    import lhc_grid
    source = lhc_grid.price_source()
    return {key: source[key] for key in ('ok', 'reason_code', 'snapshot') if key in source}


def refresh_catalog():
    """Maintenance-only bounded fetch; pinned files remain explicitly pinned."""
    import lhc_grid
    models = lhc_grid.models_module()
    if models is None or os.environ.get(lhc_grid.CATALOG_FILE_ENV):
        return
    loaded = models.load_catalog(cache_dir=os.environ.get(lhc_grid.CATALOG_CACHE_DIR_ENV) or None)
    if loaded.stale:
        raise OSError('каталог моделей пока не обновлён')


class CatalogRefresh:
    """At most one maintenance fetch; retries never delay source or HTTP work."""
    def __init__(self):
        self.worker = None
        self.deadline = 0
        self.failures = 0
        self.completed = 0

    def kick(self):
        if (self.worker is not None and self.worker.is_alive()) or time.monotonic() < self.deadline:
            return
        def run():
            try:
                refresh_catalog()
                self.failures = 0
            except Exception:
                self.failures += 1
            finally:
                self.deadline = time.monotonic() + min(600, 60 * 2 ** max(0, min(self.failures - 1, 4)))
                self.completed += 1
        self.worker = threading.Thread(target=run, daemon=True, name='lhc-price-refresh')
        self.worker.start()


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
        # Every plan in a repository's conventional task folder gets its public
        # link without editing the config, unless the owner turned that off.
        if cfg.get('auto_bind_agent_tasks', True) and path.parent.name == 'tasks' \
                and path.parent.parent.name == '.agents':
            return candidate.resolve()
    return None


def announce_once(plan):
    """True only the first time a plan's public link is handed to the owner."""
    marker = directory(plan) / 'link-announced.json'
    if marker.exists():
        return False
    pub.atomic(marker, {'at': pub.now()})
    return True


def link(plan, config_path=None):
    """Register a plan if a mirror is configured and return its public URL."""
    plan = Path(plan).expanduser().resolve()
    path = binding(plan, config_path)
    if path is None:
        candidate = Path(config_path or os.environ.get('LHC_PLAN_MIRROR_CONFIG', CONFIG)).expanduser()
        path = candidate.resolve() if candidate.is_file() else None
    if path is None:
        raise ValueError('plan mirror is not configured on this host')
    url = register(plan, path)['url']
    pub.atomic(directory(plan) / 'dirty.json', {'at': pub.now()})
    return url


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


def file_stamp(path):
    """Cheap identity for a local file, including atomic replacement and edits."""
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return None
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def source_stamp(plan):
    plan = Path(plan)
    paths = ([plan] if plan.name == 'plan.graph.json' else
             [plan / 'plan.json', *sorted((plan / 'leaves').glob('*.json')),
              plan / '.lhc-publication/plan-origin.json'])
    return tuple((str(path), file_stamp(path)) for path in paths)


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
        message = ('HTTP 409: конфликт владельца, последовательности или неизменяемой истории; зеркало не перезаписано'
                          if isinstance(error, urllib.error.HTTPError) and error.code == 409
                          else type(error).__name__ + ': синхронизация или источник недоступны')
        if state.get('error') != message:
            state['error'] = message
            pub.atomic(dest / 'mirror-state.json', state)


def run_observer(config_path, once=False, *, price_refresh=None):
    cfg = config(config_path)
    seen, retries, attempted, sent, capture_retries = {}, {}, {}, {}, {}
    registered, hashes, states = {}, {}, {}
    cfg_stamp = file_stamp(config_path)
    config_deadline = time.monotonic() + 30
    discovered, next_discovery, registry_stamp = [], 0, None
    local = Path(cfg['data_dir']).expanduser()
    # A second observer must not race sequence generation or network receipts.
    import fcntl
    local.mkdir(parents=True, exist_ok=True)
    with (local / 'observer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            if price_refresh is not None:
                price_refresh.kick()
            stamp = file_stamp(config_path)
            changed_config = stamp != cfg_stamp
            if changed_config or time.monotonic() >= config_deadline:
                fresh = config(config_path)
                changed_config = changed_config or fresh != cfg
                cfg, cfg_stamp = fresh, stamp
                config_deadline = time.monotonic() + 30
            if changed_config:
                registered.clear()
            registry_path = Path(cfg['data_dir']).expanduser() / 'registry.json'
            changed_registry = file_stamp(registry_path) != registry_stamp
            if changed_registry:
                registered.clear()
            if changed_config or changed_registry or time.monotonic() >= next_discovery:
                discovered = discover(cfg)
                next_discovery = time.monotonic() + 5
            for plan in discovered:
                try:
                    dest = directory(plan)
                    registration = (cfg_stamp, file_stamp(dest / 'mirror.json'), file_stamp(dest / 'state.json'))
                    if registered.get(plan) != registration:
                        register(plan, config_path)
                        registered[plan] = (cfg_stamp, file_stamp(dest / 'mirror.json'), file_stamp(dest / 'state.json'))
                    signature = source_stamp(plan)
                    if plan not in hashes or hashes[plan][0] != signature or time.monotonic() - hashes[plan][2] >= 30:
                        hashes[plan] = (signature, fingerprint(plan), time.monotonic())
                    current = hashes[plan][1]
                    previous, since = seen.get(plan, (None, time.monotonic()))
                    if current != previous:
                        seen[plan] = (current, time.monotonic())
                        since = time.monotonic()
                    capture_deadline, capture_failures = capture_retries.get(plan, (0, 0))
                    if current != previous:
                        capture_deadline, capture_failures = 0, 0
                    if once or (attempted.get(plan) != current and time.monotonic() >= capture_deadline and time.monotonic() - since >= max(.05, cfg.get('debounce_seconds', 1))):
                        try:
                            captured = capture(plan)
                            signature = source_stamp(plan)
                            after_capture = fingerprint(plan)
                            attempted[plan] = (captured or {}).get('source_hash', after_capture)
                            hashes[plan] = (signature, after_capture, time.monotonic())
                            seen[plan] = (after_capture, time.monotonic())
                            capture_retries[plan] = (0, 0)
                        except (ValueError, OSError) as error:
                            capture_retries[plan] = (time.monotonic() + min(60, 2 ** min(capture_failures, 6)), capture_failures + 1)
                            record_error(plan, error)
                            continue
                    if capture_retries.get(plan, (0, 0))[1]:
                        # A replay of the previous good snapshot must not clear
                        # the current source error while capture is retrying.
                        continue
                    state_path = dest / 'mirror-state.json'
                    state_stamp = file_stamp(state_path)
                    if plan not in states or states[plan][0] != state_stamp:
                        states[plan] = (state_stamp, read(state_path, {}))
                    state = states[plan][1]
                    receipt = state.get('server_receipt') or {}
                    delivery = ((state.get('pending') or {}).get('identity'), state.get('seq'))
                    acknowledged = (state.get('seq') is not None and receipt.get('seq') == state['seq']
                                    and receipt.get('identity') == (state.get('pending') or {}).get('identity'))
                    if not state.get('pending') or (not state.get('error') and (acknowledged or sent.get(plan) == delivery)):
                        continue
                    deadline, failures = retries.get(plan, (0, 0))
                    if not failures and delivery != sent.get(plan):
                        deadline = 0
                    if time.monotonic() >= deadline:
                        try:
                            sync(plan, cfg)
                            sent[plan] = delivery
                            retries[plan] = (time.monotonic() + 30, 0)
                        except Exception as error:
                            retries[plan] = (time.monotonic() + min(60, 2 ** min(failures, 6)), failures + 1)
                            record_error(plan, error)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    record_error(plan, error)
            registry_stamp = file_stamp(registry_path)
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
        self.cache_lock = threading.Lock()
        self.entry_cache = {}
        self.legacy_cache = {}
        self.renderer = pub.digest({name: Path(pub.__file__).with_name(name).read_text()
                                    for name in ('lhc_plan_publish.py', 'lhc_plan_transport.py', 'lhc_grid.py', 'lhc_plan_ui.py', 'lhc_models.py')})
        self.prices = catalog_identity()

    def refresh_prices(self):
        prices = catalog_identity()
        if prices == self.prices:
            return
        with self.lock, leaves.file_lock(self.data / 'ingest.lock'):
            for entry in self.entries():
                self.render(entry)
            self.prices = prices

    @staticmethod
    def signature(path):
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    def entries(self, *, fresh=False, shared=False):
        """Stat is cheap; unchanged multi-revision JSON is parsed only once.

        Only internal read-only consumers borrow cached objects. Ingest always
        rereads ownership/CAS state under its file lock, and public callers get
        their own copy so validation or accidental edits cannot poison the cache.
        """
        import copy
        paths = list(self.data.glob('*.json'))
        if fresh:
            return [read(path) for path in paths]
        with self.cache_lock:
            now = time.monotonic()
            current = {}
            for path in paths:
                try:
                    signature = self.signature(path)
                except FileNotFoundError:
                    continue
                cached = self.entry_cache.get(path)
                if cached is None or cached[0] != signature or now - cached[2] >= 30:
                    # Same-size in-place writes can share one filesystem clock
                    # tick. Bound that exceptional stale window without polling
                    # and reparsing every complete history on every request.
                    cached = signature, read(path), now
                current[path] = cached
            self.entry_cache = current
            values = [item[1] for item in current.values()]
            return values if shared else copy.deepcopy(values)

    def render(self, entry):
        snapshot = entry['snapshot']
        revisions = snapshot['revisions']
        doc, observed = snapshot['document'], snapshot['observed']
        version = pub.digest({'snapshot': snapshot, 'renderer': self.renderer, 'prices': catalog_identity()})
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
        import copy
        snapshot = copy.deepcopy(snapshot)
        snapshot = validate_snapshot(snapshot)
        with self.lock, leaves.file_lock(self.data / 'ingest.lock'):
            path = self.data / (snapshot['identity'] + '.json')
            previous = read(path)
            for entry in self.entries(fresh=True):
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

    def legacy(self, entries=None):
        """Older standalone publications in the webroot that the mirror never received."""
        known = {(e['snapshot']['project'], e['snapshot']['name'])
                 for e in (self.entries(shared=True) if entries is None else entries)}
        found = []
        with self.cache_lock:
            now = time.monotonic()
            current = {}
            for page in Path(self.cfg['webroot']).glob('*/*/index.html'):
                project, name = page.parent.parent.name, page.parent.name
                if (project, name) in known or not IDENT.fullmatch(project) or not IDENT.fullmatch(name):
                    continue
                try:
                    signature = self.signature(page)
                except FileNotFoundError:
                    continue
                cached = self.legacy_cache.get(page)
                if cached is None or cached[0] != signature or now - cached[2] >= 30:
                    title = re.search(r'<title>(.*?)</title>', page.read_text(errors='replace')[:4096], re.S)
                    cached = signature, (project, name, html.unescape(title.group(1)).strip() if title else name), now
                current[page] = cached
                found.append(cached[1])
            self.legacy_cache = current
        return found

    def dashboard(self):
        entries = self.entries(shared=True)
        # Render time-dependent ETA and stalled state on every request.
        return catalog.render(entries, self.legacy(entries))

    def directives(self, project, request=None):
        """The live directives of a project; request is one owner action to apply first."""
        path = self.data / 'directives' / (project + '.json')
        with self.lock, leaves.file_lock(self.data / 'directives.lock'):
            doc = directives.load(path)
            moved = directives.sweep(doc)
            snapshot = directives.apply(doc, request) if request else directives.view(doc)
            if request or moved:
                directives.save(path, doc)
            return snapshot

    def directive_counts(self):
        counts = {}
        for path in sorted((self.data / 'directives').glob('*.json')):
            counts[path.stem] = len(self.directives(path.stem)['active'])
        return counts


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

        def directive_project(self, prefix):
            name = urllib.parse.unquote(self.path[len(prefix):].split('?')[0]).strip('/')
            return name if name and name == pub.slug(name) else None

        def read_body(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BYTES or self.headers.get('Transfer-Encoding'):
                raise ValueError('invalid payload size')
            self.connection.settimeout(10)
            return json.loads(self.rfile.read(length))

        def do_GET(self):
            if self.path.startswith('/v1/directives/') and self.authorized():
                project = self.directive_project('/v1/directives/')
                if project is None:
                    return self.reply(404, {'error': 'not found'})
                return self.reply(200, replica.directives(project))
            if self.path.startswith('/directives/') and sso_enabled:
                if not self.proxy_authorized():
                    return self.reply(401, {'error': 'SSO authentication required'})
                if self.path.rstrip('/') == '/directives':
                    return self.reply(200, directives.index(replica.directive_counts()), 'text/html')
                project = self.directive_project('/directives/')
                if project is None:
                    return self.reply(404, {'error': 'not found'})
                return self.reply(200, directives.page(project, replica.directives(project)), 'text/html')
            if self.path == '/health':
                self.reply(200, {'status': 'ok'})
            elif self.path == '/v1/status' and self.authorized():
                self.reply(200, {'plans': [e['receipt'] for e in replica.entries(shared=True)]})
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
            for prefix, allowed in (('/v1/directives/', self.authorized()),
                                    ('/directives/', sso_enabled and self.proxy_authorized()
                                     and self.headers.get('X-LHC-Directives') == '1')):
                if self.path.startswith(prefix):
                    project = self.directive_project(prefix)
                    if project is None:
                        return self.reply(404, {'error': 'not found'})
                    if not allowed:
                        return self.reply(401, {'error': 'authentication required'})
                    try:
                        request = self.read_body()
                        if not isinstance(request, dict):
                            raise ValueError('request must be an object')
                        return self.reply(200, replica.directives(project, request))
                    except (ValueError, KeyError, TypeError, OSError):
                        return self.reply(400, {'error': 'invalid directive request'})
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

    class Server(ThreadingHTTPServer):
        price_refresh = None
        price_completed = 0

        def service_actions(self):
            if self.price_refresh is None:
                return
            self.price_refresh.kick()
            if self.price_refresh.completed != self.price_completed:
                try:
                    replica.refresh_prices()
                except Exception:
                    print('LHC: обновление цен на страницах повторится при следующей проверке', file=sys.stderr)
                self.price_completed = self.price_refresh.completed

    server = Server((cfg.get('listen', '127.0.0.1'), int(cfg.get('port', 8769))), Handler)
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('serve', 'watch', 'once', 'register', 'link', 'status'):
        cmd = commands.add_parser(name)
        if name in ('register', 'link'):
            cmd.add_argument('plan_dir', type=Path)
        cmd.add_argument('--config', type=Path, default=CONFIG)
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            server = make_server(config(args.config))
            server.price_refresh = CatalogRefresh()
            server.serve_forever()
        elif args.command in {'watch', 'once'}:
            if args.command == 'once':
                try:
                    refresh_catalog()
                except Exception:
                    pass  # Existing cached prices/unknown status stay honest.
            run_observer(args.config, once=args.command == 'once',
                         price_refresh=None if args.command == 'once' else CatalogRefresh())
        elif args.command == 'link':
            print(link(args.plan_dir, args.config))
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
