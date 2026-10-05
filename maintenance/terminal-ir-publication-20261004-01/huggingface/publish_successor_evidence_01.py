"""Publish a pinned evidence addition and two explicit mutable release pointers.

Every other existing path must retain its committed identity. New evidence lives
in an unoccupied namespace, and the exact parent protects concurrent updates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

REPO = 'Publicus/codebase-ir-proof-index'
PREFIX = 'releases/20261004-terminal-codebase-ir-evidence-v1'
MUTABLE = {'README.md', PREFIX + '/publication-status.json'}


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def pin(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW); digest = hashlib.sha256(); count = 0
    try:
        before = os.fstat(fd)
        while block := os.read(fd, 8 * 1024**2): digest.update(block); count += len(block)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError('evidence input changed during read')
    finally:
        os.close(fd)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


def identity(row):
    return {'path': row.path, 'bytes': row.size, 'blob_id': row.blob_id,
            'lfs_sha256': row.lfs.sha256 if row.lfs else None}


def publish(args, state):
    from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download
    from huggingface_hub.utils import get_token
    plan_pin = pin(args.plan)
    if plan_pin['sha256'] != args.expected_plan_sha256:
        raise ValueError('publication plan pin mismatch')
    plan = json.loads(args.plan.read_bytes())
    if (plan['schema'] != 'terminal-ir-successor-evidence-publication-plan@1' or
            plan['repo_id'] != REPO or plan['expected_parent_commit'] != args.expected_parent_commit):
        raise ValueError('exact successor publication plan required')
    token = get_token()
    if not token: raise ValueError('cached publication credential unavailable')
    api = HfApi(token=token); who = api.whoami()
    if who.get('name') != 'endomorphosis' or not any(
            org.get('name') == 'Publicus' and org.get('roleInOrg') == 'admin' for org in who.get('orgs', [])):
        raise ValueError('unexpected publication identity')
    parent = api.repo_info(REPO, repo_type='dataset', revision='main').sha
    if parent != args.expected_parent_commit: raise ValueError('dataset parent changed')
    before = {row.path: identity(row) for row in api.list_repo_tree(
        REPO, repo_type='dataset', revision=parent, recursive=True) if hasattr(row, 'blob_id')}
    save(args.output / 'remote-before.json', {'commit': parent, 'files': before})
    names = set(); files = plan['files']
    if not 1 <= len(files) <= 100: raise ValueError('successor commit file bound')
    for item in files:
        name = item['remote']; binding = item['local']
        if (name in names or '..' in Path(name).parts or name.startswith('/') or
                (name not in MUTABLE and not name.startswith(PREFIX + '/'))):
            raise ValueError('unsafe/duplicate publication path')
        names.add(name)
        if name in before and name not in MUTABLE: raise ValueError('immutable evidence path occupied')
        if binding['bytes'] > 256 * 1024**2 or pin(Path(binding['path'])) != binding:
            raise ValueError('successor evidence file pin/bound mismatch')
    if MUTABLE - names: raise ValueError('both release pointers must be updated explicitly')
    state.update({'plan': plan_pin, 'parent': parent, 'files': len(files),
                  'selected_bytes': sum(item['local']['bytes'] for item in files)})
    if api.repo_info(REPO, repo_type='dataset', revision='main').sha != parent:
        raise ValueError('dataset changed immediately before commit')
    for item in files:
        if pin(Path(item['local']['path'])) != item['local']:
            raise ValueError('precommit evidence pin changed')
    commit = api.create_commit(REPO, repo_type='dataset', revision='main', parent_commit=parent,
        commit_message='Publish qualified source-model evidence and close scoped archive release',
        operations=[CommitOperationAdd(path_in_repo=item['remote'], path_or_fileobj=item['local']['path'])
                    for item in files], num_threads=2)
    state['commit'] = commit.oid
    save(args.output / 'commit-observed.json', {'parent': parent, 'commit': commit.oid,
        'verification_status': 'pending', 'external_effect_observed': True})
    remote = {row.path: row for row in api.get_paths_info(
        REPO, sorted(names), repo_type='dataset', revision=commit.oid)}
    verified = []
    for item in files:
        row = remote.get(item['remote']); expected = item['local']
        if row is None or row.size != expected['bytes']: raise ValueError('remote evidence size mismatch')
        if row.lfs:
            if row.lfs.sha256 != expected['sha256']: raise ValueError('remote evidence LFS digest mismatch')
            method = 'committed_LFS_SHA256_and_size'
        else:
            if row.size > 32 * 1024**2: raise ValueError('unexpected large Git file')
            downloaded = Path(hf_hub_download(REPO, item['remote'], repo_type='dataset',
                revision=commit.oid, token=token, cache_dir=args.output / 'download-cache', force_download=True))
            resolved = downloaded.resolve(strict=True)
            if (args.output / 'download-cache').resolve() not in resolved.parents:
                raise ValueError('download cache escaped output')
            if pin(resolved)['sha256'] != expected['sha256']:
                raise ValueError('remote small evidence byte mismatch')
            method = 'downloaded_small_file_SHA256_and_size'
        if pin(Path(expected['path'])) != expected: raise ValueError('local evidence changed during publication')
        verified.append({'remote': identity(row), 'expected': expected, 'verification_method': method})
    after = {row.path: identity(row) for row in api.list_repo_tree(
        REPO, repo_type='dataset', revision=commit.oid, recursive=True) if hasattr(row, 'blob_id')}
    for name, row in before.items():
        if name not in MUTABLE and after.get(name) != row:
            raise ValueError('prior immutable dataset file changed')
    if api.repo_info(REPO, repo_type='dataset', revision='main').sha != commit.oid:
        raise ValueError('dataset changed at final verification')
    if pin(args.plan) != plan_pin: raise ValueError('publication plan changed')
    save(args.output / 'verified-files.json', {'commit': commit.oid, 'files': verified})
    state.update({'status': 'PUBLISHED_AND_VERIFIED', 'remote_readback_verified': True,
        'prior_immutable_remote_files_preserved': len(before) - len(MUTABLE),
        'mutable_paths_explicitly_updated': sorted(MUTABLE),
        'whole_large_file_duplicate_download_performed': False,
        'model_training_calls': 0, 'prover_calls': 0, 'proof_authority': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'output'): parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--expected-parent-commit', required=True)
    args = parser.parse_args(); start = time.monotonic()
    args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=False)
    state = {'schema': 'terminal-ir-HF-successor-publication@1', 'status': 'STARTED',
             'primary_error_type': None, 'external_network_effects_unknown_if_commit_call_raises': True}
    save(args.output / 'started.json', {'script': pin(Path(__file__).resolve()),
        'argv': {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}})
    try:
        publish(args, state)
    except BaseException as problem:
        state.update({'status': 'FAILED_PARTIAL_EFFECTS_PRESERVED', 'primary_error_type': type(problem).__name__})
        raise
    finally:
        state['elapsed_seconds'] = time.monotonic() - start; save(args.output / 'closed.json', state)
    print(json.dumps({key: state[key] for key in ('status', 'commit', 'files', 'selected_bytes', 'elapsed_seconds')}))


if __name__ == '__main__': main()
