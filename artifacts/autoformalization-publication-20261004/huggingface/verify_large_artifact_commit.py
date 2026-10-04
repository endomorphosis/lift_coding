"""Read-only qualification of an existing data commit and exact HF tracking delta."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

WORK = Path(__file__).resolve().parent
REVISION = 'd0867b9e15108359b247a47184b6b140b18613dc'
PLAN_SHA = '13393401bd5058181f250987dfaed24940aac269846eb3d4582694b498b8f283'
PUBLISHER_SHA = '5d5753b7de373f6621435e78d2a22495e20e1fae55fe7c801dcd5929846f0c74'
FAILED_RECEIPT_SHA = '621481b82b2cfb169501182c42d9522be0d5ce10fa8d6e7e5c7672455ea93363'


def main():
    source = WORK / 'publish_append_release.py'
    source_data = source.read_bytes()
    if hashlib.sha256(source_data).hexdigest() != PUBLISHER_SHA:
        raise ValueError('frozen publisher source differs')
    namespace = {'__name__': '_verified_publication_helpers', '__file__': str(source)}
    exec(compile(source_data, str(source), 'exec'), namespace)
    check, save, identity = (namespace[key] for key in ('check', 'save', 'identity'))
    plan_file = WORK / 'large_git_artifact_publication_plan.json'
    failed_file = WORK / 'large-artifact-upload-01/publication.json'
    for path, expected in ((plan_file, PLAN_SHA), (failed_file, FAILED_RECEIPT_SHA)):
        check({'path': str(path), 'bytes': path.stat().st_size, 'sha256': expected})
    plan = json.loads(plan_file.read_bytes())
    failure = json.loads(failed_file.read_bytes())
    if failure['commit_oid'] != REVISION or failure['integrity_error'] != 'prior remote content identities differ':
        raise ValueError('selected original rejection differs')
    preflight_binding = failure['preflight_binding']
    check(preflight_binding)
    preflight = json.loads(Path(preflight_binding['path']).read_bytes())
    output = WORK / 'large-artifact-verification-02'
    output.mkdir(mode=0o700)
    logging.getLogger('huggingface_hub').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    import requests
    from huggingface_hub import HfApi, get_token, hf_hub_url
    credential = get_token()
    api = HfApi(token=credential)
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + credential
    repo = plan['repo_id']
    prefix = plan['prefix']
    info = api.dataset_info(repo, revision=REVISION, files_metadata=True)
    if info.sha != REVISION or info.private:
        raise ValueError('exact public revision differs')
    expected = {prefix + '/' + row['path']: row for row in plan['files']}
    observed = {row.rfilename: row for row in info.siblings}
    verified = []
    for name, binding in expected.items():
        row = observed[name]
        if row.size != binding['bytes']:
            raise ValueError('remote exact-size identity differs')
        if row.lfs:
            sha = row.lfs.sha256
            method = 'exact_revision_HF_LFS_sha256_metadata'
        else:
            digest = hashlib.sha256()
            count = 0
            with session.get(hf_hub_url(repo, name, repo_type='dataset', revision=REVISION), stream=True, timeout=(15, 120)) as response:
                response.raise_for_status()
                for chunk in response.iter_content(1024 * 1024):
                    count += len(chunk)
                    if count > binding['bytes']:
                        raise ValueError('remote content exceeds pin')
                    digest.update(chunk)
            if count != binding['bytes']:
                raise ValueError('remote byte count differs')
            sha = digest.hexdigest()
            method = 'exact_revision_streamed_sha256'
        if sha != binding['sha256']:
            raise ValueError('remote exact SHA differs')
        verified.append({'path': name, 'bytes': binding['bytes'], 'sha256': sha, 'git_blob_oid': row.blob_id,
                         'verification_method': method})
    before = {row['path']: row for row in preflight['prior_files']}
    after = {name: identity(row) for name, row in observed.items() if not name.startswith(prefix + '/')}
    changed = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    if changed != ['.gitattributes'] or set(before) != set(after) or set(observed) != set(expected) | set(before):
        raise ValueError('unexpected prior-path delta')
    attributes = []
    for index, revision in enumerate((preflight['parent_revision'], REVISION)):
        response = session.get(hf_hub_url(repo, '.gitattributes', repo_type='dataset', revision=revision), timeout=(15, 60))
        response.raise_for_status()
        value = response.content
        selected = before['.gitattributes'] if index == 0 else after['.gitattributes']
        if len(value) > 16384 or len(value) != selected['bytes'] or hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() != selected['git_blob_oid']:
            raise ValueError('exact tracking metadata Git identity differs')
        path = output / ('attributes-before.txt' if index == 0 else 'attributes-after.txt')
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        attributes.append({'data': value, 'binding': {'path': str(path), 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}})
    additions = ''.join(prefix + '/' + row['path'] + ' filter=lfs diff=lfs merge=lfs -text\n'
                        for row in plan['original_git_blobs']).encode()
    if attributes[1]['data'] != attributes[0]['data'] + additions:
        raise ValueError('tracking metadata delta exceeds exact two selected artifact rules')
    for binding in plan['original_input_bindings']:
        check(binding)
    for row in plan['files']:
        check({'path': str(Path(plan['directory']) / row['path']), 'bytes': row['bytes'], 'sha256': row['sha256']})
    result = {'schema': 'HF-data-commit-readonly-verification/v1',
        'status': 'verified_selected_bytes_with_explicit_HF_tracking_metadata_delta', 'repo_id': repo, 'repo_type': 'dataset',
        'commit_oid': REVISION, 'parent_revision': preflight['parent_revision'], 'prefix': prefix,
        'remote_files': verified, 'all_six_selected_remote_files_verified': True,
        'prior_all_file_identities_unchanged': False, 'only_prior_path_changed': '.gitattributes',
        'other_prior_paths_preserved': True, 'tracking_metadata_before': before['.gitattributes'],
        'tracking_metadata_after': after['.gitattributes'], 'tracking_metadata_content_bindings': [row['binding'] for row in attributes],
        'tracking_metadata_delta_recipe': 'exact_old_bytes_plus_two_exact_selected_path_LFS_rules',
        'tracking_metadata_additions': additions.decode(), 'root_README_modified': False, 'prior_user_data_files_modified': False,
        'original_rejection_receipt': {'path': str(failed_file), 'bytes': failed_file.stat().st_size, 'sha256': FAILED_RECEIPT_SHA},
        'selected_plan': {'path': str(plan_file), 'bytes': plan_file.stat().st_size, 'sha256': PLAN_SHA},
        'original_local_selected_bytes_preserved': True, 'payloads_parsed': False, 'network_mutations_by_verifier': 0,
        'model_calls': 0, 'training_executed': False, 'prover_calls': 0, 'qualified': False,
        'source_fidelity_established': False, 'proof_authority': False, 'semantic_gold_created': False,
        'release_url': f'https://huggingface.co/datasets/{repo}/tree/{REVISION}/{prefix}',
        'verifier_source': {'path': str(Path(__file__).resolve()), 'bytes': Path(__file__).stat().st_size,
                            'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    print(json.dumps({'verification': save(output / 'verification.json', result), 'commit_oid': REVISION}, sort_keys=True))


if __name__ == '__main__':
    main()
