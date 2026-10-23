"""File-only independent review of the quiet native-only container tooling."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
CORE = WORKSPACE / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
EXPECTED = {
    'container_core_file_helpers_01.py': (10418, '3e10a1311636adbb14106437d499a9202a1a026950a43d766d955e6880083478'),
    'prepare_container_request_01.py': (7899, '409221042c8b38cd2194e3a11231a3ace5a7c18af227a03f9eb424317f1777bd'),
    'freeze_container_profile_01.py': (7071, 'bbdcc8b3a52588fdf6b2159273e77760081df141bd2a6c721253811e5a7458cc'),
    'run_container_core_controls_01.py': (25951, 'd4118c13d4a6a61575914d39f91b19df09e8b90bf09e414bcd8b5048ea6e79d6'),
    'qualification-tooling-api-01.json': (8558, '0e4813c7beac70620ecceee5b12cdc52b91ea1f1a55d20a5ceb54cfdc4510283'),
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical non-symlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 262144, 'bounded regular source/review required')
        raw = b''
        while block := os.read(fd, 65536):
            need(len(raw) + len(block) <= 262144, 'source grew beyond bound')
            raw += block
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda item: tuple(getattr(item, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and len(raw) == before.st_size, 'source changed during read')
    finally:
        os.close(fd)
    pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(str(path) not in HELD or HELD[str(path)] == pin, 'held source changed')
    HELD[str(path)] = pin
    return raw, pin


def main():
    need(__debug__, 'unoptimized source reviewer required')
    bodies, pins, trees = {}, {}, {}
    for name, expected in EXPECTED.items():
        raw, pin = read(CORE / name)
        need((pin['bytes'], pin['sha256']) == expected, 'exact externally reviewed tooling pin differs')
        bodies[name], pins[name] = raw.decode(), pin
        if name.endswith('.py'):
            trees[name] = ast.parse(raw, filename=str(CORE / name))
    api = json.loads(bodies['qualification-tooling-api-01.json'])
    need(api['schema'] == 'ranker-objective-container-core-qualification-tooling-draft-API@1' and api['tooling_sources'] == {name: pin for name, pin in pins.items() if name.endswith('.py')}, 'draft API/source pins differ')
    need(api['mode'] == 'lean-objective-container-core-01' and api['native_query_count'] == len(api['exact_native_queries']) == 4, 'exact four-query mode required')
    need(api['candidate_compiled'] is False and api['candidate_native_qualified'] is False and api['outside_current_335_file_publication_selection'] is True, 'draft qualification/publication scope differs')
    for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation', 'formalization_authority', 'mutation_authority', 'omission_authority', 'strict_cache_admission', 'theorem_qualified'):
        need(api[key] is False, 'draft cannot grant authority or qualification')
    for key in ('actual_file_only_profile_preparations', 'actual_file_only_request_preparations', 'actual_native_jobs', 'actual_native_queries', 'actual_project_imports_or_target_source_executions', 'actual_remote_or_Git_mutations', 'actual_test_model_training_metadata_archive_codec_or_dependency_setup_jobs'):
        need(api[key] == 0, 'unexecuted source draft required')
    need(api['full_task_satisfaction'] == 'unknown' and api['all32_governing_RPI_exits'] == 'OPEN' and api['official_benchmark_score'] is None, 'open broad obligations required')
    gate_raw, gate_pin = read(api['independent_math_source_gate']['path'])
    need(gate_pin == api['independent_math_source_gate'] and gate_pin['sha256'] == 'a874e5bbf40e11e37e7754b7c9efe5ea95ef60d2a6958ee893671a002d62ee4c', 'genuine independent math source gate required')
    gate = json.loads(gate_raw)
    need(gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['candidate_pins'] == api['immutable_core_sources'], 'source math/interface gate differs')
    for pin in api['immutable_core_sources'].values():
        need(read(pin['path'])[1] == pin, 'immutable three-file core draft changed')
    observed = {str(path) for path in CORE.rglob('*') if path.is_file()}
    need(not any(path.is_symlink() for path in CORE.rglob('*')) and observed == {pin['path'] for pin in [*pins.values(), *api['immutable_core_sources'].values()]}, 'quiet eight-file draft census differs')
    need(sum(pin['bytes'] for pin in [*pins.values(), *api['immutable_core_sources'].values()]) == 81954, 'quiet draft bytes differ')
    allowed = {'__future__', 'argparse', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 're', 'stat', 'subprocess', 'sys', 'time', 'traceback', 'types'}
    for name, tree in trees.items():
        for node in tree.body:
            if isinstance(node, ast.Import):
                need(all(alias.name.split('.')[0] in allowed for alias in node.names), 'only stdlib top-level imports allowed')
            elif isinstance(node, ast.ImportFrom):
                need(node.module.split('.')[0] in allowed, 'only stdlib top-level imports allowed')
        if name != 'container_core_file_helpers_01.py':
            common = next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'COMMON' for target in node.targets))
            need(ast.literal_eval(common) == EXPECTED['container_core_file_helpers_01.py'], 'held stdlib helper external pin differs')
    runner = bodies['run_container_core_controls_01.py']
    need("mode == MODE" in runner and "choices=[MODE]" in runner and "fullname.rsplit('.', 1)[-1] == 'terminal_codebase_intent_ranker_training'" in runner, 'exact mode and ranker alias refusal required')
    need(runner.count('module.compile_analytic_lean(') == 1 and 'lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)' in runner, 'one owned existing native callback and unchanged root lease required')
    need("receipt['original_checkout_guards_before'] = verify(h, f, request)" in runner and runner.count("receipt['original_checkout_guards_after'] = verify(h, f, request)") == 2 and "record['original_checkout_guards_after'] = checkout_guards(f, request)" in runner, 'original checkout guards must cover success, failure and outer closure')
    need("state['active_lease_count'] == state['waiting_request_count'] == 0" in runner and 'lease.release()' in runner and 'os.killpg(child.pid' in runner, 'owned cleanup/drain and timeout process-group cleanup required')
    profile = bodies['freeze_container_profile_01.py']
    need("all(files[path] == row for path, row in old_files.items())" in profile and "profile['source_import_modules'] == base['source_import_modules']" in profile and "profile['lean_path'] == base['lean_path']" in profile, 'frozen dependency and loader registries cannot change')
    helper = bodies['container_core_file_helpers_01.py']
    need("obj['chunks'] == list(table)" in helper and "joined.hexdigest() == obj['sha256']" in helper and '0 < actual[\'bytes\'] <= 65536' in helper, 'whole imported objects require ordered complete chunk reconstruction')
    request = bodies['prepare_container_request_01.py']
    need('len(strict) == 2391' in request and '== 2108' in request and "*seal['files'], seal_pin" in request and '== 4458' in request, 'all historical guards and metadata context required')
    need(api['unchanged_limits'] == {'native_CPU_seconds': 20, 'native_combined_output_bytes': 65536, 'native_new_raw_object_aggregate_bytes_max': 3997696, 'native_per_file_capture_bytes': 65536, 'native_retention_chunks_max': 61, 'native_wall_seconds': 20, 'native_workspace_bytes': 16777216, 'outer_wall_seconds': 120, 'proof_pressure': {'backoff_seconds': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0, 'memory_percent': 2.0}, 'root_lease': {'child_process_slots': 4, 'cpu_slots': 1, 'memory_mb': 2048}}, 'native/resource bounds changed')
    for pin in list(HELD.values()):
        need(read(pin['path'])[1] == pin, 'reviewed source changed before closure')
    receipt = {'schema': 'ranker-objective-container-core-independent-tooling-source-review@1', 'status': 'passed_source_only', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': read(Path(__file__).resolve())[1], 'reviewed_input_pins': list(HELD.values()), 'tooling_source_pins': pins, 'independent_math_source_review': gate_pin, 'findings': [], 'source_AST_syntax_parses': 4, 'target_imports': 0, 'native_or_test_or_model_or_metadata_or_remote_jobs': 0, 'tooling_executed': False, 'qualification_claimed': False, 'original_and_protected_scope_guard_policy_reviewed': True, 'exact_mode_and_four_query_policy_reviewed': True, 'complete_import_objects_and_ordered_chunks_reviewed': True, 'limits_unchanged': True, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None, **{key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}}
    destination = ROOT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': receipt['status'], 'receipt': read(destination)[1], 'native_jobs': 0}))


if __name__ == '__main__':
    main()
