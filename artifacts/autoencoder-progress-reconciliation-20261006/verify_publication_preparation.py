#!/usr/bin/env python3
"""Read local immutable Git objects; retain the post-repair source observation.

No checkout, index, model, network, database or historical receipt is changed.
The review ledger's original snapshots are deliberately not rewritten.
"""
from pathlib import Path
import hashlib
import json
import subprocess

BASE = Path('/home/barberb/lift_coding/artifacts/autoencoder-progress-reconciliation-20261006')
REPOSITORIES = {
    'workspace': Path('/home/barberb/lift_coding/.worktrees/autoencoder-progress-reconciliation-root-20261006'),
    'datasets': Path('/home/barberb/lift_coding/.worktrees/autoencoder-progress-reconciliation-datasets-20261006'),
    'accelerate': Path('/home/barberb/lift_coding/.worktrees/contextual-legal-runtime-accelerate-20261006'),
}
DATASET_HEAD = '0f36163a585a9bf514c41d8eabe202936c000705'
APPROVED_CHANGES = {
    'docs/autoencoders/contextual_legal_reconstruction_runtime.md',
    'docs/autoencoders/paraphrase_modality_diagnostics.md',
    'ipfs_datasets_py/logic/formalization/autoencoder/contextual_legal_ir_runtime.py',
    'tests/unit/logic/formalization/autoencoder/test_contextual_legal_ir_runtime.py',
}


def git(role, *args):
    return subprocess.check_output(['git', '-C', str(REPOSITORIES[role]), *args])


def main():
    ledger = json.loads((BASE / 'integration-ledger.json').read_text())
    heads = {**ledger['reviewed_main_snapshots'], 'datasets': DATASET_HEAD}
    checks = []
    for contribution in ledger['effective_contribution_reviews']:
        role = contribution['repository_role']
        for row in contribution['review']['paths']:
            raw = git(role, 'show', f"{heads[role]}:{row['path']}")
            sha = hashlib.sha256(raw).hexdigest()
            changed = sha != row['target']['sha256']
            assert not changed or (role == 'datasets' and row['path'] in APPROVED_CHANGES), (role, row['path'])
            checks.append(dict(repository_role=role, path=row['path'], target_commit=heads[role],
                bytes=len(raw), sha256=sha, changed_since_reviewed_main=changed,
                change_scope='approved metadata/documentation/test correction' if changed else 'unchanged reviewed main bytes'))
    assert len(checks) == 83
    report_checks = []
    for entry in ledger['entries'][:16]:
        source = entry['source']
        role = ('datasets' if 'ipfs_datasets' in source['repository'] else
                'accelerate' if 'ipfs_accelerate' in source['repository'] else 'workspace')
        raw = git(role, 'show', f"{source['commit']}:{source['path']}")
        assert len(raw) == source['bytes'] and hashlib.sha256(raw).hexdigest() == source['sha256']
        git(role, 'merge-base', '--is-ancestor', source['commit'], heads[role])
        report_checks.append(dict(id=entry['id'], repository_role=role,
            original_commit=source['commit'], original_report_sha256=source['sha256'],
            retained_and_reachable_from_final_component_main=True))
    receipt = dict(schema='autoencoder-reconciliation-publication-preparation/v1',
        reviewed_snapshots_unchanged_in_ledger=ledger['reviewed_main_snapshots'],
        publication_component_heads={key: heads[key] for key in ('datasets', 'accelerate')},
        parent_base=heads['workspace'],
        planned_gitlinks={'external/ipfs_datasets': DATASET_HEAD,
            'external/ipfs_accelerate': heads['accelerate'],
            'external/ipfs_kit': '8ac00bb1974b1378e12091d546d8425af34049e0'},
        contribution_path_count=len(checks), missing_paths=0,
        approved_changed_paths_count=sum(row['changed_since_reviewed_main'] for row in checks),
        contribution_checks=checks, original16_report_retention=report_checks,
        scope='The metadata repair successor is observed separately; initial peer-reviewed source snapshots and historical model receipts are preserved. No model or proof qualification is granted.')
    (BASE / 'publication-preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(current_contribution_paths_present=len(checks),
        approved_metadata_changes=receipt['approved_changed_paths_count'],
        original_reports_retained=len(report_checks), dataset_main=DATASET_HEAD)))


if __name__ == '__main__':
    main()
