"""Portable source-bound request/PNG handoff vectors; no operational claims."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

BASE = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', Path(__file__).resolve().parents[1]))
SCRIPTS = Path(os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS', BASE / 'scripts'))
spec = importlib.util.spec_from_file_location('handoff_consumer', SCRIPTS / 'swissknife_visual_functional_final_coverage.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)

class RequestProofHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.directory = self.root / 'runtime' / 'desktop'; self.directory.mkdir(parents=True)
        self.report = self.directory / 'workflow.json'
        self.scenario = {'backend_bindings': [{'binding_id': 'read.native'}], 'phases': {phase: [{}] for phase in f.BACKEND_PHASES[:3]}}
        target = self.root / 'swissknife/test/e2e/functional-workflows/authored.json'; target.parent.mkdir(parents=True); target.write_bytes(f.encoded(self.scenario))
        requests = []; observations = []; artifacts = []
        for index, phase in enumerate(('primary_result', 'failure_recovery')):
            call = f.encoded({'binding_id': 'read.native', 'correlation_id': 'request-' + str(index), 'input': {'cid': 'same-input'}})
            refs = {}
            for kind in ('receipt', 'event'):
                path = self.directory / ('backend/' + kind + '-raw-cid-' + str(index) + '.json'); path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'{"call":' + call + b'}'); ref = f.reference(self.root, path); artifacts.append(ref); refs[kind + '_artifact'] = ref['path']
            requests.append({'request_index': index, 'phase': phase, 'step_index': 0, 'generation': index + 1, 'binding_id': 'read.native', 'correlation_id': 'request-' + str(index), 'call_sha256': hashlib.sha256(call).hexdigest()})
            observations.append({'request_phase_index': index, 'owner': 'native.owner', 'tool_id': 'read_content', 'binding_id': 'read.native', 'transport': 'mcp', 'outcome': 'success', 'receipt_verified': True, 'semantic_result_verified': True, 'correlation_id': 'request-' + str(index), 'receipt_id': 'receipt-id-' + str(index), 'event_dag_cid': 'event-id-' + str(index), 'result_assertion': {'pointer': '/cid', 'operator': 'equals', 'actual': 'same-input', 'expected': 'same-input'}, **refs})
        self.child = {'app_id': 'authored', 'backend_call_count': 2, 'backend_call_phases': {phase: int(phase in ('primary_result', 'failure_recovery')) for phase in f.BACKEND_PHASES}, 'backend_request_phases': {'schema': f.BACKEND_REQUEST_PHASE_SCHEMA, 'requests': requests}, 'backend_observations': [observations[1], observations[0], {**copy.deepcopy(observations[1]), 'result_assertion': {'pointer': '/bytes_sha256', 'operator': 'equals', 'actual': '9' * 64, 'expected': '9' * 64}}], 'artifacts': artifacts}
    def rows(self): return f._project_backend_observations(self.root, self.child, self.report)
    def test_distinct_primary_and_retry_requests_stay_distinct_literal_rows(self):
        rows, additional = self.rows(); self.assertEqual(len(rows), 2); self.assertEqual(additional, [])
        self.assertEqual([row['request_phase']['phase'] for row in rows], ['failure_recovery', 'primary_result'])
        for row in rows:
            original = self.child['backend_observations'][row['observation_index']]
            self.assertEqual(row['result_assertion'], original['result_assertion'])
            witness = self.child['backend_request_phases']['requests'][original['request_phase_index']]
            self.assertEqual(row['request_phase']['correlation_id'], witness['correlation_id']); self.assertEqual(row['request_phase']['call_sha256'], witness['call_sha256'])
            for kind in ('receipt', 'event'):
                ref = row[kind + '_artifact']; reconstructed = {**ref, 'path': str((self.directory / ref['path']).relative_to(self.root))}
                self.assertEqual(reconstructed, next(record for record in self.child['artifacts'] if record['path'] == original[kind + '_artifact']))
                self.assertIn('raw-cid-', ref['path'])
            self.assertFalse({'owner_observation', 'artifact_indexes', 'same_result_as'} & set(row))
    def test_extra_predicate_only_groups_with_its_same_request(self):
        rows, _ = self.rows(); self.assertEqual(rows[0]['additional_result_assertions'], [{'observation_index': 2, 'result_assertion': self.child['backend_observations'][2]['result_assertion']}]); self.assertNotIn('additional_result_assertions', rows[1])
    def test_equal_owner_and_result_never_merges_distinct_native_calls(self):
        self.child['backend_observations'] = self.child['backend_observations'][:2]
        rows, _ = self.rows(); self.assertEqual(len(rows), 2); self.assertNotEqual(rows[0]['receipt_artifact'], rows[1]['receipt_artifact'])
    def test_artifact_identity_is_part_of_group_key(self):
        last = self.child['backend_observations'][2]; source = self.root / last['event_artifact']; target = self.directory / 'backend/event-other.json'; target.write_bytes(source.read_bytes()); ref = f.reference(self.root, target); self.child['artifacts'].append(ref); last['event_artifact'] = ref['path']
        self.assertEqual(len(self.rows()[0]), 3)
    def test_changed_actual_call_bytes_cannot_borrow_request_identity(self):
        target = self.root / self.child['backend_observations'][0]['receipt_artifact']; target.write_bytes(target.read_bytes().replace(b'same-input', b'other-input'))
        with self.assertRaises(ValueError): self.rows()
    def test_literal_native_marker_payload_remains_literal(self):
        value = {'review_ref': 'native', 'owner_observation': 0, 'artifact_indexes': [1, 2], 'typed': [False, 0, 0.0, None]}; self.child['backend_observations'][0]['result_assertion'].update(actual=value, expected=value)
        self.assertEqual(f.encoded(self.rows()[0][0]['result_assertion']['actual']), f.encoded(value))
    def test_legacy_without_request_witness_keeps_full_refs(self):
        self.child.pop('backend_request_phases'); self.child['backend_observations'] = self.child['backend_observations'][:1]; self.child['backend_observations'][0].pop('request_phase_index')
        row = self.rows()[0][0]; self.assertNotIn('request_phase', row); self.assertEqual(row['receipt_artifact']['path'], self.child['backend_observations'][0]['receipt_artifact'])

class ErrorImageRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/dev/shm'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.directory = self.root / 'desktop'; self.directory.mkdir(); self.report = self.directory / 'workflow.json'
        self.raw = self.png(2); target = self.directory / 'retained.png'; target.write_bytes(self.raw); self.ref = f.reference(self.root, target)
        self.scenario = {'phases': {
            'primary_result': [{'op': 'assert', 'requirement_id': 'result_1', 'probe': {'kind': 'image_state', 'selector': '#preview', 'pointer': '/natural_width'}, 'operator': 'equals', 'expected': 2}],
            'persist_reopen': [{'op': 'assert', 'requirement_id': 'persist_reopen', 'probe': {'kind': 'image_state', 'selector': '#preview[data-layers="two"]', 'pointer': '/natural_width'}, 'operator': 'equals', 'expected': 2}],
            'failure_recovery': [{'op': 'assert', 'checkpoint_id': 'error_observed', 'probe': {'kind': 'text', 'selector': '#error'}, 'operator': 'contains', 'expected': 'bad'}, {'op': 'assert', 'checkpoint_id': 'error_image_retained', 'probe': {'kind': 'image_state', 'selector': '#preview[data-layers="two"]', 'pointer': '/natural_width'}, 'operator': 'equals', 'expected': 2, 'retained_from': {'primary_result': 0, 'persist_reopen': 0}}, {'op': 'click', 'selector': '#retry'}]}}
        self.child = {'image_observations': [], 'artifacts': [self.ref], 'semantic_assertions': [], 'error_observations': []}
        for phase, index in [('primary_result', 0), ('persist_reopen', 0), ('failure_recovery', 1)]:
            step = self.scenario['phases'][phase][index]
            self.child['image_observations'].append({'phase': phase, 'step_index': index, 'selector': step['probe']['selector'], 'decoded': True, 'natural_width': 2, 'natural_height': 2, 'visible_area': 64, 'content_sha256': hashlib.sha256(self.raw).hexdigest(), 'source_sha256': hashlib.sha256(b'data:image/png;base64,' + base64.b64encode(self.raw)).hexdigest(), 'image_artifact': self.ref})
            self.child['error_observations' if phase == 'failure_recovery' else 'semantic_assertions'].append({'phase': phase, 'step_index': index, 'observed': {'actual': 2}})
    @staticmethod
    def png(width, color=b'\xff\x00\x00\xff'):
        def chunk(kind, raw): return struct.pack('>I', len(raw)) + kind + raw + struct.pack('>I', zlib.crc32(kind + raw) & 0xffffffff)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, 2, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\x00' + color * width) * 2)) + chunk(b'IEND', b'')
    def check(self): return f.validate_decoded_images(self.root, self.child, self.scenario, self.report)
    def test_exact_source_bound_png_retained_with_distinct_literal_selectors(self):
        self.assertEqual(len(self.check()), 3); self.assertNotEqual(self.child['image_observations'][0]['selector'], self.child['image_observations'][1]['selector'])
    def test_historical_single_error_remains_valid(self):
        self.scenario['phases']['failure_recovery'].pop(1); self.child['image_observations'].pop(); self.child['error_observations'] = []; self.assertEqual(len(self.check()), 2); self.assertEqual(len(f._scenario_error_checkpoints(self.scenario)), 1)
    def test_missing_or_duplicate_same_step_native_snapshot_refused(self):
        for rows in (self.child['image_observations'][:-1], self.child['image_observations'] + [copy.deepcopy(self.child['image_observations'][-1])]):
            old = self.child['image_observations']; self.child['image_observations'] = rows
            with self.assertRaises(ValueError): self.check()
            self.child['image_observations'] = old
    def test_other_phase_or_selector_cannot_supply_retained_image(self):
        for edit in ({'phase': 'primary_result'}, {'selector': '#other'}, {'step_index': 0}):
            old = copy.deepcopy(self.child); self.child['image_observations'][-1].update(edit)
            with self.assertRaises(ValueError): self.check()
            self.child = old
    def test_artifactless_native_dimensions_are_not_encoded_png_retention(self):
        self.child['image_observations'][-1].update(content_sha256=None, image_artifact=None)
        with self.assertRaises(ValueError): self.check()
    def test_forged_content_source_dimensions_or_actual_refused(self):
        for key, value in [('content_sha256', '0' * 64), ('source_sha256', '0' * 64), ('natural_width', 3)]:
            old = copy.deepcopy(self.child); self.child['image_observations'][-1][key] = value
            with self.assertRaises(ValueError): self.check()
            self.child = old
        self.child['error_observations'][0]['observed']['actual'] = 3
        with self.assertRaises(ValueError): self.check()
    def test_independently_valid_other_png_still_fails_cross_phase_identity(self):
        raw = self.png(2, b'\x00\x00\xff\xff'); target = self.directory / 'other.png'; target.write_bytes(raw); ref = f.reference(self.root, target); self.child['artifacts'].append(ref)
        self.child['image_observations'][-1].update(natural_width=2, content_sha256=hashlib.sha256(raw).hexdigest(), source_sha256=hashlib.sha256(b'data:image/png;base64,' + base64.b64encode(raw)).hexdigest(), image_artifact=ref); self.child['error_observations'][0]['observed']['actual'] = 2
        with self.assertRaisesRegex(ValueError, 'changed between'): self.check()
    def test_retained_baselines_are_exact_bounded_original_semantic_assertions(self):
        refs = self.scenario['phases']['failure_recovery'][1]['retained_from']
        for value in (True, -1, 64, 9):
            refs['primary_result'] = value
            with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
        refs['primary_result'] = 0; self.scenario['phases']['primary_result'][0]['requirement_id'] = 'other'
        with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
    def test_wrong_checkpoint_type_temporal_role_or_unknown_refs_refused(self):
        original = copy.deepcopy(self.scenario)
        for mutate in (lambda row: row['probe'].update(kind='text'), lambda row: row['probe'].update(temporal_ms=1), lambda row: row.update(requirement_id='failure_recovery'), lambda row: row['retained_from'].update(other=0)):
            self.scenario = copy.deepcopy(original); mutate(self.scenario['phases']['failure_recovery'][1])
            with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
    def test_checkpoint_after_retry_ui_owner_or_completion_assert_refused(self):
        for action in ({'op': 'click'}, {'op': 'press'}, {'op': 'assert', 'probe': {'kind': 'backend_result'}}, {'op': 'assert', 'requirement_id': 'failure_recovery'}):
            old = copy.deepcopy(self.scenario); self.scenario['phases']['failure_recovery'].insert(1, action)
            with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
            self.scenario = old
    def test_unknown_duplicate_and_foreign_phase_checkpoints_refused(self):
        original = copy.deepcopy(self.scenario)
        for mutate in (lambda d: d['phases']['failure_recovery'].append(copy.deepcopy(d['phases']['failure_recovery'][1])), lambda d: d['phases']['failure_recovery'][1].update(checkpoint_id='other'), lambda d: d['phases']['primary_result'].append(d['phases']['failure_recovery'].pop(1))):
            self.scenario = copy.deepcopy(original); mutate(self.scenario)
            with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
    def test_retained_from_cannot_be_smuggled_on_noncheckpoint(self):
        self.scenario['phases']['failure_recovery'][2]['retained_from'] = {'primary_result': 0, 'persist_reopen': 0}
        with self.assertRaises(ValueError): f._scenario_error_checkpoints(self.scenario)
    def test_child_artifact_closure_and_encoded_bytes_remain_required(self):
        self.child['artifacts'] = []
        with self.assertRaises(ValueError): self.check()

class CaptionCompatibilityTests(unittest.TestCase):
    def test_historical_typed_shared_caption_remains_readable(self):
        base={key: None for key in f._PHASE_FACT_FIELDS['seek']}
        value={'viewports':[{'phase_evidence':{'seek':{'projection_value_ref':'v0'}}}],
               'shared_projection_values':{'v0':base},'shared_projection_values_semantics':f._LEGACY_SHARED_SEMANTICS}
        self.assertEqual(f._expand_projection(value)['viewports'][0]['phase_evidence']['seek'],base)
        value['shared_projection_values_semantics']=f._SHARED_SEMANTICS
        self.assertEqual(f._expand_projection(value)['viewports'][0]['phase_evidence']['seek'],base)
    def test_historical_literal_caption_preserves_exact_typed_original(self):
        original={'viewports':[], 'first':{'native_values':['snow雪',False,0,-0.0,None]*60},'second':{'native_values':['snow雪',False,0,-0.0,None]*60}}
        value=f._factor_review_literals(original);self.assertIn('shared_review_literals',value)
        value['shared_review_literals_semantics']=f._LEGACY_REVIEW_LITERAL_SEMANTICS
        self.assertEqual(f.encoded(f._expand_projection(value)),f.encoded(original))

class PreviousCaptionCompatibilityTests(unittest.TestCase):
    def test_preceding_phase_caption_still_expands_exact_typed_slots(self):
        base={key:None for key in f._PHASE_FACT_FIELDS['seek']}
        value={'viewports':[{'phase_evidence':{'seek':{'projection_value_ref':'v0'}}}],
               'shared_projection_values':{'v0':base},'shared_projection_values_semantics':
               'projection_value_ref: exact same-slot typed shared_projection_values; overrides replace fields, never delete. Equality implies no shared session/element/event/phase.'}
        self.assertEqual(f._expand_projection(value)['viewports'][0]['phase_evidence']['seek'],base)
    def test_preceding_literal_caption_preserves_native_values_and_identity_fields(self):
        original={'viewports':[], 'one':{'native':[False,0,-0.0,None,'snow雪']*100},
                  'two':{'native':[False,0,-0.0,None,'snow雪']*100},'receipt':'distinct-native-CID'}
        value=f._factor_review_literals(original)
        value['shared_review_literals_semantics']='shared_review_literals_reference_key selects same-slot literal JSON in shared_review_literals; expand before phase values. No facts lost or shared session/element/call/event implied.'
        self.assertEqual(f.encoded(f._expand_projection(value)),f.encoded(original))

if __name__ == '__main__': unittest.main()
