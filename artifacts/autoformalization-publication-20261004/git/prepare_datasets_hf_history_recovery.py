"""Capture an advanced published baseline without modifying the failed attempt.

Reuses independently verified original driver bytes. All actual live published
refs are excluded from rewriting. If the selected old integration does not yet
contain current main, the conversion remains explicitly pending baseline merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRIVER = BASE / 'prepare_datasets_hf_history.py'
DRIVER_SHA = '2f56b6c4c86221d1215034bae9e6cc56ad8c972e7d1b206aa60b3a0666437b03'
FAILED = BASE / 'datasets-hf-history-conversion-01'
FAILED_STATE_SHA = '6f8efb904fbcab2e36330f588b1570c3cc3e3be99d2d82c73ffa72afe79d949e'
FAILED_RECEIPT_SHA = '0fcdf22f1e87b5f82df0b7a504cda26440c884e70725c4b967408a9a7d3495a1'


def driver():
    with DRIVER.open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != DRIVER_SHA:
        raise ValueError('frozen original datasets driver differs')
    module = types.ModuleType('frozen_datasets_driver')
    module.__file__ = str(DRIVER)
    exec(compile(data, str(DRIVER), 'exec'), module.__dict__)
    return module


def failed_bindings(module):
    state_pin, state = module.fixed_json(FAILED / 'original-state.json', FAILED_STATE_SHA)
    failure_pin, _ = module.fixed_json(FAILED / 'prepare-failure.json', FAILED_RECEIPT_SHA)
    return [state_pin, failure_pin, module.binding(DRIVER)], {
        key: value for key, value in state.items() if key not in ('schema', 'content_sha256')}


def prepare(module, directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    owner = module.owner()
    prior_bindings, prior_state = failed_bindings(module)
    plan_pin, plan = module.fixed_json(module.PLAN, module.PLAN_SHA)
    prepared_pin, prepared = module.fixed_json(module.PREPARED, module.PREPARED_SHA)
    hf_plan_pin, hf_plan = module.fixed_json(module.HF_PLAN, module.HF_PLAN_SHA)
    manifest_pin = plan['authoritative_full_tree_snapshot']['manifest_binding']
    module.read_selected(manifest_pin)
    module.read_selected(hf_plan['public_manifest_binding'])
    if prepared['integrated_tip'] != module.EXPECTED_TIP:
        raise ValueError('selected old integration tip differs')
    if module.git(module.SOURCE, 'rev-parse', plan['integration_branch']).decode().strip() != module.EXPECTED_TIP:
        raise ValueError('selected original integration ref moved')
    before = owner.source_state(module.SOURCE, plan['authoritative_source']['selected_files'])
    old_added_refs = module.preserved(prior_state, before)
    module.write(directory / 'original-state.json', {'schema': 'hf-history-original-state/v1', **before})
    remote = module.git(module.SOURCE, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in ('https://github.com/endomorphosis/ipfs_datasets_py.git',
                      'https://github.com/endomorphosis/ipfs_datasets_py',
                      'git@github.com:endomorphosis/ipfs_datasets_py.git'):
        raise ValueError('unexpected datasets publication remote')
    advertised = module.refs(module.SOURCE)
    clone = directory / 'isolated.git'
    module.git(module.SOURCE, 'clone', '--bare', '--shared', '--no-hardlinks', str(module.SOURCE), str(clone))
    module.git(clone, 'remote', 'set-url', 'origin', remote)
    module.git(clone, 'fetch', '--no-tags', '--recurse-submodules=no', '--no-auto-maintenance',
               'origin', '+refs/*:refs/published-github/*')
    published, exclusions = [], []
    for row in advertised:
        oid, ref = row.split('\t')
        private = 'refs/published-github/' + ref.removeprefix('refs/')
        if module.git(clone, 'rev-parse', private).decode().strip() != oid:
            raise ValueError('published ref changed during isolated capture')
        commit = module.git(clone, 'rev-parse', '--verify', private + '^{commit}',
                            accepted=(0, 128)).decode().strip()
        if commit:
            exclusions.append(commit)
        published.append({'ref': ref, 'git_oid': oid, 'isolated_ref': private, 'commit_oid': commit or None})
    if module.refs(module.SOURCE) != advertised:
        raise ValueError('remote ref set changed during capture')
    baseline = plan['origin_main_sha256_or_git_oid']
    current_main = next((row['git_oid'] for row in published if row['ref'] == 'refs/heads/main'), None)
    if current_main is None:
        raise ValueError('current published main is missing')
    module.git(clone, 'merge-base', '--is-ancestor', baseline, current_main)
    contains_current_main = module.git(clone, 'merge-base', '--is-ancestor', current_main,
                                       module.EXPECTED_TIP, accepted=(0, 1))
    # merge-base produces no stdout for either result; inspect ancestry through
    # the complete ancestor set rather than treating empty output as success.
    del contains_current_main
    ancestors = set(module.git(clone, 'rev-list', module.EXPECTED_TIP).decode().splitlines())
    refresh_required = current_main not in ancestors
    added = module.preserved(before, owner.source_state(module.SOURCE, plan['authoritative_source']['selected_files']))
    failed_bindings(module)
    return module.write(directory / 'preflight.json', {
        'schema': 'isolated-hf-history-reference-preflight/v1',
        'original_repository': str(module.SOURCE), 'isolated_repository': str(clone),
        'selected_plan_binding': plan_pin, 'selected_prepared_binding': prepared_pin,
        'original_fulltree_manifest_binding': manifest_pin, 'hf_release_plan_binding': hf_plan_pin,
        'converter_binding': module.binding(module.OWNER), 'driver_binding': module.binding(DRIVER),
        'recovery_driver_binding': module.binding(Path(__file__).resolve()),
        'prior_failed_attempt_bindings': prior_bindings, 'prior_original_state_verified_preserved': True,
        'original_tip': module.EXPECTED_TIP, 'published_refs': published,
        'published_commit_exclusions': sorted(set(exclusions)), 'original_state': before,
        'original_state_preserved': True, 'external_added_refs_not_selected': added,
        'external_refs_added_since_failed_attempt': old_added_refs,
        'selected_oversized_artifacts': hf_plan['original_git_blobs'],
        'selected_original_main_baseline': baseline, 'captured_live_main': current_main,
        'original_main_baseline_ancestor_of_captured_live_main': True,
        'baseline_refresh_required_before_push': refresh_required,
        'scope': 'Fresh isolated capture of advanced live published refs; old candidate requires a normal baseline merge before publication if current main is not its ancestor.',
        'git_lfs_migration_executed': False, 'origin_push_executed': False,
        'hf_upload_executed': False, 'training_executed': False})


def selected(module, directory):
    _, _, preflight = module.selected_preflight(directory)
    if module.binding(Path(__file__).resolve()) != preflight['recovery_driver_binding']:
        raise ValueError('frozen recovery driver differs')
    actual, _ = failed_bindings(module)
    if actual != preflight['prior_failed_attempt_bindings']:
        raise ValueError('preserved failed attempt differs')
    return preflight


def convert(module, directory, receipt_pin):
    preflight = selected(module, directory)
    original_write = module.write

    def qualified_write(path, value):
        if Path(path).name == 'conversion.json':
            ancestors = set(module.git(preflight['isolated_repository'], 'rev-list',
                                       value['converted_tip']).decode().splitlines())
            current_main_ancestor = preflight['captured_live_main'] in ancestors
            value = {**value, 'published_main_unchanged_and_ancestor': current_main_ancestor,
                     'selected_original_baseline_ancestor': True,
                     'captured_live_main': preflight['captured_live_main'],
                     'baseline_refresh_required_before_push': not current_main_ancestor,
                     'eligible_for_origin_main_push': False,
                     'scope': 'Exact historical archive conversion only. All actual published refs remain untouched and excluded; pending normal baseline merge and independent V4 qualification before any push.'}
        return original_write(path, value)

    module.write = qualified_write
    return module.convert(directory, receipt_pin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'convert'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hf-publication-receipt-binding', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    module = driver()
    try:
        if args.operation == 'prepare':
            result = prepare(module, args.directory)
        else:
            if args.hf_publication_receipt_binding is None:
                parser.error('conversion requires an external HF receipt file binding')
            result = convert(module, args.directory, json.loads(args.hf_publication_receipt_binding.read_bytes()))
    except Exception as error:
        if args.directory.is_dir():
            failure = args.directory / (args.operation + '-failure.json')
            if not failure.exists():
                module.write(failure, {'schema': 'isolated-hf-history-operation-failure/v1',
                    'operation': args.operation, 'error_type': type(error).__name__,
                    'error': str(error) if isinstance(error, ValueError) else None,
                    'partial_generation_preserved': True, 'origin_push_executed': False,
                    'hf_upload_executed': False, 'training_executed': False})
        raise
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
