"""Prepare and qualify an isolated datasets history with exact HF references.

Preparation captures published refs without rewriting anything. Conversion
requires an externally pinned, successful HF verification receipt. Original
worktrees, indexes, branches and published commits are preserved throughout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
CAMPAIGN = BASE.parent
SOURCE = Path('/home/barberb/lift_coding/external/ipfs_datasets')
OWNER = CAMPAIGN / 'canonical_git/convert_history_hf_references.py'
OWNER_SHA = 'ba103b5581f20f69f4c09930cdc233cfdd6a021d1162158fc1d94158d190fb0d'
PLAN = CAMPAIGN / 'canonical_git/main-restoration/datasets/plan-v2.json'
PLAN_SHA = '96c24ebbd82ddde08e3fec44ccc158f956165cf5ef9bae4c1e9a18414496b353'
PREPARED = CAMPAIGN / 'canonical_git/main-restoration/datasets/prepared-v2.json'
PREPARED_SHA = '309df567b137cdfcf607a0b0e9f77cd4de20d3013c89cba0d84508cdd06a8771'
HF_PLAN = BASE / 'hf-large-evidence-v1_publication_plan_v2.json'
HF_PLAN_SHA = '8689d9950e0362b298f708ea0cc5901a53dc2b8a2b0e89409c296c75ce06cd9a'
EXPECTED_TIP = '5eedd23dd8b8ae4e2cac1716f00f1fcaf19a2801'
MAX_JSON_BYTES = 32 * 1024 * 1024
PREFIX = 'releases/20261004-git-large-evidence-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_selected(pin):
    if set(pin) != {'path', 'bytes', 'sha256'} or type(pin['bytes']) is not int:
        raise ValueError('invalid file binding')
    if not 0 <= pin['bytes'] <= MAX_JSON_BYTES:
        raise ValueError('selected metadata file exceeds the bound')
    with Path(pin['path']).open('rb') as stream:
        data = stream.read(pin['bytes'] + 1)
    if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise ValueError('selected metadata bytes differ')
    return json.loads(data.decode('utf-8'))


def fixed_json(path, digest):
    pin = binding(path)
    if pin['sha256'] != digest:
        raise ValueError('frozen selected metadata differs')
    return pin, read_selected(pin)


def write(path, value):
    value = {key: item for key, item in value.items() if key != 'content_sha256'}
    value['content_sha256'] = hashlib.sha256(canonical(value)).hexdigest()
    path = Path(path)
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def git(repository, *args, data=None, accepted=(0,)):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_LFS_SKIP_SMUDGE': '1'})
    result = subprocess.run(
        ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c',
         'core.hooksPath=/dev/null', '-C', str(repository), *args],
        input=data, capture_output=True, env=env, check=False, timeout=300)
    if result.returncode not in accepted:
        raise RuntimeError(f'Git operation {args[0]} failed with exit {result.returncode}')
    return result.stdout


def owner():
    with OWNER.open('rb') as stream:
        data = stream.read(32769)
    if len(data) > 32768 or hashlib.sha256(data).hexdigest() != OWNER_SHA:
        raise ValueError('frozen converter bytes differ')
    module = types.ModuleType('frozen_datasets_hf_history_algorithm')
    module.__file__ = str(OWNER)
    exec(compile(data, str(OWNER), 'exec'), module.__dict__)
    # Keep the frozen tree/commit algorithm; bound individual Git operations.
    module.git = git
    return module


def preserved(before, after):
    for key in ('head', 'index', 'selected_working_file_bytes'):
        if before[key] != after[key]:
            raise ValueError('original HEAD, index or selected working bytes changed')
    old = dict(row.split(' ', 1) for row in before['refs'])
    new = dict(row.split(' ', 1) for row in after['refs'])
    if any(new.get(ref) != oid for ref, oid in old.items()):
        raise ValueError('a captured original ref moved or disappeared')
    return sorted(set(after['refs']) - set(before['refs']))


def refs(repository):
    return sorted(git(repository, 'ls-remote', '--refs', 'origin').decode().splitlines())


def prepare(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    module = owner()
    plan_pin, plan = fixed_json(PLAN, PLAN_SHA)
    prepared_pin, prepared = fixed_json(PREPARED, PREPARED_SHA)
    hf_plan_pin, hf_plan = fixed_json(HF_PLAN, HF_PLAN_SHA)
    manifest_pin = plan['authoritative_full_tree_snapshot']['manifest_binding']
    read_selected(manifest_pin)
    read_selected(hf_plan['public_manifest_binding'])
    if prepared['integrated_tip'] != EXPECTED_TIP:
        raise ValueError('selected datasets integrated tip differs')
    if git(SOURCE, 'rev-parse', plan['integration_branch']).decode().strip() != EXPECTED_TIP:
        raise ValueError('selected integration branch moved')
    before = module.source_state(SOURCE, plan['authoritative_source']['selected_files'])
    write(directory / 'original-state.json', {'schema': 'hf-history-original-state/v1', **before})
    remote = git(SOURCE, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in ('https://github.com/endomorphosis/ipfs_datasets_py.git',
                      'https://github.com/endomorphosis/ipfs_datasets_py',
                      'git@github.com:endomorphosis/ipfs_datasets_py.git'):
        raise ValueError('unexpected datasets publication remote')
    advertised = refs(SOURCE)
    clone = directory / 'isolated.git'
    git(SOURCE, 'clone', '--bare', '--shared', '--no-hardlinks', str(SOURCE), str(clone))
    git(clone, 'remote', 'set-url', 'origin', remote)
    git(clone, 'fetch', '--no-tags', '--recurse-submodules=no', '--no-auto-maintenance',
        'origin', '+refs/*:refs/published-github/*')
    published, exclusions = [], []
    for row in advertised:
        oid, ref = row.split('\t')
        private = 'refs/published-github/' + ref.removeprefix('refs/')
        if git(clone, 'rev-parse', private).decode().strip() != oid:
            raise ValueError('published ref changed during isolated capture')
        commit = git(clone, 'rev-parse', '--verify', private + '^{commit}',
                     accepted=(0, 128)).decode().strip()
        if commit:
            exclusions.append(commit)
        published.append({'ref': ref, 'git_oid': oid, 'isolated_ref': private,
                          'commit_oid': commit or None})
    if refs(SOURCE) != advertised:
        raise ValueError('remote ref set changed during isolated capture')
    baseline = plan['origin_main_sha256_or_git_oid']
    selected_main = next((row['git_oid'] for row in published if row['ref'] == 'refs/heads/main'), None)
    if baseline != selected_main:
        raise ValueError('selected integration baseline is stale against live origin/main')
    added = preserved(before, module.source_state(SOURCE, plan['authoritative_source']['selected_files']))
    return write(directory / 'preflight.json', {
        'schema': 'isolated-hf-history-reference-preflight/v1',
        'original_repository': str(SOURCE), 'isolated_repository': str(clone),
        'selected_plan_binding': plan_pin, 'selected_prepared_binding': prepared_pin,
        'original_fulltree_manifest_binding': manifest_pin,
        'hf_release_plan_binding': hf_plan_pin, 'converter_binding': binding(OWNER),
        'driver_binding': binding(Path(__file__).resolve()), 'original_tip': EXPECTED_TIP,
        'published_refs': published, 'published_commit_exclusions': sorted(set(exclusions)),
        'original_state': before, 'original_state_preserved': True,
        'external_added_refs_not_selected': added,
        'selected_oversized_artifacts': hf_plan['original_git_blobs'],
        'source_cutoff': 'Exact selected restored tip; independently added original refs are reported but not substituted.',
        'scope': 'Isolated clone and live published-ref capture only; no history conversion or artifact parsing.',
        'git_lfs_migration_executed': False, 'origin_push_executed': False,
        'hf_upload_executed': False, 'training_executed': False})


def selected_preflight(directory):
    module = owner()
    pin = binding(directory / 'preflight.json')
    selected = read_selected(pin)
    if selected != module.seal(selected):
        raise ValueError('preflight content seal differs')
    for key in ('selected_plan_binding', 'selected_prepared_binding', 'original_fulltree_manifest_binding',
                'hf_release_plan_binding'):
        read_selected(selected[key])
    if binding(Path(__file__).resolve()) != selected['driver_binding'] or binding(OWNER) != selected['converter_binding']:
        raise ValueError('frozen preparation implementation changed')
    return module, pin, selected


def verified_references(preflight, receipt_pin):
    receipt = read_selected(receipt_pin)
    hf_plan = read_selected(preflight['hf_release_plan_binding'])
    if (receipt.get('schema') != 'append-only-HF-publication/v1'
            or receipt.get('status') != 'published_and_verified'
            or receipt.get('all_remote_files_verified') is not True
            or receipt.get('plan_binding') != preflight['hf_release_plan_binding']
            or receipt.get('repo_id') != 'Publicus/autoformalization-artifacts'
            or receipt.get('repo_type') != 'dataset' or receipt.get('prefix') != PREFIX):
        raise ValueError('HF publication receipt is not the selected verified archive release')
    revision = receipt['commit_oid']
    if type(revision) is not str or len(revision) != 40 or any(x not in '0123456789abcdef' for x in revision):
        raise ValueError('HF immutable revision is malformed')
    remote_rows = {row['path']: row for row in receipt['remote_files']}
    if len(remote_rows) != len(receipt['remote_files']):
        raise ValueError('duplicate remote verification rows')
    expected = {PREFIX + '/' + row['path']: row for row in hf_plan['files']}
    if set(remote_rows) != set(expected):
        raise ValueError('HF verification does not cover the exact selected release')
    for path, row in expected.items():
        remote = remote_rows[path]
        if (remote['bytes'], remote['sha256']) != (row['bytes'], row['sha256']):
            raise ValueError('HF verified release content differs')
        if remote['verification_method'] not in ('exact_revision_HF_LFS_sha256_metadata', 'exact_revision_streamed_sha256'):
            raise ValueError('unsupported HF byte verification method')
    references = {}
    for row in preflight['selected_oversized_artifacts']:
        path = row['path']
        remote = remote_rows[PREFIX + '/' + path]
        if (remote['bytes'], remote['sha256']) != (row['bytes'], row['sha256']):
            raise ValueError('exact source archive does not match the published payload')
        references[path] = {
            'schema': 'immutable-hf-large-artifact-reference/v1', 'original_path': path,
            'source_git_blob_oid': row['git_blob_oid'], 'bytes': row['bytes'], 'sha256': row['sha256'],
            'hf_repo_id': receipt['repo_id'], 'hf_repo_type': receipt['repo_type'],
            'hf_revision': revision, 'hf_path': PREFIX + '/' + path,
            'content_kind': 'generated_nonweight_data',
            'original_raw_payload_omitted_from_this_git_tree': True}
    if len(references) != 4:
        raise ValueError('the four exact selected archive payloads are required')
    return references


def convert(directory, receipt_pin):
    module, preflight_pin, preflight = selected_preflight(directory)
    plan = read_selected(preflight['selected_plan_binding'])
    references = verified_references(preflight, receipt_pin)
    selection_pin = write(directory / 'artifact-selection.json', {
        'schema': 'hf-large-artifact-reference-selection/v1',
        'rows': [{key: value for key, value in row.items() if key not in (
            'schema', 'content_kind', 'original_raw_payload_omitted_from_this_git_tree')}
                 for row in references.values()]})
    preserved(preflight['original_state'], module.source_state(SOURCE, plan['authoritative_source']['selected_files']))
    repository = Path(preflight['isolated_repository'])
    if refs(SOURCE) != sorted(row['git_oid'] + '\t' + row['ref'] for row in preflight['published_refs']):
        raise ValueError('live published refs changed since isolated selection; fresh capture required')
    result = module.rewrite_unpublished(repository, preflight['original_tip'],
                                        preflight['published_commit_exclusions'], references)
    mapped = [{**row, 'original_oid': row['oid'],
               'oid': result['commit_map'].get(row['oid'], row['oid'])} for row in plan['heads']]
    for row in mapped:
        git(repository, 'merge-base', '--is-ancestor', row['oid'], result['tip'])
    git(repository, 'merge-base', '--is-ancestor', plan['origin_main_sha256_or_git_oid'], result['tip'])
    snapshot = plan['authoritative_full_tree_snapshot']['snapshot_commit']
    mapped_snapshot = result['commit_map'].get(snapshot, snapshot)
    if module.tree(repository, snapshot) != module.tree(repository, mapped_snapshot):
        raise ValueError('current canonical snapshot tree unexpectedly changed')
    if module.tree(repository, preflight['original_tip']) != module.tree(repository, result['tip']):
        raise ValueError('current final source tree unexpectedly changed')
    rows = git(repository, 'rev-list', '--objects', result['tip'], '--not', *preflight['published_commit_exclusions'])
    meta = git(repository, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
               data=b'\n'.join(row.split(b' ', 1)[0] for row in rows.splitlines()) + b'\n')
    oversized = [row.decode() for row in meta.splitlines()
                 if row.split()[1] == b'blob' and int(row.split()[2]) > 100 * 1024 * 1024]
    if oversized:
        write(directory / 'oversized-rejection.json', {'schema': 'hf-conversion-oversized-rejection/v1', 'rows': oversized})
        raise ValueError('converted unpublished history still contains oversized Git blobs')
    added = preserved(preflight['original_state'], module.source_state(SOURCE, plan['authoritative_source']['selected_files']))
    converted_ref = 'refs/heads/publication/hf-references-20261004/datasets'
    git(repository, 'update-ref', converted_ref, result['tip'], '0' * 40)
    return write(directory / 'conversion.json', {
        'schema': 'isolated-hf-history-reference-conversion/v1', 'preflight_binding': preflight_pin,
        'artifact_selection_binding': selection_pin, 'hf_publication_receipt_binding': receipt_pin,
        'original_tip': preflight['original_tip'], 'converted_tip': result['tip'], 'converted_ref': converted_ref,
        'isolated_repository': str(repository), 'commit_map': result['commit_map'], 'tree_map': result['tree_map'],
        'mapped_selected_heads': mapped, 'replaced_tree_occurrences': result['replaced_tree_occurrences'],
        'references': references, 'reference_blob_oids': result['reference_blob_oids'],
        'all_mapped_selected_heads_ancestors': True, 'published_main_unchanged_and_ancestor': True,
        'final_current_tree_exactly_preserved': True, 'final_canonical_snapshot_tree_exactly_preserved': True,
        'original_repository_state_preserved': True, 'external_added_refs_not_selected': added,
        'newly_reachable_oversized_git_blob_count': 0, 'original_rewritten_commit_oids_remote_ancestry_claimed': False,
        'signature_headers_modified': False, 'git_lfs_migration_executed': False, 'git_lfs_upload_executed': False,
        'origin_push_executed': False, 'hf_upload_executed': False, 'training_executed': False,
        'scope': 'Only four exact oversized historical path/blob occurrences are replaced; immutable HF payload verification is selected by external receipt pin.'})


def package(directory, receipt_pin):
    module, preflight_pin, preflight = selected_preflight(directory)
    references = verified_references(preflight, receipt_pin)
    conversion_pin = binding(directory / 'conversion.json')
    conversion = read_selected(conversion_pin)
    if conversion != module.seal(conversion) or conversion['preflight_binding'] != preflight_pin:
        raise ValueError('conversion receipt generation differs')
    if conversion['references'] != references or conversion['hf_publication_receipt_binding'] != receipt_pin:
        raise ValueError('conversion does not select the verified HF generation')
    original_plan = read_selected(preflight['selected_plan_binding'])
    original_prepared = read_selected(preflight['selected_prepared_binding'])
    manifest_pin = original_plan['authoritative_full_tree_snapshot']['manifest_binding']
    original_manifest = read_selected(manifest_pin)
    original_snapshot = original_plan['authoritative_full_tree_snapshot']['snapshot_commit']
    mapped_snapshot = conversion['commit_map'].get(original_snapshot, original_snapshot)
    repository = Path(conversion['isolated_repository'])
    if module.tree(repository, original_snapshot) != module.tree(repository, mapped_snapshot):
        raise ValueError('canonical snapshot tree differs')
    if module.tree(repository, conversion['original_tip']) != module.tree(repository, conversion['converted_tip']):
        raise ValueError('current final tree differs')
    git(repository, 'merge-base', '--is-ancestor', mapped_snapshot, conversion['converted_tip'])
    preserved(preflight['original_state'], module.source_state(SOURCE, original_plan['authoritative_source']['selected_files']))
    output = directory / 'publication-selection'
    output.mkdir(mode=0o700, exist_ok=False)
    worktree = directory / 'publication-worktree'
    branch = conversion['converted_ref'].removeprefix('refs/heads/')
    git(repository, 'worktree', 'add', str(worktree), branch)
    git(repository, 'update-ref', 'refs/heads/publication/canonical-hf-references-20261004/datasets', mapped_snapshot, '0' * 40)
    manifest = {
        'schema': 'converted-canonical-snapshot-blob-pins/v1', 'repository': str(SOURCE),
        'original_snapshot_commit': original_snapshot, 'mapped_snapshot_commit': mapped_snapshot,
        'original_manifest_binding': manifest_pin, 'conversion_receipt_binding': conversion_pin,
        'canonical_blob_path_count': original_manifest['canonical_blob_path_count'],
        'canonical_gitlinks_deferred': original_manifest['canonical_gitlinks_deferred'],
        'explicit_hf_substitutions': [], 'final_canonical_snapshot_tree_exactly_preserved': True,
        'origin_push_executed': False, 'training_executed': False}
    compact_manifest_pin = write(output / 'converted-fulltree-manifest.json', manifest)
    plan = {key: value for key, value in original_plan.items() if key != 'content_sha256'}
    plan.update({
        'fresh_worktree': str(worktree), 'integration_branch': branch,
        'baseline_remote_ref': 'refs/published-github/heads/main', 'heads': conversion['mapped_selected_heads'],
        'authoritative_source': {**plan['authoritative_source'], 'snapshot_commit': mapped_snapshot},
        'authoritative_full_tree_snapshot': {'snapshot_commit': mapped_snapshot, 'manifest_binding': compact_manifest_pin},
        'restored_prepared_tip': conversion['converted_tip'], 'history_conversion_profile': conversion['schema'],
        'conversion_receipt_binding': conversion_pin, 'hf_publication_receipt_binding': receipt_pin,
        'hf_artifact_publication_receipts': [receipt_pin]})
    plan_pin = write(output / 'plan-v3.json', plan)
    prepared = {
        'schema': 'worktree-main-integration-hf-reference-prepublication/v3',
        'canonical_repository': str(SOURCE), 'fresh_worktree': str(worktree), 'normalized_origin': plan['normalized_origin'],
        'integrated_tip': conversion['converted_tip'], 'baseline_origin_main': plan['origin_main_sha256_or_git_oid'],
        'baseline_remote_ref': plan['baseline_remote_ref'], 'selected_head_count': len(plan['heads']),
        'syntax_qualification': original_prepared['syntax_qualification'], 'python_syntax_errors': [],
        'eligible_for_root_prepublication_review': True, 'plan_binding': plan_pin,
        'fulltree_manifest_binding': compact_manifest_pin, 'full_canonical_blob_path_count': manifest['canonical_blob_path_count'],
        'conversion_receipt_binding': conversion_pin, 'hf_publication_receipt_binding': receipt_pin,
        'prior_plan_binding': preflight['selected_plan_binding'], 'prior_prepared_binding': preflight['selected_prepared_binding'],
        'original_integrated_tip': conversion['original_tip'], 'mapped_prior_integrated_tip': conversion['converted_tip'],
        'original_integrated_tip_ancestor': False, 'mapped_prior_integrated_tip_ancestor': True,
        'all_mapped_selected_heads_ancestors': True, 'original_rewritten_commit_oids_remote_ancestry_claimed': False,
        'original_repository_state_preserved': True, 'original_head_and_index_preserved': True,
        'complete_canonical_snapshot_blobs_preserved': True, 'intentional_deleted_paths_preserved': True,
        'complete_canonical_gitlink_paths_preserved': True, 'final_current_tree_exactly_preserved': True,
        'all_source_python_parses_claimed': False, 'history_rewritten': True, 'force_push_used': False,
        'original_worktrees_replaced': False, 'submodule_clone_or_checkout_executed': False,
        'origin_push_executed': False, 'git_lfs_migration_executed': False, 'git_lfs_upload_executed': False,
        'training_executed': False}
    prepared_pin = write(output / 'prepared-v3.json', prepared)
    added = preserved(preflight['original_state'], module.source_state(SOURCE, original_plan['authoritative_source']['selected_files']))
    return write(output / 'selection.json', {'schema': 'isolated-hf-history-publication-selection/v1',
        'plan_binding': plan_pin, 'prepared_binding': prepared_pin, 'manifest_binding': compact_manifest_pin,
        'tip': conversion['converted_tip'], 'worktree': str(worktree), 'external_added_refs_not_selected': added})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'convert', 'package'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hf-publication-receipt-binding', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.operation == 'prepare':
            result = prepare(args.directory)
        else:
            if args.hf_publication_receipt_binding is None:
                parser.error('conversion/packaging requires an external HF receipt file binding')
            receipt_pin = json.loads(args.hf_publication_receipt_binding.read_bytes())
            result = (convert if args.operation == 'convert' else package)(args.directory, receipt_pin)
    except Exception as error:
        if args.directory.is_dir():
            failure = args.directory / (args.operation + '-failure.json')
            if not failure.exists():
                write(failure, {'schema': 'isolated-hf-history-operation-failure/v1', 'operation': args.operation,
                    'error_type': type(error).__name__,
                    'error': str(error) if isinstance(error, ValueError) else None,
                    'provider_or_git_stderr_details_retained': False,
                    'partial_generation_preserved': True, 'origin_push_executed': False,
                    'hf_upload_executed': False, 'training_executed': False})
        raise
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
