"""Export two explicitly selected Git blobs byte-for-byte, without parsing data."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPOSITORY = Path('/home/barberb/lift_coding/external/ipfs_accelerate')
OBJECTS = [
    {'git_blob_oid': '14d6706502842110d16161a81d168281d6989a1c', 'bytes': 142880768,
     'path': 'data/agent_supervisor/formal_verification_tactician_readiness/bundles/index.duckdb'},
    {'git_blob_oid': '9b6ded832adffea56cd1402bb08d1dca484eb3c8', 'bytes': 2022179327,
     'path': 'data/agent_supervisor/proof_grounded_ir_learning/datasets/pgir-objective-ast.jsonl'},
]
PREFIX = 'releases/20261004-git-large-artifacts-v1'


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def seal(value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return raw(value) + b'\n'


def stream_export(row, directory, evidence):
    target = directory / row['path']
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    command = ['git', '-C', str(REPOSITORY), 'cat-file', 'blob', row['git_blob_oid']]
    started = time.monotonic()
    process = None
    error = None
    timed_out = False
    descriptor = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w+b') as output, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=stderr, start_new_session=True)
            while process.poll() is None:
                timed_out = time.monotonic() - started > 180
                if timed_out or os.fstat(output.fileno()).st_size > row['bytes'] or os.fstat(stderr.fileno()).st_size > 8 * 1024 ** 2:
                    raise ValueError('bounded raw export rejected')
                time.sleep(.05)
        except Exception as exception:
            error = type(exception).__name__
        finally:
            cleanup_error = None
            if process is not None and process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                except Exception as exception:
                    cleanup_error = type(exception).__name__
            output.flush()
            os.fsync(output.fileno())
            size = os.fstat(output.fileno()).st_size
            stderr.seek(0)
            stderr_data = stderr.read(8 * 1024 ** 2)
            diagnostic = {'command': command, 'returncode': process.returncode if process else None,
                'timed_out': timed_out, 'error_type': error, 'cleanup_error': cleanup_error,
                'wall_seconds': time.monotonic() - started, 'output_bytes': size,
                'stderr_bytes': os.fstat(stderr.fileno()).st_size,
                'stderr_sha256': hashlib.sha256(stderr_data).hexdigest(), 'payload_parsed': False}
            put(evidence / (row['git_blob_oid'] + '-export.json'), seal(diagnostic))
        if error or cleanup_error or timed_out or process.returncode != 0 or size != row['bytes']:
            raise ValueError('raw blob export failed; partial output and diagnostic preserved')
        output.seek(0)
        digest = hashlib.sha256()
        git_digest = hashlib.sha1(b'blob ' + str(row['bytes']).encode() + b'\0')
        count = 0
        for chunk in iter(lambda: output.read(1024 * 1024), b''):
            digest.update(chunk)
            git_digest.update(chunk)
            count += len(chunk)
        if count != row['bytes'] or git_digest.hexdigest() != row['git_blob_oid']:
            raise ValueError('raw Git blob identity differs')
    return {**row, 'sha256': digest.hexdigest(), 'git_blob_sha1_recomputed': True}


def main():
    directory = WORK / 'git-large-artifacts-v1'
    evidence = WORK / 'git-large-artifact-export-01'
    directory.mkdir(mode=0o700)
    evidence.mkdir(mode=0o700)
    rows = [stream_export(row, directory, evidence) for row in OBJECTS]
    checker = WORK / 'verify_large_git_artifacts.py'
    checker_data = checker.read_bytes()
    put(directory / checker.name, checker_data)
    card = '''---
license: agpl-3.0
tags:
- formal-logic
- generated-artifacts
---

# Retained generated autoformalization artifacts

This append-only research release exports two explicitly selected Git blobs
from `endomorphosis/ipfs_accelerate_py` without parsing or transforming them.
It retains a DuckDB bundle index (142,880,768 bytes) and a generated objective-AST
JSONL artifact (2,022,179,327 bytes). Total raw payload: 2,165,060,095 bytes.

`release_manifest.json` records exact original Git blob IDs, repository paths,
byte counts and SHA256 digests. Git blob identities were independently recomputed
from the raw bytes. Filename descriptions are producer names; payload validity,
schema, completeness, source fidelity, semantic labels, proof authority and
training suitability have not been established by this publication.

No DuckDB connection, JSONL parsing, model call, optimization or prover was run.
No additional reference banks, model backbones or source data were selected.
The original local Git objects and histories remain unchanged. The source GitHub
publication can cite the immutable Hugging Face revision instead of carrying
these oversized historical blobs in its source history.

Download the release and choose its externally published manifest SHA256:

```sh
python -I -B verify_large_git_artifacts.py --directory . --expected-manifest-sha256 SELECTED_SHA256
```

The stdlib checker streams exact file hashes and Git blob IDs without loading
the datasets into a database, data parser or model. The accompanying original
repository license is retained; this publication makes no new licensing or
third-party provenance determination for generated contents.
'''
    put(directory / 'README.md', card.encode())
    license_file = REPOSITORY / 'LICENSE'
    put(directory / 'LICENSE', license_file.read_bytes())
    files = [*[{k: row[k] for k in ('path', 'bytes', 'sha256')} for row in rows]]
    for name in ('verify_large_git_artifacts.py', 'README.md', 'LICENSE'):
        data = (directory / name).read_bytes()
        files.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    public = {'schema': 'generated-Git-artifact-release/v1', 'repo_id': 'Publicus/autoformalization-artifacts',
        'repo_type': 'dataset', 'prefix': PREFIX, 'source_repository': 'github.com/endomorphosis/ipfs_accelerate_py',
        'git_blobs': rows, 'files': files, 'payload_bytes': sum(row['bytes'] for row in rows),
        'payloads_parsed': False, 'model_calls': 0, 'training_executed': False, 'prover_calls': 0,
        'qualified': False, 'source_fidelity_established': False, 'semantic_gold_created': False, 'proof_authority': False}
    manifest = put(directory / 'release_manifest.json', seal(public))
    files.append({'path': 'release_manifest.json', 'bytes': manifest['bytes'], 'sha256': manifest['sha256']})
    input_bindings = []
    for path in (Path(__file__).resolve(), checker, license_file):
        data = path.read_bytes()
        input_bindings.append({'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    plan = {'schema': 'append-only-HF-publication-plan/v1', 'repo_id': public['repo_id'], 'repo_type': 'dataset',
        'prefix': PREFIX, 'directory': str(directory), 'create_if_missing': True, 'files': files,
        'original_input_bindings': input_bindings, 'source_git_repository': str(REPOSITORY), 'original_git_blobs': rows,
        'public_manifest_binding': manifest, 'payload_parsing_authorized_or_executed': False,
        'model_loads': 0, 'training_executed': False, 'qualified': False, 'proof_authority': False}
    binding = put(WORK / 'large_git_artifact_publication_plan.json', seal(plan))
    print(json.dumps({'plan': binding, 'manifest': manifest, 'payload_bytes': public['payload_bytes']}, sort_keys=True))


if __name__ == '__main__':
    main()
