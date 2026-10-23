"""Independent file-only semantic/native receipt audit; no helper imports or jobs.

CLI plan schema: ranker-source-slices-final-independent-review-plan@1.
documents pins: request, compiler_v1, tests_v1, compiler_v2, tests_v2,
source_specification, slices_v1, slices_v2, generated_v1, generated_v2,
typed_source_v1, typed_source_v2.
native_checks entries: mode, check, specification, owned_closed, outer_closed.
owned_phases entries: mode, closed, outer_closed, phases (for pure-tests only).
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
SOURCE_SHA = '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'
BASE_SHA = 'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084'
BOUNDS = {'cpu_seconds': 20, 'max_input_bytes': 262144, 'max_output_bytes': 65536, 'max_workspace_bytes': 16777216, 'timeout_seconds': 20}
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
TYPED_QUERIES = ['compile_eval_commutes', 'compile_sound', 'compile_refuses_unsupported', 'compile_refuses_unknown_name', 'compiled_dot_body', 'compiled_update_body', 'orderedFsum_eq_sum', 'zipBody_length', 'zipBodyWithScalar_length', 'supported_dot_eq', 'source_dot_literal_eq', 'supported_update_eq', 'source_update_literal_eq', 'originalRealStep_update_join']
GENERATED_QUERIES = ['emitted_dot_compiles', 'emitted_update_compiles', 'emitted_dot_compiler_commutes', 'emitted_update_compiler_commutes', 'emitted_dot_projection', 'emitted_update_projection', 'emitted_originalRealStep_join']


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def signature(row):
    return tuple(getattr(row, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


CACHE = {}
PIN_REFERENCES = 0


def read(path):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path, 'aliased read path ' + str(path))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        need(stat.S_ISREG(before.st_mode), 'nonregular input')
        parts = []
        while part := os.read(descriptor, 1024**2):
            parts.append(part)
        raw = b''.join(parts)
        need(signature(before) == signature(os.fstat(descriptor)) == signature(path.lstat()) and len(raw) == before.st_size, 'file changed during held read')
        result = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if str(path) in CACHE:
            need(CACHE[str(path)]['pin'] == result and CACHE[str(path)]['stat'] == signature(before), 'file changed across review')
        CACHE[str(path)] = {'pin': result, 'stat': signature(before)}
        return raw
    finally:
        os.close(descriptor)


def check_pin(binding):
    global PIN_REFERENCES
    PIN_REFERENCES += 1
    need(set(binding) == {'path', 'bytes', 'sha256'} and type(binding['bytes']) is int, 'malformed pin')
    path = str(Path(binding['path']).absolute())
    if path not in CACHE:
        read(path)
    else:
        need(signature(Path(path).lstat()) == CACHE[path]['stat'] and Path(path).resolve(strict=True) == Path(path), 'cached input identity changed')
    need(CACHE[path]['pin'] == binding, 'byte pin mismatch ' + path)
    return binding


def load_pin(binding):
    check_pin(binding)
    return json.loads(read(binding['path']))


def pin(path):
    read(path)
    return CACHE[str(Path(path).absolute())]['pin']


def digest_ast(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def reject_authority(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('_authority') or key in {'planner_activation', 'authority_activation'}:
                need(item is False, 'unexpected authority: ' + key)
            reject_authority(item)
    elif isinstance(value, list):
        for item in value:
            reject_authority(item)


def safe_scalar_tree(node, scope):
    if isinstance(node, ast.Name) and node.id in scope:
        return {'kind': 'var', 'slot': scope.index(node.id)}
    if isinstance(node, ast.BinOp) and type(node.op) in {ast.Mult, ast.Sub, ast.Add}:
        return {'kind': {ast.Mult: 'mul', ast.Sub: 'sub', ast.Add: 'add'}[type(node.op)], 'left': safe_scalar_tree(node.left, scope), 'right': safe_scalar_tree(node.right, scope)}
    raise ValueError('actual slice contains an unsupported scalar node')


def static_string(node, values):
    """Review literal string concatenations; no Python target body is executed."""
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return static_string(node.left, values) + static_string(node.right, values)
    raise ValueError('emitter template exceeds static literal concatenation')


def verify_generated_template(compiler, slices, generated):
    module = ast.parse(compiler)
    renderer = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'render_generated_lean')
    text_assignment = next(n for n in renderer.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'text' for t in n.targets))
    header = '-- SOURCE-ONLY CANDIDATE: original raw source SHA256 ' + SOURCE_SHA + '\n'
    header += '-- dot expression AST SHA256 ' + slices['dot']['expression_ast_sha256'] + '\n'
    header += '-- update assignment AST SHA256 ' + slices['update']['assignment_ast_sha256'] + '\n'
    header += '-- update function context AST SHA256 ' + slices['update']['function_ast_sha256'] + '\n'
    header += '-- No Python/Float, objective, preparation, or full training equivalence is asserted.\n'
    expected = static_string(text_assignment.value, {'header': header, 'dot_body': slices['dot']['lean_source_scalar'], 'update_body': slices['update']['lean_source_scalar']})
    need(expected.encode() == generated, 'actual generated bytes differ from reviewed static emitter template')
    need(generated.count(b'#print axioms ') == 7 and b'sorry' not in generated and b'axiom ' not in generated, 'generated gate population')


def verify_closure(owned, outer, expected_status):
    need(owned['status'] == expected_status and owned['cleanup_errors'] == [], 'owned closure')
    need(outer['returncode'] == (0 if expected_status == 'passed' else 1) and outer['cleanup_errors'] == [], 'outer closure')
    need(outer['primary_error'] is None and outer['elapsed_seconds_outer'] < 120, 'outer attempt exceeded profile or failed wrapper')
    need(owned['final_resource_state']['active_lease_count'] == owned['final_resource_state']['waiting_request_count'] == 0 and owned['root_release_returned'], 'lease not drained')
    need(all(row['matches'] is True and row['before'] == row['after'] for row in owned['selected_owned_imports']), 'owned imports drift')
    for row in owned['selected_owned_imports']:
        check_pin(row['before'])
    for field in ['native_preparation_calls', 'gradient_evaluations', 'optimizer_updates', 'fit_calls', 'autoencoder_fit_calls']:
        need(owned[field] == 0, 'forbidden numerical operation counted')
    reject_authority(owned)
    invocation = load_pin(owned['invocation'])
    need(outer['invocation'] == owned['invocation'], 'outer/owned invocation join')
    for binding in invocation['inputs']:
        check_pin(binding)
    return invocation


def verify_native(entry, documents, observations):
    mode = entry['mode']
    check = load_pin(entry['check'])
    specification = load_pin(entry['specification'])
    owned = load_pin(entry['owned_closed'])
    outer = load_pin(entry['outer_closed'])
    accepted = mode != 'lean-typed-scalar-01'
    invocation = verify_closure(owned, outer, 'passed' if accepted else 'failed')
    need(owned['mode'] == mode and check['status'] == ('passed' if accepted else 'inconclusive'), 'native status denominator')
    need(entry['check'] in owned['native_proof_checks'] or not accepted, 'owned native result join')
    need(specification['expected_success'] is True and check['expected_success'] is True, 'positive-query specification')
    need(check['source'] == specification['source'] and check['environment_manifest'] == specification['environment_manifest'], 'native source/profile specification joins')
    need(check['native_lean_invocations'] == check['native_invocations'] == 1 and check['native_bounds'] == BOUNDS, 'native calls/caps')
    need(check['native_elapsed_seconds'] <= 20 and not check['timed_out'] and not check['cancelled'] and not check['output_truncated'], 'native profile failure')
    reject_authority(check)
    for role in ['source', 'augmented_source', 'environment_manifest', 'retention_manifest', 'retention_helper', 'python_executable']:
        check_pin(check[role])
    source_role = 'typed_source_v1' if mode.endswith('scalar-01') else 'typed_source_v2' if mode.endswith('scalar-02') else 'generated_v2'
    need(read(check['source']['path']) == read(documents[source_role]['path']), 'frozen source capture equality')
    profile = load_pin(check['environment_manifest'])
    need(profile['profile_parent']['sha256'] == BASE_SHA, 'native profile must reuse qualified Q3 final closure')
    check_pin(profile['profile_parent'])
    need(profile['native_per_file_capture_bytes_unchanged'] == 65536 and profile['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696, 'retention bounds changed')
    need(profile['external_file_count'] == len(profile['files']) and profile['external_file_bytes'] == sum(x['bytes'] for x in profile['files']), 'environment census')
    for binding in profile['files']:
        check_pin(binding)
    if accepted:
        need(check['matches_expectation'] is True and check['axiom_report_error'] is None and check['post_call_binding_error'] is None and check['native_lean_returncode'] == 0, 'accepted native result incomplete')
        names = TYPED_QUERIES if mode == 'lean-typed-scalar-02' else GENERATED_QUERIES
        namespace = 'RankerSourceSemantics.' if mode == 'lean-typed-scalar-02' else 'RankerSourceSemanticsGenerated.'
        need(specification['theorem_names'] == [namespace + name for name in names], 'queried theorem registry')
        need([x['theorem'] for x in check['theorem_axiom_output']] == [namespace + name for name in names], 'actual queried names')
        need(all(set(x['axioms']) <= ALLOWED_AXIOMS and x['report_occurrences'] >= 1 for x in check['theorem_axiom_output']), 'unexpected accepted axioms')
        manifest = load_pin(check['retention_manifest'])
        need(manifest == check['retention_manifest_body'] and manifest['status'] == 'complete', 'complete retained manifest')
        chunk_pins = {Path(x['path']).name: x for x in check['retained_chunk_artifacts']}
        need(set(chunk_pins) == {x['name'] for x in manifest['chunks']}, 'exact complete chunk population')
        for chunk in manifest['chunks']:
            binding = chunk_pins[chunk['name']]
            need((binding['bytes'], binding['sha256']) == (chunk['bytes'], chunk['sha256']) and binding['bytes'] <= 65536, 'chunk cap/binding')
            check_pin(binding)
        objects = {Path(x['path']).name: x for x in check['compiled_artifacts']}
        need(set(objects) == {x['name'] for x in manifest['objects']}, 'object population')
        for item in manifest['objects']:
            full = b''.join(read(chunk_pins[name]['path']) for name in item['chunks'])
            binding = objects[item['name']]
            need(binding['complete'] is True and len(full) == item['bytes'] == binding['bytes'] and hashlib.sha256(full).hexdigest() == item['sha256'] == binding['sha256'], 'full object RAM reconstruction')
            need(read(binding['path']) == full, 'retained full object differs from chunks')
    else:
        need(check['matches_expectation'] is False and check['native_lean_returncode'] != 0 and check['compiled_artifacts'] == [] and check['retained_chunk_artifacts'] == [], 'failed native attempt accidentally admitted')
        need(check['retention_manifest_body']['status'] == 'native_nonzero' and 'sorryAx' in check['stdout'], 'retained failed elaboration evidence')
    observations.append({'mode': mode, 'status': check['status'], 'check': entry['check'], 'source': check['source'], 'environment_file_count': len(profile['files']), 'query_count_qualified': len(check['theorem_axiom_output']) if accepted else 0, 'complete_objects': len(check['compiled_artifacts']), 'chunks': len(check['retained_chunk_artifacts'])})
    return check, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    plan_raw = read(args.plan)
    need(hashlib.sha256(plan_raw).hexdigest() == args.plan_sha256, 'external review plan hash')
    plan = json.loads(plan_raw)
    need(plan['schema'] == 'ranker-source-slices-final-independent-review-plan@1', 'plan schema')
    need(plan['scope_root'] == str(WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'), 'review scope')
    documents = plan['documents']
    required = {'request', 'compiler_v1', 'tests_v1', 'compiler_v2', 'tests_v2', 'source_specification', 'slices_v1', 'slices_v2', 'generated_v1', 'generated_v2', 'typed_source_v1', 'typed_source_v2'}
    need(set(documents) == required, 'complete planned source/evidence roles')
    for binding in documents.values():
        check_pin(binding)
    request = load_pin(documents['request'])
    need(documents['request']['sha256'] == '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861', 'current protected request identity')
    need(len(request['strict_old_inputs']) == 1808 and len(request['protected_live_sources']) == 4, 'old/live denominators')
    for binding in request['strict_old_inputs'] + request['protected_live_sources']:
        check_pin(binding)
    need(read(documents['tests_v1']['path']) == read(documents['tests_v2']['path']), 'v2 tests differ without a planned test change')
    old_proof = b'  simpa only [RankerRealCurvature.realGradientStep] using\n    emitted_update_projection RankerRealCurvature.originalRealEta weights\n      (RankerRealCurvature.realCoordinateGradient RankerRealCurvature.originalRealMu\n        RankerRealCurvature.originalRealDifferences weights)'
    new_proof = b'  rw [emitted_update_projection]\n  rfl'
    need(read(documents['compiler_v2']['path']) == read(documents['compiler_v1']['path']).replace(old_proof, new_proof, 1), 'emitter v2 exact one-proof correction')
    spec = load_pin(documents['source_specification'])
    original = read(check_pin(spec['source'])['path'])
    need(len(original) == 16391 and hashlib.sha256(original).hexdigest() == SOURCE_SHA, 'actual original Python source bytes')
    shape = load_pin(spec['difference_artifact'])
    need(len(shape['differences']) == 4 and all(len(row) == 80 for row in shape['differences']), 'original supplied 4x80 artifact shape')
    s1 = load_pin(documents['slices_v1']); s2 = load_pin(documents['slices_v2'])
    need(wire(s1) == wire(s2), 'source IR/schema/body changed by proof-only emitter fix')
    reject_authority(s2); reject_authority(spec); reject_authority(request)
    need(s2['status'] == 'compiled_source_only_kernel_pending' and s2['dimension'] == 80, 'slice status/shape frontier')
    need(s2['external_shape_assumptions'] == {'difference_artifact_sha256': spec['difference_artifact']['sha256'], 'difference_columns': 80, 'difference_rows': 4, 'gradient_length': 80, 'weights_length': 80}, 'exact supplied shape assumption join')
    tree = ast.parse(original)
    dot = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_dot')
    train = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'train_terminal_codebase_intent_ranker')
    loop, guard, assign = train.body[5], train.body[5].body[2], train.body[5].body[2].body[0]
    generator = dot.body[0].value.args[0]
    need(s2['source']['module_ast_sha256'] == digest_ast(tree) and s2['source']['module_ast_nodes'] == sum(1 for _ in ast.walk(tree)), 'complete source AST digest/count')
    need(s2['dot']['function_ast_sha256'] == digest_ast(dot) and s2['dot']['expression_ast_sha256'] == digest_ast(generator), 'dot subtree context pins')
    for key, node in [('function_ast_sha256', train), ('loop_ast_sha256', loop), ('guard_ast_sha256', guard), ('assignment_ast_sha256', assign), ('expression_ast_sha256', assign.value)]:
        need(s2['update'][key] == digest_ast(node), 'training update context pin ' + key)
    for part, body, names, kind, inputs in [('dot', generator.elt, ['x', 'y'], 'zipFold', ['a', 'b']), ('update', assign.value.elt, ['w', 'g', 'step'], 'zipMap', ['weights', 'gradient'])]:
        ir = s2[part]['ir']
        need(ir['schema'] == 'ranker-typed-zip-ir@1' and ir['kind'] == kind and ir['zip_length'] == 'min' and ir['inputs'] == inputs and ir['binders'] == names[:2], 'exact container source scope')
        need(ir['scalar'] == {'schema': 'ranker-typed-scalar-ir@1', 'slots': len(names), 'body': safe_scalar_tree(body, names)}, 'actual scalar AST maps to stored typed IR')
    need(s2['dot']['lean_source_scalar'] == '(.mul (.var "x") (.var "y"))' and s2['update']['lean_source_scalar'] == '(.sub (.var "w") (.mul (.var "step") (.var "g")))', 'actual constructor literals')
    verify_generated_template(read(documents['compiler_v1']['path']), s1, read(documents['generated_v1']['path']))
    verify_generated_template(read(documents['compiler_v2']['path']), s2, read(documents['generated_v2']['path']))
    phases = plan['owned_phases']
    need({p['mode'] for p in phases} == {'compile-source-01', 'compile-source-02', 'pure-tests-source-01', 'pure-tests-source-02'} and len(phases) == 4, 'complete owned compile/test phase denominator')
    phase_observations = []
    for phase in phases:
        closed = load_pin(phase['closed']); outer = load_pin(phase['outer_closed'])
        invocation = verify_closure(closed, outer, 'passed')
        need(closed['mode'] == phase['mode'], 'phase mode join')
        if phase['mode'].startswith('pure-tests'):
            reports = load_pin(phase['phases']); calls = [p for p in reports if p['phase'] == 'call']
            need(len(calls) == closed['selected_test_count'] == 137 and closed['pytest_returncode'] == 0 and all(p['outcome'] == 'passed' for p in reports), 'meaningful pure-control result')
            need(closed['native_runner_calls_refused'] == closed['direct_process_calls_refused'] == 0, 'pure controls attempted forbidden process')
        else:
            suffix = 'v1' if phase['mode'].endswith('01') else 'v2'
            need(closed['source_slices'] == documents['slices_' + suffix] and closed['generated_Lean_candidate'] == documents['generated_' + suffix], 'actual compiler output pins')
            need(closed['source_AST_parse_calls'] == 2 and closed['source_function_execution_calls'] == closed['new_native_qualification_jobs'] == 0, 'no execution in compilation phase')
        phase_observations.append({'mode': phase['mode'], 'closed': phase['closed'], 'status': closed['status']})
    native = plan['native_checks']
    need({n['mode'] for n in native} == {'lean-typed-scalar-01', 'lean-typed-scalar-02', 'lean-generated-slices-01'} and len(native) == 3, 'native census')
    observations = []; checks = {}; profiles = {}
    for entry in native:
        checks[entry['mode']], profiles[entry['mode']] = verify_native(entry, documents, observations)
    generated_profile = profiles['lean-generated-slices-01']
    local = [r for r in generated_profile['local_checked_modules'] if r['module'] == 'TypedNumericSlice']
    typed_entry = next(n for n in native if n['mode'] == 'lean-typed-scalar-02')
    need(len(local) == 1 and local[0]['qualification'] == typed_entry['check'], 'generated module uses qualified typed02 only')
    typed_check = checks['lean-typed-scalar-02']
    module_rows = [r for r in generated_profile['source_import_modules'] if r['module'] == 'TypedNumericSlice']
    need(len(module_rows) == 1 and module_rows[0]['source'] == typed_check['augmented_source'], 'generated import actual qualified typed source')
    need(module_rows[0]['compiled'] == [{k: r[k] for k in ['path', 'bytes', 'sha256']} for r in typed_check['compiled_artifacts']], 'generated import actual complete typed object')
    failed_entry = next(n for n in native if n['mode'] == 'lean-typed-scalar-01')
    need(all(x['path'] != failed_entry['check']['path'] for x in generated_profile['files']), 'failed typed01 was registered as a dependency')
    need(sum(n['query_count_qualified'] for n in observations) == 21, 'qualified query census')
    # Re-read every top-level planned binding and every immutable input identity.
    # This is an individual held-file audit, not an atomic whole-filesystem claim.
    for binding in documents.values():
        need(pin(binding['path']) == binding, 'planned binding changed after joins')
    for path, binding in list(CACHE.items()):
        need(signature(Path(path).lstat()) == binding['stat'] and Path(path).resolve(strict=True) == Path(path), 'dependency identity changed after rehash')
    report = {'schema': 'ranker-source-slices-independent-semantic-native-file-review@1', 'status': 'passed_file_only_source_slice_semantic_native_review', 'outstanding_issues': [], 'plan': pin(args.plan), 'review_source': pin(Path(__file__).resolve()), 'documents': documents, 'native_attempts': observations, 'owned_compile_test_phases': phase_observations, 'census': {'native_attempts': 3, 'accepted_modules': 2, 'retained_inconclusive_attempts': 1, 'qualified_query_entries': 21, 'strict_old_inputs': 1808, 'protected_live_sources': 4, 'actual_pure_control_cases_each_attempt': 137, 'distinct_files_rehashed': len(CACHE), 'distinct_file_bytes': sum(b['pin']['bytes'] for b in CACHE.values()), 'pin_references_joined': PIN_REFERENCES}, 'same_original_AST_IR_and_generated_template_bytes_verified': True, 'all_accepted_chunks_and_complete_objects_rejoined_in_memory': True, 'original_shape_supplied_artifact_only': {'pairs': 4, 'coordinates': 80}, 'native_bounds': BOUNDS, 'scope': {'file_only': True, 'target_helper_imports': 0, 'target_helper_execution': 0, 'native_jobs': 0, 'test_jobs': 0, 'ranker_execution': 0, 'new_preparations': 0, 'new_fits': 0, 'new_gradient_evaluations': 0, 'new_optimizer_updates': 0, 'trace_replays': 0, 'codec_jobs': 0, 'remote_actions': 0, 'Git_actions': 0, 'protected_input_writes': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'host_parser_correctness_proved': False, 'whole_Python_source_equivalence_proved': False, 'binary64_or_libm_fsum_refinement_proved': False, 'source_objective_gradient_equivalence_proved': False, 'full_training_loop_equivalence_proved': False, 'whole_task_satisfaction': 'unknown', 'atomic_whole_filesystem_snapshot_claimed': False}, 'findings': ['Kernel arithmetic compiler and emitted constructor gates are genuinely qualified under the actual two accepted native modules.', 'Generic finite-list exact-real dot/update projection only: zip minimum length is explicit, and equal-size Fin vectors discharge truncation on the supported domain.', 'Original gradient and step remain supplied mathematical arguments in the original-step join; Python _objective and full training are outside the qualified source slice.', 'Original parser/source/AST hashes, typed IR tree/schema, renderer literal assembly, profile inputs and full retained object/chunk bodies are individually rejoined without importing the producers.', 'The failed first native attempt and its sorryAx diagnostic remain visible and confer no accepted query or module admission.']}
    destination = OUT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'receipt': pin(destination), 'census': report['census']}))


if __name__ == '__main__':
    main()
