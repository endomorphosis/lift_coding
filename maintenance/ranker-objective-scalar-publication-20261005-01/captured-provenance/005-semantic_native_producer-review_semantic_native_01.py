"""Independent read/hash/AST/JSON audit; no candidate code or jobs execute."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01')
OUT = Path(__file__).resolve().parent
HELD = {}
CAP = 32 * 1024**2
MODES = ['compile-source-objective-01', 'pure-tests-objective-01', 'lean-objective-scalar-01', 'lean-objective-generated-01']
OWNED = ['b083feb9f2397268062647867b8c993a0a774322c243605b38189f539bb43a9e',
         'b1fb4920100a38ad3955c71ccf6be3bfab5733daa8bfc9ebc518e770da938a18',
         'cf79d451ab0edcc291b9fcbccffc7518875688b93b4336ab371a2ceb9b44c7a8',
         'f79233cb4bbc17e93316aa4f54c515f3c288c658d01798a6ce6ab8ded518db99']
OUTER = ['ec8300e4f4d3a7406f8a9d3ea1f093a64726988b5ab73d71e2e1147d108019b3',
         '4bf374151c0cd69c48f6b4f20f9128d153430a02a4a58bddc2f0735da1660279',
         'df4e5481fa83da841b5cec6a251a96a371a6a3e511b8d810e06e7163462e4ca8',
         '547e672fadca53b032afbd66c5fd232eb22382e2e6b9c83cc3e59b5d7408d59e']
CHECKS = ['57ac502ebc37df08ae73b7fec69280b2dcb1a2453895ab573869d826d613bd5e',
          '4bcc8424739067b6e31382f594bd0c17e7e3e800d117bd08b2e38de302177041']


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, sha=None, capture=True):
    path = Path(path)
    need(path.suffix != '.log' and path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical non-log regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and (not capture or before.st_size <= CAP), 'input type/capture cap')
        blocks, size, digest = [], 0, hashlib.sha256()
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= before.st_size and (not capture or size <= CAP), 'input grew while hashing')
            digest.update(block)
            if capture:
                blocks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        sig = lambda value: tuple(getattr(value, name) for name in fields)
        need(sig(before) == sig(os.fstat(fd)) == sig(path.lstat()) and size == before.st_size, 'unstable input read')
        pin = {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}
        need(sha is None or pin['sha256'] == sha, 'expected digest differs')
        need(path not in HELD or HELD[path] == pin, 'repeated input differs')
        HELD[path] = pin
        return b''.join(blocks), pin
    finally:
        os.close(fd)


def document(path, sha=None):
    raw, pin = read(path, sha)
    return json.loads(raw), pin


def exact_descriptor(row, capture=False):
    expected = {name: row[name] for name in ('path', 'bytes', 'sha256')}
    raw, actual = read(expected['path'], expected['sha256'], capture=capture)
    need(actual == expected, 'complete descriptor bytes differ')
    return raw


def ast_hash(node):
    return hashlib.sha256(ast.dump(node, annotate_fields=True, include_attributes=False).encode()).hexdigest()


def scalar_witness(node):
    """Independent structural inspection of the two actual scalar AST leaves."""
    if isinstance(node, ast.Constant):
        need(type(node.value) in (int, float), 'non-numeric actual leaf')
        n, d = node.value.as_integer_ratio() if type(node.value) is float else (node.value, 1)
        return {'kind': 'num', 'numerator': str(n), 'denominator': str(d)}
    if isinstance(node, ast.Name):
        need(node.id == 'z' and isinstance(node.ctx, ast.Load), 'actual leaf lexical binding differs')
        return {'kind': 'var', 'name': 'z'}
    if isinstance(node, ast.UnaryOp):
        need(isinstance(node.op, ast.USub), 'actual unary operation differs')
        return {'kind': 'neg', 'value': scalar_witness(node.operand)}
    if isinstance(node, ast.BinOp):
        op = {ast.Add: 'add', ast.Sub: 'sub', ast.Mult: 'mul', ast.Div: 'div'}.get(type(node.op))
        need(op is not None, 'actual binary operation differs')
        return {'kind': op, 'left': scalar_witness(node.left), 'right': scalar_witness(node.right)}
    if isinstance(node, ast.Call):
        need(not node.keywords, 'actual call keywords differ')
        if isinstance(node.func, ast.Name):
            kind = node.func.id
            need(kind in ('abs', 'max'), 'actual named call target differs')
        else:
            need(isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and
                 node.func.value.id == 'math' and node.func.attr in ('exp', 'log1p'), 'actual math call differs')
            kind = node.func.attr
        arity = 2 if kind == 'max' else 1
        need(len(node.args) == arity, 'actual call arity differs')
        children = [scalar_witness(child) for child in node.args]
        return ({'kind': kind, 'left': children[0], 'right': children[1]} if arity == 2 else
                {'kind': kind, 'value': children[0]})
    need(isinstance(node, ast.IfExp) and isinstance(node.test, ast.Compare) and
         len(node.test.ops) == len(node.test.comparators) == 1 and isinstance(node.test.ops[0], ast.GtE) and
         isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == 0,
         'actual conditional predicate differs')
    return {'kind': 'ifNonneg', 'condition': scalar_witness(node.test.left),
            'then': scalar_witness(node.body), 'else': scalar_witness(node.orelse)}


def typed_witness(named):
    if named['kind'] == 'var':
        return {'kind': 'var', 'slot': 0}
    return {key: typed_witness(value) if isinstance(value, dict) else value for key, value in named.items()}


def render_witness(node):
    kind = node['kind']
    if kind == 'num':
        return ('(.num (' + node['numerator'] + ' : Rat))' if node['denominator'] == '1' else
                '(.num ((' + node['numerator'] + ' : Rat) / ' + node['denominator'] + '))')
    if kind == 'var':
        return '(.var "z")'
    keys = {'neg': ['value'], 'abs': ['value'], 'exp': ['value'], 'log1p': ['value'],
            'add': ['left', 'right'], 'sub': ['left', 'right'], 'mul': ['left', 'right'],
            'div': ['left', 'right'], 'max': ['left', 'right'], 'ifNonneg': ['condition', 'then', 'else']}[kind]
    return '(.' + kind + ' ' + ' '.join(render_witness(node[key]) for key in keys) + ')'


def inert_text(node, values):
    """Read only emitter literal concatenations; no Call node is interpreted."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return inert_text(node.left, values) + inert_text(node.right, values)
    if isinstance(node, ast.Subscript):
        return inert_text(node.value, values)[ast.literal_eval(node.slice)]
    raise ValueError('emitter literal inspection encountered a non-inert expression')


