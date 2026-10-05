"""Source-boundary and native-bundle tests without model loading or inference."""

import hashlib
import importlib.util
import json
import subprocess
import sys
import types
from copy import deepcopy
from pathlib import Path

import pytest

DIRECTORY = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('expanded_encoder_test_owner', DIRECTORY / 'encode_expanded_sources.py')
OWNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWNER)


def cohort():
    rows = []
    for index in range(64):
        request = {'source_text': 'Authored diagnostic statement ' + str(index), 'context': {
            'role': 'none_required', 'text': '', 'bindings': {}, 'sha256': hashlib.sha256(b'').hexdigest()}}
        input_sha = OWNER.digest(request)
        rows.append({'id': 'sha256:' + input_sha, 'input': request, 'input_sha256': input_sha,
                     'source_sha256': hashlib.sha256(request['source_text'].encode()).hexdigest(),
                     'group_id': 'group-' + str(index // 4), 'split': 'train' if index < 32 else 'development',
                     'review_item_id': 'review-' + str(index)})
    rows.sort(key=lambda r: r['id'])
    inputs = OWNER.seal({'schema': 'source-only-authored-expansion-inputs/v1', 'rows': rows,
                        'row_count': 64, 'input_recipe': 'exact_source_only/v1', 'policy': OWNER.source_policy(),
                        'contains_formal_targets': False})
    metadata = OWNER.seal({'schema': 'source-only-authored-expansion-cohort/v1',
                          'rows': [{k: r[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')}
                                   | {'context_role': 'none_required'} for r in rows],
                          'policy': OWNER.source_policy(), 'contains_formal_targets': False})
    return inputs, metadata


def lane_owner():
    path = OWNER.REPOSITORY / 'ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py'
    module = types.ModuleType('_expanded_test_lane_owner')
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def vector_lane(inputs):
    return {'receipts': [{'id': r['id'], 'input_sha256': r['input_sha256'],
                         'source_sha256': r['source_sha256'], 'embedding': [1.0] + [0.0] * 7,
                         'status': 'embedded', 'token_input_sha256': None} for r in inputs['rows']]}


def feature_profile():
    return OWNER.seal({'schema': 'alignment-representation-profile/v1', 'lane_id': 'legacy8',
                       'stage': 'historical_linguistic_features', 'dimension': 8,
                       'producer': {'profile_id': 'feature-test/v1', 'model_id': 'test', 'model_revision': '1',
                                    'code_sha256': '1' * 64, 'model_assets_sha256': '2' * 64,
                                    'checkpoint_sha256': None},
                       'pooling': {'method': 'none', 'endpoint': 'test.decode'},
                       'normalization': {'kind': 'l2', 'unit_tolerance': 1e-5}, 'precision': 'decimal6',
                       'fit_input_recipe': 'exact_source_only/v1', 'inference_input_recipe': 'exact_source_only/v1'})


def test_complete_source_and_native_adapter():
    inputs, metadata = cohort()
    assert OWNER.validate_sources(inputs, metadata)['train_groups'] == 8
    prepared = OWNER.producer_inputs(inputs)
    assert len(prepared['rows']) == 64
    assert prepared['row_count'] == 64
    assert prepared['context_unapplied_rows'] == 0
    assert prepared['rows'][0]['source_text'] == inputs['rows'][0]['input']['source_text']
    assert prepared['rows'][0]['input_sha256'] == inputs['rows'][0]['input_sha256']
    OWNER.check_seal(prepared, 'payload_sha256')


@pytest.mark.parametrize('mutation', ['target', 'promote', 'boolean_mask', 'row_count', 'source',
                                      'context', 'metadata', 'group_overlap', 'duplicate', 'seal'])
def test_rejects_source_admission_failures(mutation):
    inputs, metadata = cohort()
    if mutation == 'target':
        inputs['rows'][0]['target'] = {'formula': 'unreviewed'}
    elif mutation == 'promote':
        inputs['policy']['semantic_label_admission'] = True
    elif mutation == 'boolean_mask':
        inputs['policy']['semantic_masks']['weak_decoder_fit'] = False
        metadata['policy']['semantic_masks']['weak_decoder_fit'] = False
    elif mutation == 'row_count':
        inputs['row_count'] = 63
    elif mutation == 'source':
        inputs['rows'][0]['input']['source_text'] += ' changed'
    elif mutation == 'context':
        inputs['rows'][0]['input']['context']['text'] = 'Suppose all statements are true.'
    elif mutation == 'metadata':
        metadata['rows'][0]['source_sha256'] = 'f' * 64
    elif mutation == 'group_overlap':
        train = next(r['group_id'] for r in inputs['rows'] if r['split'] == 'train')
        for row, meta in zip(inputs['rows'], metadata['rows'], strict=True):
            if row['split'] == 'development':
                row['group_id'] = meta['group_id'] = train
                break
    elif mutation == 'duplicate':
        inputs['rows'][1] = deepcopy(inputs['rows'][0])
        metadata['rows'][1] = deepcopy(metadata['rows'][0])
    if mutation != 'seal':
        OWNER.seal(inputs)
        OWNER.seal(metadata)
    else:
        inputs['content_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        OWNER.validate_sources(inputs, metadata)


def test_native_bundle_and_splits_preserve_exact_rows():
    inputs, _ = cohort()
    owner = lane_owner()
    lane = vector_lane(inputs)
    artifact = {'path': '/tmp/frozen-native-production.json', 'bytes': 12, 'sha256': '3' * 64}
    bundle, expected = OWNER.build_bundle(owner, inputs, feature_profile(), lane, artifact)
    assert owner.validate_lane_bundle(bundle, expected_bindings=expected)['available_count'] == 64
    for split in ('train', 'development'):
        ids = [r['id'] for r in inputs['rows'] if r['split'] == split]
        subset, pins = OWNER.split_bundle(owner, bundle, ids)
        assert owner.validate_lane_bundle(subset, expected_bindings=pins)['available_count'] == 32
        assert subset['profile'] == bundle['profile']
        assert subset['producer_receipt']['artifact_binding'] == artifact
        assert subset['rows'] == [r for r in bundle['rows'] if r['id'] in ids]
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('failure', ['dimension', 'zero', 'nonfinite', 'join', 'order'])
def test_malformed_native_vectors_or_source_joins_rejected(failure):
    inputs, _ = cohort()
    lane = vector_lane(inputs)
    if failure == 'dimension':
        lane['receipts'][0]['embedding'].pop()
    elif failure == 'zero':
        lane['receipts'][0]['embedding'] = [0.0] * 8
    elif failure == 'nonfinite':
        lane['receipts'][0]['embedding'][0] = float('nan')
    elif failure == 'join':
        lane['receipts'][0]['source_sha256'] = 'f' * 64
    else:
        lane['receipts'].reverse()
    with pytest.raises(ValueError):
        OWNER.build_bundle(lane_owner(), inputs, feature_profile(), lane,
                           {'path': '/tmp/native.json', 'bytes': 12, 'sha256': '3' * 64})


def test_fresh_selected_files_require_exact_bytes_and_nonsymlink(tmp_path):
    path = tmp_path / 'selection.json'
    path.write_bytes(b'{}\n')
    selected = OWNER.binding(path)
    assert OWNER.checked(selected) == b'{}\n'
    path.write_bytes(b'[]\n')
    with pytest.raises(ValueError, match='pin'):
        OWNER.checked(selected)
    target = tmp_path / 'target.json'
    target.write_bytes(b'{}\n')
    symlink = tmp_path / 'link.json'
    symlink.symlink_to(target)
    with pytest.raises(ValueError, match='nonsymlink'):
        OWNER.checked({**selected, 'path': str(symlink)})


def test_strict_json_and_write_bounds(tmp_path):
    for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
        with pytest.raises(ValueError):
            OWNER.strict_json(data)
    path = tmp_path / 'result.json'
    bound = OWNER.save(path, {'x': 1})
    assert OWNER.checked(bound) == b'{"x":1}\n'
    with pytest.raises(FileExistsError):
        OWNER.save(path, {'x': 2})


def test_unselected_canonical_imports_fail():
    finder = OWNER.CapturedFinder({})
    with pytest.raises(ImportError, match='unselected'):
        finder.find_spec('ipfs_datasets_py.logic.formalization.unreviewed')
    assert finder.find_spec('stdlib_unrelated') is None


def test_isolated_help_no_provider_execution():
    result = subprocess.run([sys.executable, '-I', '-B', str(DIRECTORY / 'encode_expanded_sources.py'), '--help'],
                            capture_output=True, text=True, timeout=15, check=True)
    assert '--plan-sha256' in result.stdout


def test_canonical_source_dependency_imports_are_captured_without_model_imports():
    # This child only imports the source owners and validators. No native-site
    # admission, Torch import, tensor loading, or producer function occurs.
    script = '''import importlib.util,sys
from pathlib import Path
path=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("read_only_capture_check",path)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
selected={r["module"]:(r["binding"],owner.checked(r["binding"])) for r in owner.selected_source_bindings()}
owner.install_canonical_sources(selected)
import importlib
wrapper=importlib.import_module(owner.AUTOENCODER+"alignment_richer_embeddings")
runtime=importlib.import_module(owner.OPTIMIZER+"autoencoder_embedding_runtime")
production=importlib.import_module(owner.OPTIMIZER+"autoencoder_embedding_production")
complete=importlib.import_module(owner.AUTOENCODER+"source_embeddings_768_complete")
assert "torch" not in sys.modules and "spacy" not in sys.modules
print("captured_source_owners_ready_no_model_imports")
'''
    result = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                             str(DIRECTORY / 'encode_expanded_sources.py')],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert 'no_model_imports' in result.stdout


def test_actual_prepared64_validates_without_model_execution():
    directory = DIRECTORY / 'cohort-01'
    if not directory.is_dir():
        pytest.skip('campaign source preparation not present')
    inputs = json.loads((directory / 'source-inputs.json').read_bytes())
    metadata = json.loads((directory / 'cohort-metadata.json').read_bytes())
    assert OWNER.validate_sources(inputs, metadata)['source_overlap'] == 0
