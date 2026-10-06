"""Pure staging fixtures: exact bytes, state-only extraction and dependency joins."""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('all_weights_stager', HERE / 'stage_all_weights.py')
STAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGER)


class StagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.root_patch = patch.object(STAGER, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def source(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return STAGER.binding(path)

    def descriptor(self, value, pointer='/model_state'):
        data = STAGER.raw(value)
        return {'json_pointer': pointer, 'key': 'model_state',
                'numeric_leaf_count': STAGER.numeric_leaf_count(value),
                'canonical_json_bytes': len(data), 'canonical_json_sha256': hashlib.sha256(data).hexdigest(),
                'optimizer_only': False, 'state_parameter_key_count': len(value)}

    def json_weight(self, name, document, state, embedded=False, pointer='/model_state'):
        selected = self.source(name, json.dumps(document, ensure_ascii=False).encode())
        return {**selected, 'format': 'JSON', 'family': 'fixture_decoder', 'schema': 'fixture/v1',
                'json_states': [self.descriptor(state, pointer)], 'embedded_in_report': embedded}

    def empty_remote(self):
        coverage = {'schema': 'all-project-model-weights-prior-publication-coverage/v1', 'remote_file_references': []}
        verification = {'schema': 'all-project-model-weights-prior-remote-verification/v1',
                        'status': 'all_prior_release_files_verified_unchanged_at_current_snapshot',
                        'all_prior_release_files_verified': True,
                        'all_current_release_paths_preserved_exact_content': True, 'remote_files': []}
        return coverage, verification

    def test_gzip_is_deterministic_and_byte_exact(self):
        data = b'{  "weights": [1, 2, 3] }\n'
        first = self.root / 'a.gz'
        second = self.root / 'b.gz'
        STAGER.gzip_bytes(first, data)
        STAGER.gzip_bytes(second, data)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(gzip.decompress(first.read_bytes()), data)
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.verify_gzip(first, len(data) - 1, hashlib.sha256(data).hexdigest())

    def test_rfc6901_pointer_escaping(self):
        document = {'a/b': {'~item': [{'state': [2.0]}]}}
        self.assertEqual(STAGER.state_pointer(document, '/a~1b/~0item/0/state'), [2.0])
        for pointer in ('a', '/a~2b', '/a~1b/~0item/01/state', '/missing'):
            with self.subTest(pointer=pointer), self.assertRaises(STAGER.StagingIntegrityError):
                STAGER.state_pointer(document, pointer)

    def test_source_content_changes_are_rejected(self):
        selected = self.source('model.json', b'[1]')
        with self.assertRaises(STAGER.StagingIntegrityError):
            with STAGER.checked_source(selected):
                Path(selected['path']).write_bytes(b'[2]')

    def test_source_symlinks_are_rejected(self):
        selected = self.source('model.json', b'[1]')
        target = self.root / 'alias.json'
        target.symlink_to(selected['path'])
        with self.assertRaises(STAGER.StagingIntegrityError):
            with STAGER.checked_source({**selected, 'path': str(target)}):
                pass

    def test_inventory_device_inode_binding_is_checked(self):
        selected = self.source('model.json', b'[1]')
        info = Path(selected['path']).stat()
        selected['inode'] = {'device': info.st_dev, 'inode': info.st_ino}
        with STAGER.checked_source(selected):
            pass
        selected['inode']['device'] += 1
        with self.assertRaises(STAGER.StagingIntegrityError):
            with STAGER.checked_source(selected):
                pass

    def test_original_binding_dedup_retains_one_exact_content_representative(self):
        one = self.source('one.json', b'[1]')
        two = self.source('two.json', b'[1]')
        three = self.source('three.json', b'[2]')
        deduplicated = STAGER.deduplicate_original_bindings({item['path']: item for item in (one, two, three)})
        self.assertEqual(deduplicated, sorted([one, three], key=lambda item: item['path']))

    def test_clean_json_roundtrip_retains_original_layout_and_all_aliases(self):
        state = {'tensor': [1, 2.5]}
        row = self.json_weight('original/checkpoint.json', {'schema': 'fixture', 'model_state': state}, state)
        alias = self.source('copy/checkpoint.json', Path(row['path']).read_bytes())
        second = {**row, **alias}
        groups, sources = STAGER.group_weights([row, second])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(sources), 2)
        record = STAGER.prepare_group(groups[0], {}, self.root / 'release')
        self.assertEqual(record['aliases'], ['copy/checkpoint.json', 'original/checkpoint.json'])
        self.assertEqual(gzip.decompress((self.root / 'release' / record['storage']['path']).read_bytes()),
                         Path(row['path']).read_bytes())

    def test_mixed_report_extracts_every_declared_state_without_report_body(self):
        state = {'tensor': [1, 2.5]}
        optimizer = {'moments': [0.1, 0.2], 'step': 2}
        document = {'model_state': state, 'optimizer_state': optimizer,
                    'examples': ['PRIVATE_TRAINING_BODY_CANARY']}
        row = self.json_weight('report.json', document, state, embedded=True)
        row['json_states'].append(self.descriptor(optimizer, '/optimizer_state'))
        record = STAGER.prepare_group([row], {}, self.root / 'release')
        data = gzip.decompress((self.root / 'release' / record['storage']['path']).read_bytes())
        self.assertNotIn(b'PRIVATE_TRAINING_BODY_CANARY', data)
        capsule = json.loads(data)
        self.assertEqual(len(capsule['states']), 2)
        values = {item['metadata']['json_pointer']: item['value'] for item in capsule['states']}
        self.assertEqual(values, {'/model_state': state, '/optimizer_state': optimizer})

    def test_mixed_report_root_or_bad_state_digest_rejected(self):
        state = {'tensor': [1, 2.5]}
        root_row = self.json_weight('root.json', state, state, embedded=True, pointer='')
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.prepare_group([root_row], {}, self.root / 'release')
        row = self.json_weight('report.json', {'model_state': state}, state, embedded=True)
        row['json_states'][0]['canonical_json_sha256'] = '0' * 64
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.prepare_group([row], {}, self.root / 'release')

    def test_existing_verified_remote_full_byte_match_reused(self):
        state = {'tensor': [1, 2.5]}
        row = self.json_weight('checkpoint.json', {'model_state': state}, state)
        reference = {'repo_id': 'Publicus/legal-ir-autoencoder', 'repo_type': 'model', 'revision': 'a' * 40,
                     'path_in_repository': 'prior/model.json', 'bytes': row['bytes'], 'sha256': row['sha256']}
        record = STAGER.prepare_group([row], {(row['sha256'], row['bytes']): [reference]}, self.root / 'release')
        self.assertEqual(record['storage'], {'kind': 'existing_verified_immutable_HF_file', 'references': [reference]})
        self.assertFalse((self.root / 'release').exists())

    def test_remote_coverage_requires_complete_exact_byte_joins(self):
        coverage, verification = self.empty_remote()
        reference = {'repo_id': 'Publicus/legal-ir-autoencoder', 'repo_type': 'model', 'revision': 'a' * 40,
                     'path_in_repository': 'prior/model.json', 'bytes': 3, 'sha256': 'b' * 64}
        coverage['remote_file_references'] = [reference]
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.verified_remote_index(coverage, verification)
        verification['remote_files'] = [{'repo_id': reference['repo_id'], 'immutable_revision': reference['revision'],
                                         'path_in_repository': reference['path_in_repository'], 'bytes': 4,
                                         'sha256': reference['sha256'], 'current_contents_unchanged': True}]
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.verified_remote_index(coverage, verification)
        verification['remote_files'][0]['bytes'] = 3
        index = STAGER.verified_remote_index(coverage, verification)
        self.assertEqual(index[('b' * 64, 3)], [reference])

    def binary_triplet(self):
        model = self.source('triplet/model.safetensors', b'fixture-model')
        optimizer = self.source('triplet/optimizer.safetensors', b'fixture-optimizer')
        sidecar_body = {'schema': 'source-vector-reconstruction-checkpoint/v1',
                        'config': {'architecture': {'input_dimension': 8}, 'training_ids': ['hash-only-id']},
                        'normalization': {'mean': [0.1], 'rms': [0.2]},
                        'model_file': {**model, 'path': 'model.safetensors'},
                        'optimizer_file': {**optimizer, 'path': 'optimizer.safetensors'}}
        sidecar = self.source('triplet/checkpoint.json', STAGER.raw(STAGER.sealed(sidecar_body)) + b'\n')
        rows = [{**selected, 'format': 'safetensors', 'family': 'fixture_ae', 'schema': None,
                 'json_states': [], 'embedded_in_report': False, 'metadata_sidecar': sidecar}
                for selected in (model, optimizer)]
        return rows, sidecar

    def test_binary_triplet_exact_sidecar_and_dependency_joins(self):
        rows, sidecar = self.binary_triplet()
        records, originals = STAGER.prepare_sidecars(rows, {}, self.root / 'release')
        self.assertEqual(len(records), 1)
        self.assertEqual(originals, {sidecar['path']: sidecar})
        self.assertEqual(len(records[0]['weight_dependencies']), 2)
        self.assertEqual({item['weight_alias'] for item in records[0]['weight_dependencies']},
                         {'triplet/model.safetensors', 'triplet/optimizer.safetensors'})
        restored = gzip.decompress((self.root / 'release' / records[0]['storage']['path']).read_bytes())
        self.assertEqual(restored, Path(sidecar['path']).read_bytes())

    def test_missing_optimizer_dependency_is_rejected(self):
        rows, _sidecar = self.binary_triplet()
        with self.assertRaises(STAGER.StagingIntegrityError):
            STAGER.prepare_sidecars(rows[:1], {}, self.root / 'release')

    def test_full_offline_staging_accounts_for_all_sources_and_pins_plan(self):
        self.source('LICENSE', b'fixture repository license\n')
        state = {'tensor': [1, 2.5]}
        clean = self.json_weight('clean.json', {'model_state': state}, state)
        mixed = self.json_weight('report.json', {'model_state': state, 'examples': ['CANARY']}, state, embedded=True)
        coverage, verification = self.empty_remote()
        coverage_binding = self.source('coverage.json', STAGER.raw(STAGER.sealed(coverage)) + b'\n')
        inventory = {'schema': 'all-local-autoformalization-model-weight-inventory/v1', 'weights': [clean, mixed],
                     'frozen_for_publication': True, 'read_only_originals': True, 'models_loaded': 0,
                     'training_executed': False, 'uploads': 0, 'prior_publication_coverage_binding': coverage_binding}
        inventory_binding = self.source('inventory.json', STAGER.raw(STAGER.sealed(inventory)) + b'\n')
        verification['coverage_binding'] = coverage_binding
        verification_binding = self.source('verification.json', STAGER.raw(STAGER.sealed(verification)) + b'\n')
        arguments = argparse.Namespace(inventory=Path(inventory_binding['path']), inventory_sha256=inventory_binding['sha256'],
                                       coverage=Path(coverage_binding['path']), coverage_sha256=coverage_binding['sha256'],
                                       remote_verification=Path(verification_binding['path']),
                                       remote_verification_sha256=verification_binding['sha256'],
                                       output=self.root / 'stage', workers=2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(STAGER.stage(arguments), 0)
        report = json.loads((arguments.output / 'staging.json').read_bytes())
        plan = json.loads((arguments.output / 'publication-plan.json').read_bytes())
        catalog = json.loads((arguments.output / 'release' / 'catalog.json').read_bytes())
        self.assertTrue(report['all_inventory_source_weights_accounted_for'])
        self.assertEqual(report['source_container_count'], 2)
        self.assertEqual(len(catalog['weight_containers']), 2)
        self.assertNotIn(str(self.root), (arguments.output / 'release' / 'catalog.json').read_text())
        for item in plan['files']:
            selected = STAGER.binding(Path(plan['directory']) / item['path'])
            self.assertEqual({**selected, 'path': item['path']}, item)
        original_paths = {item['path'] for item in plan['original_input_bindings']}
        self.assertTrue({clean['path'], mixed['path']} <= original_paths)
        aliases = json.loads((arguments.output / 'source-alias-bindings.json').read_bytes())
        self.assertTrue({clean['path'], mixed['path'], str(self.root / 'LICENSE'), str(inventory_binding['path']),
                         str(coverage_binding['path']), str(verification_binding['path'])}
                        <= {item['path'] for item in aliases['original_sources']})
        self.assertEqual(plan['original_source_alias_bindings'], STAGER.binding(arguments.output / 'source-alias-bindings.json'))
        self.assertIn(plan['original_source_alias_bindings'], plan['original_input_bindings'])
        self.assertLess(report['publication_plan_binding']['bytes'], 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
