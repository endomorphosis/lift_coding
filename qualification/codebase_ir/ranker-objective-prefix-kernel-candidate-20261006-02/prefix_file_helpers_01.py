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
MODE = 'lean-objective-prefix-kernel-02'
QUERIES = ('RankerObjectivePrefixIR.compile_term_sound', 'RankerObjectivePrefixIR.compile_prefix_sound', 'RankerObjectivePrefixIR.compile_unknown_name_refuses', 'RankerObjectivePrefixIR.if_nonneg_selected_branch_only', 'RankerObjectivePrefixIR.map_exact_success_length', 'RankerObjectivePrefixIR.zip_exact_success_min_length')
CORE_PINS = {'math/ObjectivePrefixIR.lean': (28749, '0b5960fc6f7376ca14ae698dea773f1d4ef163f5f4c3c76f46cddb927518d824'), 'candidate-interface.json': (2333, '372eda66d56819cad1cf74507013434b9a07a07b8d2b0688a2f737141933506d'), 'source-model-obligations-01.json': (2836, 'd97ac4c46e34cd2052174482c25a4af581f4707be9af8274f7b599e60a4bac4a')}
SOURCE_GATE = {'path': '/home/barberb/lift_coding/maintenance/ranker-objective-prefix-kernel-source-review-20261006-02/review-receipt.json', 'bytes': 3019, 'sha256': '3c4d51b7e00db16c51e890d3a9d78fd1050c39a84c869a49867256b8c2c75d59'}
STRICT_GUARD_COUNT = 2512
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
    rows = {row['path']:row for row in inherited['strict_old_inputs']}
    additions = [*seal['files'],Q6_SEAL,OLD_HELPER,BASE_REQUEST,BASE_PROFILE]
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
    return new,joined


def qualified_module(name,base):
    return O['qualified_module'](name,base)
