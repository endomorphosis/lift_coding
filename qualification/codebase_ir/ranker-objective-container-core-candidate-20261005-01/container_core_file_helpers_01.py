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
P7 = ROOT.with_name('ranker-objective-container-source-plan-20261005-01')
MODE = 'lean-objective-container-core-01'
QUERIES = (
    'RankerObjectiveContainerIR.map_exact_ofFn_success',
    'RankerObjectiveContainerIR.mean_exact_ofFn_success',
    'RankerObjectiveContainerIR.mean_exact_empty_refuses',
    'RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq',
)
CORE_PINS = {
    'math/ObjectiveContainerCore.lean': (6368, '9f6f36352ec1b45bb8d797cae03683455fcd03d1c3e7663a1991378baeb8da14'),
    'candidate-interface.json': (10393, 'bb3a85da75cde507dbc989760e210701fbfb5f6dd0c86ed5e0604488a8770bcc'),
    'source-model-obligations-01.json': (5296, '132ebd3f91a924bcf5999324021534ac4394d9a70f1169ccae01a0dca720226c'),
}
P7_PINS = {
    'source-plan.json': (17263, 'bb53075335968870fa9a2d0ca15c7d6d574f4e032343b598678bb907d4fd1ece'),
    'source-bindings.json': (25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'),
    'ir-interface.json': (6114, 'fa017de5018525c8853cb847fefb416f18fea99b66273f3e3a57c67b6e4ed5d8'),
}
SOURCE_GATE = {
    'path': str(WORKSPACE / 'maintenance/ranker-objective-container-core-source-review-20261005-01/review-receipt.json'),
    'bytes': 83712,
    'sha256': 'a874e5bbf40e11e37e7754b7c9efe5ea95ef60d2a6958ee893671a002d62ee4c',
}
BASE_PROFILE = {
    'path': str(Q5 / 'preparation/lean-objective-generated-01-producer/environment-manifest.json'),
    'bytes': 9974503,
    'sha256': 'e4c60649f7dcfca035af7842d5f6298d773d88bd769543a8fd2591195e6c3901',
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
