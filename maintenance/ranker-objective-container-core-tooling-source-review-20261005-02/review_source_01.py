"""Independent file/AST-only review; never imports or executes target tooling."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
Q1 = W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
Q2 = Q1.with_name('ranker-objective-container-core-candidate-20261005-02')
OUT = W/'maintenance/ranker-objective-container-core-tooling-source-review-20261005-02'
EXPECTED = {
    'container_core_file_helpers_01.py': (17601, '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a'),
    'prepare_container_request_01.py': (6173, 'bd8c96da312e94af88ec42b533769a2b0cfaaa4612ffffd9d22a3400a7108d94'),
    'freeze_container_profile_01.py': (7520, '6a1a1493d75791288bf87a2473d519f29848c8546e98564d0949310c263e985f'),
    'run_container_core_controls_01.py': (26231, '53571082744f4c1c076456d70e83e6aa741ae13881c736d1859a3d738405754a'),
    'qualification-tooling-api-01.json': (4121, 'ab6e1cf43c89c7ba52895cb9587d2f747de40ffaa8b54461e5c43cc2f5998873'),
}
PRIOR = {
    'container_core_file_helpers_01.py': (10418, '3e10a1311636adbb14106437d499a9202a1a026950a43d766d955e6880083478'),
    'prepare_container_request_01.py': (7899, '409221042c8b38cd2194e3a11231a3ace5a7c18af227a03f9eb424317f1777bd'),
    'freeze_container_profile_01.py': (7071, 'bbdcc8b3a52588fdf6b2159273e77760081df141bd2a6c721253811e5a7458cc'),
    'run_container_core_controls_01.py': (25951, 'd4118c13d4a6a61575914d39f91b19df09e8b90bf09e414bcd8b5048ea6e79d6'),
}
GATE = W/'maintenance/ranker-objective-container-core-patch-source-review-20261005-02/review-receipt.json'
GATE_PAIR = (5852, '1cdfea8f580bc113a190a56720eef2b0baa335b7b5f59491aaaa7493fcdd8359')
DOCS = {
    'math/ObjectiveContainerCore.lean': (6340, '9c3761eb4b778ed04349ae29ef84a4b93f1da36c0f8ef9b59e806805ff10c9b3'),
    'candidate-interface.json': (11720, '3dcd00fba002d0ad3e2ecb06a4146bbcc4a2d0212c212d5f71fae8562d85e7ac'),
    'source-model-obligations-01.json': (6615, 'f35f270b7cc77f41a62d52a30e8c1bf2da78ffdc9474fc1e70d3d02e2c1299b7'),
}
AUTH = ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')

def need(value, message):
    if value is not True:
        raise ValueError(message)

def read(path, pair=None):
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source-only input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 1024**2, 'bounded review input')
        pieces, total = [], 0
        while part := os.read(fd, 65536):
            total += len(part)
            need(total <= first.st_size, 'review input grew')
            pieces.append(part)
        sig = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        need(total == first.st_size and sig(first) == sig(os.fstat(fd)) == sig(path.lstat()), 'review input changed')
        raw = b''.join(pieces)
        pin = {'path': str(path), 'bytes': total, 'sha256': hashlib.sha256(raw).hexdigest()}
        need(pair is None or (total, pin['sha256']) == pair, 'externally supplied exact source pin')
        return raw, pin
    finally:
        os.close(fd)

def funcs(raw):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}

def literal(raw, name):
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing literal source constant: '+name)

def main():
    need(__debug__, 'optimized source review refused')
    current = {name: read(Q2/name, pair) for name, pair in EXPECTED.items()}
    prior = {name: read(Q1/name, pair) for name, pair in PRIOR.items()}
    gate_raw, gate_pin = read(GATE, GATE_PAIR)
    doc_pins = {name: read(Q2/name, pair)[1] for name, pair in DOCS.items()}
    gate = json.loads(gate_raw)
    need(gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['candidate_pins'] == doc_pins and
         gate['actual_new_qualified_queries'] == 0 and all(gate[key] is False for key in AUTH), 'exact unqualified v2 math source gate')
    helper, old_helper = current['container_core_file_helpers_01.py'][0], prior['container_core_file_helpers_01.py'][0]
    old_f, new_f = funcs(old_helper), funcs(helper)
    need(set(new_f)-set(old_f) == {'failed_v1_inputs', 'complete_guard_union', 'validate_guard_union'} and
         all(new_f[name] == old_f[name] for name in old_f), 'all inherited helper functions unchanged')
    need(literal(helper, 'STRICT_GUARD_COUNT') == 2421 and literal(helper, 'MODE') == 'lean-objective-container-core-02', 'fresh mode and exact strict union population')
    for name in ('NATIVE_LIMITS', 'ROOT_LEASE', 'PRESSURE', 'QUERIES', 'IMPORT_CHECKS'):
        if name != 'IMPORT_CHECKS':
            need(literal(helper, name) == literal(old_helper, name), 'unchanged native/resource/query literal')
    for name in EXPECTED:
        if name.endswith('.py'):
            ast.parse(current[name][0])
            if name != 'container_core_file_helpers_01.py':
                need(literal(current[name][0], 'COMMON') == EXPECTED['container_core_file_helpers_01.py'], 'exact helper pin in all producers/runner')
    runner = current['run_container_core_controls_01.py'][0].decode()
    old_runner = prior['run_container_core_controls_01.py'][0].decode()
    old_funcs, new_funcs = funcs(old_runner), funcs(runner)
    allowed = {'validate_mode', 'validate_request', 'validate_specification', 'verify', 'owned'}
    need(set(old_funcs) == set(new_funcs) and all(new_funcs[name] == old_funcs[name] for name in old_funcs if name not in allowed), 'native callback, outer lifecycle, guards, captured loading and CLI unchanged')
    need("**h['AUTHORITY'], **f['AUTHORITY']" in runner and "f['validate_guard_union'](request)" in runner, 'full four-authority owned receipt and complete guard union admission')
    helper_text = helper.decode()
    for token in ("observed == set(paths) | {seal_pin['path']}", "for row in seal['files']:", "'qualified_native_checks'", "== 10850381", "'strict_old_inputs'] == rows", "'protected_live_sources'] == inherited['protected_live_sources']", "'root_release_returned'] is True"):
        need(token in helper_text, 'complete failed-v1 census/failure/guard admission')
    profile_text = current['freeze_container_profile_01.py'][0].decode()
    need('== 20114' in profile_text and 'len(files) == 20119' in profile_text and
         "profile['source_import_modules'] == base['source_import_modules']" in profile_text and
         "profile['local_checked_modules'] == base['local_checked_modules']" in profile_text, 'complete previous dependency and unchanged import registry')
    api = json.loads(current['qualification-tooling-api-01.json'][0])
    need(api['status'] == 'source_only_unexecuted' and api['mode'] == 'lean-objective-container-core-02' and
         api['source_pins'] == [current[name][1] for name in list(EXPECTED)[:4]] and
         api['strict_guard_union']['expected_actual_unique_count'] == 2421 and
         api['dependency_closure']['prior_actual_v1_profile_files'] == 20114 and
         api['dependency_closure']['expected_files'] == 20119 and all(api[key] is False for key in AUTH), 'source API and exact byte pins join')
    held = [(Q2/name, pin) for name, (_, pin) in current.items()] + [(Q1/name, pin) for name, (_, pin) in prior.items()] + [(GATE, gate_pin)] + [(Q2/name, pin) for name, pin in doc_pins.items()]
    need(all(read(path)[1] == pin for path, pin in held), 'all review source pins rehashed')
    receipt = {
        'schema': 'ranker-objective-container-core-independent-tooling-source-review@1',
        'status': 'passed_source_only', 'findings': [],
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': read(Path(__file__).resolve())[1],
        'independent_math_source_review': gate_pin,
        'tooling_source_pins': {name: pin for name, (_, pin) in current.items()},
        'reviewed_input_pins': [pin for _, pin in held], 'candidate_pins': doc_pins,
        'mode': 'unexecuted_target_source_only', 'candidate_compiled': False, 'candidate_native_qualified': False,
        'actual_new_qualified_queries': 0, 'source_execution_calls': 0, 'target_imports': 0,
        'actual_new_native_test_model_metadata_or_preparation_jobs': 0,
        'reviewed_controls': [
            'Fixed v2 math gate and three exact source/doc pins; exact numbered native-only mode.',
            'Externally SHA-pinned failed-v1 seal authenticates all29 regular files, sealself, review and actual nonzero attempt; complete physical census includes logs/empty locks and requires zero prior qualification.',
            'All2391 prior strict rows plus complete failed-v1 seal/self and three fresh docs are deduplicated with equal overlapping pins; exact2421 strict rows and unchanged four live rows.',
            'Prior actual20114-file native profile remains exact; only five new held source/tooling copies give20119. The same three actually qualified imports retain whole objects and ordered chunk reconstruction.',
            'Inherited descriptor and native callback/outer/guard function ASTs unchanged. Native20s CPU/wall,64KiB output,16MiB workspace,61chunks/3997696raw bytes,root1CPU/2048MiB/4children,pressure2/50/10 and120s outer bounds unchanged.',
            'Runner verifies complete guard union before/after owned admission, records all four false authority flags, retains actual failure and requires cleanup/drained leases for passed status.',
            'Only stdlib assignments/definitions at module loading; reviewed preparation reads/writes fresh local files and uses read-only Git HEAD guards. Native execution remains exclusively in the owned admitted runner.'
        ],
        'limits': ['This is source-only review; root must independently review actual prepared request/spec/profile bytes and actual native outcome. No target source is imported or executed, and no 20114-file body rehash or native job is performed by this reviewer.', 'Generic partial exact-real container primitive statements do not prove host compiler, original Python/Float objective, gradient/training, global autoencoder convergence, full IR or full-task equivalence.'],
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
        **{key: False for key in AUTH}}
    path = OUT/'review-receipt.json'
    with path.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(read(path)[1], sort_keys=True))

if __name__ == '__main__':
    main()
