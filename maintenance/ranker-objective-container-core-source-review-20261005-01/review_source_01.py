"""Independent file-only review of the first generic container core draft."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
CORE = WORKSPACE / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
Q5 = CORE.with_name('ranker-objective-ir-candidate-20261005-01')
HELD = {}
AUTHORITY_KEYS = ('completion_authority', 'execution_authority', 'formalization_authority',
    'mutation_authority', 'omission_authority', 'planner_activation', 'proof_authority',
    'strict_cache_admission', 'task_satisfaction_proved', 'theorem_qualified')
EXPECTED = {
    'math/ObjectiveContainerCore.lean': (6368, '9f6f36352ec1b45bb8d797cae03683455fcd03d1c3e7663a1991378baeb8da14'),
    'candidate-interface.json': (10393, 'bb3a85da75cde507dbc989760e210701fbfb5f6dd0c86ed5e0604488a8770bcc'),
    'source-model-obligations-01.json': (5296, '132ebd3f91a924bcf5999324021534ac4394d9a70f1169ccae01a0dca720226c'),
}
QUERIES = ('map_exact_ofFn_success', 'mean_exact_ofFn_success',
    'mean_exact_empty_refuses', 'indexed_zip_fsum_ofFn_eq')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path, *, keep=True):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical non-symlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 256 * 1024**2, 'bounded regular input required')
        digest, blocks, size = hashlib.sha256(), [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 256 * 1024**2, 'input grew beyond streaming bound')
            digest.update(block)
            if keep:
                need(size <= 32 * 1024**2, 'bounded retained input required')
                blocks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda item: tuple(getattr(item, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size, 'input changed during read')
        descriptor = {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}
        if str(path) in HELD:
            need(HELD[str(path)] == descriptor, 'repeated input changed')
        HELD[str(path)] = descriptor
        return b''.join(blocks), descriptor
    finally:
        os.close(fd)


def document(pin):
    raw, actual = read(pin['path'])
    need(actual == pin, 'exact same-buffer JSON pin differs')
    return json.loads(raw)


def main():
    need(__debug__, 'unoptimized reviewer required')
    docs, pins = {}, {}
    for name, (size, digest) in EXPECTED.items():
        raw, pin = read(CORE / name)
        need((pin['bytes'], pin['sha256']) == (size, digest), 'externally reviewed candidate pin differs')
        pins[name] = pin
        docs[name] = raw.decode() if name.endswith('.lean') else json.loads(raw)
    source = docs['math/ObjectiveContainerCore.lean']
    interface, obligations = docs['candidate-interface.json'], docs['source-model-obligations-01.json']
    need(interface['schema'] == 'ranker-objective-container-core-candidate-interface@1' and obligations['schema'] == 'ranker-objective-container-core-open-obligations@1', 'exact candidate schemas required')
    need(interface['math_source'] == obligations['math_source'] == pins['math/ObjectiveContainerCore.lean'] and obligations['candidate_interface'] == pins['candidate-interface.json'], 'candidate cross-pins differ')
    for doc in (interface, obligations):
        need(all(doc[key] is False for key in AUTHORITY_KEYS), 'no authority or qualification grant allowed')
        need(doc['candidate_compiled'] is False and doc['candidate_native_qualified'] is False and doc['full_task_satisfaction'] == 'unknown' and doc['all32_governing_RPI_exits'] == 'OPEN' and doc['official_benchmark_score'] is None, 'draft scope claims differ')
    need(interface['direct_imports'] == ['ObjectiveScalarIR'] and re.findall(r'^import\s+([^\n]+)', source, re.M) == ['ObjectiveScalarIR'], 'one qualified direct import only')
    need(re.search(r'\b(?:sorry|admit|unsafe|axiom)\b', source) is None, 'draft has a proof bypass')
    need(tuple(row['name'].split('.')[-1] for row in interface['proposed_query_batch']) == QUERIES and interface['proposed_native_query_count'] == 4, 'exact first four-query batch differs')
    need(all(row['native_query_executed'] is False and row['theorem_qualified'] is False for row in interface['proposed_query_batch']), 'queries still unexecuted')
    for name in QUERIES:
        need(len(re.findall(r'^theorem ' + name + r'\b', source, re.M)) == 1 and len(re.findall(r'^#print axioms ' + name + r'$', source, re.M)) == 1, 'exact query body/report inventory differs')
    need('if values.length = 0 then .error .divisionByZero' in source and 'min left.length right.length' in source and 'List.zipWith body left right' in source, 'empty refusal and generic truncation required')
    need('induction n generalizing inputs outputs' in source and '(success : ∀ index, body (inputs index) = .ok (outputs index))' in source and '(positive : 0 < n)' in source, 'primitive success/domain premises required')
    need('(factors : Fin n → ℝ) (rows : ExactMatrix n columns) (column : Fin columns)' in source and 'RankerSourceSemantics.zipWith_ofFn_same_length' in source, 'same-length indexed bridge is derived from shared Fin domain')
    need(interface['forbidden_high_level_opcodes'] == ['objective', 'gradient', 'dot', 'logisticLoss', 'sigmoid', 'descent', 'convergence'], 'high-level identity opcode policy differs')
    need(interface['host_SourcePrefix_compiler_implemented'] is False and interface['generated_source_objective_or_gradient_IR_emitted'] is False, 'no frontend/generated objective claim allowed')
    limits = interface['future_root_owned_native_limits']
    need(limits == {'CPU_seconds': 20, 'limits_changed': False, 'per_file_capture_bytes': 65536, 'resource_admission_and_lease_required': True, 'root_qualification_required': True, 'wall_seconds': 20, 'workspace_bytes': 16777216}, 'native limits changed')
    dependency = interface['existing_dependency_environment']
    profile = document(dependency['profile'])
    profile_files = {row['path']: row for row in profile['files']}
    api_sources = []
    for row in dependency['source_backed_core_API_pins']:
        need(row['new_dependency_added'] is False and row['same_bytes_already_in_frozen_profile'] is True, 'API cannot add new dependency')
        need(profile_files[row['source']['path']] == row['source'] and read(row['source']['path'])[1] == row['source'], 'captured API source pin differs')
        api_sources.append(row['source'])
    existing = dependency['module_qualification']
    check = document(existing['qualification'])
    need(existing['module'] == 'ObjectiveScalarIR' and check['status'] == 'passed' and check['matches_expectation'] is True and check['expected_success'] is True and check['axiom_report_error'] is None and check['post_call_binding_error'] is None, 'direct import lacks actual qualified native closure')
    need(read(dependency['existing_ObjectiveScalarIR_source']['path'])[1] == dependency['existing_ObjectiveScalarIR_source'], 'qualified scalar source differs')
    need(read(dependency['existing_TypedNumericSlice_source']['path'])[1] == dependency['existing_TypedNumericSlice_source'], 'qualified numeric source differs')
    imported_modules = {row['module'] for row in profile['source_import_modules']}
    need({'ObjectiveScalarIR', 'TypedNumericSlice', 'RealStableFactor'} <= imported_modules, 'already qualified local modules required')
    object_pins = []
    for row in check['compiled_artifacts']:
        exact = {key: row[key] for key in ('path', 'bytes', 'sha256')}
        need(row['complete'] is True and read(row['path'], keep=False)[1] == exact, 'complete retained scalar module object differs')
        object_pins.append(exact)
    need(any(Path(row['path']).name == 'ObjectiveScalarIR.olean' for row in object_pins), 'retained complete imported object required')
    plan_pins = []
    for pin in interface['P7_source_plan_context'].values():
        document(pin)
        plan_pins.append(pin)
    old = obligations['existing_qualified_Q5_untouched']
    qualified = document(old['qualified_review'])
    seal = document(old['seal'])
    need(qualified['status'] == 'passed' and qualified['qualified_theorem_queries'] == 14 and qualified['metadata_payloads'] == 4458, 'old Q5 scope differs')
    need(len(seal['files']) == 276 and sum(row['bytes'] for row in seal['files']) == 78794802, 'old sealed population differs')
    for pin in seal['files']:
        need(read(pin['path'], keep=False)[1] == pin, 'sealed Q5 leaf changed')
    need(sum(EXPECTED[name][0] for name in EXPECTED) == 22057, 'candidate size differs')
    for pin in list(HELD.values()):
        need(read(pin['path'], keep=False)[1] == pin, 'reviewed input changed before closure')
    receipt = {'schema': 'ranker-objective-container-core-independent-source-review@1',
        'status': 'passed_source_only', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer': read(Path(__file__).resolve())[1], 'candidate_pins': pins,
        'reviewed_input_pins': list(HELD.values()), 'findings': [], 'native_jobs': 0,
        'test_or_model_jobs': 0, 'project_imports_or_source_function_executions': 0,
        'remote_mutations': 0, 'actual_new_qualified_queries': 0,
        'candidate_compiled': False, 'candidate_native_qualified': False,
        'reviewed_query_names': ['RankerObjectiveContainerIR.' + name for name in QUERIES],
        'reviewed_semantics': ['ordered partial map and zip definitions stop on first body error',
            'generic zip retains the shorter input length', 'empty mean refuses before real division',
            'mean uses positive generic length and exact-real sum',
            'indexed zip/sum bridge derives equal lengths from shared Fin n',
            'kernel-side finite bounds do not assert host parser or runtime validation',
            'pointwise body-success premise contains no desired objective or gradient identity'],
        'API_sources_already_in_frozen_profile': api_sources,
        'complete_retained_ObjectiveScalarIR_objects': object_pins,
        'P7_context_pins': plan_pins, 'all_Q5_sealed_leaves_unchanged': True,
        'Q5_sealed_files': 276, 'Q5_sealed_bytes': 78794802,
        'full_source_Python_Float_training_AE_or_task_equivalence': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
        'official_benchmark_score': None, **{key: False for key in AUTHORITY_KEYS}}
    destination = ROOT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': receipt['status'], 'receipt': read(destination)[1], 'actual_new_qualified_queries': 0}))


if __name__ == '__main__':
    main()
