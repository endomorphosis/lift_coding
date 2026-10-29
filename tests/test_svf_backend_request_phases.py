"""Authored protocol facts test request/receipt joins, not actual executions."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import base64
import struct
import zlib

REPO = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', Path(__file__).resolve().parents[1]))
CANDIDATE = os.environ.get('SVF_VPC_CANDIDATE_SCRIPTS')
MODULE = Path(CANDIDATE) / 'swissknife_visual_functional_final_coverage.py' if CANDIDATE else REPO / 'scripts/swissknife_visual_functional_final_coverage.py'
spec = importlib.util.spec_from_file_location('request_phase_consumer_under_test', MODULE)
final = importlib.util.module_from_spec(spec); spec.loader.exec_module(final)


class BackendRequestPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scenario = {'backend_bindings': [{'binding_id': 'authored.binding'}],
                         'phases': {p: [{}] for p in final.BACKEND_PHASES[:3]}}
        requests = []; observations = []
        for index, phase in enumerate(('primary_result', 'failure_recovery')):
            # Deliberate JavaScript exponent/Unicode spellings: Python's JSON
            # serializer cannot be used to hash these exact native wire bytes.
            call = ('{"binding_id":"authored.binding","correlation_id":"authored-%d",'
                    '"input":{"precision":1e-7,"label":"Δ"}}' % index).encode()
            paths = {}
            for kind in ('receipt', 'event'):
                name = '%s-%d.json' % (kind, index)
                (self.root / name).write_bytes(b'{"call":' + call + b',"kind":' + json.dumps(kind).encode() + b'}')
                paths[kind + '_artifact'] = name
            observations.append({'request_phase_index': index, 'binding_id': 'authored.binding',
                                 'correlation_id': 'authored-%d' % index, **paths})
            requests.append({'request_index': index, 'phase': phase, 'step_index': 0,
                             'generation': 1, 'binding_id': 'authored.binding',
                             'correlation_id': 'authored-%d' % index,
                             'call_sha256': hashlib.sha256(call).hexdigest()})
        self.child = {'backend_call_count': 2,
                      'backend_call_phases': {p: int(p in ('primary_result', 'failure_recovery')) for p in final.BACKEND_PHASES},
                      'backend_request_phases': {'schema': final.BACKEND_REQUEST_PHASE_SCHEMA, 'requests': requests},
                      'backend_observations': observations}

    def test_native_phase_is_bound_to_each_distinct_original_receipt_call(self):
        rows = final.validate_backend_request_phases(self.root, self.child, self.scenario)
        self.assertEqual([r['phase'] for r in rows], ['primary_result', 'failure_recovery'])
        self.assertNotEqual(rows[0]['correlation_id'], rows[1]['correlation_id'])

    def test_legacy_omission_never_infers_a_phase(self):
        legacy = {'backend_observations': [{'correlation_id': 'historical'}]}
        self.assertIsNone(final.validate_backend_request_phases(self.root, legacy, self.scenario))
        legacy['backend_observations'][0]['request_phase_index'] = 0
        with self.assertRaises(ValueError): final.validate_backend_request_phases(self.root, legacy, self.scenario)

    def test_changed_ordinal_phase_step_generation_correlation_hash_or_counts_refused(self):
        edits = [
            lambda d: d['backend_request_phases']['requests'][0].update(request_index=1),
            lambda d: d['backend_request_phases']['requests'][0].update(phase='invented'),
            lambda d: d['backend_request_phases']['requests'][0].update(step_index=True),
            lambda d: d['backend_request_phases']['requests'][0].update(step_index=9),
            lambda d: d['backend_request_phases']['requests'][0].update(generation=True),
            lambda d: d['backend_request_phases']['requests'][0].update(correlation_id='foreign'),
            lambda d: d['backend_request_phases']['requests'][0].update(call_sha256='0' * 64),
            lambda d: d['backend_call_phases'].update(primary_result=0),
            lambda d: d['backend_observations'][0].update(request_phase_index=1),
            lambda d: d['backend_observations'][0].update(request_phase_index=True),
        ]
        for change in edits:
            with self.subTest(change=edits.index(change)):
                value = copy.deepcopy(self.child); change(value)
                with self.assertRaises(ValueError): final.validate_backend_request_phases(self.root, value, self.scenario)

    def test_raw_event_call_change_cannot_inherit_the_receipt_phase(self):
        target = self.root / self.child['backend_observations'][0]['event_artifact']
        target.write_bytes(target.read_bytes().replace(b'1e-7', b'1e-6'))
        with self.assertRaises(ValueError): final.validate_backend_request_phases(self.root, self.child, self.scenario)

    def test_valid_step_cannot_escape_its_window_generation(self):
        self.child['phase_evidence'] = {'phases': [{'phase': 'primary_result', 'generation_before': 2, 'generation_after': 3}]}
        with self.assertRaises(ValueError): final.validate_backend_request_phases(self.root, self.child, self.scenario)


class DecodedImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.folder = self.root / 'app'; self.folder.mkdir()
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
        self.raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff\x00\x00\xff' * 2 + b'\x00' + b'\x00\x00\xff\xff' * 2))
                    + chunk(b'IEND', b''))
        target = self.folder / 'decoded.png'; target.write_bytes(self.raw)
        self.ref = final.reference(self.root, target)
        self.row = {'phase': 'primary_result', 'step_index': 0, 'selector': '#export-preview', 'decoded': True,
                    'natural_width': 2, 'natural_height': 2, 'visible_area': 64,
                    'content_sha256': hashlib.sha256(self.raw).hexdigest(),
                    'source_sha256': hashlib.sha256(b'data:image/png;base64,' + base64.b64encode(self.raw)).hexdigest(),
                    'image_artifact': self.ref}
        self.scenario = {'phases': {'primary_result': [{'op': 'assert', 'probe': {'kind': 'image_state', 'selector': '#export-preview', 'pointer': '/decoded'}}]}}
        self.child = {'image_observations': [self.row], 'artifacts': [self.ref], 'semantic_assertions': [
            {'phase': 'primary_result', 'step_index': 0, 'observed': {'actual': True}}], 'error_observations': []}
        self.report = self.folder / 'workflow.json'

    def test_exact_decoded_png_source_bytes_are_independently_joined(self):
        rows = final.validate_decoded_images(self.root, self.child, self.scenario, self.report)
        self.assertEqual(rows[0]['content_sha256'], self.ref['sha256'])

    def test_png_hash_source_dimensions_semantic_value_and_closure_cannot_be_substituted(self):
        changes = [lambda d: d['image_observations'][0].update(content_sha256='0' * 64),
                   lambda d: d['image_observations'][0].update(source_sha256='0' * 64),
                   lambda d: d['image_observations'][0].update(natural_width=3),
                   lambda d: d['image_observations'][0].update(step_index=1),
                   lambda d: d['semantic_assertions'][0]['observed'].update(actual=False),
                   lambda d: d.update(artifacts=[])]
        for number, change in enumerate(changes):
            with self.subTest(change=number):
                value = copy.deepcopy(self.child); change(value)
                with self.assertRaises(ValueError): final.validate_decoded_images(self.root, value, self.scenario, self.report)

    def test_corrupt_raw_png_cannot_retain_the_old_image_identity(self):
        (self.folder / 'decoded.png').write_bytes(self.raw + b'changed')
        with self.assertRaises(ValueError): final.validate_decoded_images(self.root, self.child, self.scenario, self.report)


if __name__ == '__main__': unittest.main()
