#!/usr/bin/env python3
"""Freeze a paired Terminal Bench required-instruction query-reference experiment. Default prints a plan only."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/terminal-query-reference-20261012')
DATASET = Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2')
AXES = ['jobs_dir', 'job_name', 'agents[0].kwargs.query_reference_policy']
MODES = ('legacy', 'required-instruction-ref@1')


def normalize_config(config):
    value = copy.deepcopy(config)
    value.pop('jobs_dir', None)
    value.pop('job_name', None)
    agents = value.get('agents')
    if type(agents) is not list or len(agents) != 1 or type(agents[0]) is not dict:
        raise ValueError('one configured agent required')
    agents[0].get('kwargs', {}).pop('query_reference_policy', None)
    return value


def planned_trials():
    return [dict(name=name, task=task, repeat=1, query_reference_policy=mode,
                 semantic_context_profile='indexed-default@1', semantic_metadata_view='legacy')
        for name, task, mode in [
            ('batching-legacy-01', 'llm-inference-batching-scheduler', MODES[0]),
            ('batching-reference-01', 'llm-inference-batching-scheduler', MODES[1]),
            ('mjcf-reference-01', 'tune-mjcf', MODES[1]),
            ('mjcf-legacy-01', 'tune-mjcf', MODES[0])]]


def skeleton():
    return dict(schema='terminal-query-reference-comparison-protocol@1', trials=planned_trials(),
        requested_axis='query_reference_policy', pairs_match_except=AXES, execution_order='legacy-reference on batching, reference-legacy on MJCF',
        preparations={}, repeats_per_arm_per_task=1, max_concurrent_trials=1,
        resource_profile='source384-5cpu-16gib-extended@1', model='gpt-6.1-sol',
        reasoning_effort='high', cli_version='0.160.0', coding_reply_mode='ordinary-completion@1', cached_input_is_subset=True,
        failures_retained_in_requested_arm=True, native_fallback_retained_in_requested_arm=True,
        actual_reference_dispatch_required=True, live_token_savings_claimed_before_execution=False,
        task_solutions_not_read=True, verifier_files_hashed_only=True,
        limitations=['One repeat per arm on two tasks cannot establish statistical or causal improvement.',
            'Native cumulative tokens include all observed command capture and retrieval overhead.',
            'Exact input inclusion does not establish model attention, source understanding or task correctness.'])


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def source_pin(source):
    return subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()


def offline_gate(root, source):
    path = root / 'public-final/qualification.json'
    replay_path = root / 'independent-public-replay.json'
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 4 * 1024**2 for p in (path, replay_path)):
        raise ValueError('bounded final public qualification and independent replay required')
    raw = path.read_bytes()
    qualification = json.loads(raw)
    replay = json.loads(replay_path.read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if (qualification.get('schema') != 'terminal-query-reference-experiment@1'
            or qualification.get('qualified') is not True or qualification.get('provider_calls') != 0
            or replay.get('qualification_sha256') != digest or replay.get('all_four_inputs_exact') is not True):
        raise ValueError('complete independently replayed offline qualification required')
    rows = qualification.get('tasks')
    if (type(rows) is not list or len(rows) != 2
            or {row.get('task_name') for row in rows} != {row['task'] for row in planned_trials()}):
        raise ValueError('exact two-task qualification required')
    bodies = {'experiment': 'benchmarks/agent_supervisor/container_coding/terminal_query_reference_experiment.py',
        'query_reference_codec': 'ipfs_accelerate_py/agent_supervisor/runtime/semantic_query_reference.py',
        'router': 'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
        'input_audit': 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'}
    expected = {key: hashlib.sha256((source / relative).read_bytes()).hexdigest() for key, relative in bodies.items()}
    metrics = []
    for row in rows:
        if (row.get('qualified') is not True or row.get('implementation_sha256') != expected
                or row.get('coding_reply_mode') != 'ordinary-completion@1'
                or row.get('stale_required_instruction_refused') is not True
                or row.get('matched_source_selection') is not True):
            raise ValueError('offline implementation, selection or freshness differs')
        arms = row['arms']
        if ([arm.get('policy') for arm in arms] != list(MODES)
                or arms[1].get('positive_reference_observed') is not True
                or any(arm.get('historical_replay_after_workspace_removed') is not True for arm in arms)):
            raise ValueError('actual reference dispatch and historical replay required')
        for key in ('full_input_bytes', 'full_input_proxy_tokens'):
            values = [arm.get(key) for arm in arms]
            if any(type(value) is not int or value <= 0 for value in values) or values[1] >= values[0]:
                raise ValueError('positive matched complete-input improvement required')
        metrics.append({'task': row['task_name'], 'comparison': row['comparison']})
    return {'qualification_sha256': digest,
        'independent_replay_sha256': hashlib.sha256(replay_path.read_bytes()).hexdigest(),
        'source_bodies_match': True, 'positive_reference_inputs_required': True,
        'metrics': metrics, 'scope': 'local complete-input proxy; not provider usage'}


def prepare_campaign(args):
    root, source, archive = args.root.resolve(), args.source.resolve(), args.archive.resolve()
    if not re.fullmatch('[0-9a-f]{40}', args.source_commit or ''):
        raise ValueError('explicit final source commit required')
    if not re.fullmatch('[0-9a-f]{64}', args.archive_sha256 or ''):
        raise ValueError('explicit final archive SHA256 required')
    def check_source():
        if source_pin(source) != args.source_commit or subprocess.check_output(
                ['git', '-C', str(source), 'status', '--porcelain'], text=True).strip():
            raise ValueError('clean final source pin required')
    check_source()
    gate = offline_gate(root, source)
    verification = json.loads((archive / 'verification.json').read_text())
    if verification['source_repositories']['source']['head'] != args.source_commit:
        raise ValueError('archive source pin differs')
    with (archive / 'runtime.tar.gz').open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != args.archive_sha256 or digest != verification['archive_sha256']:
        raise ValueError('archive digest differs')
    for name in ('comparison-protocol.json', 'launcher-protocol.json'):
        if (root / name).exists():
            raise ValueError('campaign protocol already frozen')
    protocol = skeleton()
    protocol.update(source_commit=args.source_commit, archive_sha256=digest, offline_gate=gate)
    for row in protocol['trials']:
        if (root / 'trials' / row['name']).exists():
            raise ValueError('fresh trial directory required: ' + row['name'])
    sys.path.insert(0, str(source))
    from benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark import prepare
    from benchmarks.agent_supervisor.container_coding.terminal_profile_catalog import reviewed_profile
    from benchmarks.agent_supervisor.container_coding.terminal_task_profile import task_profile_bytes
    (root / 'profiles').mkdir(exist_ok=True)
    for task in sorted({row['task'] for row in protocol['trials']}):
        selected = reviewed_profile(dataset=args.dataset.resolve(), task_name=task)
        with (root / 'profiles' / (task + '.json')).open('xb') as stream:
            stream.write(task_profile_bytes(selected['profile']))
    for row in protocol['trials']:
        output = root / 'trials' / row['name']
        result = prepare(dataset=args.dataset.resolve(), output=output, archive=archive, arm='full',
            task_name=row['task'], task_profile=(root / 'profiles' / (row['task'] + '.json')),
            semantic_context_profile=row['semantic_context_profile'], semantic_metadata_view='legacy',
            resource_profile=protocol['resource_profile'], query_reference_policy=row['query_reference_policy'],
            coding_reply_mode=protocol['coding_reply_mode'])
        if (result.get('prepared') is not True or result.get('archive_sha256') != digest
                or any(result.get(key) != protocol[key] for key in ('model', 'reasoning_effort', 'cli_version'))):
            raise ValueError('prepared runtime/provider controls differ')
        config = json.loads((output / 'config.json').read_text())
        frozen = {key: result[key] for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256')}
        frozen['normalized_configuration'] = normalize_config(config)
        if protocol['preparations'].setdefault(row['task'], frozen) != frozen:
            raise ValueError('non-policy comparison controls differ')
        row['config_sha256'] = result['config_sha256']
        print(json.dumps({'trial': row['name'], 'prepared': True, 'provider_calls': 0}), flush=True)
    check_source()
    write_new(root / 'launcher-protocol.json', dict(schema='terminal-indexed-context-launcher-protocol@1',
        source_head=args.source_commit, archive_sha256=digest, native_cli_version='0.160.0',
        datasets_head=verification['source_repositories']['datasets']['head'],
        kit_head=verification['source_repositories']['kit']['head']))
    write_new(root / 'comparison-protocol.json', protocol)
    return protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--archive', type=Path, default=ROOT / 'runtime-archive-v1')
    parser.add_argument('--dataset', type=Path, default=DATASET)
    parser.add_argument('--source-commit')
    parser.add_argument('--archive-sha256')
    args = parser.parse_args()
    if not args.prepare:
        print(json.dumps(skeleton(), indent=2, sort_keys=True))
        return
    prepare_campaign(args)


if __name__ == '__main__':
    main()
