"""Pure fixtures for metric conflation, capture lineage and public redaction.

No campaign files, model providers, targets, network or provers are opened.
"""
from __future__ import annotations

import copy
import importlib.util
import math
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'conditioning_summary_fixture', Path(__file__).with_name('summarize_joint_conditioning.py'))
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


def fixture():
    row = {'id': 'fixture-id', 'seed': 1729, 'split': 'train', 'control': 'raw_source',
           'source_sha256': '0' * 64, 'source_text': 'Fixture source',
           'latent_sha256': '1' * 64, 'score_row_sha256': '2' * 64,
           'original_latent_sha256': '3' * 64, 'effective_latent_sha256': '1' * 64,
           'latent_donor_id': 'fixture-id', 'latent_donor_position': 0,
           'latent_input_enabled': True, 'latent_ablation': 'none',
           'model_latent_float32_sha256': '4' * 64,
           'conditioning_profile': {'id': 'fixture-profile'},
           'control_transformation_scope': 'complete_within_split32_before_preflight',
           'accepted': False, 'source_fidelity_established': False,
           'independent_semantic_review_completed': False, 'proof_authority': False,
           'greedy': {'status': 'abstained', 'reason': 'copied_spans_overlap', 'canonical_ir': None,
                      'span_diagnostics': {'modality_logits': [1.0, 0.0, -1.0], 'facets': {
                          'actor': {'present': True, 'token_start': 0, 'token_end_inclusive': 0}}}},
           'joint': {'status': 'proposal', 'reason': None, 'canonical_ir': {'rules': [{'actor': 'Fixture'}]},
                     'fixed_decisions': {'modality': 'O', 'present': [True, True, False, False, False, False],
                         'ambiguous': False, 'margins': dict.fromkeys(
                             ('modality', 'object', 'conditions', 'exceptions', 'temporal'), 1.0)},
                     'search': {'selected_spans': [[0, 0], [1, 1], None, None, None, None],
                         'status': 'selected', 'reason': None, 'best_score': 2.0,
                         'runner_up_score': 1.0, 'joint_score_margin': 1.0,
                         'diagnostics': {'incomplete_search': True, 'pruned_candidate_count': 1,
                             'pruned_beam_state_count': 2, 'attempted_expansion_count': 3,
                             'overlap_rejected_expansion_count': 1, 'complete_retained_state_count': 1}}}}
    heads = {'heads': {'start': [[1.0, 2.0]] * 6, 'end': [[2.0, 3.0]] * 6,
                       'presence': [[1.0, 0.0]] * 4, 'modality': [1.0, 0.0, -1.0]}}
    return row, heads


