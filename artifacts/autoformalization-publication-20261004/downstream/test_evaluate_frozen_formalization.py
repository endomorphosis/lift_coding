"""Pure fixtures for frozen downstream joins, controls and honest accounting."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name('evaluate_frozen_formalization.py')
SPEC = importlib.util.spec_from_file_location('frozen_downstream_fixture_owner', MODULE_PATH)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def sealed(value):
    return {**value, 'content_sha256': worker.digest(value)}


def sources():
    source_rows, meta_rows = [], []
    for n in range(64):
        text = 'The clerk must notify applicant number ' + str(n) + '.'
        input_value = {'source_text': text, 'context': {'role': 'none_required', 'text': '',
            'bindings': {}, 'sha256': hashlib.sha256(b'').hexdigest()}}
        input_sha = worker.digest(input_value)
        source_sha = hashlib.sha256(text.encode()).hexdigest()
        split = 'train' if n < 32 else 'development'
        row = {'id': 'sha256:' + input_sha, 'input': input_value, 'input_sha256': input_sha,
               'source_sha256': source_sha, 'group_id': 'group:' + str(n // 4),
               'split': split, 'review_item_id': 'authored:' + str(n)}
        meta = {k: row[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')}
        meta['context_role'] = 'none_required'
        source_rows.append(row)
        meta_rows.append(meta)
    inputs = sealed({'schema': 'source-only-authored-expansion-inputs/v1', 'rows': source_rows,
        'row_count': 64, 'input_recipe': 'exact_source_only/v1', 'policy': copy.deepcopy(worker.SOURCE_POLICY),
        'contains_formal_targets': False})
    cohort = sealed({'schema': 'source-only-authored-expansion-cohort/v1', 'rows': meta_rows,
        'contains_formal_targets': False, 'policy': copy.deepcopy(worker.SOURCE_POLICY)})
    return inputs, cohort


def row_receipt(identity, *, decoded=True, logits=(1., 2., 3.), ir=None):
    backend = {'status': 'decoded' if decoded else 'abstained',
               'reason': None if decoded else 'copied_spans_overlap',
               'canonical_ir': {'rules': []} if ir is None and decoded else ir,
               'span_diagnostics': {'modality_logits': list(logits)},
               'family_syntax_checked': decoded}
    return {'id': identity, 'outcome': 'decoder_proposal' if decoded else 'decoder_abstained',
            'preflight': {'outcome': 'unassessed'}, 'decoder_row': backend}


def endpoint_fixture(metadata):
    ref = {'path': '/tmp/frozen_fixture.json', 'bytes': 1, 'sha256': '1' * 64}
    pca = {'fit_rows': 32, 'development_rows_read_before_fit': 0, 'retained_axes': 31}
    rows = []
    vectors = []
    for n, meta in enumerate(metadata):
        values = [float(n)] * 768
        vectors.append(values)
        row = {k: meta[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'context_role')}
        row.update(panel_input_sha256=meta['input_sha256'], lane_input_sha256=meta['input_sha256'],
                   endpoints={view: [float(n)] * (64 if view in ('new_latent', 'old_latent') else
                              31 if view == 'pca_latent' else 768) for view in worker.VIEWS})
        rows.append(row)
    endpoints = sealed({'schema': 'source-only-expanded-reconstruction-endpoints/v1', 'lane_id': 'native768',
        'seed': 1729, 'architecture': [768, 128, 64], 'source_profile_sha256': worker.PROFILE_SHA,
        'native_train_bundle_binding': ref, 'native_development_bundle_binding': ref,
        'new_checkpoint_binding': ref, 'new_training_report_binding': ref, 'old_checkpoint_binding': ref,
        'pca_control': pca, 'rows': rows, 'model_inference_executed': True, 'optimizer_updates': 0,
        'semantic_relevance_measured': False})
    numeric = sealed({'schema': 'source-only-expanded-reconstruction-numeric-report/v1', 'lane_id': 'native768',
        'seed': 1729, 'architecture': [768, 128, 64], 'endpoint_binding': ref,
        'new_checkpoint_binding': ref, 'new_training_report_binding': ref, 'old_checkpoint_binding': ref,
        'pca_control': pca, 'optimizer_updates': 0, 'masks': dict.fromkeys(worker.MASKS, 0),
        'independent_semantic_accuracy_measured': False, 'qualified': False, 'proof_authority': False})
    arm = {'seed': 1729, 'endpoints_binding': ref}
    return endpoints, numeric, arm, vectors


class FrozenControlTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.cohort = sources()
        self.requests, self.metadata = worker.validate_sources(self.inputs, self.cohort)
        self.rows = [{'endpoints': {'raw_source': [float(n)] * 768,
            'pca_reconstructed': [float(n + 100)] * 768,
            'new_reconstructed': [float(n + 200)] * 768}} for n in range(64)]

    def test_all_source_identities_join_without_labels(self):
        self.assertEqual(len(self.requests), 64)
        self.assertTrue(all(not r['requires_context_resolution'] for r in self.requests))

    def test_target_admission_rejected_even_resealed(self):
        self.inputs['contains_formal_targets'] = True
        self.inputs = sealed({k: v for k, v in self.inputs.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'source-only policy'):
            worker.validate_sources(self.inputs, self.cohort)

    def test_semantic_mask_admission_rejected_even_resealed(self):
        self.cohort['policy']['semantic_masks']['weak_decoder_fit'] = 1
        self.cohort = sealed({k: v for k, v in self.cohort.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'source-only policy'):
            worker.validate_sources(self.inputs, self.cohort)

    def test_exact_source_hash_rejected(self):
        self.inputs['rows'][0]['input']['source_text'] += ' Changed.'
        self.inputs = sealed({k: v for k, v in self.inputs.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'identity/hash'):
            worker.validate_sources(self.inputs, self.cohort)

    def test_group_leakage_rejected(self):
        # Preserve four variants while transplanting a complete TRAIN group into DEV.
        for n in range(32, 36):
            for obj in (self.inputs, self.cohort):
                obj['rows'][n]['group_id'] = 'group:0'
        self.inputs = sealed({k: v for k, v in self.inputs.items() if k != 'content_sha256'})
        self.cohort = sealed({k: v for k, v in self.cohort.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'split overlap'):
            worker.validate_sources(self.inputs, self.cohort)

    def test_context_is_not_silently_applied(self):
        self.inputs['rows'][0]['input']['context']['text'] = 'Assume a holiday.'
        self.inputs = sealed({k: v for k, v in self.inputs.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'source-only context'):
            worker.validate_sources(self.inputs, self.cohort)

    def test_frozen_reconstruction_views_selected_without_refit(self):
        for name, value in [('raw_source', 0.), ('pca_reconstructed', 100.), ('new_ae_reconstructed', 200.)]:
            panel, vectors, control = worker.prepare_arm(self.rows, self.metadata, self.requests, name, 'train')
            self.assertEqual(len(panel), 32)
            self.assertEqual(vectors[0][0], value)
            self.assertEqual(control, 'none')

    def test_rotation_receives_full_development_panel_before_filter(self):
        panel, vectors, control = worker.prepare_arm(self.rows, self.metadata, self.requests, 'rotated_raw', 'development')
        self.assertEqual(control, 'rotate')
        self.assertEqual([r['id'] for r in panel], [r['id'] for r in self.requests[32:]])
        self.assertEqual([v[0] for v in vectors], list(map(float, range(32, 64))))
        self.assertNotIn(self.requests[0]['id'], [r['id'] for r in panel])

    def test_zero_and_disabled_are_distinct_wrapper_controls(self):
        self.assertEqual(worker.prepare_arm(self.rows, self.metadata, self.requests, 'zero_raw', 'train')[2], 'zero')
        self.assertEqual(worker.prepare_arm(self.rows, self.metadata, self.requests, 'disabled_raw', 'train')[2], 'disabled')

    def test_prepare_controls_does_not_mutate_saved_endpoints(self):
        before = copy.deepcopy(self.rows)
        _, vectors, _ = worker.prepare_arm(self.rows, self.metadata, self.requests, 'raw_source', 'train')
        vectors[0][0] = 999.
        self.assertEqual(self.rows, before)

    def test_endpoint_order_joins_by_id_for_interleaved_source_splits(self):
        endpoints, numeric, arm, vectors = endpoint_fixture(self.metadata)
        order = [position for n in range(32) for position in (n, n + 32)]
        interleaved_meta = [self.metadata[n] for n in order]
        interleaved_vectors = [vectors[n] for n in order]
        aligned = worker.validate_endpoints(endpoints, numeric, arm, interleaved_meta, interleaved_vectors)
        self.assertEqual([row['id'] for row in aligned], [row['id'] for row in interleaved_meta])
        aligned_requests = [self.requests[n] for n in order]
        panel, values, control = worker.prepare_arm(aligned, interleaved_meta, aligned_requests, 'rotated_raw', 'development')
        self.assertEqual(control, 'rotate')
        self.assertEqual([value[0] for value in values], list(map(float, range(32, 64))))
        self.assertEqual([row['id'] for row in panel], [row['id'] for row in self.requests[32:]])

    def test_duplicate_endpoint_ids_rejected_even_resealed(self):
        endpoints, numeric, arm, vectors = endpoint_fixture(self.metadata)
        endpoints['rows'][1] = copy.deepcopy(endpoints['rows'][0])
        endpoints = sealed({k: v for k, v in endpoints.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'unique endpoint identities'):
            worker.validate_endpoints(endpoints, numeric, arm, self.metadata, vectors)

    def test_false_is_not_an_integer_zero_semantic_mask(self):
        endpoints, numeric, arm, vectors = endpoint_fixture(self.metadata)
        numeric['masks']['weak_decoder_fit'] = False
        numeric = sealed({k: v for k, v in numeric.items() if k != 'content_sha256'})
        with self.assertRaisesRegex(ValueError, 'numeric evidence scope'):
            worker.validate_endpoints(endpoints, numeric, arm, self.metadata, vectors)


class ComparisonTests(unittest.TestCase):
    def test_logit_changes_do_not_imply_ir_changes(self):
        left = {'rows': [row_receipt('a')]}
        right = {'rows': [row_receipt('a', logits=(1.5, 2., 2.5))]}
        result = worker.compare_receipts(left, right)
        self.assertEqual(result['changed_counts']['status_reason_ir'], 0)
        self.assertEqual(result['max_abs_modality_logit_difference'], .5)
        self.assertFalse(result['semantic_improvement_measured'])

    def test_actual_ir_and_status_changes_count_separately(self):
        left = {'rows': [row_receipt('a'), row_receipt('b')]}
        right = {'rows': [row_receipt('a', ir={'rules': [{'modality': 'F'}]}), row_receipt('b', decoded=False)]}
        result = worker.compare_receipts(left, right)
        self.assertEqual(result['changed_counts']['canonical_ir'], 2)
        self.assertEqual(result['changed_counts']['status'], 1)
        self.assertEqual(result['changed_counts']['status_reason_ir'], 2)

    def test_blocked_rows_retained_and_no_numerical_denominator_invented(self):
        row = {'id': 'blocked', 'outcome': 'source_blocked', 'preflight': {'outcome': 'unsupported'}, 'decoder_row': None}
        result = worker.compare_receipts({'rows': [row]}, {'rows': [copy.deepcopy(row)]})
        self.assertEqual(result['requested_rows'], 1)
        self.assertEqual(result['modality_logit_comparison_rows'], 0)
        self.assertIsNone(result['max_abs_modality_logit_difference'])

    def test_reordered_identity_comparison_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identities'):
            worker.compare_receipts({'rows': [row_receipt('a')]}, {'rows': [row_receipt('b')]})

    def test_zeroeligible_summary_preserves_requests_and_zero_calls(self):
        row = {'id': 'blocked', 'outcome': 'source_blocked', 'preflight': {'outcome': 'unsupported'}, 'decoder_row': None}
        receipt = {'rows': [row], 'eligible_count': 0, 'decoder_call_count': 0,
                   'decoder_completion_count': 0, 'backend_exception_type': None}
        result = worker.receipt_summary(receipt)
        self.assertEqual(result['requested_rows'], 1)
        self.assertEqual(result['decoder_calls'], 0)
        self.assertEqual(result['syntax_valid_unaccepted_proposals'], 0)
        self.assertEqual(result['accepted_artifacts'], 0)


class FileIntegrityTests(unittest.TestCase):
    def test_duplicate_and_nonfinite_json_rejected(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError):
                worker.strict_json(data)

    def test_capture_recheck_rejects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.json'
            path.write_text('{"a":1}')
            capture = worker.Capture()
            capture.get(worker.binding(path))
            path.write_text('{"a":2}')
            with self.assertRaisesRegex(ValueError, 'changed during execution'):
                capture.recheck()

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'input.json'
            target.write_text('{}')
            symlink = Path(tmp) / 'link.json'
            symlink.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'nonsymlink'):
                worker.binding(symlink)

    def test_external_file_pin_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'input.json'
            target.write_text('{}')
            ref = worker.binding(target)
            ref['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'external file pin'):
                worker.Capture().get(ref)

    def test_output_is_sealed_private_and_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'receipt.json'
            worker.write(target, {'status': 'fixture_only'})
            worker.seal_check(json.loads(target.read_text()))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                worker.write(target, {'status': 'overwrite_forbidden'})

    def test_existing_wrapper_receipt_seal_preserved_in_saved_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = sealed({'schema': 'pure_wrapper_fixture/v1', 'rows': []})
            path = Path(tmp) / 'wrapper.json'
            worker.write(path, original)
            saved = json.loads(path.read_text())
            self.assertEqual(saved, original)
            worker.seal_check(saved)

    def test_invalid_existing_receipt_seal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'JSON seal'):
                worker.write(Path(tmp) / 'wrapper.json', {'status': 'fixture', 'content_sha256': '0' * 64})


class PlanTests(unittest.TestCase):
    def setUp(self):
        ref = {'path': '/tmp/selected.py', 'bytes': 1, 'sha256': '1' * 64}
        self.self_binding = ref
        self.plan = {'schema': 'source-only-frozen-downstream-span-plan/v1', 'helper_binding': ref,
            'bootstrap_binding': {**ref, 'sha256': worker.BOOTSTRAP_SHA},
            'canonical_module_bindings': [{'module': name, 'binding': {**ref,
                'path': str(worker.REPOSITORY / Path(*name.split('.')).with_suffix('.py'))}} for name in worker.MODULES],
            'cohort_binding': ref, 'source_inputs_binding': ref, 'encoding_report_binding': ref,
            'arms': [{'seed': seed, 'checkpoint_binding': ref, 'endpoints_binding': ref,
                      'numeric_report_binding': ref} for seed in worker.SEEDS],
            'controls': list(worker.CONTROLS), 'authorization_scope': copy.deepcopy(worker.AUTHORIZATION),
            'resource_limits': copy.deepcopy(worker.LIMITS)}

    def test_closed_frozen_plan_accepted(self):
        worker.validate_plan(sealed(self.plan), self.self_binding)

    def test_unknown_formal_target_binding_rejected(self):
        self.plan['formal_target_binding'] = self.self_binding
        with self.assertRaisesRegex(ValueError, 'closed downstream plan'):
            worker.validate_plan(sealed(self.plan), self.self_binding)

    def test_larger_resource_or_missing_control_rejected(self):
        self.plan['resource_limits']['address_space_bytes'] *= 2
        with self.assertRaisesRegex(ValueError, 'bounded source-only'):
            worker.validate_plan(sealed(self.plan), self.self_binding)

    def test_dev_seed_selection_rejected(self):
        self.plan['arms'] = self.plan['arms'][:1]
        with self.assertRaisesRegex(ValueError, 'three fixed seeds'):
            worker.validate_plan(sealed(self.plan), self.self_binding)


if __name__ == '__main__':
    unittest.main()
