"""Independent source/AST and compact receipt review; never load target code."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

Q4 = Path('/home/barberb/lift_coding/qualification/codebase_ir/ranker-source-semantics-20261005-01')
OUT = Path(__file__).resolve().parent
BUILDER_SHA = 'd40b60554e292a2b6b8e14a7ff7696809360479bcb81e9c0c57bf351071e6fbf'
PLAN_SHA = '7d4de36938aca90e4bff572dc00bfa53bda77c37fdd8b5c37476a0428d874d79'
held = {}


def require(ok, reason):
    if ok is not True:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path, expected=None):
    path = Path(path).absolute()
    require(path.resolve(strict=True) == path, 'canonical review input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, 'bounded regular review input')
        blocks, total = [], 0
        while block := os.read(fd, 1024**2):
            blocks.append(block)
            total += len(block)
            require(total <= 16 * 1024**2, 'review input read bound')
        raw = b''.join(blocks)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in fields)
        require(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
                and len(raw) == before.st_size, 'review input changed')
    finally:
        os.close(fd)
    binding = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(expected is None or binding['sha256'] == expected, 'external review pin mismatch')
    held[str(path)] = binding
    return raw


def load(binding):
    raw = read(binding['path'], binding['sha256'])
    require(len(raw) == binding['bytes'] and type(binding['bytes']) is int, 'compact descriptor byte count')
    return json.loads(raw)


def has(text, fragments):
    for fragment in fragments:
        require(fragment in text, 'missing source gate: ' + fragment)


def main():
    builder = Q4 / 'build_source_metadata_01.py'
    raw = read(builder, BUILDER_SHA)
    require(len(raw) == 41339, 'final builder byte count')
    tree = ast.parse(raw)
    imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    from_imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    require(imports == {'argparse', 'ast', 'hashlib', 'json', 'os', 're', 'stat'} and from_imports == {'pathlib'},
            'builder imports outside standard library')
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    require(not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                    node.func.id in {'exec', 'eval', 'compile', '__import__'} for node in ast.walk(tree)),
            'target code execution API present')
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    require(constants['DELTAS'] == {'ast': 2, 'sources': 3, 'contracts': 2,
                                   'ranker_real_curvature_proofs': 2, 'ranker_real_curvature_checks': 3, 'kg': 11},
            'exact 23-row whitelist')
    require(constants['NATIVE_BOUNDS'] == {'cpu_seconds': 20, 'max_input_bytes': 262144,
                                           'max_output_bytes': 65536, 'max_workspace_bytes': 16777216,
                                           'timeout_seconds': 20}, 'native caps changed')
    body = raw.decode()
    has(body, ['MAX_FILE = 32 * 1024 * 1024', 'MAX_READ = 256 * 1024 * 1024',
               'MAX_PAYLOAD = 64 * 1024 * 1024', 'MAX_ROW = 262144',
               'duplicate JSON key', 'input JSON depth/node budget', 'input JSON pending budget',
               'file aliases refused', 'file digest mismatch', 'post = reader.post_verify()',
               'duplicate new/prior record ID', 'need(__debug__ is True',
               'output.is_relative_to(Q4 / "preparation")', 'output.mkdir(mode=0o755)'])
    native = ast.unparse(functions['native_attempt'])
    has(native, ["same_pin(outer['invocation'], row['invocation'])", "type(calls) is list and len(calls) == 1",
                 "same_pin(calls[0]['specification'], row['specification'])",
                 "same_pin(owned['native_proof_checks'][0], row['check_result'])",
                 "reader.read(check['augmented_source']) == augmented",
                 "ranker-real-curvature-bounded-analytic-lean-check@2",
                 "retained_objects(reader, check, row['module'])"])
    retained = ast.unparse(functions['retained_objects'])
    has(retained, ["names[0] == module + '.olean'", 'len(names) == len(set(names))',
                   "profile['object_suffixes']", "type(manifest.get('aggregate_raw_object_bytes')) is int",
                   "raw == reader.read(row)", 'len(set(used)) == len(used)',
                   "manifest['native_lean_invocations'] == 1", 'aggregate <= 3997696'])
    audit = ast.unparse(functions['_source_audit'])
    has(audit, ["same_pin(outer['invocation'], owned['invocation'])", 'cases == 137',
                "Path(descriptor(plan['pure_closed'])['path']).parent / 'phases.json'",
                "values == ['setup', 'call', 'teardown']", "same_pin(compiled['source_slices'], plan['source_slices'])",
                "same_pin(compiled['generated_Lean_candidate'], plan['generated_lean'])"])
    build = ast.unparse(functions['build_metadata'])
    has(build, ['sum(map(len, prior.values())) == 4417', 'sum(map(len, records.values())) == 4440',
                "canonical(records[family][:len(rows)]) == canonical(rows)",
                "canonical(records['vectors']) == canonical(prior['vectors'])", 'runtime_enforced=False',
                'python_source_contract_proved=False', "numeric_backend='exact_real'", 'dimension=80',
                'Python_semantics_preservation_implication=False', "if row['role'] == 'typed_failed':\n            continue",
                "'full_external_dependency_closure_revalidated_here': False",
                "'pinned_executable_and_local_compiled_object_bodies_read': True"])
    plan_path = Q4 / 'preparation/metadata-build-plan-01.json'
    plan_raw = read(plan_path, PLAN_SHA)
    require(len(plan_raw) == 8272, 'frozen build plan byte count')
    plan = json.loads(plan_raw)
    require(plan['schema'] == 'ranker-source-metadata-build-plan@1', 'build plan schema')
    for name in ('compiler_source', 'compiler_tests', 'original_source', 'generated_lean'):
        binding = plan[name]
        read(binding['path'], binding['sha256'])
        require(held[binding['path']]['bytes'] == binding['bytes'], 'source/candidate byte count')
    slices = load(plan['source_slices'])
    require(plan['source_slices']['sha256'] == constants['SLICES_SHA'] and slices['dimension'] == 80,
            'frozen source compilation receipt')
    audit_rows = {}
    for label in ('pure', 'compile'):
        owned, outer = load(plan[label + '_closed']), load(plan[label + '_outer'])
        require(owned['status'] == 'passed' and outer['returncode'] == 0
                and canonical(owned['invocation']) == canonical(outer['invocation']), 'source owned/outer join')
        call = load(owned['invocation'])
        require(call['mode'] == owned['mode'], 'source invocation mode')
        audit_rows[label] = owned
    require(canonical(audit_rows['compile']['source_slices']) == canonical(plan['source_slices'])
            and canonical(audit_rows['compile']['generated_Lean_candidate']) == canonical(plan['generated_lean']),
            'actual compilation/emission output pins')
    phases = load(plan['pure_phases'])
    require(len(phases) == 411 and audit_rows['pure']['selected_test_count'] == 137
            and all(value['outcome'] == 'passed' for value in phases)
            and len({value['nodeid'] for value in phases if value['phase'] == 'call'}) == 137,
            'actual pure137/411 denominator')
    native_rows = []
    require([row['role'] for row in plan['native_attempts']] == ['typed_failed', 'typed_accepted', 'generated_accepted'],
            'exact native attempt roles')
    for row in plan['native_attempts']:
        owned, outer, check = load(row['owned_closed']), load(row['outer_closed']), load(row['check_result'])
        spec, call = load(row['specification']), load(row['invocation'])
        require(canonical(owned['invocation']) == canonical(row['invocation']) == canonical(outer['invocation'])
                and owned['mode'] == row['phase'] == call['mode'], 'actual native outer/owned/invocation joins')
        require(len(owned['native_checker_attempts']) == 1
                and canonical(owned['native_checker_attempts'][0]['specification']) == canonical(row['specification'])
                and owned['native_checker_attempts'][0]['native_invocations_observed'] == 1
                and canonical(owned['native_proof_checks'][0]) == canonical(row['check_result']), 'actual native call ledger')
        require(canonical(spec['source']) == canonical(check['source'])
                and canonical(spec['environment_manifest']) == canonical(check['environment_manifest']), 'actual native profile/source joins')
        source = read(spec['source']['path'], spec['source']['sha256'])
        augmented = read(check['augmented_source']['path'], check['augmented_source']['sha256'])
        expected = source + b'\n' + b'\n'.join(('#print axioms _root_.' + name).encode() for name in spec['theorem_names']) + b'\n'
        require(augmented == expected, 'actual queried source byte join')
        passed = row['role'] != 'typed_failed'
        require(check['status'] == ('passed' if passed else 'inconclusive'), 'actual native status')
        if passed:
            require(owned['status'] == 'passed' and outer['returncode'] == 0 and check['matches_expectation'] is True
                    and all(value['complete'] is True for value in check['compiled_artifacts']), 'complete accepted module receipt')
            require(len(check['theorem_axiom_output']) == (7 if row['role'] == 'generated_accepted' else 14),
                    'actual qualified theorem count')
            if row['role'] == 'generated_accepted':
                require(source == read(plan['generated_lean']['path'], plan['generated_lean']['sha256']), 'actual generated source copy')
        native_rows.append({'role': row['role'], 'phase': row['phase'], 'status': check['status'],
                            'qualification': row['check_result'], 'query_count': len(check['theorem_axiom_output']),
                            'compiled_artifact_descriptors': check['compiled_artifacts']})
    reviewed = dict(held)
    for path, binding in reviewed.items():
        read(path, binding['sha256'])
        require(held[path] == binding, 'reviewed source/receipt inputs changed')
    self_path = Path(__file__).resolve()
    read(self_path)
    receipt = {'schema': 'ranker-source-metadata-builder-independent-source-review@1',
               'status': 'passed_source_only_review', 'outstanding_issues': [], 'review_source': held[str(self_path)],
               'builder': held[str(builder)], 'frozen_build_plan': held[str(plan_path)],
               'reviewed_input_pin_count': len(reviewed), 'actual_native_receipt_joins': native_rows,
               'metadata_prior_rows': 4417, 'metadata_additions': 23, 'metadata_result_rows': 4440,
               'family_count': 32, 'unchanged_vector_count': 375, 'new_mathematical_domains': 2,
               'family_deltas': constants['DELTAS'], 'pure_cases': 137, 'pure_phases': 411,
               'findings': ['Actual owned native calls use one-element lists with source specification joins.',
                            'Outer/owned/invocation/specification/check schemas and pin joins fail closed.',
                            'Native typed01 remains inconclusive and is never indexed as a qualified module.',
                            'Accepted modules require exact queried sources, standard axioms and complete reconstructed object/chunk sets.',
                            'Pure transcript belongs to its owned run and compile outputs join the frozen source/IR/emission records.',
                            'Canonical4417 prefixes and375 vectors remain intact with exactly23 authorized rows and11 descriptive KG edges.',
                            'Mathematical domains use exact-real supplied-gradient assumptions and false runtime/source-contract claims.',
                            'Only a new Q4 preparation output directory may be created; source/runtime/Float/AE/authority frontiers remain open.'],
               'scope': {'source_only': True, 'target_imports': 0, 'target_execution': 0, 'test_jobs': 0,
                         'native_jobs': 0, 'model_jobs': 0, 'codec_jobs': 0, 'Git_actions': 0, 'remote_actions': 0,
                         'protected_writes': 0, 'external_binary_body_reads_in_review': 0,
                         'native_object_reconstruction_executed_in_review': False,
                         'complete_native_dependency_closure_revalidated_in_review': False,
                         'proof_authority': False, 'execution_authority': False, 'completion_authority': False}}
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    raw = target.read_bytes()
    print(json.dumps({'status': receipt['status'], 'builder': receipt['builder'],
                      'receipt': {'path': str(target), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                      'review_source': receipt['review_source']}))


if __name__ == '__main__':
    main()
