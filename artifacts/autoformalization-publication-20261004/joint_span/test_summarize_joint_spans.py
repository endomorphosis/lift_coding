"""Regression fixtures for provider metadata and closed evidence bindings.

Only the summary module's standard-library helpers execute. No evidence files,
models, checkpoints, targets, numerical providers, network or provers are read.
"""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'joint_span_summary_fixture', Path(__file__).with_name('summarize_joint_spans.py'))
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


class ProviderBindingFixtures(unittest.TestCase):
    def setUp(self):
        self.reference = {'path': '/fixture/provider.py', 'bytes': 10,
                          'sha256': '0' * 64, 'version': 'fixture-1.0'}

    def test_version_metadata_is_removed_from_binding_without_mutation(self):
        before = copy.deepcopy(self.reference)
        result = summary.provider_binding(self.reference)
        self.assertEqual(result, {key: before[key] for key in ('path', 'bytes', 'sha256')})
        self.assertEqual(set(result), {'path', 'bytes', 'sha256'})
        self.assertEqual(self.reference, before)
        result['path'] = '/fixture/changed.py'
        self.assertEqual(self.reference['path'], before['path'])

    def test_unknown_provider_metadata_is_rejected(self):
        changed = {**self.reference, 'unbound_source': '/fixture/other.py'}
        with self.assertRaises(ValueError):
            summary.provider_binding(changed)

    def test_boolean_version_metadata_is_rejected(self):
        changed = {**self.reference, 'version': False}
        with self.assertRaises(ValueError):
            summary.provider_binding(changed)

    def test_missing_version_metadata_is_rejected(self):
        changed = {key: value for key, value in self.reference.items() if key != 'version'}
        with self.assertRaises(ValueError):
            summary.provider_binding(changed)


if __name__ == '__main__':
    unittest.main()
