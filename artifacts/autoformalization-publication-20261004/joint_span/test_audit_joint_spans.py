"""Pure fixtures for the independent saved-score auditor; no model imports."""
import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).with_name('audit_joint_spans.py')
SPEC = importlib.util.spec_from_file_location('fixture_independent_joint_audit', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def heads(count=2):
    return {'modality': [3.0, 1.0, 0.0], 'presence': [[1.0, 0.0] for _ in range(4)],
            'start': [[10.0, 0.0][:count], [0.0, 10.0][:count]] + [[0.0] * count for _ in range(4)],
            'end': [[10.0, 0.0][:count], [0.0, 10.0][:count]] + [[0.0] * count for _ in range(4)]}


class AuditFixtures(unittest.TestCase):
    def test_no_provider_import(self):
        self.assertNotIn('torch', sys.modules)

    def test_known_joint_assignment_and_runner_up(self):
        result, diagnostics = audit.replay(heads(), [True, True, False, False, False, False])
        self.assertEqual(result['selected_spans'], [[0, 0], [1, 1], None, None, None, None])
        self.assertEqual(result['best_score'], 40.0)
        self.assertEqual(result['runner_up_score'], 0.0)
        self.assertEqual(result['joint_score_margin'], 40.0)
        self.assertEqual(diagnostics['complete_retained_state_count'], 2)

    def test_no_feasible_assignment(self):
        result, _ = audit.replay(heads(1), [True, True, False, False, False, False])
        self.assertEqual(result['reason'], 'no_complete_assignment_in_retained_candidates')
        self.assertIsNone(result['selected_spans'])

    def test_complete_assignment_tie_abstains(self):
        score = heads()
        score['start'] = score['end'] = [[0.0, 0.0] for _ in range(6)]
        result, _ = audit.replay(score, [True, True, False, False, False, False])
        self.assertEqual(result['reason'], 'ambiguous_joint_scores')
        self.assertIsNone(result['selected_spans'])

    def test_fixed_presence_modality(self):
        actual = audit.decisions(heads())
        self.assertEqual(actual['modality'], 'O')
        self.assertEqual(actual['present'], [True, True, False, False, False, False])
        self.assertFalse(actual['ambiguous'])

    def test_float32_rounding(self):
        self.assertEqual(audit.rounded32(16777217.0), 16777216.0)

    def test_float32_overflow_rejected(self):
        with self.assertRaises(ValueError):
            audit.rounded32(1e300)

    def test_nonfinite_head_rejected(self):
        score = heads()
        score['start'][0][0] = float('nan')
        with self.assertRaises(ValueError):
            audit.validate_heads(score, 2)

    def test_unknown_head_rejected(self):
        score = heads()
        score['reference'] = []
        with self.assertRaises(ValueError):
            audit.validate_heads(score, 2)

    def test_bool_mask_rejected(self):
        with self.assertRaises(ValueError):
            audit.zero_masks(dict.fromkeys(audit.MASKS, False))

    def test_literal_binding_and_single_rule_contract(self):
        text = 'Alice acts'
        fixed = audit.decisions(heads())
        ir, facets = audit.literal(text, audit.tokens(text), fixed,
                                  [[0, 0], [1, 1], None, None, None, None])
        audit.single_rule_contract(ir)
        self.assertEqual(ir['rules'][0]['actor'], 'Alice')
        self.assertEqual(facets['action']['char_start'], 6)

    def test_literal_overlap_rejected(self):
        with self.assertRaises(ValueError):
            audit.literal('Alice acts', audit.tokens('Alice acts'), audit.decisions(heads()),
                          [[0, 1], [1, 1], None, None, None, None])

    def test_rule_unknown_field_rejected(self):
        ir, _ = audit.literal('Alice acts', audit.tokens('Alice acts'), audit.decisions(heads()),
                              [[0, 0], [1, 1], None, None, None, None])
        ir['rules'][0]['reference'] = 'gold'
        with self.assertRaises(ValueError):
            audit.single_rule_contract(ir)


if __name__ == '__main__':
    unittest.main()
