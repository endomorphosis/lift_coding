"""Inspect retained decoder metadata and hashes without importing model code."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
REPO = WORKSPACE / 'external/ipfs_datasets'
CAMPAIGN = WORKSPACE / 'artifacts/autoformalization-alignment-20261003'
CHECKOUT = WORKSPACE / '.worktrees/alignment-decoder-768-20261003'
COMMIT = '64bc5734dc82db72e955f2e809b770127e9b6cfc'
BASE = 'ipfs_datasets_py/logic/formalization/autoencoder/'


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def binding(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(ref, base=WORKSPACE):
    path = Path(ref['path'])
    actual = binding(path if path.is_absolute() else base / path)
    assert actual['sha256'] == ref['sha256'], actual['path']
    if 'bytes' in ref:
        assert actual['bytes'] == ref['bytes'], actual['path']
    return actual


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def sidecar_run(family, arm):
    directory = REPO / 'workspace/test-logs' / family / 'training-r1/results' / arm
    training = load(directory / 'training.json')
    states = {}
    for role, filename in [('initial', 'initial-state.json'), ('selected', 'selected-state.json'),
                           ('last-attempt', 'last-attempt-state.json')]:
        path = directory / filename
        state = load(path)
        assert state['schema'] == 'private-native-dimension-source-state/v1'
        assert state['dimension'] == 768 and state['role'] == role
        assert state['selected'] is (role == 'selected')
        assert state['weights_sha256'] == digest(state['model_state'])
        assert len(state['model_state']['body.body.body.condition.weight'][0]) == 768
        assert state['architecture']['projection_frozen'] is True
        assert state['optimizer_resumable'] is False
        assert all(state[field] is False for field in ('admitted', 'qualified', 'proof_authority',
                   'checkpoint_promoted', 'fresh_holdout', 'source_semantics_verified'))
        states[role] = dict(binding(path), model_state_sha256=state['weights_sha256'],
                            recorded_tensor_sha256=state['tensor_sha256'],
                            parameter_and_buffer_count=len(state['model_state']),
                            production_runtime_compatible=state['architecture'].get('production_runtime_compatible'))
    assert states['initial']['model_state_sha256'] == states['selected']['model_state_sha256']
    assert states['initial']['model_state_sha256'] != states['last-attempt']['model_state_sha256']
    assert training['selected_epoch'] == 0 and training['optimizer_steps'] == 340
    assert training['selected_weights_sha256'] == states['selected']['recorded_tensor_sha256']
    assert training['last_complete_attempt_weights_sha256'] == states['last-attempt']['recorded_tensor_sha256']
    return {'family': family, 'arm': arm, 'dimension': 768, 'states': states,
            'training_binding': binding(directory / 'training.json'),
            'optimizer_steps': training['optimizer_steps'], 'selected_epoch': training['selected_epoch'],
            'selected_state_equals_initial': True, 'last_attempt_weights_changed': True,
            'final_development_metrics': training['last_complete_attempt']['fidelity']['metrics'],
            'final_rejection_reasons': training['history'][-1]['rejection_reasons'],
            'historical_rejection_counts': dict(Counter(reason for item in training['history']
                                                       for reason in item['rejection_reasons'])),
            'optimizer_resumable': False, 'qualified': False}


def source_span_runs():
    root = WORKSPACE / 'artifacts/legal-decoder-open-vocabulary-20261002/run-01'
    summary = load(root / 'summary.json')
    found = []
    for run in summary['runs']:
        if run['dimension'] != 768:
            continue
        selected = verify(run['checkpoint'])
        state = load(selected['path'])
        assert state['schema'] == 'native-dimensional-source-span-checkpoint/v1'
        assert state['config']['latent_dimension'] == 768
        assert state['config']['latent_enabled'] is True
        assert run['selected_new_steps'] == 400 and run['total_new_training_steps'] == 800
        assert state['progress']['optimizer_steps'] == 400
        assert all(state[key] is False for key in ('admitted', 'qualified', 'proof_authority',
                   'semantic_correctness_verified', 'promotion_performed'))
        last_path = Path(selected['path']).with_name('checkpoint-800.json')
        last = load(last_path)
        assert last['progress']['optimizer_steps'] == 800
        assert digest(state['model_state']) != digest(last['model_state'])
        found.append({'name': run['name'], 'seed': run['seed'], 'dimension': 768,
                      'selected_checkpoint': selected, 'last_checkpoint': binding(last_path),
                      'selected_new_steps': 400, 'total_new_training_steps': 800,
                      'schema': state['schema'], 'config': state['config'],
                      'context_contract': state['context_contract'],
                      'implementation': state['implementation'],
                      'selected_model_state_sha256': digest(state['model_state']),
                      'last_model_state_sha256': digest(last['model_state']),
                      'optimizer_state_serialized': isinstance(state['optimizer_state'], dict),
                      'optimizer_resume_replayed': False, 'production_ready': run['production_ready'],
                      'qualified': False, 'embedding_only_decoder': False,
                      'scope': 'byte-token source-span extraction with native768 FiLM conditioning; not vector reconstruction'})
    assert len(found) == 3
    return {'summary_binding': binding(root / 'summary.json'), 'runs': found}


def inspect():
    predecessor_path = CAMPAIGN / 'checkpoint-representation-validation.json'
    prior = load(predecessor_path)
    assert prior['content_sha256'] == digest({k: v for k, v in prior.items() if k != 'content_sha256'})
    preserved = [verify(ref, REPO) for ref in prior['source_bindings']]
    preserved += [verify(ref) for ref in prior['preserved_donor_source_bindings']]
    preserved += [verify(ref) for ref in prior['protected_protocol_bindings']]
    verify(prior['report_binding'])
    assert git(CHECKOUT, 'rev-parse', 'HEAD').decode().strip() == COMMIT
    assert git(CHECKOUT, 'branch', '--show-current').decode().strip() == 'codex/alignment-decoder-768-20261003'
    assert not git(CHECKOUT, 'status', '--porcelain=v1', '--untracked-files=all')
    files = ['source_training_v2.py', 'dimension_native_decoder_experiment.py',
             'dimension_source_inputs.py', 'action_factorized_clause_decoder_experiment.py',
             'long_span_source_value_training.py', 'generated_field_training.py',
             'gte_multilingual_profile.py', 'legal_native_conditioning.py']
    checkout_sources = []
    for name in files:
        relative = BASE + name
        observed = binding(CHECKOUT / relative)
        blob = git(REPO, 'show', COMMIT + ':' + relative)
        assert observed['sha256'] == hashlib.sha256(blob).hexdigest()
        assert observed['sha256'] == binding(REPO / relative)['sha256']
        checkout_sources.append(dict(observed, relative_path=relative, exact_git_blob_verified=True,
                                     canonical_bytes_equal=True))
    family_arms = [
        ('decoder-native-dimensions-20261003', ['pooled', 'clauses']),
        ('decoder-action-binding-20261003', ['clauses', 'action-head', 'action-contrastive']),
        ('decoder-generated-field-training-r2-20261003',
         ['boundary-first-last', 'generated-fields', 'generated-fields-every2']),
    ]
    runs = [sidecar_run(family, f'768-{arm}-{seed}') for family, arms in family_arms
            for arm in arms for seed in (1729, 2718)]
    exports = []
    for family, _ in family_arms:
        source_root = REPO / 'workspace/test-logs' / family / 'experiment-source'
        assert source_root.is_dir() and not (source_root / '.git').exists()
        exports.append({'path': str(source_root), 'kind': 'frozen_source_export_not_git_checkout',
                        'public_manifest_binding': binding(REPO / 'docs/implementation/reports/evidence' / family / 'manifest.json')})
    return {'schema': 'alignment-decoder-discovery/v1',
            'status': 'retained768_decoder_weights_found_and_isolated_checkout_created',
            'embedding_model': {'url': 'https://huggingface.co/Alibaba-NLP/gte-multilingual-base',
                                'native_dimension': 768,
                                'model_revision': '9bbca17d9273fd0d03d5725c7a4b0f6b45142062',
                                'code_revision': '40ced75c3017eb27626c9d4ea981bde21a2662f4',
                                'pooling': 'cls', 'normalization': 'l2',
                                'backbone_max_tokens': 8192, 'sidecar_experiment_token_limit': 512},
            'inspection_script_binding': binding(__file__),
            'predecessor_validation_binding': binding(predecessor_path),
            'predecessor_report_binding': prior['report_binding'],
            'unchanged_predecessor_source_count': 55, 'preserved_prior_bindings': preserved,
            'source_span_decoders': source_span_runs(),
            'formula_sidecars': {'native768_runs': runs, 'run_count': len(runs),
                                 'state_count': len(runs) * 3,
                                 'acceptance_selected_epoch_distribution': {'0': len(runs)},
                                 'trained_last_attempt_count': len(runs)},
            'frozen_exports': exports,
            'created_checkout': {'path': str(CHECKOUT), 'head': COMMIT,
                                 'branch': 'codex/alignment-decoder-768-20261003', 'git_status': 'clean',
                                 'sparse_paths': git(CHECKOUT, 'sparse-checkout', 'list').decode().splitlines(),
                                 'verified_sources': checkout_sources,
                                 'published_evidence_location': str(REPO / 'docs/implementation/reports/evidence'),
                                 'runtime_replay_admitted': False},
            'execution': {'checkpoint_metadata_read': True, 'model_loaded': False,
                          'encoder_executed': False, 'model_training_executed': False,
                          'proof_executed': False, 'download_performed': False,
                          'fresh_evaluation_executed': False, 'original_validation_corpus_accessed': False,
                          'sealed_test_accessed': False, 'new_git_worktree_created': True},
            'qualified': False, 'proof_authority': False, 'source_fidelity_established': False,
            'complete_dependency_manifest': False,
            'limitations': ['Selected catalog null is not global checkpoint absence.',
                            'Identity projection sidecars do not establish learned768 vector reconstruction.',
                            'Source-span model uses source tokens and768 conditioning, not an embedding-only neural input.',
                            'Metadata and hashes do not replace private runtime reload and numerical replay.',
                            'Final-attempt development metrics cannot relabel epoch0 selected states.',
                            'Inventory is scoped to named retained runs, not an exhaustive host search.']}


if __name__ == '__main__':
    report = inspect()
    report['content_sha256'] = digest(report)
    output = CAMPAIGN / 'decoder-discovery-01'
    output.mkdir(exist_ok=False)
    path = output / 'inventory.json'
    with path.open('x') as stream:
        json.dump(report, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'inventory': binding(path), 'formula_native768_runs': report['formula_sidecars']['run_count'],
                      'source_span_native768_runs': len(report['source_span_decoders']['runs']),
                      'created_checkout': str(CHECKOUT)}, indent=2))
