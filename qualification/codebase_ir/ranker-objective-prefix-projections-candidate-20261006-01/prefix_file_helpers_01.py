"""Fresh file-only helpers for the typed prefix qualification batch.

The old standard-library reader is held by its immutable pin. Its original
globals remain separate: the prior sealed guard union is checked as before.
New guards add complete sealed container evidence and prefix host artifacts.
No project import, compiler, scheduler, test or model runs on loading.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
Q6 = ROOT.with_name('ranker-objective-container-core-candidate-20261005-02')
Q5 = ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
MODE = 'lean-objective-prefix-projections-01'
QUERIES = ('RankerObjectivePrefixProjections.loss_denominator_compiles', 'RankerObjectivePrefixProjections.gradient_denominator_compiles', 'RankerObjectivePrefixProjections.weight_coordinate_compiles', 'RankerObjectivePrefixProjections.source_L2_compiles', 'RankerObjectivePrefixProjections.loss_denominator_source_eval', 'RankerObjectivePrefixProjections.gradient_denominator_source_eval', 'RankerObjectivePrefixProjections.weight_coordinate_source_eval', 'RankerObjectivePrefixProjections.source_L2_source_eval')
CORE_PINS = {'math/ObjectivePrefixProjections.lean': (4949, '0bb7b1057aac76aa3ceb43a8d7a4a537b4a77c88c85a0ee2fe13310246790846'), 'candidate-interface.json': (1805, '4601d7bfbc6cfb14e8abc12e3dcfbf956570773422c93ca4ae158c29b4c66e0e'), 'source-model-obligations-01.json': (1448, '2ee1f525d5bd845125e07d3875590ee5a7fe3ee22c773e28b2943f66826e4fdd')}
SOURCE_GATE = {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-projections-source-review-20261006-01/review-receipt.json', 'bytes': 2202, 'sha256': 'e8c6948ed5f2c03f63d84d4e7f717f4b8550271a47f317fc4141ce0ed634d4be'}
STRICT_GUARD_COUNT = 2610
OLD_HELPER = {'path': str(Q6 / 'container_core_file_helpers_01.py'), 'bytes': 17601,
              'sha256': '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a'}
BASE_REQUEST = {'path': str(Q6 / 'preparation/request-v3.json'), 'bytes': 637236,
                'sha256': '80c537b76529e328cad8f13b7b8e065c89c92958f5fa8690447f9a934858c96f'}
BASE_PROFILE = {'path': str(Q6 / 'preparation/lean-objective-container-core-02-producer/environment-manifest.json'),
                'bytes': 9978028, 'sha256': 'c1083d10bfb37747ba194848aa43624a9e55feeebdcd6ff77ee3db6b8e50f726'}
Q6_SEAL = {'path': str(Q6 / 'file-only-seal-01.json'), 'bytes': 11448,
           'sha256': 'a065d3bcf1469c4c41cade18bc240f978227b64df91ef7f6f1c079bfcbe18849'}
Q6_CHECK = {'path': str(Q6 / 'evidence/lean-objective-container-core-02/check-result.json'), 'bytes': 12328,
            'sha256': 'b698b4fbe82eec1184d2c59314912cbfb805bb89a87db02191d6d677c591eb41'}
PREVIOUS = (
 ('qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/objective-prefix-draft.json',13910,'4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'),
 ('qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/materialization-receipt.json',2426,'e846d7ab984a14e1d279965364360e9e8f72ab1ab0408ddff66cfefe09440430'),
 ('qualification/codebase_ir/ranker-objective-prefix-kernel-plan-20261005-01/plan-02.json',17527,'e03bd094708da43ba6a56339506e0b4009884c67bdb50ff2c093c7ea7944d1e4'),
 ('maintenance/ranker-objective-prefix-kernel-plan-final-review-20261005-01/review-receipt.json',10615,'def34af9afe58d2f9ebbedb1e62d803c54b875467a82b0663dfb29b422046a08'),
 ('maintenance/ranker-objective-container-prefix-progress-20261005-01/closed.json',5199,'f75a801d1fd2166ca8702e46be92d65e95bdbe6943655946682261bbd837942f'),
 ('maintenance/ranker-objective-prefix-progress-readback-20261005-01/review-receipt.json',8612,'a5c75a80af80f69e8797cd492eaa79420ddce5c1ddde1b18e60e53a2ab068772'),
 ('maintenance/ranker-objective-prefix-controls-20261005-01/run-01/closed.json',3787,'69445c990bcf7bcf6bc614cbbc68320249bc022c743f9e306da1b1dfdcf38505'),
 ('maintenance/ranker-objective-prefix-controls-20261005-01/run-01/junit.xml',3331,'e69fdee93b1e060560c600141d3b7a07a3ea81e753a3efcca6b4e9be4716bd2a'),
)
NATIVE_LIMITS = {'wall_seconds':20, 'cpu_seconds':20, 'output_bytes':65536, 'workspace_bytes':16777216}
ROOT_LEASE = {'cpu_slots':1, 'memory_mb':2048, 'child_process_slots':4}
PRESSURE = {'memory_percent':2.0, 'cpu_percent':50.0, 'io_percent':10.0}
AUTHORITY = {key:False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')}


def _old():
    path = Path(OLD_HELPER['path'])
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('canonical old standard-library helper required')
    with path.open('rb') as stream:
        raw = stream.read(OLD_HELPER['bytes'] + 1)
    if len(raw) != OLD_HELPER['bytes'] or hashlib.sha256(raw).hexdigest() != OLD_HELPER['sha256']:
        raise ValueError('immutable old standard-library helper differs')
    ns = {'__file__':str(path),'__name__':'held_previous_prefix_file_helpers'}
    exec(compile(raw,str(path),'exec'),ns)
    ns['exact'](OLD_HELPER)
    return ns


FAILED_PREFIX_SEAL = {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-kernel-candidate-20261006-01/file-only-seal-01.json', 'bytes': 7952, 'sha256': 'cb254001f75336797a02e06ca7f9f2204823535e4f1a661fae5a94a0c5bde59c'}

KERNEL_SEAL = {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-kernel-candidate-20261006-02/file-only-seal-01.json', 'bytes': 21087, 'sha256': '0d6af319a571269527593244b0c888d9bcd9da3242871503984ad317c74f1978'}
KERNEL_CHECK = {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-kernel-candidate-20261006-02/evidence/lean-objective-prefix-kernel-02/check-result.json', 'bytes': 32238, 'sha256': '3d0b885e02b551dc080cc61fd43362fecf3cd42062b01bf2cb1a424d77e6bbad'}
NEW_HOST_INPUTS = [{'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01/candidate-interface.json', 'bytes': 1245, 'sha256': '7572d4515d4699030e1e5cf286ebcb849a039247adb480611ecc32f9e92de318'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01/source-model-obligations-01.json', 'bytes': 978, 'sha256': 'ac31694a8e9f9795bcb7cdfc6facf712cf7d586373edf5acb7ebd2fd00a71f68'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01/source-v1/objective_prefix_decoder.py', 'bytes': 43818, 'sha256': '4939b0257334dabe239085946c8bc1a5706805df2b39f2f8108ea05ccf965965'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01/source-v1/test_objective_prefix_decoder.py', 'bytes': 17399, 'sha256': 'b0b28f880fcb2e7b0227fe8b37cff05ade0e8df46bfd54b3ff071e14ac496b58'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-host-result-20261006-01/ObjectivePrefixProjections.lean', 'bytes': 1119, 'sha256': 'e6e5d2b731d2280a6d194e5af4290d7dcf510af0852f9612d8f98aad9eeea8b6'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-host-result-20261006-01/decoded-prefix.json', 'bytes': 8497, 'sha256': 'bc63421e8c903b29bcda1ea7d42ae011e33dc117b205066d8d1d96afa46d4df1'}, {'path': '/home/barberb/lift_coding/qualification/codebase_ir/ranker-objective-prefix-decoder-host-result-20261006-01/materialization-receipt.json', 'bytes': 4790, 'sha256': 'bf7ad448d73e7c99102fab3138abf511d37932fe1e5ae702b01928da4b84e0ab'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-source-review-20261006-01/review-receipt.json', 'bytes': 3313, 'sha256': 'f33337a8c461e79247255cfe86116f28ba6920e883d90d70d5155aeb23dce62c'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-source-review-20261006-01/review-receipt.json', 'bytes': 968, 'sha256': 'e0bff8a2cd9507c478f367dbedd5d44ec023b2c119c72427b76d7e0c41e2a5ca'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/control-plan-01.json', 'bytes': 3612, 'sha256': 'd5f1bf3e226dbe3b1dbbc846a9fc2fc4447f49a1438ab923b87ec3c4b5ee2b8a'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run-01/closed.json', 'bytes': 3842, 'sha256': '231f2e877af63bb1eae6004d9843fa859d62b43c16519ac83cf00f403a076047'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run-01/held-source/objective_prefix_decoder.py', 'bytes': 43818, 'sha256': '4939b0257334dabe239085946c8bc1a5706805df2b39f2f8108ea05ccf965965'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run-01/held-source/test_objective_prefix_decoder.py', 'bytes': 17399, 'sha256': 'b0b28f880fcb2e7b0227fe8b37cff05ade0e8df46bfd54b3ff071e14ac496b58'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run-01/junit.xml', 'bytes': 2975, 'sha256': '684598ca0b7ba3ba08fd1b6b9b056737e82cc66d787aae354bc0dfd0e4856ff1'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run-01/pytest-stdout.log', 'bytes': 99, 'sha256': 'a4d0778a9ba058ff75b48cb3a145ac59e8c7ae9f3764db8fb6a0425c242bf8d2'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-controls-20261006-01/run_controls_01.py', 'bytes': 14817, 'sha256': '8709d765cde8205b6f9a976ca383beaad921f66d016b5266dda786c94ead425b'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-materialization-20261006-01/materialize_01.py', 'bytes': 6899, 'sha256': '278eee6ec09f7108f7de52bb4599cc83a742c085d3c30da30c1890398a901481'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-materialization-20261006-01/plan-01.json', 'bytes': 1138, 'sha256': '69424e52011c2f88e2220298c7718835910702506e11a3e9e56a47748cbb42e7'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-decoder-materialization-20261006-01/source-review-01.json', 'bytes': 1061, 'sha256': 'c6cd5416748d1c5a8d0c75097176c7dbb8e36209e79abc6eed67393742745876'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-source-review-20261006-02/review-receipt.json', 'bytes': 3019, 'sha256': '3c4d51b7e00db16c51e890d3a9d78fd1050c39a84c869a49867256b8c2c75d59'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-tooling-source-review-20261006-02/review-receipt.json', 'bytes': 2312, 'sha256': '40b2b9861236d4b11058962820cb8a4b3fb08ef7cab3666e2865d8a11a17b9e3'}, {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-input-review-20261006-02/review-receipt.json', 'bytes': 1280, 'sha256': '377de844397dd2c8cb8a6e3c86d827a2ead74c870eea0d5d4973ff023a9bbc34'}]

O = _old()
need, pin, exact, fixed, parse, document, write, read_pin, verify_held = (
    O[name] for name in ('need','pin','exact','fixed','parse','document','write','read_pin','verify_held'))


def core_source_gate():
    need(bool(QUERIES) and bool(CORE_PINS) and bool(SOURCE_GATE),'reviewed source pins have not been frozen')
    gate = document(SOURCE_GATE)
    wanted = {name:{'path':str(ROOT/name),'bytes':pair[0],'sha256':pair[1]} for name,pair in CORE_PINS.items()}
    need(gate['status'] == 'passed_source_only' and gate['findings'] == []
         and gate['candidate_pins'] == wanted and gate['reviewed_query_names'] == list(QUERIES)
         and gate['candidate_compiled'] is False and gate['candidate_native_qualified'] is False
         and gate['actual_new_qualified_queries'] == 0 and all(gate[k] is False for k in AUTHORITY),
         'independent exact unqualified prefix source review required')
    for row in wanted.values(): exact(row)
    return gate


def sealed_container():
    seal = document(Q6_SEAL)
    need(seal['scope_root'] == str(Q6) and seal['regular_file_count'] == len(seal['files']) == 34
         and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 11290575
         and seal['seal_self_excluded_from_files'] is True,
         'complete qualified container seal census differs')
    paths = [row['path'] for row in seal['files']]
    need(len(set(paths)) == len(paths) and Q6_SEAL['path'] not in paths
         and all(Path(p).is_relative_to(Q6) for p in paths),'unique confined container seal required')
    actual = set()
    for p in Q6.rglob('*'):
        need(not p.is_symlink(),'container alias refused')
        if p.is_file(): actual.add(str(p))
        else: need(p.is_dir(),'container special file refused')
    need(actual == set(paths)|{Q6_SEAL['path']},'complete immutable container physical census differs')
    wire = json.dumps(seal['files'],sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    need(hashlib.sha256(wire).hexdigest() == seal['file_inventory_sha256'],'container inventory digest differs')
    for row in seal['files']: exact(row)
    return seal


def complete_guard_union(unused=None):
    inherited = document(BASE_REQUEST)
    O['validate_guard_union'](inherited)
    seal = sealed_container()
    kernel = document(KERNEL_SEAL)
    kernel_root = Path(kernel['scope_root'])
    need(kernel['qualified_theorem_queries'] == 6 and len(kernel['files']) == kernel['regular_file_count'] == 75, 'actual sealed typed kernel required')
    need({str(p) for p in kernel_root.rglob('*') if p.is_file()} == {row['path'] for row in kernel['files']} | {KERNEL_SEAL['path']}
         and not any(p.is_symlink() for p in kernel_root.rglob('*')), 'complete typed kernel census differs')
    rows = {row['path']:row for row in inherited['strict_old_inputs']}
    additions = [*seal['files'],Q6_SEAL,OLD_HELPER,BASE_REQUEST,BASE_PROFILE,*kernel['files'],KERNEL_SEAL,*NEW_HOST_INPUTS]
    failed = document(FAILED_PREFIX_SEAL)
    failed_root = Path(failed['scope_root'])
    failed_paths = {row['path'] for row in failed['files']}
    need(failed['qualified_native_checks'] == failed['qualified_theorem_queries'] == 0
         and len(failed['files']) == failed['regular_file_count'] == 27
         and failed['regular_file_bytes'] == sum(row['bytes'] for row in failed['files']) == 10966926,
         'complete unqualified failed prefix seal required')
    need({str(p) for p in failed_root.rglob('*') if p.is_file()} == failed_paths | {FAILED_PREFIX_SEAL['path']}
         and not any(p.is_symlink() for p in failed_root.rglob('*')), 'complete failed prefix census differs')
    additions += [*failed['files'],FAILED_PREFIX_SEAL]
    additions += [{'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-input-review-20261006-01/review-receipt.json', 'bytes': 4029, 'sha256': '42c377bfc13ad2e9da675ae2b4ae6864ee7b18a43f39209ec20ea7eb98516787'}]
    additions += [{'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-tooling-source-review-20261006-01/review-receipt.json', 'bytes': 2116, 'sha256': 'a036e94cb8f8a6cbe9a32b4340d1430d93f4f7817d3259a3dee1cd4ba17a19ad'}]
    additions += [{'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-source-review-20261006-01/review-receipt.json', 'bytes': 2600, 'sha256': 'df79fbd991d56f19b8f631c0799d1899349cfaf7117cd43da8863e6cf7cecb20'}]
    additions += [{'path':str(WORKSPACE/path),'bytes':size,'sha256':sha} for path,size,sha in PREVIOUS]
    # Rejoin the complete descriptors in the saved root review and plan. This
    # is a finite document walk, not a loader/import or a source execution.
    def descriptors(value):
        if type(value) is dict:
            if set(value) == {'path','bytes','sha256'}:
                yield value
            else:
                for child in value.values(): yield from descriptors(child)
        elif type(value) is list:
            for child in value: yield from descriptors(child)
    for path,size,sha in PREVIOUS:
        if path.endswith(('/review-receipt.json','/plan-02.json','/closed.json')):
            row = {'path':str(WORKSPACE/path),'bytes':size,'sha256':sha}
            additions += list(descriptors(document(row)))
    additions += [fixed(ROOT/name,pair)[1] for name,pair in CORE_PINS.items()]
    for row in additions:
        need(row['path'] not in rows or rows[row['path']] == row,'overlapping historical guard differs')
        exact(row)
        rows[row['path']] = row
    return [rows[path] for path in sorted(rows)],inherited,seal


def validate_guard_union(request):
    rows,inherited,seal = complete_guard_union()
    need(len(rows) == STRICT_GUARD_COUNT and request['strict_guard_count'] == STRICT_GUARD_COUNT
         and request['strict_old_inputs'] == rows and request['protected_live_sources'] == inherited['protected_live_sources']
         and request['prior_container_request'] == BASE_REQUEST and request['prior_container_seal'] == Q6_SEAL
         and request['original_checkout_guards'] == inherited['original_checkout_guards'],
         'exact additive container/prefix guard union required')


def extended_base(base):
    """Register only the accepted whole container object, joined with its chunks."""
    check = document(Q6_CHECK)
    compiled = [{k:row[k] for k in ('path','bytes','sha256')} for row in check['compiled_artifacts']]
    need(len(compiled) == 1 and check['status'] == 'passed' and check['native_lean_returncode'] == 0,
         'actual qualified container module required')
    name = 'ObjectiveContainerCore'
    need(all(row['module'] != name for row in base['source_import_modules'])
         and all(row['module'] != name for row in base['local_checked_modules']), 'container registry must be a fresh addition')
    new = dict(base)
    new['source_import_modules'] = [*base['source_import_modules'],
        {'module':name,'source':check['augmented_source'],'compiled':compiled,'package':'locally-qualified'}]
    new['local_checked_modules'] = [*base['local_checked_modules'],
        {'module':name,'qualification':Q6_CHECK,'environment':check['environment_manifest']}]
    new['lean_path'] = [str(Path(compiled[0]['path']).parent),*base['lean_path']]
    new['requested_imports'] = [*base['requested_imports'],name]
    O['IMPORT_CHECKS'][name] = (Path(Q6_CHECK['path']),Q6_CHECK['sha256'])
    joined = O['qualified_module'](name,new)
    additions = [Q6_CHECK,joined['source'],joined['augmented_source'],joined['retention_manifest'],
                 *joined['compiled'],*joined['retained_chunks']]
    files = {row['path']:row for row in base['files']}
    for row in additions:
        need(row['path'] not in files or files[row['path']] == row,'container extension descriptor differs')
        exact(row); files[row['path']] = row
    new['files'] = [files[path] for path in sorted(files)]
    new['external_file_count'] = len(files)
    new['external_file_bytes'] = sum(row['bytes'] for row in files.values())
    kernel_check = document(KERNEL_CHECK)
    kernel_name = 'ObjectivePrefixIR'
    kernel_compiled = [{key:row[key] for key in ('path','bytes','sha256')} for row in kernel_check['compiled_artifacts']]
    need(kernel_check['status'] == 'passed' and kernel_check['native_lean_returncode'] == 0
         and len(kernel_compiled) == 1, 'actual complete qualified typed kernel required')
    new['source_import_modules'] += [{'module':kernel_name,'source':kernel_check['augmented_source'],'compiled':kernel_compiled,'package':'locally-qualified'}]
    new['local_checked_modules'] += [{'module':kernel_name,'qualification':KERNEL_CHECK,'environment':kernel_check['environment_manifest']}]
    new['lean_path'] = [str(Path(kernel_compiled[0]['path']).parent),*new['lean_path']]
    new['requested_imports'] += [kernel_name]
    O['IMPORT_CHECKS'][kernel_name] = (Path(KERNEL_CHECK['path']),KERNEL_CHECK['sha256'])
    kernel_join = O['qualified_module'](kernel_name,new)
    for row in [KERNEL_CHECK,kernel_join['source'],kernel_join['augmented_source'],kernel_join['retention_manifest'],*kernel_join['compiled'],*kernel_join['retained_chunks']]:
        need(row['path'] not in files or files[row['path']] == row,'kernel extension descriptor differs')
        exact(row); files[row['path']] = row
    new['files'] = [files[path] for path in sorted(files)]
    new['external_file_count'] = len(files)
    new['external_file_bytes'] = sum(row['bytes'] for row in files.values())
    new['qualified_prefix_import'] = kernel_join
    return new,joined


def qualified_module(name,base):
    return O['qualified_module'](name,base)
