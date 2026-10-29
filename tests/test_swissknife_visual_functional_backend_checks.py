"""Authored command/model observations exercise real controller/cache code offline.

These tests do not qualify a backend, call a provider, or grant completion.
"""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

STAGE = Path(__file__).resolve().parents[1]
CHECKOUT = Path(os.environ.get('SVF_BACKEND_DECLINE_TEST_ROOT', str(STAGE))).resolve()
sys.path[:0] = [str(STAGE / 'scripts'), str(CHECKOUT / 'scripts')]
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_native_context as context
import swissknife_visual_functional_blocked as cache
import swissknife_visual_functional_llm as adapter
import swissknife_visual_functional_phase_budget as phases


class BackendOriginalChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = {'task_id': 'SVF-133', 'kind': 'backend-repair', 'app_id': None,
            'title': 'Authored backend fixture', 'acceptance': 'Original checks and positive model receipt',
            'edit_paths': ['backend.py', 'second.py'], 'context_paths': ['contract.txt'],
            'execution_inputs': ['contract.txt'], 'semantic_recovery_inputs': ['recovery.txt'],
            'dependencies': [], 'checks': [['python3', 'tests/check_a.py'], ['python3', 'tests/check_b.py']]}
        self.profile = {'runtimeRoot': context.BACKEND_RUNTIME, 'appContractPath': 'contracts.json',
            'taskSpecPath': 'tasks.json', 'humanPlanPath': 'plan.md',
            'llm': {'provider': 'grok_cli', 'model': 'grok-4.7', 'temperature': 0,
                'allowLocalFallback': False, 'allowCrossProviderFallback': False,
                'repairReadPolicy': 'inline_only', 'maxOutputTokens': 16384}}
        self.directory = self.root / context.BACKEND_RUNTIME / 'tasks' / self.task['task_id']
        self.directory.mkdir(parents=True)
        for name, value in {'backend.py': '# current backend\n', 'second.py': '# second allowed source\n',
                'contract.txt': 'Existing exact public contract\n', 'recovery.txt': 'Original recovery policy\n',
                'plan.md': 'Original authored test plan', 'tests/check_a.py': '# original first check',
                'tests/check_b.py': '# original second check'}.items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
        for name in context.BACKEND_CONTROLLER_INPUTS:
            source = STAGE / name
            if not source.is_file(): source = CHECKOUT / name
            if source.is_file():
                target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        self.save_policy()
        self.events = []; self.paid = []; self.responses = []; self.decision = 'pass'
        self.failure = None
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        for target, name, replacement in [
            (worker, 'ROOT', self.root),
            (worker, 'ensure_lease', lambda p: (worker.assert_no_campaign_hold(p), self.events.append('lease'))),
            (worker, 'check_owned_sources', lambda p, paths: self.events.append(('owned', tuple(paths)))),
            (worker, 'assert_storage_available', lambda p: self.events.append('capacity')),
            (worker, 'remember_owned_sources', lambda p, paths: None),
            (worker, 'qualified_recovery', lambda p, t: None),
            (worker, 'run', self.run_check),
            (adapter, 'invoke_task_model', self.invoke),
        ]: self.stack.enter_context(patch.object(target, name, replacement))
        self.stack.enter_context(patch.object(worker.subprocess, 'Popen', side_effect=AssertionError('No real commands allowed')))

    def save_policy(self):
        for name, value in [('profile.json', self.profile), ('contracts.json', {'apps': []}), ('tasks.json', {'tasks': [self.task]})]:
            (self.root / name).write_text(json.dumps(value))

    def sha(self, name): return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def run_check(self, argv, **kwargs):
        self.events.append(('check', tuple(argv)))
        executed = [sys.executable, *argv[1:]]
        if self.failure is not None:
            raise worker.ValidationCommandError(executed, 17, 'actual stdout tail', self.failure)
        return {'argv': executed, 'exit_code': 0, 'output_tail': 'actual authored command output'}

    def invoke(self, profile_path, task_id, mode, **kwargs):
        self.events.append('model'); self.paid.append(kwargs)
        ctx = json.loads((self.root / kwargs['input_paths'][0]).read_text())
        self.responses.append(ctx)
        response = {'schema': adapter.RESPONSE_SCHEMA, 'task_id': task_id, 'mode': mode,
            'decision': self.decision, 'summary': 'Authored model response; no actual provider call.',
            'inspected_screenshots': [], 'findings': [], 'edits': []}
        if self.decision == 'blocked':
            response['findings'] = [{'severity': 'blocker', 'category': 'backend',
                'description': 'Authored unchanged backend refusal.', 'evidence_paths': ['contract.txt']}]
        receipt = {'schema': adapter.RECEIPT_SCHEMA, 'task_id': task_id, 'mode': mode,
            'provider': 'grok_cli', 'model': 'grok-4.7', 'temperature': 0, 'success': True,
            'allow_local_fallback': False, 'allow_cross_provider_fallback': False,
            'disable_model_retry': True, 'edits_applied': False, 'work_complete': False, 'completion_authority': False,
            'native_read_file_denied': True,
            'effective_route': {'effective_provider_name': 'grok_cli', 'effective_model_name': 'grok-4.7'},
            'native_observation': {'exit_code': 0, 'native_grok_reason_code': 'end_turn',
                'native_grok_error_observed': False, 'native_grok_progress': {'response_usable': True,
                    'tool_name_counts': {'read_file': 0, 'run_terminal_cmd': 0, 'unknown': 0}}},
            'screenshots': [], 'response': response,
            'input_files': [{'path': name, 'sha256': self.sha(name), 'size_bytes': (self.root / name).stat().st_size}
                for name in kwargs['input_paths']]}
        for key in ('source_contract_sha256', 'prompt_sha256', 'router_source_sha256', 'output_sha256'):
            receipt[key] = 'a' * 64
        receipt['response_sha256'] = hashlib.sha256(adapter._json(response).encode()).hexdigest()
        path = self.root / kwargs['output_path']; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt)); return receipt

    def probe(self): return worker._backend_original_checks(self.profile, self.task)

    def model(self, producer, **kwargs):
        return worker.model('profile.json', self.task, 'repair', ['contract.txt', 'backend.py', 'second.py'], [],
            self.directory / 'proposal.json', backend_producer=producer, **kwargs)

    def test_pass_prechecks_model_and_original_checks_reexecute_then_real_validator(self):
        receipt = worker.execute('profile.json', self.profile, {'tasks': [self.task]}, self.task)
        self.assertEqual([e for e in self.events if isinstance(e, tuple) and e[0] == 'check'],
            [('check', tuple(command)) for command in self.task['checks']] * 2)
        model_index = self.events.index('model')
        self.assertEqual(sum(isinstance(e, tuple) and e[0] == 'check' for e in self.events[:model_index]), 2)
        self.assertEqual(sum(isinstance(e, tuple) and e[0] == 'check' for e in self.events[model_index:]), 2)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.responses[0]['backend_original_checks']['outcome'], 'passed')
        self.assertFalse(receipt['completion_authority'])
        self.assertEqual(worker.validate(self.profile, self.task), receipt)

    def test_precheck_report_cannot_replace_positive_repair_receipt(self):
        producer = self.probe()
        fake = {'schema': 'swissknife.visual-functional-task.v1', 'task_id': self.task['task_id'],
            'kind': 'backend-repair', 'task_spec_sha256': worker.stable(self.task),
            'artifacts': [worker.artifact(self.root / producer['path'])],
            'checks': [self.run_check(command) for command in self.task['checks']], 'detail': {},
            'work_complete': False, 'completion_authority': False}
        (self.directory / 'receipt.json').write_text(json.dumps(fake))
        with self.assertRaisesRegex(ValueError, 'independently validated model receipt'):
            worker.validate(self.profile, self.task)
        self.assertEqual(self.paid, [])

    def test_failed_probe_is_actual_typed_command_diagnostic_and_still_has_model(self):
        self.failure = 'actual backend dependency not ready'
        producer = self.probe(); loaded = context.load_backend_check_report(self.root, self.task, producer)
        self.assertEqual(loaded['report']['outcome'], 'failed')
        self.assertEqual(loaded['report']['diagnostic'], {'stage': 'command', 'code': 'ValidationCommandError',
            'check_index': 0, 'argv': [sys.executable, *self.task['checks'][0][1:]], 'exit_code': 17,
            'stdout_tail': 'actual stdout tail', 'stderr_tail': self.failure})
        self.model(producer)
        packet = self.responses[0]['backend_original_checks']
        self.assertEqual(packet['outcome'], 'failed')
        self.assertIn(self.failure, json.dumps(packet))
        self.assertEqual(len(self.paid), 1)
        self.assertFalse((self.directory / 'last-execution-failure.json').exists())

    def test_unchanged_real_producer_does_not_renew_paid_decline(self):
        self.decision = 'blocked'
        with self.assertRaisesRegex(ValueError, 'model declined'): self.model(self.probe())
        with self.assertRaises(cache.CachedBlockedRepair): self.model(self.probe())
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(sum(isinstance(e, tuple) and e[0] == 'check' for e in self.events), 4)
        self.assertFalse((self.directory / 'receipt.json').exists())

    def test_changed_real_outcome_requalifies_one_paid_call_and_identical_failure_stops(self):
        self.decision = 'blocked'
        with self.assertRaisesRegex(ValueError, 'model declined'): self.model(self.probe())
        self.failure = 'concrete new actual stderr'
        with self.assertRaisesRegex(ValueError, 'model declined'): self.model(self.probe())
        with self.assertRaises(cache.CachedBlockedRepair): self.model(self.probe())
        self.assertEqual(len(self.paid), 2)

    def test_changed_static_source_requalifies_and_old_report_refuses(self):
        self.decision = 'blocked'; original = self.probe()
        with self.assertRaisesRegex(ValueError, 'model declined'): self.model(original)
        (self.root / 'contract.txt').write_text('A concrete new static contract')
        with self.assertRaisesRegex(ValueError, 'source|current'): self.model(original)
        self.assertEqual(len(self.paid), 1)
        with self.assertRaisesRegex(ValueError, 'model declined'): self.model(self.probe())
        self.assertEqual(len(self.paid), 2)

    def test_hold_and_capacity_refuse_before_any_precheck_or_provider(self):
        (self.root / 'HOLD').write_text('authored operator hold')
        with self.assertRaisesRegex(RuntimeError, 'hold'): self.probe()
        self.assertFalse(any(isinstance(e, tuple) and e[0] == 'check' for e in self.events)); self.assertFalse(self.paid)
        (self.root / 'HOLD').unlink()
        with patch.object(worker, 'assert_storage_available', side_effect=worker.StoragePressure('insufficient_free_bytes')):
            with self.assertRaises(worker.StoragePressure): self.probe()
        self.assertFalse(any(isinstance(e, tuple) and e[0] == 'check' for e in self.events)); self.assertFalse(self.paid)

    def test_hold_and_capacity_rechecked_after_producer_before_provider(self):
        producer = self.probe(); (self.root / 'HOLD').write_text('authored later hold')
        with self.assertRaisesRegex(RuntimeError, 'hold'): self.model(producer)
        (self.root / 'HOLD').unlink()
        with patch.object(worker, 'assert_storage_available', side_effect=worker.StoragePressure('insufficient_free_bytes')):
            with self.assertRaises(worker.StoragePressure): self.model(producer)
        self.assertEqual(self.paid, [])

    def test_recovery_subset_binds_original_report_without_expanding_edits(self):
        producer = self.probe()
        self.model(producer, edit_paths_override=['backend.py'], recovery_context={'edit_paths': ['backend.py'],
            'source_before': {name: self.sha(name) for name in self.task['edit_paths']}})
        self.assertEqual(self.paid[0]['predicted_files'], ['backend.py'])
        self.assertEqual(self.responses[0]['task']['edit_paths'], ['backend.py'])
        self.assertEqual(self.responses[0]['bounded_recovery']['source_before'], {'backend.py': self.sha('backend.py')})
        self.assertEqual(self.responses[0]['backend_original_checks']['outcome'], 'passed')

    def test_recovery_subset_decline_reuses_stable_original_producer(self):
        self.decision = 'blocked'
        with self.assertRaisesRegex(ValueError, 'model declined'):
            self.model(self.probe(), edit_paths_override=['backend.py'])
        with self.assertRaises(cache.CachedBlockedRepair):
            self.model(self.probe(), edit_paths_override=['backend.py'])
        self.assertEqual(len(self.paid), 1)
        with self.assertRaisesRegex(ValueError, 'scope exceeds'):
            self.model(self.probe(), edit_paths_override=['contract.txt'])

    def test_fresh_backend_report_does_not_admit_historical_visual_failure_budget(self):
        historical = {'failure': {'visual_review': {'original': {'path': 'old-review.json'}}}}
        with patch.object(worker, 'load_execution_failure', return_value=historical), \
                patch.object(worker, '_repair_needs_stylesheet_context', return_value=False), \
                patch.object(phases, 'admit', side_effect=AssertionError('Historical visual phase admission')):
            self.model(self.probe())
        self.assertEqual(len(self.paid), 1)
        self.assertNotIn('latest_execution_failure', self.responses[0])

    def test_no_backend_probe_for_other_implementation_kinds(self):
        self.task['kind'] = 'implementation'; self.save_policy()
        with patch.object(worker, '_backend_original_checks', side_effect=AssertionError('Backend-only producer')):
            receipt = worker.execute('profile.json', self.profile, {'tasks': [self.task]}, self.task)
        self.assertEqual(len(self.paid), 1)
        self.assertNotIn('backend_original_checks', self.responses[0])
        self.assertEqual(len(receipt['checks']), 2)


if __name__ == '__main__': unittest.main()
