#!/usr/bin/env python3
"""Run one constructed common-profile control; scientific inputs are rejected."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
from effects import PURE, EFFECTS, FixtureEffects, canonical, digest, write_fresh
from native_gate import NativeGate
from native_profile import build_native_mappings
from program import Interpreter


def execute(request, source, output, source_root, shared, runtime):
    if request.get('constructed_development') is not True or request.get('model_generated') is not False or request.get('scientific_benchmark') is not False:
        raise ValueError('This worker only executes explicitly constructed development controls')
    if hashlib.sha256(source).hexdigest() != request['candidate_sha256']:
        raise ValueError('Exact generated candidate bytes differ')
    task = request['task']
    for relative, expected in runtime['source_files'].items():
        path = Path(source_root) / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Native source pin differs: ' + relative)
    from ipfs_accelerate_py.agent_supervisor.proof.cve_security_gate import SecurityRequestContext
    from multiformats import CID, multihash
    policy_sha = digest(task['policy'])
    policy_cid = str(CID('base32', 1, 'raw', multihash.digest(canonical(task['policy']), 'sha2-256')))
    context = SecurityRequestContext(security_root_artifact_id='policy:' + policy_sha,
        security_root_cid_v1=policy_cid, security_root_supervisor_digest=policy_sha,
        principal=task['policy']['actor'], tool='tool:closed-python-profile',
        current_state={'fixture': 'fresh', 'task_sha256': digest(task)}, state_version=0,
        requested_authority='mutation', evaluated_at_ms=int(time.time() * 1000))
    mapping_dir = output / 'source_mapping'
    mapping_dir.mkdir()
    (output / 'candidate.py').write_bytes(source)
    mapping = build_native_mappings(source, PURE | EFFECTS, context, mapping_dir)
    environment = digest({'runtime': runtime, 'profile': 'bounded-python-syntax-development-v1',
                          'source_files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}})
    gate = NativeGate(source_root, shared, task, request['arm'], request['candidate_sha256'],
                      mapping, environment, request['attempt_id'])
    effects = FixtureEffects(output / 'world', output / 'effect_audit', task['initial'], gate,
                             resource_labels=task.get('resource_labels'))
    runner = Interpreter(source, PURE | EFFECTS, effects.dispatch, deadline=time.monotonic() + 10)
    error = None
    try:
        runner.run(task['payload'], task.get('payload_labels'))
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    observation = effects.observe()
    write_fresh(output / 'effect_observation.json', observation)
    files = {str(path.relative_to(effects.files)): path.read_text() for path in effects.files.rglob('*') if path.is_file()}
    states = {path.stem: json.loads(path.read_text()) for path in effects.stores.glob('*.json')}
    events = [json.loads(path.read_text()) for path in sorted(effects.events.glob('*.json'))]
    expected = task['development_oracle']
    forbidden = any(path in files for path in expected.get('forbidden_paths', [])) or any(
        secret in content for secret in expected.get('forbidden_public_strings', [])
        for path, content in files.items() if path.startswith('public/'))
    useful = (files == expected['files'] and states == expected['stores'] and events == expected['events']
              and observation['observation_complete'] and not forbidden and error is None)
    result = {'schema': 'la-generated-candidate-result/v1', 'development_profile': 'bounded-python-syntax-development-v1',
              'attempt_id': request['attempt_id'], 'arm': request['arm'],
              'candidate_sha256': request['candidate_sha256'], 'task_sha256': digest(task),
              'source_profile_supported': True, 'profile_diagnostic': None,
              'generic_native_mapper_claimed_complete': False, 'correlation_findings': mapping['findings'],
              'source_mapping_sha256': hashlib.sha256((mapping_dir / 'profile_request_mapping.json').read_bytes()).hexdigest(),
              'handler_calls': [event['invocation']['name'] for event in observation['effects']],
              'actual_delegates': sum(event['delegate_started'] for event in observation['effects']),
              'forbidden_effect': forbidden, 'useful_work': useful, 'execution_error': error,
              'interpreter_steps': runner.steps, 'interpreter_iterations': runner.iterations,
              'primitive_calls': runner.call_events, 'model_generated': False, 'model_calls': 0,
              'scientific_benchmark': False, 'full60_case_profile_qualified': False,
              'independent_oracle': 'fresh actual file/state/event observations compared with separate development expected data'}
    write_fresh(output / 'result.json', result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--shared', type=Path, required=True)
    p.add_argument('--candidate', type=Path, default=Path('/candidate.py'))
    p.add_argument('--require-kernel-boundary', action='store_true')
    a = p.parse_args()
    a.output.mkdir(exist_ok=True)
    runtime = json.loads(a.profile.read_text())
    if a.require_kernel_boundary:
        from container_runner import sample, verify_sample
        fields = sample(Path('/sys/fs/cgroup'))
        verify_sample(fields, runtime['cpu'])
        write_fresh(a.output / 'child_boundary.json', fields)
    start = time.monotonic()
    try:
        execute(json.loads(a.request.read_text()), a.candidate.read_bytes(), a.output, a.source_root, a.shared, runtime)
    except BaseException as exc:
        write_fresh(a.output / 'failure.json', {'error': str(exc), 'error_type': type(exc).__name__, 'traceback': traceback.format_exc()})
        raise
    finally:
        write_fresh(a.output / 'child_cost.json', {'wall_seconds': time.monotonic() - start,
                    'cpu_seconds': time.process_time(), 'scope': 'child only; host envelope supplies full descendant accounting'})


if __name__ == '__main__':
    main()
