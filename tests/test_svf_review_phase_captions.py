"""Portable projection interpretation cases; never app acceptance evidence."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(BASE / 'scripts')))
sys.path.insert(0, str(BASE / 'tests'))
sys.path.insert(0, str(BASE / 'scripts'))
sys.path.insert(0, str(SCRIPTS))
import test_svf_final_viewport_coverage as shapes
final = shapes.final


class ReviewPhaseCaptionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir='/dev/shm')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(patch.stopall)
        self.root = Path(temporary.name)
        self.fixture = shapes.Fixture(self.root)
        patch.object(final, '_node_source_snapshot', side_effect=self.fixture.source_vector).start()
        patch.object(shapes.worker, 'ROOT', self.root).start()
        self.group = self.fixture.group()
        self.fixture.tool_backed(self.group, declared='native-result', observed='native-result')
        for child in self.group['children']:
            child['backend_call_phases'].update(backend_proof=0, primary_result=1)
        self.fixture.persist(self.group)
        self.fixture.validated(self.group)
        self.result = final._expand_projection(final.projection(self.root, self.group['report']))

    def test_zero_named_bucket_keeps_nonzero_other_phase_and_joined_owner_proof(self):
        caption = self.result['backend_call_phases_semantics']
        self.assertIn('per named phase', caption)
        self.assertIn('Zero is only that bucket', caption)
        self.assertIn('other phases and joined owner receipts remain independent', caption)
        self.assertNotIn('backend_proof=0:no call', caption)
        for view, child in zip(self.result['viewports'], self.group['children']):
            self.assertEqual(view['backend_call_phases'], child['backend_call_phases'])
            self.assertEqual(view['backend_call_phases']['backend_proof'], 0)
            self.assertEqual(view['backend_call_phases']['primary_result'], 1)
            self.assertEqual(view['backend_call_count'], 1)
            self.assertEqual(view['backend_observation_count'], 1)
            self.assertEqual(view['backend_observations'][0]['result_assertion'], child['backend_observations'][0]['result_assertion'])
            self.assertTrue(view['backend_observations'][0]['receipt_verified'])

    def test_final_frame_chronology_does_not_reassign_earlier_phase_observations(self):
        instruction = self.result['instruction']
        self.assertIn('Final frames follow failure_recovery', instruction)
        self.assertIn('compare earlier runs with their phase receipts, not later frames', instruction)
        self.assertEqual(self.result['scenario_phase_order'], ['primary_result', 'persist_reopen', 'failure_recovery'])
        for view, child in zip(self.result['viewports'], self.group['children']):
            self.assertEqual(view['result_screenshot'], child['result_screenshot'])
            self.assertEqual([(row['phase'], row['step_index'], row['requirement_id']) for row in view['semantic_assertions']],
                             [(row['phase'], row['step_index'], row['requirement_id']) for row in child['semantic_assertions']])

    def test_existing_literal_path_identity_and_mobile_safeguards_are_retained(self):
        instruction = self.result['instruction']
        for text in ['Initial/demo/layout-only mobile state cannot prove mobile execution.',
                     'without an inferred phase or broader success',
                     'Unphased rows imply no identity.',
                     'Phased receipt/event paths are relative to viewport original directory; filenames contain raw CIDs.']:
            self.assertIn(text, instruction)
        for view, child in zip(self.result['viewports'], self.group['children']):
            self.assertEqual(view['session_id'], child['session_id'])
            self.assertEqual(view['original']['sha256'], final.reference(self.root, self.root / view['original']['path'])['sha256'])
            for role in ('receipt', 'event'):
                name = child['backend_observations'][0][role + '_artifact']
                reference = next(row for row in child['artifacts'] if row['path'] == name)
                self.assertEqual(view['backend_observations'][0][role + '_artifact'], reference)

    def test_presentation_captions_add_no_acceptance_or_completion_authority(self):
        self.assertTrue(self.result['projection_only'])
        self.assertNotIn('completion_authority', self.result)
        self.assertNotIn('work_complete', self.result)
        self.assertIn('not validity flags', self.result['backend_call_phases_semantics'])
        self.assertEqual(len(self.result['viewports']), 2)
        self.assertLessEqual(len(final.encoded(self.result)), 18000)


if __name__ == '__main__':
    unittest.main()
