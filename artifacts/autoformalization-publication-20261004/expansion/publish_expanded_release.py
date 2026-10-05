"""Publish an externally pinned append-only HF release and verify exact revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import stat
import subprocess
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path


class PublicationIntegrityError(ValueError):
    """A bounded local failure message without provider credentials or URLs."""


def require(value, message):
    if not value:
        raise PublicationIntegrityError(message)


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def check(binding):
    path = Path(binding['path']).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink source selection required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and type(binding['bytes']) is int and before.st_size == binding['bytes'],
                'ordinary exact-size selected file required')
        digest = hashlib.sha256()
        count = 0
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                count += len(chunk)
                require(count <= binding['bytes'], 'selected source exceeded bound')
                digest.update(chunk)
        after = os.fstat(fd)
        require((before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_ino, after.st_size, after.st_mtime_ns), 'selected source changed during hash')
        require(count == binding['bytes'] and digest.hexdigest() == binding['sha256'], 'selected file SHA differs')
    finally:
        os.close(fd)


def save(path, value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    data = raw(value) + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def identity(item):
    return {'path': item.rfilename, 'bytes': item.size, 'git_blob_oid': item.blob_id,
            'lfs_sha256': item.lfs.sha256 if item.lfs else None}


def validate_tracking_delta(before, after, allowed):
    require(after.startswith(before), 'old tracking metadata bytes changed')
    additions = after[len(before):]
    require(additions and additions.endswith(b'\n'), 'closed complete tracking additions required')
    rules = additions.decode('utf-8', 'strict').splitlines()
    require(len(rules) == len(set(rules)) and set(rules) <= allowed,
            'tracking additions must only name exact selected LFS files')
    return rules


def publish(arguments):
    directory = arguments.output.absolute()
    require(not directory.exists() and not any(p.is_symlink() for p in directory.parents), 'fresh private output required')
    directory.mkdir(mode=0o700, parents=True)
    report = {'schema': 'append-only-HF-publication/v1', 'created_utc': datetime.now(UTC).isoformat(),
        'status': 'failed_before_verified_publication', 'repository_creation_attempted': False, 'commit_creation_attempted': False,
        'all_remote_files_verified': False, 'payloads_parsed': False, 'model_calls': 0, 'training_executed': False,
        'qualified': False, 'source_fidelity_established': False, 'proof_authority': False, 'semantic_gold_created': False}
    try:
        plan_path = arguments.plan.absolute()
        require(plan_path.stat().st_size <= 1024 * 1024, 'bounded selected publication plan required')
        data = plan_path.read_bytes()
        plan_binding = {'path': str(plan_path), 'bytes': len(data), 'sha256': arguments.plan_sha256}
        check(plan_binding)
        plan = json.loads(data)
        body = {k: v for k, v in plan.items() if k != 'content_sha256'}
        require(hashlib.sha256(raw(body)).hexdigest() == plan['content_sha256'], 'plan seal differs')
        require(plan['schema'] == 'append-only-HF-publication-plan/v1', 'selected publication schema differs')
        repo, kind, prefix = plan['repo_id'], plan['repo_type'], plan['prefix']
        require((repo, kind, prefix) in {
            ('Publicus/autoformalization-artifacts', 'dataset', 'releases/20261004-git-large-artifacts-v1'),
            ('Publicus/autoformalization-artifacts', 'dataset', 'releases/20261004-git-large-evidence-v1'),
            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261004-formula-sidecars-v1'),
            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261004-retained-checkpoint-weights-v1'),
            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261004-additional-decoder-cutoff-v1'),
            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261004-source-reconstruction-aes-v1'),
            ('Publicus/legal-ir-autoencoder', 'model', 'releases/20261005-authored32-source-reconstruction-aes-v1')},
            'explicit approved destination/profile required')
        files = []
        seen = set()
        for binding in plan['files']:
            relative = Path(binding['path'])
            require(not relative.is_absolute() and '..' not in relative.parts and str(relative) == binding['path']
                    and binding['path'] not in seen, 'unique safe selected release path required')
            seen.add(binding['path'])
            local = {'path': str(Path(plan['directory']) / relative), 'bytes': binding['bytes'], 'sha256': binding['sha256']}
            check(local)
            files.append(local)
        for binding in plan['original_input_bindings']:
            check(binding)
        report.update({'repo_id': repo, 'repo_type': kind, 'prefix': prefix, 'plan_binding': plan_binding,
                       'selected_file_count': len(files), 'selected_bytes': sum(row['bytes'] for row in files)})
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
        os.environ['HF_HUB_DISABLE_XET'] = '1'
        logging.getLogger('huggingface_hub').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.ERROR)
        import requests
        from huggingface_hub import CommitOperationAdd, HfApi, get_token, hf_hub_url
        from huggingface_hub.errors import RepositoryNotFoundError
        credential = get_token()
        require(credential, 'HF write credential unavailable')
        api = HfApi(token=credential)
        who = api.whoami()
        organization = next((row.get('roleInOrg') for row in who.get('orgs', []) if row.get('name') == 'Publicus'), None)
        require(who['name'] == 'endomorphosis' and organization == 'admin', 'unexpected publishing principal')
        report['auth'] = {'username': who['name'], 'credential_available': True, 'Publicus_role': organization}
        try:
            before = api.repo_info(repo, repo_type=kind, files_metadata=True)
        except RepositoryNotFoundError:
            require(kind == 'dataset' and plan.get('create_if_missing') is True, 'unselected missing repository creation rejected')
            report['repository_creation_attempted'] = True
            save(directory / 'repository-creation-intent.json', {'repo_id': repo, 'repo_type': kind, 'private': False})
            api.create_repo(repo, repo_type=kind, private=False, exist_ok=False)
            before = api.repo_info(repo, repo_type=kind, files_metadata=True)
        require(before.private is False and not any(item.rfilename.startswith(prefix + '/') for item in before.siblings),
                'selected public append-only prefix already exists or destination is private')
        prior = sorted((identity(item) for item in before.siblings), key=lambda item: item['path'])
        session = requests.Session()
        session.headers['Authorization'] = 'Bearer ' + credential

        def attributes_content(revision, metadata):
            require(metadata['lfs_sha256'] is None and type(metadata['bytes']) is int and metadata['bytes'] <= 256 * 1024,
                    'bounded plain Git tracking metadata required')
            with session.get(hf_hub_url(repo, '.gitattributes', repo_type=kind, revision=revision),
                             stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    data.extend(chunk)
                    require(len(data) <= metadata['bytes'], 'tracking metadata response exceeds selected size')
            require(len(data) == metadata['bytes'] and hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                    == metadata['git_blob_oid'], 'tracking metadata exact Git identity differs')
            return bytes(data)

        attributes_before = None
        if plan.get('tracking_metadata_policy') == 'allow_only_exact_selected_path_LFS_additions':
            selected_attributes = next((row for row in prior if row['path'] == '.gitattributes'), None)
            require(selected_attributes is not None, 'explicit tracking exception requires existing exact metadata')
            attributes_before = attributes_content(before.sha, selected_attributes)
        report['preflight_binding'] = save(directory / 'preflight.json', {'schema': 'append-only-HF-preflight/v1',
            'repo_id': repo, 'repo_type': kind, 'parent_revision': before.sha, 'prior_files': prior,
            'selected_files': plan['files'], 'plan_binding': plan_binding})
        check(plan_binding)
        for binding in plan['original_input_bindings']:
            check(binding)
        for binding in files:
            check(binding)
        with ExitStack() as stack:
            operations = []
            for row, local in zip(plan['files'], files, strict=True):
                stream = stack.enter_context(Path(local['path']).open('rb'))
                require(os.fstat(stream.fileno()).st_size == local['bytes'], 'selected open file size differs')
                operations.append(CommitOperationAdd(path_in_repo=prefix + '/' + row['path'], path_or_fileobj=stream))
            report['commit_creation_attempted'] = True
            commit = api.create_commit(repo, repo_type=kind, operations=operations, parent_commit=before.sha,
                commit_message='Append pinned autoformalization research artifacts',
                commit_description='Exact selected bytes; preserve prior content and defaults; no model or data qualification.')
        report['commit_oid'] = commit.oid
        report['commit_creation_binding'] = save(directory / 'commit-created.json', {
            'schema': 'append-only-HF-commit-created/v1', 'repo_id': repo, 'repo_type': kind,
            'parent_revision': before.sha, 'commit_oid': commit.oid, 'prefix': prefix, 'selected_files': plan['files'],
            'remote_verification_completed': False})
        metadata = api.get_paths_info(repo, [prefix + '/' + row['path'] for row in plan['files']], repo_type=kind, revision=commit.oid)
        observed = {row.rfilename: row for row in metadata}
        require(set(observed) == {prefix + '/' + row['path'] for row in plan['files']}, 'remote complete file inventory differs')
        verified = []
        for binding in plan['files']:
            name = prefix + '/' + binding['path']
            remote = observed[name]
            require(remote.size == binding['bytes'], 'remote exact-size join differs')
            if remote.lfs is not None:
                actual = remote.lfs.sha256
                method = 'exact_revision_HF_LFS_sha256_metadata'
            else:
                digest = hashlib.sha256()
                count = 0
                with session.get(hf_hub_url(repo, name, repo_type=kind, revision=commit.oid), stream=True, timeout=(15, 120)) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(1024 * 1024):
                        count += len(chunk)
                        require(count <= binding['bytes'], 'bounded remote content length differs')
                        digest.update(chunk)
                require(count == binding['bytes'], 'remote response size differs')
                actual = digest.hexdigest()
                method = 'exact_revision_streamed_sha256'
            require(actual == binding['sha256'], 'remote digest differs')
            verified.append({'path': name, 'bytes': binding['bytes'], 'sha256': actual, 'verification_method': method,
                             'git_blob_oid': remote.blob_id})
        after = api.repo_info(repo, repo_type=kind, revision=commit.oid, files_metadata=True)
        after_prior = sorted((identity(row) for row in after.siblings if not row.rfilename.startswith(prefix + '/')), key=lambda row: row['path'])
        tracking_exception = None
        if prior != after_prior:
            require(attributes_before is not None, 'unselected prior tracking metadata exception rejected')
            prior_map = {row['path']: row for row in prior}
            after_map = {row['path']: row for row in after_prior}
            require(set(prior_map) == set(after_map), 'prior path additions or deletions rejected')
            changed = [name for name in prior_map if prior_map[name] != after_map[name]]
            require(changed == ['.gitattributes'], 'prior content changed beyond selected tracking metadata')
            attributes_after = attributes_content(commit.oid, after_map['.gitattributes'])
            allowed = {prefix + '/' + row['path'] + ' filter=lfs diff=lfs merge=lfs -text'
                       for row in plan['files'] if observed[prefix + '/' + row['path']].lfs is not None}
            rules = validate_tracking_delta(attributes_before, attributes_after, allowed)
            tracking_exception = {'path': '.gitattributes', 'before': prior_map['.gitattributes'],
                'after': after_map['.gitattributes'], 'before_sha256': hashlib.sha256(attributes_before).hexdigest(),
                'after_sha256': hashlib.sha256(attributes_after).hexdigest(),
                'before_content': attributes_before.decode('utf-8', 'strict'),
                'after_content': attributes_after.decode('utf-8', 'strict'),
                'exact_added_rules': rules, 'old_metadata_bytes_preserved': True,
                'scope': 'HF_selected_file_tracking_metadata_only_no_other_prior_content_change'}
        for binding in [plan_binding, *plan['original_input_bindings'], *files]:
            check(binding)
        for row in plan.get('original_git_blobs', []):
            size = int(subprocess.run(['git', '-C', plan['source_git_repository'], 'cat-file', '-s', row['git_blob_oid']],
                                      capture_output=True, check=True, timeout=30).stdout)
            require(size == row['bytes'], 'original source Git object size differs')
        report.update({'status': 'published_and_verified', 'parent_revision': before.sha, 'remote_files': verified,
            'all_remote_files_verified': True, 'prior_files_preserved_exact_git_and_LFS_identities': tracking_exception is None,
            'explicit_tracking_metadata_exception': tracking_exception, 'all_other_prior_paths_preserved': True,
            'prior_file_count': len(prior), 'original_local_file_bytes_preserved': True,
            'root_README_or_defaults_modified': False, 'prior_remote_files_deleted': False,
            'release_url': f'https://huggingface.co/{"datasets/" if kind == "dataset" else ""}{repo}/tree/{commit.oid}/{prefix}'})
    except Exception as error:
        report['error_type'] = type(error).__name__
        if isinstance(error, PublicationIntegrityError):
            report['integrity_error'] = str(error)
        # Do not retain provider exception strings that could contain credentials or signed URLs.
        report['provider_error_details_retained'] = False
    finally:
        source = Path(__file__).resolve()
        source_data = source.read_bytes()
        report['publisher_source'] = {'path': str(source), 'bytes': len(source_data), 'sha256': hashlib.sha256(source_data).hexdigest()}
        receipt = save(directory / 'publication.json', report)
        print(json.dumps({'publication': receipt, 'status': report['status'], 'commit_oid': report.get('commit_oid')}, sort_keys=True), flush=True)
    return 0 if report['all_remote_files_verified'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(publish(parser.parse_args()))
