#!/usr/bin/python3.12
"""File-only independent review of a draft, unqualified container IR plan.

No project module import, source function execution, test/native/model job,
metadata hydration, network operation, or qualification is performed here.
The only output is an exclusive source-review receipt in this review directory.
"""

import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path('/home/barberb/lift_coding')
PLAN_ROOT = ROOT / 'qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01'
REVIEW_ROOT = ROOT / 'maintenance/ranker-objective-container-plan-review-20261005-01'
Q5 = ROOT / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PINS = {
    'source-bindings.json': (25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'),
    'ir-interface.json': (6114, 'fa017de5018525c8853cb847fefb416f18fea99b66273f3e3a57c67b6e4ed5d8'),
    'source-plan.json': (17263, 'bb53075335968870fa9a2d0ca15c7d6d574f4e032343b598678bb907d4fd1ece'),
}
SOURCE_PIN = (16391, '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a')
Q5_SEAL_PIN = (86066, '874b51a3358dee5dbd18b70c66770f4e3fdf3553c2fac3fb644075c37273f43d')
Q5_REVIEW_PIN = (11167, '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00')
FALSE_BOUNDARIES = [
    'CPython_math_fsum_semantics_proved', 'Python_Float_semantics_proved',
    'Python_libm_semantics_proved', 'completion_authority', 'execution_authority',
    'formalization_authority', 'full_gradient_semantics_proved',
    'full_objective_semantics_proved', 'full_preparation_semantics_proved',
    'full_training_semantics_proved', 'global_autoencoder_convergence_proved',
    'host_parser_correctness_theorem_proved', 'mutation_authority',
    'omission_authority', 'optimizer_source_convergence_proved',
    'planner_activation', 'proof_authority', 'python_ranker_source_equivalence_proved',
    'strict_cache_admission', 'theorem_qualified',
    'whole_IR_semantic_preservation_proved',
]


def require(value, label):
    if not value:
        raise ValueError(label)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def descriptor(path, blob=None):
    p = Path(path)
    if blob is None:
        require(p.is_file() and not p.is_symlink(), 'regular nonsymlink input: ' + str(p))
        blob = p.read_bytes()
    return {'path': str(p), 'bytes': len(blob), 'sha256': digest(blob)}


held = {}


def pin(desc):
    require(type(desc) is dict and set(desc) == {'path', 'bytes', 'sha256'}, 'descriptor keys')
    p = Path(desc['path'])
    require(p.is_absolute() and p.is_file() and not p.is_symlink(), 'absolute regular input: ' + str(p))
    blob = p.read_bytes()
    require(descriptor(p, blob) == desc, 'input pin mismatch: ' + str(p))
    previous = held.setdefault(str(p), desc)
    require(previous == desc, 'conflicting descriptors: ' + str(p))
    return blob


def fixed(path, pair):
    return pin({'path': str(path), 'bytes': pair[0], 'sha256': pair[1]})


def parse_json(blob):
    def unique(items):
        output = {}
        for key, value in items:
            require(key not in output, 'duplicate JSON field: ' + key)
            output[key] = value
        return output
    return json.loads(blob, object_pairs_hook=unique)


def ast_hash(node):
    return digest(ast.dump(node, include_attributes=False).encode())


def check_binding(node, claim, source_text, ast_path, role):
    segment = ast.get_source_segment(source_text, node)
    require(type(segment) is str, 'source segment exists')
    raw_segment = segment.encode()
    actual = {
        'ast_dump': ast.dump(node, include_attributes=False),
        'ast_path': ast_path,
        'ast_sha256': ast_hash(node),
        'node_kind': type(node).__name__,
        'role': role,
        'source_segment': segment,
        'source_segment_utf8_bytes': len(raw_segment),
        'source_segment_utf8_sha256': digest(raw_segment),
        'span': [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset],
    }
    require(claim == actual, 'AST binding differs: ' + ast_path)


def declaration_line(blob, full_name, line):
    text = blob.decode()
    lines = text.splitlines()
    leaf = full_name.rsplit('.', 1)[-1]
    require(0 < line <= len(lines), 'declaration source line bound')
    require(re.search(r'\b(?:theorem|def|lemma|abbrev)\s+' + re.escape(leaf) + r'\b', lines[line - 1]),
            'source declaration at recorded line: ' + full_name)
    namespace = full_name.rsplit('.', 1)[0]
    require(re.search(r'^namespace\s+' + re.escape(namespace) + r'\s*$', text, re.M),
            'declaration namespace exists: ' + full_name)
    return {'name': full_name, 'line': line, 'source_line': lines[line - 1]}


def main():
    documents = {name: parse_json(fixed(PLAN_ROOT / name, pair)) for name, pair in PINS.items()}
    bindings = documents['source-bindings.json']
    interface = documents['ir-interface.json']
    plan = documents['source-plan.json']
    require(bindings['schema'] == 'ranker-objective-container-source-bindings@1', 'binding schema')
    require(interface['schema'] == 'ranker-objective-container-IR-interface-plan@1', 'interface schema')
    require(plan['schema'] == 'ranker-objective-container-source-plan@1', 'plan schema')
    for document in documents.values():
        require(document['status'] == 'draft_unqualified_source_only_plan', 'draft status')
        require(all(document[key] is False for key in FALSE_BOUNDARIES), 'false authorities and proof boundaries')
        require(document['all32_governing_RPI_exits'] == 'OPEN', 'all governing exits open')
        require(document['full_task_satisfaction'] == 'unknown', 'task satisfaction unknown')
        require(document['official_benchmark_score'] is None, 'no official score')
    require(plan['binding_document'] == 'source-bindings.json', 'binding filename')
    require(plan['interface_document'] == 'ir-interface.json', 'interface filename')
    require(plan['binding_document_pin'] == held[str(PLAN_ROOT / 'source-bindings.json')], 'binding join')
    require(plan['interface_document_pin'] == held[str(PLAN_ROOT / 'ir-interface.json')], 'interface join')

    source_descriptor = bindings['source']
    require((source_descriptor['bytes'], source_descriptor['sha256']) == SOURCE_PIN, 'fixed source pin')
    require(source_descriptor == plan['source'], 'plan source join')
    source_blob = pin(source_descriptor)
    source_text = source_blob.decode()
    # Parse the same bytes twice, without evaluating any part of the module.
    module = ast.parse(source_text, filename=source_descriptor['path'])
    second_module = ast.parse(source_text, filename=source_descriptor['path'])
    require(ast_hash(module) == ast_hash(second_module) == bindings['module_ast_sha256'], 'whole module AST')
    objective = module.body[24]
    dot = module.body[23]
    l2 = module.body[11]
    require(isinstance(objective, ast.FunctionDef) and objective.name == '_objective', 'objective exact location')
    require(isinstance(dot, ast.FunctionDef) and dot.name == '_dot', 'dot exact location')
    require([x.arg for x in objective.args.args] == ['weights', 'differences'], 'objective parameters')
    require([x.arg for x in dot.args.args] == ['a', 'b'], 'dot parameters')
    require(len(objective.body) == 7 == bindings['statement_count'] == plan['source_objective_statement_count'],
            'seven source statements')
    require(bindings['numeric_prefix_statement_count'] == plan['numeric_prefix_statement_count'] == 5,
            'five numeric prefix statements')
    assignment_names = ['margins', 'data', 'regularizer', 'factors', 'gradient']
    require(all(isinstance(n, ast.Assign) and len(n.targets) == 1 and
                isinstance(n.targets[0], ast.Name) and n.targets[0].id == assignment_names[i]
                for i, n in enumerate(objective.body[:5])), 'ordered source assignments')
    check_binding(objective, bindings['objective'], source_text, 'module.body[24]', 'whole_context_pin_only')
    check_binding(dot, bindings['dot_callee'], source_text, 'module.body[23]',
                  'existing Q4 admitted callee source; future inlining must join actual literal and all lexical names')
    l2_claim = dict(bindings['source_L2'])
    ratio = l2_claim.pop('literal_exact_ratio')
    check_binding(l2, l2_claim, source_text, 'module.body[11]',
                  'exact literal source binding; float-to-exact-real projection only')
    require(isinstance(l2, ast.Assign) and len(l2.targets) == 1 and l2.targets[0].id == 'L2'
            and isinstance(l2.value, ast.Constant) and type(l2.value.value) is float, 'source L2 literal')
    numerator, denominator = l2.value.value.as_integer_ratio()
    require(ratio == {'numerator': str(numerator), 'denominator': str(denominator)}
            == {'numerator': '5764607523034235', 'denominator': '576460752303423488'}, 'binary64 literal exact ratio')
    require(interface['fixed_admitted_domain']['source_L2_exact_ratio'] == ratio, 'interface L2 join')

    nodes = {name: objective.body[i] for i, name in enumerate(assignment_names)}
    nodes.update({'nonfinite_guard': objective.body[5], 'return_tuple': objective.body[6]})
    margins, data, regularizer, factors, gradient = [n.value for n in objective.body[:5]]
    gradient_sum = gradient.elt.right.left.args[0]
    nodes.update({
        'margin_body': margins.elt,
        'loss_body': data.left.args[0].elt,
        'loss_denominator': data.right,
        'regularizer_body': regularizer,
        'factor_body': factors.elt,
        'gradient_coordinate': gradient.elt,
        'gradient_denominator': gradient.elt.right.right,
        'gradient_sum_body': gradient_sum.elt,
        'gradient_sum_zip': gradient_sum.generators[0].iter,
        'coordinate_range': gradient.generators[0].iter,
    })
    require(set(nodes) == set(bindings['bindings']) and len(nodes) == 17, 'all source component bindings')
    for name, node in nodes.items():
        if name in assignment_names:
            path, role = 'module.body[24].body[' + str(assignment_names.index(name)) + ']', 'numeric_prefix_candidate'
        elif name in ['nonfinite_guard', 'return_tuple']:
            path = 'module.body[24].body[' + str(5 if name == 'nonfinite_guard' else 6) + ']'
            role = 'context_only_not_accepted_in_first_stage'
        else:
            path, role = 'under module.body[24] / ' + name, 'exact_AST_component_candidate'
        check_binding(node, bindings['bindings'][name], source_text, path, role)
    require(all(len(n.generators) == 1 and not n.generators[0].ifs and n.generators[0].is_async == 0
                for n in [margins, data.left.args[0], factors, gradient, gradient_sum]),
            'source comprehensions are single synchronous unfiltered generators')
    require(isinstance(gradient.elt.op, ast.Sub), 'gradient subtraction retained')
    require(ast.dump(data.right) == "Call(func=Name(id='len', ctx=Load()), args=[Name(id='margins', ctx=Load())], keywords=[])",
            'data divisor is source len(margins)')
    require(ast.dump(gradient.elt.right.right) == "Call(func=Name(id='len', ctx=Load()), args=[Name(id='differences', ctx=Load())], keywords=[])",
            'gradient divisor is source len(differences)')
    require(ast.dump(gradient_sum.generators[0].iter) == "Call(func=Name(id='zip', ctx=Load()), args=[Name(id='factors', ctx=Load()), Name(id='differences', ctx=Load())], keywords=[])",
            'source zip factor/row order')
    require(ast.dump(gradient.generators[0].iter) == "Call(func=Name(id='range', ctx=Load()), args=[Call(func=Name(id='len', ctx=Load()), args=[Name(id='weights', ctx=Load())], keywords=[])], keywords=[])",
            'source ascending coordinate range')
    require(ast.dump(module.body[3]) == "Import(names=[alias(name='math')])", 'pinned math module import')
    require(sum(isinstance(n, ast.FunctionDef) and n.name == '_dot' for n in module.body) == 1,
            'single top level dot definition')
    require(sum(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'L2' for t in n.targets)
                for n in module.body) == 1, 'single top level L2 assignment')

    ret = objective.body[6].value
    require(isinstance(ret, ast.Tuple) and len(ret.elts) == 2 and isinstance(ret.elts[0], ast.Dict), 'source tuple/dict shape')
    key_order = [k.value for k in ret.elts[0].keys]
    require(key_order == ['objective', 'pair_logistic_loss', 'L2_penalty', 'gradient_norm'], 'source dictionary keys')
    require(bindings['return_schema_context_only'] == {
        'compiled_first_stage': False, 'dictionary_key_order': key_order,
        'second_component_AST_sha256': ast_hash(ret.elts[1]), 'second_component_name': 'gradient', 'tuple_arity': 2,
    }, 'return context descriptor')
    require(interface['return_schema_boundary']['source_dict_keys_in_order'] == key_order
            and interface['return_schema_boundary']['source_python_tuple_arity'] == 2
            and interface['return_schema_boundary']['second_component'] == 'gradient'
            and interface['return_schema_boundary']['prefix_output_is_source_return_schema'] is False,
            'return remains context only')

    domain = interface['fixed_admitted_domain']
    require(domain == {
        'difference_row_coordinates': 80, 'difference_rows': 4,
        'domain_enforced_in_new_host_frontend': False, 'exact_real_coordinates': True,
        'is_CPython_runtime_contract': False, 'source_L2_exact_ratio': ratio, 'weights_coordinates': 80,
    }, 'prospective domain explicitly not source runtime contract')
    constructors = interface['proposed_generic_constructors']
    names = [item['name'] for item in constructors]
    require(names == ['var', 'letBind', 'scalarLiteral', 'scalarOp', 'mapVector', 'mapRows', 'zipMap',
                      'zipRowsMap', 'fsumExact', 'length', 'natToScalar', 'indexVector', 'rangeMap', 'prefixRecord'],
            'closed generic constructor proposal')
    forbidden = ['objective', 'gradient', 'logisticLoss', 'sigmoid', 'dot', 'descent', 'convergence']
    require(interface['forbidden_high_level_opcodes'] == forbidden and not set(names).intersection(forbidden),
            'no high level desired-result opcode')
    by_name = {item['name']: item for item in constructors}
    require(by_name['scalarOp']['operators'] == ['add', 'sub', 'mul', 'div', 'neg', 'abs', 'max', 'exp', 'log1p', 'ifNonneg'],
            'generic scalar operation list')
    require('minimum-length truncation' in by_name['zipMap']['semantics']
            and 'min(n,m)' in by_name['zipMap']['signature']
            and 'min(n,r)' in by_name['zipRowsMap']['signature'], 'generic zip truncation preserved')
    require('ascending ordered exact-real addition fold' in by_name['fsumExact']['semantics']
            and 'no CPython math.fsum theorem' in by_name['fsumExact']['semantics'], 'fsum projection boundary')
    require('ascending 0..n-1' in by_name['rangeMap']['semantics'], 'range order')
    errors = {item['name']: item['kind'] for item in interface['errors']}
    require('empty mean is an error' in errors['divisionByZero']
            and 'not a claimed original Python check' in errors['shapeMismatch']
            and 'external binary64-to-rational admission guard only' in errors['nonfiniteInput'],
            'division/shape/nonfinite boundaries')
    require('syntax eager in both branches, evaluation lazy in selected branch' in by_name['scalarOp']['domain'],
            'syntax validation distinct from branch evaluation')
    require('after all five numerical assignments' in interface['source_guard_boundary']
            and 'No preprocessing/error-order equivalence claim' in interface['source_guard_boundary'], 'finite guard order open')
    require('must refuse at _need/math.isfinite' in interface['first_stage_API']['full_objective_entrypoint']
            and 'never silently skip unsupported statements' in interface['first_stage_API']['full_objective_entrypoint'],
            'no whole function acceptance')

    forms = plan['planned_intermediate_forms']
    require([item['source_binding'] for item in forms] == assignment_names, 'ordered proposed bindings')
    require(forms[0]['candidate_form'] == 'let margins = mapRows(differences, row => fsumExact(zipMap(weights,row,(x,y)=>mul(x,y))))',
            'margin generic inlining proposal')
    require(forms[1]['candidate_form'] == 'let data = div(fsumExact(mapVector(margins,z=>actual emitted stable-loss scalar tree)),natToScalar(length(margins)))',
            'data mean uses original margin length')
    require(forms[2]['candidate_form'] == 'let regularizer = div(mul(actual_L2_ratio,fsumExact(zipMap(weights,weights,(x,y)=>mul(x,y)))),num(2))',
            'regularizer keeps mul/div source order')
    require(forms[3]['candidate_form'] == 'let factors = mapVector(margins,z=>actual emitted sign-split factor scalar tree)',
            'factors use emitted scalar syntax')
    require(forms[4]['candidate_form'] == 'let gradient = rangeMap(length(weights),i=>sub(mul(actual_L2_ratio,indexVector(weights,i)),div(fsumExact(zipRowsMap(factors,differences,(f,row)=>mul(f,indexVector(row,i)))),natToScalar(length(differences)))))',
            'gradient generic source tree and original divisor')
    require('derive factor/difference equal lengths and every row index bound' in forms[4]['nonzero_domain'],
            'indexed zip specialization obligations')
    require(len(plan['draft_native_queries']) == 11 and len(plan['meaningful_control_plan']) == 20
            and plan['control_plan_case_count'] == 20, 'proposed query/control counts')
    require(all(q['status'] == 'unimplemented_unqualified' for q in plan['draft_native_queries']), 'all proposed queries unqualified')
    require(len({q['name'] for q in plan['draft_native_queries']}) == 11, 'query names distinct')
    compiler_query = plan['draft_native_queries'][0]
    require('compile acceptance and typed environment only' in compiler_query['premise_policy']
            and 'no objective/gradient/desired equality premise' in compiler_query['premise_policy'], 'compiler noncircular premises')
    require(plan['circular_premises_forbidden'] == [
        'assume source objective equals mathematical objective',
        'assume source computed gradient equals model gradient',
        'assume loss contraction or convergence', 'assume Python finite guard preservation',
    ], 'noncircular projection policy')
    require(any(q['statement'] == 'meanExact([])=error divisionByZero' for q in plan['draft_native_queries']), 'planned empty mean refusal')
    controls = plan['meaningful_control_plan']
    require(len({c['case'] for c in controls}) == 20, 'control cases distinct')
    require(any('unequal generic zip' in c['case'] and 'min-length result' in c['expected'] for c in controls), 'planned unequal zip control')
    require(any('zero rows' in c['case'] and 'divisionByZero' in c['expected'] for c in controls), 'planned empty mean control')
    require(any('constant0' in c['case'] and 'CompileRefusal' in c['expected'] for c in controls), 'planned semantic gradient mutation control')
    require(any('NaN/inf' in c['case'] and 'source Float/libm behavior remains open' in c['expected'] for c in controls), 'finite-domain control boundary')
    require(any('wide/cyclic AST' in c['case'] and 'bounded refusal' in c['expected'] for c in controls), 'bounded AST control')
    require(plan['actual_control_cases_executed'] == plan['actual_native_jobs_executed'] == plan['actual_source_function_executions'] == 0,
            'zero claimed candidate execution')
    require(plan['actual_source_AST_parse_calls_for_plan_binding_collection'] == 2
            and bindings['binding_collection_AST_parse_calls'] == bindings['same_source_buffer_AST_parse_calls'] == 2,
            'plan author reports two same-buffer parses')
    require(bindings['source_function_execution_calls'] == bindings['new_native_jobs'] == bindings['new_training_jobs'] == 0,
            'binding collection has zero job/execution claims')
    step = plan['minimal_next_isolated_bounded_step']
    require(step['cap_change_authorized'] is False and step['existing_frozen_dependency_profile_only'] is True
            and step['native_wall_seconds'] == step['native_cpu_seconds'] == 20
            and step['native_per_file_capture_bytes'] == 65536 and step['native_workspace_bytes'] == 16777216,
            'prospective native caps unchanged')

    math_apis = []
    for item in plan['existing_source_backed_math']:
        blob = pin(item['file'])
        declaration = declaration_line(blob, item['declaration'], item['source_line'])
        declaration['file'] = item['file']
        math_apis.append(declaration)
    list_apis = []
    for item in plan['source_backed_list_APIs']:
        blob = pin(item['file'])
        for declaration in item['declarations']:
            if declaration['name'] == 'List.sum_ofFn':
                lines = blob.decode().splitlines()
                line = declaration['line']
                require(lines[line - 1].strip() == '@[to_additive]' and lines[line].startswith('theorem prod_ofFn'),
                        'sum_ofFn comes from source to_additive declaration')
                require('namespace List' in blob.decode(), 'List to_additive namespace')
                record = {'name': 'List.sum_ofFn', 'line': line, 'source_line': lines[line - 1],
                          'source_basis': 'to_additive on prod_ofFn; source declaration check only, no new kernel invocation'}
            else:
                record = declaration_line(blob, declaration['name'], declaration['line'])
            record['file'] = item['file']
            list_apis.append(record)

    existing_checks = []
    for item in plan['existing_actual_leaf_qualifications']:
        check = parse_json(pin(item['check_result']))
        require(check['status'] == 'passed' and check['native_lean_returncode'] == 0
                and check['native_invocations'] == check['native_lean_invocations'] == 1,
                'existing check receipt acceptance')
        outputs = check['theorem_axiom_output']
        require(len(outputs) == item['query_count'] and len({q['theorem'] for q in outputs}) == item['query_count'],
                'existing leaf query counts')
        require(all(q['report_occurrences'] == 2 and set(q['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'}
                    for q in outputs), 'existing allowed leaf axioms')
        existing_checks.append({'module': item['module'], 'receipt': item['check_result'],
                                'reported_existing_queries': item['query_count'], 'new_invocations_by_reviewer': 0})
    require([c['reported_existing_queries'] for c in existing_checks] == [5, 9], 'existing leaf qualifications separate from draft queries')

    seal = parse_json(fixed(Q5 / 'file-only-seal-01.json', Q5_SEAL_PIN))
    review = parse_json(fixed(Q5 / 'qualified-review-01.json', Q5_REVIEW_PIN))
    require(seal['regular_file_count'] == 276 and seal['regular_file_bytes'] == 78794802
            and len(seal['files']) == 276 and seal['fixture_symlinks'] == seal['excluded_dependency_roots'] == [], 'unchanged Q5 seal scope')
    require(review['status'] == 'passed' and review['qualified_theorem_queries'] == 14
            and review['pure_test_cases'] == 98 and review['metadata_payloads'] == 4458, 'prior Q5 evidence remains separate')
    for desc in seal['files']:
        path = Path(desc['path'])
        require(path.is_relative_to(Q5), 'Q5 sealed leaf path')
        pin(desc)
    require(sum(d['bytes'] for d in seal['files']) == 78794802, 'complete Q5 sealed byte count')
    for path, desc in held.items():
        require(descriptor(path) == desc, 'held input changed during review: ' + path)

    receipt = {
        'schema': 'ranker-objective-container-independent-plan-source-review@1',
        'status': 'passed_source_only_draft_plan_review',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'producer': descriptor(Path(__file__).absolute()),
        'reviewed_plan_sources': [held[str(PLAN_ROOT / name)] for name in PINS],
        'pinned_original_source': source_descriptor,
        'review_scope': 'three draft plan JSON files and their pinned local source dependencies; no candidate implementation or qualification',
        'exact_source_binding_review': {
            'module_AST_sha256': bindings['module_ast_sha256'],
            'objective_AST_sha256': bindings['objective']['ast_sha256'],
            'dot_callee_AST_sha256': bindings['dot_callee']['ast_sha256'],
            'source_L2_exact_ratio': ratio,
            'numeric_assignment_count': 5, 'whole_objective_statement_count': 7,
            'component_binding_count': 17, 'all_AST_dumps_spans_and_source_segment_pins_match': True,
            'data_divisor_source_len_margins_retained': True,
            'gradient_divisor_source_len_differences_retained': True,
            'gradient_subtraction_zip_binder_order_and_coordinate_range_retained': True,
            'whole_module_and_dot_context_pinned': True,
            'source_guard_and_return_schema_are_context_only': True,
        },
        'semantic_plan_review': {
            'generic_constructor_names': names,
            'no_objective_gradient_dot_or_convergence_opcode': True,
            'zip_shorter_length_behavior_retained': True,
            'equal_shape_specializations_require_derivation': True,
            'empty_mean_refusal_is_planned_not_executed': True,
            'fsumExact_is_ordered_exact_real_fold_only': True,
            'binary64_L2_literal_projected_as_exact_ratio': True,
            'fixed_4x80_domain_is_prospective_and_not_source_Python_validation': True,
            'scalar_syntax_eager_and_branch_evaluation_lazy_policy_retained': True,
            'compiler_and_gradient_projection_query_sketches_have_no_desired_identity_premise': True,
            'native_query_sketch_count': 11, 'planned_control_case_count': 20,
            'all_new_queries_unimplemented_and_unqualified': True,
            'forms_and_statements_are_plan_sketches_not_compiled_Lean_or_emitted_IR': True,
            'new_host_compiler_and_typed_container_core_implemented': False,
            'whole_function_guard_return_sqrt_and_error_timing_remain_open': True,
            'full_source_Float_training_AE_task_convergence_remain_open': True,
        },
        'pinned_math_declaration_source_checks': math_apis,
        'pinned_list_API_source_checks': list_apis,
        'existing_leaf_evidence_receipt_joins': existing_checks,
        'unchanged_Q5_scope': {
            'seal': held[str(Q5 / 'file-only-seal-01.json')],
            'qualified_review': held[str(Q5 / 'qualified-review-01.json')],
            'complete_regular_leaves_body_rehashed': 276, 'complete_regular_leaf_bytes': 78794802,
            'existing_queries': 14, 'existing_pure_cases': 98, 'existing_metadata_rows': 4458,
            'no_Q5_file_modified_by_review': True,
        },
        'all_held_inputs_unchanged_after_file_only_review': True,
        'reviewer_same_source_buffer_AST_parse_calls': 2,
        'reviewer_source_function_executions': 0, 'reviewer_project_imports': 0,
        'reviewer_control_cases_executed': 0, 'reviewer_native_jobs': 0,
        'reviewer_model_training_jobs': 0, 'reviewer_metadata_jobs': 0,
        'reviewer_remote_or_Git_operations': 0,
        'outstanding_source_issues': [],
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown',
        'official_benchmark_score': None, 'proof_authority': False,
        'execution_authority': False, 'formalization_authority': False,
        'completion_authority': False, 'mutation_authority': False,
        'omission_authority': False, 'planner_activation': False,
        'strict_cache_admission': False, 'theorem_qualified': False,
        'whole_IR_semantic_preservation_proved': False,
        'python_ranker_source_equivalence_proved': False,
        'full_objective_semantics_proved': False, 'full_gradient_semantics_proved': False,
        'full_training_semantics_proved': False,
        'optimizer_source_convergence_proved': False, 'global_autoencoder_convergence_proved': False,
    }
    encoded = (json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n').encode()
    target = REVIEW_ROOT / 'review-receipt.json'
    require(REVIEW_ROOT.is_dir() and not REVIEW_ROOT.is_symlink(), 'owned review directory exists')
    with target.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps({'receipt': descriptor(target), 'status': receipt['status'], 'outstanding_source_issues': []}, sort_keys=True))


if __name__ == '__main__':
    main()
