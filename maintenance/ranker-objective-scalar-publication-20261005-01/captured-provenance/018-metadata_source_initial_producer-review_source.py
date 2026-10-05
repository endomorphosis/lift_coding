"""Independent source-only metadata builder/runtime review; no targets import.

Only stable file reads, AST/JSON parsing and structural inspection are used.
No builder, runtime, tests, metadata hydration, native, model, Git, remote or
publication job is executed. Only the new sibling receipt is written.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01')
OUT = Path(__file__).resolve().parent
EXPECTED = {
    'build_objective_metadata_01.py': (49474, '45246ee6931195cecc07433384c953aa474cd903ec7c665e6b38f406dc47e1c9'),
    'run_objective_metadata_controls_01.py': (49452, '6b4a1e7b7d345d7bf27ba74eca5e64f6166deae4d777a5131ad50d0128d48908'),
    'run_objective_controls_01.py': (43354, '42db20ed326046ad9e2bc9666cc67494937dd3321a1b70ddb4f5618b8271d14f'),
}
PLAN_KEYS = {'schema', 'prior_metadata', 'compiler_source', 'compiler_tests', 'original_source', 'source_slices',
             'generated_lean', 'source_specification', 'compile_closed', 'compile_outer', 'pure_closed', 'pure_outer',
             'pure_phases', 'native_attempts'}
HELD = {}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def read(path, sha=None, size=None):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical review input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, 'bounded regular review input')
        chunks, total = [], 0
        while chunk := os.read(fd, 1024**2):
            total += len(chunk)
            need(total <= 32 * 1024**2, 'input grew beyond review cap')
            chunks.append(chunk)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        sig = lambda value: tuple(getattr(value, field) for field in fields)
        need(sig(before) == sig(os.fstat(fd)) == sig(path.lstat()) and total == before.st_size, 'review input changed')
        raw = b''.join(chunks)
        pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(sha is None or pin['sha256'] == sha, 'review source SHA differs')
        need(size is None or pin['bytes'] == size, 'review source size differs')
        need(path not in HELD or HELD[path] == pin, 'repeated review input differs')
        HELD[path] = pin
        return raw, pin
    finally:
        os.close(fd)


def assigned(tree, name):
    node = next(node for node in tree.body if isinstance(node, ast.Assign) and
                any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
    return ast.literal_eval(node.value)


def functions(tree):
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def dump(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def main():
    raws, pins, trees = {}, {}, {}
    for name, (size, sha) in EXPECTED.items():
        raw, pin = read(ROOT / name, sha, size)
        raws[name], pins[name], trees[name] = raw.decode(), pin, ast.parse(raw)
    builder, runtime, baseline = (trees[name] for name in EXPECTED)
    bf, rf, of = functions(builder), functions(runtime), functions(baseline)
    changed = sorted(name for name in of if name in rf and dump(of[name]) != dump(rf[name]))
    unchanged = sorted(name for name in of if name in rf and dump(of[name]) == dump(rf[name]))
    need(changed == ['metadata', 'owned', 'validate_mode'] and set(rf) == set(of), 'runtime changes exceed admitted metadata adaptation')
    for name in ['helpers', 'verify', 'check_lean', 'compile_source_slices', 'pure_tests', 'outer', 'held_module']:
        need(name in unchanged, 'prior admitted controller/helper function changed')
    import_roots = set()
    for node in builder.body:
        if isinstance(node, ast.Import):
            import_roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            import_roots.add(node.module)
    need(import_roots == {'argparse', 'ast', 'hashlib', 'json', 'os', 're', 'stat', 'pathlib'}, 'builder leaves stdlib/file-only scope')
    need(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                 node.func.id in {'eval', 'exec', 'compile', '__import__'} for node in ast.walk(builder)), 'builder executes source')
    for name, value in {'MAX_FILE': 33554432, 'MAX_READ': 268435456, 'MAX_PAYLOAD': 67108864, 'MAX_ROW': 262144}.items():
        # The four source expressions are fixed multiplication-only integer
        # arithmetic, inspected structurally without running target code.
        expression = next(node.value for node in builder.body if isinstance(node, ast.Assign) and
                     any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
        def literal_product(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return node.value
            need(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult), 'inert fixed integer bound expected')
            return literal_product(node.left) * literal_product(node.right)
        need(literal_product(expression) == value, 'builder IO/storage cap differs')
    need(assigned(builder, 'FIXED_DELTAS') == {'ast': 2, 'sources': 3, 'ranker_real_curvature_proofs': 2, 'kg': 9},
         'metadata fixed family deltas differ')
    need(assigned(builder, 'NATIVE_BOUNDS') == {'cpu_seconds': 20, 'max_input_bytes': 262144,
         'max_output_bytes': 65536, 'max_workspace_bytes': 16777216, 'timeout_seconds': 20}, 'native caps changed')
    authority, frontiers = assigned(builder, 'AUTHORITY'), assigned(builder, 'FRONTIERS')
    for key, value in {**authority, **frontiers}.items():
        need(value is False or (key == 'full_task_satisfaction' and value == 'unknown') or
             (key == 'official_benchmark_score' and value is None) or
             (key == 'all32_governing_RPI_exits' and value == 'OPEN'), 'builder promotes an authority/frontier flag')
    build_plan_call = next(node for node in bf['build_metadata'].body if isinstance(node, ast.Expr) and
                          isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'keys')
    need(set(ast.literal_eval(build_plan_call.value.args[1])) == PLAN_KEYS, 'builder closed plan keys differ')
    runtime_plan_sets = [set(ast.literal_eval(node)) for node in ast.walk(rf['metadata']) if isinstance(node, ast.Set) and
                        all(isinstance(element, ast.Constant) and type(element.value) is str for element in node.elts)]
    need(PLAN_KEYS in runtime_plan_sets, 'runtime closed plan API differs')
    build_text, runtime_text = raws['build_objective_metadata_01.py'], raws['run_objective_metadata_controls_01.py']
    for text in [build_text, runtime_text]:
        for schema in ['ranker-objective-scalar-metadata-build-plan@1', 'ranker-objective-scalar-metadata-file-build@1']:
            need(schema in text, 'builder/runtime schema handshake differs')
        need('"frozen_build_plan"' in text and '"metadata_inputs"' in text, 'builder/runtime receipt field handshake differs')
    for snippet in ['2 <= len(attempts) <= 12', '4440', '375', '2108', '65536', '3997696']:
        need(snippet in build_text, 'builder bound/prior population missing')
    need('2 <= len(attempts) <= 12' in runtime_text, 'runtime attempt cap differs from builder')
    builder_controls = [
        'duplicate JSON key', 'nonfinite JSON value', 'input JSON depth/node budget', 'aggregate read budget',
        'conflicting descriptors for same path', 'file aliases refused', 'os.O_NOFOLLOW', 'post_verify',
        'new metadata row pending-node limit', 'duplicate new/prior record ID', 'optimized Python invocation refused',
        'reviewed generic mathematical semantics source identity',
        'generated import registry uses exact accepted generic source and complete ordered objects',
        'accepted generic import source/object absent from generated frozen file population',
        'original source absent from source phase', 'actual admitted source compilation specification absent from compile invocation',
        'every actual native result indexed', '98-case inert pure test audit',
        'unique complete selected pure tests', 'source/queried augmented source join',
        'standard-only complete theorem query', 'chunk/full object reconstruction mismatch',
        'exact aggregate retention denominator', 'vectors or mathematical domain population drift',
        'new candidate preparation output namespace required',
    ]
    for snippet in builder_controls:
        need(snippet in build_text, 'reviewed builder refusal/provenance gate missing: ' + snippet)
    for key in ['source_AST_parse_calls', 'source_function_execution_calls', 'new_native_qualification_jobs']:
        need('type(compiled.get("' + key + '")) is int' in build_text, 'source counter accepts Boolean/float')
    for key in ['native_runner_calls_refused', 'direct_process_calls_refused']:
        need('type(pure.get("' + key + '")) is int' in build_text, 'pure counter accepts Boolean/float')
    for snippet in ['hydrate_codebase_ir_metadata(records=records', 'fresh_process_readback', 'canonical(exported) == canonical(values)',
                    'canonical(records["vectors"]) == canonical(prior["vectors"])',
                    'canonical(records["contracts"]) == canonical(prior["contracts"])',
                    'row_count == 4440 + 16 + len(attempts)', 'held_inputs.append(artifact)',
                    'for row in [*held_inputs, records_pin, build_pin, plan_pin]',
                    '"native_Lean_invocations_in_metadata_phase"] = 0',
                    '"strict_advisory_cache_entries_added_in_this_phase": 0',
                    '"new_mathematical_projection_domain_contract_rows": 0']:
        need(snippet in runtime_text, 'runtime full payload/gate/recheck/claim boundary missing: ' + snippet)
    for phase in [rf['owned'], rf['outer']]:
        need(isinstance(phase.body[0], ast.Expr) and isinstance(phase.body[0].value, ast.Call) and
             isinstance(phase.body[0].value.func, ast.Name) and phase.body[0].value.func.id == 'validate_mode',
             'mode check must precede helper/namespace mutation')
    need('metadata-objective' in dump(rf['validate_mode']) and 'len(mode) > 96' in runtime_text and
         'elif mode.startswith("metadata-objective-"):' in runtime_text, 'numbered metadata mode not isolated')
    source_dir = OUT.with_name('ranker-objective-ir-candidate-source-review-20261005-01')
    semantic_raw, semantic_pin = read(source_dir / 'semantic-native-review-01.json',
        '830fbc6d21dfb074cf4d491df78a2f4a8f5d911cd2622163856600d9c29d3eca')
    semantic = json.loads(semantic_raw)
    need(semantic['status'] == 'passed_file_only_actual_receipt_review' and semantic['actual_native_invocations'] == 2 and
         semantic['actual_distinct_kernel_queries'] == 14 and semantic['actual_pure_controls']['tests'] == 98 and
         semantic['actual_pure_controls']['phases'] == 294, 'actual prerequisite semantic/native gate differs')
    for name, expected in {'SOURCE_SHA': '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a',
        'COMPILER_SHA': 'a9f4c93423c0f10e432e005ce4f8986e903706cf7ea5b493699633618519d9d9',
        'TEST_SHA': 'c18c4a95bde5da2c780a91bc77e1ad5358ebd30723087e11fb0a8b96448c35c1',
        'SLICES_SHA': semantic['actual_AST_phase']['slices']['sha256'],
        'GENERATED_SHA': semantic['actual_AST_phase']['generated']['sha256'],
        'GENERIC_SOURCE_SHA': 'ae4d1ebec782c2395cc9d2585f40296988fc2ec10cfdab3f946258251c527d71'}.items():
        need(assigned(builder, name) == expected, 'new builder immutable source identity differs: ' + name)
    generic_queries = [row['theorem'] for row in semantic['actual_native_checks'][0]['queries']]
    generated_queries = [row['theorem'] for row in semantic['actual_native_checks'][1]['queries']]
    need(len(generic_queries) == 5 and len(generated_queries) == 9, 'actual two-module query prerequisites differ')
    prior_path = ROOT.with_name('ranker-source-semantics-20261005-01') / 'evidence/metadata-source-slices-01/metadata-inputs.json'
    # Use the actual qualified request's exact metadata path, rather than an
    # invented path or a source import of the request preparer.
    request_raw, request_pin = read(ROOT / 'preparation/request-v3.json',
        '8e9038a657519b35e769e911219dbe5ad4bf92833017663f8673d5ef2613fdd3')
    metadata_pin = json.loads(request_raw)['prior_metadata_inputs']
    need(metadata_pin['sha256'] == assigned(builder, 'PRIOR_SHA'), 'runtime/builder prior metadata pin differs')
    prior_raw, prior_pin = read(metadata_pin['path'], metadata_pin['sha256'], metadata_pin['bytes'])
    prior = json.loads(prior_raw)
    need(len(prior) == 32 and sum(map(len, prior.values())) == 4440 and
         len(prior['vectors']) == 375 and len(prior['contracts']) == 2, 'actual complete baseline metadata population differs')
    self_raw, self_pin = read(Path(__file__).resolve())
    for path, pin in list(HELD.items()):
        read(path, pin['sha256'], pin['bytes'])
    receipt = {
        'schema': 'ranker-objective-scalar-metadata-independent-source-review@1', 'status': 'passed_source_only',
        'review_source': self_pin, 'builder': pins['build_objective_metadata_01.py'],
        'runtime': pins['run_objective_metadata_controls_01.py'], 'admitted_previous_driver': pins['run_objective_controls_01.py'],
        'prerequisite_actual_semantic_native_review': semantic_pin, 'exact_actual_prior_metadata': prior_pin,
        'runtime_functions_AST_unchanged': unchanged, 'runtime_functions_changed_only': changed,
        'closed_plan_keys': sorted(PLAN_KEYS), 'native_attempt_limit': 12,
        'fixed_family_deltas': {'ast': 2, 'sources': 3, 'ranker_real_curvature_proofs': 2, 'kg': 9},
        'dynamic_native_check_delta': 'all actual attempts N, including supported inconclusive attempts as unadmitted check records only',
        'current_actual_expected_delta': {'N': 2, 'additions': 18, 'final_rows': 4458, 'families': 32,
                                          'vectors_unchanged': 375, 'contracts_unchanged': 2},
        'reviewed_properties': [
            'Builder uses only stdlib source/JSON/file reads and exactly one AST parse of the fixed original source; no project imports, source evaluation, native jobs or hydration.',
            '32MiB individual/256MiB aggregate input, 64MiB output, 262144-byte rows, finite JSON/node/depth/pending budgets, duplicate keys/IDs/aliases/conflicting pins and Python optimization refusal remain enforced.',
            'Canonical old 4440 payload prefixes, all 32 families, vectors375 and contracts2 are preserved exactly; only AST2/source3/proof2/checksN/KG9 are added.',
            'Actual source compiler/test/slices/emission and original source pins are fixed; compile spec and original source join the admitted compile/pure invocation inputs; counters use exact integers.',
            'Only actual accepted generic/generated modules create two proof records; supported inconclusive attempts remain unadmitted check history. All actual check paths are indexed once.',
            'Native specs/owned/outer/invocations/profiles/source augmentation, exact 5/9 theorem query names, standard axioms, unchanged caps and complete chunk/full raw object reconstruction are joined before metadata construction.',
            'Generated frozen import registry source and ordered full objects join this accepted generic module, with files membership; generic source is the reviewed mathematical candidate hash.',
            'Metadata runtime matches builder receipt/plan APIs and limit12, verifies accepted bodies before hydration and after full payload readback, uses the same inherited owned controls and captured hydration implementation, and checks every export payload after a fresh process.',
            'No new domain/runtime contracts or strict-cache admission entries are created; Python/full-objective/gradient/Float/host-parser/AE/task and all authority frontiers stay open.',
        ],
        'outstanding_source_issues': [],
        'limits': {'target_builder_or_runtime_imported_or_executed': 0, 'tests_native_model_metadata_classifier_codec_jobs': 0,
                   'Git_commands_or_mutations': 0, 'remote_publication_calls': 0,
                   'metadata_output_or_actual_hydration_success_claimed': False,
                   'writes_outside_authorized_review_namespace': 0,
                   'scope': 'source/AST/JSON review and actual prerequisite receipt joins only'},
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        'all_observed_inputs_rechecked_before_receipt': True,
    }
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = target.read_bytes()
    print(json.dumps({'status': receipt['status'], 'receipt': {'path': str(target), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}, 'review_source': self_pin}))


if __name__ == '__main__':
    main()
