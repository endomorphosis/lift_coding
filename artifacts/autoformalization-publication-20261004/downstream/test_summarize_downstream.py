"""Pure fixtures for complete, externally pinned downstream scalar audits."""
from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('scalar_downstream_audit',
                                             Path(__file__).with_name('summarize_downstream.py'))
owner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owner)


def receipt(decoded=True):
    rows = []
    for position in range(32):
        backend = {'status': 'decoded', 'reason': None,
                   'canonical_ir': {'rules': [{'modality': 'obligation'}]},
                   'family_syntax_checked': True,
                   'span_diagnostics': {'modality_logits': [1., 2., 3.]}} if decoded else None
        rows.append({'id': 'source:' + str(position), 'position': position,
                     'outcome': 'decoder_proposal' if decoded else 'source_blocked',
                     'submitted_position': position if decoded else None,
                     'preflight': {'outcome': 'unassessed' if decoded else 'unsupported_profile'},
                     'decoder_row': backend})
    result = {'schema': 'canonical-span-decoder-preflight-inference/v1',
              'rows': rows, 'input_count': 32, 'eligible_count': 32 if decoded else 0,
              'submitted_positions': list(range(32)) if decoded else [],
              'decoder_call_count': int(decoded), 'decoder_completion_count': int(decoded),
              'backend_exception_type': None}
    result.update(dict.fromkeys(('target_access', 'teacher_forcing', 'training_executed',
        'context_applied', 'source_fidelity_established', 'qualified', 'proof_authority', 'accepted'), False))
    return result


class ScalarReceiptTests(unittest.TestCase):
    def test_complete_proposals_remain_unaccepted(self):
        result = owner.receipt_scalars(receipt())
        self.assertEqual(result['source_outcomes'], {'decoder_proposal': 32})
        self.assertEqual(result['syntax_valid_unaccepted_proposals'], 32)
        self.assertEqual(result['accepted_artifacts'], 0)
        self.assertFalse(result['semantic_accuracy_measured'])

    def test_all_blocked_counts_are_valid_without_backend(self):
        result = owner.receipt_scalars(receipt(False))
        self.assertEqual(result['requested_rows'], 32)
        self.assertEqual(result['eligible_rows'], 0)
        self.assertEqual(result['decoder_completions'], 0)
        self.assertEqual(result['source_outcomes'], {'source_blocked': 32})

    def test_missing_request_rejects_survivor_only_denominator(self):
        value = receipt()
        value['rows'].pop()
        with self.assertRaisesRegex(ValueError, 'all32'):
            owner.receipt_scalars(value)

    def test_hidden_authority_change_rejects(self):
        value = receipt()
        value['source_fidelity_established'] = True
        with self.assertRaisesRegex(ValueError, 'authority'):
            owner.receipt_scalars(value)

    def test_boolean_count_rejects(self):
        value = receipt()
        value['decoder_call_count'] = True
        with self.assertRaisesRegex(ValueError, 'exact integer'):
            owner.receipt_scalars(value)

    def test_comparison_separates_ir_change_from_logit_change(self):
        baseline, changed = receipt(), receipt()
        changed['rows'][0]['decoder_row']['canonical_ir']['rules'][0]['modality'] = 'permission'
        changed['rows'][1]['decoder_row']['span_diagnostics']['modality_logits'][0] = 1.5
        result = owner.comparisons(baseline, changed)
        self.assertEqual(result['changed_counts']['canonical_ir'], 1)
        self.assertEqual(result['changed_counts']['status'], 0)
        self.assertEqual(result['max_abs_modality_logit_difference'], .5)
        self.assertFalse(result['semantic_improvement_measured'])

    def test_unmeasured_logits_stay_none_instead_of_zero(self):
        blocked = receipt(False)
        result = owner.comparisons(blocked, blocked)
        self.assertIsNone(result['max_abs_modality_logit_difference'])
        self.assertEqual(result['modality_logit_comparison_rows'], 0)
        self.assertEqual(owner.stats([None, None, None])['defined_seeds'], 0)

    def test_comparison_identity_mismatch_rejects(self):
        baseline, changed = receipt(), receipt()
        changed['rows'][0]['id'] = 'different-source'
        with self.assertRaisesRegex(ValueError, 'matched request'):
            owner.comparisons(baseline, changed)

    def test_grouped_reason_counts_include_absent_seed_as_zero(self):
        result = owner.grouped_counts([{'overlap': 32}, {}, {'overlap': 16}])
        self.assertEqual(result['overlap']['seed_values'], [32, 0, 16])
        self.assertEqual(result['overlap']['mean'], 16)


class ExternalPinTests(unittest.TestCase):
    def test_resealed_source_change_still_rejects_external_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'pinned.json'
            value = {'status': 'first'}
            path.write_bytes(owner.raw({**value, 'content_sha256': owner.digest(value)}))
            selected = owner.binding(path)
            changed = {'status': 'different'}
            path.write_bytes(owner.raw({**changed, 'content_sha256': owner.digest(changed)}))
            with self.assertRaisesRegex(ValueError, 'external file binding'):
                owner.Capture().json(selected)

    def test_duplicate_or_nonfinite_json_rejects(self):
        for data in (b'{"status":1,"status":2}', b'{"count":NaN}'):
            with self.assertRaises(ValueError):
                owner.strict_json(data)

    def test_missing_third_seed_rejects_before_batch_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'
            value = {'schema': 'frozen-downstream-summary-selection/v1',
                     'reports': [{'seed': 1729}, {'seed': 1730}],
                     'batch_binding': {}, 'protocol_design_binding': {}}
            path.write_bytes(owner.raw({**value, 'content_sha256': owner.digest(value)}))
            with self.assertRaisesRegex(ValueError, 'all three'):
                owner.summarize(owner.binding(path))

    def test_conflicting_binding_rejects_after_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.txt'
            path.write_bytes(b'fixture')
            selected = owner.binding(path)
            capture = owner.Capture()
            capture.get(selected)
            conflict = copy.deepcopy(selected)
            conflict['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'conflicting'):
                capture.get(conflict)


if __name__ == '__main__':
    unittest.main()
