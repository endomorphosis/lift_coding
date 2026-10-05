"""Source/JSON supplement for already frozen objective candidate inputs.

No reviewed producer, compiler, test, checker or renderer is imported or called.
No native objects, logs, SDKs, Git or remote resources are opened. Object
descriptors are joined to prior passed receipts; their bodies are not read.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01')
REVIEW = Path(__file__).resolve().parent
HELD = {}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def read(path, sha=None):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source/JSON required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'bounded input required')
        pieces, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 32 * 1024**2, 'growing review input')
            pieces.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size,
             'input changed during review read')
        raw = b''.join(pieces)
        pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(sha is None or pin['sha256'] == sha, 'same-read external digest differs')
        need(path not in HELD or HELD[path] == pin, 'repeated input changed')
        HELD[path] = pin
        return raw, pin
    finally:
        os.close(fd)


def doc(path, sha):
    raw, pin = read(path, sha)
    return json.loads(raw), pin


def main():
    source_review, source_review_pin = doc(REVIEW / 'review-receipt.json',
        '78cce15ec117574bc29b3033e4f76c430e19f582c5268aef8863c849167d2e2d')
    need(source_review['status'] == 'passed_source_only', 'prior source review did not pass')
    candidate_pins = {row['path']: row for row in source_review['candidate_sources']}
    spec, spec_pin = doc(ROOT / 'preparation/objective-slices-specification.json',
        '6aba6218c595db56698ecc8568ff0a710205fb6fd50a215c02944289d47c1d38')
    need(spec['schema'] == 'ranker-objective-scalar-compilation-specification@1' and
         spec['producer'] == candidate_pins[str(ROOT / 'source-v2/objective_scalar_compiler.py')] and
         spec['source'] == source_review['original_source'], 'prepared AST spec source/compiler differs')
    need(spec['scope'] == 'stable_loss_and_sign_split_factor_scalar_leaves_exact_real_only' and
         type(spec['source_execution_calls']) is int and spec['source_execution_calls'] == 0,
         'prepared AST scope/counter differs')
    for role, pin in source_review['planning_documents'].items():
        need(spec[role] == pin and read(pin['path'], pin['sha256'])[1] == pin, 'prepared P6 document join differs')
    producer_source_raw, producer_source_pin = read(ROOT / 'freeze_objective_specification_01.py',
        'e19f535e16983e733905f39b93bfbc2503e9e06343474291593de0c93fa39ae5')
    tree = ast.parse(producer_source_raw)
    arguments = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'ARGUMENTS' for target in node.targets))
    need(spec['arguments'] == arguments, 'prepared explicit four-hash API differs')
    need(read(spec['producer']['path'], spec['producer']['sha256'])[1] == spec['producer'] and
         read(spec['source']['path'], spec['source']['sha256'])[1] == spec['source'], 'prepared exact source bytes differ')
    lean_spec, lean_spec_pin = doc(ROOT / 'preparation/lean-objective-scalar-01-check-specification.json',
        '5a8aaac0881774c6cadb2af277afcc53e5e917190db7b6d78d7bae13bc4522ac')
    profile, profile_pin = doc(lean_spec['environment_manifest']['path'],
        '95cd44ea3b66f14ef3a633929eb1a3c94e1824cc8039f4cc8a5291b4ad5e598c')
    need(lean_spec['environment_manifest'] == profile_pin and
         lean_spec['schema'] == 'terminal-ranker-curvature-native-check-specification@1' and
         lean_spec['expected_success'] is True, 'prepared Lean specification/profile differs')
    math_pin = candidate_pins[str(ROOT / 'math/ObjectiveScalarIR.lean')]
    math_raw, captured_math_pin = read(lean_spec['source']['path'], math_pin['sha256'])
    need(captured_math_pin == lean_spec['source'] and captured_math_pin['bytes'] == math_pin['bytes'],
         'captured mathematical source differs from reviewed original')
    need(read(math_pin['path'], math_pin['sha256'])[1] == math_pin, 'live mathematical source differs')
    queries = re.findall(r'^#print axioms (\w+)$', math_raw.decode(), re.MULTILINE)
    need(lean_spec['theorem_names'] == ['RankerObjectiveIR.' + name for name in queries] and len(queries) == 5,
         'prepared full-query set differs')
    old_raw, old_pin = read(lean_spec['freeze_producer']['path'],
        '8a5766529d4a5d8ac7999508ade37f205bec29b5191a0834164957d274543455')
    new_raw, new_pin = read(ROOT / 'freeze_source_profile_01.py',
        '194acc937634ffef66116be4256e9a1943df0a066333bd6150ff7c3249994323')
    need(old_pin == lean_spec['freeze_producer'], 'captured producer descriptor differs')
    old_line = '    assert re.fullmatch(r"lean-[a-z0-9-]+", args.mode), "mode must be a bounded local basename"\n'
    new_line = '    assert len(args.mode) <= 96 and re.fullmatch(r"lean-objective(?:-[a-z0-9]+)*-[0-9]{2}", args.mode), "mode must be a numbered objective Lean basename"\n'
    need(old_raw.decode().count(old_line) == new_raw.decode().count(new_line) == 1 and
         old_raw.decode().replace(old_line, new_line) == new_raw.decode(), 'captured producer diff exceeds one mode assertion')
    mode = 'lean-objective-scalar-01'
    need(re.fullmatch(r'lean-[a-z0-9-]+', mode) is not None and len(mode) <= 96 and
         re.fullmatch(r'lean-objective(?:-[a-z0-9]+)*-[0-9]{2}', mode) is not None,
         'actually chosen profile mode fails a reviewed mode gate')
    need(profile['selected_proof_sources'] == [lean_spec['source']] and
         profile['native_per_file_capture_bytes_unchanged'] == 65536 and
         profile['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696,
         'selected source or native retention limits differ')
    for captured in profile['per_check_sources']:
        need(read(captured['captured']['path'], captured['captured']['sha256'])[1] == captured['captured'],
             'complete captured source bytes differ')
        need(captured['captured']['bytes'] == captured['original']['bytes'] and
             captured['captured']['sha256'] == captured['original']['sha256'], 'captured/historical source content differs')
    need(profile['per_check_sources'][0]['original'] == math_pin and
         profile['per_check_sources'][3]['captured'] == old_pin,
         'captured math/old producer provenance differs')
    # Original producer descriptor intentionally records the pre-tightening
    # source. The live original has the independently reviewed narrower mode
    # predicate. That historical descriptor is not an execution dependency.
    base, base_pin = doc(profile['profile_parent']['path'],
        'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084')
    need(base_pin == profile['profile_parent'], 'exact prior environment descriptor differs')
    expected_files = {row['path']: row for row in base['files']}
    need(len(expected_files) == len(base['files']), 'prior environment paths collide')
    for row in profile['per_check_sources']:
        expected_files[row['captured']['path']] = row['captured']
    expected_files[lean_spec['python_executable']['path']] = lean_spec['python_executable']
    need(lean_spec['python_executable'] == {'path': '/usr/bin/python3.12', 'bytes': 7845032,
         'sha256': '1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f'},
         'native Python descriptor differs')
    expected_modules = list(base['source_import_modules'])
    expected_local = list(base['local_checked_modules'])
    expected_paths = list(base['lean_path'])
    imports = {}
    for name, descriptor in source_review['actual_prior_checked_import_receipts'].items():
        check, check_pin = doc(descriptor['path'], descriptor['sha256'])
        need(check_pin == descriptor and check['status'] == 'passed' and check['matches_expectation'] is True and
             check['expected_success'] is True and check['native_invocations'] == 1 and
             check['post_call_binding_error'] is None and check['axiom_report_error'] is None,
             'actual qualified-import receipt differs')
        compiled = [{key: row[key] for key in ('path', 'bytes', 'sha256')} for row in check['compiled_artifacts']]
        need(compiled and all(row['complete'] is True for row in check['compiled_artifacts']) and
             any(Path(row['path']).name == name + '.olean' for row in compiled), 'qualified import completeness differs')
        for row in [*compiled, check['source'], check['augmented_source'], check['environment_manifest'], check_pin]:
            expected_files[row['path']] = row
        library = str(Path(compiled[0]['path']).parent)
        if library not in expected_paths:
            expected_paths.insert(0, library)
        expected_modules.append({'module': name, 'package': 'qualified-local-theorem',
                                 'source': check['augmented_source'], 'compiled': compiled})
        expected_local.append({'module': name, 'qualification': check_pin, 'environment': check['environment_manifest']})
        imports[name] = check_pin
    need(profile['files'] == [expected_files[name] for name in sorted(expected_files)] and
         profile['source_import_modules'] == expected_modules and profile['local_checked_modules'] == expected_local and
         profile['lean_path'] == expected_paths, 'prepared environment is not exact prior closure plus reviewed imports/captures')
    need(type(profile['external_file_count']) is int and profile['external_file_count'] == len(expected_files) == 20104 and
         type(profile['external_file_bytes']) is int and profile['external_file_bytes'] ==
         sum(row['bytes'] for row in expected_files.values()) == 3534384768, 'complete declared closure census differs')
    need(lean_spec['retention_helper'] in profile['files'] and lean_spec['python_executable'] in profile['files'],
         'prepared native helpers outside closure')
    allowed_changes = {'profile_parent', 'per_check_sources', 'selected_proof_sources', 'files',
                       'source_import_modules', 'local_checked_modules', 'lean_path', 'external_file_count', 'external_file_bytes'}
    need(set(profile) == set(base) | {'profile_parent', 'per_check_sources', 'selected_proof_sources'} and
         all(profile[key] == value for key, value in base.items() if key not in allowed_changes),
         'unexpected native environment bound/status/toolchain mutation')
    request, request_pin = doc(ROOT / 'preparation/request-v3.json',
        '8e9038a657519b35e769e911219dbe5ad4bf92833017663f8673d5ef2613fdd3')
    prior = ROOT.with_name('ranker-source-semantics-20261005-01')
    old_request, old_request_pin = doc(prior / 'preparation/request-v3.json',
        '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861')
    seal, seal_pin = doc(prior / 'file-only-seal-01.json',
        '21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65')
    qualification, qualification_pin = doc(prior / 'qualified-review-01.json',
        '39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550')
    expected_guards = {row['path']: row for row in old_request['strict_old_inputs']}
    need(len(expected_guards) == len(old_request['strict_old_inputs']) == 1808, 'prior strict guards differ')
    for row in [*seal['files'], seal_pin]:
        need(row['path'] not in expected_guards or expected_guards[row['path']] == row, 'strict guard overlap differs')
        expected_guards[row['path']] = row
    need(request['strict_old_inputs'] == [expected_guards[name] for name in sorted(expected_guards)] and
         len(expected_guards) == 2108 and request['protected_live_sources'] == old_request['protected_live_sources'] and
         len(request['protected_live_sources']) == 4, 'complete inherited request guard set differs')
    need(request['prior_source_slice_request'] == old_request_pin and request['prior_source_slice_seal'] == seal_pin and
         request['prior_source_slice_review'] == qualification_pin and seal['review'] == qualification_pin and
         qualification['status'] == 'passed', 'request/seal/actual prior qualification join differs')
    for key in ['proof_limits', 'proof_pressure_limits', 'root_request', 'outer_timeout_seconds']:
        need(request[key] == old_request[key], 'request native/controller cap changed')
    need(request['schema'] == 'terminal-ranker-objective-scalar-IR-request@1' and request['planner_activation'] is False and
         request['objective_source_equivalence_proved'] is False and request['gradient_source_equivalence_proved'] is False and
         request['full_task_satisfaction'] == 'unknown' and request['official_benchmark_score'] is None,
         'prepared request promotes runtime/frontier claims')
    self_raw, self_pin = read(Path(__file__).resolve())
    for path, descriptor in list(HELD.items()):
        need(read(path)[1] == descriptor, 'observed prepared input changed before supplement')
    receipt = {
        'schema': 'ranker-objective-scalar-prepared-input-source-review@1', 'status': 'passed_file_only',
        'review_source': self_pin, 'current_candidate_source_review': source_review_pin,
        'prepared_AST_specification': spec_pin, 'prepared_Lean_specification': lean_spec_pin,
        'prepared_Lean_environment': profile_pin, 'prepared_request': request_pin,
        'captured_earlier_freeze_producer': old_pin, 'reviewed_current_freeze_producer': new_pin,
        'exact_source_diff': 'Only the single mode assertion changed; actual lean-objective-scalar-01 satisfies both.',
        'captured_earlier_freeze_producer_accepted_for_prepared_mode': True,
        'historical_original_freeze_descriptor_not_asserted_equal_current_live_source': True,
        'declared_environment_census': {'files': 20104, 'bytes': 3534384768},
        'complete_prior_environment_descriptor_prefix_preserved': True,
        'exact_added_qualified_local_imports': imports,
        'prepared_native_queries': lean_spec['theorem_names'],
        'strict_guard_descriptors': 2108, 'protected_live_sources': 4,
        'native_retention_caps_unchanged': {'per_file': 65536, 'reconstruction_aggregate': 3997696},
        'outstanding_source_issues': [],
        'limits': {'target_imports_or_execution': 0, 'compiler_renderer_test_native_model_jobs': 0,
                   'Git_commands_or_mutations': 0, 'remote_calls': 0, 'native_object_bodies_or_log_bodies_read': 0,
                   'environment_dependency_bytes_rehashed': False,
                   'actual_original_checkout_or_resource_state_rechecked': False,
                   'scope': 'same-read source and JSON pins plus exact descriptor joins; actual bounded controller/checker must recheck dependencies at execution'},
        'native_qualification_claimed': False, 'test_success_claimed': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'planner_activation': False, 'all32_governing_RPI_exits': 'OPEN',
        'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'all_observed_sources_and_JSON_inputs_rechecked': True,
    }
    destination = REVIEW / 'prepared-input-review-receipt-01.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = destination.read_bytes()
    print(json.dumps({'status': receipt['status'], 'receipt': {'path': str(destination), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}, 'review_source': self_pin}))


if __name__ == '__main__':
    main()
