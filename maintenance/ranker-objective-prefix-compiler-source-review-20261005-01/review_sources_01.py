"""Independent file-only review: no candidate imports, compiler calls or tests."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
SCOPE = ROOT / 'qualification/codebase_ir/ranker-objective-container-prefix-candidate-20261005-01'
OUT = ROOT / 'maintenance/ranker-objective-prefix-compiler-source-review-20261005-01/review-receipt.json'
EXPECTED = {
    'source-v1/objective_prefix_compiler.py': (40622, '1737357b8fd967d43064c754a6f8957c3744a96b899f14c47e0f3359abbf1a6a'),
    'source-v1/test_objective_prefix_compiler.py': (20709, '17a63c33ef978feceb851d962b6f1225dd2ad6eea68fae7dfc84265ef25c15d0'),
    'candidate-interface.json': (11251, '06d0d8a7168ba1c94956872bf347c7e29487b389db0a865e58e5cf7879e4a8a6'),
    'source-model-obligations-01.json': (15064, 'e7152c9b0227f35821425c2b7180a8a65f943ea86935f9650a0313aa5f17aab4'),
}


def need(condition, description):
    if condition is not True:
        raise ValueError(description)


def read_pin(path, size, digest):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), 'regular non-symlink input required')
    need(path.stat().st_size == size and size <= 262144, 'exact bounded input size')
    raw = path.read_bytes()
    need(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, 'exact input SHA256')
    return raw


def descriptor(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def ast_digest(node):
    return hashlib.sha256(ast.dump(node, annotate_fields=True, include_attributes=False).encode()).hexdigest()


def source_record(node, source, path, role):
    segment = ast.get_source_segment(source, node)
    raw = segment.encode('utf-8')
    return {'ast_dump': ast.dump(node, annotate_fields=True, include_attributes=False),
            'ast_path': path, 'ast_sha256': ast_digest(node), 'node_kind': type(node).__name__,
            'role': role, 'source_segment': segment, 'source_segment_utf8_bytes': len(raw),
            'source_segment_utf8_sha256': hashlib.sha256(raw).hexdigest(),
            'span': [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]}


def main():
    need(not OUT.exists(), 'exclusive new receipt')
    census = sorted(str(path.relative_to(SCOPE)) for path in SCOPE.rglob('*') if path.is_file())
    need(census == sorted(EXPECTED), 'exact four-file draft census')
    need(not any(path.is_symlink() for path in SCOPE.rglob('*')), 'no candidate symlinks')
    raws = {name: read_pin(SCOPE / name, *pin) for name, pin in EXPECTED.items()}
    need(sum(map(len, raws.values())) == 87646, 'complete draft bytes')
    interface = json.loads(raws['candidate-interface.json'])
    obligations = json.loads(raws['source-model-obligations-01.json'])
    input_pins = interface['immutable_input_pins']
    immutable_raws = {name: read_pin(row['path'], row['bytes'], row['sha256'])
                      for name, row in input_pins.items()}
    compiler_ast = ast.parse(raws['source-v1/objective_prefix_compiler.py'].decode('utf-8'))
    tests_ast = ast.parse(raws['source-v1/test_objective_prefix_compiler.py'].decode('utf-8'))
    imports = sorted(alias.name for node in ast.walk(compiler_ast)
                     if type(node) is ast.Import for alias in node.names)
    need(imports == ['ast', 'hashlib', 'json', 're'], 'pure compiler import set')
    need(not any(type(node) is ast.ImportFrom for node in ast.walk(compiler_ast)), 'no compiler from imports')
    forbidden = {'eval', 'exec', 'open', '__import__', 'compile', 'subprocess', 'os', 'socket', 'requests', 'torch'}
    need(not any(type(node) is ast.Name and node.id in forbidden for node in ast.walk(compiler_ast)),
         'no compiler file/eval/process/project/model capability names')
    definitions = {node.name: node for node in compiler_ast.body if type(node) is ast.FunctionDef}
    need(set(interface['public_API']).issubset(definitions), 'all documented public functions exist')
    control_names = [node.name for node in tests_ast.body
                     if type(node) is ast.FunctionDef and node.name.startswith('test_')]
    planned = obligations['meaningful_controls']
    need(len(control_names) == len(planned) == 20, 'exact twenty unexecuted control groups')
    need(control_names == [row['test'] for row in planned] and
         [row['group'] for row in planned] == list(range(1, 21)), 'control names/order match sidecar')
    for document in (interface, obligations):
        need(all(document[key] is False for key in
                 ('proof_authority', 'formalization_authority', 'execution_authority', 'mutation_authority',
                  'completion_authority', 'omission_authority', 'strict_cache_admission', 'planner_activation',
                  'theorem_qualified', 'typed_Lean_SourcePrefix_exists', 'whole_IR_semantic_preservation_proved',
                  'python_ranker_source_equivalence_proved', 'full_objective_semantics_proved',
                  'full_gradient_semantics_proved', 'Python_Float_semantics_proved',
                  'Python_libm_semantics_proved', 'CPython_math_fsum_semantics_proved',
                  'optimizer_source_convergence_proved', 'global_autoencoder_convergence_proved')),
             'no proof or broader authority claim')
        need(document['all32_governing_RPI_exits'] == 'OPEN' and
             document['full_task_satisfaction'] == 'unknown', 'broad exits remain open')
        need(all(type(value) is int and value == 0 for value in document['actual_execution_in_this_scope'].values()),
             'draft actual execution counts zero')
    source = immutable_raws['original_source'].decode('utf-8')
    module = ast.parse(source)
    bindings = json.loads(immutable_raws['P7_source_bindings'])
    need(ast_digest(module) == bindings['module_ast_sha256'] ==
         '61ae9578f4a087b1b181af6fe4f78c3d811bbaa09368f833f6240384d085407b', 'full module AST pin')
    objective, dot, l2 = module.body[24], module.body[23], module.body[11]
    need(type(objective) is ast.FunctionDef and objective.name == '_objective' and len(objective.body) == 7,
         'all seven actual objective statements retained as context')
    expected_objective = source_record(objective, source, 'module.body[24]', 'whole_context_pin_only')
    expected_dot = source_record(dot, source, 'module.body[23]',
        'existing Q4 admitted callee source; future inlining must join actual literal and all lexical names')
    expected_l2 = source_record(l2, source, 'module.body[11]',
        'exact literal source binding; float-to-exact-real projection only')
    numerator, denominator = l2.value.value.as_integer_ratio()
    expected_l2['literal_exact_ratio'] = {'numerator': str(numerator), 'denominator': str(denominator)}
    need((numerator, denominator) == (5764607523034235, 576460752303423488), 'actual binary literal ratio')
    need(bindings['objective'] == expected_objective and bindings['dot_callee'] == expected_dot and
         bindings['source_L2'] == expected_l2, 'actual same-buffer whole context records')
    names = ('margins', 'data', 'regularizer', 'factors', 'gradient')
    assignments = dict(zip(names, objective.body[:5]))
    gradient = assignments['gradient'].value.elt
    generator = gradient.right.left.args[0]
    components = {'margin_body': assignments['margins'].value.elt,
        'loss_body': assignments['data'].value.left.args[0].elt,
        'loss_denominator': assignments['data'].value.right,
        'regularizer_body': assignments['regularizer'].value,
        'factor_body': assignments['factors'].value.elt, 'gradient_coordinate': gradient,
        'gradient_denominator': gradient.right.right, 'gradient_sum_body': generator.elt,
        'gradient_sum_zip': generator.generators[0].iter,
        'coordinate_range': assignments['gradient'].value.generators[0].iter}
    records = {name: source_record(objective.body[index], source, 'module.body[24].body[' + str(index) + ']',
                                 'numeric_prefix_candidate') for index, name in enumerate(names)}
    for index, name in ((5, 'nonfinite_guard'), (6, 'return_tuple')):
        records[name] = source_record(objective.body[index], source, 'module.body[24].body[' + str(index) + ']',
                                    'context_only_not_accepted_in_first_stage')
    records.update({name: source_record(node, source, 'under module.body[24] / ' + name,
                                      'exact_AST_component_candidate') for name, node in components.items()})
    need(len(records) == 17 and records == bindings['bindings'], 'independent same-buffer all17 AST/span/segment joins')
    for name, row in input_pins.items():
        need(read_pin(row['path'], row['bytes'], row['sha256']) == immutable_raws[name], 'all immutable inputs unchanged')
    for name, pin in EXPECTED.items():
        need(read_pin(SCOPE / name, *pin) == raws[name], 'all four candidate inputs unchanged')
    findings = [
        {'id': 'Q7-STRUCTURED-REFUSAL-01', 'severity': 'medium',
         'status': 'OPEN_REQUIRES_FRESH_SOURCE_REVISION',
         'scope': 'unbound optional mutation helper only; pinned original parsed-source path unaffected',
         'location': 'source-v1/objective_prefix_compiler.py:_ast_bounds;_Lowerer.comprehension;_Lowerer.lower',
         'reason': 'AST field presence and primitive bounds do not validate expected per-field container type; None is universally admitted, then lowering can raise TypeError rather than CompileRefusal.',
         'source_only_examples_not_executed': [
             "ast.ListComp(elt=ast.Constant(value=0), generators=None) -> len(node.generators)",
             "ast.Call(func=ast.Name(id='abs', ctx=ast.Load()), args=None, keywords=[]) -> iteration of node.args",
             "ast.IfExp(test=ast.Compare(left=ast.Name(id='z', ctx=ast.Load()), ops=None, comparators=[]), body=ast.Constant(value=1), orelse=ast.Constant(value=2)) -> len(test.ops)"],
         'required_control_change': 'extend existing control07 or control19 to invalid required-list field types and require CompileRefusal, preserving exactly20 groups'},
        {'id': 'Q7-STRUCTURED-REFUSAL-02', 'severity': 'medium',
         'status': 'OPEN_REQUIRES_FRESH_SOURCE_REVISION',
         'scope': 'optional l2_literal accepted by unbound lower_generic_expression; pinned-source parser supplies valid literal',
         'location': 'source-v1/objective_prefix_compiler.py:_Lowerer.__init__',
         'reason': 'Optional l2_literal lacks _ast_bounds/required-field validation before .value access; exact standard ast.Constant() can raise AttributeError.',
         'source_only_examples_not_executed': ["lower_generic_expression(ast.Name(id='z', ctx=ast.Load()), {'z': {'kind': 'scalar'}}, l2_literal=ast.Constant())"],
         'required_control_change': 'validate/bound optional literal AST before access and add missing-field control inside existing group'}]
    receipt = {'schema': 'ranker-objective-container-prefix-independent-source-review@1',
        'status': 'source_only_review_completed_with_material_helper_refusal_gaps',
        'findings': findings, 'all_findings_are_source_inferences_without_candidate_execution': True,
        'candidate_scope': str(SCOPE), 'candidate_files': 4, 'candidate_bytes': 87646,
        'candidate_pins': [descriptor(SCOPE / name, raws[name]) for name in sorted(raws)],
        'immutable_input_pins_verified_before_after': input_pins,
        'same_buffer_independent_AST_record_join': {'module': True, 'objective_statement_count': 7,
            'numeric_prefix_statement_count': 5, 'context_only_suffix': ['nonfinite_guard', 'return_tuple'],
            'binding_records': 17, 'actual_dot_callee': True, 'actual_L2_binary_ratio': expected_l2['literal_exact_ratio']},
        'source_review_positive_findings': [
            'only bounded caller-owned buffers; compiler imports ast/hashlib/json/re without file/eval/process/model capabilities',
            'fixed full source/P7 hashes cannot be rebound by caller; whole module/objective/callee/L2 and all17 records rejoin',
            'actual _dot AST is lowered under substituted argument scope into generic zip/scalar/ordered sum, not a dot opcode',
            'five ordered assignments retain source scalar syntax and coordinate roles; generic zip uses minimum lengths',
            'prospective original admission4x80 is distinct from generic helpers and full Python runtime/finite-guard semantics',
            'actual L2 is binary64 exact rational, not1/100; bit256 budget excludes some finite binary64 inputs explicitly',
            'both scalar branch syntaxes lower; proposed evaluation policy is selected branch only, with no semantic-proof claim',
            'JSON renderer bounds input and independently reextracts same source/bindings, then compares complete canonical receipt',
            'exactly20 authored control names align with obligation groups; tests remain unimported and unexecuted',
            'draft JSON only, no typed Lean SourcePrefix, preservation/objective/gradient/Float/training/task/convergence authority'],
        'recommended_next_step': 'fresh v2 source/test/sidecars preserving v1; independently review narrow schema/literal changes before root-owned bounded controls',
        'source_review_authorizes_candidate_execution': False,
        'actual_review_counts': {'candidate_AST_syntax_parses': 2, 'original_source_AST_parse_calls': 1,
            'compiler_imports': 0, 'compiler_calls': 0, 'renderer_calls': 0, 'source_function_execution_calls': 0,
            'tests_imported': 0, 'control_groups_executed': 0, 'native_jobs': 0, 'model_jobs': 0,
            'training_jobs': 0, 'metadata_jobs': 0, 'remote_jobs': 0, 'Git_jobs': 0},
        'qualified_native_checks': 0, 'qualified_theorem_queries': 0,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown',
        'proof_authority': False, 'formalization_authority': False, 'execution_authority': False,
        'mutation_authority': False, 'completion_authority': False, 'omission_authority': False,
        'planner_activation': False, 'strict_cache_admission': False,
        'producer_pin': descriptor(Path(__file__).resolve(), Path(__file__).read_bytes())}
    raw = (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('utf-8')
    with OUT.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'path': str(OUT), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'status': receipt['status'], 'findings': len(findings)}))


if __name__ == '__main__':
    main()
