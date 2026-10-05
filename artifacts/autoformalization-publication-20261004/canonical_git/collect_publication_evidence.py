"""Collect selected verified Git/HF receipts; do not create a training gate.

The root coordinator chooses actual publication receipts and remains responsible
for training authorization. This metadata-only collector imports no model code,
calls no network services, and makes no new remote verification claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
from pathlib import Path

OWNER = Path(__file__).with_name('update_published_child_gitlinks.py')
OWNER_SHA = '605020a6c4f263b6f743e569e752251fc6ade608324f3dabd6d3be82bfbe4b31'
EXPECTED_REPOS = {'DCEC_Library', 'Eng-DCEC', 'ShadowProver', 'Talos', 'common_crawl_search_engine',
                  'convert_to_txt_based_on_mime_type', 'omni_converter_mk2', 'ipfs_model_manager_py',
                  'ipfs_transformers_py', 'ipfs_kit_py', 'Mcp-Plus-Plus', 'swissknife', 'hallucinate_app',
                  'ipfs_accelerate_py', 'ipfs_datasets_py', 'lift_coding'}
LANES = {'Publicus/legal-ir-autoencoder', 'Publicus/intent-ir-autoencoder',
         'Publicus/security-ir-autoencoder', 'Publicus/ui-ux-ir-autoencoder'}


def owner():
    if hashlib.sha256(OWNER.read_bytes()).hexdigest() != OWNER_SHA:
        raise ValueError('selected immutable receipt collector owner differs')
    return runpy.run_path(str(OWNER), run_name='publication_receipt_library')


def metadata(module, path, digest):
    pin = module['binding'](path)
    module['require'](pin['sha256'] == digest, 'selected publication receipt bytes differ')
    value = json.loads(Path(path).read_bytes())
    body = {k: v for k, v in value.items() if k != 'content_sha256'}
    encoded = module['raw'](body)
    if value.get('schema') in {'retained-HF-append-only-publication/v1', 'retained-HF-publication-complete/v1'}:
        encoded += b'\n'  # Original retained publisher seals its canonical LF wire.
    if 'content_sha256' in value:
        module['require'](value['content_sha256'] == hashlib.sha256(encoded).hexdigest(),
                          'schema-specific publication receipt seal differs')
    return value, pin


def metadata_pin(module, pin):
    module['require'](type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'}, 'closed receipt binding required')
    value, observed = metadata(module, pin['path'], pin['sha256'])
    module['require'](observed == pin, 'exact receipt binding differs')
    return value


def check_git(module, pin, expected_origin):
    receipt = module['pinned'](pin)
    require = module['require']
    oid = receipt.get('integrated_tip')
    require(receipt.get('schema') == 'git-integrated-main-publication/v1'
            and receipt.get('status') == 'published_and_verified'
            and receipt.get('remote_publication_verified') is True
            and receipt.get('normalized_origin') == expected_origin
            and isinstance(oid, str) and module['OID'].fullmatch(oid)
            and receipt.get('remote_main_after') == oid
            and receipt.get('force_push_used') is False and receipt.get('remote_refs_deleted') is False,
            'actual verified non-force Git publication receipt required')
    return {'normalized_origin': expected_origin, 'oid': oid, 'url': receipt['url'], 'receipt_binding': pin}


def check_hf(module, pin, retained=False):
    receipt = metadata_pin(module, pin)
    require = module['require']
    if retained:
        require(receipt.get('schema') == 'retained-HF-append-only-publication/v1'
                and receipt.get('remote_verification_completed') is True,
                'verified retained HF publication required')
    else:
        require(receipt.get('schema') == 'append-only-HF-publication/v1'
                and receipt.get('status') == 'published_and_verified'
                and receipt.get('all_remote_files_verified') is True,
                'actual verified append-only HF publication required')
    recovered = receipt.get('publication_verified_by_readonly_recovery') is True
    if recovered:
        require(receipt.get('repo_id') == 'Publicus/autoformalization-artifacts'
                and receipt.get('repo_type') == 'dataset'
                and receipt.get('preservation_exception') == 'HF_added_exact_two_selected_path_LFS_rules_to_initial_system_gitattributes'
                and receipt.get('only_prior_path_changed') == '.gitattributes'
                and receipt.get('other_prior_paths_preserved') is True
                and receipt.get('prior_user_data_files_modified') is False
                and receipt.get('root_README_modified') is False
                and receipt.get('network_mutations_by_verifier') == 0,
                'closed readonly HF tracking-metadata recovery required')
        plan = metadata_pin(module, receipt['selected_plan'])
        require(plan['repo_id'] == receipt['repo_id'] and plan['prefix'] == receipt['prefix']
                and len(plan['original_git_blobs']) == 2, 'exact two-artifact recovery selection required')
        identity_text = []
        for text_pin in receipt['tracking_metadata_content_bindings']:
            require(module['binding'](text_pin['path']) == text_pin, 'selected tracking metadata bytes differ')
            identity_text.append(Path(text_pin['path']).read_bytes())
        require(len(identity_text) == 2, 'exact before/after tracking metadata required')
        expected_additions = ''.join(receipt['prefix'] + '/' + row['path']
            + ' filter=lfs diff=lfs merge=lfs -text\n' for row in plan['original_git_blobs']).encode()
        require(identity_text[1] == identity_text[0] + expected_additions
                and receipt['tracking_metadata_additions'].encode() == expected_additions,
                'only exact selected-artifact tracking rules may differ')
        preservation_scope = receipt['preservation_exception']
    else:
        require(receipt.get('prior_remote_files_deleted') is False
                and receipt.get('root_README_or_defaults_modified') is False
                and receipt.get('prior_files_preserved_exact_git_and_LFS_identities') is True,
                'HF prior-path preservation differs')
        preservation_scope = 'all_prior_paths_exact_git_and_LFS_identities_preserved'
    oid = receipt.get('commit_oid')
    require(isinstance(oid, str) and module['OID'].fullmatch(oid), 'exact HF immutable revision required')
    files = receipt.get('remote_files')
    require(isinstance(files, list) and files, 'verified HF file identities required')
    names = set()
    size = 0
    for row in files:
        name = module['safe_path'](row['path'])
        require(name not in names and isinstance(row['bytes'], int) and not isinstance(row['bytes'], bool)
                and row['bytes'] >= 0 and isinstance(row.get('sha256'), str)
                and module['SHA'].fullmatch(row['sha256']), 'unique verified HF file size/SHA identities required')
        names.add(name)
        size += row['bytes']
    if recovered:
        declared = {receipt['prefix'] + '/' + row['path']: (row['bytes'], row['sha256']) for row in plan['files']}
        require(declared == {row['path']: (row['bytes'], row['sha256']) for row in files},
                'recovered HF files differ from selected plan')
    else:
        count_key, bytes_key = ('new_file_count', 'new_bytes') if retained else ('selected_file_count', 'selected_bytes')
        require(receipt.get(count_key) == len(files) and receipt.get(bytes_key) == size,
                'HF verified-file count or size joins differ')
    return {'repo_id': receipt['repo_id'], 'repo_type': receipt.get('repo_type', 'model'),
            'commit_oid': oid, 'prefix': receipt['prefix'], 'release_url': receipt['release_url'],
            'verified_file_count': len(files), 'verified_file_bytes': size, 'receipt_binding': pin,
            'prior_path_preservation_scope': preservation_scope}


def collect(args):
    module = owner()
    require = module['require']
    ready, ready_pin = module['selected'](args.git_ready_map, args.git_ready_map_sha)
    require(ready.get('schema') == 'verified-child-publication-ready-map/v1', 'selected initial owned-origin map required')
    git_rows = []
    for row in ready['repositories']:
        git_rows.append(check_git(module, row['publication_binding'], row['normalized_origin']))
    for expected_origin, path, digest in args.git_publication:
        _, pin = module['selected'](path, digest)
        git_rows.append(check_git(module, pin, expected_origin))
    origins = [row['normalized_origin'] for row in git_rows]
    require(len(origins) == len(set(origins)) == 16 and set(origins) ==
            {'github.com/endomorphosis/' + name for name in EXPECTED_REPOS},
            'all sixteen exact owned origins must have one selected verified receipt')
    retained, retained_pin = metadata(module, args.retained_lanes, args.retained_lanes_sha)
    require(retained.get('schema') == 'retained-HF-publication-complete/v1'
            and retained.get('all_remote_files_verified') is True, 'complete initial HF publication receipt required')
    hf_rows = []
    for row in retained['releases']:
        release = check_hf(module, row['receipt'], retained=True)
        require(release['repo_id'] == row['repo_id'] and release['commit_oid'] == row['commit_oid']
                and release['verified_file_count'] == row['new_files'] and release['verified_file_bytes'] == row['new_bytes'],
                'retained aggregate/release identity differs')
        hf_rows.append(release)
    require(len(hf_rows) == 4 and {row['repo_id'] for row in hf_rows} == LANES
            and sum(row['verified_file_count'] for row in hf_rows) == retained['total_files']
            and sum(row['verified_file_bytes'] for row in hf_rows) == retained['total_bytes'],
            'four initial lane release identities and totals required')
    for path, digest in args.hf_publication:
        _, pin = module['selected'](path, digest)
        hf_rows.append(check_hf(module, pin))
    identities = [(row['repo_id'], row['repo_type'], row['commit_oid'], row['prefix']) for row in hf_rows]
    require(len(identities) == len(set(identities)), 'duplicate HF release selection')
    pins = [ready_pin, retained_pin, *[row['receipt_binding'] for row in git_rows],
            *[row['receipt_binding'] for row in hf_rows]]
    for pin in pins:
        require(module['binding'](pin['path']) == pin, 'selected receipt bytes changed during collection')
    evidence = {'schema': 'verified-autoformalization-publication-evidence/v1',
        'initial_owned_repository_count': 16, 'github_publications': sorted(git_rows, key=lambda row: row['normalized_origin']),
        'huggingface_publications': sorted(hf_rows, key=lambda row: (row['repo_id'], row['commit_oid'], row['prefix'])),
        'selected_initial_ready_map_binding': ready_pin, 'selected_initial_HF_aggregate_binding': retained_pin,
        'all_selected_publications_report_verified': True,
        'receipt_collection_scope': 'Exact root-selected immutable receipt bytes and producer-reported verification; no new network revalidation.',
        'training_gate_created': False, 'training_executed': False, 'model_calls': 0,
        'proof_authority': False, 'source_fidelity_established': False, 'semantic_gold_created': False}
    selected_evidence = module['save'](args.output, evidence)
    print(json.dumps({'evidence_binding': selected_evidence,
                      'training_gate_created': False, 'github_publication_count': len(git_rows),
                      'HF_release_count': len(hf_rows)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('git-ready-map', 'retained-lanes', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('git-ready-map-sha', 'retained-lanes-sha'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--git-publication', nargs=3, action='append', default=[],
                        metavar=('ORIGIN', 'RECEIPT', 'SHA256'))
    parser.add_argument('--hf-publication', nargs=2, action='append', default=[], metavar=('RECEIPT', 'SHA256'))
    os.umask(0o077)
    collect(parser.parse_args())
