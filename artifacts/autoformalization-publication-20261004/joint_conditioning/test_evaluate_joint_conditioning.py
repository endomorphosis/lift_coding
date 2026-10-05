"""Pure fixtures for effective conditioner and historical outcome joins.

No model, checkpoint, campaign vectors, numerical provider, network or prover
is loaded. These tests establish transport integrity, never source fidelity.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import types
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'joint_conditioning_worker_fixture', Path(__file__).with_name('evaluate_joint_conditioning.py'))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def raw(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=ascii,
                      allow_nan=False).encode()


def digest(value, *, ascii=False):
    return hashlib.sha256(raw(value, ascii=ascii)).hexdigest()


def closed(value, keys, label):
    worker.require(type(value) is dict and set(value) == set(keys), 'closed ' + label + ' required')


def seal(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def seal_check(value):
    worker.require(value['content_sha256'] == digest({k: v for k, v in value.items() if k != 'content_sha256'}),
                   'fixture seal differs')


MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
HELPER = types.SimpleNamespace(closed=closed, seal_check=seal_check, raw=raw, MASKS=MASKS,
                               LIMITS={'cpu_threads': 1})
FROZEN = types.SimpleNamespace(POLICY={'candidates_per_facet': 16, 'beam_width': 64})
BINDING = {'path': '/fixture', 'bytes': 1, 'sha256': 'a' * 64}


def fixture_plan():
    return seal({'schema': 'source-only-joint-conditioning-plan/v1', 'helper_binding': BINDING,
        'baseline_helper_binding': {**BINDING, 'sha256': worker.BASELINE_HELPER_SHA},
        'baseline_plan_binding': BINDING,
        'frozen_joint_helper_binding': {**BINDING, 'sha256': worker.FROZEN_JOINT_HELPER_SHA},
        'selector_binding': {**BINDING, 'sha256': worker.SELECTOR_SHA}, 'protocol_binding': BINDING,
        'summary_baseline_helper_binding': {**BINDING, 'sha256': worker.SUMMARY_BASELINE_HELPER_SHA},
        'baseline_receipts': [{'seed': seed, 'arms': {control: {'train_binding': BINDING,
            'development_binding': BINDING} for control in worker.CONTROLS}} for seed in worker.SEEDS],
        'baseline_joint_ledgers': [{'seed': seed, 'ledger_binding': BINDING} for seed in worker.SEEDS],
        'controls': list(worker.CONTROLS), 'policy': FROZEN.POLICY, 'resource_limits': HELPER.LIMITS,
        'semantic_masks': dict.fromkeys(MASKS, 0)})


def conditioning_fixture(control):
    panel = [{'id': 'source-' + str(n), 'source_text': 'Café ' + str(n)} for n in range(32)]
    vectors = [[float(n + 1)] * 768 for n in range(32)]
    ablation = {'zero_raw': 'zero', 'disabled_raw': 'disabled', 'rotated_raw': 'rotate'}.get(control, 'none')
    rows = []
    for position in range(32):
        donor = (position + 1) % 32 if control == 'rotated_raw' else position
        vector = [0.0] * 768 if control == 'zero_raw' else vectors[donor]
        enabled = control != 'disabled_raw'
        rows.append({'id': panel[position]['id'], 'position': position, 'submitted_position': position,
            'preflight': {'outcome': 'unassessed'}, 'encoding': {'outcome': 'admitted'},
            'original_latent_sha256': digest(vectors[position], ascii=True),
            'effective_latent_sha256': digest(vector, ascii=True),
            'latent_donor_id': panel[donor]['id'], 'latent_donor_position': donor,
            'latent_input_enabled': enabled,
            'decoder_row': {'latent_sha256': digest(vector, ascii=True), 'latent_input_enabled': enabled}})
    record = {'rows': rows, 'eligible_count': 32, 'submitted_positions': list(range(32)),
              'backend_exception_type': None, 'requested_control': ablation,
              'owner_control': 'disabled' if control == 'disabled_raw' else 'none'}
    return panel, vectors, record


def previous_row(n):
    return {'id': 'source-' + str(n), 'split': 'train' if n < 32 else 'development',
            'source_sha256': 'a' * 64, 'latent_sha256': 'b' * 64, 'score_row_sha256': 'c' * 64,
            'source_text': 'Café owners must notify clients.',
            'greedy': {'status': 'abstained', 'reason': 'copied_spans_overlap'},
            'joint': {'status': 'proposal', 'reason': None, 'canonical_ir': {'rules': [{'actor': 'Café owners'}]},
                      'facets': {'actor': {'token_start': 0}}, 'search': {'score': 1.0},
                      'fixed_decisions': {'modality': 'O'}, 'family_syntax_checked': True},
            'accepted': False, 'source_fidelity_established': False,
            'independent_semantic_review_completed': False, 'proof_authority': False}


def previous_ledger():
    return {'schema': 'source-only-joint-span-proposal-ledger/v1', 'seed': 1729,
            'rows': [previous_row(n) for n in range(64)], 'semantic_accuracy_measured': False,
            'accepted': False, 'qualified': False, 'proof_authority': False}


class ClosedPlanFixtures(unittest.TestCase):
    def test_fixed_six_control_plan_and_three_baselines_validate(self):
        worker.validate_plan(fixture_plan(), HELPER, FROZEN, BINDING)

    def test_unknown_supervision_key_is_rejected(self):
        plan = fixture_plan()
        plan['targets'] = []
        with self.assertRaises(ValueError):
            worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_mask_integer_zero_cannot_be_boolean_zero(self):
        plan = fixture_plan()
        plan['semantic_masks']['weak_decoder_fit'] = False
        with self.assertRaises(ValueError):
            worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_each_frozen_implementation_pin_is_enforced(self):
        for field in ('baseline_helper_binding', 'frozen_joint_helper_binding', 'selector_binding',
                      'summary_baseline_helper_binding'):
            plan = fixture_plan()
            plan[field] = {**BINDING, 'sha256': '0' * 64}
            with self.subTest(field=field), self.assertRaises(ValueError):
                worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_control_order_and_missing_control_are_rejected(self):
        for values in (list(reversed(worker.CONTROLS)), list(worker.CONTROLS[:-1])):
            plan = fixture_plan()
            plan['controls'] = values
            with self.subTest(values=values), self.assertRaises(ValueError):
                worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_each_seed_requires_all_six_two_split_receipts(self):
        for mutation in ('seed', 'control', 'split', 'target'):
            plan = fixture_plan()
            row = plan['baseline_receipts'][1]
            if mutation == 'seed':
                row['seed'] = 1729
            elif mutation == 'control':
                del row['arms']['zero_raw']
            elif mutation == 'split':
                del row['arms']['zero_raw']['development_binding']
            else:
                row['arms']['zero_raw']['formal_target_binding'] = BINDING
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_previous_joint_ledgers_require_all_three_seed_bindings(self):
        for mutation in ('missing', 'duplicate', 'extra'):
            plan = fixture_plan()
            if mutation == 'missing':
                plan['baseline_joint_ledgers'].pop()
            elif mutation == 'duplicate':
                plan['baseline_joint_ledgers'][1]['seed'] = 1729
            else:
                plan['baseline_joint_ledgers'][0]['formal_targets'] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)

    def test_policy_or_resource_changes_are_rejected(self):
        for field in ('policy', 'resource_limits'):
            plan = fixture_plan()
            plan[field] = {}
            with self.subTest(field=field), self.assertRaises(ValueError):
                worker.validate_plan(seal(plan), HELPER, FROZEN, BINDING)


class EffectiveConditionerFixtures(unittest.TestCase):
    def join(self, control, panel=None, vectors=None, record=None):
        baseline = conditioning_fixture(control)
        return worker.conditioner_joins(panel if panel is not None else baseline[0],
            vectors if vectors is not None else baseline[1], record if record is not None else baseline[2],
            control, digest, {'fixture_control': control})

    def test_raw_and_reconstruction_controls_retain_own_donors(self):
        for control in ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed'):
            rows = self.join(control)
            with self.subTest(control=control):
                self.assertEqual(rows[7]['original_latent_sha256'], rows[7]['effective_latent_sha256'])
                self.assertEqual(rows[7]['latent_donor_id'], 'source-7')
                self.assertTrue(rows[7]['latent_input_enabled'])
                self.assertEqual(rows[7]['latent_ablation'], 'none')

    def test_rotation_joins_successor_and_wraparound_before_filtering(self):
        rows = self.join('rotated_raw')
        self.assertEqual(rows[0]['latent_donor_id'], 'source-1')
        self.assertEqual(rows[31]['latent_donor_id'], 'source-0')
        self.assertEqual(rows[31]['latent_donor_position'], 0)
        self.assertEqual(rows[31]['effective_latent_sha256'], rows[0]['original_latent_sha256'])
        self.assertNotEqual(rows[31]['effective_latent_sha256'], rows[31]['original_latent_sha256'])
        self.assertEqual(rows[31]['latent_ablation'], 'rotate')

    def test_zero_retains_own_donor_but_uses_zero_vector_with_gate_enabled(self):
        rows = self.join('zero_raw')
        zero_hash = digest([0.0] * 768, ascii=True)
        self.assertEqual({row['effective_latent_sha256'] for row in rows}, {zero_hash})
        self.assertNotEqual(rows[5]['original_latent_sha256'], zero_hash)
        self.assertEqual(rows[5]['latent_donor_id'], 'source-5')
        self.assertTrue(rows[5]['latent_input_enabled'])
        self.assertEqual(rows[5]['model_latent_float32_sha256'], zero_hash)

    def test_disabled_retains_raw_vector_with_gate_disabled(self):
        rows = self.join('disabled_raw')
        self.assertEqual(rows[5]['original_latent_sha256'], rows[5]['effective_latent_sha256'])
        self.assertFalse(rows[5]['latent_input_enabled'])
        self.assertEqual(rows[5]['latent_donor_id'], 'source-5')
        self.assertEqual(rows[5]['latent_ablation'], 'disabled')
        self.assertNotEqual(rows[5]['effective_latent_sha256'], digest([0.0] * 768, ascii=True))

    def test_transformations_do_not_mutate_original_panel_or_vectors(self):
        for control in worker.CONTROLS:
            fixture = conditioning_fixture(control)
            before = copy.deepcopy(fixture)
            worker.conditioner_joins(*fixture, control, digest, {'kind': control})
            with self.subTest(control=control):
                self.assertEqual(fixture, before)

    def test_rotated_own_source_donor_is_rejected(self):
        panel, vectors, record = conditioning_fixture('rotated_raw')
        record['rows'][0]['latent_donor_id'] = panel[0]['id']
        with self.assertRaisesRegex(ValueError, 'donor/gate'):
            self.join('rotated_raw', panel, vectors, record)

    def test_any_source_or_conditioner_join_mutation_is_rejected(self):
        for field, value in (('id', 'wrong'), ('position', 8), ('submitted_position', 8),
                             ('original_latent_sha256', '0' * 64), ('effective_latent_sha256', '0' * 64),
                             ('latent_donor_position', 8), ('latent_donor_id', 'source-8'),
                             ('latent_input_enabled', False)):
            panel, vectors, record = conditioning_fixture('rotated_raw')
            record['rows'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.join('rotated_raw', panel, vectors, record)

    def test_native_row_must_match_effective_hash_and_gate(self):
        for field, value in (('latent_sha256', '0' * 64), ('latent_input_enabled', False)):
            panel, vectors, record = conditioning_fixture('zero_raw')
            record['rows'][0]['decoder_row'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.join('zero_raw', panel, vectors, record)

    def test_disabled_and_zero_owner_controls_cannot_be_conflated(self):
        for control, owner_control in (('zero_raw', 'zero'), ('disabled_raw', 'none')):
            panel, vectors, record = conditioning_fixture(control)
            record['owner_control'] = owner_control
            with self.subTest(control=control), self.assertRaises(ValueError):
                self.join(control, panel, vectors, record)

    def test_any_blocked_or_missing_row_fails_closed_before_subset_rotation(self):
        for mutation in ('subset', 'eligible', 'submitted', 'blocked', 'encoding', 'backend'):
            panel, vectors, record = conditioning_fixture('rotated_raw')
            if mutation == 'subset':
                panel.pop()
                vectors.pop()
                record['rows'].pop()
            elif mutation == 'eligible':
                record['eligible_count'] = 31
            elif mutation == 'submitted':
                record['submitted_positions'].pop()
            elif mutation == 'blocked':
                record['rows'][0]['preflight']['outcome'] = 'clarification_required'
            elif mutation == 'encoding':
                record['rows'][0]['encoding']['outcome'] = 'unavailable'
            else:
                record['backend_exception_type'] = 'RuntimeError'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.join('rotated_raw', panel, vectors, record)

    def test_invalid_native768_vector_is_rejected(self):
        for value in (True, math.nan, math.inf, '1', 3.5e38, 10 ** 400):
            panel, vectors, record = conditioning_fixture('raw_source')
            vectors[0][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.join('raw_source', panel, vectors, record)
        panel, vectors, record = conditioning_fixture('raw_source')
        vectors[0].pop()
        with self.assertRaises(ValueError):
            self.join('raw_source', panel, vectors, record)

    def test_duplicate_source_identity_is_rejected(self):
        panel, vectors, record = conditioning_fixture('raw_source')
        panel[1]['id'] = panel[0]['id']
        with self.assertRaises(ValueError):
            self.join('raw_source', panel, vectors, record)

    def test_tensor_float32_hash_is_separate_from_original_native_hash(self):
        panel, vectors, record = conditioning_fixture('raw_source')
        vectors[0] = [0.1] * 768
        native_hash = digest(vectors[0], ascii=True)
        record['rows'][0]['original_latent_sha256'] = native_hash
        record['rows'][0]['effective_latent_sha256'] = native_hash
        record['rows'][0]['decoder_row']['latent_sha256'] = native_hash
        rows = self.join('raw_source', panel, vectors, record)
        self.assertNotEqual(rows[0]['model_latent_float32_sha256'], rows[0]['effective_latent_sha256'])

    def test_conditioner_profiles_keep_reconstruction_producer_claims_false(self):
        profiles = worker.conditioner_profiles({'pca_control': {'retained_axes': 31},
                                               'new_checkpoint_binding': BINDING}, 'f' * 64)
        self.assertEqual(set(profiles), set(worker.CONTROLS))
        self.assertEqual(profiles['raw_source']['source_profile_sha256'], 'f' * 64)
        for control in ('pca_reconstructed', 'new_ae_reconstructed', 'zero_raw'):
            self.assertIs(profiles[control]['original_producer_receipt_claimed'], False)
        self.assertIs(profiles['rotated_raw']['original_matched_source_producer_receipt_claimed'], False)
        self.assertIs(profiles['disabled_raw']['latent_input_enabled'], False)


class ActualJointCallFixtures(unittest.TestCase):
    def test_fixed_decision_ambiguity_retains_outcome_without_search_or_extra_forward(self):
        calls = {'actual_model_forward_calls': 384, 'source_row_decode_calls': 384,
                 'wrapper_calls': 12, 'owner_decoder_calls': 12,
                 'joint_additional_model_forward_calls': 0, 'joint_selection_calls': 383}
        banks = [{'fixture_capture_index': n} for n in range(384)]
        results = [{'joint': {'status': 'proposal', 'search': {'fixture': True}, 'reason': None}}
                   for _ in range(383)]
        results.append({'joint': {'status': 'abstained', 'search': None,
                                 'reason': 'ambiguous_fixed_decision_scores'}})
        self.assertEqual(worker.validate_joint_counters(calls, banks, results), 1)
        self.assertEqual(len(results), 384)
        self.assertEqual(calls['actual_model_forward_calls'], 384)
        self.assertEqual(calls['joint_selection_calls'], 383)
        for mutation in ('fictitious_search_call', 'missing_retained_reason', 'additional_forward'):
            changed_calls, changed_results = copy.deepcopy(calls), copy.deepcopy(results)
            if mutation == 'fictitious_search_call':
                changed_calls['joint_selection_calls'] = 384
            elif mutation == 'missing_retained_reason':
                changed_results[-1]['joint']['reason'] = 'some_other_abstention'
            else:
                changed_calls['joint_additional_model_forward_calls'] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.validate_joint_counters(changed_calls, banks, changed_results)


class PreviousRawOutcomeFixtures(unittest.TestCase):
    def test_complete_old_raw_outcomes_index_by_split_and_identity(self):
        result = worker.previous_joint_rows(previous_ledger(), 1729)
        self.assertEqual(len(result), 64)
        self.assertIn(('train', 'source-0'), result)
        self.assertIn(('development', 'source-63'), result)

    def test_wrong_seed_missing_or_duplicate_rows_are_rejected(self):
        for mutation in ('seed', 'missing', 'duplicate', 'cross_split_identity'):
            ledger = previous_ledger()
            if mutation == 'seed':
                ledger['seed'] = 1730
            elif mutation == 'missing':
                ledger['rows'].pop()
            elif mutation == 'duplicate':
                ledger['rows'][1] = copy.deepcopy(ledger['rows'][0])
            else:
                ledger['rows'][32]['id'] = ledger['rows'][0]['id']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.previous_joint_rows(ledger, 1729)

    def test_old_semantic_promotion_claims_are_rejected(self):
        for field in ('semantic_accuracy_measured', 'accepted', 'qualified', 'proof_authority'):
            ledger = previous_ledger()
            ledger[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                worker.previous_joint_rows(ledger, 1729)
        ledger = previous_ledger()
        ledger['rows'][7]['source_fidelity_established'] = True
        with self.assertRaises(ValueError):
            worker.previous_joint_rows(ledger, 1729)

    def test_raw_outcome_replay_allows_only_new_capture_metadata(self):
        previous = previous_row(0)
        result = copy.deepcopy(previous)
        result.update(seed=1729, control='raw_source', score_row_sha256='d' * 64,
                      original_latent_sha256='e' * 64)
        worker.match_previous_raw_joint(previous, result, digest)

    def test_entire_joint_diagnostics_and_greedy_outcomes_are_matched(self):
        for mutation in ('joint_ir', 'joint_search', 'joint_facets', 'joint_fixed_decisions',
                         'joint_status', 'greedy', 'source_text', 'latent_sha256', 'accepted'):
            previous = previous_row(0)
            result = copy.deepcopy(previous)
            if mutation == 'joint_ir':
                result['joint']['canonical_ir']['rules'][0]['actor'] = 'owners'
            elif mutation == 'joint_search':
                result['joint']['search']['score'] = 2.0
            elif mutation == 'joint_facets':
                result['joint']['facets']['actor']['token_start'] = 1
            elif mutation == 'joint_fixed_decisions':
                result['joint']['fixed_decisions']['modality'] = 'P'
            elif mutation == 'joint_status':
                result['joint']['status'] = 'abstained'
            elif mutation == 'greedy':
                result['greedy']['reason'] = 'ambiguous_decoder_scores'
            elif mutation == 'source_text':
                result['source_text'] += ' Extra.'
            elif mutation == 'latent_sha256':
                result['latent_sha256'] = '0' * 64
            else:
                result['accepted'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                worker.match_previous_raw_joint(previous, result, digest)

    def test_previous_raw_outcome_check_does_not_mutate_evidence(self):
        ledger = previous_ledger()
        before = copy.deepcopy(ledger)
        result = worker.previous_joint_rows(ledger, 1729)
        worker.match_previous_raw_joint(result[('train', 'source-0')], ledger['rows'][0], digest)
        self.assertEqual(ledger, before)
        result[('train', 'source-0')]['joint']['status'] = 'abstained'
        self.assertEqual(ledger, before)


if __name__ == '__main__':
    unittest.main()
