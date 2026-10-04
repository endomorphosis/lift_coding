"""Overlay exactly selected final source/metadata files in a fresh root candidate.

This prepares an ordinary commit and publisher inputs. It never pushes, loads a
model, edits the original source checkout, or collects unselected source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parent.parent
LIBRARY = BASE / 'canonical_git/update_published_child_gitlinks.py'
LIBRARY_SHA = '605020a6c4f263b6f743e569e752251fc6ade608324f3dabd6d3be82bfbe4b31'
REFRESH = BASE / 'refresh_main_candidate.py'
REFRESH_SHA = '8c20d17e5c0936abca0423854a22fe91433aa0c58227260a47756dedef06d4e8'
RESTORER = BASE / 'canonical_git/restore_leaf_trees.py'
RESTORER_SHA = '5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa'
STAGING = ('huggingface/retained-lanes-v1/', 'huggingface/git-large-artifacts-v1/',
           'huggingface/formula-sidecars-v1/', 'huggingface/additional-decoder-cutoff-v1/',
           'huggingface/retained-checkpoint-weights-v1/', 'huggingface/source-reconstruction-aes-v1/',
           'git/hf-large-evidence-v1/', 'git/hf-retained-checkpoint-weights-v1/')
RAW_VECTOR_KEYS = {'vector', 'vectors', 'source_vector', 'source_vectors', 'embedding_vector',
                   'embedding_vectors', 'embeddings', 'latent_vector', 'latent_vectors',
                   'reconstructed_vector', 'reconstructed_vectors'}
RAW_STATE_KEYS = {'weights', 'encoder_weights', 'decoder_weights', 'state_dict', 'model_state', 'optimizer_state'}


def checked_owner(path, digest, name):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('selected frozen implementation owner differs')
    namespace = {'__name__': name, '__file__': str(path)}
    exec(compile(data, str(path), 'exec'), namespace)
    return namespace


def contains_numeric_array(value):
    if isinstance(value, list):
        return any(type(item) in {int, float} or contains_numeric_array(item) for item in value)
    if isinstance(value, dict):
        return any(contains_numeric_array(item) for item in value.values())
    return False


def reject_nested_payloads(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in RAW_VECTOR_KEYS and contains_numeric_array(item):
                raise ValueError('raw nested vector payload rejected')
            if key in RAW_STATE_KEYS and isinstance(item, (dict, list)):
                raise ValueError('raw nested model state payload rejected')
            reject_nested_payloads(item)
    elif isinstance(value, list):
        for item in value:
            reject_nested_payloads(item)


def eligible(name, data):
    parts, lower = Path(name).parts, Path(name).name.lower()
    if name not in {'.gitignore'} and not name.startswith(('implementation_plan/docs/',
            'artifacts/autoformalization-publication-20261004/', 'artifacts/autoformalization-alignment-20261003/')):
        raise ValueError('explicit root campaign source/metadata scope required')
    if any(prefix in name for prefix in STAGING) or set(parts) & {
            'isolated.git', 'publication-worktree', 'source-supplement-worktree', 'logs', 'banks',
            'reference-banks', 'reference_banks', 'reference-bank', 'reference_bank'}:
        raise ValueError('staging, runtime, raw bank or log path rejected')
    if Path(name).suffix.lower() not in {'.py', '.md', '.json', '.txt', '.yaml', '.yml', '.toml'} and name != '.gitignore':
        raise ValueError('binary/archive/weight or unsupported source type rejected')
    if lower in {'training-report.json', 'training.json', 'train_weak_supervision.json'}:
        raise ValueError('full training report or raw training bank rejected')
    if not lower.endswith('.hf.json') and (lower.endswith(('.checkpoint.json', '-checkpoint.json', '.state.json', '-state.json'))
                                         or lower in {'checkpoint.json', 'model.json', 'optimizer.json'}):
        raise ValueError('checkpoint/state payload rejected')
    if b'\0' in data:
        raise ValueError('binary source payload rejected')
    data.decode('utf-8')
    if lower.endswith('.json'):
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError('JSON metadata must be an object')
        schema = value.get('schema', '')
        if schema == 'alignment-lane-bundle/v1':
            raise ValueError('raw lane vector bank schema rejected')
        if isinstance(schema, str) and 'checkpoint' in schema and 'report' not in schema and 'publication' not in schema:
            raise ValueError('checkpoint payload schema rejected')
        reject_nested_payloads(value)


def source_file(root, row, module):
    module['require'](set(row) == {'path', 'bytes', 'sha256', 'mode'}, 'closed selected file binding required')
    name = module['safe_path'](row['path'])
    path = root / name
    module['require'](row['mode'] in {'100644', '100755'} and type(row['bytes']) is int
                      and 0 < row['bytes'] <= 8 * 1024 * 1024, 'bounded regular source file required')
    module['require'](all(not parent.is_symlink() for parent in (path, *path.parents)), 'symlink source path rejected')
    info = path.stat()
    module['require'](stat.S_ISREG(info.st_mode), 'selected source must be a regular file')
    data = path.read_bytes()
    mode = '100755' if info.st_mode & 0o111 else '100644'
    module['require'](len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
                      and mode == row['mode'], 'exact selected source bytes or mode differ')
    eligible(name, data)
    return name, data


def prepare(args):
    module = checked_owner(LIBRARY, LIBRARY_SHA, 'final_source_library')
    refresh = checked_owner(REFRESH, REFRESH_SHA, 'final_refresh_library')
    restore = checked_owner(RESTORER, RESTORER_SHA, 'final_syntax_library')
    require = module['require']
    selection, selection_pin = module['selected'](args.selection, args.selection_sha)
    require(set(selection) - {'content_sha256'} == {'schema', 'canonical_repository', 'source_publication_binding', 'selected_files', 'commit_message'}
            and selection['schema'] == 'final-root-source-supplement-selection/v1', 'closed final source selection required')
    publication = module['pinned'](selection['source_publication_binding'])
    require(publication.get('schema') == 'git-integrated-main-publication/v1'
            and publication.get('status') == 'published_and_verified' and publication.get('remote_publication_verified') is True
            and publication.get('normalized_origin') == 'github.com/endomorphosis/lift_coding'
            and publication['integrated_tip'] == publication['remote_main_after'], 'verified owned root publication required')
    root = Path(selection['canonical_repository']).absolute()
    require(root == Path(publication['canonical_repository']).absolute(), 'original root source repository differs')
    files = selection['selected_files']
    require(isinstance(files, list) and 0 < len(files) <= 256
            and sum(row['bytes'] for row in files) <= 64 * 1024 * 1024, 'bounded explicit final source selection required')
    selected_data = dict(source_file(root, row, module) for row in files)
    require(len(selected_data) == len(files), 'duplicate final selected source path')
    message = selection['commit_message']
    require(isinstance(message, str) and 0 < len(message) <= 1000 and '\0' not in message, 'bounded ordinary commit message required')
    original_head = module['text'](root, 'rev-parse', 'HEAD')
    original_branch = module['text'](root, 'symbolic-ref', '--quiet', 'HEAD')
    original_index = module['original_index'](root)
    old_plan = module['pinned'](publication['plan_binding'])
    old_prepared = module['pinned'](publication['prepared_binding'])
    require(old_prepared['integrated_tip'] == publication['integrated_tip'], 'previous publication candidate differs')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    module['save'](args.output / 'start.json', {'schema': 'final-root-source-supplement-start/v1',
        'selection_binding': selection_pin, 'source_publication_binding': selection['source_publication_binding'],
        'original_HEAD': original_head, 'original_branch': original_branch, 'original_index_binding': original_index,
        'push_executed': False, 'training_executed': False})
    refresh['refresh'](SimpleNamespace(plan=Path(publication['plan_binding']['path']),
        plan_sha=publication['plan_binding']['sha256'], prepared=Path(publication['prepared_binding']['path']),
        prepared_sha=publication['prepared_binding']['sha256'], output=args.output / 'baseline-refresh', branch=args.branch))
    refreshed_plan = json.loads((args.output / 'baseline-refresh/plan.json').read_bytes())
    refreshed_prepared = json.loads((args.output / 'baseline-refresh/prepared.json').read_bytes())
    work = Path(refreshed_plan['fresh_worktree'])
    before = module['text'](work, 'rev-parse', 'HEAD')
    require(before == refreshed_prepared['integrated_tip'] and refreshed_prepared['eligible_for_root_prepublication_review'],
            'refreshed candidate qualification differs')
    before_tree = module['tree'](work, before)
    expected, rows = dict(before_tree), []
    for row in files:
        name, data = source_file(root, row, module)
        require(data == selected_data[name], 'selected source changed after baseline refresh')
        require(before_tree.get(name, {}).get('mode') != '160000', 'ordinary source cannot replace child Gitlink')
        require(not any(path != name and (path.startswith(name + '/') or name.startswith(path + '/'))
                        for path in before_tree), 'selected source would remove an unselected tree entry')
        destination = work / name
        require(all(not parent.is_symlink() for parent in (destination, *destination.parents)), 'symlink destination rejected')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        destination.chmod(0o755 if row['mode'] == '100755' else 0o644)
        result = module['git'](work, 'hash-object', '-w', '--stdin', data=data)
        oid = result.stdout.decode().strip()
        expected[name] = {'mode': row['mode'], 'kind': 'blob', 'oid': oid}
        rows.append(row['mode'].encode() + b' ' + oid.encode() + b'\t' + os.fsencode(name) + b'\0')
    module['git'](work, 'update-index', '-z', '--index-info', data=b''.join(rows))
    if module['git'](work, 'diff', '--cached', '--quiet', accepted=(0, 1)).returncode:
        module['git'](work, 'commit', '-m', message)
    tip = module['text'](work, 'rev-parse', 'HEAD')
    actual = module['tree'](work, tip)
    require(actual == expected, 'hook or source supplement changed an unselected committed path')
    module['git'](work, 'diff', '--quiet', '--ignore-submodules=all')
    module['git'](work, 'diff', '--cached', '--quiet')
    for row in files:
        source_file(root, row, module)
    require(module['text'](root, 'rev-parse', 'HEAD') == original_head
            and module['text'](root, 'symbolic-ref', '--quiet', 'HEAD') == original_branch
            and module['original_index'](root) == original_index, 'original whole HEAD/index or branch changed')
    for ancestor in (before, publication['integrated_tip'], refreshed_plan['origin_main_sha256_or_git_oid']):
        module['git'](work, 'merge-base', '--is-ancestor', ancestor, tip)
    require(module['binding'](selection_pin['path']) == selection_pin, 'selected metadata bytes changed')
    links = old_plan.get('published_gitlinks', [])
    require(refreshed_plan.get('published_gitlinks', []) == links
            and all(actual[row['path']] == {'mode': '160000', 'kind': 'commit', 'oid': row['oid']} for row in links),
            'verified published child links changed')
    sources = [{'path': name, 'mode': row['mode'], 'kind': row['kind'], 'source_git_oid': row['oid']}
               for name, row in sorted(actual.items())]
    manifest = {'schema': 'full-current-git-tree-qualification/v1', 'canonical_repository': str(root),
        'canonical_snapshot_commit': tip, 'integrated_tip': tip, 'source_bindings': sources,
        'source_binding_count': len(sources), 'canonical_entries_missing_or_changed': [],
        'full_current_tree_exactly_preserved': True, 'metadata_only_no_source_credentials_or_model_bytes_read': True,
        'normalized_origin': refreshed_plan['normalized_origin'], 'origin_push_performed': False,
        'qualification_binding': selection_pin,
        'source_git_oid_recipe': 'raw_selected_source_Git_blob_identity_and_complete_committed_tree_equality'}
    manifest_path = args.output / 'fulltree-manifest.json'
    with manifest_path.open('xb') as stream:
        os.chmod(manifest_path, 0o600)
        stream.write(module['raw'](manifest) + b'\n')
    manifest_pin = module['binding'](manifest_path)
    prior_full = module['pinned'](old_plan['authoritative_full_tree_snapshot']['manifest_binding'])
    if prior_full['schema'] == 'converted-canonical-snapshot-blob-pins/v1':
        prior_full = module['pinned'](prior_full['original_manifest_binding'])
    omissions = [row for row in prior_full['authoritative_source']['selected_files'] if row['state'] == 'deleted']
    require(not any(row['path'] in actual for row in omissions), 'original intentional payload omission reappeared')
    plan = {'schema': 'final-root-source-supplement-main-plan/v1', 'canonical_repository': str(root),
        'normalized_origin': refreshed_plan['normalized_origin'], 'fresh_worktree': str(work), 'integration_branch': args.branch,
        'baseline_remote_ref': 'origin/main', 'origin_main_sha256_or_git_oid': refreshed_plan['origin_main_sha256_or_git_oid'],
        'heads': [{'oid': publication['integrated_tip'], 'kind': 'previous_verified_publication'},
                  {'oid': tip, 'kind': 'canonical_current_source'}],
        'authoritative_source': {'snapshot_commit': tip, 'selected_files':
            [{**row, 'state': 'present'} for row in files] + omissions},
        'authoritative_full_tree_snapshot': {'snapshot_commit': tip, 'manifest_binding': manifest_pin},
        'published_gitlinks': links, 'previous_publication_binding': selection['source_publication_binding'],
        'selected_supplement_binding': selection_pin, 'original_canonical_source_authority_except_exact_selected_overlays': True,
        'origin_push_authorized_for_helper': False, 'training_authorized_for_helper': False}
    plan_pin = module['save'](args.output / 'plan.json', plan)
    syntax = restore['syntax_findings'](work, plan['origin_main_sha256_or_git_oid'], tip,
        {name: {'git_oid': row['oid']} for name, row in actual.items()})
    require(not syntax['newly_invalid_executable_source'] and not syntax['inherited_canonical_syntax_findings'],
            'invalid changed Python blocks final source publication')
    prepared = {'schema': 'worktree-main-integration-fulltree-prepublication/v2', 'canonical_repository': str(root),
        'normalized_origin': plan['normalized_origin'], 'fresh_worktree': str(work), 'integrated_tip': tip,
        'baseline_origin_main': plan['origin_main_sha256_or_git_oid'], 'baseline_remote_ref': 'origin/main',
        'selected_head_count': len(plan['heads']), 'all_selected_heads_ancestors': True, 'published_gitlinks': links,
        'plan_binding': plan_pin, 'fulltree_manifest_binding': manifest_pin,
        'full_canonical_blob_path_count': sum(row['kind'] == 'blob' for row in actual.values()),
        'complete_canonical_snapshot_blobs_preserved': True, 'intentional_deleted_paths_preserved': True,
        'prior_integrated_tip_ancestor': True, 'original_head_and_index_preserved': True,
        'all_source_python_parses_claimed': False, 'syntax_qualification': syntax, 'python_syntax_errors': [],
        'eligible_for_root_prepublication_review': True, 'origin_push_executed': False, 'training_executed': False,
        'history_rewritten': False, 'force_push_used': False, 'original_worktrees_replaced': False,
        'source_supplement_overlays': files, 'unselected_committed_entries_and_modes_preserved': True,
        'local_git_hooks_disabled': False}
    prepared_pin = module['save'](args.output / 'prepared.json', prepared)
    result = {'schema': 'final-root-source-supplement-preparation/v1', 'tip': tip,
        'plan_binding': plan_pin, 'prepared_binding': prepared_pin, 'manifest_binding': manifest_pin,
        'selection_binding': selection_pin, 'selected_source_file_count': len(files),
        'original_HEAD_index_branch_and_selected_bytes_preserved': True,
        'ordinary_commit_preserves_previous_published_history': True, 'push_executed': False, 'training_executed': False}
    module['save'](args.output / 'preparation.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--branch', required=True)
    os.umask(0o077)
    prepare(parser.parse_args())
