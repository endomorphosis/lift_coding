"""Independent source/AST/JSON inspection only; never imports reviewed modules.

The reviewer binds the manually inspected candidate bytes, confirms inert API
and source-context joins, and records limits of the source review. It does not
run the candidate compiler, renderer, harness, tests, native checker or Git.
Only its sibling review-receipt.json is created, with exclusive creation.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PLAN = ROOT.with_name('ranker-objective-ir-source-plan-20261005-01')
PRIOR = ROOT.with_name('ranker-source-semantics-20261005-01')
REVIEW = WORKSPACE / 'maintenance/ranker-objective-ir-candidate-source-review-20261005-01'
EXPECTED = {
    'math/ObjectiveScalarIR.lean': (13094, 'ae4d1ebec782c2395cc9d2585f40296988fc2ec10cfdab3f946258251c527d71'),
    'prepare_request_01.py': (7043, '55206b57dc89973866f610f2f53032bb539f636db23be43997ae00474cbaeafd'),
    'run_objective_controls_01.py': (43354, '42db20ed326046ad9e2bc9666cc67494937dd3321a1b70ddb4f5618b8271d14f'),
    'freeze_source_profile_01.py': (8719, '194acc937634ffef66116be4256e9a1943df0a066333bd6150ff7c3249994323'),
    'freeze_objective_specification_01.py': (5155, 'e19f535e16983e733905f39b93bfbc2503e9e06343474291593de0c93fa39ae5'),
    'source-v2/objective_scalar_compiler.py': (33191, 'a9f4c93423c0f10e432e005ce4f8986e903706cf7ea5b493699633618519d9d9'),
    'source-v2/test_typed_slice_compiler.py': (18118, 'c18c4a95bde5da2c780a91bc77e1ad5358ebd30723087e11fb0a8b96448c35c1'),
    'source-snippets.json': (15471, '292c8e2ed9bbdad5de5bf8bd7c5a5fbcb79a3ff3dbb2565d363d123f9546b5cc'),
    'candidate-interface.json': (7386, '60b9ac3e6737db5406dd58be06c010ea07bb455c10ace450493b4fbb449d79ab'),
}
ARGUMENTS = {
    'expected_source_sha256': '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a',
    'expected_objective_ast_sha256': '129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2',
    'expected_stable_loss_ast_sha256': 'b71027e5d37d1a5b5b574a4b880a0857f0885dbc19c81dff3e652f8f7c76287e',
    'expected_stable_factor_ast_sha256': 'a5f60c17cb8efc0869ec1ac4001c04c1b43f67d7d38bc025cbb87061247d70aa',
}
DOCUMENTS = {
    'source_bindings': ('source-bindings.json', '5f76eed1e9b025c8e7bb61d23e368a4740b01f329c40472f0c77f2f909bd5c16'),
    'source_plan': ('source-plan.json', 'f0e712a1b78ba1a728f5f4a41a8d8f66540017ae86418e23f4bd3c40f6cce690'),
    'ir_interface': ('ir-interface.json', '53a6ba907b4ac64d79f88a97fb9b987a54d0b2efeb930cef798c249d483a6cd0'),
}
HELD = {}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def read(path, expected_sha=None, expected_bytes=None):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical regular review input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'bounded input required')
        pieces, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 32 * 1024**2, 'input grew beyond review read bound')
            pieces.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size,
             'input changed during bounded read')
        raw = b''.join(pieces)
        descriptor = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(expected_sha is None or descriptor['sha256'] == expected_sha, 'review input digest differs')
        need(expected_bytes is None or descriptor['bytes'] == expected_bytes, 'review input byte count differs')
        need(path not in HELD or HELD[path] == descriptor, 'repeated review input differs')
        HELD[path] = descriptor
        return raw, descriptor
    finally:
        os.close(fd)


def literal_assignment(tree, name):
    assignments = [node.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    need(len(assignments) == 1, 'unique inert literal assignment required: ' + name)
    return ast.literal_eval(assignments[0])


def functions(tree):
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def dump(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def ast_sha(node):
    return hashlib.sha256(dump(node).encode()).hexdigest()


def static_test_population(tree):
    literals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            try:
                literals[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    count, names = 0, []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith('test_'):
            continue
        names.append(node.name)
        cases = 1
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == 'parametrize':
                argument = decorator.args[1]
                values = literals[argument.id] if isinstance(argument, ast.Name) else ast.literal_eval(argument)
                cases *= len(values)
        count += cases
    return count, names


def main():
    raws, pins, trees = {}, {}, {}
    for name, (size, sha) in EXPECTED.items():
        raw, descriptor = read(ROOT / name, sha, size)
        raws[name], pins[name] = raw, descriptor
        if name.endswith('.py'):
            trees[name] = ast.parse(raw, filename=str(ROOT / name))
        elif name.endswith('.json'):
            json.loads(raw)
    documents, document_pins = {}, {}
    for role, (name, sha) in DOCUMENTS.items():
        raw, descriptor = read(PLAN / name, sha)
        documents[role], document_pins[role] = json.loads(raw), descriptor
    bindings = documents['source_bindings']
    need(bindings['schema'] == 'ranker-objective-source-ast-bindings@1', 'P6 binding schema differs')
    source_raw, source_pin = read(bindings['source']['path'], ARGUMENTS['expected_source_sha256'], 16391)
    need(source_pin == bindings['source'], 'P6 source descriptor differs')
    text = source_raw.decode()
    module = ast.parse(text, filename=source_pin['path'])
    objectives = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == '_objective']
    need(len(objectives) == 1, 'unique original objective required')
    objective = objectives[0]
    objective_index = module.body.index(objective)
    loss = objective.body[1].value.left.args[0].elt
    factor = objective.body[3].value.elt
    need(ast_sha(module) == bindings['module_ast_sha256'], 'complete original module AST differs')
    need(ast_sha(objective) == ARGUMENTS['expected_objective_ast_sha256'] == bindings['objective']['ast_dump_utf8_sha256'],
         'original function AST join differs')
    for role, node in [('stable_loss', loss), ('stable_factor', factor)]:
        need(ast_sha(node) == ARGUMENTS['expected_' + role + '_ast_sha256'] ==
             bindings['selected_scalar_leaves'][role + '_scalar']['ast_dump_utf8_sha256'], 'original leaf AST join differs')
    compiler = trees['source-v2/objective_scalar_compiler.py']
    driver = trees['run_objective_controls_01.py']
    spec_freezer = trees['freeze_objective_specification_01.py']
    need(literal_assignment(driver, 'OBJECTIVE_ARGUMENTS') == literal_assignment(spec_freezer, 'ARGUMENTS') == ARGUMENTS,
         'driver/spec/actual original source and AST pins differ')
    need(literal_assignment(driver, 'OBJECTIVE_DOCUMENTS') == literal_assignment(spec_freezer, 'DOCUMENTS') == DOCUMENTS,
         'driver/spec/P6 document pins differ')
    for name, value in {'MAX_SOURCE_BYTES': 262144, 'MAX_MODULE_NODES': 4096, 'MAX_SCALAR_NODES': 128,
                        'MAX_DEPTH': 32, 'MAX_INTEGER_BITS': 256, 'MAX_RECEIPT_BYTES': 65536}.items():
        need(type(literal_assignment(compiler, name)) is int and literal_assignment(compiler, name) == value,
             'frontend bound differs: ' + name)
    imports = [node for node in compiler.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    need({(node.names[0].name if isinstance(node, ast.Import) else node.module) for node in imports} ==
         {'ast', 'hashlib', 'json', 're', 'fractions'}, 'frontend imports leave inert stdlib-only scope')
    forbidden = {'eval', 'exec', 'compile', 'open', '__import__'}
    need(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden
                 for node in ast.walk(compiler)), 'frontend executes or opens target source')
    cf = functions(compiler)
    need(set(ARGUMENTS).issubset({argument.arg for argument in cf['compile_objective_scalar_slices'].args.args}),
         'frontend hash-binding CLI argument names differ')
    renderer = cf['render_generated_lean_with_receipt']
    result_dict = next(node.value for node in renderer.body if isinstance(node, ast.Return))
    fields = [ast.literal_eval(key) for key in result_dict.keys]
    expected_fields = {'text', 'validation_AST_parse_calls', 'source_sha256', 'source_execution_calls',
                       'native_qualification_jobs', 'theorem_qualified'}
    need(set(fields) == expected_fields and len(fields) == 6, 'renderer closed API differs')
    interface = json.loads(raws['candidate-interface.json'])
    need(interface['schema'] == 'ranker-objective-scalar-candidate-interface@1' and
         interface['status'] == 'unexecuted_uncompiled_unqualified_source_candidate', 'candidate interface scope differs')
    need(set(interface['host_API']['renderer_closed_fields']) == expected_fields, 'documented renderer API differs')
    for row in interface['source_files']:
        need(pins[str(Path(row['path']).relative_to(ROOT))] == row, 'candidate interface source pin differs')
    need(interface['source_plan'] == document_pins['source_plan'], 'candidate interface plan descriptor differs')
    for key, value in interface['frontier_flags'].items():
        need(value == ('OPEN' if key == 'all32_governing_RPI_exits' else 'unknown' if key == 'full_task_satisfaction' else False),
             'candidate interface promotes a frontier')
        if key not in {'all32_governing_RPI_exits', 'full_task_satisfaction'}:
            need(value is False, 'frontier flag must be exact false')
    driver_text = raws['run_objective_controls_01.py'].decode()
    need('assert set(rendered) == ' + repr(expected_fields) in driver_text or
         any(isinstance(node, ast.Set) and all(isinstance(item, ast.Constant) for item in node.elts) and
             {ast.literal_eval(item) for item in node.elts} == expected_fields
             for node in ast.walk(functions(driver)['compile_source_slices'])),
         'driver renderer schema differs')
    for snippet in ['type(rendered["native_qualification_jobs"]) is int', 'rendered["theorem_qualified"] is False',
                    'type(spec["source_execution_calls"]) is int', 'type(result[counter]) is int']:
        need(snippet in driver_text, 'exact counter/frontier API gate missing')
    old_driver_raw, old_driver_pin = read(PRIOR / 'run_source_semantics_controls_v2.py',
        '3c183e16c3b0b5578048f60055953a34965b958c793734ad59ade9a2e1d68d96', 38817)
    old_functions, new_functions = functions(ast.parse(old_driver_raw)), functions(driver)
    unchanged = sorted(name for name, node in old_functions.items() if name in new_functions and dump(node) == dump(new_functions[name]))
    changed = sorted(name for name, node in old_functions.items() if name in new_functions and dump(node) != dump(new_functions[name]))
    need(changed == ['compile_source_slices', 'outer', 'owned', 'pure_tests'], 'unexpected inherited driver function changed')
    need(set(new_functions) - set(old_functions) == {'validate_mode'}, 'unexpected new harness callback')
    for name in ['helpers', 'verify', 'check_lean', 'held_module']:
        need(name in unchanged, 'owned helper/checker protection changed')
    owned, outer = new_functions['owned'], new_functions['outer']
    for phase in (owned, outer):
        need(isinstance(phase.body[0], ast.Expr) and isinstance(phase.body[0].value, ast.Call) and
             isinstance(phase.body[0].value.func, ast.Name) and phase.body[0].value.func.id == 'validate_mode',
             'phase-mode refusal must precede helper loading and writes')
    mode_regex = r'(?:compile-source-objective|pure-tests-objective|lean-objective(?:-[a-z0-9]+)*)-[0-9]{2}'
    need(mode_regex in [node.value for node in ast.walk(new_functions['validate_mode']) if isinstance(node, ast.Constant)],
         'only three owned phase types permitted')
    need('len(mode) > 96' in driver_text and 'fullname.rsplit(".", 1)[-1] == "terminal_codebase_intent_ranker_training"' in driver_text,
         'bounded numbered phase/bare and alternate ranker import refusal absent')
    need('raise ValueError("use the separately pinned file-only prepare_request_01.py")' in driver_text,
         'inherited prepare path remains admitted')
    old_profile_raw, old_profile_pin = read(PRIOR / 'freeze_source_profile_01.py',
        '82d36418fc74f5b32ea759b11b2af92aadc6c3d683f4a4cdafbc72edba781de8', 6693)
    old_profile_functions = functions(ast.parse(old_profile_raw))
    profile_functions = functions(trees['freeze_source_profile_01.py'])
    need(dump(old_profile_functions['pin']) == dump(profile_functions['pin']) and
         dump(old_profile_functions['write']) == dump(profile_functions['write']), 'profile inherited capture helpers changed')
    profile_text = raws['freeze_source_profile_01.py'].decode()
    for snippet in ['65536', '3997696', 'args.expected_source_sha256', 'args.objective_check_sha256',
                    'compiled and any', 'check["expected_success"] is True', 'check["matches_expectation"] is True',
                    'if not __debug__']:
        need(snippet in profile_text, 'qualified profile source gate missing')
    checked_imports = {}
    for name, path, sha in [
        ('RealStableFactor', ROOT.with_name('ranker-real-convergence-20261005-01') / 'evidence/lean-stable-factor-01/check-result.json',
         '25adf30103c3d7455df5c7fff9eedf6b9e4ceb1fbd5263e919247ed18588e0f5'),
        ('TypedNumericSlice', PRIOR / 'evidence/lean-typed-scalar-02/check-result.json',
         '1e11d2917e3087dc2e231bdf6b329416518eb74542d6e83074d000ee7f8a0e23')]:
        raw, descriptor = read(path, sha)
        check = json.loads(raw)
        need(check['status'] == 'passed' and check['expected_success'] is True and check['matches_expectation'] is True
             and check['axiom_report_error'] is None and check['post_call_binding_error'] is None,
             'actual prior checked-module status differs')
        need(Path(check['source']['path']).stem == name and check['native_invocations'] == 1,
             'actual checked-module source/invocation join differs')
        need(all(row['complete'] is True for row in check['compiled_artifacts']) and
             any(Path(row['path']).name == name + '.olean' for row in check['compiled_artifacts']),
             'actual prior complete module absent')
        checked_imports[name] = descriptor
    request_text = raws['prepare_request_01.py'].decode()
    for snippet in ['1808', '299', '4440', '16777216', 'memory_mb\': 2048', 'child_process_slots\': 4',
                    '20', "'ranker_import'", "'native_ranker_objective'", "'optimizer_update'", 'os.O_NOFOLLOW']:
        need(snippet in request_text, 'request population/boundary/capture requirement missing')
    for name, sha in [('preparation/request-v3.json', '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861'),
                      ('file-only-seal-01.json', '21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65'),
                      ('qualified-review-01.json', '39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550')]:
        read(PRIOR / name, sha)
    tests = trees['source-v2/test_typed_slice_compiler.py']
    cases, test_names = static_test_population(tests)
    need(cases == 98 and len(test_names) == 30, 'source-derived test population differs')
    need(interface['test_population']['source_declared_functions'] == 30 and
         interface['test_population']['source_declared_parameterized_cases'] == 98 and
         interface['test_population']['actual_pytest_collection_or_execution_count'] == 0,
         'interface upgrades static population to execution')
    for fragment in ['wide_ast', 'cyclic_ast', 'malformed_dead_branch', 'lexically_shadowed', 'nonload_call_target',
                     'valid', 'unhashable', 'oversized_decimal', 'oversized_hash', 'unbounded_caller_receipt',
                     'pin_mismatches', 'changed_query', 'parse_counter', 'frontiers']:
        need(any(fragment in name for name in test_names), 'meaningful refusal/source-control missing: ' + fragment)
    snippets = json.loads(raws['source-snippets.json'])
    need(snippets['schema'] == 'ranker-objective-candidate-source-snippet-inventory@1' and
         snippets['source'] == source_pin and len(snippets['snippets']) == 9, 'inert snippet inventory scope differs')
    l2 = next(node.value for node in module.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'L2' for target in node.targets))
    nodes = {'stable_loss_scalar': loss, 'stable_factor_scalar': factor, 'factor_condition': factor.test,
             'factor_then_branch': factor.body, 'factor_else_branch': factor.orelse,
             'loss_max_subexpression': loss.left, 'log1p_argument': loss.right.args[0],
             'source_L2_literal': l2, 'gradient_coordinate': objective.body[4].value.elt}
    need(set(nodes) == set(snippets['snippets']), 'inventory node set differs')
    for name, node in [('objective_context', objective), *nodes.items()]:
        row = snippets['objective_context'] if name == 'objective_context' else snippets['snippets'][name]
        segment = ast.get_source_segment(text, node)
        raw = segment.encode()
        need(row['ast_sha256'] == ast_sha(node) and row['ast_dump'] == dump(node) and row['source_segment'] == segment and
             row['source_segment_utf8_bytes'] == len(raw) and row['source_segment_utf8_sha256'] == hashlib.sha256(raw).hexdigest()
             and row['span'] == [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset],
             'actual source snippet/hash/span join differs')
    math_text = raws['math/ObjectiveScalarIR.lean'].decode()
    math_queries = re.findall(r'^#print axioms (\w+)$', math_text, re.MULTILINE)
    expected_math_queries = ['compile_scalar_sound', 'compile_scalar_refuses_unsupported',
                            'compile_scalar_refuses_unknown_name', 'stableLoss_eval_success', 'stableFactor_eval_success']
    need(math_queries == expected_math_queries, 'math query set differs')
    need(not re.search(r'\b(?:sorry|admit|axiom)\b', re.sub(r'^#print axioms .*$', '', math_text, flags=re.MULTILINE)),
         'mathematical candidate contains an admitted proof or custom axiom')
    for snippet in ['accepted : compileScalar scope source = .ok program', 'induction source generalizing program',
                    '| ifNonneg c t e hc ht he', 'mapThree ScalarIR.ifNonneg',
                    'if b = 0 then .error .divisionByZero', 'if 0 < 1 + a then',
                    'if 0 ≤ value then evalExact t environment else evalExact e environment']:
        need(snippet in math_text, 'accepted-program partial semantics structure differs')
    host_text = raws['source-v2/objective_scalar_compiler.py'].decode()
    emitted_queries = re.findall(r'^#print axioms (\w+)$', host_text, re.MULTILINE)
    need(emitted_queries == interface['planned_queries']['generated_module'] and len(emitted_queries) == 9,
         'literal-generated query set differs')
    need(math_queries == interface['planned_queries']['root_kernel_module'], 'declared root query set differs')
    need('realStablePairLoss_eq' in host_text and 'realStableLogisticP_eq' in host_text and
         'compilation_wire == _bounded_wire(actual)' in host_text,
         'same-buffer original literal bridge/provenance join absent')
    self_raw, self_pin = read(Path(__file__).resolve())
    # Reopen every observed input; no target code or source-defined function runs.
    for path, descriptor in list(HELD.items()):
        need(read(path)[1] == descriptor, 'review input changed before receipt closure')
    receipt = {
        'schema': 'ranker-objective-scalar-independent-source-review@1',
        'status': 'passed_source_only', 'review_source': self_pin,
        'candidate_sources': [pins[name] for name in EXPECTED],
        'candidate_file_count': len(pins), 'candidate_source_bytes': sum(row['bytes'] for row in pins.values()),
        'original_source': source_pin, 'planning_documents': document_pins,
        'prior_owned_driver': old_driver_pin, 'prior_profile_freezer': old_profile_pin,
        'actual_prior_checked_import_receipts': checked_imports,
        'inherited_driver_functions_AST_unchanged': unchanged,
        'inherited_driver_functions_changed_only': changed,
        'static_test_population': {'functions': 30, 'parameterized_cases': 98, 'actual_collection_or_execution': 0},
        'planned_root_math_queries': math_queries, 'planned_generated_math_queries': emitted_queries,
        'source_review_findings': [
            'All nine candidate files and complete original/P6 context digests are bound to stable same-read bytes.',
            'Generic scalar AST/IR uses closed keys, finite lexical slots, exact rational literals, 262144-byte source/4096-module-node/128-scalar-node/depth32/256-bit/65536-receipt caps; incremental pending-node guards precede allocation.',
            'Builtin/math lexical shadowing and non-load targets are refused; both conditional syntax branches are checked even if a branch would not evaluate.',
            'Mathematical compiler soundness is restricted to accepted programs; div/log1p errors and lazy branch evaluation are retained. This is a source inspection, not a Lean proof check.',
            'Actual stable-loss/sign-split operator trees and exact binary64 L2 ratio are preserved; original bridges require whole receipt equality after same-buffer canonical source re-extraction.',
            'Driver/spec/frontend agree on four hash arguments and six-field renderer API; parse/zero-execution counters use exact non-Boolean integers.',
            'Owned driver only admits numbered objective compile-source, pure-tests and lean modes of at most 96 characters, and blocks bare/alternate/full ranker imports; inherited checker/verify/lease/drain helpers and native 20s/65536-byte/16MiB/pressure limits are unchanged.',
            'Profile freezer pins actual accepted RealStableFactor/TypedNumericSlice checks, preserves complete local artifacts and old retention caps, and requires external source and optional ObjectiveScalarIR check digests.',
            'Pure source controls include changed pins/query trees, eager dead-branch refusals, malformed and valid changed gradient shapes, cyclic/wide AST, lexical/non-load calls, numeric/hash pre-regex caps, bounded caller receipts, and honest projection frontiers.',
        ],
        'outstanding_source_issues': [],
        'scope': 'source/AST/JSON inspection and pin joins only; qualification pending',
        'source_only_review_limits': {
            'target_modules_imported': 0, 'target_helpers_or_compiler_or_renderer_executed': 0,
            'tests_imported_collected_or_run': 0, 'native_model_classifier_codec_jobs': 0,
            'git_commands_or_mutations': 0, 'remote_calls': 0,
            'writes_outside_authorized_review_namespace': 0,
            'host_parser_correctness_theorem_proved': False, 'Lean_candidate_native_qualified': False,
            'Python_Float_libm_fsum_semantics_proved': False,
            'full_objective_gradient_optimizer_source_equivalence_proved': False,
        },
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'planner_activation': False, 'global_autoencoder_convergence_proved': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'all_observed_inputs_rechecked_before_receipt': True,
    }
    destination = REVIEW / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = destination.read_bytes()
    print(json.dumps({'status': receipt['status'], 'receipt': {'path': str(destination), 'bytes': len(raw),
          'sha256': hashlib.sha256(raw).hexdigest()}, 'review_source': self_pin,
          'candidate_files': len(pins), 'static_cases': cases}))


if __name__ == '__main__':
    main()
