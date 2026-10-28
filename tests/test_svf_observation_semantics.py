"""Authored RAM proof-shape vectors; no browser, provider or task acceptance."""
import base64
import copy
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(Path(__file__).resolve().parents[1])))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', str(REPOSITORY / 'scripts')))
sys.path.insert(0, str(REPOSITORY / 'scripts')); sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('semantics_fixture', REPOSITORY / 'tests/test_svf_final_viewport_coverage.py')
fixture_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture_module)
final = fixture_module.final; worker = fixture_module.worker; llm = fixture_module.llm


class ObservationSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='svf-observation-semantics-', dir='/dev/shm'); self.addCleanup(self.tmp.cleanup)
        self.addCleanup(patch.stopall); self.f = fixture_module.Fixture(Path(self.tmp.name))
        patch.object(final, '_node_source_snapshot', side_effect=self.f.source_vector).start()
        patch.object(final, '_node_source_snapshots', side_effect=lambda root, profile, apps: {
            app['app_id']: self.f.source_vector(root, profile, {'app_id': app['app_id']}, app) for app in apps}).start()
        self.g = self.f.group(); patch.object(worker, 'ROOT', self.f.root).start()

    def image_case(self):
        scenario = self.f.scenario(self.f.apps[0])
        probe = {'kind': 'image_state', 'selector': '[data-saved-project-image]', 'pointer': '/natural_width'}
        for phase in ('primary_result', 'persist_reopen'):
            scenario['phases'][phase][1].update(probe=probe, expected=64)
        retained = {'op': 'assert', 'checkpoint_id': 'error_image_retained', 'probe': probe,
                    'operator': 'equals', 'expected': 64, 'retained_from': {'primary_result': 1, 'persist_reopen': 1}}
        scenario['phases']['failure_recovery'].insert(2, retained)
        self.f.write('swissknife/test/e2e/functional-workflows/app-0.json', scenario)
        children = []
        for index, original in enumerate(self.g['children']):
            child = copy.deepcopy(original)
            raw = bytearray(129); raw[:8] = b'\x89PNG\r\n\x1a\n'; raw[12:16] = b'IHDR'; raw[16:24] = struct.pack('>II', 64, 64); raw[-1] = index
            name = self.g['folder'] / child['viewport']['name'] / 'native-saved.png'
            self.f.write(str(name.relative_to(self.f.root)), bytes(raw)); ref = final.reference(self.f.root, name)
            child['artifacts'].append(ref); child['image_observations'] = []
            for phase, step in [('primary_result', 1), ('persist_reopen', 1), ('failure_recovery', 2)]:
                child['image_observations'].append({'phase': phase, 'step_index': step, 'selector': probe['selector'],
                    'decoded': True, 'natural_width': 64, 'natural_height': 64, 'visible_area': 4096,
                    'source_sha256': hashlib.sha256(b'data:image/png;base64,' + base64.b64encode(raw)).hexdigest(),
                    'content_sha256': hashlib.sha256(raw).hexdigest(), 'image_artifact': ref})
            for row in child['semantic_assertions']:
                if row['phase'] in ('primary_result', 'persist_reopen'):
                    row['probe'] = probe; row['observed'] = {'operator': 'equals', 'actual': 64, 'expected': 64}
                elif row['phase'] == 'failure_recovery': row['step_index'] += 1
            child['error_observations'].append({'phase': 'failure_recovery', 'step_index': 2, 'checkpoint_id': 'error_image_retained',
                'probe': probe, 'observed': {'operator': 'equals', 'actual': 64, 'expected': 64}})
            children.append({'entry': {'report': {'path': str((self.g['folder'] / child['viewport']['name'] / 'workflow.json').relative_to(self.f.root))}}, 'data': child})
        return {'children': children}

    def test_native_png_summary_is_exact_and_each_viewport_is_independent(self):
        evidence = self.image_case(); original = copy.deepcopy(evidence)
        value = worker._independent_review_guidance(self.f.profile, self.g['task'], evidence)
        groups = value['native_saved_png_equalities']['groups']
        self.assertEqual([row['viewport'] for row in groups], ['desktop', 'mobile'])
        self.assertNotEqual(groups[0]['png_bytes_sha256'], groups[1]['png_bytes_sha256'])
        self.assertEqual(groups[0]['steps'], [['primary_result', 1], ['persist_reopen', 1], ['failure_recovery', 2]])
        self.assertEqual(evidence, original)
        self.assertLessEqual(len(final.encoded(value)), 2200)
        self.assertIn('not canvas/layers or unsampled times', value['native_saved_png_equalities']['scope'])
        self.assertFalse(any(key in value for key in ('passed', 'decision', 'acceptance', 'work_complete')))

    def test_missing_snapshot_refuses_an_equality_summary(self):
        evidence = self.image_case(); evidence['children'][0]['data']['image_observations'].pop()
        with self.assertRaises(ValueError): worker._independent_review_guidance(self.f.profile, self.g['task'], evidence)

    def test_rehashed_changed_png_cannot_be_presented_as_retained(self):
        evidence = self.image_case(); child = evidence['children'][0]['data']; row = child['image_observations'][-1]
        raw = bytearray((self.f.root / row['image_artifact']['path']).read_bytes()); raw[-1] = 9
        target = self.g['folder'] / 'desktop' / 'changed-native.png'; self.f.write(str(target.relative_to(self.f.root)), bytes(raw))
        ref = final.reference(self.f.root, target); child['artifacts'].append(ref)
        row.update(image_artifact=ref, content_sha256=hashlib.sha256(raw).hexdigest(),
                   source_sha256=hashlib.sha256(b'data:image/png;base64,' + base64.b64encode(raw)).hexdigest())
        with self.assertRaises(ValueError): worker._independent_review_guidance(self.f.profile, self.g['task'], evidence)

    def test_forged_source_hash_refuses_an_equality_summary(self):
        evidence = self.image_case(); evidence['children'][0]['data']['image_observations'][-1]['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError): worker._independent_review_guidance(self.f.profile, self.g['task'], evidence)

    def test_separate_validated_baselines_do_not_gain_a_universal_equality_requirement(self):
        evidence = self.image_case()
        scenario_path = self.f.root / 'swissknife/test/e2e/functional-workflows/app-0.json'
        scenario = final.parse(scenario_path.read_bytes())
        second = copy.deepcopy(scenario['phases']['failure_recovery'][2])
        second.update(checkpoint_id='recovery_image_retained', retained_from={'primary_result': 2, 'persist_reopen': 2})
        scenario['phases']['failure_recovery'].append(second); self.f.write(str(scenario_path.relative_to(self.f.root)), scenario)
        for child in evidence['children']:
            rows = child['data']['image_observations']
            for phase, index in [('primary_result', 2), ('persist_reopen', 2), ('failure_recovery', 5)]:
                rows.append({**rows[0], 'phase': phase, 'step_index': index, 'content_sha256': '1' * 64, 'source_sha256': '2' * 64})
        # The strict consumer owns baseline qualification. This unit vector
        # prevents the optional summary from imposing extra cross-group policy.
        with patch.object(final, 'validate_decoded_images', side_effect=lambda _root, child, _scenario, _path: child['image_observations']):
            value = worker._independent_review_guidance(self.f.profile, self.g['task'], evidence)
        self.assertLessEqual(len(final.encoded(value)), 2200)

    def test_without_retained_steps_there_is_no_png_or_media_restore_claim(self):
        value = worker._independent_review_guidance(self.f.profile, self.g['task'], {'children': []})
        self.assertNotIn('native_saved_png_equalities', value)
        self.assertIn('native src URI, not media bytes', value['hashes'])
        self.assertIn('not a viewport label', value['identity'])
        self.assertIn('unsupported is not rendered output', value['requirements'])
        self.assertIn('no producer pass forces acceptance', value['requirements'])

    def test_real_model_compiler_retains_literal_contract_evidence_and_caps(self):
        class BeforeProvider(Exception): pass
        captured = {}; validated = self.f.validated(self.g); expected = final.projection(self.f.root, self.g['report'])
        def stop(_root):
            frame = inspect.currentframe().f_back
            while frame and 'prompt' not in frame.f_locals: frame = frame.f_back
            captured.update(prompt=frame.f_locals['prompt'], settings=frame.f_locals['settings'], contract=frame.f_locals['contract'])
            raise BeforeProvider()
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, 'storage_refusal', return_value=None), patch.object(llm, '_load_backend', side_effect=stop) as provider:
            with self.assertRaises(BeforeProvider):
                worker.model('config/swissknife_visual_functional_supervisor.json', self.g['task'], 'review',
                    [str(self.g['report'].relative_to(self.f.root))], [row['path'] for row in validated['images']], self.g['folder'] / 'visual-review-audit.json')
            provider.assert_called_once()
        inputs = {Path(row['path']).name: row['content'] for row in captured['contract']['input_files']}
        context = final.parse(inputs['context.json']); projection = final.parse(inputs['evidence-0.json'])
        self.assertEqual(context['final_workflow_evidence'], final.binding(self.g['task'], validated))
        self.assertEqual(context['app_contract']['primary_workflow'], self.f.apps[0]['primary_workflow'])
        self.assertEqual(final.encoded(final._expand_projection(projection)), final.encoded(final._expand_projection(expected)))
        self.assertIn('evidence_interpretation', context)
        self.assertLessEqual(len(captured['prompt'].encode()), 32768)
        self.assertEqual([captured['settings'][key] for key in ('modelContextBytes', 'maxOutputTokens', 'maxTurns')], [32768, 8192, 8])
        for child in self.g['children']: self.assertEqual(captured['prompt'].count(child['session_id']), 1)

    def test_invalid_independent_source_refuses_before_guidance_or_provider(self):
        data = json.loads(self.g['report'].read_bytes()); data['source_sha256']['scripts/swissknife_visual_functional_worker.py'] = '0' * 64
        self.f.write(str(self.g['report'].relative_to(self.f.root)), data)
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
                patch.object(worker, '_independent_review_guidance') as guidance, patch.object(llm, 'invoke_task_model') as provider:
            with self.assertRaises(ValueError): worker.model('config/swissknife_visual_functional_supervisor.json', self.g['task'], 'review',
                [str(self.g['report'].relative_to(self.f.root))], [row['result_screenshot']['path'] for row in self.g['children']], self.g['folder'] / 'never.json')
            guidance.assert_not_called(); provider.assert_not_called()


if __name__ == '__main__': unittest.main()
