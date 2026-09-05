#!/usr/bin/env python3
"""Offline checks for a declared LHC task graph; NOT a scheduler or LLM evaluator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

DEFAULT_CLASSES = ('frontier', 'fable', 'sonnet', 'haiku')


def path_parts(value: Any) -> tuple[str, ...]:
    """Use portable repository-relative, literal paths; '.' means the entire tree."""
    if not isinstance(value, str) or not value or value.startswith('/') or '\\' in value:
        raise ValueError(f'invalid repository-relative path: {value!r}')
    if value == '.':
        return ()
    parts = value.rstrip('/').split('/')
    if any(p in ('', '.', '..') for p in parts) or any(c in value for c in ('*', '?', '\x00', ':')):
        raise ValueError(f'expected a literal normalized path, not a glob: {value!r}')
    return tuple(parts)


def overlaps(left: str, right: str) -> bool:
    a, b = path_parts(left), path_parts(right)
    return a[:len(b)] == b or b[:len(a)] == a


def validate_graph(document: Any, model_classes: tuple[str, ...] = DEFAULT_CLASSES) -> dict[str, Any]:
    """Return structural errors and dependency layers for declared live-path access.

    Path reads refer to mutable live inputs. Immutable snapshot reads need not be
    declared as live reads. Resource/account/semantic conflicts require Lead review.
    """
    errors: list[str] = []
    if not model_classes or len(set(model_classes)) != len(model_classes):
        return {'valid': False, 'errors': ['model_classes must be nonempty and unique']}
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        return {'valid': False, 'errors': ['expected an object with integer schema_version: 1']}
    tasks = document.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        return {'valid': False, 'errors': ['tasks must be a nonempty list']}
    by_id: dict[str, dict[str, Any]] = {}
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f'tasks[{i}] must be an object')
            continue
        tid = task.get('id')
        if not isinstance(tid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', tid):
            errors.append(f'tasks[{i}] needs a simple nonempty id')
            continue
        if tid in by_id:
            errors.append(f'duplicate task id: {tid}')
            continue
        by_id[tid] = task
        for key in ('role', 'acceptance'):
            if not isinstance(task.get(key), str) or not task[key].strip():
                errors.append(f'{tid}: missing {key}')
        if task.get('model_class') not in model_classes:
            errors.append(f'{tid}: unknown model_class {task.get("model_class")!r}')
        for key in ('depends_on', 'read_paths', 'write_paths'):
            vals = task.get(key)
            if not isinstance(vals, list) or not all(isinstance(v, str) for v in vals):
                errors.append(f'{tid}: {key} must be a list of strings')
                continue
            if len(vals) != len(set(vals)):
                errors.append(f'{tid}: duplicate value in {key}')
            if key.endswith('_paths'):
                for val in vals:
                    try:
                        path_parts(val)
                    except ValueError as exc:
                        errors.append(f'{tid}: {exc}')
    if errors:
        return {'valid': False, 'errors': errors}
    for tid, task in by_id.items():
        for dep in task['depends_on']:
            if dep not in by_id:
                errors.append(f'{tid}: missing dependency {dep}')
            elif dep == tid:
                errors.append(f'{tid}: self dependency')
    if errors:
        return {'valid': False, 'errors': errors}

    remaining = set(by_id)
    complete: set[str] = set()
    layers: list[list[str]] = []
    ancestors: dict[str, set[str]] = {}
    while remaining:
        ready = sorted(t for t in remaining if set(by_id[t]['depends_on']) <= complete)
        if not ready:
            return {'valid': False, 'errors': ['dependency cycle involving: ' + ', '.join(sorted(remaining))]}
        for tid in ready:
            ancestors[tid] = set(by_id[tid]['depends_on'])
            for dep in by_id[tid]['depends_on']:
                ancestors[tid].update(ancestors[dep])
        layers.append(ready)
        remaining.difference_update(ready)
        complete.update(ready)

    ids = list(by_id)
    for i, left_id in enumerate(ids):
        for right_id in ids[i+1:]:
            if left_id in ancestors[right_id] or right_id in ancestors[left_id]:
                continue
            left, right = by_id[left_id], by_id[right_id]
            pairs = [(w, p) for w in left['write_paths'] for p in right['write_paths'] + right['read_paths']]
            pairs += [(p, w) for w in right['write_paths'] for p in left['read_paths']]
            collisions = [(a, b) for a, b in pairs if overlaps(a, b)]
            if collisions:
                a, b = collisions[0]
                errors.append(f'concurrent mutable-path conflict: {left_id} ({a}) / {right_id} ({b}); declare a dependency or isolate ownership')
    return {
        'valid': not errors,
        'errors': errors,
        'dependency_layers': layers,
        'limits': 'Declared paths/dependencies only. Layers are not runtime schedules; model/tool/resource/semantic suitability still requires verification.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', type=Path)
    parser.add_argument('--config', type=Path, help='Optional routing JSON with a tier_order list')
    args = parser.parse_args()
    try:
        classes = DEFAULT_CLASSES
        if args.config:
            cfg = json.loads(args.config.read_text(encoding='utf-8'))
            order = cfg.get('tier_order') if isinstance(cfg, dict) else None
            if not isinstance(order, list) or not all(isinstance(t, str) and t for t in order):
                raise ValueError('config tier_order must be a list of nonempty strings')
            classes = tuple(order)
        result = validate_graph(json.loads(args.graph.read_text(encoding='utf-8')), classes)
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 2


if __name__ == '__main__':
    sys.exit(main())
