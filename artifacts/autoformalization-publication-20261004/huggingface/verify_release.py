"""Bounded stdlib integrity check; no numerical inference or trust admission."""

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def read(path, limit=32 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('unsafe file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read(limit + 1)
    finally:
        os.close(fd)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def verify(directory):
    root = Path(directory).resolve(strict=True)
    manifest = json.loads(read(root / 'manifest.json'))
    seal = manifest.pop('content_sha256')
    if hashlib.sha256(encoded(manifest)).hexdigest() != seal:
        raise ValueError('manifest seal mismatch')
    if manifest['schema'] != 'retained-autoformalization-hub-release/v1':
        raise ValueError('unsupported release schema')
    for binding in manifest['files']:
        relative = Path(binding['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe relative path')
        data = read(root / relative)
        if (len(data), hashlib.sha256(data).hexdigest()) != (binding['bytes'], binding['sha256']):
            raise ValueError(f'file pin mismatch: {relative}')
    for asset in manifest['assets']:
        if asset['asset_type'] == 'source384_joint_reconstruction_and_typed_formula_decoder':
            value = json.loads(read(root / asset['checkpoint']['path']))
            if value['schema'] != 'shared-source-384-autoencoder/v2' or value['dimension'] != 384:
                raise ValueError('source384 schema mismatch')
        elif asset['asset_type'] == 'spacy8_linguistic_sparse_heads':
            value = json.loads(read(root / asset['files']['manifest.json']['path']))
            if value['schema'] != 'legacy-linguistic-training-checkpoint/v1' or value['dimension'] != 8:
                raise ValueError('linguistic schema mismatch')
        elif asset['asset_type'] == 'source_span_decoder_with_native768_conditioning':
            value = json.loads(read(root / asset['checkpoint']['path']))
            if value['schema'] != 'native-dimensional-source-span-checkpoint/v1' or value['config']['latent_dimension'] != 768:
                raise ValueError('span decoder schema mismatch')
        else:
            raise ValueError('unknown asset type')
    return {'status': 'integrity_verified', 'file_count': len(manifest['files']) + 1,
            'asset_count': len(manifest['assets']), 'numerical_models_loaded': 0,
            'qualified': False, 'proof_authority': False, 'source_fidelity_established': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), sort_keys=True))
