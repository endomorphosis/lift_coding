"""Append explicitly pinned releases; preserve remote defaults and prior files."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

WORK = Path(__file__).resolve().parent
MAX_FILE = 32 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wire(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode()


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
            raise ValueError('unsafe selected input')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_FILE + 1)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('selected input changed during read')
        return data
    finally:
        os.close(fd)


def check(binding):
    data = read(binding['path'])
    if (sha(data), len(data)) != (binding['sha256'], binding['bytes']):
        raise ValueError(f'selected file changed: {binding["path"]}')
    return data


def save(name, value):
    path = WORK / name
    value['content_sha256'] = sha(wire(value))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(wire(value))
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'sha256': sha(wire(value)), 'bytes': len(wire(value))}


def file_identity(file):
    return {'path': file.rfilename, 'bytes': file.size, 'git_blob_id': file.blob_id,
            'lfs_sha256': file.lfs.sha256 if file.lfs is not None else None}


def verify_remote(api, session, repo, revision, prefix, local):
    from huggingface_hub import hf_hub_url
    metadata = api.get_paths_info(repo, [f'{prefix}/{f["path"]}' for f in local],
                                  repo_type='model', revision=revision)
    found = {f.rfilename: f for f in metadata}
    if set(found) != {f'{prefix}/{f["path"]}' for f in local}:
        raise ValueError('remote selected-file inventory mismatch')
    result = []
    for binding in local:
        remote_path = f'{prefix}/{binding["path"]}'
        item = found[remote_path]
        if item.size != binding['bytes']:
            raise ValueError('remote size mismatch')
        if item.lfs is not None:
            observed_sha = item.lfs.sha256
            method = 'exact_commit_LFS_sha256_metadata'
        else:
            digest = hashlib.sha256()
            count = 0
            with session.get(hf_hub_url(repo, remote_path, revision=revision), stream=True,
                             timeout=(15, 60)) as response:
                response.raise_for_status()
                for data in response.iter_content(128 * 1024):
                    count += len(data)
                    if count > binding['bytes']:
                        raise ValueError('remote response exceeds selected size')
                    digest.update(data)
            if count != binding['bytes']:
                raise ValueError('remote response length mismatch')
            observed_sha = digest.hexdigest()
            method = 'exact_commit_streamed_download_sha256'
        if observed_sha != binding['sha256']:
            raise ValueError(f'remote digest mismatch: {remote_path}')
        result.append({'path': remote_path, 'bytes': binding['bytes'], 'sha256': observed_sha,
                       'verification_method': method, 'git_blob_id': item.blob_id})
    return result


def publish(expected_plan_sha256):
    # Network imports stay outside the integrity preparation/check route.
    import requests
    from huggingface_hub import CommitOperationAdd, HfApi, get_token
    logging.getLogger('huggingface_hub').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    selected_plan = WORK / 'retained_publication_plan.json'
    data = read(selected_plan)
    if sha(data) != expected_plan_sha256:
        raise ValueError('external publication-plan file pin mismatch')
    plan = json.loads(data)
    seal = plan.pop('content_sha256')
    if sha(wire(plan)) != seal or plan['schema'] != 'retained-autoformalization-publication-plan/v1':
        raise ValueError('publication-plan integrity mismatch')
    for binding in plan['original_input_bindings']:
        check(binding)
    token = get_token()
    if not token:
        raise ValueError('HF write credential unavailable')
    api = HfApi(token=token)
    who = api.whoami()
    auth_summary = {'username': who['name'], 'token_available': True,
                    'token_role': who.get('auth', {}).get('accessToken', {}).get('role'),
                    'Publicus_role': next((o.get('roleInOrg') for o in who.get('orgs', [])
                                          if o.get('name') == 'Publicus'), None)}
    if auth_summary['username'] != 'endomorphosis' or auth_summary['Publicus_role'] != 'admin':
        raise ValueError('unexpected publishing principal or organization scope')
    session = requests.Session()
    session.headers['Authorization'] = f'Bearer {token}'
    selected_teacher = plan['teacher_reference']
    teacher_info = api.repo_info(selected_teacher['repo_id'], repo_type='dataset',
                                 revision=selected_teacher['revision'], files_metadata=True)
    teacher = next(f for f in teacher_info.siblings if f.rfilename == selected_teacher['path'])
    if (teacher_info.sha != selected_teacher['revision'] or teacher_info.private or teacher.lfs is None
            or (teacher.size, teacher.lfs.sha256) != (selected_teacher['bytes'], selected_teacher['sha256'])):
        raise ValueError('immutable public teacher metadata mismatch')
    # Freeze all pre-mutation repository snapshots before publishing any repo.
    preflight = []
    for release in plan['releases']:
        if release['prefix'] != 'releases/20261004-autoformalization-lanes-v1':
            raise ValueError('unexpected release prefix')
        if release['repo_id'] not in {
                'Publicus/legal-ir-autoencoder', 'Publicus/intent-ir-autoencoder',
                'Publicus/security-ir-autoencoder', 'Publicus/ui-ux-ir-autoencoder'}:
            raise ValueError('unexpected destination')
        info = api.model_info(release['repo_id'], files_metadata=True)
        if info.private or any(f.rfilename.startswith(release['prefix'] + '/') for f in info.siblings):
            raise ValueError('destination private or selected append-only prefix already exists')
        prior = sorted((file_identity(f) for f in info.siblings), key=lambda f: f['path'])
        files = []
        for binding in release['files']:
            relative = Path(binding['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('unsafe selected local release path')
            actual = {'path': str(Path(release['directory']) / relative),
                      'bytes': binding['bytes'], 'sha256': binding['sha256']}
            check(actual)
            files.append(actual)
        preflight.append({'repo_id': release['repo_id'], 'parent_commit': info.sha,
                          'prior_files': prior, 'selected_file_count': len(files),
                          'selected_bytes': sum(f['bytes'] for f in files)})
    preflight_binding = save('retained_upload_preflight.json', {
        'schema': 'retained-HF-append-only-preflight/v1', 'auth': auth_summary,
        'plan_file_sha256': expected_plan_sha256, 'repositories': preflight,
        'teacher_reference_verified': selected_teacher, 'remote_mutation_executed': False,
        'numerical_models_loaded': 0})
    receipts = []
    for release, before in zip(plan['releases'], preflight, strict=True):
        for binding in plan['original_input_bindings']:
            check(binding)
        if sha(read(selected_plan)) != expected_plan_sha256:
            raise ValueError('publication plan changed after selection')
        operations = []
        for binding in release['files']:
            data = check({'path': str(Path(release['directory']) / binding['path']),
                          'sha256': binding['sha256'], 'bytes': binding['bytes']})
            # Byte inputs prevent later local-path mutation from altering submitted objects.
            operations.append(CommitOperationAdd(path_in_repo=f'{release["prefix"]}/{binding["path"]}',
                                                  path_or_fileobj=data))
        commit = api.create_commit(release['repo_id'], repo_type='model', operations=operations,
                                   parent_commit=before['parent_commit'],
                                   commit_message='Publish retained autoformalization lane research snapshots',
                                   commit_description='Append-only pinned authorial assets; preserve defaults and prior releases.')
        commit_binding = save(f'{release["repo_id"].split("/")[1]}-commit.json', {
            'schema': 'retained-HF-commit-created/v1', 'repo_id': release['repo_id'],
            'commit_oid': commit.oid, 'parent_commit': before['parent_commit'],
            'prefix': release['prefix'], 'selected_files': release['files'],
            'remote_verification_completed': False, 'qualified': False, 'proof_authority': False})
        verified = verify_remote(api, session, release['repo_id'], commit.oid, release['prefix'], release['files'])
        after = api.model_info(release['repo_id'], revision=commit.oid, files_metadata=True)
        observed_prior = sorted((file_identity(f) for f in after.siblings
                                 if not f.rfilename.startswith(release['prefix'] + '/')), key=lambda f: f['path'])
        if before['prior_files'] != observed_prior:
            raise ValueError('prior remote content changed in selected commit')
        for binding in plan['original_input_bindings']:
            check(binding)
        for binding in release['files']:
            check({'path': str(Path(release['directory']) / binding['path']),
                   'sha256': binding['sha256'], 'bytes': binding['bytes']})
        receipt = {
            'schema': 'retained-HF-append-only-publication/v1', 'created_at': datetime.now(UTC).isoformat(),
            'repo_id': release['repo_id'], 'parent_commit': before['parent_commit'], 'commit_oid': commit.oid,
            'release_url': f'https://huggingface.co/{release["repo_id"]}/tree/{commit.oid}/{release["prefix"]}',
            'prefix': release['prefix'], 'remote_files': verified, 'prior_file_count': len(observed_prior),
            'prior_files_preserved_exact_git_and_LFS_identities': True,
            'root_README_or_defaults_modified': False, 'prior_remote_files_deleted': False,
            'new_file_count': len(verified), 'new_bytes': sum(f['bytes'] for f in verified),
            'remote_verification_completed': True, 'original_local_input_bytes_preserved': True,
            'commit_creation_receipt': commit_binding, 'qualified': False, 'proof_authority': False,
            'source_fidelity_established': False, 'semantic_gold_created': False,
            'training_or_evaluation_admission': False, 'numerical_models_loaded': 0,
        }
        binding = save(f'{release["repo_id"].split("/")[1]}-publication.json', receipt)
        receipts.append({'repo_id': release['repo_id'], 'commit_oid': commit.oid, 'receipt': binding,
                         'new_files': len(verified), 'new_bytes': sum(f['bytes'] for f in verified)})
        print(json.dumps({'published': release['repo_id'], 'commit_oid': commit.oid,
                          'files_verified': len(verified), 'bytes': sum(f['bytes'] for f in verified)}), flush=True)
    return save('retained_publication_receipt.json', {
        'schema': 'retained-HF-publication-complete/v1', 'plan_file_sha256': expected_plan_sha256,
        'preflight': preflight_binding, 'releases': receipts, 'all_remote_files_verified': True,
        'total_files': sum(r['new_files'] for r in receipts), 'total_bytes': sum(r['new_bytes'] for r in receipts),
        'original_source_inputs_preserved': True, 'model_loads': 0, 'new_training_executed': False,
        'qualified': False, 'proof_authority': False, 'source_fidelity_established': False,
        'signing_or_review_authentication_executed': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-plan-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps({'complete': publish(args.expected_plan_sha256)}, sort_keys=True))
