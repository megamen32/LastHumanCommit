"""Regressions for honest unknown estimates in the offline graph validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'scripts' / 'lhc_validate_graph.py'
SPEC = importlib.util.spec_from_file_location('lhc_validate_graph', SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def graph_with_unknown(reason: str | None):
    unknown = {
        'id': 'external', 'label': 'External wait', 'role': 'Owner',
        'status': 'blocked', 'depends_on': ['bounded'], 'read_paths': [],
        'write_paths': [], 'acceptance': 'Access is verified.',
    }
    if reason is not None:
        unknown['estimate_unknown_reason'] = reason
    return {
        'schema_version': 2,
        'tasks': [
            {'id': 'bounded', 'label': 'Bounded work', 'role': 'Worker',
             'status': 'queued', 'depends_on': [], 'read_paths': [], 'write_paths': [],
             'acceptance': 'The bounded result is verified.',
             'estimate_minutes': {'minimum': 5, 'maximum': 10,
                                  'uncertainty': 'One small repair may be needed.',
                                  'basis': 'A focused source and test change.'}},
            unknown,
        ],
    }


class UnknownEstimateTests(unittest.TestCase):
    def test_explicit_unknown_is_valid_but_suppresses_total_forecast(self):
        result = validator.validate_graph(graph_with_unknown('Waiting for owner access.'))
        self.assertTrue(result['valid'], result['errors'])
        self.assertFalse(result['estimate']['available'])
        self.assertEqual(result['estimate']['unknown_task_ids'], ['external'])

    def test_missing_estimate_without_reason_is_invalid(self):
        result = validator.validate_graph(graph_with_unknown(None))
        self.assertFalse(result['valid'])
        self.assertIn('external: missing estimate_minutes requires a nonempty estimate_unknown_reason',
                      result['errors'])

    def test_unassigned_model_class_is_not_filled_or_required(self):
        result = validator.validate_graph(graph_with_unknown('Waiting for owner access.'))
        self.assertNotIn('model_class', graph_with_unknown('Waiting for owner access.')['tasks'][0])
        self.assertTrue(result['valid'], result['errors'])

    def test_numeric_and_unknown_estimate_cannot_conflict(self):
        graph = graph_with_unknown('Waiting for owner access.')
        graph['tasks'][1]['estimate_minutes'] = {'minimum': 5, 'maximum': 5, 'basis': 'fixture'}
        result = validator.validate_graph(graph)
        self.assertIn('external: provide either estimate_minutes or estimate_unknown_reason, not both',
                      result['errors'])


if __name__ == '__main__':
    unittest.main()
