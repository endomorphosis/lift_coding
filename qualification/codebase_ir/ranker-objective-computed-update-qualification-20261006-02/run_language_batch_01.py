"""Unexecuted owned native-only runner for one exact typed-prefix query batch.

There is no AST, test, dependency setup, metadata, model, or replay callback.
The caller supplies reviewed driver/request/specification SHA256 pins. Only the
exact numbered mode is accepted; ranker module basename aliases are refused.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import types

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
OLD = WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-20261005-01'
HEAD = WORKSPACE / 'artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01'
CAP = WORKSPACE / 'artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-learned-intent-join-20261004-01/source-generation-08'
COMMON = (55852, '2bbf3529187151e76bc2f78113e91ab796e4c3c1826b1d453dd314bcd24c3916')
MODES = ('lean-original-computed-source-update-01',)
MODE = None
QUERIES = ()



def need(value, message):
    if value is not True:
        raise ValueError(message)


def validate_mode(mode):
    need(type(mode) is str and mode in MODES and mode == MODE, 'only one selected exact frozen language mode is permitted')


def files():
    path = ROOT / 'language_file_helpers_01.py'
    need(len(COMMON) == 2, 'reviewed q5 helper has not been frozen')
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical reviewed helper source required')
    with path.open('rb') as stream:
        raw = stream.read(COMMON[0] + 1)
    need(len(raw) == COMMON[0] and hashlib.sha256(raw).hexdigest() == COMMON[1], 'reviewed standard-library file helper differs')
    namespace = {'__file__': str(path), '__name__': 'held_container_core_file_helpers'}
    exec(compile(raw, str(path), 'exec'), namespace)
    namespace['exact']({'path': str(path), 'bytes': COMMON[0], 'sha256': COMMON[1]})
    selected = namespace['module'](MODE)
    global QUERIES
    QUERIES = tuple(selected['queries'])
    namespace['core_source_gate'] = lambda: namespace['source_gate'](MODE)
    return namespace


def sealed_helpers(f):
    # Only the previously sealed standard-library definitions are loaded here.
    seal_raw, seal_pin = f['read_pin'](OLD / 'file-only-seal-01.json', True)
    need(seal_pin['sha256'] == '8ea31286ffda2a5f08b4820bcc6ccf9ee05f133b96018132378f8c96ec16f438', 'previous helper seal differs')
    seal = f['parse'](seal_raw)
    path = OLD / 'run_trace_controls_02.py'
    expected = next(row for row in seal['files'] if row['path'] == str(path))
    raw = f['exact'](expected, True)
    namespace = {'__file__': str(path), '__name__': 'held_sealed_container_native_helpers'}
    exec(compile(raw, str(path), 'exec'), namespace)
    namespace['ROOTS'] = (OLD / 'source', HEAD / 'source', CAP / 'accelerate', CAP / 'datasets', CAP / 'kit')
    return namespace


def validate_request(f, request):
    need(request['schema'] == 'terminal-ranker-container-language-request@1'
         and request['exact_native_mode'] == MODE and request['exact_theorem_names'] == list(QUERIES)
         and request['proof_limits'] == f['NATIVE_LIMITS'] and request['root_request'] == f['ROOT_LEASE']
         and request['proof_pressure_limits'] == f['PRESSURE'] and request['outer_timeout_seconds'] == 120
         and request['native_retention_chunk_count_max'] == 61 and request['native_retention_aggregate_raw_bytes_max'] == 3997696,
         'exact mode/query/native/resource/retention request required')
    need(request['independent_core_source_review'] == f['SOURCE_GATE']
         and request['candidate_compiled'] is False and request['candidate_native_qualified'] is False
         and all(request[key] is False for key in f['AUTHORITY'])
         and request['full_task_satisfaction'] == 'unknown', 'unqualified request authority/source gate differs')
    need(len(request['strict_old_inputs']) == len({row['path'] for row in request['strict_old_inputs']}) == f['STRICT_GUARD_COUNT']
         and len(request['protected_live_sources']) == 4, 'exact guarded population required')
    f['core_source_gate']()
    f['validate_guard_union'](request)


def validate_specification(f, descriptor):
    spec = f['document'](descriptor)
    keys = {'schema','mode','selected_module','source','environment_manifest','expected_success','theorem_names',
            'freeze_producer','checker_wrapper','retention_helper','file_helpers','python_executable',
            'independent_core_source_review','qualified_imports','profile_parent','preparation_plan',
            'staged_import_inputs','source_capture_scope'}
    selected = f['module'](MODE)
    need(selected['qualification_root'] == str(ROOT), 'earlier accepted stages must be reused')
    need(set(spec) == keys and spec['schema'] == 'ranker-container-language-native-specification@1'
         and spec['mode'] == MODE and spec['selected_module'] == selected
         and spec['theorem_names'] == list(QUERIES) and spec['expected_success'] is True,
         'closed exact selected module specification required')
    dest = ROOT / 'preparation' / (MODE + '-producer')
    paths = {'source': Path(selected['source']['path']).name, 'environment_manifest':'environment-manifest.json',
             'freeze_producer':'prepare_language_batch_01.py','checker_wrapper':'bounded_analytic_checker.py',
             'retention_helper':'RetainLeanProof.py','file_helpers':'language_file_helpers_01.py'}
    for key, name in paths.items():
        need(spec[key]['path'] == str(dest/name), 'exact captured module input path required')
        f['exact'](spec[key])
    need((spec['source']['bytes'],spec['source']['sha256']) == (selected['source']['bytes'],selected['source']['sha256']),
         'held source must equal independently reviewed selected original')
    need(spec['checker_wrapper']['bytes'] == 29086 and spec['checker_wrapper']['sha256'] == '04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4'
         and spec['retention_helper']['bytes'] == 5828 and spec['retention_helper']['sha256'] == 'ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66'
         and (spec['file_helpers']['bytes'],spec['file_helpers']['sha256']) == COMMON,
         'immutable checker/retention/helper required')
    need(spec['independent_core_source_review'] == f['SOURCE_GATE'] and spec['profile_parent'] == f['BASE_PROFILE'],
         'whole candidate source gate and prior profile required')
    plan = f['document'](spec['preparation_plan'])
    need(set(plan) == {'schema','mode','imports','tooling_source_review'}
         and plan['schema'] == 'ranker-container-language-batch-plan@1' and plan['mode'] == MODE
         and plan['imports'] == spec['staged_import_inputs']
         and [row['mode'] for row in plan['imports']] == selected['prior_modes'],
         'exact previously closed dependency-prefix plan required')
    originals = [selected['source'],
        f['pin'](WORKSPACE/'qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-original-descent-01-producer/bounded_analytic_checker.py'),
        f['pin'](WORKSPACE/'qualification/codebase_ir/ranker-real-curvature-20261005-01/preparation/lean-original-descent-01-producer/RetainLeanProof.py'),
        f['pin'](ROOT/'prepare_language_batch_01.py'), f['pin'](ROOT/'language_file_helpers_01.py')]
    captures = [spec[key] for key in ('source','checker_wrapper','retention_helper','freeze_producer','file_helpers')]
    gate = f['document'](plan['tooling_source_review'])
    # Both entrypoint and held original producer are joined to the one source
    # audit; the captured-driver body equals the reviewed live entrypoint.
    live_driver = f['pin'](ROOT/'run_language_batch_01.py')
    need(gate['status'] == 'passed_source_only' and gate['findings'] == []
         and gate['reviewed_sources'] == [originals[4],originals[3],live_driver]
         and all(gate[k] is False for k in f['AUTHORITY']), 'exact three-source tooling gate required')
    profile,base = [f['document'](spec[key]) for key in ('environment_manifest','profile_parent')]
    extended,joined = f['import_extension'](base,plan['imports'])
    expected_files = {row['path']:row for row in extended['files']}
    for original,held in zip(originals,captures):
        need((original['bytes'],original['sha256']) == (held['bytes'],held['sha256']) and held['path'] not in expected_files,
             'exact unique held module copy required')
        expected_files[held['path']] = held
    wanted = dict(extended)
    wanted.update(selected_proof_sources=[spec['source']],profile_parent=spec['profile_parent'],
        per_check_sources=[{'original':o,'captured':c} for o,c in zip(originals,captures)],
        files=[expected_files[p] for p in sorted(expected_files)],external_file_count=len(expected_files),
        external_file_bytes=sum(row['bytes'] for row in expected_files.values()))
    need(profile == wanted and len(base['files']) == base['external_file_count'] == 20184,
         'whole unchanged prior environment plus exact qualified stages/five captures required')
    imports = [f['qualified_module'](name,extended) for name in
        f['BASE_IMPORT_NAMES']] + joined
    need(spec['qualified_imports'] == imports, 'all historical and staged whole-object/chunk import joins required')
    executable = f['pin'](Path(sys.executable).resolve(strict=True))
    need(spec['python_executable'] == executable and executable['bytes'] == 7845032
         and executable['sha256'] == '1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f',
         'exact immutable Python executable required')
    return spec


def checkout_guards(f, request):
    qualified_pin = request['prior_objective_scalar_qualified_review']
    need(qualified_pin == {'path': str(f['Q5'] / 'qualified-review-01.json'), 'bytes': 11167,
                          'sha256': '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'},
         'exact prior checkout guard source required')
    qualified = f['document'](qualified_pin)
    wanted = request['original_checkout_guards']
    need(set(wanted) == {'root', 'child'} and wanted == qualified['original_checkout_guards'],
         'exact original root/child checkout guard join required')
    found = {}
    for role, cwd, index_path in (
        ('root', WORKSPACE, WORKSPACE / '.git/index'),
        ('child', WORKSPACE / 'external/ipfs_accelerate', WORKSPACE / '.git/modules/external/ipfs_accelerate/index'),
    ):
        need(set(wanted[role]) == {'head', 'index'} and wanted[role]['index']['path'] == str(index_path),
             'fixed original checkout role/index path required')
        head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'],
                                       text=True, timeout=30).strip()
        index = f['pin'](index_path)
        need(head == wanted[role]['head'] and index == wanted[role]['index'], 'original checkout HEAD/index changed')
        found[role] = {'head': head, 'index': index}
    return found


def verify(h, f, request):
    f['validate_guard_union'](request)
    h['verify_old'](request)
    for row in f['document'](request['prior_trace_seal'])['files']:
        f['exact'](row)
    f['exact'](request['independent_core_source_review'])
    return checkout_guards(f, request)


def check_lean(run, receipt, request, h, f, invocation, lease):
    spec = validate_specification(f, invocation['specification'])
    module = types.ModuleType('held_container_core_native_checker')
    module.__file__ = spec['checker_wrapper']['path']
    sys.modules[module.__name__] = module
    exec(compile(f['exact'](spec['checker_wrapper'], True), module.__file__, 'exec'), module.__dict__)
    output = run / 'lean'
    output.mkdir()
    receipt['native_checker_attempts'] = [{'specification': invocation['specification'], 'native_invocations_observed': 0}]
    check = module.compile_analytic_lean(
        environment_manifest=Path(spec['environment_manifest']['path']),
        expected_environment_manifest_sha256=spec['environment_manifest']['sha256'], source_pin=spec['source'],
        output=output, root_lease=lease, expected_success=True, theorem_names=QUERIES,
        retention_helper_pin=spec['retention_helper'], python_executable_pin=spec['python_executable'])
    receipt['native_checker_attempts'][0]['native_invocations_observed'] = check['native_invocations']
    h['write'](run / 'check-result.json', check, compact=True, maximum=65536)
    receipt['native_proof_checks'] = [f['pin'](run / 'check-result.json')]
    need(check['status'] == 'passed' and check['matches_expectation'] is True
         and check['native_invocations'] == check['native_lean_invocations'] == 1
         and check['native_lean_returncode'] == 0 and check['axiom_report_error'] is None
         and check['post_call_binding_error'] is None and check['reconstruction_validation_error'] is None
         and check['reconstruction_validation']['status'] == 'passed'
         and check['compiled_artifacts'] and all(row['complete'] is True for row in check['compiled_artifacts']),
         'native result failed/inconclusive; retain the actual attempt')
    queries = check['theorem_axiom_output']
    need([row['theorem'] for row in queries] == list(QUERIES)
         and all(row['report_occurrences'] == 2 and set(row['axioms']) <= {'Classical.choice', 'Quot.sound', 'propext'} for row in queries),
         'exact typed-prefix standard-axiom native query reports required')
    validate_specification(f, invocation['specification'])


def owned(mode, specification, expected_invocation_sha256):
    validate_mode(mode)
    f = files()
    h = sealed_helpers(f)
    need(Path(specification) == ROOT / 'preparation' / (MODE + '-invocation.json'), 'exact owned invocation path required')
    raw, invocation_pin = f['read_pin'](specification, True)
    need(invocation_pin['sha256'] == expected_invocation_sha256, 'externally frozen invocation differs')
    invocation = f['parse'](raw)
    need(set(invocation) == {'schema', 'mode', 'inputs', 'request', 'specification', 'driver', 'extra_inputs',
                            'outer_timeout_seconds', 'started_utc', 'independent_core_source_review'}
         and invocation['schema'] == 'ranker-objective-prefix-kernel-frozen-invocation@1'
         and invocation['mode'] == mode and invocation['outer_timeout_seconds'] == 120
         and invocation['independent_core_source_review'] == f['SOURCE_GATE'], 'closed owned invocation required')
    need(invocation['driver'] == f['pin'](Path(__file__).resolve()) and invocation['driver']['path'] == str(ROOT / ('captured-driver-' + MODE + '.py')),
         'only the exact frozen driver may own this phase')
    for row in invocation['inputs']:
        f['exact'](row)
    request = f['document'](invocation['request'])
    validate_request(f, request)
    validate_specification(f, invocation['specification'])
    run = ROOT / 'evidence' / mode
    run.mkdir()
    started = time.monotonic()
    scheduler = lease = guard = None
    cleanup = []
    receipt = {'schema': 'ranker-objective-prefix-kernel-owned-native-control@1', 'mode': mode, 'status': 'started',
               'invocation': invocation_pin, 'independent_core_source_review': f['SOURCE_GATE'],
               'native_preparation_calls': 0, 'gradient_evaluations': 0, 'optimizer_updates': 0,
               'fit_calls': 0, 'autoencoder_fit_calls': 0, 'test_cases': 0, 'metadata_hydration_calls': 0,
               'source_function_executions': 0, 'dependency_setup_calls': 0, 'native_proof_checks': [],
               'primary_error': None, 'cleanup_errors': cleanup, 'full_task_satisfaction': 'unknown',
               'global_convergence_proved': False, 'global_autoencoder_convergence_proved': False,
               'python_ranker_source_equivalence_proved': False, 'all32_governing_RPI_exits': 'OPEN',
               'official_benchmark_score': None, **h['AUTHORITY'], **f['AUTHORITY']}
    try:
        receipt['original_checkout_guards_before'] = verify(h, f, request)
        base = f['parse'](f['exact']({'path': str(CAP / 'generation-manifest.json'), 'bytes': 25932539, 'sha256': h['BASE_SHA']}, True))
        expected = {row['captured_path']: {'path': row['captured_path'], 'bytes': row['bytes'], 'sha256': row['sha256']} for row in base['files']}
        extension = f['parse'](f['read_pin'](OLD / 'source-manifest.json', True)[0])
        for descriptor in [*extension['extension_manifests'], f['pin'](OLD / 'source-manifest.json')]:
            for row in f['document'](descriptor)['files']:
                expected[row['captured']['path']] = row['captured']
        for descriptor in invocation['extra_inputs']:
            path = Path(descriptor['path'])
            if path.suffix == '.py' and path.is_relative_to(ROOT):
                expected[descriptor['path']] = descriptor
        roots = h['ROOTS']
        sys.path[:] = [*[str(root) for root in roots]] + [value for value in sys.path if value and not Path(value).resolve().is_relative_to(WORKSPACE)]
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        sys.dont_write_bytecode = True
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        os.environ['IPFS_DATASETS_RESOURCE_SCHEDULER_PATH'] = str(run / 'resources.json')
        class CoreNativeGuard(h['Guard']):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.rsplit('.', 1)[-1] == 'terminal_codebase_intent_ranker_training':
                    self.blocked.append({'module': fullname, 'reason': 'ranker execution forbidden in native-only primitive phase'})
                    raise ImportError('native-only container qualification refuses ranker basename aliases')
                return super().find_spec(fullname, path, target)
        guard = CoreNativeGuard(expected)
        sys.meta_path.insert(0, guard)
        import benchmarks.agent_supervisor.container_coding as package
        package.__path__ = [str(root / 'benchmarks/agent_supervisor/container_coding') for root in roots[:2]] + list(package.__path__)
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane
        scheduler = get_global_resource_scheduler()
        config = scheduler.config
        need(config.proof_safety_enabled and
             (config.proof_memory_stall_percent, config.proof_cpu_stall_percent, config.proof_io_stall_percent, config.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0),
             'unchanged native proof admission pressure policy required')
        receipt['resource_policy'] = config.persisted_dict()
        h['write'](run / 'started.json', receipt)
        lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)
        receipt['root_lease'] = lease.to_dict()
        check_lean(run, receipt, request, h, f, invocation, lease)
        receipt['original_checkout_guards_after'] = verify(h, f, request)
        need(receipt['original_checkout_guards_after'] == receipt['original_checkout_guards_before'],
             'original checkout guard changed during owned native phase')
        for row in invocation['inputs']:
            f['exact'](row)
        f['verify_held']()
        receipt.update(strict_old_input_count=f['STRICT_GUARD_COUNT'], protected_live_source_count=4,
                       all_strict_old_and_protected_live_inputs_unchanged=True, status='passed')
    except BaseException as error:
        receipt['status'] = 'failed'
        receipt['primary_error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        if lease is not None:
            try:
                receipt['root_release_returned'] = lease.release()
            except BaseException as error:
                cleanup.append({'stage': 'release', 'error': str(error)})
        if scheduler is not None:
            try:
                state = scheduler.snapshot()
                receipt['final_resource_state'] = state
                need(state['active_lease_count'] == state['waiting_request_count'] == 0, 'owned lease/waiters did not drain')
            except BaseException as error:
                cleanup.append({'stage': 'drain', 'error': str(error)})
        if guard is not None:
            receipt['selected_owned_imports'] = []
            for name, before in guard.records.items():
                try:
                    after = f['pin'](before['path'])
                    receipt['selected_owned_imports'].append({'module': name, 'before': before, 'after': after, 'matches': before == after})
                    if before != after:
                        cleanup.append({'stage': 'source_readback', 'module': name})
                except BaseException as error:
                    cleanup.append({'stage': 'source_readback', 'module': name, 'error': str(error)})
            receipt['blocked_imports'] = guard.blocked
        try:
            receipt['original_checkout_guards_after'] = verify(h, f, request)
            for row in invocation['inputs']:
                f['exact'](row)
            f['verify_held']()
            receipt['strict_old_input_count'] = f['STRICT_GUARD_COUNT']
            receipt['protected_live_source_count'] = 4
            receipt['all_strict_old_and_protected_live_inputs_unchanged'] = True
            if 'original_checkout_guards_before' in receipt:
                need(receipt['original_checkout_guards_after'] == receipt['original_checkout_guards_before'],
                     'original checkout guard changed before owned closure')
        except BaseException as error:
            cleanup.append({'stage': 'original_checkout_guard_readback', 'error': str(error)})
        if cleanup:
            receipt['status'] = 'failed'
        receipt['elapsed_seconds_owned'] = time.monotonic() - started
        h['write'](run / 'closed.json', receipt)
    print(json.dumps({'status': receipt['status'], 'owned_seconds': receipt['elapsed_seconds_owned'], 'primary_error': receipt['primary_error']}))
    return 0 if receipt['status'] == 'passed' else 1


def outer(args):
    validate_mode(args.mode)
    f = files()
    own = f['pin'](Path(__file__).resolve())
    need(own['path'] == str(ROOT / 'run_language_batch_01.py') and own['sha256'] == args.expected_driver_sha256,
         'exact reviewed original native-only driver required')
    request_path = ROOT / 'preparation' / (MODE + '-request.json')
    specification_path = ROOT / 'preparation' / (MODE + '-check-specification.json')
    request_pin, spec_pin = [f['pin'](path) for path in (request_path, specification_path)]
    need(request_pin['sha256'] == args.expected_request_sha256 and spec_pin['sha256'] == args.expected_specification_sha256,
         'externally reviewed prepared request/specification pins required')
    request = f['document'](request_pin)
    validate_request(f, request)
    spec = validate_specification(f, spec_pin)
    h = sealed_helpers(f)
    checkout_before = verify(h, f, request)
    f['verify_held']()
    snapshot = ROOT / ('captured-driver-' + MODE + '.py')
    with snapshot.open('xb') as stream:
        stream.write(f['exact'](own, True))
        stream.flush()
        os.fsync(stream.fileno())
    snapshot.chmod(0o444)
    driver = f['pin'](snapshot)
    extra = [spec_pin, own, f['SOURCE_GATE'], *[spec[key] for key in (
        'source', 'environment_manifest', 'freeze_producer', 'checker_wrapper', 'retention_helper', 'file_helpers', 'python_executable')]]
    inputs = [driver, request_pin, *extra]
    need(len({row['path'] for row in inputs}) == len(inputs), 'unique closed native invocation inputs required')
    invocation = {'schema': 'ranker-objective-prefix-kernel-frozen-invocation@1', 'mode': MODE,
                  'inputs': inputs, 'request': request_pin, 'specification': spec_pin, 'driver': driver, 'extra_inputs': extra,
                  'outer_timeout_seconds': 120, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'independent_core_source_review': f['SOURCE_GATE']}
    target = ROOT / 'preparation' / (MODE + '-invocation.json')
    invocation_pin = f['write'](target, invocation)
    need(verify(h, f, request) == checkout_before, 'original checkout changed during outer invocation freeze')
    record = {'schema': 'ranker-objective-prefix-kernel-outer-native-control@1', 'invocation': invocation_pin,
              'returncode': None, 'primary_error': None, 'cleanup_errors': [], 'native_model_test_metadata_or_codec_callbacks': 'native_only'}
    record['original_checkout_guards_before'] = checkout_before
    started = time.monotonic()
    child = None
    try:
        with (ROOT / 'evidence' / (MODE + '.stdout.log')).open('xb') as stream:
            child = subprocess.Popen([sys.executable, '-B', str(snapshot), 'owned', MODE, str(target), invocation_pin['sha256']],
                                     stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
            record['child_pid'] = child.pid
            record['returncode'] = child.wait(timeout=120)
    except BaseException as error:
        record['primary_error'] = {'type': type(error).__name__, 'message': str(error)}
        if child is not None and child.poll() is None:
            import signal
            try:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
            except BaseException as cleanup_error:
                record['cleanup_errors'].append(str(cleanup_error))
    finally:
        record['elapsed_seconds_outer'] = time.monotonic() - started
        try:
            record['original_checkout_guards_after'] = checkout_guards(f, request)
            need(record['original_checkout_guards_after'] == checkout_before, 'original checkout changed during outer native phase')
        except BaseException as error:
            record['cleanup_errors'].append({'stage': 'original_checkout_guard_readback', 'error': str(error)})
        f['write'](ROOT / 'evidence' / (MODE + '-closed.json'), record)
    print(json.dumps(record))
    return record['returncode'] or (1 if record['primary_error'] or record['cleanup_errors'] else 0)


def main():
    if not __debug__:
        raise RuntimeError('optimized Python would disable qualification gates')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('mode', choices=MODES)
    for name in ('driver', 'request', 'specification'):
        run.add_argument('--expected-' + name + '-sha256', required=True)
    owned_parser = commands.add_parser('owned')
    owned_parser.add_argument('mode', choices=MODES)
    owned_parser.add_argument('invocation', type=Path)
    owned_parser.add_argument('expected_invocation_sha256')
    args = parser.parse_args()
    global MODE
    MODE = args.mode
    pins = [getattr(args, 'expected_' + name + '_sha256') for name in ('driver', 'request', 'specification')] if args.action == 'run' else [args.expected_invocation_sha256]
    need(all(re.fullmatch('[0-9a-f]{64}', value) is not None for value in pins), 'external lower-case SHA256 arguments required')
    if args.action == 'run':
        return outer(args)
    return owned(args.mode, args.invocation, args.expected_invocation_sha256)


if __name__ == '__main__':
    raise SystemExit(main())
