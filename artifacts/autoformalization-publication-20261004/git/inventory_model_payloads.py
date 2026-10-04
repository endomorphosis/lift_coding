"""Read-only JSON-weight and unpublished datasets-blob inventory."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
OUT = ROOT / 'artifacts/autoformalization-publication-20261004/git'
RUN = OUT / 'model-payload-inventory-01'
PUBLICATION = OUT.parent
ROOT_SNAPSHOT = 'bc64e1a2d3d3428ae3823fd4754d0051a61d485d'
DATASETS = ROOT / '.worktrees/publication-main-20261004/datasets'
MAX_JSON = 64 * 1024**2
MAX_BLOB = 100 * 1024**2
MODEL_KEYS = {'model_state', 'state_dict', 'model_parameters', 'source_parameters',
              'target_parameters', 'encoder_weights', 'decoder_weights', 'parameters',
              'weights', 'encoder', 'decoder', 'model'}
KEY_HINT = re.compile(rb'"(?:' + b'|'.join(k.encode() for k in sorted(MODEL_KEYS)) + rb')"\s*:')
BINARY_SUFFIXES = {'.safetensors', '.pt', '.pth', '.ckpt', '.onnx', '.gguf', '.bin',
                   '.npy', '.npz', '.pkl', '.pickle', '.h5', '.hdf5', '.msgpack', '.tflite'}
ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
for _key in ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE']:
    ENV.pop(_key, None)


def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def git(repo, *args, data=None, allowed=(0,), timeout=90):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'core.fsmonitor=false', '-C', str(repo), *args],
                            capture_output=True, input=data, env=ENV, timeout=timeout)
    if result.returncode not in allowed:
        raise ValueError('read-only Git operation failed: ' + args[0])
    return result.stdout


def text(repo, *args, **kwargs):
    return git(repo, *args, **kwargs).decode().strip()


def tree(repo, ref):
    rows = {}
    for row in git(repo, 'ls-tree', '-r', '-z', ref).split(b'\0'):
        if row:
            properties, name = row.split(b'\t', 1)
            mode, kind, oid = properties.decode().split()
            rows[os.fsdecode(name)] = {'mode': mode, 'kind': kind, 'git_blob_oid': oid}
    return rows


def live_remote(repo):
    rows = []
    for line in git(repo, 'ls-remote', '--heads', 'origin').splitlines():
        oid, name = line.decode().split()
        git(repo, 'cat-file', '-e', oid + '^{commit}')
        rows.append({'ref': name, 'oid': oid})
    if not rows:
        raise ValueError('live remote branch inventory empty')
    objects = set(git(repo, 'rev-list', '--objects', '--no-object-names',
                      *sorted({row['oid'] for row in rows})).decode().splitlines())
    return rows, objects


def numeric_array(value):
    if isinstance(value, list):
        if value and all(type(item) in {float, int} for item in value):
            return True
        return any(numeric_array(item) for item in value)
    if isinstance(value, dict):
        return any(numeric_array(item) for item in value.values())
    return False


def model_fields(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in MODEL_KEYS and isinstance(item, (dict, list)) and numeric_array(item):
                found.add(key)
            found.update(model_fields(item))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                found.update(model_fields(item))
    return found


def main():
    RUN.mkdir(mode=0o700)
    selected = json.loads((PUBLICATION / 'canonical_git/final-selection.json').read_bytes())
    root_entry = next(row for row in selected['snapshots'] if row['name'] == 'root')
    if root_entry['snapshot_commit'] != ROOT_SNAPSHOT:
        raise ValueError('root canonical snapshot selection changed')
    original_head = text(ROOT, 'rev-parse', 'HEAD')
    original_tree = tree(ROOT, original_head)
    snapshot_tree = tree(ROOT, ROOT_SNAPSHOT)
    root_remote, root_published_objects = live_remote(ROOT)
    hf_plan_file = PUBLICATION / 'huggingface/retained_publication_plan.json'
    hf_receipt_file = PUBLICATION / 'huggingface/retained_publication_receipt.json'
    hf_plan = json.loads(hf_plan_file.read_bytes())
    hf_receipt = json.loads(hf_receipt_file.read_bytes())
    if hf_receipt['all_remote_files_verified'] is not True:
        raise ValueError('initial HF receipt does not establish complete remote verification')
    hf_by_sha = {}
    for release in hf_plan['releases']:
        verified = next(row for row in hf_receipt['releases'] if row['repo_id'] == release['repo_id'])
        for row in release['files']:
            hf_by_sha.setdefault(row['sha256'], []).append({
                'repo_id': release['repo_id'], 'path': release['prefix'] + '/' + row['path'],
                'commit_oid': verified['commit_oid'], 'bytes': row['bytes'],
            })
    paths = {ROOT / name for name in set(original_tree) | set(snapshot_tree)
             if name.startswith('artifacts/') and name.endswith('.json')}
    # These two owned campaigns are bounded experiment/publication generations;
    # unrelated archived repositories, wheels, caches and private source banks
    # outside the selected snapshot are not recursively inventoried.
    scoped_physical = 0
    for directory in [ROOT / 'artifacts/autoformalization-alignment-20261003', PUBLICATION]:
        for path in directory.rglob('*.json'):
            if any(part in {'__pycache__', 'temporary-indexes', 'git-large-artifact-export-01'} for part in path.parts):
                continue
            paths.add(path)
            scoped_physical += 1
    findings, scan_counts, skipped = [], Counter(), []
    for path in sorted(paths):
        if not path.is_file() or path.is_symlink():
            skipped.append({'path': str(path.relative_to(ROOT)), 'reason': 'unavailable_or_symlink'})
            continue
        if path.stat().st_size > MAX_JSON:
            skipped.append({'path': str(path.relative_to(ROOT)), 'reason': 'JSON_parse_bound_64MiB', 'bytes': path.stat().st_size})
            continue
        data = path.read_bytes()
        scan_counts['available_JSON_bytes_scanned'] += len(data)
        scan_counts['available_JSON_files_scanned'] += 1
        if not KEY_HINT.search(data):
            continue
        value = json.loads(data)
        fields = model_fields(value)
        if not fields:
            scan_counts['numeric_parameter_key_hint_without_numeric_model_arrays'] += 1
            continue
        relative = str(path.relative_to(ROOT))
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        entry = snapshot_tree.get(relative)
        digest = hashlib.sha256(data).hexdigest()
        findings.append({
            'path': relative, 'absolute_path': str(path), 'sha256': digest, 'bytes': len(data),
            'git_blob_oid': oid, 'numeric_model_array_fields': sorted(fields),
            'schema': value.get('schema') if isinstance(value, dict) else None,
            'contains_optimizer_state': isinstance(value, dict) and 'optimizer_state' in value,
            'present_in_original_root_HEAD': original_tree.get(relative, {}).get('git_blob_oid') == oid,
            'present_in_canonical_root_source_snapshot': entry is not None and entry['git_blob_oid'] == oid,
            'reachable_in_current_live_GitHub_branch_history': oid in root_published_objects,
            'verified_initial_HF_upload_matches': hf_by_sha.get(digest, []),
            'classification': 'model_parameter_payload_not_metadata_only',
        })
    datasets_tip = text(DATASETS, 'rev-parse', 'HEAD')
    dataset_remote, _published_dataset_objects = live_remote(DATASETS)
    revisions = [datasets_tip, *['^' + row['oid'] for row in dataset_remote]]
    object_rows = git(DATASETS, 'rev-list', '--objects', '--stdin', data=('\n'.join(revisions) + '\n').encode()).splitlines()
    objects = {}
    for row in object_rows:
        oid, _, path = row.partition(b' ')
        objects.setdefault(oid, os.fsdecode(path))
    metadata = git(DATASETS, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                   data=b'\n'.join(objects) + (b'\n' if objects else b'')).splitlines()
    big, binaries, data_assets, blob_count, max_blob = [], [], [], 0, 0
    for row in metadata:
        oid, kind, raw_size = row.split()
        if kind != b'blob':
            continue
        size = int(raw_size)
        blob_count += 1
        max_blob = max(max_blob, size)
        path = objects[oid]
        item = {'path': path, 'git_blob_oid': oid.decode(), 'bytes': size}
        if size > MAX_BLOB:
            big.append(item)
        if Path(path).suffix.lower() in BINARY_SUFFIXES:
            binaries.append({**item, 'classification': 'binary_model_or_numeric_array_candidate_suffix_only_not_loaded'})
        if Path(path).suffix.lower() in {'.duckdb', '.jsonl'}:
            data_assets.append(item)
    root_upload = [row for row in findings if row['present_in_canonical_root_source_snapshot']
                   and not row['verified_initial_HF_upload_matches']]
    groups = Counter()
    for row in root_upload:
        name = Path(row['path']).name
        groups['projection' if '/projection-01/' in row['path'] else
               'typed_source' if '-source-' in name else 'typed_anchor' if '-anchor-' in name else 'other'] += 1
    report = {
        'schema': 'read-only-model-payload-and-datasets-publication-inventory/v1',
        'created_utc': datetime.now(UTC).isoformat(), 'runner_binding': pin(Path(__file__)),
        'root_original_head': original_head, 'root_canonical_source_snapshot': ROOT_SNAPSHOT,
        'canonical_final_selection_binding': pin(PUBLICATION / 'canonical_git/final-selection.json'),
        'root_live_remote_branch_refs': root_remote,
        'initial_HF_plan_binding': pin(hf_plan_file), 'initial_HF_receipt_binding': pin(hf_receipt_file),
        'artifact_JSON_scan_scope': 'all available artifact JSON paths from original/current canonical root Git trees, plus two owned alignment/publication campaigns; unrelated archived clone/runtime copies excluded',
        'root_snapshot_artifact_JSON_path_count': sum(name.startswith('artifacts/') and name.endswith('.json') for name in snapshot_tree),
        'physical_owned_campaign_JSON_paths_observed': scoped_physical,
        'scan_counts': dict(scan_counts), 'skipped_files': skipped,
        'numeric_model_JSON_payloads': findings,
        'root_source_snapshot_model_payload_count': sum(row['present_in_canonical_root_source_snapshot'] for row in findings),
        'actionable_root_HF_uploads': root_upload,
        'actionable_root_HF_upload_count': len(root_upload),
        'actionable_root_HF_upload_bytes': sum(row['bytes'] for row in root_upload),
        'actionable_root_HF_upload_groups': dict(groups),
        'datasets': {
            'repository': str(DATASETS), 'selected_integration_tip': datasets_tip,
            'live_remote_branch_refs': dataset_remote,
            'object_exclusion_scope': 'every actual live origin branch head; all commit objects locally verified, no fetch',
            'new_object_count': len(objects), 'new_blob_count': blob_count, 'maximum_new_blob_bytes': max_blob,
            'new_blobs_over_100MiB': big,
            'new_binary_model_or_array_candidates': binaries,
            'new_DuckDB_or_JSONL_assets': data_assets,
            'model_payloads_loaded_or_deserialized': False,
        },
        'private_bank_or_parameter_values_printed': False,
        'numerical_models_imported_loaded_or_executed': False,
        'Git_indexes_checkouts_commits_refs_or_remotes_mutated': False,
        'Hugging_Face_uploads_or_Git_pushes_performed': False,
    }
    result = save(RUN / 'report.json', report)
    print(json.dumps({'report_binding': result, 'root_model_payload_count': report['root_source_snapshot_model_payload_count'],
                      'root_upload_groups': dict(groups), 'root_upload_bytes': report['actionable_root_HF_upload_bytes'],
                      'datasets_new_oversized_count': len(big), 'datasets_new_binary_candidate_count': len(binaries),
                      'datasets_new_DuckDB_JSONL_count': len(data_assets)}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
