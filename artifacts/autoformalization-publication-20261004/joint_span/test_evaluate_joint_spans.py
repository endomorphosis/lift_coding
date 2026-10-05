"""Pure fixtures for detached head validation and literal proposal transport.

These tests load no model, score bank, checkpoint, tokenizer owner, network
provider or prover. Copying and non-overlap tests establish no source fidelity.
"""
from __future__ import annotations

import copy
import importlib.util
import math
import re
import struct
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'joint_span_worker_fixture', Path(__file__).with_name('evaluate_joint_spans.py'))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def heads(count=3):
    return {'start': [[0.0] * count for _ in range(6)],
            'end': [[0.0] * count for _ in range(6)],
            'presence': [[0.0, 1.0] for _ in range(4)],
            'modality': [2.0, 0.0, -1.0]}


def tokens(text):
    return [{'text': match.group(), 'start': match.start(), 'end': match.end()}
            for match in re.finditer(r'\w+|[^\w\s]', text, re.UNICODE)]


def decisions(present=None, modality='O'):
    return {'modality': modality,
            'present': [True, True, False, False, False, False] if present is None else present}


class DetachedScoreFixtures(unittest.TestCase):
    def test_valid_detached_heads_are_not_mutated(self):
        scores = heads()
        before = copy.deepcopy(scores)
        self.assertIsNone(worker.shape_scores(scores, 3))
        self.assertEqual(scores, before)

    def test_both_token_bounds_are_supported(self):
        for count in (1, 256):
            with self.subTest(count=count):
                worker.shape_scores(heads(count), count)

    def test_token_count_must_be_bounded_integer(self):
        for count in (False, True, 0, -1, 257, 3.0, '3'):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    worker.shape_scores(heads(), count)

    def test_head_bank_has_closed_keys(self):
        for change in ('missing', 'unknown'):
            scores = heads()
            if change == 'missing':
                del scores['modality']
            else:
                scores['reference_ir'] = None
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    worker.shape_scores(scores, 3)

    def test_every_span_head_has_six_full_token_rows(self):
        for name, change in (('start', 'facets'), ('end', 'tokens'), ('start', 'tuple')):
            scores = heads()
            if change == 'facets':
                scores[name].pop()
            elif change == 'tokens':
                scores[name][4].pop()
            else:
                scores[name][2] = tuple(scores[name][2])
            with self.subTest(name=name, change=change):
                with self.assertRaises(ValueError):
                    worker.shape_scores(scores, 3)

    def test_presence_and_modality_shapes_are_checked(self):
        for name, replacement in (('presence', [[0.0, 1.0]] * 3),
                                  ('presence', [[0.0, 1.0, 2.0]] * 4),
                                  ('modality', [0.0, 1.0]),
                                  ('modality', (2.0, 0.0, -1.0))):
            scores = heads()
            scores[name] = replacement
            with self.subTest(name=name, replacement=replacement):
                with self.assertRaises(ValueError):
                    worker.shape_scores(scores, 3)

    def test_head_values_reject_booleans_text_and_nonfinite_numbers(self):
        for value in (True, '1', None, math.nan, math.inf, -math.inf):
            scores = heads()
            scores['end'][5][2] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    worker.shape_scores(scores, 3)

    def test_scores_must_be_exact_native_float32_values(self):
        scores = heads()
        scores['presence'][0][1] = 0.1
        with self.assertRaises(ValueError):
            worker.shape_scores(scores, 3)
        scores['presence'][0][1] = struct.unpack('f', struct.pack('f', 0.1))[0]
        worker.shape_scores(scores, 3)

    def test_out_of_float32_range_is_a_controlled_rejection(self):
        for value in (3.5e38, -3.5e38, 10 ** 400):
            scores = heads()
            scores['modality'][0] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    worker.shape_scores(scores, 3)


