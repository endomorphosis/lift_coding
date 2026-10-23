"""Export and plan-only regressions use authored receipts and no benchmark calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import aggregate_trials as agg
from export_benchmark import export_report
from test_aggregate_trials import fixture, model_report, selected

spec = importlib.util.spec_from_file_location('prepare_campaign', Path(__file__).with_name('prepare-campaign.py'))
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


class CampaignToolTests(unittest.TestCase):
    def test_skeleton_is_unfrozen_abba_with_same_context(self):
        value = preparation.protocol_skeleton()
        agg.validate_protocol(value)
        self.assertNotIn('source_commit', value)
        self.assertNotIn('archive_sha256', value)
        self.assertEqual(value['preparations'], {})
        self.assertEqual([row['semantic_metadata_view'] for row in value['trials']],
            ['legacy', 'common-bindings@1', 'common-bindings@1', 'legacy'])
        self.assertEqual([row['repeat'] for row in value['trials']], [1, 1, 2, 2])
        self.assertEqual(len({row['name'] for row in value['trials']}), 4)
        self.assertTrue(all(row['semantic_context_profile'] == agg.CONTEXT_PROFILE for row in value['trials']))

    def test_export_preserves_all_repeats_and_compares_arm_totals(self):
        selections = preparation.planned_trials()
        reports = [(model_report(row['name'], row['semantic_metadata_view']), 1) for row in selections]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, selections, reports)
            value = export_report(agg.aggregate(root))
            self.assertEqual(len(value['trials']), 4)
            self.assertEqual(len({row['trial'] for row in value['trials']}), 4)
            self.assertEqual(value['observed_requested_arm_comparison']['complete_tokens_all_attempts']['legacy'], 220)
            self.assertEqual(value['observed_requested_arm_comparison']['complete_tokens_all_attempts']['requested_common_bindings'], 220)
            self.assertEqual(value['observed_requested_arm_comparison']['complete_tokens_all_attempts']['candidate_change_percent'], 0)
            baseline = [row for row in value['trials'] if row['requested_metadata_view'] == 'legacy']
            self.assertTrue(all(row['effective_treatment_observed'] is False for row in baseline))
            self.assertTrue(all(row['effective_treatment_comparison_eligible'] for row in baseline))
            self.assertEqual(value['arms']['legacy']['fallback_trials'], 0)

    def test_export_does_not_promote_valid_fallback_to_effective_treatment(self):
        selections = [selected(), selected('factored-01', 'common-bindings@1')]
        reports = [(model_report('base'), 1), (model_report('fall', 'common-bindings@1', 'legacy'), 1)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, selections, reports)
            metric = export_report(agg.aggregate(root))['observed_requested_arm_comparison']['complete_tokens_all_attempts']
            self.assertTrue(metric['requested_arm_comparison_eligible'])
            self.assertFalse(metric['effective_treatment_comparison_eligible'])
            self.assertEqual(metric['candidate_change_percent'], 0)

    def test_export_pending_is_null_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, preparation.planned_trials())
            value = export_report(agg.aggregate(root))
            self.assertTrue(all(row['total_tokens'] is None for row in value['trials']))
            self.assertTrue(all(metric['candidate_change_percent'] is None for metric in value['observed_requested_arm_comparison'].values()))

    def test_unequal_repeat_populations_do_not_produce_qualified_deltas(self):
        selections = [selected(), selected('factored-01', 'common-bindings@1'),
            selected('factored-02', 'common-bindings@1', 2)]
        reports = [(model_report(row['name'], row['semantic_metadata_view']), 1) for row in selections]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, selections, reports)
            result = agg.aggregate(root)
            self.assertFalse(result['requested_arm_populations_match'])
            value = export_report(result)
            comparison = value['observed_requested_arm_comparison']['complete_tokens_all_attempts']
            self.assertEqual(comparison['legacy'], 110)
            self.assertEqual(comparison['requested_common_bindings'], 220)
            self.assertFalse(comparison['requested_arm_comparison_eligible'])
            self.assertFalse(comparison['effective_treatment_comparison_eligible'])
            self.assertIsNone(comparison['candidate_change_percent'])

    def test_missing_retained_task_integrity_is_unknown_and_disqualifies_comparison(self):
        item = selected()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root, [item], [(model_report('base'), 1)])
            path = root / 'trials' / item['name'] / 'receipt.json'
            receipt = json.loads(path.read_text())
            receipt.pop('original_task_inputs_unchanged')
            path.write_text(json.dumps(receipt))
            row = agg.aggregate(root)['trials'][0]
            self.assertIsNone(row['frozen_controls']['original_task_inputs_unchanged_receipt'])
            self.assertFalse(row['requested_arm_comparison_eligible'])
            self.assertIn('original_task_input_integrity_not_verified', row['comparison_exclusions'])
            self.assertEqual(row['complete_tokens']['total_tokens'], 110)

    def test_cumulative_session_identity_required_and_malformed_is_not_a_crash(self):
        for identity in (None, True, ['bad'], {}, '', 'x' * 4097):
            report = model_report('one')
            report['provider_invocations'][0]['native_rollout_usage']['thread_id'] = identity
            value = agg.usage(report)
            self.assertFalse(value['complete'])
            self.assertIn('native_session_identity_unavailable_or_invalid', value['problems'])
            self.assertIsNone(value['complete_tokens']['total_tokens'])
            self.assertIsNone(value['known_token_subtotal']['total_tokens'])
            self.assertEqual(value['observed_tokens']['total_tokens'], 110)
            self.assertIsNone(value['calls'][0]['native_session_sha256'])

    def test_legacy_missing_matchjoin_does_not_qualify(self):
        report = model_report('baseline')
        report['context_input_audit']['matches'] = []
        observation = agg.metadata_observation(report, 'legacy')
        self.assertFalse(observation['all_coding_inputs_verified_by_retained_audit'])
        self.assertIsNone(observation['effective_treatment_observed'])

if __name__ == '__main__': unittest.main(verbosity=2)
