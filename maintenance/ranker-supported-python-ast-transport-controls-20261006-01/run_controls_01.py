"""Run reviewed Python-AST syntax controls in a bounded ordinary subprocess.

Root alone executes this runner. Historical integrity is replayed from the
externally reviewed standalone checkpoint source before and after the tests.
No historical private helper, original ranker, native prover, model or metadata
job executes. This is ordinary pytest evidence, not supervisor/proof admission.
"""
import argparse
import ast
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

W = Path('/home/barberb/lift_coding')
ROOT = W / 'maintenance/ranker-supported-python-ast-transport-controls-20261006-01'
CANDIDATE = W / 'qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01'
REPLAY_ROOT = W / 'qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-01'
AUTHORITY = {key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
PLAN_KEYS = {'schema', 'runner_source_review', 'candidate_source_review', 'candidate_pins',
             'original_source', 'bindings', 'draft', 'lean_grammar',
             'replay_source', 'replay_manifest', 'replay_source_review'}
FIXTURES = {
    'original_source': ('artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py',
                        16391, '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'),
    'bindings': ('qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01/source-bindings.json',
                 25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'),
    'draft': ('qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01/objective-prefix-draft.json',
              13910, '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'),
    'lean_grammar': ('qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-01/math/PyAstNumericSubset.lean',
                     3916, '11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def signature(info):
    return tuple(getattr(info, key) for key in STAT_FIELDS)


def read_body(path, expected=None, capture=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical nonsymlink input path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and (not capture or before.st_size <= 32 * 1024**2),
             'regular bounded body required')
        digest, total, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'body grew while reading')
            digest.update(block)
            if capture:
                blocks.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and total == before.st_size,
             'input body/stat changed while reading')
    finally:
        os.close(fd)
    found = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    if expected is not None:
        need(type(expected) is dict and set(expected) == {'path', 'bytes', 'sha256'} and found == expected,
             'exact input descriptor/body differs')
    return found, b''.join(blocks)


def exact(row, capture=False):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
         and type(row['path']) is str and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
         'exact canonical descriptor required')
    return read_body(row['path'], row, capture)[1]


def pin(path):
    return read_body(path)[0]


def document(row):
    return parse(exact(row, True))


def write(path, raw):
    need(type(raw) is bytes, 'output bytes required')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def gate_document(row):
    gate = document(row)
    need(gate['status'] == 'passed_source_only' and gate['findings'] == []
         and all(gate[key] is False for key in AUTHORITY), 'independent source-only gate required')
    return gate


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def group_members(group):
    members = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            value = (entry / 'stat').read_text()
        except FileNotFoundError:
            continue
        tail = value[value.rfind(')') + 2:].split()
        need(len(tail) > 3, 'proc group observation malformed')
        if int(tail[2]) == group:
            members.append(int(entry.name))
    return sorted(members)


def close_group(process):
    """Kill/reap the complete subprocess group under the unchanged five seconds."""
    started = time.monotonic()
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=max(0.01, 5 - (time.monotonic() - started)))
    reaped = []
    while True:
        try:
            while True:
                pid, status = os.waitpid(-process.pid, os.WNOHANG)
                if pid == 0:
                    break
                reaped.append({'pid': pid, 'wait_status': status})
        except ChildProcessError:
            pass
        members = group_members(process.pid)
        if not members:
            break
        need(time.monotonic() - started < 5, 'subprocess group did not drain within cleanup bound')
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.02)
    if process.stdout is not None:
        process.stdout.close()
    return {'process_group': process.pid, 'reaped_adopted_children': reaped,
            'remaining_members': [], 'elapsed_seconds': time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--expected-source-sha256', required=True)
    args = parser.parse_args()
    need(__debug__ and all(re.fullmatch('[0-9a-f]{64}', value) is not None for value in
                          (args.plan_sha256, args.expected_source_sha256)), 'external exact plan/source pins required')
    own = pin(Path(__file__).resolve())
    need(own['path'] == str(ROOT / 'run_controls_01.py') and own['sha256'] == args.expected_source_sha256,
         'exact fixed runner source differs')
    plan_pin = pin(args.plan)
    need(plan_pin['sha256'] == args.plan_sha256, 'externally pinned plan differs')
    plan = document(plan_pin)
    need(type(plan) is dict and set(plan) == PLAN_KEYS
         and plan['schema'] == 'ranker-supported-python-ast-transport-control-plan@1', 'closed exact control plan required')
    runner_gate = gate_document(plan['runner_source_review'])
    need(runner_gate['reviewed_source'] == own, 'independent exact runner source review required')
    candidate_gate = gate_document(plan['candidate_source_review'])
    candidates = plan['candidate_pins']
    need(type(candidates) is list and len(candidates) == 3 and len({row['path'] for row in candidates}) == 3,
         'exact three candidate source/test/interface roles required')
    by_name = {Path(row['path']).name: row for row in candidates}
    need(set(by_name) == {'python_ast_transport.py', 'test_python_ast_transport.py', 'candidate-interface.json'}
         and all(row['path'] == str(CANDIDATE / name) for name, row in by_name.items()), 'fixed candidate role paths required')
    need(sorted(candidate_gate['candidate_pins'].values(), key=lambda row: row['path']) ==
         sorted(candidates, key=lambda row: row['path']), 'exact three-body candidate source gate required')
    need(plan['candidate_source_review']['path'] == str(W / 'maintenance/ranker-supported-python-ast-transport-source-review-20261006-01/review-receipt-01.json'),
         'fixed independent transport source gate required')
    for row in candidates:
        exact(row)
    interface = document(by_name['candidate-interface.json'])
    need(interface['schema'] == 'ranker-supported-python-ast-source-transport-candidate-interface@1'
         and interface['implementation'] == by_name['python_ast_transport.py']
         and interface['controls'] == by_name['test_python_ast_transport.py']
         and interface['control_status'] == 'NOT_EXECUTED; root alone may run reviewed bounded controls'
         and interface['new_qualified_queries'] == 0, 'reviewed unexecuted host controls/interface join required')
    groups = interface['control_groups']
    need(type(groups) is list and len(groups) == 20 and len(set(groups)) == 20
         and all(type(name) is str and re.fullmatch(r'test_[0-9]{2}_[a-z_]+', name) for name in groups)
         and [name[5:7] for name in groups] == [f'{i:02d}' for i in range(1, 21)], 'exact twenty ordered control names required')
    test_tree = ast.parse(exact(by_name['test_python_ast_transport.py'], True))
    found = [node.name for node in test_tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')]
    need(found == groups, 'source declarations must match exact interface test names')
    for role, (relative, count, digest) in FIXTURES.items():
        need(plan[role] == {'path': str(W / relative), 'bytes': count, 'sha256': digest}, 'fixed fixture differs: ' + role)
        exact(plan[role])
    need(interface['grammar_api_source_only'] == plan['lean_grammar'], 'transport grammar API fixture differs')
    need(plan['replay_source']['path'] == str(REPLAY_ROOT / 'checkpoint_replay.py')
         and plan['replay_manifest']['path'] == str(REPLAY_ROOT / 'history-checkpoint-02.json')
         and plan['replay_source_review']['path'] == str(W / 'maintenance/ranker-supported-python-ast-checkpoint-replay-source-review-20261006-01/review-receipt-01.json'),
         'fixed standalone history checkpoint/review paths required')
    replay_gate = gate_document(plan['replay_source_review'])
    need(replay_gate['candidate_pins']['replay_source'] == plan['replay_source']
         and replay_gate['candidate_pins']['manifest'] == plan['replay_manifest']
         and replay_gate['reviewed_sources'] == [plan['replay_source'], plan['replay_manifest']],
         'externally reviewed exact ordered replay source/manifest required')
    manifest = document(plan['replay_manifest'])
    need(manifest['schema'] == 'ranker-qualified-history-checkpoint@1'
         and manifest['accepted_guard_count'] == 3676 and manifest['closure_count'] == 3920
         and manifest['scope_count'] == 48 and manifest['physical_scope_count'] == 47
         and all(manifest[key] is False for key in AUTHORITY), 'exact unprivileged accepted-history checkpoint required')
    direct = [own, plan_pin, plan['runner_source_review'], plan['candidate_source_review'], *candidates,
              *(plan[role] for role in FIXTURES), plan['replay_source'], plan['replay_manifest'], plan['replay_source_review']]
    for row in direct:
        exact(row)

    run = ROOT / 'run-01'
    run.mkdir()
    held = run / 'held-source'
    held.mkdir()
    copies = []
    held_roles = {}
    originals = {'implementation': by_name['python_ast_transport.py'], 'tests': by_name['test_python_ast_transport.py'],
                 'replay': plan['replay_source'], **{role: plan[role] for role in FIXTURES}}
    need(len({Path(row['path']).name for row in originals.values()}) == len(originals), 'held basenames must be unique')
    for role, original in originals.items():
        out = held / Path(original['path']).name
        write(out, exact(original, True))
        out.chmod(0o444)
        actual = pin(out)
        need((actual['bytes'], actual['sha256']) == (original['bytes'], original['sha256']), 'held immutable body differs')
        copies.append({'role': role, 'original': original, 'captured': actual})
        held_roles[role] = out
    replay_source = exact(next(row['captured'] for row in copies if row['role'] == 'replay'), True)
    replay_namespace = {'__file__': str(held_roles['replay']), '__name__': 'held_reviewed_history_checkpoint_replay'}
    exec(compile(replay_source, str(held_roles['replay']), 'exec'), replay_namespace)
    need(callable(replay_namespace.get('replay')), 'reviewed standalone replay API required')
    before = replay_namespace['replay'](plan['replay_manifest'])
    need(before['status'] == 'passed_file_only' and before['manifest'] == plan['replay_manifest']
         and before['closure_count'] == 3920 and before['physical_scope_count'] == 47
         and before['historical_helpers_executed'] == 0 and before['digest_cache_used'] is False,
         'fresh complete historical replay before tests required')
    # Subreaping is process-local and allows strict orphan group reaping, unlike
    # checking only that the direct pytest child exited. No supervisor lease.
    libc = ctypes.CDLL(None, use_errno=True)
    need(libc.prctl(36, 1, 0, 0, 0) == 0, 'Linux child subreaper setup failed')
    xml = run / 'junit.xml'
    env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'RANKER_PY_AST_TRANSPORT': str(held_roles['implementation']),
           'RANKER_AST_SOURCE': str(held_roles['original_source']),
           'RANKER_PREFIX_BINDINGS': str(held_roles['bindings']),
           'RANKER_PREFIX_DRAFT': str(held_roles['draft']),
           'RANKER_PY_AST_API': str(held_roles['lean_grammar'])}
    argv = [sys.executable, '-I', '-B', '-m', 'pytest', '-c', os.devnull, str(held_roles['tests']), '-q', '--tb=short',
            '--noconftest', '-p', 'no:cacheprovider', '--rootdir', str(run), '-o', 'addopts=', '--junitxml', str(xml)]
    process = selector = None
    output, cleanup = bytearray(), []
    error, returncode, group_closure, after, successful_names = None, None, None, None, []
    started = time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=run, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=child_limits)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            need(time.monotonic() - started <= 45, 'pytest wall timeout')
            for key, _ in selector.select(timeout=0.2):
                block = os.read(key.fileobj.fileno(), 8192)
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    need(len(output) + len(block) <= 65536, 'pytest stdout cap')
                    output.extend(block)
        returncode = process.wait(timeout=max(0.01, 45 - (time.monotonic() - started)))
        need(time.monotonic() - started <= 45 and returncode == 0, 'bounded pytest did not pass')
        xml_pin = pin(xml)
        need(xml_pin['bytes'] <= 1024**2, 'JUnit file cap')
        report = ET.fromstring(exact(xml_pin, True))
        cases, suites = report.findall('.//testcase'), report.findall('.//testsuite')
        need(len(cases) == 20 and len(suites) == 1 and suites[0].get('tests') == '20'
             and all(suites[0].get(key) == '0' for key in ('errors', 'failures', 'skipped'))
             and all(not list(case) for case in cases)
             and [case.get('name') for case in cases] == groups, 'exact twenty named successful control groups required')
        successful_names = [case.get('name') for case in cases]
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            try:
                group_closure = close_group(process)
                returncode = process.returncode
            except BaseException as exc:
                cleanup.append({'stage': 'strict_process_group_cleanup', 'message': str(exc)})
        try:
            for row in direct:
                exact(row)
            for row in copies:
                exact(row['captured'])
                need(stat.S_IMODE(Path(row['captured']['path']).stat().st_mode) == 0o444, 'held readonly mode changed')
            after = replay_namespace['replay'](plan['replay_manifest'])
            comparable = set(before) - {'elapsed_seconds'}
            need(set(after) == set(before) and all(after[key] == before[key] for key in comparable),
                 'fresh complete historical replay after tests differs')
        except BaseException as exc:
            cleanup.append({'stage': 'fresh_input_history_readback', 'message': str(exc)})
    stdout_pin = write(run / 'pytest-stdout.log', bytes(output))
    passed = error is None and cleanup == [] and successful_names == groups and group_closure is not None and after is not None
    receipt = {'schema': 'ranker-supported-python-ast-transport-bounded-host-controls@1',
        'status': 'passed' if passed else 'failed', 'producer': own, 'plan': plan_pin,
        'runner_source_review': plan['runner_source_review'], 'candidate_source_review': plan['candidate_source_review'],
        'replay_source_review': plan['replay_source_review'], 'replay_source': plan['replay_source'],
        'replay_manifest': plan['replay_manifest'], 'history_before': before, 'history_after': after,
        'captured_sources_and_fixtures': copies, 'ordinary_pytest_job': True, 'supervisor_lease_claimed': False,
        'qualified_native_queries': 0, 'native_jobs': 0, 'model_fit_calls': 0, 'metadata_hydration_calls': 0,
        'original_ranker_import_or_execution_calls': 0, 'historical_private_helpers_executed': 0,
        'test_groups_passed': 20 if passed else 0, 'expected_control_names': groups,
        'successful_control_names': successful_names if passed else [],
        'history_closure_count_verified_before_after': 3920, 'protected_live_sources': 4,
        'complete_physical_scopes_verified_before_after': 47,
        'all_historical_and_candidate_inputs_unchanged': after is not None and cleanup == [],
        'original_checkout_guards': before['original_checkout_guards'], 'pytest_returncode': returncode,
        'process_group_closure': group_closure, 'primary_error': error, 'cleanup_errors': cleanup,
        'stdout': stdout_pin, 'junit': pin(xml) if xml.is_file() and not xml.is_symlink() else None,
        'limits': {'wall_seconds': 45, 'cpu_seconds': 20, 'memory_bytes': 1024**3,
                   'per_file_bytes': 1024**2, 'stdout_bytes': 65536, 'cleanup_seconds': 5},
        'pytest_and_readback_elapsed_seconds': time.monotonic() - started,
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_parser_correctness_proved': False, 'normalization_preservation_proved': False,
        'kernel_semantic_equivalence_proved': False, 'strict_cache_admission': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN', **AUTHORITY}
    closed = write(run / 'closed.json', wire(receipt) + b'\n')
    print(json.dumps({'status': receipt['status'], 'receipt': closed,
                      'test_groups_passed': receipt['test_groups_passed'], 'pytest_returncode': returncode,
                      'primary_error': error, 'cleanup_errors': cleanup}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
