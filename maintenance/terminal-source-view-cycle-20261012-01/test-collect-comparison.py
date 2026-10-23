"""Authored temporary artifacts qualify the content-free comparison collector."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

SPEC = importlib.util.spec_from_file_location('source_view_comparison', Path(__file__).with_name('collect-comparison.py'))
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.names = ['raw-one', 'compact-one', 'raw-two', 'compact-two']
        self.protocol = {'schema': 'terminal-source-view-comparison-protocol@1',
            'source_commit': 'a' * 40, 'archive_sha256': 'b' * 64, 'trials': [
                {'name': name, 'task': 'authored-task-' + str(i // 2),
                    'source_view_policy': COLLECTOR.MODES[i % 2]} for i, name in enumerate(self.names)]}
        self.write('comparison-protocol.json', self.protocol)

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def complete(self, name, *, reward=1, adopted=False, tokens=110):
        arm = self.protocol['trials'][self.names.index(name)]['source_view_policy']
        helper = {'schema': 'code-source-view-usage@1', 'status': 'observed' if adopted else 'not_observed',
            'operations': 2 if adopted else 0, 'operation_counts': {'index': 1, 'read': 1} if adopted else {},
            'format_counts': {'compact' if 'compact' in arm else 'raw': 1} if adopted else {},
            'response_bytes': 512 if adopted else 0, 'changed_edits': 0, 'no_op_edits': 0}
        receipt = {'schema': 'terminal-full-supervisor-receipt@1', 'complete_single_trial_receipt': True,
            'trials': [{'source_view_dispatch': {'schema': 'terminal-source-view-dispatch-observation@1',
                'requested_policy': arm, 'effective_advisory_observed': True},
                'supervisor': {'provider_invocations': [{'invocation_id': name, 'phase': 'coding',
                    'source_view_policy': {'usage': helper}, 'raw_model_response': 'DO_NOT_EXPORT_MODEL_CONTENT'}]}}]}
        digest = self.write(f'trials/{name}/receipt.json', receipt)
        self.write(f'trials/{name}/invocation.json', {'authored': True})
        self.write(f'launcher-state/{name}/process.json', {'pid': 1234})
        outcome = {'trial': name, 'classification': 'task_passed' if reward else 'task_failed', 'receipt_sha256': digest,
            'usage': {'n_input_tokens': tokens - 10, 'n_cache_tokens': 60, 'n_output_tokens': 10},
            'supervisor_usage': {'usage_accounting_complete': True, 'token_count_scope': 'native_session_cumulative',
                'cache_included_in_input': True, 'input_tokens': tokens - 10, 'cached_input_tokens': 60,
                'output_tokens': 10, 'total_tokens': tokens}, 'official_rewards': {'reward': reward},
            'raw_transcript': 'DO_NOT_EXPORT_MODEL_CONTENT'}
        self.write(f'launcher-state/{name}/outcome.json', outcome)
        return receipt, outcome

    def test_requested_population_retains_unstarted_and_unknown(self):
        self.complete('raw-one', adopted=False)
        result = COLLECTOR.collect(self.root)
        self.assertEqual(len(result['trials']), 4)
        self.assertEqual(result['trials'][1]['state'], 'unstarted')
        self.assertIsNone(result['trials'][1]['native_usage']['complete_total_tokens'])
        raw = result['arms'][0]
        self.assertEqual(raw['known_native_token_subtotal'], 110)
        self.assertIsNone(raw['all_requested_native_tokens'])
        self.assertIsNone(raw['tokens_per_successfully_solved_task'])
        self.assertEqual(raw['helper_nonadoption_observed_trials'], 1)
        self.assertNotIn('DO_NOT_EXPORT', json.dumps(result))

    def test_failed_task_tokens_retained_and_cache_not_double_counted(self):
        self.complete('raw-one', reward=1)
        self.complete('raw-two', reward=0, tokens=210)
        result = COLLECTOR.collect(self.root)['arms'][0]
        self.assertEqual(result['all_requested_native_tokens'], 320)
        self.assertEqual(result['tokens_per_successfully_solved_task'], 320)
        self.assertEqual(result['official_failures_observed'], 1)

    def test_observed_adoption_and_guidance_are_separate(self):
        self.complete('compact-one', adopted=True)
        row = COLLECTOR.collect(self.root)['trials'][1]
        self.assertTrue(row['effective_guidance_observed'])
        self.assertEqual(row['source_helper']['operations'], 2)
        self.assertEqual(row['source_helper']['format_counts'], {'compact': 1})

    def test_invalid_token_arithmetic_stays_unknown(self):
        _, outcome = self.complete('raw-one')
        for key, bad in [('total_tokens', 111), ('cached_input_tokens', 101), ('input_tokens', True),
                         ('token_count_scope', 'unknown'), ('cache_included_in_input', False)]:
            invalid = copy.deepcopy(outcome)
            invalid['supervisor_usage'][key] = bad
            self.write('launcher-state/raw-one/outcome.json', invalid)
            usage = COLLECTOR.collect(self.root)['trials'][0]['native_usage']
            self.assertFalse(usage['complete'], key)
            self.assertIsNone(usage['complete_total_tokens'], key)

    def test_reward_bool_nan_or_unrelated_key_cannot_claim_success(self):
        _, outcome = self.complete('raw-one')
        for rewards in ({'reward': True}, {'reward': float('nan')}, {'unrelated': 1}):
            outcome['official_rewards'] = rewards
            self.write('launcher-state/raw-one/outcome.json', outcome)
            self.assertIsNone(COLLECTOR.collect(self.root)['trials'][0]['official_success'])

    def test_receipt_digest_mismatch_invalidates_usage_and_reward(self):
        _, outcome = self.complete('raw-one')
        outcome['receipt_sha256'] = '0' * 64
        self.write('launcher-state/raw-one/outcome.json', outcome)
        row = COLLECTOR.collect(self.root)['trials'][0]
        self.assertFalse(row['outcome_receipt_binding_verified'])
        self.assertIsNone(row['native_usage']['complete_total_tokens'])
        self.assertIsNone(row['official_success'])

    def test_stops_retained_despite_incomplete_receipt(self):
        receipt, outcome = self.complete('raw-one')
        receipt['complete_single_trial_receipt'] = False
        receipt['trials'][0]['provider_stop'] = {'schema': 'terminal-provider-stop@1', 'state': 'rate_limited',
            'reason_code': 'rate_limit', 'provider': 'codex_cli', 'retry_after_seconds': 60, 'observation_valid': True}
        outcome['receipt_sha256'] = self.write('trials/raw-one/receipt.json', receipt)
        outcome['supervisor_usage']['usage_accounting_complete'] = False
        outcome['official_rewards'] = None
        self.write('launcher-state/raw-one/outcome.json', outcome)
        row = COLLECTOR.collect(self.root)['trials'][0]
        self.assertEqual(row['provider_stop']['reason_code'], 'rate_limit')
        self.assertIsNone(row['native_usage']['complete_total_tokens'])

    def test_deferral_is_not_attempt_or_zero_token_usage(self):
        self.write('launcher-state/raw-one/outcome.json', {'trial': 'raw-one', 'classification': 'provider_deferred',
            'provider_deferral': {'reason': 'cooldown'}})
        row = COLLECTOR.collect(self.root)['trials'][0]
        self.assertEqual(row['state'], 'provider_deferred')
        self.assertEqual(row['provider_deferral_reason'], 'cooldown')
        self.assertFalse(row['attempted'])
        self.assertIsNone(row['native_usage']['complete_total_tokens'])

    def test_bad_helper_counter_population_is_unknown(self):
        receipt, _ = self.complete('compact-one', adopted=True)
        receipt['trials'][0]['supervisor']['provider_invocations'][0]['source_view_policy']['usage']['operations'] = 99
        self.write('trials/compact-one/receipt.json', receipt)
        helper = COLLECTOR.collect(self.root)['trials'][1]['source_helper']
        self.assertEqual(helper['status'], 'unknown')
        self.assertIsNone(helper['operations'])

    def test_symlink_receipt_not_followed(self):
        self.complete('raw-one')
        path = self.root / 'trials/raw-one/receipt.json'
        path.unlink()
        path.symlink_to('/unavailable/private-transcript')
        row = COLLECTOR.collect(self.root)['trials'][0]
        self.assertFalse(row['native_usage']['complete'])

    def test_duplicate_requested_trial_rejected(self):
        self.protocol['trials'].append(self.protocol['trials'][0])
        self.write('comparison-protocol.json', self.protocol)
        with self.assertRaises(ValueError):
            COLLECTOR.collect(self.root)

    def test_default_stdout_and_output_exclusive_create(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(COLLECTOR.main(['--root', str(self.root)]), 0)
        self.assertEqual(json.loads(stream.getvalue())['schema'], COLLECTOR.SCHEMA)
        output = self.root / 'new-comparison.json'
        COLLECTOR.main(['--root', str(self.root), '--output', str(output)])
        with self.assertRaises(FileExistsError):
            COLLECTOR.main(['--root', str(self.root), '--output', str(output)])


if __name__ == '__main__':
    unittest.main()
