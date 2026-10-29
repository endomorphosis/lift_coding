"""Actual SDK observations plus strict native-service failure boundaries."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

STAGE = Path(__file__).resolve().parents[1]
LIVE = Path(os.environ.get('SVF_OBSERVATION_TEST_SOURCE_ROOT', STAGE)).resolve()
sys.path.insert(0, str(STAGE / 'scripts/svf_backends'))
import native_accelerate_service as service


class NativeObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        names = [service.SDK_PATH, service.BACKEND_PATH, service.SERVICE_PATH,
                 service.OBSERVATION_PATH, *[row[0] for row in service.OBSERVATION_TOOLS.values()]]
        for name in names:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged = STAGE / name
            destination.write_bytes((staged if staged.exists() else LIVE / name).read_bytes())
        interpreter = LIVE / service.PYTHON_PATH
        self.python = patch.object(service, 'PYTHON_PATH', str(interpreter if interpreter.is_file() else Path(sys.executable)))
        self.python.start()
        self.addCleanup(self.python.stop)
        self.native = service.NativeAccelerate(service.NAMESPACE / 'backends/observation-unit', root=self.root)

    def call(self, name, args=None):
        value = self.native.call(name, {'correlation_id': 'unit-real-sdk-observation', **(args or {})})
        self.assertEqual(value['receipt']['native_provenance'], value['content'][0]['json']['native_provenance'])
        self.assertFalse(value['isError'])
        return value['content'][0]['json']

    def test_actual_public_health_preserves_sdk_data_without_claiming_inference_or_models(self):
        value = self.call('HealthChecker.check_detailed')
        self.assertEqual(value['status'], 'healthy')
        self.assertIsInstance(value['timestamp'], str)
        self.assertEqual(value['components'], {})
        self.assertGreaterEqual(value['uptime_seconds'], 0)
        self.assertFalse(value['inference_executed'])
        self.assertFalse(value['native_runtime']['engine_loaded'])
        provenance = value['native_provenance']
        self.assertEqual(provenance['sdk_method'], 'check_detailed')
        self.assertEqual(provenance['service_pid'], os.getpid())
        self.assertNotEqual(provenance['observation_pid'], os.getpid())
        path = service.OBSERVATION_TOOLS['HealthChecker.check_detailed'][0]
        self.assertEqual(provenance['sdk_source_sha256'], service.digest(LIVE / path))
        self.assertNotIn('model_loader', value['components'])

    def test_actual_metrics_exporter_contains_the_same_measured_host_utilization(self):
        value = self.call('PrometheusMetrics.generate_metrics')
        self.assertGreaterEqual(value['utilization'], 0)
        self.assertLessEqual(value['utilization'], 100)
        self.assertGreater(value['memory_total_bytes'], 0)
        self.assertIsNone(value['gpu_utilization'])
        self.assertIn('hf_server_hardware_utilization{device="host_aggregate",hardware="cpu"} ' + str(value['utilization']), value['metrics'])
        self.assertEqual(value['native_provenance']['scope'], 'host_cpu_memory_and_observation_process')
        self.assertIn('not the inference worker', value['prometheus_process_scope'])

    def test_repeated_actual_metrics_use_fresh_bounded_processes_without_registry_collisions(self):
        first = self.call('PrometheusMetrics.generate_metrics')
        second = self.call('PrometheusMetrics.generate_metrics')
        self.assertNotEqual(first['native_provenance']['observation_pid'], second['native_provenance']['observation_pid'])
        self.assertNotEqual(first['timestamp'], second['timestamp'])

    def test_preview_unknown_arguments_and_invalid_correlation_never_launch_a_process(self):
        with patch.object(service.subprocess, 'run') as run:
            for args in ({'dry_run': True}, {'output_path': '/tmp/forbidden'}, {'correlation_id': 'x' * 257}, {'fixture_scope': {}}, {'scope': 'ignored-arg'}):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    self.call('HealthChecker.check_detailed', args)
            run.assert_not_called()

    def test_changed_monitoring_source_invalidates_the_native_source_contract(self):
        source = self.root / service.OBSERVATION_TOOLS['HealthChecker.check_detailed'][0]
        source.write_text(source.read_text() + '\n# actual readonly dependency changed\n')
        self.assertFalse(self.native.sources_current())
        with patch.object(service.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                self.call('HealthChecker.check_detailed')
            run.assert_not_called()

    def test_changed_observation_helper_also_invalidates_source_contract(self):
        source = self.root / service.OBSERVATION_PATH
        source.write_text(source.read_text() + '\n# changed helper\n')
        self.assertFalse(self.native.sources_current())

    def test_observation_timeout_releases_the_slot_without_fallback(self):
        with patch.object(service.subprocess, 'run', side_effect=subprocess.TimeoutExpired('actual-sdk', 6)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.call('HealthChecker.check_detailed')
        self.assertFalse(self.native.observation_slot.locked())

    def test_busy_observation_does_not_start_duplicate_sampling(self):
        self.native.observation_slot.acquire()
        with patch.object(service.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                self.call('HealthChecker.check_detailed')
            run.assert_not_called()

    def test_oversized_response_is_not_parsed_or_accepted(self):
        with patch.object(service.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'x' * 65537, '')):
            with self.assertRaisesRegex(RuntimeError, 'response bound'):
                self.call('HealthChecker.check_detailed')
        self.assertFalse(self.native.observation_slot.locked())

    def test_nonzero_sdk_exit_is_a_real_failure(self):
        with patch.object(service.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'SDK failed')):
            with self.assertRaisesRegex(RuntimeError, 'SDK observation failed'):
                self.call('HealthChecker.check_detailed')

    def test_forged_helper_identity_and_simulation_are_refused(self):
        tool = 'HealthChecker.check_detailed'
        path, sdk_class, method = service.OBSERVATION_TOOLS[tool]
        value = {'schema': 'swissknife.native-accelerate-observation-result.v1', 'tool': tool,
                 'sdk_class': sdk_class, 'sdk_method': method, 'sdk_source_path': path,
                 'sdk_source_sha256': self.native.observation_sources[path],
                 'observation_source_sha256': self.native.observation_sources[service.OBSERVATION_PATH],
                 'parent_pid': os.getpid(), 'pid': 1, 'simulated': False, 'inference_executed': False,
                 'external_provider_called': False, 'result': {}, 'scope': 'unit'}
        for override in ({'parent_pid': -1}, {'sdk_class': 'fake.Owner'}, {'simulated': True},
                         {'sdk_source_sha256': '0' * 64}, {'inference_executed': True}, {'external_provider_called': True}):
            with self.subTest(override=override), patch.object(service.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps({**value, **override}), '')):
                with self.assertRaisesRegex(RuntimeError, 'provenance'):
                    self.call(tool)


if __name__ == '__main__':
    unittest.main()