class FixedNativeDecisionFixtures(unittest.TestCase):
    def test_modality_presence_and_required_facets_remain_native_choices(self):
        scores = heads()
        scores['modality'] = [-1.0, 0.0, 2.0]
        scores['presence'] = [[2.0, 1.0], [0.0, 2.0], [2.0, -1.0], [-2.0, -1.0]]
        result = worker.fixed_decisions(scores)
        self.assertEqual(result['modality'], 'F')
        self.assertEqual(result['present'], [True, True, False, True, False, True])
        self.assertFalse(result['ambiguous'])

    def test_tied_modality_uses_native_stable_choice_and_abstains(self):
        scores = heads()
        scores['modality'] = [1.0, 1.0, 0.0]
        result = worker.fixed_decisions(scores)
        self.assertEqual(result['modality'], 'O')
        self.assertEqual(result['margins']['modality'], 0.0)
        self.assertTrue(result['ambiguous'])

    def test_tied_optional_presence_stays_absent_and_abstains(self):
        scores = heads()
        scores['presence'][3] = [1.0, 1.0]
        result = worker.fixed_decisions(scores)
        self.assertFalse(result['present'][-1])
        self.assertTrue(result['ambiguous'])

    def test_float32_margin_epsilon_applies_to_presence(self):
        scores = heads()
        scores['presence'][0] = [0.0, 2 ** -24]
        self.assertTrue(worker.fixed_decisions(scores)['ambiguous'])
        scores['presence'][0] = [1.0, 1.0 + 2 ** -23]
        result = worker.fixed_decisions(scores)
        self.assertEqual(result['margins']['object'], 2 ** -23)
        self.assertFalse(result['ambiguous'])

    def test_float32_margin_epsilon_applies_to_modality(self):
        scores = heads()
        scores['modality'] = [2 ** -24, 0.0, -1.0]
        self.assertTrue(worker.fixed_decisions(scores)['ambiguous'])
        scores['modality'] = [2 ** -23, 0.0, -1.0]
        self.assertFalse(worker.fixed_decisions(scores)['ambiguous'])

    def test_overflowed_modality_difference_cannot_be_a_confidence_margin(self):
        scores = heads()
        value = struct.unpack('f', struct.pack('f', 3e38))[0]
        scores['modality'] = [value, -value, -value]
        worker.shape_scores(scores, 3)
        with self.assertRaises(ValueError):
            worker.fixed_decisions(scores)

    def test_overflowed_presence_difference_is_rejected(self):
        scores = heads()
        value = struct.unpack('f', struct.pack('f', 3e38))[0]
        scores['presence'][1] = [-value, value]
        worker.shape_scores(scores, 3)
        with self.assertRaises(ValueError):
            worker.fixed_decisions(scores)

    def test_decision_computation_does_not_mutate_saved_heads(self):
        scores = heads()
        before = copy.deepcopy(scores)
        worker.fixed_decisions(scores)
        self.assertEqual(scores, before)


