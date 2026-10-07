"""Independent final metadata/source readiness for one owned384 preflight.

Hashes actual1260 inputs and5 deployed extensions, verifies strict pure driver
profiles, and rebinds the independent source review. Imports only the standalone
stdlib driver declaration; no numerical owner, model, tensor, cache, encoder,
scheduler or reservation is executed. Fresh locked admission remains root-owned.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
G = R / 'guardian'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
OLD_RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007'
A = {}
CHECKS = []


def pin(path, wanted=None):
    path = Path(path).resolve()
    before = path.stat(); digest = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            digest.update(data); size += len(data)
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or identity(before) != identity(after) or size != before.st_size:
        raise ValueError('artifact changed during streaming: ' + str(path))
    value = dict(sha256=digest.hexdigest(), bytes=size)
    if wanted is not None and value['sha256'] != wanted:
        raise ValueError('reviewed artifact SHA differs: ' + str(path))
    if str(path) in A and A[str(path)] != value: raise ValueError('conflicting artifact binding')
    A[str(path)] = value
    return value


def read(path, wanted=None):
    pin(path, wanted)
    return json.loads(Path(path).read_bytes())


def check(name, condition, detail):
    if not condition: raise ValueError(name)
    CHECKS.append(dict(id=name, passed=True, detail=detail))


def references(value):
    refs = {}
    def walk(node):
        if type(node) is dict:
            if type(node.get('path')) is str and type(node.get('sha256')) is str:
                path = str(Path(node['path']).resolve())
                if path in refs and refs[path] != node['sha256']: raise ValueError('conflicting reference')
                refs[path] = node['sha256']
            for item in node.values(): walk(item)
        elif type(node) is list:
            for item in node: walk(item)
    walk(value)
    return refs


def main():
    manifest = read(RUN / 'training-manifest.json', '40a4be04a2f44b6abe4ddb85dbe38373caf8a0fe55d11d62f2896fb817f0b0e1')
    plan = read(RUN / 'training-plan.json', 'c33925e386d0fefca399e64474041c46b2098d9a6f3ff7e6f4086173e9110d3a')
    seed = read(G / 'input-closure-seed-r2.json', '07ada819b4ac8c2f09f477ee335c1c404c33afa3aa98fae1121d52af908f10c6')
    source_review = read(R / 'independent-review/runtime-source-independent-review-r2.json',
                         'cb272c86b4e8f1f973ed89a798ecfec090434f90b4f1e3e8eb9e075875c389c7')
    source_freeze = read(R / 'runtime/source-freeze.json',
                         'b0665e581bbd9edf011a41069bc613afaed0a7eb0e07cda0f92ee2ccc66af97d')
    protocol = read(R / 'predeclared-protocol.json',
                    '75d4d01893578265c2be3bcc53ed96ca661fdb03781704a074b9df56e6bf30d2')
    phase_profiles = read(R / 'runtime/phase-profiles.json',
                          '9942465438acc88f9411265d8fa1ed9d1a7101ecf7851720eeb147dbbc8a320a')
    staging = read(G / 'actual-phase-input-preparation-r2.json')
    proposal = read(G / 'guardian-proposal.json')
    guardian_freeze = read(G / 'source-results-freeze-r2.json',
                           '71df58f5258e1e708c538487bf599e7db94828d655716c35d4735a67d17d6d47')
    for path, record in source_review['artifacts'].items():
        check('source-review-binding:' + path, pin(path, record['sha256']) == record, 'Exact reviewed size and SHA freshly rechecked.')
    for path, record in source_freeze['files'].items():
        check('runtime-freeze-binding:' + path, pin(path, record['sha256']) == record, 'Actual r2 authored source/profile/test body bound.')
    for path, record in guardian_freeze['artifacts'].items():
        check('guardian-proposal-binding:' + path, pin(path, record['sha256']) == record, 'Read-only guardian proposal source and metadata body unchanged.')
    check('independent-source-review302-checks27-contract-tests', source_review['passed'] is True
          and source_review['findings'] == [] and source_review['check_count'] == len(source_review['checks']) == 302
          and len(source_review['artifacts']) == 22
          and all(item['passed'] is True for item in source_review['checks'])
          and source_review['independent_author_interface_tests_passed'] == 17
          and source_review['independently_authored_descriptor_mutation_tests_passed'] == 10
          and source_review['models_or_encoders_executed_by_review'] is False
          and source_review['numerical_gradient_or_autograd_tests_executed'] is False
          and source_review['execution_readiness_granted'] is False,
          'Reuse independent source/mutation review; synthetic flags do not claim numerical gradients or prior admission.')
    for path, wanted in manifest['inputs'].items(): pin(path, wanted)
    for relative, wanted in manifest['extensions'].items(): pin(RUN / 'experiment-source' / relative, wanted)
    check('actual1260-map-is-exact1235-seed-plus25-frozen-source-pins',
          manifest['schema'] == 'dual-bank-replay-manifest/v1'
          and plan['schema'] == 'dual-bank-replay-plan/v1'
          and len(manifest['inputs']) == 1260 and len(seed['input_sha256']) == 1235
          and all(manifest['inputs'].get(path) == wanted for path, wanted in seed['input_sha256'].items())
          and manifest['inputs'] == plan['input_sha256'] and len(manifest['extensions']) == 5
          and manifest['plan_sha256'] == A[str(RUN / 'training-plan.json')]['sha256'],
          'Full authenticated numerical/archival input map and operative plan binding freshly hashed.')
    expected_additions = dict(source_freeze['files'])
    for path in (R / 'runtime/source-freeze.json', R / 'runtime/README.md',
                 G / 'guardian-proposal.json', G / 'input-closure-seed-r2.json',
                 G / 'phase-resource-plan.json', G / 'source-results-freeze-r2.json'):
        expected_additions[str(path)] = pin(path)
    for name in ('run_guardian.py', 'run_reserved.py', 'adopt_shared_scheduler.py',
                 'lazy_scheduler_adoption.py', 'owned_lease_watchdog.py'):
        expected_additions[str(RUN / name)] = pin(RUN / name)
    for relative in manifest['extensions']:
        expected_additions[str(RUN / 'experiment-source' / relative)] = pin(RUN / 'experiment-source' / relative)
    added = {path: wanted for path, wanted in manifest['inputs'].items() if path not in seed['input_sha256']}
    check('exact25-added-input-inventory-and-physical-source-mirrors', len(added) == len(expected_additions) == 25
          and added == {path: record['sha256'] for path, record in expected_additions.items()}
          and all(manifest['extensions'][relative] == source_freeze['files'][
              str(R / 'runtime/experiment-source' / relative)]['sha256'] for relative in manifest['extensions']),
          'Only explicit r2 five extensions, source/profile receipts and owned guardian copies added; no hidden producer substitution.')
    check('root-staging-receipt-matches-actual-files', staging['passed'] is True
          and staging['findings'] == [] and staging['model_executed'] is False
          and staging['seed_pins_preserved'] is True and staging['inputs'] == 1260
          and staging['extensions'] == manifest['extensions']
          and all(pin(path, record['sha256']) == record for path, record in staging['files'].items()),
          'Root staging receipt is independently rechecked against actual files; it alone grants no admission.')
    check('protocol-physical-refs-all-in-actual-map', protocol['schema'] == 'dual-bank-replay-comparison-protocol/v1'
          and manifest['comparison_protocol'] == str(R / 'predeclared-protocol.json')
          and all(manifest['inputs'].get(path) == wanted for path, wanted in references(protocol).items())
          and manifest['inputs'][str(R / 'predeclared-protocol.json')] == '75d4d01893578265c2be3bcc53ed96ca661fdb03781704a074b9df56e6bf30d2',
          'Predeclared parent/archive/helper/schedule/candidate refs are physical immutable inputs; archived references are not fresh control runs.')
    parent = read(manifest['parent_summary'], manifest['inputs'][manifest['parent_summary']])
    parent_refs = references(parent)
    producer = str(W / 'external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006/preparation-r1/results/train-source384-artifacts/training-source-texts.txt')
    check('all-parent-summary-and-deeper-producer-refs-bound', len(parent_refs) == 32
          and all(manifest['inputs'].get(path) == wanted for path, wanted in parent_refs.items())
          and manifest['inputs'][producer] == 'd1e3e1d05913ebaaaeb3991632b5c17b60390c25ceb771db0773e97f0185f0b9'
          and seed['all1185_predecessor_pins_unchanged'] is True,
          'Every32 selected-parent physical refs plus deeper native-producer source-text ref operationally present; prior missing28-report failure cannot recur on this map.')
    check('completed-exact-E384-parent', parent['dimension'] == 384 and parent['arm'] == 'normative-wording-ce'
          and parent['budget_completed'] is True
          and parent['states']['selected']['tensor_sha256'] == protocol['parent']['tensor_sha256']
          == '0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594'
          and parent['states']['selected']['path'] == protocol['parent']['path']
          and parent['states']['selected']['sha256'] == protocol['parent']['sha256'],
          'No replacement checkpoint or optimizer resume; exact selected numerical parent is retained.')
    old_manifest = read(OLD_RUN / 'training-manifest.json',
                        '3dbbc5490293010cf8e045d7a7062ddb3d00308435ddcdd1e63c54ffceafdf57')
    fields = ('initialization_extension_root', 'initialization_manifest', 'initialization_plan',
              'parent_summary', 'scalar_observer_source', 'source_inventories', 'original90_rules',
              'balanced_source_inputs', 'candidate_builder_relative')
    check('initialization-and-native-source-owners-unchanged', all(manifest[k] == old_manifest[k] for k in fields)
          and all(manifest['inputs'].get(path) == wanted for path, wanted in old_manifest['inputs'].items())
          and manifest['runtime_source_freeze_sha256'] == A[str(R / 'runtime/source-freeze.json')]['sha256'],
          'Exact frozen E/S numerical/schema owners and distinct native384 source caches retained; no HACC or canonical compiler switch.')
    driver_path = RUN / 'experiment-source/scripts/ops/autoencoder/benchmark_dual_bank_replay.py'
    imported_before = set(sys.modules)
    spec = importlib.util.spec_from_file_location('_independent_dual_readiness_driver', driver_path)
    driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
    check('pure-driver-import-no-numerical-modules', not any(name.startswith(('torch', 'ipfs_datasets_py', 'transformers'))
          for name in set(sys.modules) - imported_before), 'Standalone driver declarations import only stdlib; execute/main not invoked.')
    check('strict-real-driver-profile-validation', driver.validate_plan(plan, manifest, 'preflight') == driver.PREFLIGHT
          and driver.validate_plan(plan, manifest, 'training') == driver.TRAINING
          and phase_profiles['preflight_profile'] == plan['preflight_profile']
          and phase_profiles['training_profile'] == plan['training_profile'],
          'Actual deployed pure validator checks complete types/keys/values for both profiles without entering numerical phases.')
    pre = plan['preflight_profile']; train = plan['training_profile']
    check('preflight384-zero-fit-native-cache-and-greedy-scope', pre['dimension'] == 384
          and pre['fits'] == pre['optimizer_steps'] == 0 and pre['training_executed'] is False
          and pre['source_bank_roles'] == ['control', 'balanced'] and pre['source_bank_rows'] == 180
          and pre['max_seconds_total'] == 800 and pre['storage_bytes'] == 100000000
          and pre['memory_mb'] == 1536 and pre['cpu_slots'] == 1,
          'One owned source/cache dispatch preflight, full180 banks and actual new48 parent greedy; no fit or checkpoint selection.')
    check('future-training-one-fit-original-stream-budget-and-replay', train['fits'] == 1
          and train['optimizer_steps_per_fit'] == 170 and train['row_presentations_per_fit'] == train['count_presentations_per_fit'] == 1220
          and train['target_token_presentations_per_fit'] == 112920 and train['source_value_presentations_per_fit'] == 12800
          and train['original_used113_presentations_per_fit'] == train['new_auxiliary_presentations_per_fit'] == 1020
          and train['source_updates_per_bank'] == 85 and train['source_presentations_per_bank'] == 510
          and train['first_bank'] == 'control' and train['bank_local_ordinal_policy'] == 'floor(global_committed_step/2)'
          and train['source_auxiliary_weight'] == .05 and train['seed'] == 1729,
          'Declared one-fit later lane keeps original streams and same1020 six-clause objective budget; this receipt does not permit fitting.')
    check('original-selection-all9-panels-output-and-gates-retained', len(pre['original_panel_names']) == len(train['original_panel_names']) == 9
          and pre['original_panel_names'] == protocol['postfit_panels']
          and pre['native_context_tokens'] == pre['output_tokens'] == train['native_context_tokens'] == train['output_tokens'] == 512
          and pre['full_vocabulary_size'] == train['full_vocabulary_size'] == 32
          and pre['temperature'] == train['temperature'] == 0 and pre['selection_unchanged'] is True
          and train['reference_rows_unavailable_to_selection'] == ['balanced48', 'sealed60', 'exposed-v3'],
          'All18 later original panels and explicit original selection remain; authored new/v3/sealed refs cannot select weights or raise context.')
    guardian_source = (RUN / 'run_reserved.py').read_text()
    old_guardian = (OLD_RUN / 'run_reserved.py').read_text()
    check('owned-guardian-only-two-runner-basename-replacements', guardian_source == old_guardian.replace(
          'benchmark_balanced_wording_continuation.py', 'benchmark_dual_bank_replay.py').replace(
          'evaluate_balanced_wording_continuation.py', 'evaluate_dual_bank_replay.py')
          and all((RUN / name).read_bytes() == (OLD_RUN / name).read_bytes()
                  for name in ('run_guardian.py', 'adopt_shared_scheduler.py', 'lazy_scheduler_adoption.py', 'owned_lease_watchdog.py')),
          'Birth/group cleanup, exact scheduler adoption, watchdog, streamed seal validation and durable finalization unchanged.')
    check('guardian-preflight-resource-and-offline-boundaries', "'preflight': ('benchmark_dual_bank_replay.py',100_000_000,1536,900)" in guardian_source
          and 'cpu_slots=1, child_process_slots=1' in guardian_source and "CUDA_VISIBLE_DEVICES=''" in guardian_source
          and "HF_HUB_OFFLINE='1'" in guardian_source and "IPFS_DATASETS_LEGAL_IR_METRIC_DISK_CACHE='0'" in guardian_source
          and proposal['cap_bytes'] == 145000000000 and proposal['reservation_acquired'] is False,
          'Fresh locked145GB accounting still required; bounded CPU/offline child with no metric disk cache or external prover activation.')
    history = read(G / 'staged-not-executed-r1.json')
    check('first-staging-preserved-and-not-an-executed-attempt', history['models_executed'] is False
          and history['newattempts_created'] is False and history['reservations_acquired'] is False
          and Path(history['history']).is_dir() and source_freeze['revision'] == 'source-r2'
          and source_review['resolved_prior_finding']['id'] == 'descriptor_metadata_not_closed',
          'Rejected source r1 and metadata validation bug are archived without numerical execution; current exact closed descriptor fix independently reviewed.')
    check('semantic-proof-and-native-admission-remain-false', all(pre[k] is False and train[k] is False
          for k in ('qualified', 'admitted', 'proof_authority', 'source_semantics_verified', 'formalized', 'encoder_executed', 'downloads_performed'))
          and manifest['actual_semantic_admission'] is False
          and protocol['current_canonical_compiler_executed'] is False and protocol['Lake_executed'] is False
          and protocol['Constitution_formalized'] is False and protocol['checkpoint_promoted'] is False,
          'Historical _rule schema validation does not execute canonical compiler or Lean; fixture reconstruction preflight grants no admission.')
    pin(Path(__file__).resolve())
    for path, record in list(A.items()):
        if pin(path, record['sha256']) != record: raise ValueError('artifact changed after readiness inspection')
    result = dict(schema='dual-bank-independent-preflight-execution-readiness/v1', passed=True, findings=[],
                  phase='preflight', dimension=384, run_root=str(RUN), checks=CHECKS, artifacts=A,
                  execution_readiness_granted=True, training_execution_readiness_granted=False,
                  scope='One explicitly owned bounded native384 authored source/cache/greedy preflight only. Training requires independently audited successful actual preflight and separate readiness.',
                  source_review_checks_reused=302, pure_contract_tests_reused=27,
                  strict_profile_validator_executed=True, actual_input_count=1260, extension_count=5,
                  seed1235_all_pins_preserved=True, original1185_all_pins_preserved=True,
                  resource_policy=dict(cpu_slots=1, child_slots=1, memory_mib=1536,
                                       storage_bytes=100000000, guardian_seconds=900,
                                       driver_seconds=800, cap_bytes=145000000000,
                                       fresh_locked_admission_still_required=True),
                  models_imported=False, numerical_owner_imported=False, tensor_libraries_imported=False,
                  models_executed=False, encoder_executed=False, training_executed=False,
                  guardian_executed=False, reservation_acquired=False, live_shared_state_read_by_review=False,
                  shared_state_written=False, canonical_source_or_Git_state_modified=False,
                  fresh_holdout=False, qualified=False, admitted=False, proof_authority=False,
                  source_semantics_verified=False, formalized=False, Lake_executed=False,
                  Constitution_formalized=False, checkpoint_promoted=False)
    target = G / 'preflight-execution-readiness.json'
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                         bytes=target.stat().st_size, checks=len(CHECKS), bindings=len(A), passed=True)))


if __name__ == '__main__': main()
