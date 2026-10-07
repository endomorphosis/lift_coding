"""Grant only one bounded private replay after independently audited preflight.

Invoke only after root explicitly reports preflight completion and supplies the
immutable passed independent audit SHA. No numerical owner, model, optimizer,
encoder, guardian, reservation or shared scheduler state is executed/read here.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
G = R / 'guardian'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
PRE_READY_SHA = 'e53daa730d80a736e3ec571bb9ca4e1fbf76d60fff83f66e56bafff005a5b864'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed-preflight-review', type=Path, required=True)
    parser.add_argument('--completed-preflight-review-sha256', required=True)
    args = parser.parse_args()
    ready_path = G / 'preflight-execution-readiness.json'
    if hashlib.sha256(ready_path.read_bytes()).hexdigest() != PRE_READY_SHA:
        raise ValueError('immutable independently sealed preflight readiness required')
    ready = json.loads(ready_path.read_bytes())
    helper_path = G / 'review_preflight_readiness.py'
    if hashlib.sha256(helper_path.read_bytes()).hexdigest() != ready['artifacts'][str(helper_path)]['sha256']:
        raise ValueError('review helper source changed before import')
    spec = importlib.util.spec_from_file_location('_dual_training_readiness_bindings', helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    pin, read, check, refs = helper.pin, helper.read, helper.check, helper.references
    read(ready_path, PRE_READY_SHA)
    check('clean-source-and-preflight-readiness64-checks', ready['passed'] is True
          and ready['findings'] == [] and ready['phase'] == 'preflight' and ready['dimension'] == 384
          and ready['run_root'] == str(RUN) and len(ready['checks']) == 64
          and ready['actual_input_count'] == 1260 and ready['extension_count'] == 5
          and ready['training_execution_readiness_granted'] is False,
          'Passed preflight readiness permits no training by itself; separate actual audit is required.')
    for path, record in ready['artifacts'].items():
        if pin(path, record['sha256']) != record: raise ValueError('preflight readiness body size differs')
    manifest = read(RUN / 'training-manifest.json', '40a4be04a2f44b6abe4ddb85dbe38373caf8a0fe55d11d62f2896fb817f0b0e1')
    plan = read(RUN / 'training-plan.json', 'c33925e386d0fefca399e64474041c46b2098d9a6f3ff7e6f4086173e9110d3a')
    check('same-exact1260-input5-extension-operational-map', len(manifest['inputs']) == 1260
          and len(manifest['extensions']) == 5 and manifest['inputs'] == plan['input_sha256']
          and all(helper.A[path]['sha256'] == wanted for path, wanted in manifest['inputs'].items()),
          'No source/plan/profile/bank/parent change since the successful preflight; every operational input freshly rehashed.')
    audit = read(args.completed_preflight_review, args.completed_preflight_review_sha256)
    check('explicit-completed-clean-independent-actual-preflight-audit',
          audit['schema'] == 'dual-bank-replay-actual-preflight-independent-review/v1'
          and audit['passed'] is True and audit['findings'] == []
          and all(item['passed'] is True for item in audit['checks'])
          and audit['all_semantic_runtime_proof_qualification_false'] is True
          and audit['dual_preparation']['qualified'] is False
          and audit['dual_preparation']['admitted'] is False
          and audit['dual_preparation']['proof_authority'] is False
          and audit['schema_validator']['compiler_execution'] is False
          and audit['schema_validator']['Lean_execution'] is False,
          'Root completion precedes this review; a separately supplied immutable independent actual-result audit, rather than a source-only declaration, is required.')
    for path, record in audit['artifacts'].items():
        if pin(path, record['sha256']) != record: raise ValueError('independent actual audit artifact size differs')
    attempt = RUN / 'preflight-384-r1'
    summary_path = attempt / 'results/summary.json'
    summary = read(summary_path)
    check('actual-preflight-summary-present-in-independent-audit',
          audit['artifacts'].get(str(summary_path)) == helper.A[str(summary_path)]
          and summary['schema'] == 'dual-bank-replay-result/v1' and summary['complete'] is True
          and summary['dimension'] == 384 and summary['phase'] == 'preflight'
          and summary['fits'] == summary['optimizer_steps'] == 0 and summary['runs'] == []
          and summary['training_executed'] is False and summary['model_executed'] is True,
          'Actual complete numerical source/cache/greedy preflight exists; no fit or checkpoint selection occurred.')
    for path, wanted in refs(summary).items():
        record = pin(path, wanted)
        if audit['artifacts'].get(path) != record:
            raise ValueError('actual preflight physical reference not bound in independent audit: ' + path)
    metrics = summary['initial_bank_source_scalar_metrics']
    check('full-two-bank-parent-readouts-match-measured-baseline', set(metrics) == {'control', 'balanced'}
          and all(set(metrics[role]) == {'actor', 'action', 'object', 'modality'} for role in metrics)
          and all(value['total'] == 180 for role in metrics.values() for value in role.values())
          and all(value['correct'] == 180 for value in metrics['balanced'].values())
          and metrics['control']['action']['correct'] == 179
          and all(metrics['control'][field]['correct'] == 180 for field in ('actor', 'object', 'modality'))
          and summary['initial_balanced_bank_all_four_scalars_correct'] is True,
          'Balanced720/720 and control719/720 genuine source sites remain; continuation is confidence/retention rather than claimed new-bank classification repair.')
    fidelity = read(summary['balanced48_posthoc_formula_fidelity']['path'], summary['balanced48_posthoc_formula_fidelity']['sha256'])
    fm = fidelity['metrics']
    scores = read(summary['balanced48_posthoc_scalar_scores']['path'], summary['balanced48_posthoc_scalar_scores']['sha256'])
    check('actual-new48-parent-greedy-full-formula-and-scalar-denominators',
          fidelity['complete_evaluation'] is True and fm['rows'] == fm['ordered_exact'] == fm['eos_count'] == 48
          and fm['expected_rules'] == fm['generated_rules'] == fm['valid_generated_rules'] == 180
          and all(fm[key] == 0 for key in ('invalid_rule_count', 'whole_rules_missing', 'whole_rules_extra',
                                         'duplicate_rules', 'order_mismatch_rows', 'prediction_missing_rows'))
          and set(fidelity['by_facet']) == {'actor', 'action', 'object', 'modality', 'conditions', 'exceptions', 'temporal'}
          and all(value['correct'] == value['total'] == 180 for value in fidelity['by_facet'].values())
          and scores['complete'] is True and scores['scored_sites'] == 720
          and scores['unscored_sites'] == scores['unvisited_reference_sites'] == [],
          'Same-pass actual generated formulas and all7 authored facets complete; empty qualifier labels do not show nonempty qualifier coverage or Lake admission.')
    cache = read(summary['parent_dual_cache_receipt']['path'], summary['parent_dual_cache_receipt']['sha256'])
    check('actual-dual-cache-two-authentic-shared-model-handles', cache['schema'] == 'dual-authored-wording-modality-cache/v1'
          and cache['bank_count'] == 2 and set(cache['authentic_caches_by_role']) == {'control', 'balanced'}
          and cache['max_optimizer_steps'] == 170 and cache['max_local_uses_per_bank'] == 85
          and cache['cached_tensor_bytes'] == 4982400 and cache['authentic_cache_handles_retained'] is True
          and cache['model_copied'] is cache['tensors_copied'] is cache['prepared_caches_mutated'] is False,
          'Both authentic2,491,200-byte caches allocated with one parent model; ownership and source order were independently audited, not inferred from a fake360-row cache.')
    dispatch = [read(ref['path'], ref['sha256']) for ref in summary['parent_dual_detached_losses']]
    check('both-detached-full32-bank-dispatches-executed-without-gradient', len(dispatch) == 2
          and all(item['global_committed_step'] == global_step
                  and item['bank_role'] == role and item['bank_local_committed_step'] == 0
                  and item['authentic_receipt']['committed_step'] == 0
                  and item['authentic_receipt']['gradient_enabled'] is False
                  and item['authentic_receipt']['full_vocabulary_size'] == 32
                  and item['authentic_receipt']['batch_size'] == 6 and item['source_head_forward_calls'] == 1
                  and item['local_receipt_relabelled'] is False
                  for global_step, (role, item) in enumerate(zip(('control', 'balanced'), dispatch, strict=True))),
          'Actual global0/control/local0 and global1/balanced/local0 full32 detached dispatch receipts retained; no numerical backward/optimizer convergence claim.')
    parity = read(summary['initial_parity']['path'], summary['initial_parity']['sha256'])
    check('actual-parent-parity-assertion-with-explicit-body-limitation', parity['predictions_equal'] is True
          and parity['rows'] == 48 and parity['model_tensor_sha256'] == plan['training_profile']['parent_tensor_sha256'],
          'Executed exact archived validation equality assertion only; replay token body was not separately retained and cannot be independently compared here.')
    outer = read(RUN / 'preflight-384-r1-guardian-exit.json')
    child = read(attempt / 'child-exit.json')
    resources = read(attempt / 'resources-final.json')
    for path in (RUN / 'preflight-384-r1-guardian-exit.json', attempt / 'child-exit.json', attempt / 'resources-final.json'):
        if audit['artifacts'].get(str(path)) != helper.A[str(path)]:
            raise ValueError('terminal receipt absent from independent audit')
    post = resources['lease_watchdog']['post_release_observation']
    check('actual-clean-owned-terminal-and-durable-release', outer['returncode'] == child['returncode'] == 0
          and child['leader_reaped'] is True and resources['status'] == 'released'
          and resources['cleanup_error'] is None and resources['record']['artifacts_durable_asserted'] is True
          and resources['record']['last_usage']['group_rss']['live_processes'] == 0
          and resources['record']['attempt_exceeded_reservation'] is False
          and post['healthy'] is True and post['expected'] == 'absent' and post['lease_present'] is False
          and post['configuration_matches'] is True and resources['lease_watchdog']['shared_state_mutated_by_observer'] is False,
          'Root-owned child exited/reaped, group0, durable finalized reservation and own lease absence independently checked; no foreign ledger inspection/reset by this reviewer.')
    profile = plan['training_profile']
    check('one170step-fit-resource-limits-and-original-selection', profile['fits'] == 1
          and profile['optimizer_steps_per_fit'] == 170 and profile['source_auxiliary_weight'] == .05
          and profile['source_updates_per_bank'] == 85 and profile['source_presentations_per_bank'] == 510
          and profile['cpu_slots'] == 1 and profile['memory_mb'] == 1536 and profile['storage_bytes'] == 400000000
          and profile['max_seconds_total'] == 900 and profile['max_seconds_per_fit'] == 180
          and profile['max_fit_memory_bytes'] == 1073741824 and profile['max_seconds_per_original_panel'] == 30
          and len(profile['original_panel_names']) == 9 and profile['selection_unchanged'] is True,
          'One fresh-optimizer replay, all18 original panels, full32 auxiliary and unchanged original selection remain; guardian1000s inside fresh locked145GB admission.')
    check('no-semantic-or-proof-admission', all(profile[key] is False for key in
          ('qualified', 'admitted', 'proof_authority', 'source_semantics_verified', 'formalized', 'encoder_executed', 'downloads_performed'))
          and manifest['actual_semantic_admission'] is False and summary['qualification_granted'] is False,
          'Private authored numerical continuation only; current canonical compiler/logic-family/Lean/proof validation remains separate.')
    pin(Path(__file__).resolve())
    for path, record in list(helper.A.items()):
        if pin(path, record['sha256']) != record: raise ValueError('artifact changed after training review')
    result = dict(schema='dual-bank-independent-training-execution-readiness/v1', passed=True, findings=[],
                  phase='training', dimension=384, run_root=str(RUN), checks=helper.CHECKS, artifacts=helper.A,
                  execution_readiness_granted=True, scope='One owned bounded native384 dual-bank authored numerical replay only; original selection and every declared panel retained.',
                  completed_preflight_attempt=str(attempt),
                  independent_actual_preflight_review=dict(path=str(args.completed_preflight_review.resolve()),
                                                          sha256=args.completed_preflight_review_sha256),
                  unchanged_current1260_inputs=True, unchanged_five_extensions=True,
                  fits_authorized=1, optimizer_steps_per_fit=170, auxiliary_presentations=1020,
                  resource_policy=dict(cpu_slots=1, child_slots=1, memory_mib=1536, storage_bytes=400000000,
                                       guardian_seconds=1000, driver_seconds=900, per_fit_seconds=180,
                                       cap_bytes=145000000000, fresh_locked_admission_still_required=True),
                  measured_parent_scope='Balanced720/720 source sites and balanced48/48 actual formulas already correct; control action179/180. Confidence/retention diagnostic, not new-bank classification repair.',
                  parent_parity_scope='Saved runtime assertion only; replay token body not independently retained.',
                  semantic_train_eligible=False, fresh_semantic_holdout=False,
                  models_imported=False, models_executed=False, encoder_executed=False,
                  numerical_gradient_tests_executed_by_review=False, training_executed=False,
                  guardian_executed=False, reservation_acquired=False, live_shared_state_read=False,
                  shared_state_written=False, canonical_source_or_Git_state_modified=False,
                  qualified=False, admitted=False, proof_authority=False, source_semantics_verified=False,
                  formalized=False, Lake_executed=False, Constitution_formalized=False, checkpoint_promoted=False)
    target = G / 'training-execution-readiness.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                         bytes=target.stat().st_size, checks=len(helper.CHECKS), bindings=len(helper.A), passed=True)))


if __name__ == '__main__': main()
