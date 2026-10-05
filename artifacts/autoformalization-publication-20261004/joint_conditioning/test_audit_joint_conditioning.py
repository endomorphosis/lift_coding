"""Risk fixtures for independent conditioning joins and matrix auditing."""
import copy
import importlib.util
import math
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).with_name('audit_joint_conditioning.py')
SPEC = importlib.util.spec_from_file_location('independent_conditioning_audit_fixture', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
replay, public = audit.support()


def endpoints():
    ids = ['source-' + str(index) for index in range(32)]
    rows = {identity: {'endpoints': {'raw_source': [index + 0.25] * 768,
                'pca_reconstructed': [index + 0.5] * 768, 'new_reconstructed': [index + 0.75] * 768}}
            for index, identity in enumerate(ids)}
    return ids, rows


def heads():
    return {'modality': [3.0, 1.0, 0.0], 'presence': [[1.0, 0.0] for _ in range(4)],
            'start': [[10.0, 0.0], [0.0, 10.0]] + [[0.0, 0.0] for _ in range(4)],
            'end': [[10.0, 0.0], [0.0, 10.0]] + [[0.0, 0.0] for _ in range(4)]}


def pair_and_bank():
    score = {'id': 'fixture-id', 'seed': 1729, 'split': 'train', 'heads': heads(),
             'source_text': 'Alice acts', 'tokens': replay.tokens('Alice acts')}
    fixed = replay.decisions(score['heads'])
    search, diagnostics = replay.replay(score['heads'], fixed['present'])
    diagnostics.update(token_count=2, candidates_per_facet=16, beam_width=64,
        confidence_scope='retained_complete_beam_only', global_optimality_established=False,
        incomplete_search=False, expansion_count_upper_bound=6144, native_head_value_count=24,
        enumerated_span_count_upper_bound=18,
        peak_feasible_expanded_state_count=max(row['feasible_expanded_state_count'] for row in diagnostics['layers']))
    diagnostics.update(dict.fromkeys(('target_access', 'teacher_forcing', 'training_executed',
        'grammar_validation_performed', 'source_fidelity_verified', 'qualified', 'accepted', 'proof_authority'), False))
    search['diagnostics'] = diagnostics
    ir, facets = replay.literal('Alice acts', score['tokens'], fixed, search['selected_spans'])
    pair = {'id': 'fixture-id', 'seed': 1729, 'split': 'train', 'greedy': {
        'status': 'decoded', 'reason': None, 'canonical_ir': copy.deepcopy(ir), 'span_diagnostics': {'facets': {
            field: {'present': facet['present'], 'token_start': facet['token_start'],
                    'token_end_inclusive': facet['token_end_inclusive']} for field, facet in facets.items()}}},
        'joint': {'status': 'proposal', 'reason': None, 'canonical_ir': ir, 'facets': facets,
                  'fixed_decisions': fixed, 'search': search, 'family_syntax_checked': True}}
    return pair, score


class ConditioningAuditFixtures(unittest.TestCase):
    def test_standard_library_only(self):
        self.assertNotIn('torch', sys.modules)
        self.assertNotIn('transformers', sys.modules)
        self.assertNotIn('safetensors', sys.modules)

    def test_selected_independent_source_pin_rejected(self):
        reference = {**audit.REPLAY_BINDING, 'sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'source changed'):
            audit.load_independent(reference, 'bad_selected_independent_source')

    def test_split_rotation_uses_successor_and_retains_recipient_original(self):
        ids, rows = endpoints()
        actual = audit.conditioning('rotated_raw', 0, ids, rows)
        self.assertEqual(actual['original_latent_sha256'], audit.digest(rows[ids[0]]['endpoints']['raw_source'], ascii=True))
        self.assertEqual(actual['effective_latent_sha256'], audit.digest(rows[ids[1]]['endpoints']['raw_source'], ascii=True))
        self.assertEqual(actual['latent_donor_id'], ids[1])
        self.assertEqual(actual['latent_donor_position'], 1)

    def test_rotation_wraps_at_complete_split_boundary(self):
        ids, rows = endpoints()
        actual = audit.conditioning('rotated_raw', 31, ids, rows)
        self.assertEqual(actual['latent_donor_id'], ids[0])
        self.assertEqual(actual['latent_donor_position'], 0)

    def test_rotation_rejects_filtered_denominator(self):
        ids, rows = endpoints()
        with self.assertRaisesRegex(ValueError, 'split32'):
            audit.conditioning('rotated_raw', 0, ids[:-1], rows)

    def test_rotation_rejects_duplicate_id(self):
        ids, rows = endpoints()
        ids[31] = ids[0]
        with self.assertRaises(ValueError):
            audit.conditioning('rotated_raw', 0, ids, rows)

    def test_boolean_position_rejected(self):
        ids, rows = endpoints()
        with self.assertRaises(ValueError):
            audit.conditioning('raw_source', False, ids, rows)

    def test_pca_and_ae_use_distinct_saved_views(self):
        ids, rows = endpoints()
        pca = audit.conditioning('pca_reconstructed', 2, ids, rows)
        ae = audit.conditioning('new_ae_reconstructed', 2, ids, rows)
        self.assertNotEqual(pca['effective_latent_sha256'], ae['effective_latent_sha256'])
        self.assertEqual(pca['effective_latent_sha256'], audit.digest([2.5] * 768, ascii=True))
        self.assertEqual(ae['effective_latent_sha256'], audit.digest([2.75] * 768, ascii=True))

    def test_zero_preserves_original_and_gate_enabled(self):
        ids, rows = endpoints()
        actual = audit.conditioning('zero_raw', 5, ids, rows)
        self.assertEqual(actual['original_latent_sha256'], audit.digest([5.25] * 768, ascii=True))
        self.assertEqual(actual['effective_latent_sha256'], audit.digest([0.0] * 768, ascii=True))
        self.assertTrue(actual['latent_input_enabled'])

    def test_disabled_retains_raw_with_gate_off(self):
        ids, rows = endpoints()
        actual = audit.conditioning('disabled_raw', 5, ids, rows)
        self.assertEqual(actual['original_latent_sha256'], actual['effective_latent_sha256'])
        self.assertFalse(actual['latent_input_enabled'])
        self.assertEqual(actual['latent_donor_id'], ids[5])

    def test_actual_float32_hash_separate_from_original_vector_hash(self):
        ids, rows = endpoints()
        rows[ids[0]]['endpoints']['raw_source'][0] = 1.00000006
        actual = audit.conditioning('raw_source', 0, ids, rows)
        self.assertNotEqual(actual['effective_latent_sha256'], actual['model_latent_float32_sha256'])

    def test_nonfinite_conditioner_rejected(self):
        ids, rows = endpoints()
        rows[ids[0]]['endpoints']['raw_source'][0] = math.inf
        with self.assertRaises(ValueError):
            audit.conditioning('raw_source', 0, ids, rows)

    def test_float32_conditioner_overflow_rejected(self):
        ids, rows = endpoints()
        rows[ids[0]]['endpoints']['raw_source'][0] = 1e50
        with self.assertRaises(ValueError):
            audit.conditioning('raw_source', 0, ids, rows)

    def test_boolean_donor_position_not_integer_zero(self):
        with self.assertRaises(ValueError):
            audit.compare_fields({'latent_donor_position': 0}, {'latent_donor_position': False}, 'wrong donor')

    def test_exact_public_digest_distinguishes_boolean_authority_from_zero(self):
        self.assertNotEqual(audit.digest({'accepted': False}), audit.digest({'accepted': 0}))

    def test_known_joint_proposal_independently_replayed(self):
        row, score = pair_and_bank()
        self.assertTrue(audit.validate_joint(row, score, replay, public))

    def test_ambiguous_fixed_decision_evaluated_without_selector_call(self):
        row, score = pair_and_bank()
        score['heads']['presence'][0] = [0.0, 0.0]
        row['joint'].update(status='abstained', reason='ambiguous_fixed_decision_scores',
                            canonical_ir=None, facets=None, search=None,
                            fixed_decisions=replay.decisions(score['heads']), family_syntax_checked=False)
        self.assertFalse(audit.validate_joint(row, score, replay, public))

    def test_placeholder_grammar_rejection_remains_unaccepted(self):
        row, score = pair_and_bank()
        score['source_text'] = 'todo acts'
        score['tokens'] = replay.tokens(score['source_text'])
        row['joint'].update(status='abstained', reason='joint_generated_ir_rejected',
                            canonical_ir=None, facets=None, family_syntax_checked=False,
                            grammar_error='placeholder rejected by native grammar')
        self.assertTrue(audit.validate_joint(row, score, replay, public))

    def test_altered_source_role_ir_rejected(self):
        row, score = pair_and_bank()
        row['joint']['canonical_ir']['rules'][0]['actor'] = 'wrong actor'
        with self.assertRaisesRegex(ValueError, 'canonical proposal differs'):
            audit.validate_joint(row, score, replay, public)

    def test_altered_span_character_binding_rejected(self):
        row, score = pair_and_bank()
        row['joint']['facets']['actor']['char_end'] = 4
        with self.assertRaises(ValueError):
            audit.validate_joint(row, score, replay, public)

    def test_policy_pruning_counter_tampering_rejected(self):
        row, score = pair_and_bank()
        row['joint']['search']['diagnostics']['attempted_expansion_count'] += 1
        with self.assertRaisesRegex(ValueError, 'search counters'):
            audit.validate_joint(row, score, replay, public)

    def test_qualified_search_rejected(self):
        row, score = pair_and_bank()
        row['joint']['search']['diagnostics']['qualified'] = True
        with self.assertRaisesRegex(ValueError, 'authority'):
            audit.validate_joint(row, score, replay, public)

    def test_fixed_presence_boolean_alias_rejected(self):
        row, score = pair_and_bank()
        row['joint']['fixed_decisions']['present'][0] = 1
        with self.assertRaisesRegex(ValueError, 'fixed native'):
            audit.validate_joint(row, score, replay, public)

    def test_changed_ir_alone_counts_union_without_categorical_change(self):
        row, score = pair_and_bank()
        candidate = copy.deepcopy(row)
        candidate['joint']['canonical_ir']['rules'][0]['actor'] = 'changed actor'
        result = audit.raw_comparison([row], [candidate], [score], [score])
        self.assertEqual(result['changed_counts']['joint_status'], 0)
        self.assertEqual(result['changed_counts']['joint_reason'], 0)
        self.assertEqual(result['changed_counts']['joint_canonical_ir'], 1)
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 1)
        self.assertFalse(result['semantic_improvement_measured'])

    def test_different_scores_do_not_imply_changed_proposal(self):
        row, score = pair_and_bank()
        altered = copy.deepcopy(score)
        altered['heads']['modality'][0] += 1
        result = audit.raw_comparison([row], [row], [score], [altered])
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 0)
        self.assertEqual(result['head_value_diagnostics']['modality']['changed_rows'], 1)
        self.assertEqual(result['head_value_diagnostics']['modality']['changed_scalar_count'], 1)
        self.assertEqual(result['head_value_diagnostics']['modality']['maximum_absolute_difference'], 1)

    def test_mismatched_comparison_identity_rejected(self):
        row, score = pair_and_bank()
        altered = copy.deepcopy(row)
        altered['id'] = 'other'
        with self.assertRaises(ValueError):
            audit.raw_comparison([row], [altered], [score], [score])

    def test_duplicate_comparison_identity_rejected(self):
        row, score = pair_and_bank()
        with self.assertRaises(ValueError):
            audit.raw_comparison([row, row], [row, row], [score, score], [score, score])

    def test_optional_score_definedness_separate_from_score_change(self):
        result = audit.scalar_differences([(None, 1.0), (3.0, 5.0), (7.0, 7.0)])
        self.assertEqual(result['paired_defined_count'], 2)
        self.assertEqual(result['changed_definedness_count'], 1)
        self.assertEqual(result['changed_value_count'], 1)
        self.assertEqual(result['mean_absolute_difference'], 1.0)

    def test_boolean_diagnostic_scalar_rejected(self):
        with self.assertRaises(ValueError):
            audit.scalar_differences([(False, 0.0)])

    def test_public_transport_removes_only_modality_logits(self):
        row, _ = pair_and_bank()
        row['greedy']['span_diagnostics']['modality_logits'] = [1.0, 0.0, -1.0]
        actual = public.public_row(row, 1729, 0)
        self.assertNotIn('modality_logits', actual['greedy']['span_diagnostics'])
        self.assertEqual(actual['joint'], row['joint'])
        self.assertEqual(actual['source_position'], 0)
        self.assertFalse(actual['qualified'])
        public.zero_masks(actual['semantic_masks'])


if __name__ == '__main__':
    unittest.main()
