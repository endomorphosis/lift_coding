"""Offline launcher checks; never execute a benchmark or call a provider."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prepared_launcher', Path(__file__).with_name('run-prepared-trials.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def healthy():
    return {'mem_available_bytes': 24 * launcher.GIB, 'disk_free_bytes': 20 * launcher.GIB,
            'load_1m': 8.5, 'affinity_cpus': 10}


def native(*, started=True, reward=0):
    return {'agent_execution': {'started_at': '2026-10-11T00:00:00Z'} if started else None,
            'finished_at': '2026-10-11T00:01:00Z',
            'verifier_result': {'rewards': {'reward': reward}}}


def complete_receipt():
    return {'schema': 'terminal-full-supervisor-receipt@1', 'complete_single_trial_receipt': True,
            'trial_count': 1, 'native_job_result_present': True, 'trials': [{'supervisor': {}}]}


class AdmissionTests(unittest.TestCase):
    def test_exact_thresholds_admit_and_each_pressure_source_blocks(self):
        self.assertEqual(launcher.pressure_reasons(healthy()), [])
        for key, value in (('mem_available_bytes', 24 * launcher.GIB - 1),
                           ('disk_free_bytes', 20 * launcher.GIB - 1), ('load_1m', 8.51)):
            with self.subTest(key=key):
                self.assertEqual(len(launcher.pressure_reasons({**healthy(), key: value})), 1)

    def test_backoff_waits_for_recovery_and_caps_every_sleep(self):
        samples = iter([{**healthy(), 'mem_available_bytes': 0}] * 5 + [healthy()])
        clock, sleeps = [0.0], []
        def sleep(value):
            sleeps.append(value)
            clock[0] += value
        stream = io.StringIO()
        result = launcher.await_resources(stream, 300, sample_fn=lambda: next(samples),
                                          sleeper=sleep, monotonic=lambda: clock[0])
        self.assertEqual(result, healthy())
        self.assertEqual(sleeps, [5.0, 10.0, 20.0, 30.0, 30.0])
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        decisions = [r['admitted'] for r in records if r['event'] == 'resource_admission']
        self.assertEqual(decisions, [False] * 5 + [True])

    def test_exhausted_admission_does_not_sleep_or_launch(self):
        with self.assertRaises(TimeoutError):
            launcher.await_resources(io.StringIO(), 0,
                                     sample_fn=lambda: {**healthy(), 'disk_free_bytes': 0},
                                     sleeper=lambda _: self.fail('unexpected sleep'), monotonic=lambda: 0)


class ReceiptTests(unittest.TestCase):
    def test_setup_error_stops_even_when_setup_timing_finished(self):
        evidence = native(started=False)
        evidence['agent_setup'] = {'started_at': 'a', 'finished_at': 'b'}
        evidence['exception_info'] = {'exception_type': 'RuntimeError'}
        self.assertEqual(launcher.classify_receipt(complete_receipt(), evidence), ('setup_failed', False))

    def test_completed_failed_task_continues_without_relabeling_success(self):
        self.assertEqual(launcher.classify_receipt(complete_receipt(), native(reward=0)), ('task_failed', True))
        self.assertEqual(launcher.classify_receipt(complete_receipt(), native(reward=1)), ('task_passed', True))

    def test_predispatch_pipeline_error_stops_despite_complete_reward_zero_receipt(self):
        receipt = complete_receipt()
        receipt['trials'][0]['supervisor'] = {
            'error': {'type': 'ValueError', 'message': 'worker context exceeds configured budget'},
            'error_phase': 'initial_context', 'provider_invocations': [], 'task_completed': False,
            'error_traceback': ['private context must never be copied'],
        }
        self.assertEqual(launcher.classify_receipt(receipt, native(reward=0)), ('supervisor_predispatch_failed', False))
        observation = launcher.supervisor_error_observation(receipt['trials'][0]['supervisor'])
        self.assertEqual(observation['provider_invocation_count'], 0)
        self.assertEqual(observation['error_category'], 'worker_context_budget_exceeded')
        self.assertNotIn('private context', json.dumps(observation))

    def test_missing_dispatch_receipt_does_not_claim_zero_calls(self):
        receipt = complete_receipt()
        report = {'error': {'type': 'RuntimeError'}, 'provider_invocations': [], 'coding_dispatch_possible': True}
        receipt['trials'][0]['supervisor'] = report
        self.assertEqual(launcher.classify_receipt(receipt, native()), ('supervisor_dispatch_unknown', False))
        report['unreceipted_provider_attempt'] = {'phase': 'coding'}
        self.assertEqual(launcher.classify_receipt(receipt, native()), ('incomplete_provider_dispatch_receipt', False))

    def test_receipted_model_failure_retains_failed_task_classification(self):
        receipt = complete_receipt()
        receipt['trials'][0]['supervisor'] = {
            'error': {'type': 'TimeoutError'}, 'error_phase': 'implementation',
            'provider_invocations': [{'phase': 'coding', 'invocation_id': 'fixture'}],
        }
        self.assertEqual(launcher.classify_receipt(receipt, native()), ('task_failed', True))

    def test_incomplete_receipts_stop(self):
        for changed in ({'complete_single_trial_receipt': False}, {'native_job_result_present': False},
                        {'trial_count': 2}, {'trials': [{'supervisor': None}]}):
            with self.subTest(changed=changed):
                self.assertFalse(launcher.classify_receipt({**complete_receipt(), **changed}, native())[1])
        incomplete = native()
        incomplete['verifier_result'] = None
        self.assertEqual(launcher.classify_receipt(complete_receipt(), incomplete), ('incomplete_verifier_receipt', False))

    def test_failed_task_usage_is_retained_including_cache_subset(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            output, job = root / 'trial', root / 'trial/jobs/job'
            (job / 'native').mkdir(parents=True)
            context = native(reward=0)
            context['agent_result'] = {'n_input_tokens': 100, 'n_cache_tokens': 60,
                                      'n_output_tokens': 20, 'cost_usd': None,
                                      'metadata': {'usage': {'all_invocations_receipted': True}}}
            (job / 'native/result.json').write_text(json.dumps(context))
            (output / 'receipt.json').write_text(json.dumps(complete_receipt()))
            result = launcher.collect_outcome({'name': 'fixture', 'job': job, 'output': output}, 0)
            self.assertEqual(result['classification'], 'task_failed')
            self.assertEqual(result['usage'], {'n_input_tokens': 100, 'n_cache_tokens': 60,
                                              'n_output_tokens': 20, 'cost_usd': None})
            self.assertTrue(result['supervisor_usage']['all_invocations_receipted'])


class OneShotTests(unittest.TestCase):
    def test_campaign_protocol_requires_complete_pins_and_supported_cli(self):
        pins = {'schema': 'terminal-indexed-context-launcher-protocol@1',
                'source_head': 'a' * 40, 'datasets_head': 'b' * 40, 'kit_head': 'c' * 40,
                'archive_sha256': 'd' * 64, 'native_cli_version': '0.160.0'}
        self.assertEqual(launcher.validate_campaign_pins(pins), pins)
        for change in ({'source_head': 'short'}, {'archive_sha256': None}, {'native_cli_version': 'latest'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                launcher.validate_campaign_pins({**pins, **change})

    def test_invocation_marker_refuses_reexecution(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            output = root / 'trials/fixture'
            output.mkdir(parents=True)
            config = {'environment': {'force_build': True, 'override_cpus': 5, 'override_memory_mb': 16384,
                                     'cpu_enforcement_policy': 'limit', 'memory_enforcement_policy': 'limit'},
                      'n_attempts': 1, 'n_concurrent_trials': 1, 'retry': {'max_retries': 0},
                      'jobs_dir': str(output / 'jobs'), 'job_name': 'job'}
            (output / 'config.json').write_text(json.dumps(config))
            (output / 'preparation.json').write_text(json.dumps({
                'prepared': True, 'config_sha256': launcher.digest(output / 'config.json'),
                'archive_sha256': 'd' * 64, 'cli_version': '0.160.0'}))
            with patch.object(launcher, 'TRIALS', root / 'trials'), patch.object(launcher, 'STATE', root / 'state'), patch.object(launcher, 'ARCHIVE_SHA256', 'd' * 64):
                self.assertEqual(launcher.validate_trial('fixture')['name'], 'fixture')
                (output / 'invocation.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'one-shot'):
                    launcher.validate_trial('fixture')


if __name__ == '__main__':
    unittest.main()
