"""Pure bounded retention tests; inert bytes and no Lean/process invocation.

The root owns admitted pytest execution. Source authoring only parses ASTs.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import types

import pytest


def _load(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


@pytest.fixture(scope='module')
def checker():
    path = Path(os.environ.get('RANKER_CHUNK_CHECKER_SOURCE',
                               str(Path(__file__).with_name('bounded_analytic_checker.py')))).resolve()
    return _load(path, 'bounded_chunk_checker_pure_test')


@pytest.fixture(scope='module')
def helper():
    path = Path(os.environ.get('RANKER_CHUNK_HELPER_SOURCE',
                               str(Path(__file__).with_name('RetainLeanProof.py')))).resolve()
    return _load(path, 'bounded_chunk_helper_pure_test')


def seal(body):
    return (json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def capture(checker, objects=None):
    objects = objects or [('Fixture.olean', b'x' * (65536 + 19)), ('Fixture.ir', b'ir fixture')]
    chunks, rows, files = [], [], {}
    for object_name, data in objects:
        names = []
        for start in range(0, len(data), 65536):
            name = 'LeanProofChunk%03d.bin' % len(chunks)
            raw = data[start:start + 65536]
            files[name] = raw
            names.append(name)
            chunks.append({'name': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        rows.append({'name': object_name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'chunks': names})
    body = {'schema': 'bounded_lean_chunks@1', 'status': 'complete',
            'retention_profile_sha256': checker.RETENTION_PROFILE_SHA256,
            'native_lean_invocations': 1, 'native_lean_returncode': 0,
            'objects': rows, 'chunks': chunks, 'aggregate_raw_object_bytes': sum(len(data) for _, data in objects)}
    files[checker.RETENTION_MANIFEST_NAME] = seal(body)
    return files, body


def test_exact_profile_and_unchanged_native_caps(checker, helper):
    assert checker.RETENTION_PROFILE == helper.PROFILE
    assert checker.RETENTION_PROFILE_SHA256 == helper.PROFILE_SHA256
    assert checker.BOUNDS == {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
                              'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
    assert len(checker.RETENTION_CHUNK_NAMES) + 1 == 62 <= 64
    assert checker.RETENTION_PROFILE['max_raw_object_bytes'] == 3997696
    assert 2 * 3997696 + 262144 + 65536 < 16777216


def test_reconstructs_complete_large_object_and_companion(checker):
    files, body = capture(checker)
    observed, reconstructed = checker._reconstruct_chunks(files, 'Fixture.lean')
    assert observed == body
    assert [(row['name'], len(raw)) for row, raw in reconstructed] == [('Fixture.olean', 65555), ('Fixture.ir', 10)]
    assert reconstructed[0][1] == b'x' * 65555


@pytest.mark.parametrize('attack', ['missing', 'extra', 'reordered_chunks', 'reordered_partition',
    'forged_chunk_hash', 'forged_object_hash', 'changed_chunk', 'duplicate_chunk', 'duplicate_object',
    'unknown_object', 'reordered_objects', 'wrong_total', 'bool_total', 'bool_chunk_bytes',
    'wrong_profile', 'wrong_status', 'wrong_native_calls', 'wrong_native_return', 'missing_main'])
def test_consistently_resealed_manifest_attacks_refused(checker, attack):
    files, body = capture(checker)
    if attack == 'missing':
        del files['LeanProofChunk000.bin']
    elif attack == 'extra':
        files['unexpected.bin'] = b'extra'
    elif attack == 'reordered_chunks':
        body['chunks'][0], body['chunks'][1] = body['chunks'][1], body['chunks'][0]
    elif attack == 'reordered_partition':
        body['objects'][0]['chunks'].reverse()
    elif attack == 'forged_chunk_hash':
        body['chunks'][0]['sha256'] = '0' * 64
    elif attack == 'forged_object_hash':
        body['objects'][0]['sha256'] = '0' * 64
    elif attack == 'changed_chunk':
        files['LeanProofChunk000.bin'] = b'z' * 65536
    elif attack == 'duplicate_chunk':
        body['objects'][0]['chunks'].append(body['objects'][0]['chunks'][0])
    elif attack == 'duplicate_object':
        body['objects'].append(deepcopy(body['objects'][0]))
    elif attack == 'unknown_object':
        body['objects'][0]['name'] = '../Fixture.olean'
    elif attack == 'reordered_objects':
        body['objects'].reverse()
    elif attack == 'wrong_total':
        body['aggregate_raw_object_bytes'] += 1
    elif attack == 'bool_total':
        body['aggregate_raw_object_bytes'] = True
    elif attack == 'bool_chunk_bytes':
        body['chunks'][0]['bytes'] = True
    elif attack == 'wrong_profile':
        body['retention_profile_sha256'] = '0' * 64
    elif attack == 'wrong_status':
        body['status'] = 'retention_inconclusive'
    elif attack == 'wrong_native_calls':
        body['native_lean_invocations'] = True
    elif attack == 'wrong_native_return':
        body['native_lean_returncode'] = 1
    elif attack == 'missing_main':
        body['objects'][0]['name'] = 'Fixture.olean.private'
    files[checker.RETENTION_MANIFEST_NAME] = seal(body)
    with pytest.raises(ValueError):
        checker._reconstruct_chunks(files, 'Fixture.lean')


def test_rejects_short_nonfinal_chunk_even_with_all_hashes_resealed(checker):
    files, body = capture(checker, [('Fixture.olean', b'abcd')])
    files['LeanProofChunk000.bin'] = b'ab'
    files['LeanProofChunk001.bin'] = b'cd'
    body['chunks'] = [{'name': name, 'bytes': 2, 'sha256': hashlib.sha256(files[name]).hexdigest()}
                      for name in ('LeanProofChunk000.bin', 'LeanProofChunk001.bin')]
    body['objects'][0]['chunks'] = [row['name'] for row in body['chunks']]
    files[checker.RETENTION_MANIFEST_NAME] = seal(body)
    with pytest.raises(ValueError, match='nonfinal'):
        checker._reconstruct_chunks(files, 'Fixture.lean')


@pytest.mark.parametrize('attack', ['oversize_chunk', 'too_many_chunks', 'oversize_raw', 'oversize_manifest', 'noncanonical', 'duplicate_key'])
def test_native_capture_and_complete_population_caps_refused(checker, attack):
    if attack == 'too_many_chunks':
        files, body = capture(checker, [('Fixture.olean', b'x' * (62 * 65536))])
    else:
        files, body = capture(checker)
    if attack == 'oversize_chunk':
        files['LeanProofChunk000.bin'] += b'x'
        body['chunks'][0].update(bytes=65537, sha256=hashlib.sha256(files['LeanProofChunk000.bin']).hexdigest())
    elif attack == 'oversize_raw':
        body['aggregate_raw_object_bytes'] = 3997697
    files[checker.RETENTION_MANIFEST_NAME] = seal(body)
    if attack == 'oversize_manifest':
        files[checker.RETENTION_MANIFEST_NAME] += b' ' * 65536
    elif attack == 'noncanonical':
        files[checker.RETENTION_MANIFEST_NAME] = json.dumps(body, indent=2).encode()
    elif attack == 'duplicate_key':
        files[checker.RETENTION_MANIFEST_NAME] = b'{"schema":"ignored",' + seal(body)[1:]
    with pytest.raises(ValueError):
        checker._reconstruct_chunks(files, 'Fixture.lean')


def test_largest_allowed_complete_raw_body(checker):
    files, body = capture(checker, [('Fixture.olean', b'x' * 3997696)])
    observed, reconstructed = checker._reconstruct_chunks(files, 'Fixture.lean')
    assert observed == body and len(body['chunks']) == 61
    assert len(reconstructed[0][1]) == 3997696


def test_helper_runs_stub_once_and_preserves_complete_bytes(helper, checker, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    def stub(command, check):
        calls.append((command, check))
        Path('Fixture.olean').write_bytes(b'z' * 70000)
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(helper.subprocess, 'run', stub)
    assert helper.main(['/inert/pinned/lean', 'Fixture.lean', 'positive']) == 0
    files = {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.name.startswith('LeanProof')}
    body, reconstructed = checker._reconstruct_chunks(files, 'Fixture.lean')
    assert calls == [(['/inert/pinned/lean', '-o', 'Fixture.olean', 'Fixture.lean'], False)]
    assert reconstructed[0][1] == b'z' * 70000 and body['native_lean_invocations'] == 1


def test_helper_nonzero_is_not_a_complete_reconstruction(helper, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    def stub(command, check):
        calls.append(command)
        return types.SimpleNamespace(returncode=7)
    monkeypatch.setattr(helper.subprocess, 'run', stub)
    assert helper.main(['/inert/pinned/lean', 'Fixture.lean', 'negative']) == 7
    body = json.loads(Path(helper.MANIFEST_NAME).read_bytes())
    assert body['status'] == 'native_nonzero' and body['native_lean_returncode'] == 7
    assert body['native_lean_invocations'] == len(calls) == 1


def test_helper_overflow_preserves_inconclusive_manifest(helper, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    def stub(command, check):
        Path('Fixture.olean').write_bytes(b'x' * 3997697)
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(helper.subprocess, 'run', stub)
    assert helper.main(['/inert/pinned/lean', 'Fixture.lean', 'positive']) == 70
    body = json.loads(Path(helper.MANIFEST_NAME).read_bytes())
    assert body['status'] == 'retention_inconclusive' and body['native_lean_returncode'] == 0
    assert body['native_lean_invocations'] == 1
    assert not list(tmp_path.glob('LeanProofChunk*.bin'))
