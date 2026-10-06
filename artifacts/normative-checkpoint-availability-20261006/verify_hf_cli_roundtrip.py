#!/usr/bin/env python3
"""Private native-CLI downloads and streamed byte-only original-state comparison.

No checkpoint JSON is decoded, no model code/ML library is imported, and no
database is opened. Only public immutable-revision checkpoint files are fetched.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path('/home/barberb/lift_coding')
ROOT = BASE / 'artifacts/normative-checkpoint-availability-20261006'
OUT = ROOT / 'roundtrip'
EXPECTED = {
    'Publicus/legal-ir-autoencoder': 'aed9bff916e52f43f378dc31c93f98e8a9f52ed1',
    'Publicus/legal-ir-autoencoder-384d': '8199354f58af914768c2296c441ccda2f8e39daa',
    'Publicus/legal-ir-autoencoder-768d': '1cc315894142c9d3b05c6fff90556cde7a2578fe',
}


def pin(path):
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    after = path.stat()
    witness = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
    if witness(before) != witness(after):
        raise ValueError('file changed across byte hash')
    return {'path': str(path), 'bytes': before.st_size, 'sha256': digest.hexdigest()}


def raw(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def durable(path, value):
    with path.open('xb') as handle:
        handle.write(raw(value))
        handle.flush()
        os.fsync(handle.fileno())


def closed(value):
    return {key: value[key] for key in ('path', 'bytes', 'sha256')}


def main():
    if OUT.exists():
        raise ValueError('fresh roundtrip directory required; existing receipt/payloads are preserved')
    OUT.mkdir(mode=0o700)
    cli_path = shutil.which('hf')
    if not cli_path:
        raise ValueError('native hf CLI is unavailable')
    version = subprocess.check_output([cli_path, 'version'], text=True).strip()
    summary_path = ROOT / 'publication/publication-summary.json'
    auth_path = ROOT / 'authentication/authenticated-states.json'
    summary_pin, auth_pin = pin(summary_path), pin(auth_path)
    summary = json.loads(summary_path.read_bytes())
    authentication = json.loads(auth_path.read_bytes())
    if not summary['completed'] or len(summary['releases']) != 3 or len(authentication['states']) != 8:
        raise ValueError('complete three-release/eight-original metadata required')
    states = {row['original_checkpoint_pin']['sha256']: row for row in authentication['states']}
    if len(states) != 8:
        raise ValueError('eight distinct original serialization identities required')
    source_before = [pin(row['original_checkpoint_pin']['path']) for row in states.values()]
    for observed in source_before:
        if observed != closed(states[observed['sha256']]['original_checkpoint_pin']):
            raise ValueError('original source pin changed')
    env = dict(os.environ)
    env['HF_HUB_CACHE'] = str(OUT / 'private-hub-cache')
    env['HF_HUB_DISABLE_TELEMETRY'] = '1'
    env['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    results, receipt_pins = [], []
    for index, release in enumerate(summary['releases']):
        repo, revision = release['repository_id'], release['revision']
        if EXPECTED.get(repo) != revision:
            raise ValueError('unexpected repository or immutable revision')
        native_pin = closed(release['native_receipt_pin'])
        if pin(native_pin['path']) != native_pin:
            raise ValueError('native publication receipt changed')
        native = json.loads(Path(native_pin['path']).read_bytes())
        if not native['files_verified'] or native['revision'] != revision:
            raise ValueError('native publication receipt is unverified')
        files = [file for file in native['files'] if '/checkpoints/' in file['path_in_repo']]
        dimension = 384 if repo.endswith('-384d') else 768 if repo.endswith('-768d') else None
        expected_shas = {sha for sha, state in states.items()
                         if dimension is None or state['dimension'] == dimension}
        if {file['sha256'] for file in files} != expected_shas or len(files) != len(expected_shas):
            raise ValueError('complete repository checkpoint inventory differs')
        target = OUT / repo.replace('/', '--')
        command = [cli_path, 'download', repo, *[file['path_in_repo'] for file in files],
                   '--revision', revision, '--local-dir', str(target), '--quiet']
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = {'repository_id': repo, 'revision': revision, 'native_publication_receipt_pin': native_pin,
            'command': command, 'CLI_returncode': completed.returncode, 'started_at_utc': started,
            'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'stdout_bytes': len(completed.stdout), 'stdout_sha256': hashlib.sha256(completed.stdout).hexdigest(),
            'stderr_bytes': len(completed.stderr), 'stderr_sha256': hashlib.sha256(completed.stderr).hexdigest(),
            'complete': False, 'downloaded_files': []}
        if completed.returncode == 0:
            for file in files:
                local = target / file['path_in_repo']
                actual = pin(local)
                source_pin = closed(states[file['sha256']]['original_checkpoint_pin'])
                if actual['sha256'] != source_pin['sha256'] or actual['bytes'] != source_pin['bytes']:
                    raise ValueError('downloaded checkpoint differs from original source bytes')
                result['downloaded_files'].append({'path_in_repo': file['path_in_repo'],
                    'downloaded_pin': actual, 'original_checkpoint_pin': source_pin,
                    'role': states[file['sha256']]['role'], 'dimension': states[file['sha256']]['dimension'],
                    'arm': states[file['sha256']]['arm'], 'downloaded_bytes_equal_original': True,
                    'native_reported_remote_identity': file['remote_identity']})
            result['complete'] = True
        receipt = OUT / ('repository-' + str(index + 1) + '-download.json')
        durable(receipt, result)
        receipt_pins.append(pin(receipt))
        results.append(result)
        print(json.dumps({'repository_id': repo, 'revision': revision, 'downloaded_files': len(result['downloaded_files']),
                          'complete': result['complete'], 'receipt_pin': pin(receipt)}), flush=True)
        if not result['complete']:
            raise ValueError('native CLI download failed; durable receipt records its return code')
    source_after = [pin(item['path']) for item in source_before]
    if source_before != source_after or pin(summary_path) != summary_pin or pin(auth_path) != auth_pin:
        raise ValueError('source metadata/checkpoint bytes changed across roundtrip')
    copies = [file for result in results for file in result['downloaded_files']]
    if len(copies) != 16:
        raise ValueError('exact sixteen public copies required')
    report = {'schema': 'normative-checkpoint-native-HF-CLI-byte-roundtrip/v1', 'completed': True,
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_pin': pin(Path(__file__).resolve()), 'HF_CLI': {'version_output': version,
            'command_path': cli_path, 'resolved_executable_pin': pin(Path(cli_path).resolve()),
            'commands_retained_in_per_repository_receipts': True, 'token_arguments_or_credentials_printed': False},
        'source_publication_summary_pin': summary_pin, 'source_authentication_pin': auth_pin,
        'downloaded_copy_count': 16, 'unique_original_serialization_count': 8,
        'original_tensor_endpoint_count_from_authenticated_metadata': 4,
        'downloaded_weight_bytes': sum(file['downloaded_pin']['bytes'] for file in copies),
        'per_repository_receipt_pins': receipt_pins, 'original_checkpoint_pins_before': source_before,
        'original_checkpoint_pins_after': source_after, 'all_originals_and_source_receipts_unchanged': True,
        'all_16_downloaded_checkpoint_bytes_equal_originals': True,
        'weight_files_private_roundtrip_directory': str(OUT), 'weight_payloads_added_to_Git': False,
        'source_filename_and_immutable_revision_provenance_retained': True,
        'scope': 'Independent native hf CLI download of16 immutable public checkpoint copies and streamed byte/SHA comparison to8 authenticated originals. Metadata/config/README files are not downloaded; existing32-file native publication receipts supply their declared metadata evidence only.',
        'operations': {'native_HF_CLI_weight_downloads': True, 'Hub_upload_or_settings_changes': False,
            'database_read_or_write': False, 'model_or_decoder_or_encoder_loaded': False,
            'checkpoint_JSON_or_tensors_decoded': False, 'model_supplied_Python_executed': False,
            'training_or_new_embeddings': False, 'source_or_ref_changes': False},
        'authority': {'runtime_ready': False, 'teacher_qualified': False, 'proof_authority': False,
            'source_semantics_verified': False, 'quality_qualified': False}}
    final = OUT / 'roundtrip-verification.json'
    durable(final, report)
    print(json.dumps({'completed': True, 'downloaded_copies': 16, 'weight_bytes': report['downloaded_weight_bytes'],
                      'receipt_pin': pin(final)}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'failed': True, 'failure_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
