"""Storage admission refuses before paid work without changing failure budgets."""
import contextlib
import errno
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm
from ipfs_accelerate_py.agent_supervisor.rescue import storage_pressure as storage

spec = importlib.util.spec_from_file_location('_svf_storage_context_fixture', Path(__file__).with_name('test_swissknife_visual_functional_context.py'))
context_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_fixture)


class StorageAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.case = context_fixture.RepairContextTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_real_healthy_capacity_keeps_original_context_edits_and_provider_boundary(self):
        called = []
        def invoke(*args, **kwargs):
            called.append(1)
            self.assertEqual(kwargs['predicted_files'], self.case.targets)
            self.assertTrue(all(name in kwargs['input_paths'] for name in self.case.targets))
            return {'success': True}
        self.case.call(invoke)
        self.assertEqual(called, [1])
        self.assertFalse(list(self.case.root.glob('.supervisor-capacity-*')))

    def test_real_statvfs_floor_refuses_before_context_phase_or_provider(self):
        info = type('Capacity', (), {'f_bavail': 0, 'f_frsize': 4096})()
        with patch.object(storage.os, 'statvfs', return_value=info), \
                patch.object(storage, '_durable_probe') as probe, \
                patch('swissknife_visual_functional_phase_budget.admit') as admit, \
                patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaises(worker.StoragePressure) as caught:
                worker.model('profile.json', self.case.task, 'repair', [], [], self.case.output)
            self.assertEqual((caught.exception.reason, caught.exception.errno), ('insufficient_free_bytes', None))
            probe.assert_not_called(); admit.assert_not_called(); provider.assert_not_called()
        self.assertFalse((self.case.output.parent / 'model-inputs').exists())

    def test_actual_durable_enospc_and_edquot_are_typed_before_spend(self):
        for number, reason in [(errno.ENOSPC, 'ENOSPC'), (errno.EDQUOT, 'EDQUOT')]:
            with self.subTest(number=number), patch.object(storage, '_durable_probe', side_effect=OSError(number, 'capacity probe failed')), \
                    patch('swissknife_visual_functional_phase_budget.admit') as admit, patch.object(llm, 'invoke_task_model') as provider:
                with self.assertRaises(worker.StoragePressure) as caught:
                    worker.model('profile.json', self.case.task, 'repair', [], [], self.case.output)
                self.assertEqual((caught.exception.reason, caught.exception.errno), (reason, number))
                admit.assert_not_called(); provider.assert_not_called()

    def test_permission_and_unrelated_io_do_not_become_resource_refusals(self):
        for number in [errno.EACCES, errno.EIO]:
            with self.subTest(number=number), patch.object(storage, '_durable_probe', side_effect=OSError(number, 'not capacity')):
                with self.assertRaises(OSError) as caught:
                    worker.assert_storage_available(self.case.profile)
                self.assertEqual(caught.exception.errno, number)
                self.assertIsNone(worker.storage_refusal(caught.exception))

    def test_second_gate_after_context_precedes_visual_phase_and_provider_admission(self):
        self.case.visual_failure()
        with patch.object(worker, 'assert_storage_available', side_effect=[None, worker.StoragePressure('ENOSPC', errno.ENOSPC)]), \
                patch('swissknife_visual_functional_phase_budget.admit') as admit, patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaises(worker.StoragePressure):
                worker.model('profile.json', self.case.task, 'repair', self.case.targets, [], self.case.output)
            admit.assert_not_called(); provider.assert_not_called()

    def test_hold_remains_authoritative_before_any_capacity_or_provider_work(self):
        (self.case.root / 'HOLD').touch()
        with patch.object(worker, 'assert_storage_available') as capacity, patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaisesRegex(RuntimeError, 'hold is active'):
                worker.model('profile.json', self.case.task, 'repair', [], [], self.case.output)
            capacity.assert_not_called(); provider.assert_not_called()

    def test_execute_refuses_before_runtime_directory_or_browser_launch(self):
        profile = dict(self.case.profile, runtimeRoot='data/not-created-storage-test')
        with patch.object(worker, 'ensure_lease'), patch.object(worker, 'check_owned_sources'), \
                patch.object(worker, 'assert_storage_available', side_effect=worker.StoragePressure('EDQUOT', errno.EDQUOT)), \
                patch.object(worker, 'run') as run:
            with self.assertRaises(worker.StoragePressure):
                worker.execute('profile.json', profile, {'tasks': [self.case.task]}, self.case.task)
            run.assert_not_called()
        self.assertFalse((self.case.root / profile['runtimeRoot']).exists())

    def test_baseline_and_workflow_refuse_before_attempts_and_chrome(self):
        self.case.write('swissknife/scripts/run-visual-functional-workflow.mjs', '// runner fixture')
        for function in [worker.baseline, worker.workflow]:
            directory = self.case.output.parent / function.__name__
            with self.subTest(function=function.__name__), patch.object(worker, 'assert_storage_available', side_effect=worker.StoragePressure('ENOSPC', errno.ENOSPC)), patch.object(worker, 'run') as run:
                with self.assertRaises(worker.StoragePressure):
                    function(self.case.profile, self.case.task, directory)
                run.assert_not_called()
            self.assertFalse(directory.exists())

    def test_recovery_refuses_before_bridge_or_paid_model(self):
        with patch.object(worker, 'assert_storage_available', side_effect=worker.StoragePressure('ENOSPC', errno.ENOSPC)), \
                patch('swissknife_visual_functional_recovery.run_recovery') as bridge:
            with self.assertRaises(worker.StoragePressure):
                worker.recover('profile.json', self.case.profile, self.case.task)
            bridge.assert_not_called()

    def test_exact_cli_packets_exit75_without_status_artifacts_or_false_completion(self):
        for reason, number in [('insufficient_free_bytes', None), ('ENOSPC', errno.ENOSPC), ('EDQUOT', errno.EDQUOT)]:
            error = worker.StoragePressure(reason, number)
            with self.subTest(reason=reason), patch.object(worker, 'load', return_value=(self.case.profile, {'tasks': [self.case.task]})), \
                    patch.object(worker, 'execute', side_effect=error), contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = worker.main(['--task-id', self.case.task['task_id']])
                packet = json.loads(stderr.getvalue())
                self.assertEqual(code, 75)
                self.assertEqual(packet, {'task_id': self.case.task['task_id'], 'error': {'code': 'storage_pressure', 'reason': reason, 'errno': number},
                                          'retryable': True, 'work_complete': False, 'completion_authority': False})

    def test_pre_admission_raw_space_error_gets_resource_cli_but_permission_does_not(self):
        for number, expected in [(errno.ENOSPC, 75), (errno.EDQUOT, 75), (errno.EACCES, 1), (errno.EIO, 1)]:
            with self.subTest(number=number), patch.object(worker, 'load', return_value=(self.case.profile, {'tasks': [self.case.task]})), \
                    patch.object(worker, 'execute', side_effect=OSError(number, 'injected')), contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(worker.main(['--task-id', self.case.task['task_id']]), expected)
                if expected == 75:
                    self.assertEqual(json.loads(stderr.getvalue())['error']['errno'], number)
                else:
                    self.assertNotIn('storage_pressure', stderr.getvalue())

    def test_midflight_space_failure_retains_admitted_attempt_without_refund_or_feedback(self):
        self.case.visual_failure()
        with patch.object(worker, 'assert_storage_available'), \
                patch('swissknife_visual_functional_phase_budget.admit', return_value='durably-admitted') as admit, \
                patch('swissknife_visual_functional_phase_budget.finish') as finish, \
                patch.object(worker, 'remember_repair_failure') as feedback, \
                patch.object(llm, 'invoke_task_model', side_effect=OSError(errno.ENOSPC, 'post-admission disk full')):
            with self.assertRaises(worker.StoragePressure):
                worker.model('profile.json', self.case.task, 'repair', self.case.targets, [], self.case.output)
            admit.assert_called_once(); finish.assert_not_called(); feedback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
