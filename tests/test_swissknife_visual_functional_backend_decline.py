"""Authored source/receipt-bound backend admission tests; no provider or services."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import sys
import unittest

STAGE = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('SVF_BACKEND_DECLINE_TEST_ROOT', str(STAGE))).resolve()
sys.path[:0] = [str(STAGE / 'scripts'), str(ROOT / 'scripts')]
import swissknife_visual_functional_blocked as cache
import swissknife_visual_functional_llm as adapter
spec = importlib.util.spec_from_file_location('backend_decline_original_fixture', ROOT / 'tests/test_swissknife_visual_functional_blocked.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class BackendDecline(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BlockedTests('test_valid_negative_reuses_reason_and_findings_without_granting_acceptance')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.task = dict(self.fixture.task, kind='backend-repair', app_id=None,
                         context_paths=['backend.py'], execution_inputs=['backend.py', 'compiler.py', *sorted(cache.PROPOSAL_METADATA)],
                         dependencies=['SVF-010'], llm_limits={'modelContextBytes': 262144})
        self.route = dict(self.fixture.route, repairReadPolicy='inline_only')
        (self.root / 'compiler.py').write_text('# exact readonly context compiler\n')
        for name in cache.PROPOSAL_METADATA:
            p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('unrelated board status ready\n')
        self.edits = dict(self.fixture.edits)
        self.readonly = {name: self.sha(name) for name in ['backend.py', 'compiler.py', *sorted(cache.PROPOSAL_METADATA)]}
        self.directory = self.fixture.directory
        self.receipt_path = self.fixture.path
        self.context_path = None
        self.save_receipt()

    def sha(self, name): return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def scope(self, **changes):
        kwargs = dict(task=self.task, route=self.route, edit_hashes=self.edits, readonly_hashes=self.readonly)
        kwargs.update(changes)
        return cache.build_proposal_scope(self.root, **kwargs)

    def save_receipt(self, change=lambda r: None, suffix='first'):
        context_name = cache.RUNTIME + 'tasks/' + self.task['task_id'] + '/model-inputs/proposal-' + suffix + '/context.json'
        p = self.root / context_name; p.parent.mkdir(parents=True, exist_ok=True)
        context = {'task': {key: self.task[key] for key in ('task_id', 'title', 'kind', 'app_id', 'acceptance', 'checks', 'edit_paths', 'dependencies', 'llm_limits', 'conflict_policy') if key in self.task},
                   'proposal_scope_fingerprint': self.scope()['fingerprint'],
                   'authority': 'proposal_only; do not manufacture evidence', 'private_body_not_to_cache': 'CONTEXT_BODY_MUST_NOT_BE_COPIED'}
        p.write_text(json.dumps(context)); self.context_path = p
        r = self.fixture.save_receipt()
        r['input_files'] = [{'path': name, 'sha256': value} for name, value in {**self.edits, **self.readonly}.items()]
        r['input_files'].append({'path': context_name, 'sha256': self.sha(context_name), 'size_bytes': p.stat().st_size})
        r['native_read_file_denied'] = True
        change(r)
        self.receipt_path.write_text(json.dumps(r))
        return r

    def remember(self, scope=None):
        return cache.remember_blocked(self.root, self.directory, scope or self.scope(), self.receipt_path.relative_to(self.root).as_posix())

    def index(self): return self.root / self.directory / (self.scope()['fingerprint'] + '.json')

    def test_real_blocked_no_edits_receipt_suppresses_next_paid_admission_without_failure_fabrication(self):
        scope = self.scope(); self.assertNotIn('failure', scope['identity'])
        self.assertEqual(scope['identity']['proposal'], {'mode': 'repair', 'reason': 'backend_model_decline'})
        record = self.remember()
        with self.assertRaises(cache.CachedBlockedRepair): cache.raise_if_blocked(self.root, self.directory, self.scope())
        self.assertFalse(record['completion_authority']); self.assertFalse(record['work_complete'])
        self.assertFalse((self.root / cache.RUNTIME / 'state').exists())

    def test_missing_new_edit_target_is_bound_as_absent_and_becoming_present_requalifies(self):
        self.task['edit_paths'] = [*self.task['edit_paths'], 'new_sdk.py']; self.edits['new_sdk.py'] = None
        self.save_receipt(); self.remember()
        (self.root / 'new_sdk.py').write_text('# newly implemented SDK\n')
        with self.assertRaises(cache.BlockedCacheError): self.scope()
        fresh = self.scope(edit_hashes={**self.edits, 'new_sdk.py': self.sha('new_sdk.py')})
        self.assertIsNone(cache.raise_if_blocked(self.root, self.directory, fresh))

    def test_source_context_and_route_changes_allow_a_new_scoped_admission(self):
        self.remember(); old = self.scope()
        (self.root / 'compiler.py').write_text('# real context fix\n')
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, old)
        fresh = self.scope(readonly_hashes={**self.readonly, 'compiler.py': self.sha('compiler.py')})
        self.assertIsNone(cache.raise_if_blocked(self.root, self.directory, fresh))
        route = {**self.route, 'maxOutputTokens': 8000}
        fresh_route = self.scope(route=route, readonly_hashes={**self.readonly, 'compiler.py': self.sha('compiler.py')})
        self.assertNotEqual(fresh['fingerprint'], fresh_route['fingerprint'])

    def test_unrelated_global_task_and_board_status_changes_cannot_renew_paid_eligibility(self):
        before = self.scope(); self.remember()
        for name in cache.PROPOSAL_METADATA: (self.root / name).write_text('unrelated task completed\n')
        readonly = {name: self.sha(name) for name in self.readonly}
        self.assertEqual(before, self.scope(readonly_hashes=readonly))
        with self.assertRaises(cache.CachedBlockedRepair): cache.raise_if_blocked(self.root, self.directory, self.scope(readonly_hashes=readonly))

    def test_generated_attempt_context_ids_are_excluded_from_fingerprint(self):
        before = self.scope(); self.remember()
        for name in ['model-inputs/new-uuid/context.json', 'model-invocations/new-uuid.json', 'proposal.progress.json']:
            relative = cache.RUNTIME + 'tasks/' + self.task['task_id'] + '/' + name
            p = self.root / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('fresh generated attempt artifact')
            self.assertEqual(before, self.scope(readonly_hashes={**self.readonly, relative: self.sha(relative)}))

    def test_new_generated_context_path_does_not_change_retained_negative_admission(self):
        before = self.scope(); self.remember(); self.save_receipt(suffix='different-uuid')
        self.assertEqual(before, self.scope())
        with self.assertRaises(cache.CachedBlockedRepair): cache.raise_if_blocked(self.root, self.directory, self.scope())

    def test_actual_task_policy_and_declared_context_change_are_new_scopes(self):
        before = self.scope()
        for key, value in [('acceptance', 'Different actual behavior'), ('checks', [['python3', 'gate.py']]),
                           ('dependencies', ['SVF-042']), ('timeout_seconds', 90), ('llm_limits', {'modelContextBytes': 200000})]:
            with self.subTest(field=key): self.assertNotEqual(before['fingerprint'], self.scope(task={**self.task, key: value})['fingerprint'])
        path = self.root / 'additional.py'; path.write_text('new declared API')
        task = {**self.task, 'context_paths': [*self.task['context_paths'], 'additional.py']}
        with self.assertRaises(cache.BlockedCacheError): self.scope(task=task)
        fresh = self.scope(task=task, readonly_hashes={**self.readonly, 'additional.py': self.sha('additional.py')})
        self.assertNotEqual(before['fingerprint'], fresh['fingerprint'])

    def test_all_declared_real_dependencies_are_required_in_the_hash_closure(self):
        with self.assertRaises(cache.BlockedCacheError): self.scope(readonly_hashes={'backend.py': self.sha('backend.py')})
        with self.assertRaises(cache.BlockedCacheError): self.scope(readonly_hashes={})
        with self.assertRaises(cache.BlockedCacheError): self.scope(task={**self.task, 'kind': 'verify'})

    def test_failed_native_or_contract_model_response_never_becomes_negative_cache(self):
        changes = [lambda r: r.update(success=False), lambda r: r['native_observation'].update(exit_code=1),
                   lambda r: r['native_observation'].update(native_grok_error_observed=True),
                   lambda r: r['effective_route'].update(effective_model_name='wrong'),
                   lambda r: r.update(native_read_file_denied=False), lambda r: r.pop('response')]
        for change in changes:
            with self.subTest(change=change):
                self.save_receipt(change)
                with self.assertRaises((cache.BlockedCacheError, adapter.ModelAdapterError, KeyError)): self.remember()
                self.assertFalse(self.index().exists())

    def test_receipt_task_context_must_match_actual_semantic_policy(self):
        scope = self.scope(task={**self.task, 'acceptance': 'another task policy'})
        with self.assertRaisesRegex(cache.BlockedCacheError, 'another task policy'): self.remember(scope)
        self.save_receipt(lambda r: r.update(input_files=[row for row in r['input_files'] if not row['path'].endswith('/context.json')]))
        with self.assertRaisesRegex(cache.BlockedCacheError, 'one admitted task context'): self.remember()

    def test_historical_receipt_cannot_be_rebound_to_changed_context_compiler(self):
        self.save_receipt(lambda r: r.update(input_files=[row for row in r['input_files'] if row['path'] != 'compiler.py']))
        (self.root / 'compiler.py').write_text('# genuinely changed readonly compiler\n')
        fresh = self.scope(readonly_hashes={**self.readonly, 'compiler.py': self.sha('compiler.py')})
        with self.assertRaisesRegex(cache.BlockedCacheError, 'fingerprint'):
            self.remember(fresh)

    def test_changed_retained_context_is_not_accepted_even_after_valid_cache_creation(self):
        self.remember(); self.context_path.write_text('{"task":{}}')
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, self.scope())

    def test_sanitized_cache_retains_context_reference_but_never_copies_its_body(self):
        self.remember(); raw = b''.join(p.read_bytes() for p in (self.root / self.directory).glob('*.json'))
        self.assertIn(b'/context.json', raw); self.assertNotIn(b'CONTEXT_BODY_MUST_NOT_BE_COPIED', raw)

    def test_dangling_index_symlink_fails_closed_before_clean_miss(self):
        p = self.index(); p.parent.mkdir(parents=True); p.symlink_to('missing-index-target')
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, self.scope())

    def test_orphan_receipt_from_interrupted_persistence_cannot_renew_paid_admission(self):
        self.remember(); self.index().unlink()
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, self.scope())

    def test_dangling_orphan_receipt_also_fails_closed(self):
        p = self.index().with_name(self.scope()['fingerprint'] + '.receipt.json')
        p.parent.mkdir(parents=True); p.symlink_to('missing-copy')
        with self.assertRaises(cache.BlockedCacheError): cache.raise_if_blocked(self.root, self.directory, self.scope())

    def test_controlled_runtime_fixture_change_is_a_real_readonly_input_change(self):
        relative = cache.RUNTIME + 'backends/fixtures/actual.json'; p = self.root / relative
        p.parent.mkdir(parents=True); p.write_text('{"cid":"old"}')
        old = self.scope(readonly_hashes={**self.readonly, relative: self.sha(relative)})
        p.write_text('{"cid":"new"}')
        new = self.scope(readonly_hashes={**self.readonly, relative: self.sha(relative)})
        self.assertNotEqual(old['fingerprint'], new['fingerprint'])


if __name__ == '__main__': unittest.main()
