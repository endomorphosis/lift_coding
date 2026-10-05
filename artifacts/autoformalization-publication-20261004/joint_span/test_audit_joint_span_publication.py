"""Pure publication-audit fixtures, independent of runtime model outputs."""
import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).with_name('audit_joint_span_publication.py')
SPEC = importlib.util.spec_from_file_location('fixture_joint_publication_audit', PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def ir(actor='Alice', action='acts'):
    return {'rules': [{'modality': 'O', 'actor': actor, 'action': action, 'object': '',
                       'conditions': [], 'exceptions': [], 'temporal': []}]}


def pair(greedy_status='abstained', joint_status='proposal', same=True):
    return {'greedy': {'status': greedy_status, 'reason': None if greedy_status == 'decoded' else 'copied_spans_overlap',
                       'canonical_ir': ir() if greedy_status == 'decoded' else None},
            'joint': {'status': joint_status, 'reason': None if joint_status == 'proposal' else 'no_assignment',
                      'canonical_ir': ir() if same else ir('Bob'), 'search': None}}


class PublicationFixtures(unittest.TestCase):
    def test_no_provider_import(self):
        self.assertNotIn('torch', sys.modules)

    def test_empty_statistics(self):
        value = audit.statistics([])
        self.assertEqual(value['request_count'], 0)
        self.assertEqual(value['policy_outcome_count'], 0)
        self.assertEqual(value['search_totals'], {})

    def test_rescued_overlap_is_structural(self):
        value = audit.statistics([pair()])
        self.assertEqual(value['rescued_greedy_overlap_abstentions'], 1)
        self.assertEqual(value['policy_outcome_count'], 2)
        self.assertEqual(value['greedy_proposals'], 0)

    def test_preserved_changed_lost_counts(self):
        rows = [pair('decoded'), pair('decoded', same=False), pair('decoded', 'abstained')]
        value = audit.statistics(rows)
        self.assertEqual(value['preserved_greedy_proposals'], 1)
        self.assertEqual(value['changed_greedy_proposals'], 1)
        self.assertEqual(value['lost_greedy_proposals'], 1)

    def test_public_transform_removes_only_logits(self):
        row = pair()
        row['greedy']['span_diagnostics'] = {'modality_logits': [1, 2, 3], 'tokens': ['a']}
        public = audit.public_row(row, 1729, 0)
        self.assertEqual(public['greedy']['span_diagnostics'], {'tokens': ['a']})
        self.assertIn('modality_logits', row['greedy']['span_diagnostics'])
        self.assertFalse(public['qualified'])
        self.assertEqual(public['source_position'], 0)

    def test_zero_mask_booleans_rejected(self):
        with self.assertRaises(ValueError):
            audit.zero_masks(dict.fromkeys(audit.MASKS, False))

    def test_native_byte_ids_and_reduced_recipe_differ(self):
        full = audit.native_source_tokens('É acts')
        self.assertEqual(full[0]['byte_ids'], [byte + 1 for byte in 'é'.encode()])
        reduced = [{key: token[key] for key in ('text', 'start', 'end')} for token in full]
        self.assertNotEqual(audit.digest(full), audit.digest(reduced))

    def test_source_char_bound(self):
        with self.assertRaises(ValueError):
            audit.native_source_tokens('a' * 16385)

    def test_source_token_bound(self):
        with self.assertRaises(ValueError):
            audit.native_source_tokens('a ' * 257)

    def test_source_byte_bound(self):
        with self.assertRaises(ValueError):
            audit.native_source_tokens('é' * 1025)

    def test_valid_rule(self):
        audit.complete_copied_rule_contract(ir())

    def test_all_placeholder_families_rejected(self):
        for value in ('{{todo}}', '<copy>', 'TBD', 'lorem ipsum', '__source__'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit.complete_copied_rule_contract(ir(action=value))

    def test_plain_copy_verb_allowed(self):
        audit.complete_copied_rule_contract(ir(action='copy'))

    def test_placeholder_qualifier_rejected(self):
        value = ir()
        value['rules'][0]['conditions'] = ['source_text']
        with self.assertRaises(ValueError):
            audit.complete_copied_rule_contract(value)


if __name__ == '__main__':
    unittest.main()
