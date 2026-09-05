"""Offline structural tests. These do not attest live agents, browser runs or adapters."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lhc_graph', ROOT / 'scripts/lhc_validate_graph.py')
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def task(tid='a', deps=None, writes=None, reads=None, model='sonnet'):
    return {'id': tid, 'role': 'Worker', 'model_class': model, 'depends_on': deps or [],
            'read_paths': reads or [], 'write_paths': writes or [], 'acceptance': 'Observed behavior is verified.'}


def graph(*tasks):
    return {'schema_version': 1, 'tasks': list(tasks)}


def estimated(tid, minimum, maximum, deps=None):
    node = task(tid, deps)
    node['estimate_minutes'] = {
        'minimum': minimum, 'maximum': maximum,
        'basis': 'Implement the named behavior and run its acceptance check.',
        'uncertainty': 'A failed acceptance check may require one repair and replay.',
    }
    return node


class GraphTests(unittest.TestCase):
    def valid(self, document):
        result = mod.validate_graph(document)
        self.assertTrue(result['valid'], result)
        return result

    def invalid(self, document, fragment):
        result = mod.validate_graph(document)
        self.assertFalse(result['valid'])
        self.assertIn(fragment, ' '.join(result['errors']))

    def test_single(self): self.valid(graph(task()))
    def test_legacy_graph_has_no_invented_estimate(self):
        self.assertFalse(self.valid(graph(task()))['estimate']['available'])

    def test_estimated_effort_and_distinct_critical_paths(self):
        result = self.valid(graph(estimated('start', 1, 2),
                                 estimated('a', 7, 8, ['start']),
                                 estimated('b', 3, 12, ['start']),
                                 estimated('join', 2, 3, ['a', 'b'])))['estimate']
        self.assertEqual(result['effort_minutes'], {'minimum': 13, 'maximum': 25})
        self.assertEqual(result['dependency_critical_path_minutes'], {'minimum': 10, 'maximum': 17})
        self.assertEqual(result['critical_paths'],
                         {'minimum': ['start', 'a', 'join'], 'maximum': ['start', 'b', 'join']})
        self.assertIn('lower bound', result['limits'])
        self.assertIn('not elapsed', result['limits'])

    def test_critical_path_does_not_impose_layer_barriers(self):
        result = self.valid(graph(estimated('a', 2, 2), estimated('b', 9, 9),
                                 estimated('c', 8, 8, ['a'])))['estimate']
        self.assertEqual(result['dependency_critical_path_minutes']['minimum'], 10)
        self.assertEqual(result['critical_paths']['minimum'], ['a', 'c'])

    def test_partial_estimates_rejected(self):
        self.invalid(graph(estimated('a', 1, 2), task('b')), 'all nodes')

    def test_invalid_estimate_bounds(self):
        for minimum, maximum in ((True, 2), (1, False), (-1, 2), (3, 2),
                                 ('1', 2), (0, float('inf')), (float('nan'), 3)):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.invalid(graph(estimated('a', minimum, maximum)), 'estimate_minutes')

    def test_explained_estimates_required(self):
        for change in ({'basis': ''}, {'uncertainty': ''}, {'minimum': None}):
            node = estimated('a', 1, 2)
            node['estimate_minutes'].update(change)
            self.invalid(graph(node), 'estimate_minutes')
        node = estimated('a', 0, 0)
        node['estimate_minutes'].pop('uncertainty')
        self.assertEqual(self.valid(graph(node))['estimate']['effort_minutes']['minimum'], 0)

    def test_malformed_estimate_object(self):
        for estimate in (None, [], 2, {}):
            node = task()
            node['estimate_minutes'] = estimate
            self.invalid(graph(node), 'estimate_minutes')

    def test_nonfinite_aggregate_is_not_reported_as_a_valid_total(self):
        self.invalid(graph(estimated('a', 1e308, 1e308),
                           estimated('b', 1e308, 1e308)), 'finite numeric range')
    def test_parallel_disjoint(self):
        self.assertEqual(self.valid(graph(task('a', writes=['src/a']), task('b', writes=['src/b'])))['dependency_layers'], [['a', 'b']])
    def test_shared_read_only(self): self.valid(graph(task('a', reads=['src/common']), task('b', reads=['src/common'])))
    def test_dependency_serializes_conflict(self): self.valid(graph(task('a', writes=['src']), task('b', deps=['a'], writes=['src/a'])))
    def test_transitive_dependency(self): self.valid(graph(task('a', writes=['x']), task('b', deps=['a']), task('c', deps=['b'], writes=['x'])))
    def test_write_write_conflict(self): self.invalid(graph(task('a', writes=['src']), task('b', writes=['src/a'])), 'conflict')
    def test_write_read_conflict(self): self.invalid(graph(task('a', writes=['src']), task('b', reads=['src/a'])), 'conflict')
    def test_read_write_conflict_reverse(self): self.invalid(graph(task('a', reads=['src/a']), task('b', writes=['src'])), 'conflict')
    def test_boundary_not_string_prefix(self): self.valid(graph(task('a', writes=['src/a']), task('b', writes=['src/abc'])))
    def test_root_owns_every_path(self): self.invalid(graph(task('a', writes=['.']), task('b', writes=['src/a'])), 'conflict')
    def test_cycle(self): self.invalid(graph(task('a', ['b']), task('b', ['a'])), 'cycle')
    def test_self_dependency(self): self.invalid(graph(task('a', ['a'])), 'self dependency')
    def test_missing_dependency(self): self.invalid(graph(task('a', ['missing'])), 'missing dependency')
    def test_duplicate_id(self): self.invalid(graph(task(), task()), 'duplicate task id')
    def test_invalid_paths(self):
        for path in ('/tmp/file', '../x', 'a/../b', 'a//b', 'a\\b', 'src/*', 'C:/x', ''):
            with self.subTest(path=path): self.assertFalse(mod.validate_graph(graph(task(writes=[path])))['valid'])
    def test_unknown_class(self): self.invalid(graph(task(model='unknown')), 'model_class')
    def test_configurable_classes(self): self.assertTrue(mod.validate_graph(graph(task(model='custom')), ('custom',))['valid'])
    def test_invalid_class_configuration(self): self.assertFalse(mod.validate_graph(graph(task()), ('sonnet', 'sonnet'))['valid'])
    def test_schema_errors(self):
        for data in (None, [], {}, {'schema_version':True,'tasks':[task()]}, graph(), graph(None)):
            with self.subTest(data=data): self.assertFalse(mod.validate_graph(data)['valid'])
    def test_missing_acceptance(self):
        t = task(); t.pop('acceptance'); self.invalid(graph(t), 'acceptance')
    def test_malformed_list(self):
        t = task(); t['depends_on'] = 'a'; self.invalid(graph(t), 'list of strings')
    def test_duplicate_dependency(self): self.invalid(graph(task('a'), task('b', ['a', 'a'])), 'duplicate value')
    def test_full_example(self):
        sample = ROOT/'src/common/skills/decompose-and-dispatch/references/execution-graph.json'
        result = self.valid(json.loads(sample.read_text()))
        self.assertEqual(result['dependency_layers'][1], ['backend', 'frontend'])
        self.assertEqual(result['estimate']['effort_minutes'], {'minimum': 21, 'maximum': 37})
        self.assertEqual(result['estimate']['dependency_critical_path_minutes'], {'minimum': 16, 'maximum': 28})
    def test_cli_valid_and_invalid(self):
        (ROOT / '.tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as d:
            f = Path(d)/'plan.json'
            for data, code in ((graph(task()),0), (graph(task('a',['b']),task('b',['a'])),2)):
                f.write_text(json.dumps(data))
                p = subprocess.run([sys.executable, str(ROOT/'scripts/lhc_validate_graph.py'), str(f)], capture_output=True, text=True)
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertEqual(json.loads(p.stdout)['valid'], code == 0)
    def test_cli_missing_file(self):
        p = subprocess.run([sys.executable, str(ROOT/'scripts/lhc_validate_graph.py'), '/a/nonexistent/lhc-graph.json'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertFalse(json.loads(p.stdout)['valid'])

    def test_cli_uses_configured_classes_and_rejects_invalid_config(self):
        (ROOT / '.tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as d:
            plan, config = Path(d) / 'plan.json', Path(d) / 'routing.json'
            plan.write_text(json.dumps(graph(task(model='local'))))
            for order, expected in ((['local'], 0), (['sonnet'], 2),
                                    (['local', 'local'], 2), ([], 2), ([7], 2)):
                with self.subTest(order=order):
                    config.write_text(json.dumps({'tier_order': order}))
                    result = subprocess.run(
                        [sys.executable, str(ROOT / 'scripts/lhc_validate_graph.py'),
                         str(plan), '--config', str(config)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertEqual(json.loads(result.stdout)['valid'], expected == 0)

    def test_cli_invalid_json_returns_structured_failure(self):
        (ROOT / '.tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as d:
            plan = Path(d) / 'plan.json'
            plan.write_text('{')
            result = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/lhc_validate_graph.py'), str(plan)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(json.loads(result.stdout)['valid'])


class ArtifactStructureTests(unittest.TestCase):
    def test_skill_metadata(self):
        dirs = sorted((ROOT/'src/common/skills').glob('*/SKILL.md'))
        expected = {'architecture-design', 'model-routing', 'decompose-and-dispatch', 'user-testing',
                    'focus-groups', 'council', 'challenge-decision', 'improve-workflow'}
        self.assertTrue(expected <= {f.parent.name for f in dirs})
        for f in dirs:
            raw = f.read_text()
            self.assertTrue(raw.startswith('---\n'))
            metadata = raw.split('---',2)[1]
            name = re.search(r'^name: (.+)$', metadata, re.M).group(1)
            description = re.search(r'^description: (.+)$', metadata, re.M).group(1)
            self.assertEqual(name, f.parent.name)
            self.assertRegex(name, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
            self.assertLessEqual(len(name),64)
            self.assertTrue(1 <= len(description) <= 1024)
    def test_catalog_links_resolve(self):
        index=ROOT/'src/common/skills/README.md'
        for target in re.findall(r'\]\(([^)]+)\)',index.read_text()):
            self.assertTrue((index.parent/target).is_file(),target)
    def test_model_examples_are_configuration(self):
        cfg=json.loads((ROOT/'src/common/config/model-routing.example.json').read_text())
        self.assertEqual(cfg['tier_order'], ['frontier','fable','sonnet','haiku'])
        self.assertEqual(cfg['tiers']['fable']['user_examples'], ['GPT-6A','Star','GLM 5.3'])
        self.assertEqual(cfg['tiers']['sonnet']['user_examples'], ['5.3 Flash','Panthera'])
        self.assertEqual(cfg['tiers']['haiku']['user_examples'], ['GLM 4.7','MiniMax M3'])
        self.assertIsNone(cfg['selection']['fixed_cheap_token_quota'])
    def test_relative_skill_and_template_links(self):
        for base in (ROOT/'src/common/skills',):
            for f in base.rglob('*.md'):
                for ref in re.findall(r'`((?:\.\./)+[^`]+\.(?:md|json|py))`', f.read_text()):
                    self.assertTrue((f.parent/ref).is_file(),f'{f.relative_to(ROOT)} -> {ref}')


if __name__ == '__main__': unittest.main()
