"""Check downloaded experimental decoder weights without importing ML libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def require(value, reason):
    if not value:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key rejected')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON rejected')))


def read(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink input required')
    require(path.is_file() and 0 < path.stat().st_size <= 32 * 1024 ** 2, 'bounded ordinary input required')
    return path.read_bytes()


def finite_count(value, depth=0):
    require(depth <= 16, 'saved weight depth exceeded')
    if type(value) is list:
        return sum(finite_count(v, depth + 1) for v in value)
    require(type(value) in (int, float) and math.isfinite(value), 'finite saved numerical leaf required')
    return 1


def verify(directory, expected_manifest_sha256):
    directory = directory.absolute()
    data = read(directory / 'release_manifest.json')
    require(hashlib.sha256(data).hexdigest() == expected_manifest_sha256, 'external manifest pin differs')
    manifest = decode(data)
    require(manifest['schema'] == 'additional-experimental-decoder-release/v1', 'release schema differs')
    require(hashlib.sha256(raw({k: v for k, v in manifest.items() if k != 'content_sha256'})).hexdigest()
            == manifest['content_sha256'], 'manifest seal differs')
    seen = set()
    for binding in manifest['files']:
        relative = Path(binding['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative) == binding['path']
                and binding['path'] not in seen, 'unique safe release path required')
        seen.add(binding['path'])
        value = read(directory / relative)
        require(len(value) == binding['bytes'] and hashlib.sha256(value).hexdigest() == binding['sha256'],
                'release file identity differs')
    leaves = 0
    extracted = 0
    for endpoint in manifest['states']:
        state = decode(read(directory / endpoint['path']))
        require(state['dimension'] == endpoint['dimension'] and state['role'] == endpoint['role'], 'state identity differs')
        require(hashlib.sha256(raw(state['model_state'])).hexdigest() == state['weights_sha256']
                == endpoint['weights_sha256'], 'weight payload digest differs')
        require(state['optimizer_resumable'] is False, 'weights-only scope differs')
        for field in ('admitted', 'qualified', 'proof_authority', 'source_semantics_verified', 'checkpoint_promoted'):
            require(state[field] is False, 'saved state authority differs')
        if endpoint['extracted_weights_only']:
            require(state['schema'] == 'experimental-native4096-formula-weight-checkpoint/v1'
                    and state['dimension'] == 4096 and state['learned_embedding_reconstruction'] is False,
                    'extracted native4096 formula-head scope differs')
            require(state['training_report_body_included'] is False and state['runtime_restore_smoke_executed'] is False,
                    'extraction or restore scope differs')
            require(hashlib.sha256(raw({k: v for k, v in state.items() if k != 'content_sha256'})).hexdigest()
                    == state['content_sha256'], 'extracted checkpoint seal differs')
            extracted += 1
        else:
            require(state['schema'] == 'private-native-dimension-source-state/v1'
                    and state['architecture']['production_runtime_compatible'] is False,
                    'historical checkpoint scope differs')
            require(state['initializer_receipt']['learned_projection_reconstruction'] is False,
                    'historical formula head cannot claim vector reconstruction')
        leaves += sum(finite_count(v) for v in state['model_state'].values())
    require(len(manifest['states']) == 24 and extracted == 6, 'fixed-cutoff endpoint counts differ')
    return {'schema': 'additional-experimental-decoder-integrity-check/v1', 'files_verified': len(seen),
            'states_verified': 24, 'extracted_native4096_states': extracted, 'finite_weight_leaves_checked': leaves,
            'model_loads': 0, 'model_calls': 0, 'optimizer_updates': 0,
            'runtime_tensor_digest_recomputed': False, 'runtime_restore_smoke_executed': False,
            'source_fidelity_established': False, 'proof_authority': False, 'qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.expected_manifest_sha256), sort_keys=True))