class LiteralSourceTransportFixtures(unittest.TestCase):
    def setUp(self):
        self.text = 'Café owners notify clients under review unless barred before noon.'
        self.tokens = tokens(self.text)
        self.spans = [[0, 1], [2, 2], [3, 3], [4, 5], [6, 7], [8, 9]]

    def test_all_facets_copy_exact_unicode_source_slices(self):
        ir, facets = worker.literal_rule(
            self.text, self.tokens, decisions([True] * 6), self.spans)
        rule = ir['rules'][0]
        self.assertEqual(rule, {'modality': 'O', 'actor': 'Café owners', 'action': 'notify',
                               'object': 'clients', 'conditions': ['under review'],
                               'exceptions': ['unless barred'], 'temporal': ['before noon']})
        self.assertEqual(facets['actor']['char_end'], 11)
        self.assertEqual(facets['actor']['text'], self.text[:11])
        self.assertNotEqual(len('Café owners'.encode()), facets['actor']['char_end'])
        for facet in facets.values():
            self.assertEqual(facet['text'], self.text[facet['char_start']:facet['char_end']])

    def test_absent_object_and_qualifiers_have_distinct_ir_shapes(self):
        ir, facets = worker.literal_rule(
            self.text, self.tokens, decisions(), [[0, 1], [2, 2], None, None, None, None])
        rule = ir['rules'][0]
        self.assertEqual(rule['object'], '')
        for field in ('conditions', 'exceptions', 'temporal'):
            self.assertEqual(rule[field], [])
        for field in worker.OPTIONAL:
            self.assertEqual(facets[field], {'present': False, 'token_start': None,
                             'token_end_inclusive': None, 'char_start': None,
                             'char_end': None, 'text': None})

    def test_adjacent_required_spans_are_valid_without_shared_tokens(self):
        ir, _ = worker.literal_rule('A acts.', tokens('A acts.'), decisions(),
                                   [[0, 0], [1, 1], None, None, None, None])
        self.assertEqual(ir['rules'][0]['actor'], 'A')
        self.assertEqual(ir['rules'][0]['action'], 'acts')

    def test_shared_token_is_rejected_even_with_different_character_slices(self):
        spans = copy.deepcopy(self.spans)
        spans[1] = [1, 2]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            worker.literal_rule(self.text, self.tokens, decisions([True] * 6), spans)

    def test_inclusive_token_coordinates_must_be_integer_and_in_range(self):
        for interval in ([True, 1], [1.0, 1], [-1, 1], [2, 1], [0, len(self.tokens)], (0, 1)):
            spans = copy.deepcopy(self.spans)
            spans[0] = interval
            with self.subTest(interval=interval):
                with self.assertRaises(ValueError):
                    worker.literal_rule(self.text, self.tokens, decisions([True] * 6), spans)

    def test_predicted_present_facet_cannot_be_silently_omitted(self):
        spans = copy.deepcopy(self.spans)
        spans[4] = None
        with self.assertRaises(ValueError):
            worker.literal_rule(self.text, self.tokens, decisions([True] * 6), spans)

    def test_predicted_absent_facet_cannot_be_added(self):
        with self.assertRaises(ValueError):
            worker.literal_rule(self.text, self.tokens, decisions(), self.spans)

    def test_required_facets_cannot_be_marked_absent(self):
        for index in (0, 1):
            present = [True] * 6
            present[index] = False
            spans = copy.deepcopy(self.spans)
            spans[index] = None
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    worker.literal_rule(self.text, self.tokens, decisions(present), spans)

    def test_decision_modality_and_presence_contract_is_checked(self):
        for choice in (decisions([True] * 6, 'X'), decisions([1] * 6), decisions([True] * 5)):
            with self.subTest(choice=choice):
                with self.assertRaises(ValueError):
                    worker.literal_rule(self.text, self.tokens, choice, self.spans)

    def test_token_endpoint_text_cannot_be_forged(self):
        changed = copy.deepcopy(self.tokens)
        changed[0]['text'] = 'Cafe'
        with self.assertRaisesRegex(ValueError, 'binding'):
            worker.literal_rule(self.text, changed, decisions([True] * 6), self.spans)

    def test_character_bounds_and_unicode_character_offsets_are_checked(self):
        for bad_start in (True, -1, len(self.text)):
            changed = copy.deepcopy(self.tokens)
            changed[0]['start'] = bad_start
            with self.subTest(start=bad_start):
                with self.assertRaises(ValueError):
                    worker.literal_rule(self.text, changed, decisions([True] * 6), self.spans)

    def test_literal_transport_does_not_mutate_inputs(self):
        choice = decisions([True] * 6)
        before = copy.deepcopy((self.tokens, choice, self.spans))
        worker.literal_rule(self.text, self.tokens, choice, self.spans)
        self.assertEqual((self.tokens, choice, self.spans), before)


if __name__ == '__main__':
    unittest.main()
