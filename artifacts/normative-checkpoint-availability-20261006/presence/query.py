#!/usr/bin/env python3
"""Read-only exact-state catalog and public Hub metadata survey; no weights fetch.

Run from any directory with Python, duckdb and huggingface_hub available.  The
only writes are new evidence JSON files inside --output-directory. No project
manager, encoder, decoder or numerical/training implementation is constructed.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

BASE = Path('/home/barberb/lift_coding')
SOURCE = BASE / '.worktrees/contextual-legal-runtime-accelerate-20261006'
STORE = BASE / 'external/ipfs_accelerate/model_manager.duckdb'
PRIOR = BASE / 'artifacts/autoencoder-progress-reconciliation-20261006/datasets/reconciliation-findings.json'
CUSTODY = BASE / 'artifacts/decoder-profile-recovery-20261006/asset-survey/contextual-state-custody-survey.json'
SKILL = Path('/home/barberb/.codex/plugins/cache/openai-curated-remote/hugging-face/1.0.0/skills/cli/SKILL.md')
REPOS = ('Publicus/legal-ir-autoencoder', 'Publicus/legal-ir-autoencoder-384d',
         'Publicus/legal-ir-autoencoder-768d')
MAX_LOCAL = 6 * 1024 * 1024
MAX_MANIFEST = 1024 * 1024
PINS = {}


def raw_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def local_bytes(path, maximum=MAX_LOCAL):
    path = Path(path)
    before = path.stat()
    if not path.is_file() or not 0 < before.st_size <= maximum:
        raise ValueError('bounded regular local evidence file required')
    value = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('local evidence changed while reading')
    pin = {'path': str(path), 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
    PINS[str(path)] = pin
    return value, pin


def stat_witness(path):
    try:
        value = Path(path).stat()
        return {'exists': True, 'device': value.st_dev, 'inode': value.st_ino,
                'mode': value.st_mode, 'bytes': value.st_size,
                'mtime_ns': value.st_mtime_ns, 'ctime_ns': value.st_ctime_ns}
    except FileNotFoundError:
        return {'exists': False}


def git_blob(value):
    return hashlib.sha1(b'blob ' + str(len(value)).encode('ascii') + b'\0' + value).hexdigest()


def exception_types(error):
    # Keep lock/network failure types without logging authentication material.
    names = []
    while error is not None and len(names) < 5:
        names.append(type(error).__name__)
        error = error.__cause__
    return names


def catalog(targets):
    before = {'store': stat_witness(STORE), 'wal': stat_witness(str(STORE) + '.wal')}
    imported = []
    result = {'path': str(STORE), 'read_only': True, 'native_load_attempts': 1,
              'native_source': 'IRPersistentCatalogSource', 'whole_store_hash_or_copy': False,
              'scope': 'Exact serialization SHA matches in the one explicitly selected live store; not an all-host inventory.'}
    try:
        sys.path.insert(0, str(SOURCE))
        from ipfs_accelerate_py.model_catalog.sources.ir_persistent import IRPersistentCatalogSource
        snapshot = IRPersistentCatalogSource(path=STORE).load()
        bindings = snapshot.ir_bindings
        lane_records = {}
        for binding in bindings:
            key = binding['ir_family_id'] + ':' + str(binding['dimension']) + ':' + binding['dimension_role']
            declaration = binding['declaration']
            lane_records.setdefault(key, []).append({name: binding[name] for name in (
                'record_id', 'ir_family_id', 'dimension', 'dimension_role', 'schema_version',
                'task_id', 'profile_id', 'format_id', 'checkpoint_sha256', 'role')})
            lane_records[key][-1]['declared_readiness'] = {name: declaration[name] for name in (
                'trained', 'initialization_only', 'runtime_ready', 'teacher_qualified', 'proof_authority')}
        result['existing_family_dimension_role_records'] = lane_records
        result['existing_family_dimension_role_counts'] = {key: len(rows) for key, rows in lane_records.items()}
        result['lane_scope'] = 'Current persisted declarations; lane counts are availability metadata, not inferred runtime readiness or source fidelity.'
        result.update({'status': 'assessed', 'binding_count': len(bindings),
                       'binding_snapshot_revision': snapshot.binding_snapshot_revision,
                       'catalog_revision': snapshot.revision,
                       'exact_sha_matches': {sha: [row for row in bindings
                           if row['checkpoint_sha256'] == sha] for sha in targets}})
        for name, module in sorted(sys.modules.items()):
            if name.startswith('ipfs_accelerate_py') and getattr(module, '__file__', None):
                path = Path(module.__file__).resolve(strict=True)
                if not path.is_relative_to(SOURCE):
                    raise ValueError('foreign project import origin')
                _, pin = local_bytes(path)
                imported.append({'module': name, 'pin': pin})
        forbidden = [name for name in sys.modules if name == 'torch' or
                     name.startswith(('torch.', 'transformers', 'huggingface_hub')) or
                     name == 'ipfs_accelerate_py.model_manager']
        if forbidden:
            raise ValueError('forbidden model/manager/library import')
        result['forbidden_imports'] = forbidden
    except Exception as error:
        result.update({'status': 'unassessed', 'failure_types': exception_types(error),
                       'no_lock_bypass_copy_or_writer_connection_attempted': True})
        result.pop('exact_sha_matches', None)
    after = {'store': stat_witness(STORE), 'wal': stat_witness(str(STORE) + '.wal')}
    result.update({'stat_before': before, 'stat_after': after,
                   'stat_endpoints_unchanged': before == after,
                   'native_import_source_pins': imported,
                   'stat_scope': 'Cooperative endpoint witness; not whole-file authentication or an atomic filesystem snapshot.'})
    if before != after:
        result['status'] = 'unassessed_concurrent_store_change'
        result.pop('exact_sha_matches', None)
    return result


def file_metadata(file):
    lfs = None
    if file.lfs is not None:
        lfs = {'sha256': file.lfs.sha256, 'size': file.lfs.size,
               'pointer_size': file.lfs.pointer_size}
    return {'path': file.rfilename, 'bytes': file.size, 'git_blob_oid': file.blob_id,
            'lfs': lfs}


def mentions(value, shas, prefix='$'):
    result = []
    if type(value) is dict:
        for key, item in value.items():
            result.extend(mentions(item, shas, prefix + '.' + key))
    elif type(value) is list:
        for index, item in enumerate(value):
            result.extend(mentions(item, shas, prefix + '[' + str(index) + ']'))
    elif type(value) is str:
        for sha in shas:
            if sha in value:
                result.append({'checkpoint_sha256': sha, 'json_path': prefix,
                               'exact_scalar': value == sha, 'value': value[:400]})
    return result


def manifest_candidate(file):
    name = file['path'].rsplit('/', 1)[-1]
    return file['bytes'] is not None and 0 < file['bytes'] <= MAX_MANIFEST and (
        name in ('release_manifest.json', 'lane-manifest.json') or
        file['path'].endswith('20261006-contextual-selected-v1/manifest.json') or
        ('normative' in file['path'].lower() and name.endswith('manifest.json')))


def public_manifest(repo, commit, file, targets, output):
    url = 'https://huggingface.co/' + repo + '/resolve/' + commit + '/' + urllib.parse.quote(file['path'], safe='/')
    result = {'repository': repo, 'revision': commit, 'path': file['path'],
              'metadata': file, 'url': url}
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            value = response.read(MAX_MANIFEST + 1)
        if len(value) > MAX_MANIFEST or len(value) != file['bytes']:
            raise ValueError('manifest byte bound/size mismatch')
        blob = git_blob(value)
        if file['lfs'] is not None:
            if hashlib.sha256(value).hexdigest() != file['lfs']['sha256']:
                raise ValueError('manifest LFS identity mismatch')
        elif blob != file['git_blob_oid']:
            raise ValueError('manifest Git blob identity mismatch')
        decoded = json.loads(value)
        dst = output / 'manifests' / repo.replace('/', '--') / file['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('xb') as handle:
            handle.write(value)
        result.update({'status': 'assessed', 'retained_pin': {'path': str(dst),
                       'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()},
                       'git_blob_oid': blob, 'target_mentions': mentions(decoded, targets),
                       'root_metadata': {key: item for key, item in decoded.items()
                           if type(item) in (str, int, bool) or item is None}
                           if type(decoded) is dict else {}})
    except Exception as error:
        result.update({'status': 'unassessed', 'failure_types': exception_types(error)})
    return result


def hub(assets, output):
    from huggingface_hub import HfApi
    api = HfApi(token=False)
    results = []
    for repo in REPOS:
        entry = {'repository': repo, 'authentication': 'anonymous public metadata only',
                 'weights_downloaded': False, 'writes': False}
        try:
            info = api.model_info(repo, revision='main', timeout=20,
                                  files_metadata=True, token=False)
            commit = info.sha
            if info.private or len(commit) != 40:
                raise ValueError('public immutable repository snapshot required')
            files = [file_metadata(file) for file in info.siblings or []]
            if not files or len(files) > 10000 or any(file['bytes'] is None or not file['git_blob_oid'] for file in files):
                raise ValueError('complete bounded file identity metadata required')
            matches = {}
            for asset in assets:
                pin = asset['original_complete_state_pin']
                matched = []
                for file in files:
                    lfs = file['lfs']
                    if file['bytes'] != pin['bytes']:
                        continue
                    if (lfs is not None and lfs['sha256'] == pin['sha256']) or (
                            lfs is None and file['git_blob_oid'] == asset['local_git_blob_oid']):
                        matched.append({**file, 'identity_join': 'LFS SHA256' if lfs else 'Git blob OID from exact local serialization bytes'})
                matches[pin['sha256']] = matched
            manifests = [public_manifest(repo, commit, file, matches.keys(), output)
                         for file in files if manifest_candidate(file)]
            after = api.model_info(repo, revision='main', timeout=20,
                                   expand=['sha'], token=False).sha
            release_roots = {}
            for file in files:
                parts = file['path'].split('/')
                if len(parts) >= 2 and parts[0] == 'releases':
                    prefix = '/'.join(parts[:2])
                elif len(parts) >= 3 and parts[0] == 'experiments':
                    prefix = '/'.join(parts[:3])
                else:
                    prefix = '<other root>'
                release_roots[prefix] = release_roots.get(prefix, 0) + 1
            entry['existing_release_roots_file_counts'] = release_roots
            entry.update({'status': 'assessed', 'public': True, 'immutable_revision': commit,
                          'main_revision_after': after, 'main_stable_at_endpoints': after == commit,
                          'file_metadata_count': len(files), 'file_metadata': files,
                          'exact_serialization_identity_matches': matches,
                          'bounded_publication_manifests': manifests,
                          'normative_named_paths': [file['path'] for file in files if 'normative' in file['path'].lower()],
                          'identity_scope': 'All sibling file metadata at the recorded immutable repository revision; original weight contents were not downloaded. Exact local serialization SHA256 is joined to Hub Git blob OID/LFS SHA metadata, not a fresh remote weight SHA256 measurement.',
                          'manifest_scope': 'All bounded release_manifest.json/lane-manifest.json files, the original contextual mirror manifest, and normative-named manifests; SHA mentions alone do not establish runtime/model qualification.'})
        except Exception as error:
            entry.update({'status': 'unassessed', 'failure_types': exception_types(error)})
        results.append(entry)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prior_bytes, prior_pin = local_bytes(PRIOR)
    custody_bytes, custody_pin = local_bytes(CUSTODY)
    _, script_pin = local_bytes(Path(__file__).resolve())
    _, skill_pin = local_bytes(SKILL)
    prior = json.loads(prior_bytes)
    custody = json.loads(custody_bytes)
    assets = []
    for state in prior['newer_normative_training_already_published']['states']:
        assets.append({'kind': 'new_normative', 'dimension': state['dimension'],
                       'arm': state['arm'], 'role': state['role'],
                       'native_tensor_sha256_from_retained_survey': state['native_tensor_sha256'],
                       'original_complete_state_pin': state['original_complete_state_pin']})
    for lane in custody['lanes']:
        assets.append({'kind': 'legacy_contextual', 'dimension': lane['dimension'],
                       'role': 'selected', 'original_complete_state_pin': lane['original_checkpoint_pin']})
    if len(assets) != 10 or sum(state['role'] == 'selected' for state in assets[:8]) != 4:
        raise ValueError('exact four normative selected plus four last aliases and two legacy states required')
    for asset in assets:
        expected = asset['original_complete_state_pin']
        value, pin = local_bytes(expected['path'])
        if pin != expected:
            raise ValueError('original complete state pin changed')
        asset['local_git_blob_oid'] = git_blob(value)
    targets = [asset['original_complete_state_pin']['sha256'] for asset in assets]
    catalog_result = catalog(targets)
    hub_results = hub(assets, output)
    before_pins = [PINS[path] for path in sorted(PINS)]
    after_pins = []
    for pin in before_pins:
        _, after_pin = local_bytes(pin['path'])
        after_pins.append(after_pin)
    unchanged = before_pins == after_pins
    result = {'schema': 'autoencoder-selected-state-presence-readonly-survey/v1',
              'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'completed': unchanged and catalog_result['status'] == 'assessed' and
                  all(entry['status'] == 'assessed' for entry in hub_results),
              'script_pin': script_pin, 'HF_skill_pin': skill_pin,
              'reused_query_origin': {'path': '/home/barberb/lift_coding/artifacts/autoencoder-progress-reconciliation-20261006/datasets/presence/query.py',
                  'sha256': 'f2611ed5465bd412130e1a26f6a6809dbdb9d516d8813ad862e7b6031c1de2b6'},
              'fresh_output_preserves_old_receipts': True,
              'prior_original_normative_evidence_pin': prior_pin,
              'prior_original_contextual_custody_pin': custody_pin,
              'assets': assets, 'current_selected_ModelManager': catalog_result,
              'current_public_Hub_snapshots': hub_results,
              'local_pins_before': before_pins, 'local_pins_after': after_pins,
              'original_assets_evidence_and_source_bytes_unchanged': unchanged,
              'operations': {'catalog_writes': False, 'HF_writes': False,
                  'model_or_encoder_loaded': False, 'inference_or_training': False,
                  'weights_downloaded': False, 'anonymous_public_metadata_requests': True,
                  'bounded_publication_manifest_downloads_only': True,
                  'source_or_git_mutation': False},
              'authority': {'new_model_quality_measured': False, 'runtime_admitted': False,
                  'teacher_qualified': False, 'proof_authority': False}}
    with (output / 'presence-survey.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'completed': result['completed'], 'catalog_status': catalog_result['status'],
                      'binding_count': catalog_result.get('binding_count'),
                      'catalog_exact_sha_match_counts': {sha: len(rows) for sha, rows in catalog_result.get('exact_sha_matches', {}).items()},
                      'hub': [{'repository': entry['repository'], 'status': entry['status'],
                               'revision': entry.get('immutable_revision'),
                               'file_metadata_count': entry.get('file_metadata_count'),
                               'exact_sha_match_counts': {sha: len(rows) for sha, rows in entry.get('exact_serialization_identity_matches', {}).items()},
                               'manifest_count': len(entry.get('bounded_publication_manifests', []))}
                              for entry in hub_results],
                      'output': str(output / 'presence-survey.json')}, sort_keys=True))


if __name__ == '__main__':
    main()
