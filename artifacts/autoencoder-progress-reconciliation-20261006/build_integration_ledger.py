"""Bind published studies and effective source to explicit repository snapshots.

Reuses the existing read-only Git auditor. No compiler, model, encoder, database,
Hub, provider, or proof runtime is imported or called.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

BASE = Path('/home/barberb/lift_coding')
ROOT = BASE / '.worktrees/autoencoder-progress-reconciliation-root-20261006'
DATASETS = BASE / '.worktrees/autoencoder-progress-reconciliation-datasets-20261006'
ACCELERATE = BASE / '.worktrees/contextual-legal-runtime-accelerate-20261006'
OUT = BASE / 'artifacts/autoencoder-progress-reconciliation-20261006'


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def source(repo, commit, path):
    blob = git(repo, 'show', commit + ':' + path)
    return {'repository': str(repo), 'commit': commit, 'path': path,
            'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def main():
    spec = importlib.util.spec_from_file_location('existing_progress_auditor', ROOT / 'scripts/review_autoencoder_progress.py')
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    targets = {'workspace': git(ROOT, 'rev-parse', 'HEAD').decode().strip(),
               'datasets': '795d960170214d03e2eaf4c0a13ad4eb922c5c08',
               'accelerate': 'd5c59e961d1a0ca8d09296b520cbd414a2078235'}
    prior_path = 'artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json'
    prior_bytes = git(ROOT, 'show', targets['workspace'] + ':' + prior_path)
    prior = json.loads(prior_bytes)
    assert len(prior['entries']) == 16
    studies = copy.deepcopy(prior['entries'])
    for row in studies:
        saved = row['source']
        lane = 'datasets' if 'ipfs_datasets' in saved['repository'] else 'workspace'
        repo = DATASETS if lane == 'datasets' else ROOT
        actual = source(repo, saved['commit'], saved['path'])
        assert (actual['bytes'], actual['sha256']) == (saved['bytes'], saved['sha256'])
        review = auditor.review(repo, saved['commit'], targets[lane], [saved['path']])
        assert review['source_history_reachable_from_target'] and not review['counts']['missing']
        row['current_main_observation'] = {'repository_role': lane, 'target_commit': targets[lane],
            'history_reachable': True, 'effective_report_status': review['paths'][0]['status'],
            'target_report_identity': review['paths'][0]['target']}
    original = json.loads(git(DATASETS, 'show',
        '39f25777d557df1c51b8f98ed0dcd084c35d4d6d:docs/autoencoders/evidence/contextual-legal-runtime-20261006/separate-evaluation.json'))
    assert len(original['lanes']) == 2
    for lane in original['lanes']:
        assert lane['ir_metrics']['ordered_exact'] == lane['canonical_contract_exact'] == 48
        assert lane['ir_metrics']['expected_rules'] == 180
        assert lane['reference_qualifier_fields_all_empty']
        assert lane['original_text_metrics']['verbatim_utf8_exact'] == lane['original_text_metrics']['nfc_whitespace_exact'] == 0
    normative = json.loads(git(DATASETS, 'show', targets['datasets'] +
        ':docs/implementation/reports/evidence/decoder-normative-wording-20261006/results.json'))
    selected = {(row['dimension'], row['arm']): row for row in normative['panels'] if row['role'] == 'selected'}
    assert len(normative['panels']) == 8 and len(selected) == 4
    expected = {(384, 'normative-wording-zero'): 55, (384, 'normative-wording-ce'): 60,
                (768, 'normative-wording-zero'): 60, (768, 'normative-wording-ce'): 60}
    for identity, exact in expected.items():
        row = selected[identity]
        assert row['ordered_exact'] == exact and row['sample_count'] == 60
        assert row['selected_last_identical_tensor_alias'] is True
    assert normative['fresh_holdout'] is False and normative['original_development_meanings_previously_exposed'] is True
    assert normative['logic_family_projections_executed'] is False and normative['lake_executed'] is False
    new = [
        {'id': 'original-contextual-cached-replay-and-text-baseline',
         'source': source(DATASETS, '39f25777d557df1c51b8f98ed0dcd084c35d4d6d',
             'docs/autoencoders/evidence/contextual-legal-runtime-20261006/separate-evaluation.json'),
         'kind': 'original-cached-decoder-replay-and-separate-source-withheld-text-evaluation',
         'scope': 'Original selected Legal384/768, exposed48 paragraphs and180 rules per width, cached512 experiment.',
         'findings': ['Both widths48/48 ordered and canonical IRs,180/180 rules, exact historical raw token/status/EOS parity.',
             'Deterministic source-withheld text baseline48 outputs per width:0/48 UTF8 and0/48 NFC/whitespace exact.',
             'Same original state/donor/paragraph/clause assets; generation/evaluation separated;454 saved local controls passed.'],
         'limitations': ['Every qualifier list is empty; no independent semantic holdout, trained prose head,8192 trial or proof.',
             'Caller-pinned paragraph bytes alone do not authenticate native producer provenance; saved clause-context joins bind supplied clause/context bytes to the original saved inventory.'],
         'next_gap': 'Fresh grouped source fidelity, explicit prose decoder/residual contract and task-specific warm-start transfer.'},
        {'id': 'broader-normative-wording-paired-decoder-fits',
         'source': source(DATASETS, targets['datasets'],
             'docs/implementation/reports/evidence/decoder-normative-wording-20261006/results.json'),
         'kind': 'decoder-modality-auxiliary-training-and-prospective-wording-development',
         'scope': 'Two native widths, zero/0.05 arms, original90 TRAIN meanings and separately authored60 wording sources from30 exposed DEV meanings.',
         'findings': ['384D new wording exact55/60->60/60;768D60/60 in both arms.',
             'Original48-row development stays48/48;768 auxiliary token CE is slightly worse, so gains are width-specific.',
             'Four unique trained tensors; selected/last aliases do not count as independent replications;297 published pure contracts.'],
         'limitations': ['Prospective wording is not untouched meaning; empty qualifiers and fixed32-token grammar.',
             'No native compiler/logic-family projection/prover/Lake in this experiment and no automatic checkpoint promotion.'],
         'next_gap': 'Replay exposed v3 retention and independently reviewed richer/groups before promotion or extending decoder dialect.'},
    ]
    for row in new:
        saved = row['source']
        review = auditor.review(DATASETS, saved['commit'], targets['datasets'], [saved['path']])
        assert review['source_history_reachable_from_target'] and review['counts']['identical'] == 1
        row['current_main_observation'] = {'repository_role': 'datasets', 'target_commit': targets['datasets'],
            'history_reachable': True, 'effective_report_status': 'identical',
            'target_report_identity': review['paths'][0]['target']}
    studies.extend(new)
    cohorts = [row['id'] for row in studies]
    assert len(studies) == len(set(cohorts)) == 18
    contributions = []
    for repo, lane, source_commit, parent, prefixes in [
        (DATASETS, 'datasets', '39f25777d557df1c51b8f98ed0dcd084c35d4d6d', '7a16fc06578abbf3cc95ad3ed8e4fa8a33b1ea0d', ()),
        (DATASETS, 'datasets', targets['datasets'], '39f25777d557df1c51b8f98ed0dcd084c35d4d6d', ()),
        (ACCELERATE, 'accelerate', 'bcd466018cff101c34b281a4fe234bdc1f33fb0a', '82671e6c8411875cb9919e3a71b07831548c0aeb', ()),
        (ACCELERATE, 'accelerate', '82671e6c8411875cb9919e3a71b07831548c0aeb', 'a98308e4c162bd4cd2977a3ac37394f55d3a06c0', ()),
    ]:
        paths = git(repo, 'diff', '--name-only', parent, source_commit).decode().splitlines()
        review = auditor.review(repo, source_commit, targets[lane], paths)
        assert review['source_history_reachable_from_target'] and not review['counts']['missing']
        contributions.append({'repository_role': lane, 'source_commit': source_commit,
                              'target_commit': targets[lane], 'review': review})
    result = {'schema': 'autoencoder-current-effort-integration-ledger/v1', 'reviewed_main_snapshots': targets,
        'prior_review_pin': {'path': prior_path, 'commit': targets['workspace'], 'bytes': len(prior_bytes),
                            'sha256': hashlib.sha256(prior_bytes).hexdigest()},
        'study_count': 18, 'prior_study_count': 16, 'new_observation_count': 2, 'entries': studies,
        'effective_contribution_reviews': contributions, 'main_source_omissions_found_in_selected_contributions': 0,
        'non_aggregation_rules': prior['non_aggregation_rules'], 'model_or_training_executed_by_this_review': False,
        'existing_weights_or_caches_modified': False, 'semantic_or_proof_admission_granted': False,
        'scope': 'Selected explicit contribution/report paths at immutable snapshots; inventory does not qualify every branch or live divergent file.'}
    (OUT / 'integration-ledger.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'studies': 18, 'prior_studies': 16, 'new_observations': 2,
                      'contribution_paths': sum(len(row['review']['paths']) for row in contributions),
                      'selected_main_omissions': 0, 'snapshots': targets}))


if __name__ == '__main__':
    main()
