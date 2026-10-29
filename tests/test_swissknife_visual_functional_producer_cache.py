"""Authored actual-report protocol fixtures; no check commands or providers run."""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest

STAGE = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('SVF_BACKEND_DECLINE_TEST_ROOT', str(STAGE))).resolve()
sys.path[:0] = [str(STAGE / 'scripts'), str(ROOT / 'scripts')]
import swissknife_visual_functional_blocked as cache
import swissknife_visual_functional_native_context as producer
import swissknife_visual_functional_llm as adapter


class ProducerAwareCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = {'task_id': 'SVF-044', 'kind': 'backend-repair', 'app_id': None,
                     'acceptance': 'Original gates and fresh genuine model review',
                     'edit_paths': ['app.py'], 'context_paths': ['api.py'],
                     'execution_inputs': ['app.py', 'api.py', *sorted(cache.PROPOSAL_METADATA)],
                     'checks': [['python3', 'scripts/original_check.py'], ['node', 'scripts/original_check.cjs']],
                     'dependencies': ['SVF-042'], 'llm_limits': {'modelContextBytes': 262144}}
        self.route = {'provider': 'grok_cli', 'model': 'grok-4.7', 'temperature': 0,
                      'allowLocalFallback': False, 'allowCrossProviderFallback': False, 'repairReadPolicy': 'inline_only'}
        for name in [*producer.BACKEND_CONTROLLER_INPUTS, 'app.py', 'api.py',
                     'scripts/original_check.py', 'scripts/original_check.cjs', *sorted(cache.PROPOSAL_METADATA)]:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# authored source fixture; never executed\n')
        self.directory = cache.RUNTIME + 'tasks/SVF-044/blocked-repairs'
        self.receipt_path = self.root / 'blocked.json'

    def sources(self): return producer.backend_source_hashes(self.root, self.task)
    def ref(self, *, failed=False, stdout='actual assertion differs', stderr='', pass_output='passed in 0.01s'):
        checks = []
        for index, declared in enumerate(self.task['checks']):
            executed = list(declared)
            if declared[0] == 'python3': executed[0] = sys.executable
            checks.append({'index': index, 'declared_argv': declared, 'executed_argv': executed,
                           'exit_code': 1 if failed and index == 1 else 0,
                           'output_tail': producer.backend_output_tail(stdout, stderr) if failed and index == 1 else pass_output})
        diagnostic = None
        if failed:
            diagnostic = {'stage': 'command', 'code': 'ValidationCommandError', 'check_index': 1,
                          'argv': checks[-1]['executed_argv'], 'exit_code': 1,
                          'stdout_tail': stdout, 'stderr_tail': stderr}
        return producer.write_backend_check_report(self.root, self.task, source_sha256=self.sources(),
                                                   checks=checks, diagnostic=diagnostic)
    def scope(self, reference, **changes):
        sources = self.sources(); kwargs = {'task': self.task, 'route': self.route,
            'edit_hashes': {name: sources[name] for name in self.task['edit_paths']},
            'readonly_hashes': {name: value for name, value in sources.items() if name not in self.task['edit_paths']},
            'producer': reference}
        kwargs.update(changes)
        return cache.build_producer_scope(self.root, **kwargs)
    def receipt(self, scope, *, producer_digest=True):
        context = {'task': {key: scope['identity']['task'][key] for key in ('task_id', 'kind', 'app_id', 'acceptance', 'checks', 'edit_paths',
                   'dependencies', 'llm_limits', 'conflict_policy') if key in scope['identity']['task']},
                   'proposal_scope_fingerprint': scope['fingerprint']}
        if producer_digest: context['producer_identity_sha256'] = cache._sha(cache._json(scope['identity']['producer']).encode())
        path = self.root / (cache.RUNTIME + 'tasks/SVF-044/model-inputs/repair-test/context.json')
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(context))
        response = {'schema': adapter.RESPONSE_SCHEMA, 'task_id': 'SVF-044', 'mode': 'repair', 'decision': 'blocked',
                    'summary': 'Authoring fixture: repair context remains insufficient.', 'inspected_screenshots': [],
                    'findings': [{'severity': 'blocker', 'category': 'backend', 'description': 'The exact original assertion remains.',
                                  'evidence_paths': ['api.py']}], 'edits': []}
        value = {'schema': adapter.RECEIPT_SCHEMA, 'task_id': 'SVF-044', 'mode': 'repair',
            'provider': 'grok_cli', 'model': 'grok-4.7', 'temperature': 0, 'success': True,
            'allow_local_fallback': False, 'allow_cross_provider_fallback': False, 'disable_model_retry': True,
            'edits_applied': False, 'work_complete': False, 'completion_authority': False, 'screenshots': [],
            'native_read_file_denied': True,
            'effective_route': {'effective_provider_name': 'grok_cli', 'effective_model_name': 'grok-4.7'},
            'native_observation': {'exit_code': 0, 'native_grok_reason_code': 'end_turn', 'native_grok_error_observed': False,
               'native_grok_progress': {'response_usable': True, 'tool_name_counts': {'read_file': 0, 'run_terminal_cmd': 0, 'unknown': 0}}},
            'input_files': [{'path': name, 'sha256': digest} for name, digest in self.sources().items()],
            'response': response}
        value['input_files'].append({'path': str(path.relative_to(self.root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                    'size_bytes': path.stat().st_size})
        for key in ('source_contract_sha256', 'prompt_sha256', 'router_source_sha256', 'output_sha256'): value[key] = 'a' * 64
        value['response_sha256'] = hashlib.sha256(adapter._json(response).encode()).hexdigest()
        self.receipt_path.write_text(json.dumps(value)); return value
    def remember(self, scope):
        return cache.remember_blocked(self.root, self.directory, scope, 'blocked.json')

    def test_passing_producer_is_observation_not_a_synthetic_failure_or_completion(self):
        scope = self.scope(self.ref())
        self.assertNotIn('failure', scope['identity'])
        self.assertEqual(scope['identity']['producer']['outcome'], 'passed')
        self.assertIsNone(scope['identity']['producer']['diagnostic'])
        self.assertEqual(scope['identity']['proposal']['reason'], 'backend_checked_model_decline')
        self.assertFalse((self.root / self.directory).exists())

    def test_initial_no_producer_negative_scope_is_disjoint_from_real_checked_scope(self):
        scope = self.scope(self.ref()); identity = scope['identity']
        initial = cache.build_proposal_scope(self.root, task=self.task, route=self.route,
            edit_hashes=identity['edit_hashes'], readonly_hashes=identity['readonly_hashes'])
        self.assertNotEqual(scope['fingerprint'], initial['fingerprint'])

    def test_same_actual_outcome_does_not_renew_eligibility_on_new_report_uuid_or_time(self):
        first = self.scope(self.ref(pass_output='success in 0.001s'))
        second = self.scope(self.ref(pass_output='success in 9.992s'))
        self.assertNotEqual(first['producer_reference'], second['producer_reference'])
        self.assertEqual(first['identity'], second['identity']); self.assertEqual(first['fingerprint'], second['fingerprint'])

    def test_same_checked_decline_is_reused_with_fresh_same_outcome_report(self):
        first = self.scope(self.ref()); self.receipt(first); self.remember(first)
        current = self.scope(self.ref(pass_output='fresh actual check in 0.4s'))
        with self.assertRaises(cache.CachedBlockedRepair): cache.raise_if_blocked(self.root, self.directory, current)

    def test_changed_actual_outcome_or_asserted_failure_qualifies_a_new_scope(self):
        first = self.scope(self.ref(failed=True, stdout='expected X actual Y'))
        self.receipt(first); self.remember(first)
        for reference in [self.ref(), self.ref(failed=True, stdout='expected X actual Z')]:
            scope = self.scope(reference)
            self.assertNotEqual(scope['fingerprint'], first['fingerprint'])
            self.assertIsNone(cache.raise_if_blocked(self.root, self.directory, scope))

    def test_failed_diagnostic_ignores_uuid_paths_times_pids_and_nonce_only(self):
        one = '2026-10-27T22:11:12.123Z attempt-11111111-1111-4111-8111-111111111111 {"pid": 12, "duration_seconds": 1.2, "challenge": "' + 'a'*32 + '"} in 0.2s expected X actual Y'
        two = '2026-10-28T23:12:13.456Z attempt-22222222-2222-4222-8222-222222222222 {"pid": 98, "duration_seconds": 3.4, "challenge": "' + 'b'*32 + '"} in 4.5s expected X actual Y'
        self.assertEqual(self.scope(self.ref(failed=True, stdout=one))['fingerprint'],
                         self.scope(self.ref(failed=True, stdout=two))['fingerprint'])

    def test_rpc_observation_hashes_and_attempt_tokens_do_not_renew_identical_failure(self):
        first = {'schema': 'swissknife.supervisor-foundation-rpc-failure.v1', 'response_sha256': 'a'*64,
                 'request_sha256': 'b'*64, 'capture_sha256': 'c'*64,
                 'capture': {'path': 'events/attempt-' + 'd'*32, 'sha256': 'e'*64},
                 'error': {'code': 'actual_backend_error', 'message': 'same semantic failure'}}
        second = copy.deepcopy(first)
        second.update(response_sha256='1'*64, request_sha256='2'*64, capture_sha256='3'*64)
        second['capture'] = {'path': 'events/attempt-' + '4'*32, 'sha256': '5'*64}
        a = self.scope(self.ref(failed=True, stderr=json.dumps(first)))
        b = self.scope(self.ref(failed=True, stderr=json.dumps(second)))
        self.assertEqual(a['fingerprint'], b['fingerprint'])
        second['error']['message'] = 'genuinely different semantic failure'
        changed = self.scope(self.ref(failed=True, stderr=json.dumps(second)))
        self.assertNotEqual(a['fingerprint'], changed['fingerprint'])

    def test_pubsub_failure_artifact_reference_is_observation_not_new_semantic_failure(self):
        first = {'schema': 'swissknife.pubsub-foundation-capsule.v1', 'passed': False,
                 'error_code': 'peer_ack_missing', 'failure_artifact': {
                     'path': 'qualification/attempt-' + 'a'*32 + '/failure.json', 'sha256': 'b'*64, 'bytes': 8000}}
        second = copy.deepcopy(first)
        second['failure_artifact'] = {'path': 'qualification/attempt-' + 'c'*32 + '/failure.json',
                                      'sha256': 'd'*64, 'bytes': 8200}
        a = self.scope(self.ref(failed=True, stdout=json.dumps(first)))
        b = self.scope(self.ref(failed=True, stdout=json.dumps(second)))
        self.assertEqual(a['fingerprint'], b['fingerprint'])
        second['error_code'] = 'different_actual_peer_failure'
        self.assertNotEqual(a['fingerprint'], self.scope(self.ref(failed=True, stdout=json.dumps(second)))['fingerprint'])

    def test_raw_failed_output_is_never_copied_into_negative_cache(self):
        scope = self.scope(self.ref(failed=True, stdout='RAW_PRIVATE_COMMAND_BODY_DO_NOT_CACHE'))
        self.receipt(scope); self.remember(scope)
        content = b''.join(p.read_bytes() for p in (self.root / self.directory).glob('*.json'))
        self.assertNotIn(b'RAW_PRIVATE_COMMAND_BODY', content)

    def test_source_change_requires_a_fresh_real_report_and_changes_cache_identity(self):
        old = self.ref(); first = self.scope(old)
        (self.root / 'api.py').write_text('# actual readonly API changed\n')
        with self.assertRaises(cache.BlockedCacheError): self.scope(old)
        current = self.scope(self.ref())
        self.assertNotEqual(first['fingerprint'], current['fingerprint'])

    def test_unrelated_taskboard_status_does_not_change_actual_producer_identity(self):
        reference = self.ref(); first = self.scope(reference)
        for name in cache.PROPOSAL_METADATA: (self.root / name).write_text('unrelated task now completed')
        self.assertEqual(first, self.scope(reference))

    def test_report_source_closure_cannot_be_omitted_from_negative_admission(self):
        reference = self.ref(); scope = self.scope(reference)
        readonly = dict(scope['identity']['readonly_hashes']); readonly.pop('scripts/swissknife_visual_functional_phase_budget.py')
        with self.assertRaises(cache.BlockedCacheError): self.scope(reference, readonly_hashes=readonly)

    def test_mutating_current_or_historical_immutable_report_fails_closed(self):
        reference = self.ref(); scope = self.scope(reference); self.receipt(scope); self.remember(scope)
        current = self.scope(self.ref())
        path = self.root / reference['path']; path.write_text('{}')
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, current)

    def test_producer_reference_omission_or_rebinding_cannot_bypass_integrity_fence(self):
        scope = self.scope(self.ref()); self.receipt(scope)
        missing = {key: value for key, value in scope.items() if key != 'producer_reference'}
        with self.assertRaises(cache.BlockedCacheError): self.remember(missing)
        changed = dict(scope, producer_reference=self.ref(failed=True))
        with self.assertRaises(cache.BlockedCacheError): self.remember(changed)

    def test_genuine_receipt_shape_without_producer_context_binding_is_not_cached(self):
        scope = self.scope(self.ref()); self.receipt(scope, producer_digest=False)
        with self.assertRaisesRegex(cache.BlockedCacheError, 'producer identity'): self.remember(scope)

    def test_wrong_actual_producer_context_binding_is_rejected(self):
        scope = self.scope(self.ref()); value = self.receipt(scope)
        reference = value['input_files'][-1]; path = self.root / reference['path']
        body = json.loads(path.read_text()); body['producer_identity_sha256'] = '0' * 64
        path.write_text(json.dumps(body)); reference['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest(); reference['size_bytes'] = path.stat().st_size
        self.receipt_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(cache.BlockedCacheError, 'producer identity'): self.remember(scope)

    def test_malformed_nonprivate_symlink_or_wrong_task_report_never_admits_paid_repair(self):
        reference = self.ref()
        with self.assertRaises(cache.BlockedCacheError): self.scope({**reference, 'sha256': '0'*64})
        path = self.root / reference['path']; path.chmod(0o644)
        with self.assertRaises(cache.BlockedCacheError): self.scope(reference)
        path.chmod(0o600); original = path.with_name('original.json'); path.rename(original); path.symlink_to(original)
        with self.assertRaises(cache.BlockedCacheError): self.scope(reference)

    def test_python_normalization_cannot_change_a_later_node_original_check(self):
        scope = self.scope(self.ref())
        self.assertEqual(scope['identity']['producer']['checks'][0]['executed_argv'][0], 'python3')
        self.assertEqual(scope['identity']['producer']['checks'][1]['executed_argv'][0], 'node')

    def test_recovery_subset_keeps_full_original_producer_task_and_outside_targets_readonly(self):
        (self.root / 'other.py').write_text('# original second target\n')
        self.task['edit_paths'].append('other.py'); self.task['execution_inputs'].append('other.py')
        reference = self.ref(); full = copy.deepcopy(self.task); narrow = {**full, 'edit_paths': ['app.py']}
        sources = self.sources()
        scope = self.scope(reference, task=narrow, producer_task=full,
            edit_hashes={'app.py': sources['app.py']},
            readonly_hashes={key: value for key, value in sources.items() if key != 'app.py'})
        self.assertEqual(scope['identity']['task']['edit_paths'], ['app.py'])
        self.assertEqual(scope['identity']['producer']['original_edit_paths'], ['app.py', 'other.py'])
        self.assertIn('other.py', scope['identity']['readonly_hashes'])
        self.receipt(scope); self.remember(scope)
        with self.assertRaises(cache.CachedBlockedRepair): cache.raise_if_blocked(self.root, self.directory, scope)

    def test_original_producer_cannot_authorize_extra_recovery_targets_or_changed_policy(self):
        reference = self.ref(); original = copy.deepcopy(self.task)
        (self.root / 'outside.py').write_text('# undeclared target\n')
        sources = self.sources()
        with self.assertRaises(cache.BlockedCacheError):
            self.scope(reference, task={**self.task, 'edit_paths': ['app.py', 'outside.py']}, producer_task=original,
                       edit_hashes={'app.py': sources['app.py'], 'outside.py': hashlib.sha256((self.root / 'outside.py').read_bytes()).hexdigest()})
        with self.assertRaises(cache.BlockedCacheError):
            self.scope(reference, producer_task={**original, 'acceptance': 'different original policy'})


if __name__ == '__main__': unittest.main()
