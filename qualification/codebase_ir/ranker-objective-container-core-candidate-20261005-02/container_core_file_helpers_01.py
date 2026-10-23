"""Standard-library file helpers for unexecuted container-core qualification tooling.

No project import or job occurs on loading this module. All native actions are
in the separately reviewed runner and require actual owned admission/lease.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
Q5 = ROOT.with_name('ranker-objective-ir-candidate-20261005-01')
V1 = ROOT.with_name('ranker-objective-container-core-candidate-20261005-01')
P7 = ROOT.with_name('ranker-objective-container-source-plan-20261005-01')
MODE = 'lean-objective-container-core-02'
QUERIES = (
    'RankerObjectiveContainerIR.map_exact_ofFn_success',
    'RankerObjectiveContainerIR.mean_exact_ofFn_success',
    'RankerObjectiveContainerIR.mean_exact_empty_refuses',
    'RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq',
)
CORE_PINS = {
    'math/ObjectiveContainerCore.lean': (6340, '9c3761eb4b778ed04349ae29ef84a4b93f1da36c0f8ef9b59e806805ff10c9b3'),
    'candidate-interface.json': (11720, '3dcd00fba002d0ad3e2ecb06a4146bbcc4a2d0212c212d5f71fae8562d85e7ac'),
    'source-model-obligations-01.json': (6615, 'f35f270b7cc77f41a62d52a30e8c1bf2da78ffdc9474fc1e70d3d02e2c1299b7'),
}
P7_PINS = {
    'source-plan.json': (17263, 'bb53075335968870fa9a2d0ca15c7d6d574f4e032343b598678bb907d4fd1ece'),
    'source-bindings.json': (25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'),
    'ir-interface.json': (6114, 'fa017de5018525c8853cb847fefb416f18fea99b66273f3e3a57c67b6e4ed5d8'),
}
SOURCE_GATE = {
    'path': str(WORKSPACE / 'maintenance/ranker-objective-container-core-patch-source-review-20261005-02/review-receipt.json'),
    'bytes': 5852,
    'sha256': '1cdfea8f580bc113a190a56720eef2b0baa335b7b5f59491aaaa7493fcdd8359',
}
BASE_PROFILE = {
    'path': str(V1 / 'preparation/lean-objective-container-core-01-producer/environment-manifest.json'),
    'bytes': 9976569,
    'sha256': 'ccd64014d7b3c9df828d25b28a6d27fb0a68fd4adac60c660b9a294bdd6f3d79',
}
IMPORT_CHECKS = {
    'ObjectiveScalarIR': (Q5 / 'evidence/lean-objective-scalar-01/check-result.json', '57ac502ebc37df08ae73b7fec69280b2dcb1a2453895ab573869d826d613bd5e'),
    'RealStableFactor': (ROOT.with_name('ranker-real-convergence-20261005-01') / 'evidence/lean-stable-factor-01/check-result.json', '25adf30103c3d7455df5c7fff9eedf6b9e4ceb1fbd5263e919247ed18588e0f5'),
    'TypedNumericSlice': (ROOT.with_name('ranker-source-semantics-20261005-01') / 'evidence/lean-typed-scalar-02/check-result.json', '1e11d2917e3087dc2e231bdf6b329416518eb74542d6e83074d000ee7f8a0e23'),
}
NATIVE_LIMITS = {'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}
ROOT_LEASE = {'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}
PRESSURE = {'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}
AUTHORITY = {key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}
STRICT_GUARD_COUNT = 2421
V1_REQUEST = {'path': str(V1 / 'preparation/request-v3.json'), 'bytes': 628543,
              'sha256': 'b1aba00577a79bb2e2818ddb426c3422d8247124b9fc274ae3a7620a4ff4e90d'}
V1_ATTEMPT_PINS = {
    'check_result': {'path': str(V1 / 'evidence/lean-objective-container-core-01/check-result.json'), 'bytes': 10128,
        'sha256': '9eea43fd7e1a67da9b135b84e3ad2646d5cbb42488baa3c31a8f74bcd86e4d80'},
    'owned_closed': {'path': str(V1 / 'evidence/lean-objective-container-core-01/closed.json'), 'bytes': 18690,
        'sha256': '37b775169ca4c2cc34a94b1dedfe33d30a5f438af63bb468536218da89168464'},
    'outer_closed': {'path': str(V1 / 'evidence/lean-objective-container-core-01-closed.json'), 'bytes': 1493,
        'sha256': '5155fef0434a8e0651b8acf3d2451940dbbbcb11ada27786b7e8e95fcc2907f1'},
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read_pin(path, capture=False):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical nonsymlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode), 'regular input required')
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
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and total == before.st_size, 'input changed during read')
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


def core_source_gate():
    gate = document(SOURCE_GATE)
    wanted = {name: {'path': str(ROOT / name), 'bytes': pair[0], 'sha256': pair[1]} for name, pair in CORE_PINS.items()}
    need(gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['candidate_pins'] == wanted
         and gate['reviewed_query_names'] == list(QUERIES) and gate['candidate_compiled'] is False
         and gate['candidate_native_qualified'] is False and gate['actual_new_qualified_queries'] == 0,
         'exact independent uncompiled core source gate required')
    need(all(gate[key] is False for key in AUTHORITY) and gate['all32_governing_RPI_exits'] == 'OPEN', 'source review cannot grant operational authority')
    for row in wanted.values():
        exact(row)
    return gate


def failed_v1_inputs(seal_pin):
    """Bind the externally pinned complete failed-v1 seal, without qualification."""
    need(type(seal_pin) is dict and seal_pin.get('path') == str(V1 / 'file-only-seal-01.json'),
         'exact failed-v1 seal path required')
    seal = document(seal_pin)
    need(seal['schema'] == 'ranker-objective-container-core-failed-v1-file-only-seal@1'
         and seal['scope_root'] == str(V1) and seal['fixture_symlinks'] == seal['excluded_dependency_roots'] == []
         and seal['seal_self_excluded_from_files'] is True
         and type(seal['regular_file_count']) is int and seal['regular_file_count'] == len(seal['files']) == 29
         and type(seal['regular_file_bytes']) is int
         and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files'])
         and seal['qualified_native_checks'] == seal['qualified_theorem_queries'] == 0
         and seal['native_attempts_retained'] == 1 and all(seal[key] is False for key in AUTHORITY),
         'complete failed-v1 seal must retain zero qualification and all files')
    wire = json.dumps(seal['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    need(hashlib.sha256(wire).hexdigest() == seal['file_inventory_sha256'], 'failed-v1 inventory digest differs')
    paths = [row['path'] for row in seal['files']]
    need(len(paths) == len(set(paths)) and all(Path(path).is_relative_to(V1) for path in paths)
         and seal_pin['path'] not in paths and seal['review']['path'] == str(V1 / 'failed-review-01.json')
         and seal['review'] in seal['files'], 'unique complete confined failed-v1 inventory required')
    observed = set()
    for path in V1.rglob('*'):
        need(not path.is_symlink(), 'failed-v1 aliases are forbidden')
        if path.is_file():
            observed.add(str(path))
        else:
            need(path.is_dir(), 'failed-v1 special files are forbidden')
    need(observed == set(paths) | {seal_pin['path']}, 'complete quiet failed-v1 physical census differs')
    for row in seal['files']:
        exact(row)
    review = document(seal['review'])
    need(review['schema'] == 'ranker-objective-container-core-failed-v1-closure@1'
         and review['status'] == 'closed_failed_native_attempt_without_qualification'
         and review['native_attempts'] == 1 and review['qualified_native_checks'] == review['qualified_theorem_queries'] == 0
         and review['candidate_native_qualified'] is False and review['guards_same'] is True
         and review['leases_drained'] is True and review['strict_input_count'] == 2391
         and review['protected_live_source_count'] == 4
         and review['prior_regular_file_count'] == 28 and review['prior_regular_file_bytes'] == 10850381
         and all(review[key] is False for key in AUTHORITY) and review['request'] == V1_REQUEST
         and all(review[key] == row for key, row in V1_ATTEMPT_PINS.items()),
         'actual failed-v1 review and fixed attempt pins required')
    need(sum(row['bytes'] for row in seal['files'] if row != seal['review']) == 10850381,
         'original failed-v1 complete 28-file byte denominator differs')
    inherited = document(V1_REQUEST)
    need(inherited['schema'] == 'terminal-ranker-objective-container-core-request@1'
         and inherited['exact_native_mode'] == 'lean-objective-container-core-01'
         and inherited['exact_theorem_names'] == list(QUERIES)
         and inherited['proof_limits'] == NATIVE_LIMITS and inherited['root_request'] == ROOT_LEASE
         and inherited['proof_pressure_limits'] == PRESSURE and inherited['outer_timeout_seconds'] == 120
         and inherited['native_retention_chunk_count_max'] == 61
         and inherited['native_retention_aggregate_raw_bytes_max'] == 3997696
         and inherited['original_checkout_guards'] == review['original_checkout_guards']
         and len(inherited['strict_old_inputs']) == len({row['path'] for row in inherited['strict_old_inputs']}) == 2391
         and len(inherited['protected_live_sources']) == 4,
         'unchanged actual failed-v1 request, guards and resource bounds required')
    check, owned, outer = [document(V1_ATTEMPT_PINS[key]) for key in ('check_result', 'owned_closed', 'outer_closed')]
    need(check['status'] == 'inconclusive' and check['native_invocations'] == check['native_lean_invocations'] == 1
         and check['native_lean_returncode'] == outer['returncode'] == 1
         and check['compiled_artifacts'] == check['retained_chunk_artifacts'] == []
         and owned['status'] == 'failed' and owned['cleanup_errors'] == outer['cleanup_errors'] == []
         and owned['root_release_returned'] is True
         and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True
         and owned['final_resource_state']['active_lease_count'] == owned['final_resource_state']['waiting_request_count'] == 0,
         'failed-v1 actual nonzero native attempt must remain unadmitted and drained')
    return inherited, seal, review


def complete_guard_union(seal_pin):
    inherited, seal, review = failed_v1_inputs(seal_pin)
    strict = {row['path']: row for row in inherited['strict_old_inputs']}
    additions = [*seal['files'], seal_pin]
    additions += [fixed(ROOT / name, pair)[1] for name, pair in CORE_PINS.items()]
    for row in additions:
        need(row['path'] not in strict or strict[row['path']] == row, 'overlapping historical guard differs')
        strict[row['path']] = row
    need(len(strict) == STRICT_GUARD_COUNT == 2421, 'actual deduplicated complete guard denominator differs')
    return [strict[path] for path in sorted(strict)], inherited, seal, review


def validate_guard_union(request):
    rows, inherited, seal, review = complete_guard_union(request['prior_failed_container_seal'])
    need(request['strict_old_inputs'] == rows
         and request['protected_live_sources'] == inherited['protected_live_sources']
         and request['prior_failed_container_request'] == V1_REQUEST
         and request['prior_failed_container_review'] == seal['review']
         and request['original_checkout_guards'] == inherited['original_checkout_guards'],
         'exact inherited failed-v1 plus complete sealed census and fresh core guard union required')


def qualified_module(name, base):
    path, expected_sha = IMPORT_CHECKS[name]
    raw, check_pin = read_pin(path, True)
    need(check_pin['sha256'] == expected_sha, 'fixed qualified import check differs')
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
