#!/usr/bin/env python3
"""Offline checks for a declared LHC task graph; NOT a scheduler or LLM evaluator.

The accepted contract is the canonical task graph published in
``src/common/protocols/TASK_GRAPH.md``: ``schema_version: 2`` with ``id``,
``label``, ``status`` and ``depends_on`` required per task. Every other field is
optional and is checked only when it is present, so the published example and a
graph exported by ``lhc_grid.py export`` validate without extra ceremony.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

DEFAULT_CLASSES = ('glm-5.3-flash', 'minimax-3.1-flash', 'gpt-6-luna', 'glm-5.3', 'gpt-6.1-sol')
SCHEMA_VERSIONS = (1, 2)
LIVE_STATUSES = ('done', 'running', 'blocked', 'waiting', 'queued')
REQUIRED_TASK_FIELDS = {1: ('id',), 2: ('id', 'label', 'status', 'depends_on')}
CLOCK_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
BLOCKER_DETAIL_KEYS = ('reason', 'responsible', 'next_action', 'human_required', 'human_action')
HUMAN_REQUIRED_VALUES = ('yes', 'no', 'unknown')


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


def finite_minutes(value: Any) -> bool:
    return type(value) is int and value >= 0 or (
        type(value) is float and math.isfinite(value) and value >= 0
    )


def estimate_bounds(task: dict[str, Any]) -> tuple[Any, Any]:
    """Return the declared estimate bounds of a task as (minimum, maximum)."""
    estimate = task.get('estimate_minutes')
    if not isinstance(estimate, dict):
        return None, None
    return estimate.get('minimum'), estimate.get('maximum')


def estimate_summary(by_id: dict[str, dict[str, Any]], layers: list[list[str]]) -> dict[str, Any]:
    """Aggregate the estimates that are actually declared.

    Only leaves that carry an estimate take part: a graph may estimate some leaves
    and not others, and an unestimated leaf must not become a false error or a
    silent zero inside the total.

    A leaf that declares ``estimate_unknown_reason`` says out loud that its
    effort cannot be bounded. Then no total is inferred at all: the unknown leaf
    ids are reported instead of a number that would be a fiction.
    """
    unknown = sorted(tid for tid, task in by_id.items() if task.get('estimate_unknown_reason'))
    if unknown:
        return {
            'available': False,
            'reason': 'No total or finish time is inferred while estimates are unknown.',
            'unknown_task_ids': unknown,
        }
    estimated = {tid: task for tid, task in by_id.items()
                 if any(bound is not None for bound in estimate_bounds(task))}
    if not estimated:
        return {'available': False, 'reason': 'No per-node estimates supplied; no total is inferred.'}

    def bound_value(task: dict[str, Any], bound: str) -> Any:
        low, high = estimate_bounds(task)
        if bound == 'minimum':
            return low if low is not None else high
        return high if high is not None else low

    effort: dict[str, int | float] = {}
    duration: dict[str, int | float] = {}
    paths: dict[str, list[str]] = {}
    for bound in ('minimum', 'maximum'):
        effort[bound] = sum(bound_value(task, bound) for task in estimated.values())
        totals: dict[str, int | float] = {}
        routes: dict[str, list[str]] = {}
        for layer in layers:
            for tid in layer:
                if tid not in estimated:
                    continue
                deps = [dep for dep in by_id[tid].get('depends_on') or [] if dep in estimated]
                prior = max(sorted(deps), key=lambda dep: totals[dep]) if deps else None
                totals[tid] = bound_value(by_id[tid], bound) + (totals[prior] if prior else 0)
                routes[tid] = (routes[prior] if prior else []) + [tid]
        predecessors = {dep for tid in estimated
                        for dep in by_id[tid].get('depends_on') or [] if dep in estimated}
        sinks = sorted(set(estimated) - predecessors)
        last = max(sinks, key=lambda tid: totals[tid]) if sinks else None
        duration[bound], paths[bound] = (totals[last], routes[last]) if last else (0, [])
        if not finite_minutes(effort[bound]) or not finite_minutes(duration[bound]):
            raise ValueError('estimate_minutes aggregate exceeds finite numeric range')
    return {
        'available': True,
        'effort_minutes': effort,
        'dependency_critical_path_minutes': duration,
        'critical_paths': paths,
        'limits': 'Estimated dependency path is a lower bound without capacity, resource or queue costs. '
                  'It assumes ready independent work can run concurrently; actual parallelism must be '
                  'verified in the harness. These are estimates, not elapsed or measured active time. '
                  'Only leaves that declare an estimate take part in the total.',
    }


def estimate_field_errors(tid: str, estimate: Any) -> list[str]:
    """Check a declared estimate object; a missing object is not an error."""
    if not isinstance(estimate, dict):
        return [f'{tid}: estimate_minutes must be an object']
    errors: list[str] = []
    if 'minimum' not in estimate and 'maximum' not in estimate:
        errors.append(f'{tid}: estimate_minutes needs a minimum or a maximum bound')
    for bound in ('minimum', 'maximum'):
        if bound in estimate and not finite_minutes(estimate[bound]):
            errors.append(f'{tid}: estimate_minutes {bound} must be a finite nonnegative number, not a boolean')
    minimum, maximum = estimate.get('minimum'), estimate.get('maximum')
    if finite_minutes(minimum) and finite_minutes(maximum) and maximum < minimum:
        errors.append(f'{tid}: estimate_minutes maximum must be at least minimum')
    for key in ('uncertainty', 'basis'):
        if key in estimate:
            value = estimate[key]
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{tid}: estimate_minutes {key} must explain the estimate')
    return errors


def unknown_reason_errors(tid: str, task: dict[str, Any]) -> list[str]:
    """Check a declared unknown-estimate reason and its relation to a numeric estimate."""
    reason = task.get('estimate_unknown_reason')
    if reason is None:
        return []
    errors: list[str] = []
    if not isinstance(reason, str) or not reason.strip():
        errors.append(f'{tid}: estimate_unknown_reason must explain why the estimate is unknown')
    if 'estimate_minutes' in task:
        errors.append(f'{tid}: provide either estimate_minutes or estimate_unknown_reason, not both')
    return errors


def blocker_details_errors(tid: str, details: Any) -> list[str]:
    """Check a declared blocker_details object; an absent object is not an error."""
    if not isinstance(details, dict):
        return [f'{tid}: blocker_details must be an object']
    errors: list[str] = []
    for key in details:
        if key not in BLOCKER_DETAIL_KEYS:
            errors.append(f'{tid}: unknown blocker_details key {key!r}')
            continue
        value = details[key]
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{tid}: blocker_details {key} must be a nonempty string')
    required = details.get('human_required')
    if required is not None and required.strip().lower() not in HUMAN_REQUIRED_VALUES:
        errors.append(f'{tid}: blocker_details human_required must be one of {", ".join(HUMAN_REQUIRED_VALUES)}')
    return errors


def task_field_errors(tid: str, task: dict[str, Any], model_classes: tuple[str, ...]) -> list[str]:
    """Check the optional fields of one task; an absent field is never an error."""
    errors: list[str] = []
    for key in ('role', 'acceptance'):
        value = task.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f'{tid}: {key} must be a nonempty string')
    if 'model_class' in task and task['model_class'] not in model_classes:
        errors.append(f'{tid}: unknown model_class {task["model_class"]!r}')
    for key in ('owner', 'session', 'harness', 'model', 'blocker', 'note'):
        value = task.get(key)
        if value is not None and not isinstance(value, str):
            errors.append(f'{tid}: {key} must be a string')
    for key in ('depends_on', 'parallel_with', 'read_paths', 'write_paths'):
        if key not in task:
            continue
        vals = task[key]
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
    status = task.get('status')
    if status is not None:
        if not isinstance(status, str) or status.strip().lower() not in LIVE_STATUSES:
            errors.append(f'{tid}: status must be one of {", ".join(LIVE_STATUSES)}')
    for key in ('started_at', 'finished_at'):
        value = task.get(key)
        if value is not None and (not isinstance(value, str) or not CLOCK_RE.match(value.strip())):
            errors.append(f'{tid}: {key} must be a local HH:MM time')
    actual = task.get('actual_minutes')
    if actual is not None and not finite_minutes(actual):
        errors.append(f'{tid}: actual_minutes must be a finite nonnegative number')
    wave = task.get('wave')
    if wave is not None and type(wave) is not int:
        errors.append(f'{tid}: wave must be an integer')
    if 'blocker_details' in task:
        errors.extend(blocker_details_errors(tid, task['blocker_details']))
    errors.extend(unknown_reason_errors(tid, task))
    return errors


def document_field_errors(document: dict[str, Any]) -> list[str]:
    """Check the optional document-level fields; an absent field is never an error."""
    errors: list[str] = []
    for key in ('title', 'goal', 'business_result', 'current_progress', 'external_waits'):
        if key not in document:
            continue
        value = document[key]
        if not isinstance(value, str):
            errors.append(f'{key} must be a string')
        elif value.strip() and key == 'external_waits' and value != value.strip():
            errors.append(f'{key} must be a trimmed string')
    return errors


def validate_graph(document: Any, model_classes: tuple[str, ...] = DEFAULT_CLASSES) -> dict[str, Any]:
    """Return structural errors and dependency layers for declared live-path access.

    The accepted shape is the canonical task graph from ``TASK_GRAPH.md``: for
    ``schema_version: 2`` every task needs ``id``, ``label``, ``status`` and
    ``depends_on``. Everything else is optional and is checked only when it is
    present, so declaring paths, a model class, an acceptance line or an unknown
    estimate is a choice, never a demand.

    Path reads refer to mutable live inputs. Immutable snapshot reads need not be
    declared as live reads. Resource/account/semantic conflicts require Lead review.
    """
    errors: list[str] = []
    if not model_classes or len(set(model_classes)) != len(model_classes):
        return {'valid': False, 'errors': ['model_classes must be nonempty and unique']}
    if (not isinstance(document, dict) or type(document.get('schema_version')) is not int
            or document['schema_version'] not in SCHEMA_VERSIONS):
        return {'valid': False, 'errors': [
            'expected an object with integer schema_version: 1 or 2']}
    version = document['schema_version']
    errors.extend(document_field_errors(document))
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
        for key in REQUIRED_TASK_FIELDS[version]:
            if key not in task:
                errors.append(f'{tid}: missing {key}')
        label = task.get('label')
        if 'label' in task and (not isinstance(label, str) or not label.strip()):
            errors.append(f'{tid}: label must be a nonempty string')
        if 'estimate_minutes' in task:
            errors.extend(estimate_field_errors(tid, task['estimate_minutes']))
        errors.extend(task_field_errors(tid, task, model_classes))
    if errors:
        return {'valid': False, 'errors': errors}
    for tid, task in by_id.items():
        for dep in task.get('depends_on') or []:
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
        ready = sorted(t for t in remaining if set(by_id[t].get('depends_on') or []) <= complete)
        if not ready:
            return {'valid': False, 'errors': ['dependency cycle involving: ' + ', '.join(sorted(remaining))]}
        for tid in ready:
            ancestors[tid] = set(by_id[tid].get('depends_on') or [])
            for dep in by_id[tid].get('depends_on') or []:
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
            left_writes = left.get('write_paths') or []
            left_reads = left.get('read_paths') or []
            right_writes = right.get('write_paths') or []
            right_reads = right.get('read_paths') or []
            pairs = [(w, p) for w in left_writes for p in right_writes + right_reads]
            pairs += [(p, w) for w in right_writes for p in left_reads]
            collisions = [(a, b) for a, b in pairs if overlaps(a, b)]
            if collisions:
                a, b = collisions[0]
                errors.append(f'concurrent mutable-path conflict: {left_id} ({a}) / {right_id} ({b}); declare a dependency or isolate ownership')
    try:
        estimate = estimate_summary(by_id, layers) if not errors else {
            'available': False, 'reason': 'Resolve graph conflicts before using estimates.'}
    except (ValueError, OverflowError) as exc:
        errors.append(str(exc))
        estimate = {'available': False, 'reason': 'Invalid aggregate estimate.'}
    return {
        'valid': not errors,
        'errors': errors,
        'dependency_layers': layers,
        'estimate': estimate,
        'limits': 'Declared paths/dependencies only. Layers are not runtime schedules; model/tool/resource/semantic suitability still requires verification.',
    }


def model_classes_from_config(config: Any) -> tuple[str, ...]:
    """Return the model classes a routing config allows.

    ``model_classes`` is the explicit flat list. Older configs declare
    ``tier_order`` instead; that list names the allowed tiers.
    """
    if not isinstance(config, dict):
        raise ValueError('config must be a JSON object')
    declared = config.get('model_classes')
    if declared is not None:
        if not isinstance(declared, list) or not all(isinstance(t, str) and t for t in declared):
            raise ValueError('config model_classes must be a list of nonempty strings')
        return tuple(declared)
    order = config.get('tier_order')
    if not isinstance(order, list) or not all(isinstance(t, str) and t for t in order):
        raise ValueError('config tier_order must be a list of nonempty strings')
    return tuple(order)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', type=Path)
    parser.add_argument('--config', type=Path,
                        help='Optional routing JSON with a model_classes or tier_order list')
    args = parser.parse_args()
    try:
        classes = DEFAULT_CLASSES
        if args.config:
            classes = model_classes_from_config(
                json.loads(args.config.read_text(encoding='utf-8')))
        result = validate_graph(json.loads(args.graph.read_text(encoding='utf-8')), classes)
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 2


if __name__ == '__main__':
    sys.exit(main())