def main():
    source_review, source_review_pin = document(OUT / 'review-receipt.json',
        '78cce15ec117574bc29b3033e4f76c430e19f582c5268aef8863c849167d2e2d')
    prepared_review, prepared_review_pin = document(OUT / 'prepared-input-review-receipt-01.json',
        '4e9436bdaf2a8cbb9182e476f95a04bb49997c85c0fe61fbeaa0f77ce8ec271f')
    need(source_review['status'] == 'passed_source_only' and prepared_review['status'] == 'passed_file_only',
         'independent source/prepared gates differ')
    for row in source_review['candidate_sources']:
        exact_descriptor(row)
    pairs, actual = {}, {}
    request = None
    for mode, sha, outer_sha in zip(MODES, OWNED, OUTER):
        owned, owned_pin = document(ROOT / 'evidence' / mode / 'closed.json', sha)
        outer, outer_pin = document(ROOT / 'evidence' / (mode + '-closed.json'), outer_sha)
        invocation_raw = exact_descriptor(owned['invocation'], capture=True)
        invocation = json.loads(invocation_raw)
        need(owned['schema'] == 'terminal-ranker-curvature-owned-control@1' and owned['mode'] == mode and
             owned['status'] == 'passed' and owned['primary_error'] is None and not owned['cleanup_errors'],
             'actual owned control did not pass cleanly')
        need(outer['schema'] == 'terminal-ranker-curvature-outer-control@1' and type(outer['returncode']) is int and
             outer['returncode'] == 0 and outer['primary_error'] is None and not outer['cleanup_errors'] and
             outer['invocation'] == owned['invocation'] and outer['elapsed_seconds_outer'] <= 120,
             'actual outer control did not pass or join')
        need(invocation['mode'] == mode and invocation['outer_timeout_seconds'] == 120 and
             invocation['inputs'][1] == invocation['request'] and invocation['inputs'][2:] == invocation['extra_inputs'],
             'owned invocation shape/timeout differs')
        for row in invocation['inputs']:
            exact_descriptor(row)
        current_request = json.loads(exact_descriptor(invocation['request'], capture=True))
        need(request is None or current_request == request, 'phase request differs')
        request = current_request
        need(invocation['inputs'][0]['sha256'] == '42db20ed326046ad9e2bc9666cc67494937dd3321a1b70ddb4f5618b8271d14f',
             'executed captured driver differs from reviewed final source')
        need(owned['strict_old_input_count'] == len(request['strict_old_inputs']) == 2108 and
             owned['protected_live_source_count'] == len(request['protected_live_sources']) == 4 and
             owned['all_strict_old_and_protected_live_inputs_unchanged'] is True, 'actual guards incomplete')
        for name in ['native_preparation_calls', 'gradient_evaluations', 'optimizer_updates', 'fit_calls', 'autoencoder_fit_calls']:
            need(type(owned[name]) is int and owned[name] == 0, 'actual control evaluated or fitted ranker')
        for name in ['proof_authority', 'execution_authority', 'completion_authority', 'planner_activation', 'whole_program_proved']:
            need(owned[name] is False, 'actual owned control promotes authority/source proof')
        need(owned['full_task_satisfaction'] == 'unknown' and owned['root_release_returned'] is True, 'actual task/release differs')
        lease = owned['root_lease']
        need((lease['cpu_slots'], lease['memory_mb'], lease['child_process_slots']) == (1, 2048, 4) and
             lease['owner_pid'] == outer['child_pid'], 'actual owned lease differs')
        for name in ['active_lease_count', 'waiting_request_count', 'active_root_lease_count', 'active_child_lease_count', 'allocated_child_process_slots']:
            need(type(owned['final_resource_state'][name]) is int and owned['final_resource_state'][name] == 0,
                 'actual lease/waiters did not drain')
        for row in owned['selected_owned_imports']:
            need(row['matches'] is True and row['before'] == row['after'], 'actual selected import drift')
            exact_descriptor(row['after'])
        need(not owned['blocked_imports'], 'actual blocked-import attempt recorded')
        pairs[mode] = {'owned': owned_pin, 'outer': outer_pin, 'invocation': owned['invocation']}
        actual[mode] = owned
    need(request['proof_limits'] == {'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216},
         'actual inherited proof caps changed')
    compiled = actual[MODES[0]]
    need(type(compiled['source_AST_parse_calls']) is int and compiled['source_AST_parse_calls'] == 2 and
         type(compiled['source_function_execution_calls']) is int and compiled['source_function_execution_calls'] == 0 and
         compiled['new_native_qualification_jobs'] == 0 and not compiled['native_proof_checks'], 'actual AST phase counters differ')
    slices = json.loads(exact_descriptor(compiled['objective_scalar_slices'], capture=True))
    generated = exact_descriptor(compiled['generated_Lean_candidate'], capture=True)
    need(compiled['objective_scalar_slices']['sha256'] == '20f4cc89a1b92a9ab2eb3a53ec15298e9892c00550b5cb61891d278256fae124' and
         compiled['generated_Lean_candidate']['sha256'] == 'c6ba9dbc3a9ed056d04d004692180efd76db4e8d379681d7c8ff2edb1da8e919',
         'actual emission/slices externally reported pin differs')
    original = exact_descriptor(source_review['original_source'], capture=True)
    original_tree = ast.parse(original)
    objective = next(node for node in original_tree.body if isinstance(node, ast.FunctionDef) and node.name == '_objective')
    need(ast_hash(original_tree) == slices['source']['module_ast_sha256'] and ast_hash(objective) ==
         slices['objective_context']['ast_sha256'] == '129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2',
         'actual same-buffer whole source/context digest differs')
    loss, factor = objective.body[1].value.left.args[0].elt, objective.body[3].value.elt
    l2 = next(node.value for node in original_tree.body if isinstance(node, ast.Assign) and
              any(isinstance(target, ast.Name) and target.id == 'L2' for target in node.targets))
    values = {'actual': slices, 'SOURCE_SHA256': source_review['original_source']['sha256'],
              'OBJECTIVE_AST_SHA256': slices['objective_context']['ast_sha256']}
    for role, node, emitted_name in [('stable_loss', loss, 'loss'), ('stable_factor', factor, 'factor'), ('source_L2', l2, 'l2')]:
        named = scalar_witness(node)
        need(slices[role]['source_scalar'] == named and slices[role]['ir'] ==
             {'schema': 'ranker-objective-scalar-ir@1', 'slots': 1, 'body': typed_witness(named)} and
             slices[role]['lean_source_scalar'] == render_witness(named), 'actual operator/literal/lexical tree differs')
        values[emitted_name] = render_witness(named)
    host = ast.parse(exact_descriptor(next(row for row in source_review['candidate_sources']
                          if row['path'].endswith('/objective_scalar_compiler.py')), capture=True))
    renderer = next(node for node in host.body if isinstance(node, ast.FunctionDef) and node.name == 'render_generated_lean_with_receipt')
    for statement in renderer.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name) and statement.targets[0].id in ('header', 'text'):
            values[statement.targets[0].id] = inert_text(statement.value, values)
        elif isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name) and statement.target.id == 'header':
            need(isinstance(statement.op, ast.Add), 'emitter header operation differs')
            values['header'] += inert_text(statement.value, values)
    need(values['text'].encode() == generated, 'actual generated bytes differ from inspected literal emitter and source trees')
    pure = actual[MODES[1]]
    need(pure['pytest_returncode'] == 0 and pure['selected_test_count'] == 98 and
         pure['native_runner_calls_refused'] == pure['direct_process_calls_refused'] == 0 and not pure['native_proof_checks'],
         'actual pure controls differ')
    phases, phases_pin = document(ROOT / 'evidence/pure-tests-objective-01/phases.json',
        '2cbb99f6ced96d6251f241a89fbfa9d92b838982f7d84cb40772c8cb650976bd')
    by_test = {}
    for row in phases:
        need(row['outcome'] == 'passed', 'pure phase did not pass')
        by_test.setdefault(row['nodeid'], []).append(row['phase'])
    need(len(phases) == 294 and len(by_test) == 98 and all(value == ['setup', 'call', 'teardown'] for value in by_test.values()),
         'actual complete pure-test phase population differs')
    checks, modules, environments, all_files = [], [], [], {}
    for index, mode in enumerate(MODES[2:]):
        check, check_pin = document(ROOT / 'evidence' / mode / 'check-result.json', CHECKS[index])
        owned = actual[mode]
        need(owned['native_proof_checks'] == [check_pin] and len(owned['native_checker_attempts']) == 1 and
             owned['native_checker_attempts'][0]['native_invocations_observed'] == 1, 'actual single native attempt differs')
        spec_row = owned['native_checker_attempts'][0]['specification']
        spec = json.loads(exact_descriptor(spec_row, capture=True))
        profile = json.loads(exact_descriptor(check['environment_manifest'], capture=True))
        need(spec['source'] == check['source'] and spec['environment_manifest'] == check['environment_manifest'] and
             spec['retention_helper'] == check['retention_helper'] and spec['python_executable'] == check['python_executable'] and
             spec['expected_success'] is check['expected_success'] is True, 'actual native specification/profile/helper joins differ')
        source = exact_descriptor(check['source'], capture=True)
        need(source == (exact_descriptor(next(row for row in source_review['candidate_sources']
                         if row['path'].endswith('/ObjectiveScalarIR.lean')), capture=True) if index == 0 else generated),
             'actual qualified source differs from reviewed math or emitted candidate')
        augmented = exact_descriptor(check['augmented_source'], capture=True)
        need(augmented == (source.decode() + '\n' + '\n'.join('#print axioms _root_.' + name for name in spec['theorem_names']) + '\n').encode(),
             'actual full kernel-query augmentation differs')
        need(check['status'] == 'passed' and check['matches_expectation'] is True and check['returncode'] ==
             check['native_lean_returncode'] == 0 and check['native_invocations'] == check['native_lean_invocations'] == 1,
             'actual native check did not pass first attempt')
        for name in ['axiom_report_error', 'post_call_binding_error', 'reconstruction_validation_error']:
            need(check[name] is None, 'actual native binding/reconstruction error')
        for name in ['timed_out', 'unavailable', 'resource_exhausted', 'cancelled', 'workspace_limit_exceeded', 'output_truncated']:
            need(check[name] is False, 'actual native refusal/truncation recorded')
        need(check['workspace_cleaned'] is True and not check['artifact_anomalies'] and
             check['actual_root_lease'] == owned['root_lease'], 'actual native cleanup/lease join differs')
        need(check['native_bounds'] == {'cpu_seconds': 20, 'max_input_bytes': 262144, 'max_output_bytes': 65536,
             'max_workspace_bytes': 16777216, 'timeout_seconds': 20}, 'actual native bounds differ')
        need(check['native_elapsed_seconds'] <= 20 and check['allowed_standard_axioms'] == ['Classical.choice', 'Quot.sound', 'propext'],
             'actual native elapsed/axiom allowlist differs')
        reports = check['theorem_axiom_output']
        need([row['theorem'] for row in reports] == spec['theorem_names'] and len(reports) == (5 if index == 0 else 9) and
             all(type(row['report_occurrences']) is int and row['report_occurrences'] == 2 and
                 set(row['axioms']) <= {'Classical.choice', 'Quot.sound', 'propext'} for row in reports), 'actual per-query report population differs')
        parsed_reports = [(name, [] if axioms == '' else [part.strip() for part in axioms.split(',')])
                          for name, axioms in re.findall(r"'([^']+)' (?:depends on axioms:\s*\[([^]]*)\]|does not depend on any axioms)", check['stdout'])]
        expected_reports = [(row['theorem'], row['axioms']) for row in reports]
        need(parsed_reports == expected_reports + expected_reports, 'actual raw full-query report occurrences disagree')
        for name in ['proof_authority', 'execution_authority', 'completion_authority', 'planner_activation',
                     'python_ranker_source_equivalence_proved', 'binary64_error_bound_proved', 'optimizer_convergence_proved']:
            need(check[name] is False, 'native mathematical receipt promotes Python/Float/authority')
        need(check['all32_governing_RPI_exits'] == 'OPEN' and check['full_task_satisfaction'] == 'unknown' and
             check['official_benchmark_score'] is None and check['environment_actual_runtime_open_trace_claimed'] is False,
             'native receipt overclaims whole task/runtime tracing')
        retained = json.loads(exact_descriptor(check['retention_manifest'], capture=True))
        need(retained == check['retention_manifest_body'] and retained['schema'] == 'bounded_lean_chunks@1' and
             retained['status'] == 'complete' and retained['native_lean_invocations'] == 1 and
             retained['native_lean_returncode'] == 0 and retained['retention_profile_sha256'] == check['retention_profile_sha256'],
             'complete retention manifest join differs')
        need(len(retained['objects']) == 1 and len(retained['chunks']) == (29 if index == 0 else 2) and
             len(check['compiled_artifacts']) == 1, 'actual module/chunk population differs')
        chunks, reconstructed = {}, b''
        directory = Path(check['retention_manifest']['path']).parent
        for chunk_index, row in enumerate(retained['chunks']):
            need(row['name'] == 'LeanProofChunk' + str(chunk_index).zfill(3) + '.bin' and
                 type(row['bytes']) is int and 0 < row['bytes'] <= 65536, 'retained chunk order/bound differs')
            raw, pin = read(directory / row['name'], row['sha256'])
            need(len(raw) == row['bytes'], 'chunk bytes differ')
            chunks[row['name']] = raw
            need({**pin, 'complete': True} in check['retained_chunk_artifacts'], 'chunk descriptor absent from actual receipt')
        body = retained['objects'][0]
        need(body['chunks'] == [row['name'] for row in retained['chunks']], 'full module chunk concatenation order differs')
        reconstructed = b''.join(chunks[name] for name in body['chunks'])
        artifact = check['compiled_artifacts'][0]
        expected_module_name = 'ObjectiveScalarIR.olean' if index == 0 else 'GeneratedObjectiveScalarLeaves.olean'
        need(body['name'] == expected_module_name and Path(artifact['path']) == directory / body['name'] and
             artifact['complete'] is True and artifact['retention_format'] == 'bounded_lean_chunks@1' and
             body['bytes'] == len(reconstructed) == artifact['bytes'] == (1881720 if index == 0 else 73712) and
             body['sha256'] == hashlib.sha256(reconstructed).hexdigest() == artifact['sha256'] ==
             ('4e8a30cb3830ee6f1c689d827db695ebad8555bf1c6ac624fd320f3c6c80f134' if index == 0 else
              '867a5617be43f395e05ef1cec1c5027b298f800c0969b625dabc0f2f74224f9a'), 'complete retained module reconstruction differs')
        need(exact_descriptor(artifact, capture=True) == reconstructed and
             retained['aggregate_raw_object_bytes'] == len(reconstructed) <= 3997696 and
             check['reconstruction_validation']['status'] == 'passed', 'full raw retained module differs')
        need(sorted(path.name for path in directory.glob('LeanProofChunk*.bin')) == sorted(chunks), 'extra/missing retained chunk file')
        file_rows = profile['files']
        need(len(file_rows) == len({row['path'] for row in file_rows}) == check['environment_file_count'] == profile['external_file_count'] and
             sum(row['bytes'] for row in file_rows) == profile['external_file_bytes'], 'full environment descriptor census differs')
        need(profile['selected_proof_sources'] == [check['source']] and check['source'] in file_rows and
             check['retention_helper'] in file_rows and check['python_executable'] in file_rows and
             profile['native_per_file_capture_bytes_unchanged'] == 65536 and
             profile['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696, 'per-job source/helper/native caps differ')
        for row in file_rows:
            need(row['path'] not in all_files or all_files[row['path']] == row, 'cross-environment path has conflicting descriptors')
            all_files[row['path']] = row
        environments.append({'manifest': check['environment_manifest'], 'files': len(file_rows), 'bytes': profile['external_file_bytes']})
        checks.append({'check': check_pin, 'specification': spec_row, 'queries': reports})
        modules.append({'artifact': artifact, 'retention_manifest': check['retention_manifest'],
                        'chunks': len(chunks), 'full_raw_equals_ordered_chunks': True})
    need(len(all_files) <= 25000 and sum(row['bytes'] for row in all_files.values()) <= 4 * 1024**3, 'environment union audit bound exceeded')
    print(json.dumps({'progress': 'hashing_complete_environment_union', 'files': len(all_files),
                      'bytes': sum(row['bytes'] for row in all_files.values())}), flush=True)
    for row in all_files.values():
        exact_descriptor(row)
    all_files_digest = hashlib.sha256(json.dumps([all_files[name] for name in sorted(all_files)], sort_keys=True,
                                               separators=(',', ':')).encode()).hexdigest()
    # Every body is stable for its own read; compact/source inputs are rechecked
    # at closure. This does not assert one atomic snapshot or runtime open trace.
    self_raw, self_pin = read(Path(__file__).resolve())
    for path, pin in list(HELD.items()):
        if str(path) not in all_files:
            exact_descriptor(pin)
    receipt = {
        'schema': 'ranker-objective-scalar-independent-semantic-native-review@1', 'status': 'passed_file_only_actual_receipt_review',
        'review_source': self_pin, 'source_review': source_review_pin, 'prepared_input_review': prepared_review_pin,
        'actual_phase_receipts': pairs, 'actual_native_checks': checks, 'complete_retained_modules': modules,
        'passed_native_modules': 2, 'actual_native_invocations': 2, 'actual_distinct_kernel_queries': 14,
        'actual_query_report_occurrences_per_query': 2, 'only_allowed_standard_axioms': ['Classical.choice', 'Quot.sound', 'propext'],
        'actual_pure_controls': {'tests': 98, 'phases': 294, 'all_passed': True, 'phases_pin': phases_pin,
                                 'native_or_direct_process_attempts': 0},
        'actual_AST_phase': {'parses': 2, 'source_function_execution_calls': 0,
                             'slices': compiled['objective_scalar_slices'], 'generated': compiled['generated_Lean_candidate'],
                             'actual_operator_trees_match_independent_source_AST_inspection': True,
                             'generated_bytes_equal_independently_inspected_inert_emitter_literal_concatenation': True},
        'actual_each_phase_guard_counts': {'strict_old_inputs': 2108, 'protected_live_sources': 4},
        'actual_each_phase_owned_receipt_guards_unchanged_and_leases_drained': True,
        'physical_environment_profiles': environments,
        'independently_read_complete_environment_union': {'files': len(all_files), 'bytes': sum(row['bytes'] for row in all_files.values()),
            'complete_sorted_descriptor_map_sha256': all_files_digest, 'every_file_body_matches_descriptor': True,
            'each_fd_read_and_path_stat_stable': True, 'whole_live_atomic_snapshot_claimed': False,
            'actual_runtime_open_trace_claimed': False},
        'narrow_semantic_claims': ['Accepted generic named-to-finite-slot scalar mathematical compilation preserves exact-real partial evaluation and domain errors.',
            'Both syntax branches are validated; exact evaluation selects one branch lazily.',
            'Literal emitted stable-loss and sign-split factor trees compile to the inspected exact-real trees and join the prior realPairLoss/realLogisticP statements.',
            'Host AST/source/emitter joins are independently inspected and pure-controlled, not proved by the Lean kernel.'],
        'outstanding_review_issues': [],
        'reviewer_work': {'target_modules_imported_or_executed': 0, 'compiler_renderer_tests_native_model_jobs_rerun': 0,
                         'Git_commands_or_mutations': 0, 'remote_calls': 0, 'log_bodies_read': 0,
                         'writes_outside_owned_review_namespace': 0},
        'host_parser_correctness_theorem_proved': False, 'python_ranker_source_equivalence_proved': False,
        'full_objective_source_equivalence_proved': False, 'gradient_source_equivalence_proved': False,
        'Python_Float_libm_fsum_semantics_proved': False, 'optimizer_source_convergence_proved': False,
        'whole_codebase_IR_semantic_preservation_proved': False, 'global_autoencoder_convergence_proved': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
    }
    target = OUT / 'semantic-native-review-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = target.read_bytes()
    print(json.dumps({'status': receipt['status'], 'receipt': {'path': str(target), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}, 'review_source': self_pin}), flush=True)


if __name__ == '__main__':
    main()
