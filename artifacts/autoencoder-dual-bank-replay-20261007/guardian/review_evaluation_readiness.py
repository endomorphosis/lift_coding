"""Independent readiness for the frozen eight-panel postfit observer.

Invoke after root's explicit training completion and immutable actual-training
audit. Reconstruct the staging closure independently, without model execution,
and require every original panel and both endpoint files. No live resource
ledger/scheduler access or numerical owner import occurs in this review.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
G = R / 'guardian'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
TRAIN = RUN / 'training-384-r1'
EVALUATOR = 'scripts/ops/autoencoder/evaluate_dual_bank_replay.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed-training-review', type=Path, required=True)
    parser.add_argument('--completed-training-review-sha256', required=True)
    args = parser.parse_args()
    ready_path = G / 'training-execution-readiness.json'
    if hashlib.sha256(ready_path.read_bytes()).hexdigest() != '1546f07dd038f8a581e29625f9fdb01e1a1d83d788d7f076210b2db1a1d28805':
        raise ValueError('unchanged independently sealed training readiness required')
    ready = json.loads(ready_path.read_bytes())
    helper_path = G / 'review_preflight_readiness.py'
    if hashlib.sha256(helper_path.read_bytes()).hexdigest() != ready['artifacts'][str(helper_path)]['sha256']:
        raise ValueError('review helper source changed before import')
    spec = importlib.util.spec_from_file_location('_dual_evaluation_readiness_bindings', helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    pin, read, check, refs = helper.pin, helper.read, helper.check, helper.references
    read(ready_path)
    for path, record in ready['artifacts'].items():
        if pin(path, record['sha256']) != record: raise ValueError('earlier readiness artifact size differs')
    original = read(RUN / 'training-manifest.json', '40a4be04a2f44b6abe4ddb85dbe38373caf8a0fe55d11d62f2896fb817f0b0e1')
    original_plan = read(RUN / 'training-plan.json', 'c33925e386d0fefca399e64474041c46b2098d9a6f3ff7e6f4086173e9110d3a')
    manifest = read(RUN / 'evaluation-manifest.json', 'bdb3a58baa70dfcdf462a19f0db7d0789a1e70ff276546b6e29b336f9e7f85ba')
    plan = read(RUN / 'evaluation-plan.json', '07c4c859779608e20d3b89cd4e71cee39698e618bb267391b434cf7adb9652d9')
    check('actual1325-input6-extension-deployed-seal', manifest['schema'] == 'dual-bank-replay-postfit-evaluation-manifest/v1'
          and len(manifest['inputs']) == 1325 and len(manifest['extensions']) == 6
          and manifest['inputs'] == plan['input_sha256']
          and manifest['plan_sha256'] == helper.A[str(RUN / 'evaluation-plan.json')]['sha256']
          and all(manifest['inputs'].get(path) == wanted for path, wanted in original['inputs'].items())
          and manifest['current_training_manifest_sha256'] == helper.A[str(RUN / 'training-manifest.json')]['sha256'],
          'All1260 training pins preserved and65 completed-output/evaluation metadata pins added; no source/parent substitution.')
    for path, wanted in manifest['inputs'].items(): pin(path, wanted)
    for relative, wanted in manifest['extensions'].items(): pin(RUN / 'experiment-source' / relative, wanted)
    source_review = read(R / 'independent-review/evaluation-source-independent-review.json',
                         '324a82090b861e81e6e7798168062f07bb822bf7b7184620b750c06b661bd927')
    source_freeze = read(R / 'evaluation/source-freeze.json',
                         '294fd6d4b33564265d151d802d907caaa510da8b1d0b05f04e03fffcc0c1c601')
    for group in (source_review['artifacts'], source_freeze['artifacts']):
        for path, record in group.items():
            if pin(path, record['sha256']) != record: raise ValueError('frozen evaluator source evidence differs')
    check('independent-frozen-evaluator25-checks16-pure-tests', source_review['passed'] is True
          and source_review['findings'] == [] and source_review['check_count'] == len(source_review['checks']) == 25
          and source_review['independent_pure_tests_passed'] == 16
          and all(item['passed'] is True for item in source_review['checks'])
          and source_review['models_or_encoders_executed_by_review'] is False
          and source_review['numerical_owner_functions_executed_by_review'] is False
          and source_review['execution_readiness_granted'] is False
          and source_freeze['tests'] == 16 and source_freeze['passed'] is True,
          'Reuse exact source/mutation contract review; actual saved eight-panel result audit remains required after execution.')
    evaluator_source = R / 'evaluation/source/evaluate_dual_bank_replay.py'
    evaluator_deployed = RUN / 'experiment-source' / EVALUATOR
    check('exact-evaluator-copy-and-five-runtime-extensions-unchanged',
          helper.A[str(evaluator_source)]['sha256'] == helper.A[str(evaluator_deployed)]['sha256']
          == manifest['extensions'][EVALUATOR] == 'bd2862167fa61ba4451b79436e79609e5ff6d8280151256aab459ba9df1837f5'
          and {relative: sha for relative, sha in manifest['extensions'].items() if relative != EVALUATOR} == original['extensions'],
          'Only exact sixth evaluator source added; dual adapter/driver/native source owners remain byte-identical.')
    imported_before = set(sys.modules)
    spec = importlib.util.spec_from_file_location('_dual_independent_evaluation_profile', evaluator_deployed)
    evaluator = importlib.util.module_from_spec(spec); spec.loader.exec_module(evaluator)
    evaluator.validate_plan(plan, manifest)
    check('actual-pure-profile-validator-and-no-numerical-imports',
          not any(name.startswith(('torch', 'ipfs_datasets_py', 'transformers')) for name in set(sys.modules) - imported_before)
          and all(type(plan[k]) is type(v) and plan[k] == v for k, v in evaluator.PROFILE.items())
          and set(plan) == set(evaluator.PROFILE) | {'input_sha256'},
          'Standalone stdlib evaluator declarations and actual strict validator checked; execute/main not invoked.')
    staging = read(R / 'evaluation/actual-input-preparation.json')
    check('root-completed-only-metadata-staging-receipt-rechecked', staging['passed'] is True
          and staging['findings'] == [] and staging['inputs'] == 1325
          and staging['extensions'] == manifest['extensions'] and staging['models_executed'] is False
          and staging['reservation_acquired'] is False
          and all(pin(path, record['sha256']) == record for path, record in staging['files'].items()),
          'Builder receipt agrees with actual sealed files; source is independently inspected and no numerical launch is inferred from staging.')
    summary_path = TRAIN / 'results/summary.json'
    summary = read(summary_path, manifest['inputs'][str(summary_path)])
    expected = dict(original['inputs']); collected = set()
    def add(path, wanted=None):
        path = Path(path).resolve(); record = pin(path, wanted)
        if str(path) in expected and expected[str(path)] != record['sha256']: raise ValueError('conflicting closure pin')
        expected[str(path)] = record['sha256']
        return path
    def collect(value):
        for path, wanted in refs(value).items():
            path = add(path, wanted)
            if path.suffix == '.json' and path not in collected:
                if len(collected) >= 256: raise ValueError('bounded saved numerical JSON reference closure exceeded')
                collected.add(path); collect(json.loads(path.read_bytes()))
    add(summary_path); collect(summary)
    owned_files = [path for path in sorted(TRAIN.rglob('*')) if path.is_file()]
    if any(path.is_symlink() for path in owned_files): raise ValueError('owned TRAIN evidence cannot contain symlink aliases')
    for path in owned_files: add(path)
    for path in (RUN / 'training-384-r1-guardian-exit.json', RUN / 'training-manifest.json',
                 RUN / 'training-plan.json', evaluator_source,
                 R / 'independent-review/evaluation-source-independent-review.json',
                 R / 'evaluation/source-freeze.json', evaluator_deployed,
                 W / 'external/ipfs_datasets/workspace/test-logs/decoder-fresh-normative-style-r2-20261004/preparation-r1/results/references.json',
                 R / 'evaluation/prepare_actual_evaluation.py'):
        add(path)
    check('independently-reconstructed-completed-output-closure-exact', expected == manifest['inputs']
          and manifest['training_summary'] == str(summary_path)
          and manifest['training_terminal'] == {'child_exit': str(TRAIN / 'child-exit.json'),
                                               'resources_final': str(TRAIN / 'resources-final.json')},
          'Reconstruct full closure independently from all owned files, recursive saved path/SHA references and immutable evaluator/v3 metadata; historical ledger locators are not treated as live dependencies.')
    audit = read(args.completed_training_review, args.completed_training_review_sha256)
    check('completed-clean-independent-actual-training-audit',
          audit['schema'] == 'dual-bank-replay-native384-training-independent-review/v1'
          and audit['passed'] is True and audit['findings'] == []
          and all(item['passed'] is True for item in audit['checks'])
          and all(audit[key] is False for key in ('qualified', 'admitted', 'proof_authority',
                                                 'source_semantics_verified', 'checkpoint_promoted',
                                                 'convergence_proven', 'fresh_semantic_holdout')),
          'Completed separately audited actual fit required; audit cleanliness concerns evidence accuracy and does not imply semantic reconstruction qualification.')
    for path, record in audit['artifacts'].items():
        if pin(path, record['sha256']) != record: raise ValueError('actual training audit body differs')
    check('actual-one-complete-replay-fit-and-audited-summary', summary['complete'] is True
          and summary['phase'] == 'training' and summary['dimension'] == 384
          and len(summary['runs']) == 1 and summary['fits'] == 1 and summary['optimizer_steps_per_fit'] == 170
          and summary['training_executed'] is True
          and audit['artifacts'].get(str(summary_path)) == helper.A[str(summary_path)],
          'One completed fresh-optimizer diagnostic fit; original streams and dual receipts are independently audited before observation.')
    run_ref = summary['runs'][0]; run = read(run_ref['path'], run_ref['sha256'])
    check('both-typed-endpoints-and18-original-panels-bound', run['arm'] == 'dual-bank-retention-ce'
          and run['dimension'] == 384 and run['budget_completed'] is True
          and run['fresh_optimizer'] is True and run['fresh_scheduler'] is True and run['exact_optimizer_resume'] is False
          and all(set(run['postfit'][role]) == set(original_plan['training_profile']['original_panel_names'])
                  for role in ('selected', 'last-attempt'))
          and all(manifest['inputs'].get(str(Path(run['states'][role]['path']).resolve())) == run['states'][role]['sha256']
                  for role in ('selected', 'last-attempt'))
          and run['original_panels_physically_evaluated_for_both_roles'] is True,
          'Both exact saved endpoint files and every9 original panel for each role are retained; tensor aliases are disclosed and never treated as independent training fits.')
    outer = read(RUN / 'training-384-r1-guardian-exit.json')
    child = read(TRAIN / 'child-exit.json')
    resources = read(TRAIN / 'resources-final.json')
    post = resources['lease_watchdog']['post_release_observation']
    check('completed-owned-training-durable-release-and-group0', outer['returncode'] == child['returncode'] == 0
          and child['leader_reaped'] is True and resources['status'] == 'released' and resources['cleanup_error'] is None
          and resources['record']['artifacts_durable_asserted'] is True
          and resources['record']['last_usage']['group_rss']['live_processes'] == 0
          and resources['record']['attempt_exceeded_reservation'] is False
          and post['healthy'] is True and post['expected'] == 'absent' and post['lease_present'] is False
          and post['configuration_matches'] is True,
          'Terminal evidence is frozen; own released resources/group0 checked without reading or changing any current foreign ledger.')
    check('eight-physical-full-family-fixture-panels-fixed-denominators', plan['arms'] == ['dual-bank-retention-ce']
          and plan['roles'] == ['selected', 'last-attempt'] and plan['cohorts'] == list(evaluator.COHORTS)
          and plan['logical_panels'] == plan['physical_panels'] == 8 and plan['samples_per_panel'] == 48
          and plan['rules_per_panel'] == 180 and plan['scalar_reference_sites_per_panel'] == 720
          and plan['same_pass_scalar_observation'] is True and plan['extra_source_head_passes'] == 0
          and plan['full_vocabulary_size'] == 32 and plan['predictions_fsynced_before_v3_reference_load'] is True,
          'Actual writer must compute all8 panels/384 paragraphs/1440 rules/5760 sites, including tensor aliases; full32 source/recurrent/combined same-pass observation and explicit v3 barrier retained.')
    check('evaluation-resource-context-temperature-and-no-training-policy', plan['cpu_slots'] == 1
          and plan['memory_mb'] == 1536 and plan['storage_bytes'] == 100000000
          and plan['max_seconds_total'] == 800 and plan['max_seconds_per_panel'] == 60
          and plan['source_context_tokens'] == plan['output_tokens'] == 512 and plan['temperature'] == 0
          and plan['bridge_names'] == [] and plan['legal_ir_evaluate_provers'] is False
          and plan['metric_disk_cache_used'] is False and plan['training_executed'] is False
          and plan['encoder_executed'] is False and plan['used_for_selection'] is False,
          'Fixed bounded CPU/offline warm source caches; no fit/encoder/prover/bridge/teacher-forced loss or context increase.')
    for key in ('comparison_protocol', 'initialization_extension_root', 'initialization_manifest',
                'initialization_plan', 'source_inventories', 'scalar_observer_source'):
        if manifest[key] != original[key]: raise ValueError('inherited owner field changed: ' + key)
    check('canonical-compiler-Lake-proof-and-semantic-authority-stay-false', manifest['historical_schema_owners_only'] is True
          and manifest['qualification_granted'] is False
          and all(plan[k] is False for k in ('qualified', 'admitted', 'proof_authority', 'formalized',
                                            'source_semantics_verified', 'checkpoint_promoted', 'convergence_proven',
                                            'lake_executed', 'native_family_validation_performed', 'fresh_holdout',
                                            'independent_semantic_holdout', 'Constitution_formalized')),
          'Frozen historical schema callback only; current canonical compiler/native-family/Lake validation and fresh semantic holdout remain separate requirements.')
    pin(Path(__file__).resolve())
    for path, record in list(helper.A.items()):
        if pin(path, record['sha256']) != record: raise ValueError('artifact changed after evaluation review')
    result = dict(schema='dual-bank-independent-evaluation-execution-readiness/v1', passed=True, findings=[],
                  phase='evaluation', dimension=None, run_root=str(RUN), checks=helper.CHECKS, artifacts=helper.A,
                  execution_readiness_granted=True,
                  scope='One explicitly owned bounded native384 eight-panel source-only postfit observer; no training/selection/semantic or proof admission.',
                  completed_training_attempt=str(TRAIN), current_inputs=1325, current_extensions=6,
                  all1260_training_inputs_preserved=True, complete_actual_reference_closure_reconstructed=True,
                  physical_panels=8, logical_panels=8, physical_paragraphs=384, reference_rules=1440,
                  reference_scalar_sites=5760, source_recurrent_combined_distributions_if_all_visited=17280,
                  independent_actual_training_review=dict(path=str(args.completed_training_review.resolve()),
                                                          sha256=args.completed_training_review_sha256),
                  resource_policy=dict(cpu_slots=1, child_slots=1, memory_mib=1536, storage_bytes=100000000,
                                       guardian_seconds=900, driver_seconds=800,
                                       cap_bytes=145000000000, fresh_locked_admission_still_required=True),
                  models_imported=False, numerical_owners_imported=False, models_executed=False,
                  encoder_executed=False, training_executed=False, guardian_executed=False,
                  reservation_acquired=False, live_shared_state_read=False, shared_state_written=False,
                  canonical_source_or_Git_state_modified=False, qualified=False, admitted=False,
                  proof_authority=False, source_semantics_verified=False, formalized=False,
                  Lake_executed=False, Constitution_formalized=False, checkpoint_promoted=False,
                  fresh_semantic_holdout=False, actual_eight_panel_saved_output_audit_pending=True)
    target = G / 'evaluation-execution-readiness.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                         bytes=target.stat().st_size, checks=len(helper.CHECKS), bindings=len(helper.A), passed=True)))


if __name__ == '__main__': main()
