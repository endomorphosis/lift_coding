"""Prepare four opaque Git archives and 27 raw checkpoint JSONs; never publish."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
INVENTORY = OUT / 'model-payload-inventory-01/report.json'
INVENTORY_SHA = 'd024446ade17b4e197a4e2c958caf1a003b5f497cc7ce13718583116844c3d34'
DATASETS = ROOT / 'external/ipfs_datasets'
EVIDENCE_PREFIX = 'releases/20261004-git-large-evidence-v1'
WEIGHTS_PREFIX = 'releases/20261004-retained-checkpoint-weights-v1'
CHECKER = OUT / 'verify_generated_payload_release.py'


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def put(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def seal(value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return raw(value) + b'\n'


def export_archive(row, directory, receipts):
    target = directory / row['path']
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    command = ['git', '-c', 'gc.auto=0', '-C', str(DATASETS), 'cat-file', 'blob', row['git_blob_oid']]
    process = None
    error = None
    timed_out = False
    started = time.monotonic()
    fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w+b') as output, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=stderr, start_new_session=True,
                                       env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'})
            while process.poll() is None:
                timed_out = time.monotonic() - started > 180
                if timed_out or os.fstat(output.fileno()).st_size > row['bytes'] or os.fstat(stderr.fileno()).st_size > 8 * 1024**2:
                    raise ValueError('bounded opaque export rejected')
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
            error_bytes = stderr.read(8 * 1024**2)
            put(receipts / (row['git_blob_oid'] + '.json'), seal({
                'schema': 'raw-Git-archive-export/v1', 'command': command,
                'returncode': process.returncode if process else None, 'error_type': error,
                'timed_out': timed_out, 'cleanup_error': cleanup_error,
                'output_bytes': size, 'expected_bytes': row['bytes'],
                'stderr_bytes': os.fstat(stderr.fileno()).st_size,
                'stderr_sha256': hashlib.sha256(error_bytes).hexdigest(),
                'wall_seconds': time.monotonic() - started,
                'archives_extracted_or_payloads_parsed': False,
            }))
        if error or cleanup_error or timed_out or process.returncode != 0 or size != row['bytes']:
            raise ValueError('archive export failed; partial bytes and receipt preserved')
        output.seek(0)
        digest = hashlib.sha256()
        git_digest = hashlib.sha1(b'blob ' + str(row['bytes']).encode() + b'\0')
        count = 0
        for chunk in iter(lambda: output.read(1024 * 1024), b''):
            digest.update(chunk)
            git_digest.update(chunk)
            count += len(chunk)
        if count != row['bytes'] or git_digest.hexdigest() != row['git_blob_oid']:
            raise ValueError('exported Git blob differs')
    return {**row, 'sha256': digest.hexdigest(), 'git_blob_sha1_recomputed': True}


def finish(directory, rows, *, schema, repo_id, repo_type, prefix, source_repo, card, inputs):
    checker_data = CHECKER.read_bytes()
    put(directory / CHECKER.name, checker_data)
    put(directory / 'README.md', card.encode())
    license_path = DATASETS / 'LICENSE'
    put(directory / 'SOURCE_REPOSITORY_LICENSE', license_path.read_bytes())
    put(directory / 'LICENSE_SCOPE.md', b'# License scope\n\nThe original source repository license is retained in SOURCE_REPOSITORY_LICENSE.\nIt covers its code according to its terms. Opaque generated archive contents and raw\ncheckpoint provenance were not independently inspected or relicensed by this release.\nUpstream assets retain their original rights; this package grants no new rights to them.\n')
    files = [{key: row[key] for key in ['path', 'bytes', 'sha256']} for row in rows]
    for name in [CHECKER.name, 'README.md', 'SOURCE_REPOSITORY_LICENSE', 'LICENSE_SCOPE.md']:
        selected = pin(directory / name)
        files.append({'path': name, 'bytes': selected['bytes'], 'sha256': selected['sha256']})
    manifest = put(directory / 'release_manifest.json', seal({
        'schema': schema, 'repo_id': repo_id, 'repo_type': repo_type, 'prefix': prefix,
        'source_repository': source_repo, 'git_blobs': rows, 'files': files,
        'payload_bytes': sum(row['bytes'] for row in rows),
        'payloads_parsed_during_release_preparation': False,
        'models_loaded_or_executed': False, 'training_executed': False, 'prover_calls': 0,
        'qualified': False, 'source_fidelity_established': False,
        'semantic_gold_created': False, 'proof_authority': False,
    }))
    files.append({'path': 'release_manifest.json', 'bytes': manifest['bytes'], 'sha256': manifest['sha256']})
    inputs.extend([pin(Path(__file__)), pin(CHECKER), pin(license_path), pin(INVENTORY)])
    plan = put(OUT / (directory.name + '_publication_plan.json'), seal({
        'schema': 'append-only-HF-publication-plan/v1', 'repo_id': repo_id, 'repo_type': repo_type,
        'prefix': prefix, 'directory': str(directory), 'create_if_missing': False,
        'files': files, 'original_input_bindings': inputs,
        'source_git_repository': str(DATASETS if repo_type == 'dataset' else ROOT),
        'original_git_blobs': rows, 'public_manifest_binding': manifest,
        'payload_parsing_authorized_or_executed': False,
        'model_loads': 0, 'training_executed': False, 'qualified': False, 'proof_authority': False,
    }))
    spec = importlib.util.spec_from_file_location('raw_release_checker', CHECKER)
    checker = importlib.util.module_from_spec(spec)
    exec(compile(checker_data, str(CHECKER), 'exec'), checker.__dict__)
    verified = checker.verify(directory, manifest['sha256'])
    check = put(OUT / (directory.name + '_integrity.json'), seal({
        'schema': 'prepared-raw-release-integrity/v1', 'plan_binding': plan,
        'manifest_binding': manifest, 'verification': verified, 'network_publication_performed': False,
    }))
    return {'plan_binding': plan, 'manifest_binding': manifest, 'integrity_binding': check,
            'card_binding': pin(directory / 'README.md'), 'payload_bytes': sum(row['bytes'] for row in rows)}


def main():
    inventory_bytes = INVENTORY.read_bytes()
    if hashlib.sha256(inventory_bytes).hexdigest() != INVENTORY_SHA:
        raise ValueError('frozen model/archive inventory differs')
    inventory = json.loads(inventory_bytes)
    archives = inventory['datasets']['new_blobs_over_100MiB']
    if len(archives) != 4 or any(not row['path'].endswith('/evidence.tar.xz') for row in archives):
        raise ValueError('four exact oversized evidence archives required')
    directory = OUT / 'hf-large-evidence-v1'
    directory.mkdir(mode=0o700)
    receipts = OUT / 'hf-large-evidence-export-01'
    receipts.mkdir(mode=0o700)
    rows = [export_archive(row, directory, receipts) for row in archives]
    archive_card = '''---
license: other
tags:
- formal-logic
- opaque-evidence-archive
---

# Retained opaque decoder evidence archives

This append-only release retains four exact `evidence.tar.xz` Git blobs from
`endomorphosis/ipfs_datasets_py`. Total raw payload is 625,978,536 bytes.
Paths identify producer runs for action binding, action consistency, context
boundary training, and generated-field training. These names describe their
producers; the compressed contents were not extracted or parsed for this release.

The manifest records original repository paths, exact byte counts, SHA256 hashes
and independently recomputed Git blob SHA1 identities. No archive extraction,
dataset parser, encoder, model, optimizer or prover ran during preparation.
Content schema, completeness, embedded assets, licensing, semantic labels,
source fidelity, training suitability and proof authority are unestablished.
Archives may contain producer evidence or model/data artifacts; publication does
not certify their contents or grant new rights to upstream material.

Original source-repository license text is retained with an explicit license
scope note. Original local histories and worktrees are preserved. Git source
history can cite the immutable verified Hugging Face revision instead of these
oversized compressed objects. Existing repository files outside this prefix are
not selected for replacement or deletion.

Select the manifest SHA256 from the publication receipt and run:
`python -I -B verify_generated_payload_release.py --directory . --expected-manifest-sha256 SELECTED_SHA256`.
The checker reads raw bytes for integrity only; it never opens archive members.
'''
    evidence = finish(directory, rows, schema='generated-Git-evidence-archive-release/v1',
                      repo_id='Publicus/autoformalization-artifacts', repo_type='dataset',
                      prefix=EVIDENCE_PREFIX, source_repo='github.com/endomorphosis/ipfs_datasets_py',
                      card=archive_card, inputs=[])
    print(json.dumps({'evidence_release': evidence}, sort_keys=True), flush=True)
    weight_directory = OUT / 'hf-retained-checkpoint-weights-v1'
    weight_directory.mkdir(mode=0o700)
    models = inventory['actionable_root_HF_uploads']
    if len(models) != 27:
        raise ValueError('27 exact root checkpoint payloads required')
    model_rows, inputs = [], []
    for row in models:
        path = Path(row['absolute_path'])
        data = path.read_bytes()
        selected = {'path': str(path), 'bytes': row['bytes'], 'sha256': row['sha256']}
        if pin(path) != selected:
            raise ValueError('original checkpoint bytes differ')
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if oid != row['git_blob_oid']:
            raise ValueError('checkpoint Git blob differs')
        put(weight_directory / row['path'], data)
        model_rows.append({'path': row['path'], 'bytes': row['bytes'], 'sha256': row['sha256'],
                           'git_blob_oid': oid, 'git_blob_sha1_recomputed': True,
                           'checkpoint_schema': row['schema']})
        inputs.append(selected)
    card = '''---
license: other
tags:
- formal-logic
- experimental-checkpoint
---

# Retained raw diagnostic checkpoint weights

This append-only release retains 27 exact JSON parameter payloads previously
stored in the root alignment campaign: twelve projection checkpoints, six
typed-source decoder checkpoints, six anchor-head checkpoints and three
constructed native768 source-span initial controls. Total: 69,450,296 bytes.

Initial/final/control roles remain explicit in original filenames and saved
metadata. Projection and decoder states are distinct model families; these
files are not pretrained embedding backbones or a three-lane autoencoder suite.
Constructed initial controls are untrained controls. Saved optimizer state is
preserved where present; no new training, numerical restore or inference ran.

The original diagnostic fits use weak constructed supervision. This release
establishes neither semantic-label admission, independent fidelity, fresh-holdout
accuracy, proof authority nor production compatibility. Raw checkpoints may
retain vocabularies, local paths and training identity hashes. No separate
reference panels or raw input banks are added. Matching producer code, codecs,
source/model identities and runtime dependencies remain loading prerequisites.
No standalone downloaded numerical restore was executed for this release.

All payload bytes, saved flags and metadata remain unchanged. Integrity checker
results concern exact bytes and Git blob identities only, not model quality.
Original repository license text is included with a separate license-scope note;
this publication makes no independent licensing determination or new upstream
rights grant. Existing files outside this selected release prefix are preserved.

Select the manifest SHA256 from the publication receipt and run:
`python -I -B verify_generated_payload_release.py --directory . --expected-manifest-sha256 SELECTED_SHA256`.
The checker streams bytes without JSON checkpoint parsing or loading a model.
'''
    weights = finish(weight_directory, model_rows, schema='raw-retained-checkpoint-weights-release/v1',
                     repo_id='Publicus/legal-ir-autoencoder', repo_type='model', prefix=WEIGHTS_PREFIX,
                     source_repo='github.com/endomorphosis/lift_coding', card=card, inputs=inputs)
    print(json.dumps({'weights_release': weights}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
