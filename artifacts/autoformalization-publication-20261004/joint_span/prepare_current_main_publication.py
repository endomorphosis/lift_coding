"""Overlay selected campaign sources on an exact current-main baseline.

Create only a fresh private worktree and ordinary commit. Preserve every
baseline entry, mode and Gitlink except explicit ordinary source overlays.
Never refresh an old canonical cutoff, restore old child links, push, reset an
original worktree, read model tensors or execute training/provers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent.parent
LIBRARY = BASE / 'canonical_git/update_published_child_gitlinks.py'
LIBRARY_SHA = '605020a6c4f263b6f743e569e752251fc6ade608324f3dabd6d3be82bfbe4b31'
ELIGIBILITY = BASE / 'canonical_git/prepare_final_root_supplement.py'
ELIGIBILITY_SHA = 'cfdea5657e95beb09fbb0a0c377347f2cea7fb1a4523e93b7f73f05351b9011e'
SYNTAX = BASE / 'canonical_git/restore_leaf_trees.py'
SYNTAX_SHA = '5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa'
OID = re.compile('[0-9a-f]{40}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_owner(path, sha, name):
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'canonical frozen helper path required')
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == sha, 'frozen helper bytes differ')
    namespace = {'__name__': name, '__file__': str(path)}
    exec(compile(data, str(path), 'exec'), namespace)
    return namespace


def safe_name(value):
    require(type(value) is str and value and not any(c in value for c in ('\0', '\n', '\r', '\t')),
            'ordinary source path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and not set(path.parts) & {'.', '..', '.git'},
            'normalized relative source path required')
    return value


def overlay_expectation(baseline, overlays):
    """Pure complete-tree expectation; selected blobs cannot replace links/trees."""
    require(type(baseline) is dict and type(overlays) is dict, 'tree maps required')
    expected = {name: dict(entry) for name, entry in baseline.items()}
    for name, entry in overlays.items():
        safe_name(name)
        require(type(entry) is dict and set(entry) == {'mode', 'kind', 'oid'} and
                entry['mode'] in ('100644', '100755') and entry['kind'] == 'blob' and
                type(entry['oid']) is str and OID.fullmatch(entry['oid']), 'ordinary selected blob required')
        prior = baseline.get(name)
        require(prior is None or prior['kind'] == 'blob' and prior['mode'] in ('100644', '100755'),
                'selected source cannot replace a baseline Gitlink or symlink')
        require(not any(path != name and (path.startswith(name + '/') or name.startswith(path + '/'))
                        for path in expected), 'selected source collides with another baseline or selected entry')
        expected[name] = dict(entry)
    return expected


def prepare(args):
    module = checked_owner(LIBRARY, LIBRARY_SHA, 'current_main_git_library')
    eligibility = checked_owner(ELIGIBILITY, ELIGIBILITY_SHA, 'current_main_source_eligibility')
    syntax_owner = checked_owner(SYNTAX, SYNTAX_SHA, 'current_main_syntax_library')
    selection, selection_pin = module['selected'](args.selection, args.selection_sha)
    require(set(selection) - {'content_sha256'} == {'schema', 'canonical_repository',
            'previous_publication_binding', 'baseline_origin_main', 'selected_files', 'commit_message'} and
            selection['schema'] == 'current-main-source-overlay-selection/v1', 'closed current-main selection required')
    previous = module['pinned'](selection['previous_publication_binding'])
    require(previous.get('schema') == 'git-integrated-main-publication/v1' and
            previous.get('status') == 'published_and_verified' and previous.get('remote_publication_verified') is True and
            previous.get('normalized_origin') == 'github.com/endomorphosis/lift_coding' and
            previous['integrated_tip'] == previous['remote_main_after'], 'verified previous root publication required')
    root = Path(selection['canonical_repository']).absolute()
    require(root == Path(previous['canonical_repository']).absolute() and
            root.resolve(strict=True) == root and not any(p.is_symlink() for p in (root, *root.parents)),
            'canonical original repository differs')
    origin = module['origin'](module['text'](root, 'remote', 'get-url', 'origin'))
    require(origin == previous['normalized_origin'], 'owned canonical origin differs')
    baseline = selection['baseline_origin_main']
    require(type(baseline) is str and OID.fullmatch(baseline), 'exact selected current-main OID required')
    require(type(args.branch) is str and args.branch.startswith('codex/') and len(args.branch) <= 200,
            'fresh bounded campaign branch required')
    module['git'](root, 'check-ref-format', '--branch', args.branch)
    require(module['git'](root, 'show-ref', '--verify', '--quiet', 'refs/heads/' + args.branch,
                          accepted=(0, 1)).returncode == 1, 'selected branch already exists')
    files = selection['selected_files']
    require(type(files) is list and 0 < len(files) <= 256 and
            all(type(row) is dict and type(row.get('bytes')) is int and row['bytes'] > 0 for row in files) and
            sum(row['bytes'] for row in files) <= 64 * 1024 * 1024, 'bounded explicit source selection required')
    selected_data = dict(eligibility['source_file'](root, row, module) for row in files)
    require(len(selected_data) == len(files), 'duplicate selected source path')
    message = selection['commit_message']
    require(type(message) is str and 0 < len(message) <= 1000 and '\0' not in message,
            'bounded ordinary commit message required')
    original_head = module['text'](root, 'rev-parse', 'HEAD')
    original_branch = module['text'](root, 'symbolic-ref', '--quiet', 'HEAD')
    original_index = module['original_index'](root)
    output = args.output.absolute()
    require(not output.exists() and output.parent.is_dir() and
            not any(p.is_symlink() for p in (output, *output.parents)), 'fresh canonical preparation output required')
    output.mkdir(mode=0o700)
    module['save'](output / 'start.json', {'schema': 'current-main-source-overlay-start/v1',
        'selection_binding': selection_pin, 'previous_publication_binding': selection['previous_publication_binding'],
        'baseline_origin_main': baseline, 'original_HEAD': original_head, 'original_branch': original_branch,
        'original_index_binding': original_index, 'push_executed': False, 'training_executed': False})
    module['git'](root, 'fetch', '--no-recurse-submodules', '--no-auto-maintenance', 'origin',
                  'refs/heads/main:refs/remotes/origin/main')
    require(module['text'](root, 'rev-parse', 'refs/remotes/origin/main') == baseline,
            'origin/main advanced from selected baseline; prepare a new immutable selection')
    module['git'](root, 'merge-base', '--is-ancestor', previous['integrated_tip'], baseline)
    baseline_tree = module['tree'](root, baseline)
    work = output / 'publication-worktree'
    module['git'](root, 'worktree', 'add', '-b', args.branch, str(work), baseline)
    require(module['text'](work, 'rev-parse', 'HEAD') == baseline and
            module['text'](work, 'symbolic-ref', '--short', 'HEAD') == args.branch,
            'fresh baseline worktree or branch differs')
    require(not module['text'](work, 'status', '--porcelain', '--untracked-files=normal'),
            'fresh baseline worktree is not clean')
    require(module['tree'](work, baseline) == baseline_tree, 'fresh baseline complete tree differs')
    overlays, index_rows = {}, []
    for row in files:
        name, data = eligibility['source_file'](root, row, module)
        require(data == selected_data[name], 'selected source changed after baseline selection')
        oid = module['git'](work, 'hash-object', '-w', '--stdin', data=data).stdout.decode().strip()
        overlays[name] = {'mode': row['mode'], 'kind': 'blob', 'oid': oid}
        index_rows.append(row['mode'].encode() + b' ' + oid.encode() + b'\t' + os.fsencode(name) + b'\0')
    expected = overlay_expectation(baseline_tree, overlays)
    for row in files:
        name = row['path']
        destination = work / name
        require(not any(p.is_symlink() for p in (destination, *destination.parents)), 'symlink destination rejected')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(selected_data[name])
        destination.chmod(0o755 if row['mode'] == '100755' else 0o644)
    module['git'](work, 'update-index', '-z', '--index-info', data=b''.join(index_rows))
    if module['git'](work, 'diff', '--cached', '--quiet', accepted=(0, 1)).returncode:
        module['git'](work, 'commit', '-m', message)
    tip = module['text'](work, 'rev-parse', 'HEAD')
    actual = module['tree'](work, tip)
    require(actual == expected, 'commit/hook changed an unselected entry or selected source')
    require(not module['text'](work, 'status', '--porcelain', '--untracked-files=normal'),
            'prepared private worktree is not clean')
    for name, entry in baseline_tree.items():
        require(name in overlays or actual.get(name) == entry, 'unselected baseline entry or mode changed')
        if entry['mode'] == '160000':
            require(actual.get(name) == entry, 'baseline Gitlink changed')
    require(not set(actual) - set(baseline_tree) - set(overlays), 'unselected source path appeared')
    for row in files:
        eligibility['source_file'](root, row, module)
    require(module['text'](root, 'rev-parse', 'HEAD') == original_head and
            module['text'](root, 'symbolic-ref', '--quiet', 'HEAD') == original_branch and
            module['original_index'](root) == original_index, 'original HEAD/index or branch changed')
    for ancestor in (baseline, previous['integrated_tip']):
        module['git'](work, 'merge-base', '--is-ancestor', ancestor, tip)
    require(module['binding'](selection_pin['path']) == selection_pin and
            module['binding'](selection['previous_publication_binding']['path']) == selection['previous_publication_binding'],
            'source selection or previous publication receipt changed')
    sources = [{'path': name, 'mode': row['mode'], 'kind': row['kind'], 'source_git_oid': row['oid']}
               for name, row in sorted(actual.items())]
    manifest = {'schema': 'full-current-git-tree-qualification/v1', 'canonical_repository': str(root),
        'canonical_snapshot_commit': tip, 'integrated_tip': tip, 'source_bindings': sources,
        'source_binding_count': len(sources), 'canonical_entries_missing_or_changed': [],
        'full_current_tree_exactly_preserved': True, 'metadata_only_no_source_credentials_or_model_bytes_read': True,
        'normalized_origin': origin, 'origin_push_performed': False, 'qualification_binding': selection_pin,
        'source_git_oid_recipe': 'complete_selected_current_main_tree_plus_only_exact_source_overlays'}
    manifest_path = output / 'fulltree-manifest.json'
    with manifest_path.open('xb') as stream:
        os.chmod(manifest_path, 0o600)
        stream.write(module['raw'](manifest) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    manifest_pin = module['binding'](manifest_path)
    plan = {'schema': 'current-main-source-overlay-main-plan/v1', 'canonical_repository': str(root),
        'normalized_origin': origin, 'fresh_worktree': str(work), 'integration_branch': args.branch,
        'baseline_remote_ref': 'origin/main', 'origin_main_sha256_or_git_oid': baseline,
        'heads': [{'oid': baseline, 'kind': 'selected_current_main_baseline'},
                  {'oid': previous['integrated_tip'], 'kind': 'previous_verified_publication'},
                  {'oid': tip, 'kind': 'canonical_current_source'}],
        'authoritative_source': {'snapshot_commit': tip, 'selected_files': [{**row, 'state': 'present'} for row in files]},
        'authoritative_full_tree_snapshot': {'snapshot_commit': tip, 'manifest_binding': manifest_pin},
        'published_gitlinks': [], 'previous_publication_binding': selection['previous_publication_binding'],
        'selected_supplement_binding': selection_pin, 'current_baseline_entries_preserved_except_selected_overlays': True,
        'baseline_gitlinks_unchanged': True, 'origin_push_authorized_for_helper': False, 'training_authorized_for_helper': False}
    plan_pin = module['save'](output / 'plan.json', plan)
    syntax = syntax_owner['syntax_findings'](work, baseline, tip,
        {name: {'git_oid': row['oid']} for name, row in actual.items()})
    require(not syntax['newly_invalid_executable_source'] and not syntax['inherited_canonical_syntax_findings'],
            'invalid changed Python blocks current-main publication')
    prepared = {'schema': 'worktree-main-integration-fulltree-prepublication/v2', 'canonical_repository': str(root),
        'normalized_origin': origin, 'fresh_worktree': str(work), 'integrated_tip': tip,
        'baseline_origin_main': baseline, 'baseline_remote_ref': 'origin/main', 'selected_head_count': len(plan['heads']),
        'all_selected_heads_ancestors': True, 'published_gitlinks': [], 'plan_binding': plan_pin,
        'fulltree_manifest_binding': manifest_pin, 'full_canonical_blob_path_count': sum(row['kind'] == 'blob' for row in actual.values()),
        'complete_canonical_snapshot_blobs_preserved': True, 'intentional_deleted_paths_preserved': True,
        'prior_integrated_tip_ancestor': True, 'original_head_and_index_preserved': True,
        'all_source_python_parses_claimed': False, 'syntax_qualification': syntax, 'python_syntax_errors': [],
        'eligible_for_root_prepublication_review': True, 'origin_push_executed': False, 'training_executed': False,
        'history_rewritten': False, 'force_push_used': False, 'original_worktrees_replaced': False,
        'source_supplement_overlays': files, 'unselected_committed_entries_and_modes_preserved': True,
        'baseline_gitlinks_unchanged': True, 'local_git_hooks_disabled': False,
        'deletion_scope': 'No baseline paths deleted; previous payload omissions stay absent through unchanged baseline entries.'}
    prepared_pin = module['save'](output / 'prepared.json', prepared)
    result = {'schema': 'current-main-source-overlay-preparation/v1', 'tip': tip,
        'baseline_origin_main': baseline, 'plan_binding': plan_pin, 'prepared_binding': prepared_pin,
        'manifest_binding': manifest_pin, 'selection_binding': selection_pin, 'selected_source_file_count': len(files),
        'baseline_tree_entry_count': len(baseline_tree), 'baseline_gitlink_count': sum(r['mode'] == '160000' for r in baseline_tree.values()),
        'original_HEAD_index_branch_and_selected_bytes_preserved': True,
        'unselected_baseline_entries_modes_and_gitlinks_preserved': True,
        'ordinary_commit_preserves_previous_and_current_main_history': True, 'push_executed': False, 'training_executed': False}
    module['save'](output / 'preparation.json', result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--branch', required=True)
    os.umask(0o077)
    prepare(parser.parse_args())


if __name__ == '__main__':
    main()
