"""SOURCE-ONLY: standalone scalar Python AST qualification file readers.

No historical helper executes or has its globals patched. Historical inputs
are preserved by an independent reviewed closure replay; actual current and
imported native modules still pass owned admission and whole object checks.
Disabled until all exact source/manifest/gate/module pins are frozen.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]
Q5=ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
HELD={}
FROZEN={'REPLAY_SOURCE': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/checkpoint_replay.py', 'bytes': 16861, 'sha256': 'bddc7677eceb8db478fb32183ba9ef47520f6fb6156c8b525ab5ddd246ffa152'}, 'CHECKPOINT': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02/history-checkpoint-02.json', 'bytes': 1213138, 'sha256': '6c81310108cc3594a96fcf46070c2eceae2441311f83dfc74a069e90cf02bc99'}, 'REPLAY_GATE': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-02/review-receipt-01.json', 'bytes': 4886, 'sha256': 'ffec7170766fe5ad2026dc2fcb746877878e3f516bc268109d76080b57294160'}, 'MODULE_MAP': {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/module-map-01.json', 'bytes': 3803, 'sha256': 'be9a1884cc3627c7a1a8e0ccdd0987ef66994f79421170d2c8c83a5df0e0dd2a'}, 'CANDIDATE_PINS': {'candidate-interface.json': {'bytes': 6001, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/candidate-interface.json', 'sha256': '8759accb4badb6b7abcc1d50dd4cadad0e4916a3a027405e1936866c06fdc910'}, 'math/PyAstNumericLowering.lean': {'bytes': 5287, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericLowering.lean', 'sha256': '9694b40446f7c8661e183b9d137bf936642940f879227c8373d2a3bdf627b881'}, 'math/PyAstNumericPreservation.lean': {'bytes': 19755, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericPreservation.lean', 'sha256': 'feb5ab4a66c940f6e7b14c1ca983b0f9c39ced7a622b0a0af3407a06317c1b50'}, 'math/PyAstNumericSemantics.lean': {'bytes': 6314, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSemantics.lean', 'sha256': '3ce628f904f57b800f67b7a739f04e3adf72e0888b1689e23f7cef3e1ac2a2b8'}, 'math/PyAstNumericSubset.lean': {'bytes': 3916, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSubset.lean', 'sha256': '11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf'}, 'obligations.json': {'bytes': 1749, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/obligations.json', 'sha256': '9577586a4e312ebe7bdebea3b6c56128fc2d79b3367586b9c2af1fb7d06f1cf1'}}, 'SOURCE_GATE': {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-math-source-review-20261006-01/review-receipt-01.json', 'bytes': 8187, 'sha256': '320d464175c620bfb4c517918246b19c71a056248328bbe8980b8dda5e1e4924'}, 'EXTRA_CONTEXT': [{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-01/candidate-pins-01.json', 'bytes': 1716, 'sha256': '3e0bb18e99aa9d624f87dceef0aa6dbef7f61c887e855a895057db1a7fbd0e7b'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-input-review-20261006-02/replay-readback-01.json', 'bytes': 1782, 'sha256': 'e4b8541138af2838f7fe59da7f8fd6f814de83b199ace9bf7745a5ad9ee01f48'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-01/review-receipt-01.json', 'bytes': 3704, 'sha256': '1f8b7f58545d7c641df08404dbc7ebc1a07b936f80d48647157679c03863c691'}], 'CONTEXT_SEALS': [{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-01/file-only-seal-01.json', 'bytes': 1836, 'sha256': '0eb2413bc22d4bcdc9aacd46907ff30a4aff5867ceaa186a689a151c32195a31'}], 'STRICT_GUARD_COUNT': 3939}
BASE_PROFILE={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-projections-candidate-20261006-02/preparation/lean-objective-prefix-projections-02-producer/environment-manifest.json', 'bytes': 10016048, 'sha256': 'b3071501a40a55cb1dc6ec547f2573090d382403e1887ef9f8db4ad74c244350'}
PRIOR_REQUEST={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-infinite-evaluator-extension-qualification-20261006-01/preparation/lean-original-source-evaluator-infinite-extension-01-request.json', 'bytes': 979363, 'sha256': '4182b135d81188179950c4f89864ed45321bcec11d5d8bf74e634fd57c6f487a'}
PRIOR_SEAL={'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-infinite-evaluator-extension-qualification-20261006-01/file-only-seal-01.json', 'bytes': 11913, 'sha256': 'bfb72c24f578eaef2d961876f62d4c37d92016e3f2374774ffcde2bded64e623'}
BASE_IMPORT_NAMES=['ObjectiveScalarIR', 'RealStableFactor', 'TypedNumericSlice', 'ObjectiveContainerCore', 'ObjectivePrefixIR', 'RealGapContraction']
PRIOR_IMPORTS=[{'check_result': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'mode': 'lean-container-source-01'}, {'check_result': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'mode': 'lean-container-typed-01'}, {'check_result': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}, 'mode': 'lean-container-semantics-01'}]
DEPENDENCY_MODULES={'lean-container-source-01': {'direct_imports': ['ObjectivePrefixIR'], 'module': 'ObjectiveContainerSource', 'prior_modes': [], 'queries': ['RankerObjectiveContainerLanguage.source_zip_left_index_bound'], 'source': {'bytes': 3060, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-01/math/ObjectiveContainerSource.lean', 'sha256': 'fc01f1d99e348e79f9cc9fdaf35cbbdb29d0c0963e88b4b984fde469e2eee410'}}, 'lean-container-typed-01': {'direct_imports': ['ObjectiveContainerSource'], 'module': 'ObjectiveContainerTyped', 'prior_modes': ['lean-container-source-01'], 'queries': ['RankerObjectiveContainerLanguage.typed_zip_right_index_bound'], 'source': {'bytes': 3583, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-01/math/ObjectiveContainerTyped.lean', 'sha256': 'bdb3140f15e51c5f52c37f2326ef7dcb2ebbdf372720915202eb13c1701cda67'}}, 'lean-container-semantics-01': {'direct_imports': ['ObjectiveContainerTyped'], 'module': 'ObjectiveContainerSemantics', 'prior_modes': ['lean-container-source-01', 'lean-container-typed-01'], 'qualification_root': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02', 'queries': ['RankerObjectiveContainerLanguage.map_to_vector_error', 'RankerObjectiveContainerLanguage.zip_to_vector_error', 'RankerObjectiveContainerLanguage.ordered_map_first_error', 'RankerObjectiveContainerLanguage.ordered_zip_first_error'], 'source': {'bytes': 11695, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-candidate-20261006-02/math/ObjectiveContainerSemantics.lean', 'sha256': '23bf7349c698832ad088adc68b41913a88affafff235008b38ef6688079b5ec8'}}}
DEPENDENCY_ROOTS={'lean-container-source-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'lean-container-typed-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01', 'lean-container-semantics-01': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02'}
DEPENDENCY_SOURCE_GATES={'lean-container-source-01': {'bytes': 13034, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-01.json', 'sha256': '6704fc5676a6ebe5ff1abddc58acfa06d91168a5d59a26faa181ed116bafcb94'}, 'lean-container-typed-01': {'bytes': 13034, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-01.json', 'sha256': '6704fc5676a6ebe5ff1abddc58acfa06d91168a5d59a26faa181ed116bafcb94'}, 'lean-container-semantics-01': {'bytes': 14517, 'path': '/home/barberb/lift_coding/maintenance/ranker-objective-container-language-source-review-20261006-01/review-receipt-02.json', 'sha256': 'd3a869e27ab6ee61d2adca560fc5e802f775cc508bfe6e3f974a7ac504ade09c'}}
ACCEPTED_CHECK_PINS={'lean-container-source-01': {'bytes': 14071, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-source-01/check-result.json', 'sha256': 'ca7ed3da92fbae947f595bfde1a8eb1025bc9758ebdd58eaf11210b2d125c0bf'}, 'lean-container-typed-01': {'bytes': 15524, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-01/evidence/lean-container-typed-01/check-result.json', 'sha256': 'cfb690034025ad99470dad89ab537952955ddb4b14b1ed3675bf8181dfcfad63'}, 'lean-container-semantics-01': {'bytes': 13707, 'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-container-language-qualification-20261006-02/evidence/lean-container-semantics-01/check-result.json', 'sha256': '8650075e9f209aa2d61d284d043b51200a866611703ad40739ce29af3f05d62b'}}
NATIVE_LIMITS={'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE={'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE={'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY={'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False}
MODE_ORDER=['lean-python-ast-subset-01', 'lean-python-ast-semantics-01', 'lean-python-ast-lowering-01', 'lean-python-ast-preservation-01']

def need(value, message):
    if value is not True:
        raise ValueError(message)

def read_pin(path, capture=False):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical nonsymlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'unaliased regular input required')
        need(not capture or before.st_size <= 32 * 1024**2, 'parsed input exceeds fixed cap')
        blocks, total, digest = [], 0, hashlib.sha256()
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'input grew during read')
            digest.update(block)
            if capture:
                blocks.append(block)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
             and path.resolve(strict=True) == path and not path.is_symlink()
             and total == before.st_size, 'input changed during read')
    finally:
        os.close(fd)
    descriptor = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == descriptor, 'held input changed')
    HELD[str(path)] = descriptor
    return b''.join(blocks), descriptor

def pin(path):
    return read_pin(path)[1]

def exact(row, capture=False):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact descriptor required')
    raw, actual = read_pin(row['path'], capture)
    need(actual == row, 'same-buffer descriptor differs')
    return raw

def fixed(path, pair, capture=False):
    row = {'path': str(path), 'bytes': pair[0], 'sha256': pair[1]}
    return exact(row, capture), row

def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)

def document(row):
    return parse(exact(row, True))

def write(path, value):
    path = Path(path)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)

def verify_held():
    for row in list(HELD.values()):
        exact(row)

def qualified_module(name, base, check_row=None):
    registry_local = next(row for row in base['local_checked_modules'] if row['module'] == name)
    check_pin = registry_local['qualification'] if check_row is None else check_row
    need(check_pin == registry_local['qualification'], 'exact declared qualified check registry required')
    raw = exact(check_pin, True)
    check = parse(raw)
    need(check['status'] == 'passed' and check['matches_expectation'] is True and check['expected_success'] is True
         and check['native_lean_returncode'] == 0 and check['native_invocations'] == 1
         and check['axiom_report_error'] is None and check['post_call_binding_error'] is None,
         'actual accepted native import required')
    queries = check['theorem_axiom_output']
    need(queries and all(row['report_occurrences'] == 2 and set(row['axioms']) <= {'Classical.choice', 'Quot.sound', 'propext'} for row in queries), 'qualified standard axioms required')
    registry = next(row for row in base['source_import_modules'] if row['module'] == name)
    local = next(row for row in base['local_checked_modules'] if row['module'] == name)
    need(local['qualification'] == check_pin and local['environment'] == check['environment_manifest']
         and registry['source'] == check['augmented_source'], 'existing qualified module registry differs')
    objects = []
    for row in check['compiled_artifacts']:
        need(row['complete'] is True, 'complete imported object required')
        descriptor = {key: row[key] for key in ('path', 'bytes', 'sha256')}
        exact(descriptor)
        objects.append(descriptor)
    need(objects == registry['compiled'] and len(objects) == 1 and Path(objects[0]['path']).name == name + '.olean', 'whole ordered import object registry differs')
    for row in (check['source'], check['augmented_source'], check['environment_manifest']):
        exact(row)
    retention = check['retention_manifest']
    need(retention['complete'] is True, 'complete import retention manifest required')
    manifest = document({key: retention[key] for key in ('path', 'bytes', 'sha256')})
    need(manifest == check['retention_manifest_body'] and manifest['schema'] == 'bounded_lean_chunks@1'
         and manifest['status'] == 'complete' and manifest['native_lean_returncode'] == 0,
         'same-buffer actual retained object manifest differs')
    chunks = check['retained_chunk_artifacts']
    need(len(chunks) == len(manifest['chunks']) <= 61 and len(manifest['objects']) == 1, 'complete bounded chunk population required')
    table, held_chunks = {}, {}
    for actual, declared in zip(chunks, manifest['chunks']):
        need(actual['complete'] is True and Path(actual['path']).name == declared['name'] and 0 < actual['bytes'] <= 65536
             and actual['bytes'] == declared['bytes'] and actual['sha256'] == declared['sha256'], 'import chunk descriptor differs')
        descriptor = {key: actual[key] for key in ('path', 'bytes', 'sha256')}
        need(declared['name'] not in table, 'duplicate import chunk name')
        table[declared['name']] = exact(descriptor, True)
        held_chunks[declared['name']] = descriptor
    obj = manifest['objects'][0]
    need(obj['name'] == Path(objects[0]['path']).name and obj['bytes'] == objects[0]['bytes'] and obj['sha256'] == objects[0]['sha256']
         and obj['chunks'] == list(table) and manifest['aggregate_raw_object_bytes'] == obj['bytes'] <= 3997696,
         'complete reconstructed historical object differs')
    joined = hashlib.sha256()
    total = 0
    for chunk in obj['chunks']:
        total += len(table[chunk])
        joined.update(table[chunk])
    need(total == obj['bytes'] and joined.hexdigest() == obj['sha256'], 'historical chunks do not reconstruct whole object')
    return {'module': name, 'qualification': check_pin, 'source': check['source'], 'augmented_source': check['augmented_source'],
            'compiled': objects, 'retention_manifest': {key: retention[key] for key in ('path', 'bytes', 'sha256')},
            'retained_chunks': list(held_chunks.values()), 'historical_complete_object_join_verified': True}

def _append_imports(base,imports):
    """Only dependency-prefix modules with whole native objects may be added."""
    need(type(imports) is list and len(imports)<=len(DEPENDENCY_MODULES)+len(MODE_ORDER),'finite declared dependency population required')
    new=dict(base)
    new['source_import_modules']=list(base['source_import_modules'])
    new['local_checked_modules']=list(base['local_checked_modules'])
    new['lean_path']=list(base['lean_path'])
    new['requested_imports']=list(base['requested_imports'])
    files={r['path']:r for r in base['files']};joined=[];seen=set()
    for row in imports:
        need(type(row) is dict and set(row)=={'mode','check_result'} and row['mode'] not in seen,
             'unique closed dependency mode descriptors required')
        seen.add(row['mode']);selected=dependency_module(row['mode']);name=selected['module']
        stage_root=Path(DEPENDENCY_ROOTS.get(row['mode'], str(ROOT)))
        need(stage_root in (ROOT, ROOT.with_name('ranker-objective-container-language-qualification-20261006-01'),
                            ROOT.with_name('ranker-objective-container-language-qualification-20261006-02')),
             'only three historical scalar-target stages or fresh declared AST modes allowed')
        expected=stage_root/'evidence'/row['mode']/'check-result.json'
        need(row['check_result']['path']==str(expected),'exact prior-stage qualified check path required')
        need(row['mode'] not in ACCEPTED_CHECK_PINS or row['check_result']==ACCEPTED_CHECK_PINS[row['mode']],
             'exact accepted prior-stage check descriptor required')
        check=document(row['check_result'])
        owned_row=pin(expected.with_name('closed.json'))
        outer_row=pin(stage_root/'evidence'/(row['mode']+'-closed.json'))
        owned=document(owned_row);outer=document(outer_row)
        invocation_row=pin(stage_root/'preparation'/(row['mode']+'-invocation.json'))
        invocation=document(invocation_row)
        need(invocation['mode']==row['mode'] and owned['mode']==row['mode']
             and owned['invocation']==outer['invocation']==invocation_row
             and owned['native_proof_checks']==[row['check_result']]
             and owned['native_checker_attempts']==[{'specification':invocation['specification'],
                                                    'native_invocations_observed':1}]
             and invocation['specification']['path']==str(stage_root/'preparation'/(row['mode']+'-check-specification.json')),
             'exact check/owned/outer/invocation staged execution joins required')
        specification=document(invocation['specification'])
        source_gate_row=DEPENDENCY_SOURCE_GATES.get(row['mode'], SOURCE_GATE);gate=document(source_gate_row)
        need(specification['selected_module']==selected
             and specification['independent_core_source_review']==source_gate_row
             and gate['status']=='passed_source_only' and gate['findings']==[]
             and gate['reviewed_modules'][row['mode']]==selected
             and all(gate[k] is False for k in AUTHORITY),
             'exact declared dependency source-review/selected-module join required')
        inherited=document(PRIOR_REQUEST)
        need(check['source']==specification['source'] and check['environment_manifest']==specification['environment_manifest']
             and check['actual_root_lease']==owned['root_lease']
             and owned['root_lease']['owner_pid']==outer['child_pid']
             and owned['original_checkout_guards_before']==owned['original_checkout_guards_after']==inherited['original_checkout_guards']
             and check['native_invocations']==check['native_lean_invocations']==1
             and check['native_bounds']=={'timeout_seconds':20,'cpu_seconds':20,'max_input_bytes':262144,
                                        'max_output_bytes':65536,'max_workspace_bytes':16777216}
             and owned['final_resource_state']['counters']['acquisitions_total']==1
             and owned['final_resource_state']['counters']['releases_total']==1
             and all(check[k] is owned[k] is False for k in AUTHORITY)
             and all(owned[k]==0 for k in ('native_preparation_calls','gradient_evaluations','optimizer_updates',
                                           'fit_calls','autoencoder_fit_calls','test_cases','metadata_hydration_calls',
                                           'source_function_executions','dependency_setup_calls')),
             'owned staged check must preserve exact native bounds/guards/lease and zero prohibited callbacks')
        need(owned['status']=='passed' and owned['root_release_returned'] is True
             and owned['cleanup_errors']==outer['cleanup_errors']==[] and outer['returncode']==0
             and owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0
             and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True,
             'prior staged module must be owned, closed and drained before import')
        need(check['status']=='passed' and check['native_lean_returncode']==0
             and check['source']['bytes']==selected['source']['bytes']
             and check['source']['sha256']==selected['source']['sha256']
             and [r['theorem'] for r in check['theorem_axiom_output']]==selected['queries'],
             'actual accepted source-bound staged module required')
        compiled=[{k:r[k] for k in ('path','bytes','sha256')} for r in check['compiled_artifacts']]
        need(len(compiled)==1 and all(r['module']!=name for r in new['source_import_modules']),
             'unique new qualified whole module required')
        new['source_import_modules'].append({'module':name,'source':check['augmented_source'],
                                             'compiled':compiled,'package':'locally-qualified'})
        new['local_checked_modules'].append({'module':name,'qualification':row['check_result'],
                                            'environment':check['environment_manifest']})
        new['lean_path']=[str(Path(compiled[0]['path']).parent),*new['lean_path']]
        new['requested_imports'].append(name)
        proof=qualified_module(name,new,row['check_result']);joined.append(proof)
        for r in [row['check_result'],owned_row,outer_row,invocation_row,invocation['specification'],source_gate_row,
                  proof['source'],proof['augmented_source'],proof['retention_manifest'],
                  *proof['compiled'],*proof['retained_chunks']]:
            need(r['path'] not in files or files[r['path']]==r,'qualified dependency body changed')
            exact(r);files[r['path']]=r
    new['files']=[files[p] for p in sorted(files)]
    new['external_file_count']=len(files)
    new['external_file_bytes']=sum(r['bytes'] for r in files.values())
    new['staged_qualified_imports']=joined
    return new,joined


# A single literal source review freezes these descriptors before any execution.
SOURCE_GATE=FROZEN['SOURCE_GATE']
STRICT_GUARD_COUNT=FROZEN['STRICT_GUARD_COUNT']

def module(mode):
    modules=document(FROZEN['MODULE_MAP'])
    need(type(mode) is str and mode in modules, 'exact frozen AST mode required')
    return modules[mode]

def dependency_module(mode):
    return DEPENDENCY_MODULES[mode] if mode in DEPENDENCY_MODULES else module(mode)

def source_gate(mode):
    selected=module(mode);gate=document(SOURCE_GATE)
    need(gate['status']=='passed_source_only' and gate['findings']==[]
         and gate['candidate_pins']==FROZEN['CANDIDATE_PINS']
         and gate['reviewed_modules']==document(FROZEN['MODULE_MAP'])
         and gate['candidate_compiled'] is False and gate['actual_new_qualified_queries']==0
         and all(gate[key] is False for key in AUTHORITY), 'exact reviewed unqualified scalar AST source gate required')
    for row in FROZEN['CANDIDATE_PINS'].values():exact(row)
    need(selected['source'] in FROZEN['CANDIDATE_PINS'].values(), 'selected AST source absent from gate')
    return gate

def complete_guard_union():
    gate=document(FROZEN['REPLAY_GATE'])
    need(gate['status']=='passed_source_only' and gate['findings']==[]
         and gate['reviewed_sources']==[FROZEN['REPLAY_SOURCE'],FROZEN['CHECKPOINT']]
         and all(gate[key] is False for key in AUTHORITY), 'exact independent checkpoint replay source gate required')
    raw=exact(FROZEN['REPLAY_SOURCE'], True)
    namespace={'__file__':FROZEN['REPLAY_SOURCE']['path'],'__name__':'held_standalone_checkpoint_replay'}
    exec(compile(raw,FROZEN['REPLAY_SOURCE']['path'],'exec'),namespace)
    result=namespace['replay'](FROZEN['CHECKPOINT'])
    need(result['status']=='passed_file_only' and result['historical_helpers_executed']==0
         and result['digest_cache_used'] is False, 'fresh complete historical closure replay required')
    checkpoint=document(FROZEN['CHECKPOINT']);inherited=document(PRIOR_REQUEST)
    rows={row['path']:row for row in checkpoint['closure']}
    for seal_pin in FROZEN['CONTEXT_SEALS']:
        seal=document(seal_pin);scope=Path(seal['scope_root']);leaves=seal['files']
        need(seal['schema']=='ranker-checkpoint-replay-failed-file-only-seal@1'
             and scope==WORKSPACE/'qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-01'
             and Path(seal_pin['path']).parent==scope
             and len(leaves)==seal['regular_file_count']==3
             and len({row['path'] for row in leaves})==3
             and seal['regular_file_bytes']==sum(row['bytes'] for row in leaves)
             and hashlib.sha256(json.dumps(leaves,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()==seal['file_inventory_sha256']
             and seal['seal_self_excluded_from_files'] is True
             and seal['fixture_symlinks']==seal['excluded_dependency_subtrees']==[]
             and all(Path(row['path']).is_relative_to(scope) for row in leaves)
             and all(seal[key] is False for key in AUTHORITY), 'exact unqualified failed replay context seal required')
        physical=list(scope.rglob('*'))
        need(scope.resolve(strict=True)==scope and not scope.is_symlink()
             and not any(path.is_symlink() for path in physical)
             and all(path.is_file() or path.is_dir() for path in physical)
             and {str(path) for path in physical if path.is_file()}=={row['path'] for row in leaves}|{seal_pin['path']},
             'complete preserved failed replay physical context differs')
        for row in [seal_pin,*leaves,seal['review']]:
            need(row['path'] not in rows or rows[row['path']]==row,'failed replay context overlaps changed body')
            exact(row);rows[row['path']]=row
    additions=[FROZEN['REPLAY_SOURCE'],FROZEN['CHECKPOINT'],FROZEN['REPLAY_GATE'],
               FROZEN['MODULE_MAP'],*FROZEN['CANDIDATE_PINS'].values(),SOURCE_GATE,*FROZEN['EXTRA_CONTEXT']]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']]==row,'overlapping current guarded descriptor differs')
        exact(row);rows[row['path']]=row
    need(len(rows)==STRICT_GUARD_COUNT, 'fixed current closure denominator differs')
    return [rows[path] for path in sorted(rows)],inherited

def validate_guard_union(request):
    rows,inherited=complete_guard_union()
    need(request['strict_old_inputs']==rows and request['strict_guard_count']==STRICT_GUARD_COUNT
         and request['protected_live_sources']==inherited['protected_live_sources']
         and request['original_checkout_guards']==inherited['original_checkout_guards']
         and request['prior_language_context_request']==PRIOR_REQUEST
         and request['prior_language_context_seal']==PRIOR_SEAL, 'complete checkpoint/current source union required')

def import_extension(base, imports):
    need(type(imports) is list and len(imports)>=3 and imports[:3]==PRIOR_IMPORTS
         and len(imports[3:])<=3
         and [row['mode'] for row in imports[3:]]==MODE_ORDER[:len(imports[3:])],
         'exact three historical target imports followed by declared completed AST prefix required')
    return _append_imports(base,imports)
