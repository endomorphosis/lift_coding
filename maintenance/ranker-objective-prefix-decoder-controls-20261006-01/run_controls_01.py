"""Run twenty reviewed host compiler controls in a bounded separate process.

This is ordinary pytest validation, without a supervisor lease or native proof.
No source under test is executed in the parent. Held source copies and pinned
fixture buffers are used; every historical guard is read before and after.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

W = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
HELPER = W / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02/container_core_file_helpers_01.py'
AUTHORITY = {key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--expected-source-sha256', required=True)
    args = parser.parse_args()
    need(__debug__ and all(re.fullmatch('[0-9a-f]{64}', s) is not None
         for s in (args.plan_sha256, args.expected_source_sha256)), 'exact external source/plan pins required')
    raw = HELPER.read_bytes()
    need(len(raw) == 17601 and hashlib.sha256(raw).hexdigest() ==
         '815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a', 'reviewed stdlib file helper differs')
    h = {'__file__': str(HELPER), '__name__': 'held_prefix_control_file_readers'}
    exec(compile(raw, str(HELPER), 'exec'), h)
    pin, exact, document = h['pin'], h['exact'], h['document']
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_source_sha256, 'runner source differs')
    plan_pin = pin(args.plan)
    need(plan_pin['sha256'] == args.plan_sha256, 'control plan differs')
    plan = document(plan_pin)
    need(set(plan) == {'schema', 'runner_source_review', 'candidate_source_review', 'candidate_pins',
         'original_source', 'bindings', 'draft', 'materialization_receipt', 'qualified_host_compiler', 'native_guard_request', 'proof_seal', 'proof_review'}
         and plan['schema'] == 'ranker-objective-prefix-decoder-control-plan@1', 'closed control plan required')
    source_gate = document(plan['runner_source_review'])
    need(source_gate['status'] == 'passed_source_only' and source_gate['findings'] == []
         and source_gate['reviewed_source'] == own, 'exact runner source review required')
    gate = document(plan['candidate_source_review'])
    need(plan['candidate_source_review']['path'] == str(W / 'maintenance/ranker-objective-prefix-decoder-source-review-20261006-01/review-receipt.json'),
         'fixed independent decoder source review required')
    need(gate['status'] == 'passed_source_only' and gate['findings'] == []
         and sorted(gate['candidate_pins'], key=lambda r: r['path']) ==
             sorted(plan['candidate_pins'], key=lambda r: r['path']), 'exact passed candidate source gate required')
    need(all(source_gate[k] is gate[k] is False for k in AUTHORITY), 'source gates grant authority')
    candidates = plan['candidate_pins']
    need(len(candidates) == 4 and len({r['path'] for r in candidates}) == 4, 'exact four candidate source/doc pins required')
    by_name = {Path(r['path']).name: r for r in candidates}
    need(set(by_name) == {'objective_prefix_decoder.py', 'test_objective_prefix_decoder.py',
         'candidate-interface.json', 'source-model-obligations-01.json'}, 'exact candidate roles required')
    compiler = Path(by_name['objective_prefix_decoder.py']['path'])
    tests = Path(by_name['test_objective_prefix_decoder.py']['path'])
    candidate_root = W / 'qualification/codebase_ir/ranker-objective-prefix-decoder-candidate-20261006-01'
    for name, relative in {'objective_prefix_decoder.py': 'source-v1/objective_prefix_decoder.py',
                          'test_objective_prefix_decoder.py': 'source-v1/test_objective_prefix_decoder.py',
                          'candidate-interface.json': 'candidate-interface.json',
                          'source-model-obligations-01.json': 'source-model-obligations-01.json'}.items():
        need(by_name[name]['path'] == str(candidate_root / relative), 'exact candidate role path required')
    for row in candidates:
        exact(row)
    need((plan['original_source']['bytes'], plan['original_source']['sha256']) ==
         (16391, '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a')
         and (plan['bindings']['bytes'], plan['bindings']['sha256']) ==
         (25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'), 'exact original buffers required')
    needed_buffers = {
        'draft': (13910, '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'),
        'materialization_receipt': (2426, 'e846d7ab984a14e1d279965364360e9e8f72ab1ab0408ddff66cfefe09440430'),
        'qualified_host_compiler': (48095, 'd4aec9ef8f239314c48ca2d2e0a70495be6d2df4c79329e338d9a96c26ee196c'),
    }
    for role, pair in needed_buffers.items():
        need((plan[role]['bytes'], plan[role]['sha256']) == pair, 'exact pinned decoder buffer required: ' + role)
    request = document(plan['native_guard_request'])
    need(request['exact_native_mode'] == 'lean-objective-container-core-02'
         and len(request['strict_old_inputs']) == 2421 and len(request['protected_live_sources']) == 4,
         'unchanged historical guard context required')
    h['validate_guard_union'](request)
    proof = document(plan['proof_review']); seal = document(plan['proof_seal'])
    need(proof['status'] == 'passed' and proof['qualified_theorem_queries'] == 4
         and proof['qualified_native_checks'] == 1 and proof['request'] == plan['native_guard_request']
         and proof['original_checkout_guards'] == request['original_checkout_guards']
         and proof['guards_same'] is True and proof['leases_drained'] is True
         and seal['review'] == plan['proof_review'] and seal['review'] in seal['files']
         and seal['schema'] == 'ranker-objective-container-core-qualified-file-only-seal@1'
         and seal['regular_file_count'] == len(seal['files']) == 34
         and len({r['path'] for r in seal['files']}) == 34
         and seal['regular_file_bytes'] == sum(r['bytes'] for r in seal['files'])
         and seal['seal_self_excluded_from_files'] is True
         and all(request[k] is proof[k] is seal[k] is False for k in AUTHORITY)
         and seal['fixture_symlinks'] == seal['excluded_dependency_roots'] == [], 'complete qualified proof seal required')
    inventory_wire = json.dumps(seal['files'], sort_keys=True, separators=(',', ':'),
                                ensure_ascii=True, allow_nan=False).encode()
    need(hashlib.sha256(inventory_wire).hexdigest() == seal['file_inventory_sha256'], 'proof seal inventory differs')
    q = W / 'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'
    need(plan['proof_seal']['path'] == str(q / 'file-only-seal-01.json') and seal['scope_root'] == str(q)
         and all(Path(r['path']).is_relative_to(q) for r in seal['files']), 'fixed proof scope required')
    def proof_census():
        physical = list(q.rglob('*'))
        need(q.resolve(strict=True) == q and not any(p.is_symlink() for p in physical)
             and all(p.is_file() or p.is_dir() for p in physical)
             and {str(p) for p in physical if p.is_file()} ==
                 {r['path'] for r in seal['files']} | {plan['proof_seal']['path']},
             'complete quiet proof census differs')
    proof_census()
    for row in [*request['strict_old_inputs'], *request['protected_live_sources'], *seal['files'],
                plan['original_source'], plan['bindings'], plan['draft'], plan['materialization_receipt'], plan['qualified_host_compiler']]:
        exact(row)

    def checkout_guards():
        found = {}
        for role, cwd in (('root', W), ('child', W / 'external/ipfs_accelerate')):
            expected = request['original_checkout_guards'][role]
            head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd),
                'rev-parse', 'HEAD'], timeout=10, text=True).strip()
            need(head == expected['head'] and pin(expected['index']['path']) == expected['index'], 'original checkout changed')
            found[role] = expected
        return found

    before = checkout_guards()
    run = ROOT / 'run-01'
    run.mkdir()
    held = run / 'held-source'; held.mkdir()
    copies = []
    for original in (by_name['objective_prefix_decoder.py'], by_name['test_objective_prefix_decoder.py']):
        out = held / Path(original['path']).name
        with out.open('xb') as stream:
            stream.write(exact(original, True)); stream.flush(); os.fsync(stream.fileno())
        out.chmod(0o444)
        actual = pin(out)
        need((actual['bytes'], actual['sha256']) == (original['bytes'], original['sha256']), 'held source body differs')
        copies.append({'original': original, 'captured': actual})
    xml = run / 'junit.xml'
    env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'PYTHONPATH': str(held), 'RANKER_AST_SOURCE': plan['original_source']['path'],
           'RANKER_PREFIX_BINDINGS': plan['bindings']['path'],
           'RANKER_PREFIX_DRAFT': plan['draft']['path'], 'RANKER_PREFIX_RECEIPT': plan['materialization_receipt']['path'],
           'RANKER_PREFIX_COMPILER': plan['qualified_host_compiler']['path']}
    argv = [sys.executable, '-B', '-m', 'pytest', str(held / tests.name), '-q', '--tb=short',
            '--noconftest', '-p', 'no:cacheprovider', '--rootdir', str(run), '-o', 'addopts=', '--junitxml', str(xml)]
    process = selector = None
    output = bytearray(); cleanup = []; started = time.monotonic(); error = None; returncode = None
    try:
        process = subprocess.Popen(argv, cwd=run, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=child_limits)
        selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            need(time.monotonic() - started <= 45, 'pytest wall timeout')
            for key, _ in selector.select(timeout=0.2):
                block = os.read(key.fileobj.fileno(), 8192)
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    need(len(output) + len(block) <= 65536, 'pytest stdout cap')
                    output.extend(block)
        returncode = process.wait(timeout=max(0.1, 45 - (time.monotonic() - started)))
        need(returncode == 0, 'pytest failed')
        need(xml.stat().st_size <= 1024**2, 'JUnit file cap')
        report = ET.fromstring(exact(pin(xml), True))
        cases = report.findall('.//testcase'); suites = report.findall('.//testsuite')
        need(len(cases) == 20 and len(suites) == 1 and suites[0].get('tests') == '20'
             and all(suites[0].get(k) == '0' for k in ('errors', 'failures', 'skipped'))
             and all(not list(c) for c in cases)
             and len({c.get('name') for c in cases}) == 20
             and {c.get('name', '')[5:7] for c in cases} == {f'{i:02d}' for i in range(1, 21)},
             'exact twenty successful control groups required')
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            try:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                returncode = process.wait(timeout=5)
                process.stdout.close()
            except BaseException as exc:
                cleanup.append({'stage': 'process_group_cleanup', 'message': str(exc)})
        try:
            need(checkout_guards() == before, 'original checkout differs after tests')
            h['verify_held']()
            proof_census()
        except BaseException as exc:
            cleanup.append({'stage': 'input_guard_readback', 'message': str(exc)})
    with (run / 'pytest-stdout.log').open('xb') as stream:
        stream.write(output); stream.flush(); os.fsync(stream.fileno())
    receipt = {'schema': 'ranker-objective-prefix-decoder-bounded-host-controls@1',
        'status': 'passed' if error is None and cleanup == [] else 'failed', 'producer': own, 'plan': plan_pin,
        'candidate_source_review': plan['candidate_source_review'], 'runner_source_review': plan['runner_source_review'],
        'captured_test_sources': copies, 'ordinary_pytest_job': True, 'supervisor_lease_claimed': False,
        'qualified_native_queries': 0, 'native_jobs': 0, 'model_fit_calls': 0, 'metadata_hydration_calls': 0,
        'original_ranker_import_or_execution_calls': 0, 'test_groups_passed': 20 if error is None and cleanup == [] else 0,
        'strict_guards_verified_before_after': 2421, 'protected_live_sources': 4,
        'all_historical_and_candidate_inputs_unchanged': cleanup == [], 'original_checkout_guards': before,
        'pytest_returncode': returncode, 'primary_error': error, 'cleanup_errors': cleanup,
        'stdout': pin(run / 'pytest-stdout.log'), 'junit': pin(xml) if xml.is_file() else None,
        'limits': {'wall_seconds': 45, 'cpu_seconds': 20, 'memory_bytes': 1024**3,
                   'per_file_bytes': 1024**2, 'stdout_bytes': 65536, 'cleanup_seconds': 5},
        'elapsed_seconds': time.monotonic() - started, 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'kernel_semantic_equivalence_proved': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', **AUTHORITY}
    out = h['write'](run / 'closed.json', receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': out, 'test_groups_passed': receipt['test_groups_passed'],
                      'pytest_returncode': returncode, 'primary_error': error, 'cleanup_errors': cleanup}))
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
