"""Stream raw artifact identities without parsing DuckDB or JSONL payloads."""

import argparse
import hashlib
import json
from pathlib import Path


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verify(directory, expected_manifest_sha256):
    directory = directory.absolute()
    path = directory / 'release_manifest.json'
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError('ordinary bounded manifest required')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_manifest_sha256:
        raise ValueError('external manifest SHA differs')
    manifest = json.loads(data)
    body = {k: v for k, v in manifest.items() if k != 'content_sha256'}
    if manifest['schema'] != 'generated-Git-artifact-release/v1' or hashlib.sha256(raw(body)).hexdigest() != manifest['content_sha256']:
        raise ValueError('manifest schema/seal differs')
    blobs = {row['path']: row for row in manifest['git_blobs']}
    for row in manifest['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts or str(relative) != row['path']:
            raise ValueError('safe release path required')
        selected = directory / relative
        if any(p.is_symlink() for p in (selected, *selected.parents)) or selected.stat().st_size != row['bytes']:
            raise ValueError('ordinary exact-size file required')
        digest = hashlib.sha256()
        git_digest = hashlib.sha1(b'blob ' + str(row['bytes']).encode() + b'\0') if row['path'] in blobs else None
        count = 0
        with selected.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                count += len(chunk)
                if count > row['bytes']:
                    raise ValueError('stream exceeds selected size')
                digest.update(chunk)
                if git_digest is not None:
                    git_digest.update(chunk)
        if count != row['bytes'] or digest.hexdigest() != row['sha256']:
            raise ValueError('raw artifact SHA/size differs')
        if git_digest is not None and git_digest.hexdigest() != blobs[row['path']]['git_blob_oid']:
            raise ValueError('original Git blob identity differs')
    return {'files_verified': len(manifest['files']), 'git_blobs_verified': len(blobs),
            'payload_bytes': manifest['payload_bytes'], 'payloads_parsed': False, 'model_calls': 0, 'training_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.expected_manifest_sha256), sort_keys=True))
