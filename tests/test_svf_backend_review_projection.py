"""Authored RAM review-presentation vectors; no operational acceptance."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(BASE / 'scripts')))
sys.path.insert(0, str(BASE / 'tests')); sys.path.insert(0, str(BASE / 'scripts')); sys.path.insert(0, str(SCRIPTS))
import test_svf_final_viewport_coverage as shapes
import test_svf_phase_evidence as phase_shapes
final = shapes.final


class BackendReviewProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm'); self.addCleanup(self.temp.cleanup)
        self.addCleanup(patch.stopall)
        self.root = Path(self.temp.name); self.f = shapes.Fixture(self.root)
        patch.object(final, '_node_source_snapshot', side_effect=self.f.source_vector).start()
        patch.object(shapes.worker, 'ROOT', self.root).start()
        self.g = self.f.group()

    def tool(self, actual='delivered'):
        self.f.tool_backed(self.g, declared=actual, observed=actual)
        for child in self.g['children']:
            child['backend_call_phases'].update(backend_proof=0, primary_result=1)
        self.f.persist(self.g)
        self.f.validated(self.g)
        return final.projection(self.root, self.g['report'])

    def factored(self):
        vector = phase_shapes.PhaseEvidenceTests('test_positive_exact_phase_evidence_and_rich_projection')
        vector.setUp(); self.addCleanup(vector.doCleanups)
        for which, child in enumerate(vector.group['children']):
            for phase in child['phase_evidence']['phases']:
                for row in phase['steps']:
                    for media in row['media']:
                        source = str(which + 1) * 64
                        for sample in (media['before'], media['after']):
                            if sample and sample.get('present'):
                                sample['src_sha256'] = source
                                sample['current_time'] += (which + 1) * .01234567890123
                                sample['duration'] += (which + 1) * .01234567890123
                        for index, event in enumerate(media['seeked_events']):
                            event['current_time'] += (which + 1) * .01234567890123 + index * .00000000123456
        vector.f.persist(vector.group)
        value = final.projection(vector.root, vector.group['report'])
        # Pure codec stress: arbitrary unrelated literal data must survive too.
        value['authored_padding'] = 'x' * max(0, 18001 - len(final.encoded(value)))
        return value, final._factor_projection(value)

    def test_exact_owner_result_and_immutable_raw_references_with_zero_proof_phase_calls(self):
        result = self.tool()
        for view, child in zip(result['viewports'], self.g['children']):
            item = view['backend_observations'][0]; original = child['backend_observations'][0]
            self.assertEqual(item['result_assertion'], original['result_assertion'])
            self.assertEqual(item['owner'], 'ipfs_kit_py')
            self.assertTrue(item['receipt_verified']); self.assertTrue(item['semantic_result_verified'])
            self.assertEqual(view['backend_call_phases']['backend_proof'], 0)
            self.assertNotIn('phase', item)
            for kind in ('receipt', 'event'):
                reference = next(row for row in child['artifacts'] if row['path'] == original[kind + '_artifact'])
                self.assertEqual(item[kind + '_artifact'], reference)
                self.assertEqual(final.reference(self.root, self.root / reference['path']), reference)
        self.assertNotIn('shared_projection_values', result)

    def test_arbitrary_owner_actual_types_and_marker_shaped_payload_remain_literal(self):
        actual = {'projection_value_ref': 'v0', 'overrides': {'int': 0, 'bool': False},
                  'values': [0, -0.0, False, None, 'delivered', {'nested': True}]}
        result = self.tool(actual)
        for view in result['viewports']:
            self.assertEqual(final.encoded(view['backend_observations'][0]['result_assertion']['actual']), final.encoded(actual))
        result['authored_padding'] = 'x' * 18000
        factored = final._factor_projection(result)
        self.assertEqual(final.encoded(final._expand_projection(factored)), final.encoded(result))
        self.assertEqual(factored['viewports'][0]['backend_observations'], result['viewports'][0]['backend_observations'])

    def test_large_native_values_have_exact_hash_size_and_child_pointer_not_clipped_strings(self):
        actual = 'native-unicode-λ' * 200
        result = self.tool(actual)
        marker = result['viewports'][0]['backend_observations'][0]['result_assertion']['actual']
        self.assertTrue(marker['projection_omitted'])
        self.assertEqual(marker['original_sha256'], final.digest(actual))
        self.assertEqual(marker['original_bytes'], len(final.encoded(actual)))
        self.assertEqual(marker['original_child_pointer'], '/backend_observations/0/result_assertion/actual')

    def test_missing_backend_artifact_closure_is_refused(self):
        self.tool()
        child = self.g['children'][0]; name = child['backend_observations'][0]['event_artifact']
        child['artifacts'] = [item for item in child['artifacts'] if item['path'] != name]
        self.f.persist(self.g)
        with self.assertRaises(ValueError): final.projection(self.root, self.g['report'])

    def test_changed_raw_backend_bytes_are_refused(self):
        self.tool()
        target = self.root / self.g['children'][0]['backend_observations'][0]['receipt_artifact']
        target.write_bytes(target.read_bytes() + b' ')
        with self.assertRaises(ValueError): final.projection(self.root, self.g['report'])

    def test_phase_numbering_count_and_nonmedia_reopen_meanings_are_explicit(self):
        result = self.tool()
        self.assertEqual(result['scenario_phase_order'], ['primary_result', 'persist_reopen', 'failure_recovery'])
        self.assertIn('Zero-based', result['step_index_semantics']); self.assertIn('resets to 0', result['step_index_semantics'])
        self.assertIn('not validity flags', result['backend_call_phases_semantics'])
        self.assertIn('HTMLMediaElement/CID facts only', result['instruction'])
        self.assertIn('without an inferred phase or broader success', result['instruction'])

    def test_local_backend_list_stays_empty_without_fabricated_owner_proof(self):
        result = final.projection(self.root, self.g['report'])
        self.assertTrue(all(view['backend_observations'] == [] for view in result['viewports']))

    def test_historical_v1_projection_boundary_is_unchanged(self):
        data = json.loads(self.g['report'].read_bytes()); data['schema'] = 'swissknife.visual-functional-workflow.v1'
        self.f.write(str(self.g['report'].relative_to(self.root)), data)
        with self.assertRaises(ValueError): final.projection(self.root, self.g['report'])

    def test_lossless_differing_native_facts_roundtrip_and_literal_identity_references(self):
        original, factored = self.factored()
        self.assertIn('shared_projection_values', factored)
        self.assertEqual(final.encoded(final._expand_projection(factored)), final.encoded(original))
        self.assertLess(len(final.encoded(factored)), len(final.encoded(original)))
        for before, after in zip(original['viewports'], factored['viewports']):
            for key in ('name', 'session_id', 'original', 'result_screenshot', 'backend_observations'):
                self.assertEqual(final.encoded(before[key]), final.encoded(after[key]))

    def test_factoring_is_deterministic_and_only_activated_above_existing_cap(self):
        value = self.tool()
        self.assertIs(final._factor_projection(value), value)
        original, factored = self.factored()
        self.assertEqual(final.encoded(factored), final.encoded(final._factor_projection(original)))

    def test_unknown_reference_is_refused(self):
        _, factored = self.factored()
        factored['viewports'][0]['phase_evidence']['seek'] = {'projection_value_ref': 'unknown'}
        with self.assertRaises(ValueError): final._expand_projection(factored)

    def test_cyclic_shared_base_is_refused(self):
        _, factored = self.factored()
        key = next(iter(factored['shared_projection_values']))
        factored['shared_projection_values'][key] = {'projection_value_ref': key}
        with self.assertRaises(ValueError): final._expand_projection(factored)

    def test_marker_collision_in_known_fact_slot_is_refused(self):
        original, _ = self.factored()
        original['viewports'][0]['phase_evidence']['seek']['projection_value_ref'] = 'v0'
        with self.assertRaises(ValueError): final._factor_projection(original)

    def test_reference_override_cannot_add_or_delete_a_native_field(self):
        _, factored = self.factored()
        native = next((owner, key) for owner, key, _ in final._projection_snapshot_slots(factored)
                      if type(owner[key]) is dict and 'projection_value_ref' in owner[key])
        native[0][native[1]]['overrides'] = {'absent_original_field': None}
        with self.assertRaises(ValueError): final._expand_projection(factored)

    def test_typed_zero_float_and_boolean_differences_survive_factoring(self):
        original, _ = self.factored()
        seek = original['viewports'][0]['phase_evidence']['seek']
        seek['before']['current_time'] = -0.0; seek['after']['current_time'] = 0
        seek['before']['paused'] = False; seek['after']['paused'] = True
        factored = final._factor_projection(original)
        expanded = final._expand_projection(factored)
        self.assertEqual(final.encoded(expanded), final.encoded(original))
        self.assertIs(type(expanded['viewports'][0]['phase_evidence']['seek']['before']['current_time']), float)
        self.assertIs(type(expanded['viewports'][0]['phase_evidence']['seek']['after']['current_time']), int)


if __name__ == '__main__': unittest.main()
