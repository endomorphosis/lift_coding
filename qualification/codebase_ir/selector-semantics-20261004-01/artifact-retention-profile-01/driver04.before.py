"""Captured-source, admitted requirement controls and conditional Lean evidence."""
import datetime
import hashlib
import importlib.abc
import importlib.machinery
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
ARTIFACTS = WORKSPACE / 'artifacts/codebase_ir_terminal_bench'
GROUND = ARTIFACTS / 'terminal-codebase-ir-requirement-grounding-20261004-01'
PRIOR = ARTIFACTS / 'terminal-codebase-ir-expanded-transfer-20261004-01'
HEAD = ARTIFACTS / 'terminal-codebase-ir-intent-corpus-head-20261004-01'
CONSUMER = ARTIFACTS / 'terminal-codebase-ir-analysis-consumer-20261004-01'
CAP = ARTIFACTS / 'terminal-codebase-ir-learned-intent-join-20261004-01/source-generation-08'
BASE_SHA = '5efc3725539ced8b5a0f6e172c3b4c7e92fccc158940feaa71b4890a054203a3'
BASE_CID = 'sha256:30d08864e562515c29af9c138f944a70626361137a8ae3721f532a6b6014a5fa'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path); before = path.lstat()
    assert path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    raw = path.read_bytes(); after = path.lstat()
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    assert signature(before) == signature(after) and path.resolve(strict=True) == path
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def write(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def read_pinned(row):
    assert pin(row['path']) == row
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'] and pin(row['path']) == row
    return raw


def prepare():
    (ROOT / 'preparation').mkdir(); (ROOT / 'evidence').mkdir()
    selected = []
    for relative, expected in (
        ('final-retention-01/seal.json', 'ffc3cdc19502f8cc7cf604ca2d7494d185048b6211119b62a28fd9c887e46484'),
        ('final-retention-01/verification/readback.json', 'b664bd63023e0fc3dff8a76cd61017f04af82d6245df14744663e175b1e6cd7e'),
        ('final-retention-01/verification/final-closure.json', '2d41293aa99b5aea10aef9ead24aed2b594a4c87855543cab1e676447a04f852')):
        row = pin(PRIOR / relative); assert row['sha256'] == expected; selected.append(row)
    inherited = json.loads((PRIOR / 'final-retention-01/external-pins.json').read_bytes())['pins']
    for row in inherited:
        actual = pin(row['path']); assert actual['sha256'] == row['sha256']; selected.append(actual)
    for relative in ('preparation/input-pins.json', 'source-manifest-02.json',
                     'evidence/actual-01/metadata-inputs.json', 'evidence/actual-01/metadata-readback.json',
                     'file-only-audit-01.json'):
        selected.append(pin(PRIOR / relative))
    frozen = json.loads((PRIOR / 'evidence/freeze-01/frozen.json').read_bytes())
    assert frozen['envelope']['sha256'] == 'baf3ea631e06ff366768f489d67026d0caabd26a87d5561818db6d03b40eb508'
    envelope = json.loads(read_pinned(frozen['envelope']))
    assert envelope['corpus']['corpus_sha256'] == frozen['corpus_sha256']
    executable = Path('/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.0/bin/lean')
    request = {'schema': 'terminal-batching-grounding-request@1', 'frozen_envelope': frozen['envelope'],
        'expected_corpus_sha256': frozen['corpus_sha256'], 'query_id': 'batching-representative',
        'review_ref': 'reviewed:developer-batching-constraint-slice-20261004@1',
        'native_lean': pin(executable), 'selected_prior': selected,
        'prior_metadata_inputs': pin(PRIOR / 'evidence/actual-01/metadata-inputs.json'),
        'grounding_arguments': pin(GROUND / 'evidence/actual-03/grounding-arguments.json'),
        'grounding_result': pin(GROUND / 'evidence/actual-03/grounding-result.json'),
        'prior_grounding_metadata_inputs': pin(GROUND / 'evidence/actual-03/metadata-inputs.json'),
        'grounding_seal': pin(GROUND / 'final-retention-01/seal.json'),
        'scope': 'Closed exact-int list selector helper and exact rational ranker step prerequisites; no whole Python runtime, Hessian/binary64/asymptotic/AE convergence, original-task or planning authority.'}
    write(ROOT / 'preparation/request.json', request)
    print(json.dumps({'request': pin(ROOT / 'preparation/request.json'), 'selected_prior': len(selected)}))


def capture():
    destination = ROOT / 'source-04'; destination.mkdir()
    files = []
    entries = [(WORKSPACE / 'external/ipfs_accelerate', relative) for relative in (
        'benchmarks/agent_supervisor/container_coding/terminal_codebase_selector_semantics.py',
        'benchmarks/agent_supervisor/container_coding/terminal_codebase_ranker_step_certificate.py',
        'test/api/test_terminal_codebase_selector_semantics.py',
        'test/api/test_terminal_codebase_ranker_step_certificate.py')]
    entries += [(GROUND / 'source-04', 'test/api/test_terminal_codebase_requirement_grounding.py')]
    entries += [(HEAD / 'source', relative) for relative in ('test/__init__.py', 'test/api/__init__.py')]
    for base, relative in entries:
        original = base / relative; before = pin(original); raw = read_pinned(before)
        target = destination / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.open('xb').write(raw); target.chmod(0o444)
        files.append({'original': before, 'captured': pin(target)})
    config = destination / 'pytest.ini'; config.open('x').write('[pytest]\n'); config.chmod(0o444)
    files.append({'captured': pin(config)})
    assert pin(CAP / 'generation-manifest.json')['sha256'] == BASE_SHA
    write(ROOT / 'source-manifest-04.json', {'schema': 'terminal-batching-grounding-source-extension@1',
        'base_manifest': pin(CAP / 'generation-manifest.json'), 'base_generation_cid': BASE_CID,
        'extension_manifests': [pin(path) for path in (HEAD / 'source-manifest.json',
            CONSUMER / 'source-manifest-02.json', PRIOR / 'source-manifest-02.json',
            GROUND / 'source-manifest-04.json')],
        'files': files, 'scope': 'Stable individually pinned selected sources; no atomic whole-live or all-loader census.'})
    write(ROOT / 'preparation/producer-pins-04.json', {'driver': pin(Path(__file__).resolve()),
        'source_manifest': pin(ROOT / 'source-manifest-04.json'), 'request': pin(ROOT / 'preparation/request.json')})
    print(json.dumps({'source_manifest': pin(ROOT / 'source-manifest-04.json'),
        'producer_pins': pin(ROOT / 'preparation/producer-pins-04.json')}))


ROOTS = (ROOT / 'source-04', GROUND / 'source-04', PRIOR / 'source-02', CONSUMER / 'source-02', HEAD / 'source',
         CAP / 'accelerate', CAP / 'datasets', CAP / 'kit')


class Guard(importlib.abc.MetaPathFinder):
    def __init__(self, expected): self.expected = expected; self.records = {}; self.blocked = []
    def find_spec(self, fullname, path=None, target=None):
        if not any(fullname == prefix or fullname.startswith(prefix + '.') for prefix in
            ('benchmarks', 'ipfs_accelerate_py', 'ipfs_datasets_py', 'ipfs_kit_py', 'ipfs_kit', 'test')): return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None: raise ImportError('captured owned module unavailable: ' + fullname)
        if spec.origin is not None:
            actual = pin(spec.origin)
            if self.expected.get(actual['path']) != actual:
                self.blocked.append({'module': fullname, 'origin': spec.origin})
                raise ImportError('owned source drift: ' + fullname)
            self.records[fullname] = actual
        else:
            assert all(any(Path(value).is_relative_to(root) for root in ROOTS)
                       for value in spec.submodule_search_locations or [])
        return spec


def owned(mode):
    run = ROOT / 'evidence' / mode; run.mkdir()
    started = time.monotonic(); scheduler = lease = guard = None; cleanup = []
    receipt = {'schema': 'terminal-selector-step-owned-control@1', 'mode': mode, 'status': 'started',
        'primary_error': None, 'cleanup_errors': cleanup, 'root_lease': None,
        'new_public_fit_calls': 0, 'new_autoencoder_fits': 0, 'synthetic_fits': 0,
        'native_lean_checks_invoked': [], 'native_metadata_hydration_attempts': 0,
        'PlanCreate_calls': 0}
    try:
        producers = json.loads((ROOT / 'preparation/producer-pins-04.json').read_bytes())
        assert all(pin(row['path']) == row for row in producers.values())
        request = json.loads(read_pinned(producers['request']))
        for row in request['selected_prior']: assert pin(row['path']) == row
        assert pin(request['native_lean']['path']) == request['native_lean']
        base_raw = (CAP / 'generation-manifest.json').read_bytes(); assert sha(base_raw) == BASE_SHA
        base = json.loads(base_raw); assert base['generation_cid'] == BASE_CID
        expected = {row['captured_path']: {'path': row['captured_path'], 'bytes': row['bytes'], 'sha256': row['sha256']}
                    for row in base['files']}
        extension = json.loads(read_pinned(producers['source_manifest']))
        for manifest in [*extension['extension_manifests'], producers['source_manifest']]:
            for row in json.loads(read_pinned(manifest))['files']:
                descriptor = row['captured']; assert pin(descriptor['path']) == descriptor
                expected[descriptor['path']] = descriptor
        receipt['producer_pins'] = producers
        sys.path[:] = [str(root) for root in ROOTS] + [value for value in sys.path
            if value and not Path(value).resolve().is_relative_to(WORKSPACE)]
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'; sys.dont_write_bytecode = True
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        os.environ['IPFS_DATASETS_RESOURCE_SCHEDULER_PATH'] = str(run / 'resources.json')
        os.environ['TERMINAL_BATCHING_GROUNDING_FROZEN_ENVELOPE'] = request['frozen_envelope']['path']
        guard = Guard(expected); sys.meta_path.insert(0, guard)
        import benchmarks.agent_supervisor.container_coding as package
        package.__path__ = [str(root / 'benchmarks/agent_supervisor/container_coding') for root in ROOTS[:-3]] + list(package.__path__)
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane
        scheduler = get_global_resource_scheduler(); config = scheduler.config
        assert config.proof_safety_enabled and (config.proof_memory_stall_percent, config.proof_cpu_stall_percent,
            config.proof_io_stall_percent, config.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0)
        receipt['resource_policy'] = config.persisted_dict(); write(run / 'started.json', receipt)
        lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)
        receipt['root_lease'] = lease.to_dict()
        from benchmarks.agent_supervisor.container_coding import terminal_codebase_intent_ranker_training as head_api
        def forbidden_fit(*args, **kwargs): raise AssertionError('grounding must not fit a model')
        head_api.train_terminal_codebase_intent_ranker = forbidden_fit
        if mode.startswith('tests'):
            import pytest
            phases = []
            class Reports:
                def pytest_runtest_logreport(self, report):
                    phases.append({'nodeid': report.nodeid, 'phase': report.when, 'outcome': report.outcome,
                                   'seconds': report.duration})
            argv = ['-q', '-p', 'no:cacheprovider', '-c', str(ROOT / 'source-04/pytest.ini'), '--noconftest',
                '-o', 'addopts=', '--basetemp', str(run / 'fixtures'), '--junitxml', str(run / 'tests.xml'),
                str(ROOT / 'source-04/test/api/test_terminal_codebase_selector_semantics.py'),
                str(ROOT / 'source-04/test/api/test_terminal_codebase_ranker_step_certificate.py')]
            code = int(pytest.main(argv, plugins=[Reports()])); write(run / 'phases.json', phases)
            receipt['pytest_returncode'] = code
            assert code == 0 and all(row['outcome'] == 'passed' for row in phases), 'selected tests failed or skipped'
        elif mode.startswith('actual'):
            envelope = json.loads(read_pinned(request['frozen_envelope']))
            grounding_arguments = json.loads(read_pinned(request['grounding_arguments']))
            grounding_result = json.loads(read_pinned(request['grounding_result']))
            old_source = grounding_result['source_context']['source_record']
            public_path = WORKSPACE / '.benchmarks/terminal-bench-2/llm-inference-batching-scheduler' / old_source['path']
            public_binding = pin(public_path); public_raw = read_pinned(public_binding)
            assert public_raw == old_source['source_text'].encode()
            current_source = dict(old_source, source_text=public_raw.decode(), source_sha256=sha(public_raw))
            from benchmarks.agent_supervisor.container_coding import terminal_codebase_selector_semantics as selector_api
            from benchmarks.agent_supervisor.container_coding import terminal_codebase_ranker_step_certificate as step_api
            selector_arguments = {'grounding_receipt': grounding_result, 'grounding_arguments': grounding_arguments,
                'expected_grounding_sha256': grounding_result['grounding_sha256'], 'current_source_records': [current_source]}
            selector = selector_api.build_terminal_batching_selector_semantics(**selector_arguments)
            assert selector_api.validate_terminal_batching_selector_semantics(selector, **selector_arguments) == selector
            step_arguments = {'corpus_receipt': envelope['corpus'], 'original_inputs': envelope['original_inputs'],
                'expected_corpus_sha256': request['expected_corpus_sha256']}
            step = step_api.build_terminal_ranker_step_certificate(**step_arguments)
            assert step_api.validate_terminal_ranker_step_certificate(step, **step_arguments) == step
            write(run / 'selector-arguments.json', selector_arguments); write(run / 'selector-result.json', selector)
            write(run / 'step-arguments.json', step_arguments); write(run / 'step-result.json', step)
            receipt['current_public_source_binding'] = public_binding
            from benchmarks.agent_supervisor.container_coding import terminal_codebase_logic_qualification as logic
            checks = []; output = run / 'lean'; output.mkdir()
            selector_negative = selector['lean_source'] + '\nnamespace BatchingSelector\n' + (
                'theorem false_unconditional_lower_bound : sourceSemantics [1] 2 = some 1 ∧ (2 : Int) ≤ 1 := by decide\nend BatchingSelector\n')
            step_negative = step['lean_source'] + '\nnamespace RankerStepPrerequisites\n' + (
                'theorem false_reversed_step_bound : 1 < eta * conditionalSmoothness := by decide\nend RankerStepPrerequisites\n')
            for key, filename, source, success in (
                ('selector', 'SelectorSemantics.lean', selector['lean_source'], True),
                ('false_selector_lower_bound', 'FalseSelectorLowerBound.lean', selector_negative, False),
                ('step_parameters', 'RankerStepParameters.lean', step['lean_source'], True),
                ('false_reversed_step_bound', 'FalseReversedStepBound.lean', step_negative, False)):
                assert pin(request['native_lean']['path']) == request['native_lean']
                receipt['native_lean_checks_invoked'].append({'key': key, 'expected_success': success})
                checked = logic._compile_lean(executable=Path(request['native_lean']['path']),
                    filename=filename, source=source, output=output, expected_success=success)
                checks.append({'key': key, **checked}); write(run / ('lean-' + key + '-check.json'), checks[-1])
                assert checked['matches_expectation'] is True, 'Lean check inconclusive or wrong result: ' + key
            write(run / 'lean-checks.json', checks)
            prior = json.loads(read_pinned(request['prior_grounding_metadata_inputs']))
            assert len(prior) == 22 and sum(map(len, prior.values())) == 4209
            delta = {'selector_source_model': [selector],
                'selector_proof_obligations': [{'selector_sha256': selector['selector_sha256'],
                    'source_binding': selector['source_binding'], 'closed_domain': selector['ir']['input_domains'],
                    'assumptions': selector['model_assumptions'], 'conditional_model_checker_accepted': True,
                    'source_runtime_equivalence_verified': False, 'full_task_satisfaction': 'unknown',
                    'planning_handoff': 'abstained', 'canonical_tasks': []}],
                'ranker_step_parameters': [step], 'selector_step_lean_checks': checks}
            assert not (set(prior) & set(delta)) and len(prior) + len(delta) <= 32
            records = {**prior, **delta}; assert all(records[key] == value for key, value in prior.items())
            write(run / 'metadata-inputs.json', records)
            from benchmarks.agent_supervisor.container_coding.codebase_ir_metadata import hydrate_codebase_ir_metadata
            receipt['native_metadata_hydration_attempts'] = 1
            metadata = hydrate_codebase_ir_metadata(records=records, output=run / 'metadata',
                source_snapshot={'schema': 'terminal-selector-step-source-snapshot@1',
                    'corpus': request['frozen_envelope'], 'prior_grounding_metadata': request['prior_grounding_metadata_inputs'],
                    'selector': pin(run / 'selector-result.json'), 'step': pin(run / 'step-result.json'),
                    'lean_checks': pin(run / 'lean-checks.json'),
                    'scope': request['scope']})
            write(run / 'metadata-readback.json', metadata)
            receipt['native_metadata_readback'] = pin(run / 'metadata-readback.json')
            receipt['native_fresh_readback'] = metadata['fresh_process_readback']
            receipt['selector_result'] = pin(run / 'selector-result.json')
            receipt['step_result'] = pin(run / 'step-result.json')
            receipt['prior_4209_rows_preserved_exactly'] = True
            assert pin(public_binding['path']) == public_binding
        else:
            raise ValueError('unknown owned mode')
        for row in request['selected_prior']: assert pin(row['path']) == row
        for row in (request['native_lean'], request['frozen_envelope']): assert pin(row['path']) == row
        assert all(pin(row['path']) == row for row in producers.values())
        receipt['selected_inputs_and_prior_unchanged'] = True; receipt['status'] = 'passed'
    except BaseException as error:
        receipt['status'] = 'failed'; receipt['primary_error'] = {
            'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        if lease is not None:
            try: receipt['root_release_returned'] = lease.release()
            except BaseException as error: cleanup.append({'stage': 'release', 'error': str(error)})
        if scheduler is not None:
            try:
                state = scheduler.snapshot(); receipt['final_resource_state'] = state
                assert state['active_lease_count'] == 0 and state['waiting_request_count'] == 0
            except BaseException as error: cleanup.append({'stage': 'drain', 'error': str(error)})
        if guard is not None:
            observations = []
            for name, before in guard.records.items():
                try:
                    after = pin(before['path']); observations.append({'module': name, 'before': before, 'after': after, 'matches': before == after})
                    if before != after: cleanup.append({'stage': 'source_readback', 'module': name})
                except BaseException as error:
                    observations.append({'module': name, 'before': before, 'after': None, 'matches': False, 'error': str(error)})
                    cleanup.append({'stage': 'source_readback', 'module': name, 'error': str(error)})
            receipt['selected_owned_imports'] = observations; receipt['blocked_imports'] = guard.blocked
        if cleanup: receipt['status'] = 'failed'
        receipt['elapsed_seconds_owned'] = time.monotonic() - started; write(run / 'closed.json', receipt)
    print(json.dumps({'status': receipt['status'], 'owned_seconds': receipt['elapsed_seconds_owned'], 'primary_error': receipt['primary_error']}))
    return 0 if receipt['status'] == 'passed' else 1


def outer(mode):
    started = time.monotonic(); child = None
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), 'owned', mode]
    record = {'schema': 'terminal-selector-step-outer-control@1', 'argv': argv,
        'driver': pin(Path(__file__).resolve()), 'producer_pin_specification': pin(ROOT / 'preparation/producer-pins-04.json'),
        'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'returncode': None, 'primary_error': None, 'cleanup_errors': []}
    write(ROOT / 'evidence' / (mode + '-invocation.json'), record)
    try:
        with (ROOT / 'evidence' / (mode + '.stdout.log')).open('x') as stream:
            child = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT)
            record['child_pid'] = child.pid; record['returncode'] = child.wait(timeout=120)
    except BaseException as error:
        record['primary_error'] = {'type': type(error).__name__, 'message': str(error)}
        if child is not None and child.poll() is None:
            try:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
            except BaseException as cleanup_error: record['cleanup_errors'].append(str(cleanup_error))
        record['returncode'] = child.returncode if child is not None else None
    finally:
        record['elapsed_seconds_outer'] = time.monotonic() - started
        write(ROOT / 'evidence' / (mode + '-closed.json'), record)
    print(json.dumps(record)); return record['returncode'] or (1 if record['primary_error'] or record['cleanup_errors'] else 0)


if __name__ == '__main__':
    if sys.argv[1] == 'prepare': prepare()
    elif sys.argv[1] == 'capture': capture()
    elif sys.argv[1] == 'owned': raise SystemExit(owned(sys.argv[2]))
    else: raise SystemExit(outer(sys.argv[1]))
