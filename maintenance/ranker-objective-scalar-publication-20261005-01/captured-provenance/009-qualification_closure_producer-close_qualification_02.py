"""Close the quiet objective-scalar qualification using pinned local evidence.

This file-only producer grants no execution, planner, proof-cache, or task
completion authority. It never invokes Lean, a model, or metadata hydration.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
Q = WORKSPACE / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PRIOR = Q.with_name('ranker-source-semantics-20261005-01')
HELD = {}
EXPECTED_SOURCES = {
    'preparation/request-v3.json': '8e9038a657519b35e769e911219dbe5ad4bf92833017663f8673d5ef2613fdd3',
    'source-v2/objective_scalar_compiler.py': 'a9f4c93423c0f10e432e005ce4f8986e903706cf7ea5b493699633618519d9d9',
    'source-v2/test_typed_slice_compiler.py': 'c18c4a95bde5da2c780a91bc77e1ad5358ebd30723087e11fb0a8b96448c35c1',
    'math/ObjectiveScalarIR.lean': 'ae4d1ebec782c2395cc9d2585f40296988fc2ec10cfdab3f946258251c527d71',
    'evidence/compile-source-objective-01/objective-slices.json': '20f4cc89a1b92a9ab2eb3a53ec15298e9892c00550b5cb61891d278256fae124',
    'evidence/compile-source-objective-01/GeneratedObjectiveScalarLeaves.lean': 'c6ba9dbc3a9ed056d04d004692180efd76db4e8d379681d7c8ff2edb1da8e919',
}
MODES = {'compile-source-objective-01', 'pure-tests-objective-01', 'lean-objective-scalar-01',
         'lean-objective-generated-01', 'metadata-objective-01'}
NATIVE_MODES = {'lean-objective-scalar-01': (5, '57ac502ebc37df08ae73b7fec69280b2dcb1a2453895ab573869d826d613bd5e'),
                'lean-objective-generated-01': (9, '4bcc8424739067b6e31382f594bd0c17e7e3e800d117bd08b2e38de302177041')}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def read(path):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 32 * 1024**2, 'bounded regular input required')
        blocks, total = [], 0
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= 32 * 1024**2, 'input exceeded read cap')
            blocks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'input changed during read')
        raw = b''.join(blocks)
    finally:
        os.close(fd)
    observed = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == observed, 'previously held input changed')
    HELD[str(path)] = observed
    return raw


def pin(path):
    # Guard bodies can be larger than bounded parsed JSON inputs. Hash them
    # in a fixed-size stream; this never grants a document/body read.
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular guard required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 256 * 1024**2, 'bounded streaming guard required')
        digest, total = hashlib.sha256(), 0
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= 256 * 1024**2, 'streaming guard exceeded cap')
            digest.update(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'guard changed during streaming hash')
    finally:
        os.close(fd)
    observed = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == observed, 'previously held guard changed')
    HELD[str(path)] = observed
    return observed


def document(descriptor):
    need(type(descriptor) is dict and set(descriptor) == {'path', 'bytes', 'sha256'}, 'exact descriptor required')
    raw = read(descriptor['path'])
    need(HELD[descriptor['path']] == descriptor, 'parsed descriptor differs')
    return json.loads(raw)


def load(path):
    return json.loads(read(path))


def save(path, value):
    with path.open('xb') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def inventory():
    leaves = []
    for directory, directories, files in os.walk(Q, followlinks=False):
        need(all(not (Path(directory) / name).is_symlink() for name in directories), 'directory symlink refused')
        for name in files:
            path = Path(directory) / name
            if path != Q / 'file-only-seal-01.json':
                leaves.append(pin(path))
    return sorted(leaves, key=lambda row: os.fsencode(row['path']))


def guards(prior_review):
    result = {}
    for role, cwd in (('root', WORKSPACE), ('child', WORKSPACE / 'external/ipfs_accelerate')):
        expected = prior_review['original_checkout_guards'][role]
        head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'],
                                       env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).decode().strip()
        index = pin(expected['index']['path'])
        need(head == expected['head'] and index == expected['index'], 'original checkout changed')
        result[role] = {'head': head, 'index': index}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    plan_raw = read(args.plan)
    plan_pin = HELD[str(args.plan.absolute())]
    need(plan_pin['sha256'] == args.plan_sha256, 'externally pinned closure plan differs')
    plan = json.loads(plan_raw)
    need(set(plan) == {'schema', 'scope_root', 'source_and_artifacts_quiet', 'independent_reviews', 'metadata_build_receipt'}, 'closed closure plan schema required')
    need(plan['schema'] == 'ranker-objective-scalar-closure-plan@1' and plan['scope_root'] == str(Q) and
         plan['source_and_artifacts_quiet'] is True, 'quiet scoped closure required')
    need(not (Q / 'qualified-review-01.json').exists() and not (Q / 'file-only-seal-01.json').exists(), 'fresh closure required')
    first = inventory()
    prior_seal_pin = pin(PRIOR / 'file-only-seal-01.json')
    need(prior_seal_pin['sha256'] == '21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65', 'prior seal differs')
    prior_seal = document(prior_seal_pin)
    prior_review = document(prior_seal['review'])
    need(prior_review['status'] == 'passed' and len(prior_seal['files']) == 299, 'prior qualified census differs')
    need(all(pin(row['path']) == row for row in prior_seal['files']), 'prior qualified file changed')
    original = guards(prior_review)
    for name, expected in EXPECTED_SOURCES.items():
        need(pin(Q / name)['sha256'] == expected, 'quiet qualified source differs: ' + name)
    request = load(Q / 'preparation/request-v3.json')
    need(len(request['strict_old_inputs']) == 2108 and len(request['protected_live_sources']) == 4, 'guard census differs')
    need(all(pin(row['path']) == row for row in request['strict_old_inputs'] + request['protected_live_sources']), 'old/live input changed')
    reviews, semantic = [], None
    required_reviews = {
        'ranker-objective-scalar-independent-source-review@1': ('passed_source_only', 'outstanding_source_issues'),
        'ranker-objective-scalar-prepared-input-source-review@1': ('passed_file_only', 'outstanding_source_issues'),
        'ranker-objective-scalar-independent-semantic-native-review@1': ('passed_file_only_actual_receipt_review', 'outstanding_review_issues'),
        'ranker-objective-scalar-metadata-independent-source-review@1': ('passed_source_only', 'outstanding_source_issues'),
    }
    seen_reviews = set()
    seen_paths = set()
    for row in plan['independent_reviews']:
        need(set(row) == {'receipt', 'expected_status', 'issue_field'}, 'exact peer review binding required')
        need(row['receipt']['path'] not in seen_paths, 'unique independent review receipt paths required')
        seen_paths.add(row['receipt']['path'])
        reviewed = document(row['receipt'])
        schema = reviewed['schema']
        if schema in required_reviews:
            need(schema not in seen_reviews and (row['expected_status'], row['issue_field']) == required_reviews[schema], 'unique required review schema/status required')
            seen_reviews.add(schema)
        need(reviewed['status'] == row['expected_status'] and reviewed[row['issue_field']] == [], 'independent review failed')
        reviews.append(row['receipt'])
        if reviewed['schema'] == 'ranker-objective-scalar-independent-semantic-native-review@1':
            need(semantic is None, 'unique semantic/native review required')
            semantic = reviewed
    need(seen_reviews == set(required_reviews) and semantic is not None, 'source, prepared input, semantic/native and metadata reviews required')
    need(semantic['actual_distinct_kernel_queries'] == 14 and semantic['actual_native_invocations'] == 2 and
         semantic['only_allowed_standard_axioms'] == ['Classical.choice', 'Quot.sound', 'propext'], 'independent accepted native scope differs')
    need(semantic['actual_AST_phase']['slices'] == pin(Q / 'evidence/compile-source-objective-01/objective-slices.json') and
         semantic['actual_AST_phase']['generated'] == pin(Q / 'evidence/compile-source-objective-01/GeneratedObjectiveScalarLeaves.lean'),
         'independent source/emitter joins differ')
    build = document(plan['metadata_build_receipt'])
    need(build['schema'] == 'ranker-objective-scalar-metadata-file-build@1' and build['status'] == 'passed', 'metadata build gate failed')
    checks, queries = [], []
    need({path.parent.name for path in (Q / 'evidence').glob('*/check-result.json')} == set(NATIVE_MODES), 'complete actual native attempt census differs')
    for mode, (count, expected) in NATIVE_MODES.items():
        path = Q / 'evidence' / mode / 'check-result.json'
        check_pin = pin(path)
        need(check_pin['sha256'] == expected, 'actual native check differs')
        check = document(check_pin)
        need(check['status'] == 'passed' and check['matches_expectation'] is True and check['expected_success'] is True and
             check['native_invocations'] == check['native_lean_invocations'] == 1 and check['native_lean_returncode'] == 0,
             'actual native acceptance differs')
        need(check['axiom_report_error'] is None and check['post_call_binding_error'] is None and check['artifact_anomalies'] == [] and
             check['reconstruction_validation']['status'] == 'passed' and check['workspace_cleaned'] is True, 'native binding/retention differs')
        need(check['native_bounds'] == {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
                                       'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}, 'native limits changed')
        document(check['environment_manifest'])
        need(pin(check['source']['path']) == check['source'], 'native source changed')
        reports = check['theorem_axiom_output']
        need(len(reports) == count and all(set(row['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'} and
                                         row['report_occurrences'] == 2 for row in reports), 'native query/axiom census differs')
        queries.extend(row['theorem'] for row in reports)
        need(check['compiled_artifacts'] and all(row['complete'] is True for row in check['compiled_artifacts']), 'whole native modules required')
        for artifact in check['compiled_artifacts'] + check['retained_chunk_artifacts']:
            need(pin(artifact['path']) == {key: artifact[key] for key in ('path', 'bytes', 'sha256')}, 'whole object/chunk changed')
        checks.append({'mode': mode, 'qualification': check_pin, 'source': check['source'],
                       'environment_manifest': check['environment_manifest'], 'status': 'passed',
                       'owned_closed': pin(path.parent / 'closed.json'),
                       'outer_closed': pin(path.parent.with_name(mode + '-closed.json'))})
    need(len(queries) == len(set(queries)) == 14, 'distinct genuine query population required')
    need({row['qualification']['path']: row['qualification'] for row in checks} ==
         {row['check']['path']: row['check'] for row in semantic['actual_native_checks']}, 'semantic/native check joins differ')
    phases = []
    need({path.parent.name for path in (Q / 'evidence').glob('*/closed.json')} == MODES, 'all owned phase census differs')
    for mode in sorted(MODES):
        path = Q / 'evidence' / mode / 'closed.json'
        owned, outer = load(path), load(path.parent.with_name(mode + '-closed.json'))
        need(owned['status'] == 'passed' and outer['returncode'] == 0 and outer['primary_error'] is None and
             owned['cleanup_errors'] == outer['cleanup_errors'] == [] and owned['invocation'] == outer['invocation'], 'owned/outer phase failed')
        need(owned['final_resource_state']['active_lease_count'] == owned['final_resource_state']['waiting_request_count'] == 0 and
             owned['strict_old_input_count'] == 2108 and owned['protected_live_source_count'] == 4 and
             owned['all_strict_old_and_protected_live_inputs_unchanged'] is True, 'owned guards/drain differ')
        need(all(owned[key] == 0 for key in ('fit_calls', 'autoencoder_fit_calls', 'gradient_evaluations', 'optimizer_updates', 'native_preparation_calls')),
             'ranker/model execution outside qualification scope')
        phases.append(pin(path))
    pure = load(Q / 'evidence/pure-tests-objective-01/closed.json')
    pure_phases = load(Q / 'evidence/pure-tests-objective-01/phases.json')
    need(pure['selected_test_count'] == 98 and pure['pytest_returncode'] == 0 and pure['native_runner_calls_refused'] ==
         pure['direct_process_calls_refused'] == 0 and len(pure_phases) == 294 and all(row['outcome'] == 'passed' for row in pure_phases), 'pure controls differ')
    metadata_pin = pin(Q / 'evidence/metadata-objective-01/metadata-readback.json')
    metadata = document(metadata_pin)
    need(metadata['schema'] == 'ranker-objective-scalar-native-metadata-readback@1' and metadata['status'] == 'passed' and metadata['metadata_row_count'] == 4458 and metadata['metadata_family_count'] == 32 and
         metadata['fresh_process_readback_verified'] is True and metadata['all_payload_rows_read_back_exactly'] is True and
         metadata['metadata_build_receipt'] == plan['metadata_build_receipt'], 'fresh metadata readback gate differs')
    old_rows, new_rows = document(request['prior_metadata_inputs']), document(metadata['metadata_inputs'])
    need(metadata['frozen_build_plan'] == build['frozen_build_plan'] and wire(new_rows) == wire(document(build['metadata_inputs'])), 'exact built payload/plan joins differ')
    need(set(new_rows) == set(old_rows) and len(new_rows) == 32 and sum(map(len, old_rows.values())) == 4440 and
         sum(map(len, new_rows.values())) == 4458, 'metadata family/payload census differs')
    need(all(wire(new_rows[family][:len(values)]) == wire(values) for family, values in old_rows.items()), 'old payload prefix changed')
    need(wire(new_rows['vectors']) == wire(old_rows['vectors']) and len(new_rows['vectors']) == 375 and
         wire(new_rows['contracts']) == wire(old_rows['contracts']) and len(new_rows['contracts']) == 2, 'vector/contract drift')
    for family, values in new_rows.items():
        exported = [json.loads(line)['payload'] for line in read(Q / 'evidence/metadata-objective-01/metadata/exports' / (family + '.jsonl')).splitlines()]
        need(wire(exported) == wire(values), 'complete metadata export differs: ' + family)
    need(first == inventory() and guards(prior_review) == original, 'quiet inventory/original checkout changed')
    need(all(pin(path) == descriptor for path, descriptor in list(HELD.items())), 'held input changed before closure')
    result = {
        'schema': 'ranker-objective-scalar-closed-qualification@1', 'status': 'passed',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()),
        'closure_plan': plan_pin, 'prior_source_slice_seal': prior_seal_pin, 'independent_reviews': reviews,
        'metadata_build_receipt': plan['metadata_build_receipt'], 'native_checks': checks,
        'native_lean_calls': 2, 'qualified_positive_native_lean_checks': 2, 'inconclusive_native_lean_checks_retained': 0,
        'qualified_theorem_queries': 14, 'owned_phase_count': 5, 'phases': phases, 'pure_test_cases': 98,
        'all_owned_leases_drained': True, 'all_prior299_regular_leaves_unchanged': True, 'original_checkout_guards': original,
        'accepted_scalar_compiler_partial_semantic_preservation_proved': True,
        'emitted_stable_loss_exact_real_projection_proved': True, 'emitted_stable_factor_exact_real_projection_proved': True,
        'emitted_stable_loss_equals_realPairLoss_proved': True, 'emitted_stable_factor_equals_realLogisticP_proved': True,
        'prior_original_exact_real_model_weights_and_objective_convergence_preserved': True,
        'native_metadata_readback': metadata_pin, 'metadata_family_count': 32, 'metadata_payloads': 4458,
        'prior4440_payloads_preserved_exactly_as_prefixes': True, 'additive_metadata_payloads': 18,
        'vectors_payloads_unchanged': True, 'unchanged_vector_rows': 375, 'contracts_payloads_unchanged': True,
        'unchanged_contract_rows': 2, 'new_mathematical_projection_domain_contract_rows': 0,
        'strict_advisory_cache_entries_added': 0, 'native_proof_and_metadata_limits_unchanged': True,
        'new_autoencoder_fits': 0, 'new_public_fits': 0, 'new_gradient_evaluations': 0, 'new_optimizer_updates': 0,
        'new_ranker_training_trace_replays': 0, 'new_feature_preparations': 0,
        'open_obligations': pin(Q / 'source-model-obligations-01.json'),
        'host_parser_correctness_theorem_proved': False, 'python_ranker_source_equivalence_proved': False,
        'objective_to_IR_translation_proved': False, 'computed_gradient_source_equivalence_proved': False,
        'feature_preparation_to_IR_translation_proved': False, 'full_training_loop_to_IR_translation_proved': False,
        'CPython_math_fsum_semantics_proved': False, 'binary64_error_bound_proved': False,
        'native_Float_optimizer_convergence_proved': False, 'global_autoencoder_convergence_proved': False,
        'whole_codebase_IR_semantic_preservation_proved': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'atomic_whole_source_snapshot_claimed': False, 'historical_execution_origin_proved': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
    }
    save(Q / 'qualified-review-01.json', result)
    leaves = inventory()
    review_pin = pin(Q / 'qualified-review-01.json')
    need(leaves == sorted(first + [review_pin], key=lambda row: os.fsencode(row['path'])), 'final sealed population differs from reviewed census plus result')
    seal = {'schema': 'ranker-objective-scalar-file-only-seal@1', 'scope_root': str(Q), 'review': pin(Q / 'qualified-review-01.json'),
            'regular_file_count': len(leaves), 'regular_file_bytes': sum(row['bytes'] for row in leaves), 'files': leaves,
            'file_inventory_sha256': hashlib.sha256(wire(leaves)).hexdigest(), 'fixture_symlinks': [], 'excluded_dependency_roots': [],
            'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
    save(Q / 'file-only-seal-01.json', seal)
    print(json.dumps({'status': 'passed', 'review': pin(Q / 'qualified-review-01.json'), 'seal': pin(Q / 'file-only-seal-01.json'),
                      'files': len(leaves), 'bytes': seal['regular_file_bytes'], 'native_queries': 14, 'metadata_payloads': 4458}))


if __name__ == '__main__':
    main()
