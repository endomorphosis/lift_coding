"""Source/JSON/std-filesystem review only; never import reviewed producers."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
Q = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
OUT = Path(__file__).resolve().parent
PRIOR = Q.with_name('ranker-real-convergence-20261005-01')
CURVATURE = Q.with_name('ranker-real-curvature-20261005-01')
TRACE = Q.with_name('ranker-trace-authentication-20261005-01')


def require(value, message):
    if not value:
        raise ValueError(message)


held = {}


def read(path):
    path = Path(path).absolute()
    require(path.resolve(strict=True) == path, 'alias in review input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'nonregular review input')
        blocks = []
        while block := os.read(fd, 1024**2):
            blocks.append(block)
        raw = b''.join(blocks)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda item: tuple(getattr(item, field) for field in fields)
        require(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()), 'review input changed')
        require(len(raw) == before.st_size, 'review input truncated')
    finally:
        os.close(fd)
    held[str(path)] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return raw


def pin(path):
    read(path)
    return held[str(Path(path).absolute())]


def load(path):
    return json.loads(read(path))


def function(module, name):
    return next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name)


def has(text, fragments, label):
    for fragment in fragments:
        require(fragment in text, label + ' missing ' + fragment)


def main():
    producer_paths = [Q / 'run_source_semantics_controls.py', Q / 'freeze_source_profile_01.py', Q / 'prepare_request_01.py']
    raw = {path.name: read(path) for path in producer_paths}
    texts = {name: body.decode() for name, body in raw.items()}
    require(hashlib.sha256(raw['run_source_semantics_controls.py']).hexdigest() == '362a6ad08063f9920b114f4a68edba87c732b1e5e3e3a24e6f9ba01a96a590f4', 'owner-bound final harness source')
    require(hashlib.sha256(raw['freeze_source_profile_01.py']).hexdigest() == '82d36418fc74f5b32ea759b11b2af92aadc6c3d683f4a4cdafbc72edba781de8', 'owner-bound final freezer source')
    trees = {name: ast.parse(text) for name, text in texts.items()}
    harness = texts['run_source_semantics_controls.py']
    htree = trees['run_source_semantics_controls.py']
    owned = ast.unparse(function(htree, 'owned'))
    compile_body = ast.unparse(function(htree, 'compile_source_slices'))
    tests_body = ast.unparse(function(htree, 'pure_tests'))
    dispatch = []
    for node in ast.walk(function(htree, 'owned')):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'startswith' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'mode':
            require(len(node.args) == 1 and isinstance(node.args[0], ast.Constant), 'dispatch must use literal prefixes')
            dispatch.append(node.args[0].value)
    require(sorted(dispatch) == ['compile-source', 'lean', 'metadata', 'pure-tests'], 'only four authorized dispatch families')
    require(not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'extract', 'numeric', 'dependencies', 'environment_capture', 'cache_joins'} for n in ast.walk(function(htree, 'owned'))), 'old numerical/setup dispatch reachable')
    has(owned, ["verify(h, request)", "guard.records.items()", "expected[descriptor['path']] = descriptor", "scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)", "state['active_lease_count'] == state['waiting_request_count'] == 0", "lease.release()"], 'owned profile')
    require(owned.count('verify(h, request)') == 2, 'before/after inherited verification')
    has(harness, ['terminal_codebase_intent_ranker_training', 'source semantics phase only permits AST compilation, pure tests, Lean and metadata', 'if not __debug__:', '2.0, 50.0, 10.0, 2.0', 'timeout=120'], 'guard/pressure/outer')
    has(owned, ['class SourceSliceGuard', "fullname == 'benchmarks.agent_supervisor.container_coding.terminal_codebase_intent_ranker_training'", 'self.blocked.append', "raise ImportError('source-slice qualification refuses ranker module import')", 'super().find_spec(fullname, path, target)', 'guard = SourceSliceGuard(expected)'], 'explicit ranker import refusal')
    has(compile_body, ["source_bytes = h['read_pinned'](spec['source'])", "api.compile_ranker_slices(source_bytes, **spec['arguments'])", "api.render_generated_lean(result, source_bytes)", "h['read_pinned'](spec['difference_artifact'])", "len(generated.encode()) <= 262144", "receipt['source_AST_parse_calls'] = 2", "receipt['source_function_execution_calls'] = 0"], 'same-buffer AST compilation')
    require('_prepare(' not in compile_body and '_objective(' not in compile_body and '_dot(' not in compile_body, 'no ranker numerical recomputation')
    has(tests_body, ['BoundedToolRunner.run = forbidden_run', 'subprocess', "('Popen', 'run', 'check_call', 'check_output', 'call')", 'setattr(subprocess, name, forbidden_process)', 'BoundedToolRunner.run = original', 'setattr(subprocess, name, function)', "receipt['native_runner_calls_refused'] == 0", "receipt['direct_process_calls_refused'] == 0"], 'pure controls process refusal')
    # Last metadata definition shadows inherited dead helper and owns 4417-prefix handling.
    metadata_nodes = [n for n in htree.body if isinstance(n, ast.FunctionDef) and n.name == 'metadata']
    metadata = ast.unparse(metadata_nodes[-1])
    has(metadata, ["len(prior) == len(records) == 32", "sum(map(len, prior.values())) == 4417", "records[family][:len(values)] == values", "records['contracts'] == prior['contracts']", "records['vectors'] == prior['vectors']", "native['fresh_process_readback']['verified'] is True", 'exported == values'], 'metadata closure')
    freeze = texts['freeze_source_profile_01.py']
    has(freeze, ['ranker-real-convergence-20261005-01', 'lean-original-convergence-02-producer/environment-manifest.json', 'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084', '04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4', 'ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66', '1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f', 'body["native_per_file_capture_bytes_unchanged"] == 65536', 'body["root_reconstructed_external_module_aggregate_max_bytes"] == 3997696', 'captured.chmod(0o444)', 'profile.chmod(0o444)', 'pin(original) == before', 'sources[3]["captured"]'], 'freezer profile')
    require('base_raw' in freeze and 'json.loads(base_raw)' in freeze, 'base parsed from digest-bound buffer')
    require('check_raw' in freeze and 'json.loads(check_raw)' in freeze, 'prior checks parsed from digest-bound buffer')
    require('args.mode' in freeze and ('isidentifier' in freeze or 'fullmatch' in freeze or 'Path(args.mode).name' in freeze), 'new-mode path scope validation')
    mutations = [ast.unparse(n.func) for n in ast.walk(trees['freeze_source_profile_01.py']) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {'chmod', 'unlink', 'rename', 'replace', 'rmdir'}]
    require(mutations == ['profile.chmod', 'captured.chmod'] or sorted(mutations) == ['captured.chmod', 'profile.chmod'], 'permissions changed only on new copies/profile')
    request_path = Q / 'preparation/request-v3.json'
    request = load(request_path)
    require(held[str(request_path)]['sha256'] == '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861' and held[str(request_path)]['bytes'] == 478981, 'externally bound current request')
    require(len(request['strict_old_inputs']) == 1808 and len(request['protected_live_sources']) == 4, 'guard denominators')
    for binding in request['strict_old_inputs'] + request['protected_live_sources']:
        require(pin(binding['path']) == binding, 'inherited/live guard byte binding')
    require(request['proof_limits'] == {'wall_seconds': 20, 'cpu_seconds': 20, 'output_bytes': 65536, 'workspace_bytes': 16777216}, 'native caps unchanged')
    require(request['root_request'] == {'cpu_slots': 1, 'memory_mb': 2048, 'child_process_slots': 4}, 'root lease unchanged')
    require(request['proof_pressure_limits'] == {'memory_percent': 2.0, 'cpu_percent': 50.0, 'io_percent': 10.0}, 'pressure caps unchanged')
    require(request['prior_metadata_inputs']['sha256'] == 'c0f5ab88db02ff6b59d36f5dbce63c99a8fc09414f2eedbab6c4116241881f41', 'prior metadata binding')
    prior_metadata = load(request['prior_metadata_inputs']['path'])
    require(len(prior_metadata) == 32 and sum(map(len, prior_metadata.values())) == 4417, 'prior metadata census')
    for field in ['proof_authority', 'execution_authority', 'completion_authority', 'planner_activation', 'full_source_runtime_equivalence', 'source_interpreter_semantics_proved', 'binary64_error_bound_proved', 'native_Float_optimizer_convergence_proved', 'global_autoencoder_convergence_proved']:
        require(request[field] is False, 'request authority/scope field ' + field)
    base = PRIOR / 'preparation/lean-original-convergence-02-producer/environment-manifest.json'
    require(pin(base)['sha256'] == 'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084', 'actual inherited native base')
    trace_seal = load(TRACE / 'file-only-seal-01.json')
    helper = TRACE / 'run_trace_controls_02.py'
    require(pin(TRACE / 'file-only-seal-01.json')['sha256'] == '8ea31286ffda2a5f08b4820bcc6ccf9ee05f133b96018132378f8c96ec16f438', 'sealed std helper source')
    require(pin(helper) == next(row for row in trace_seal['files'] if row['path'] == str(helper)), 'helper exact sealed pin')
    before = dict(held)
    require(all(pin(path) == binding for path, binding in before.items()), 'whole reviewed input pins unchanged before/after')
    report = {'schema': 'ranker-source-semantics-harness-independent-source-review@1', 'status': 'passed_source_only_review', 'outstanding_issues': [], 'review_source': pin(Path(__file__).resolve()), 'reviewed_producers': [held[str(p)] for p in producer_paths], 'request': held[str(request_path)], 'input_pin_count': len(before), 'strict_old_inputs': 1808, 'protected_live_sources': 4, 'dispatch_prefixes': sorted(dispatch), 'inherited_dead_functions_unreachable_from_authorized_dispatch': ['prepare', 'extract', 'numeric', 'dependencies', 'environment_capture', 'cache_joins', 'first metadata definition'], 'findings': ['Original ranker module imports explicitly refused by owned guard.', 'Compile phase uses one pinned source buffer for compiler and renderer, with two AST parses and zero source execution.', 'Pure controls refuse bounded native runner and direct subprocess calls, restoring patches in finally.', 'Owned source guard rechecks selected captured source imports and inherited/live leaves before and after; lease released and zero active/waiting leases required.', 'Freezer uses qualified Q3 final closure, digest-bound base/prior JSON buffers, safe new mode path, and writes/chmods only new captured files/profile.', 'Native source/output/workspace/CPU/time and root/pressure/family limits unchanged.', 'Metadata reuses 32 families, preserves all 4417 prior prefix values and vector/contract payloads, and verifies complete exports and fresh process result.', 'Source/Float/full task/AE/authority frontiers remain open and false.'], 'scope': {'source_only': True, 'target_imports': 0, 'target_execution': 0, 'test_jobs': 0, 'native_jobs': 0, 'model_jobs': 0, 'codec_jobs': 0, 'Git_actions': 0, 'remote_actions': 0, 'protected_writes': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False}}
    destination = OUT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'producers': report['reviewed_producers'], 'receipt': pin(destination), 'rehashed_inputs': len(before)}))


if __name__ == '__main__':
    main()
