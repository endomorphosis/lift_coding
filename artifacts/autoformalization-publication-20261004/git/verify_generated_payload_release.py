"""Verify selected release bytes and Git blob identities without decoding payloads."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def verify(directory, expected_manifest_sha256):
    directory = Path(directory).resolve(strict=True)
    path = directory / 'release_manifest.json'
    data = path.read_bytes()
    if len(data) > 4 * 1024**2 or hashlib.sha256(data).hexdigest() != expected_manifest_sha256:
        raise ValueError('externally selected manifest bytes differ')
    manifest = json.loads(data)
    body = {key: value for key, value in manifest.items() if key != 'content_sha256'}
    if hashlib.sha256(raw(body)).hexdigest() != manifest['content_sha256']:
        raise ValueError('manifest seal differs')
    if manifest['schema'] not in {'generated-Git-evidence-archive-release/v1', 'raw-retained-checkpoint-weights-release/v1'}:
        raise ValueError('unsupported release schema')
    blobs = {row['path']: row for row in manifest['git_blobs']}
    paths = set()
    checked_bytes = 0
    for row in manifest['files']:
        relative = row['path']
        parsed = PurePosixPath(relative)
        if not relative or parsed.is_absolute() or '..' in parsed.parts or str(parsed) != relative or relative in paths:
            raise ValueError('unique canonical relative payload path required')
        paths.add(relative)
        selected = directory / relative
        if any(part.is_symlink() for part in [selected, *selected.parents]):
            raise ValueError('symlink payload rejected')
        sha256 = hashlib.sha256()
        sha1 = hashlib.sha1(b'blob ' + str(row['bytes']).encode() + b'\0')
        count = 0
        with selected.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                count += len(chunk)
                if count > row['bytes']:
                    raise ValueError('payload size exceeds declared bytes')
                sha256.update(chunk)
                sha1.update(chunk)
        if count != row['bytes'] or sha256.hexdigest() != row['sha256']:
            raise ValueError('payload byte integrity differs')
        if relative in blobs and sha1.hexdigest() != blobs[relative]['git_blob_oid']:
            raise ValueError('original Git blob identity differs')
        checked_bytes += count
    if not set(blobs) <= paths:
        raise ValueError('all selected Git payloads must be present')
    return {'schema': 'generated-payload-integrity-verification/v1',
            'manifest_sha256': expected_manifest_sha256, 'files_verified': len(paths),
            'bytes_verified': checked_bytes, 'Git_blob_identities_verified': len(blobs),
            'archives_extracted_or_payloads_parsed': False, 'models_loaded_or_executed': False,
            'source_fidelity_established': False, 'semantic_gold_created': False,
            'proof_authority': False, 'production_runtime_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.expected_manifest_sha256), sort_keys=True))
