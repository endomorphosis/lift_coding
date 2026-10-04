"""Verify a downloaded experimental formula-sidecar release without ML imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

MAX_FILE = 32 * 1024 ** 2


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink inputs rejected')
    require(path.is_file() and 0 < path.stat().st_size <= MAX_FILE, 'bounded ordinary file required')
    return path.read_bytes()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key rejected')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON rejected')))


def numerical_leaves(value, depth=0):
    require(depth <= 16, 'saved state depth bound exceeded')
    if type(value) is list:
        return sum(numerical_leaves(v, depth + 1) for v in value)
    require(type(value) in (int, float) and math.isfinite(value), 'finite saved numerical leaf required')
    return 1


def verify(directory, expected_manifest_sha256):
    directory = directory.absolute()
    data = read(directory / 'release_manifest.json')
    require(hashlib.sha256(data).hexdigest() == expected_manifest_sha256, 'external release manifest pin differs')
    manifest = decode(data)
    body = {k: v for k, v in manifest.items() if k != 'content_sha256'}
    require(manifest['schema'] == 'experimental-formula-sidecar-release/v1'
            and hashlib.sha256(raw(body)).hexdigest() == manifest['content_sha256'], 'manifest schema/seal differs')
    seen = set()
    for binding in manifest['files']:
        relative = Path(binding['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and str(relative) == binding['path']
                and binding['path'] not in seen, 'unique safe release path required')
        seen.add(binding['path'])
        value = read(directory / relative)
        require(len(value) == binding['bytes'] and hashlib.sha256(value).hexdigest() == binding['sha256'], 'release file identity differs')
    counts = 0
    for endpoint in manifest['states']:
        state = decode(read(directory / endpoint['path']))
        require(state['schema'] == 'private-native-dimension-source-state/v1'
                and state['dimension'] == endpoint['dimension'] and state['role'] == endpoint['role'], 'state identity differs')
        require(state['optimizer_resumable'] is False and state['architecture']['production_runtime_compatible'] is False,
                'experimental weights-only scope differs')
        require(state['initializer_receipt']['learned_projection_reconstruction'] is False,
                'formula sidecar cannot claim learned vector reconstruction')
        require(hashlib.sha256(raw(state['model_state'])).hexdigest() == endpoint['weights_sha256'] == state['weights_sha256'],
                'saved JSON weights digest differs')
        counts += sum(numerical_leaves(value) for value in state['model_state'].values())
        for field in ('admitted', 'qualified', 'proof_authority', 'source_semantics_verified', 'checkpoint_promoted'):
            require(state[field] is False, 'state authority differs')
    return {'schema': 'experimental-formula-sidecar-integrity-check/v1', 'files_verified': len(seen),
            'states_verified': len(manifest['states']), 'finite_saved_numerical_leaves_checked': counts,
            'model_loads': 0, 'model_calls': 0, 'optimizer_updates': 0, 'runtime_tensor_digest_recomputed': False,
            'semantic_fidelity_or_proof_established': False, 'runtime_restore_smoke_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.directory, arguments.expected_manifest_sha256), sort_keys=True))