class ComparisonFixtures(unittest.TestCase):
    def setUp(self):
        self.row, self.bank = fixture()

    def compare(self, row=None, bank=None):
        return summary.compare_rows([self.row], [row or copy.deepcopy(self.row)],
                                    [self.bank], [bank or copy.deepcopy(self.bank)])

    def test_score_change_does_not_count_as_ir_status_or_reason_change(self):
        row, bank = copy.deepcopy(self.row), copy.deepcopy(self.bank)
        bank['heads']['modality'][0] += 0.01
        row['joint']['search']['best_score'] += 0.1
        row['joint']['fixed_decisions']['margins']['modality'] += 0.01
        result = self.compare(row, bank)
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 0)
        self.assertEqual(result['changed_counts']['greedy_status_reason_ir'], 0)
        self.assertEqual(result['changed_counts']['fixed_modality'], 0)
        self.assertEqual(result['head_value_diagnostics']['modality']['changed_rows'], 1)
        self.assertEqual(result['joint_search_score_diagnostics']['best_score']['changed_value_count'], 1)
        self.assertFalse(result['semantic_improvement_measured'])

    def test_ir_only_change_counts_union_without_status_change(self):
        row = copy.deepcopy(self.row)
        row['joint']['canonical_ir']['rules'][0]['actor'] = 'Changed'
        result = self.compare(row)
        self.assertEqual(result['changed_counts']['joint_status'], 0)
        self.assertEqual(result['changed_counts']['joint_reason'], 0)
        self.assertEqual(result['changed_counts']['joint_canonical_ir'], 1)
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 1)

    def test_changed_presence_and_interval_are_separate(self):
        row = copy.deepcopy(self.row)
        row['joint']['fixed_decisions']['present'][2] = True
        row['joint']['search']['selected_spans'][2] = [2, 2]
        result = self.compare(row)
        self.assertEqual(result['changed_counts']['fixed_presence'], 1)
        self.assertEqual(result['changed_presence_by_facet']['object'], 1)
        self.assertEqual(result['changed_joint_selected_interval_by_facet']['object'], 1)
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 0)

    def test_missing_search_records_definedness_without_numeric_zero(self):
        row = copy.deepcopy(self.row)
        row['joint']['search'] = None
        row['joint']['status'] = 'abstained'
        row['joint']['reason'] = 'ambiguous_fixed_decision_scores'
        row['joint']['canonical_ir'] = None
        row['joint']['fixed_decisions']['ambiguous'] = True
        row['joint']['fixed_decisions']['margins']['modality'] = 0.0
        result = self.compare(row)
        score = result['joint_search_score_diagnostics']['best_score']
        self.assertEqual(score['changed_definedness_count'], 1)
        self.assertEqual(score['paired_defined_count'], 0)
        self.assertIsNone(score['maximum_absolute_difference'])
        self.assertEqual(result['changed_counts']['joint_search_presence'], 1)
        self.assertEqual(result['changed_counts']['joint_status_reason_ir'], 1)
        self.assertEqual(result['changed_counts']['fixed_ambiguity'], 1)
        self.assertFalse(result['semantic_improvement_measured'])

    def test_misaligned_source_id_is_rejected(self):
        row = copy.deepcopy(self.row)
        row['id'] = 'other'
        with self.assertRaises(ValueError):
            self.compare(row)

    def test_boolean_score_is_rejected(self):
        bank = copy.deepcopy(self.bank)
        bank['heads']['modality'][0] = True
        with self.assertRaises(ValueError):
            self.compare(bank=bank)

    def test_nonfinite_score_is_rejected(self):
        bank = copy.deepcopy(self.bank)
        bank['heads']['modality'][0] = math.inf
        with self.assertRaises(ValueError):
            self.compare(bank=bank)

    def test_unequal_head_array_size_is_rejected(self):
        bank = copy.deepcopy(self.bank)
        bank['heads']['modality'].pop()
        with self.assertRaises(ValueError):
            self.compare(bank=bank)

    def test_control_metadata_and_record_digest_do_not_imply_head_difference(self):
        row = copy.deepcopy(self.row)
        row['control'] = 'rotated_raw'
        row['score_row_sha256'] = 'f' * 64
        result = self.compare(row)
        self.assertTrue(all(value == 0 for value in result['changed_counts'].values()))
        self.assertTrue(all(value['changed_rows'] == 0 for value in result['head_value_diagnostics'].values()))


class PublicationAndLineageFixtures(unittest.TestCase):
    def test_public_row_preserves_donor_gate_hashes_but_removes_full_logits(self):
        row, _ = fixture()
        before = copy.deepcopy(row)
        row['latent_donor_id'] = 'successor-id'
        row['latent_donor_position'] = 1
        row['latent_input_enabled'] = False
        result = summary.public_row(row, 1729, 0)
        self.assertNotIn('modality_logits', result['greedy']['span_diagnostics'])
        self.assertIn('modality_logits', row['greedy']['span_diagnostics'])
        self.assertEqual(result['latent_donor_id'], 'successor-id')
        self.assertEqual(result['latent_donor_position'], 1)
        self.assertFalse(result['latent_input_enabled'])
        self.assertEqual(result['effective_latent_sha256'], before['effective_latent_sha256'])
        self.assertTrue(all(type(v) is int and v == 0 for v in result['semantic_masks'].values()))
        self.assertFalse(result['accepted'])
        self.assertFalse(result['qualified'])

    def test_new_capture_digest_is_allowed_when_old_outcomes_are_exact(self):
        previous, _ = fixture()
        current = copy.deepcopy(previous)
        current['score_row_sha256'] = 'f' * 64
        summary.match_previous_raw_joint(previous, current)

    def test_changed_previous_joint_search_is_rejected(self):
        previous, _ = fixture()
        current = copy.deepcopy(previous)
        current['joint']['search']['best_score'] += 1.0
        with self.assertRaises(ValueError):
            summary.match_previous_raw_joint(previous, current)

    def test_changed_previous_conditioner_hash_is_rejected(self):
        previous, _ = fixture()
        current = copy.deepcopy(previous)
        current['latent_sha256'] = 'f' * 64
        with self.assertRaises(ValueError):
            summary.match_previous_raw_joint(previous, current)


if __name__ == '__main__':
    unittest.main()
