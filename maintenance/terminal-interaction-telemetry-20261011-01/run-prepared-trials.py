#!/usr/bin/env python3
"""Run explicitly named prepared trials sequentially, with resource admission.

Usage (no model calls):
  python run-prepared-trials.py --preflight-only batching-default-01 batching-compact-01
Usage (executes the named prepared model trials exactly once):
  python run-prepared-trials.py batching-default-01 batching-compact-01

All launcher artifacts live in launcher-state, outside immutable preparations.
Interrupted or failed trials are never retried. Read their retained receipts and
prepare a new trial explicitly if another experiment is warranted. There is no
container cleanup or pressure-triggered termination in this launcher.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

CAMPAIGN = Path(__file__).resolve().parent
TRIALS = CAMPAIGN / 'trials'
STATE = CAMPAIGN / 'launcher-state'
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
DATASETS = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011')
KIT = Path('/home/barberb/lift_coding/.worktrees/publication-main-20261004/kit')
HARBOR_PYTHON = Path('/home/barberb/lift_coding/.venvs/terminal-bench-harbor/bin/python')
SOURCE_HEAD = None
ARCHIVE_SHA256 = None
DEPENDENCY_HEADS = {}
GIB = 1024**3
MIN_MEMORY_BYTES = 24 * GIB
MIN_DISK_BYTES = 20 * GIB
LOAD_FRACTION = 0.85


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
        raise ValueError('bounded regular JSON required: ' + str(path))
    with path.open() as stream:
        return json.load(stream)


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def validate_campaign_pins(value):
    fields = {'schema', 'source_head', 'datasets_head', 'kit_head', 'archive_sha256', 'native_cli_version'}
    if not isinstance(value, dict) or set(value) != fields or value['schema'] != 'terminal-indexed-context-launcher-protocol@1':
        raise ValueError('explicit complete campaign launcher protocol required')
    for name in ('source_head', 'datasets_head', 'kit_head', 'archive_sha256'):
        size = 64 if name == 'archive_sha256' else 40
        if not isinstance(value[name], str) or not re.fullmatch('[0-9a-f]{' + str(size) + '}', value[name]):
            raise ValueError('complete immutable revision/digest required: ' + name)
    if value['native_cli_version'] != '0.160.0':
        raise ValueError('review this launcher before changing its native CLI pin')
    return value


def resource_sample():
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        memory[key] = int(value.strip().split()[0]) * 1024
    affinity = len(os.sched_getaffinity(0))
    return {
        'at': now(), 'mem_available_bytes': memory['MemAvailable'],
        'disk_free_bytes': shutil.disk_usage(CAMPAIGN).free,
        'load_1m': os.getloadavg()[0], 'affinity_cpus': affinity,
        'load_limit': LOAD_FRACTION * affinity,
    }


def pressure_reasons(sample):
    reasons = []
    if sample['mem_available_bytes'] < MIN_MEMORY_BYTES:
        reasons.append('available_memory_below_24_GiB')
    if sample['disk_free_bytes'] < MIN_DISK_BYTES:
        reasons.append('free_disk_below_20_GiB')
    if sample['load_1m'] > LOAD_FRACTION * sample['affinity_cpus']:
        reasons.append('load_above_85_percent_of_affinity_CPUs')
    return reasons


def emit(stream, event):
    stream.write(json.dumps({'at': now(), **event}, sort_keys=True) + '\n')
    stream.flush()


def await_resources(stream, max_wait, *, sample_fn=resource_sample, sleeper=time.sleep,
                    monotonic=time.monotonic):
    started, delay = monotonic(), 5.0
    while True:
        sample = sample_fn()
        reasons = pressure_reasons(sample)
        emit(stream, {'event': 'resource_admission', 'sample': sample,
                      'admitted': not reasons, 'pressure_reasons': reasons})
        if not reasons:
            return sample
        remaining = max_wait - (monotonic() - started)
        if remaining <= 0:
            raise TimeoutError('resource admission wait exhausted; no trial launched')
        duration = min(delay, remaining, 30.0)
        emit(stream, {'event': 'resource_backoff', 'sleep_seconds': duration})
        sleeper(duration)
        delay = min(30.0, delay * 2)


def selected_environment():
    overrides = {
        'PATH': str(CAMPAIGN / 'native-cli/node_modules/.bin') + os.pathsep + os.environ.get('PATH', ''),
        'PYTHONPATH': os.pathsep.join(map(str, (SOURCE, DATASETS, KIT))),
        'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
        'DOCKER_DEFAULT_PLATFORM': 'linux/arm64', 'PYTHONUNBUFFERED': '1',
    }
    return {**os.environ, **overrides}, overrides


def validate_host(env):
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True, timeout=10).strip()
    if head != SOURCE_HEAD:
        raise ValueError('frozen source revision differs')
    dependencies = {}
    for name, path in (('datasets', DATASETS), ('kit', KIT)):
        revision = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True, timeout=10).strip()
        if revision != DEPENDENCY_HEADS.get(name):
            raise ValueError('frozen dependency revision differs: ' + name)
        dependencies[name] = revision
    cli = CAMPAIGN / 'native-cli/node_modules/.bin/codex'
    version = subprocess.check_output([str(cli), '--version'], env=env, text=True, timeout=30).strip()
    if version != 'codex-cli 0.160.0':
        raise ValueError('private native CLI pin differs')
    architecture = subprocess.check_output(
        ['docker', 'version', '--format', '{{.Server.Os}}/{{.Server.Arch}}'],
        env=env, text=True, timeout=15).strip()
    if architecture not in ('linux/arm64', 'linux/aarch64'):
        raise ValueError('selected Docker daemon is not Linux arm64')
    return {'source_head': head, 'dependency_heads': dependencies,
            'codex_version': version, 'docker_platform': architecture}


def validate_trial(name):
    if not isinstance(ARCHIVE_SHA256, str) or not re.fullmatch(r'[0-9a-f]{64}', ARCHIVE_SHA256):
        raise ValueError('load the frozen campaign protocol before validating a trial')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}', name):
        raise ValueError('simple prepared trial name required')
    output = TRIALS / name
    if output.resolve(strict=True) != output:
        raise ValueError('canonical prepared trial directory required')
    config = read_json(output / 'config.json')
    prepared = read_json(output / 'preparation.json')
    if prepared.get('prepared') is not True or digest(output / 'config.json') != prepared.get('config_sha256'):
        raise ValueError('trial is not prepared or its configuration changed: ' + name)
    if prepared.get('archive_sha256') != ARCHIVE_SHA256 or prepared.get('cli_version') != '0.160.0':
        raise ValueError('trial archive/provider selection differs: ' + name)
    environment = config.get('environment', {})
    required = {'force_build': True, 'override_cpus': 5, 'override_memory_mb': 16384,
                'cpu_enforcement_policy': 'limit', 'memory_enforcement_policy': 'limit'}
    if any(environment.get(key) != value for key, value in required.items()):
        raise ValueError('trial does not enforce the common native build/resource profile')
    if config.get('n_attempts') != 1 or config.get('n_concurrent_trials') != 1 or config.get('retry', {}).get('max_retries') != 0:
        raise ValueError('trial may retry or run concurrently')
    job = Path(config['jobs_dir']) / config['job_name']
    if not job.is_relative_to(output) or job.resolve() != job:
        raise ValueError('native job artifacts must remain inside the prepared output')
    for marker in (output / 'invocation.json', output / 'receipt.json', job, STATE / name / 'claim.json'):
        if marker.exists():
            raise ValueError('one-shot trial has already been invoked or claimed: ' + name)
    return {'name': name, 'output': output, 'job': job, 'prepared': prepared,
            'config_sha256': prepared['config_sha256']}


def unresolved_campaign_invocations():
    return sorted(path.parent.name for path in TRIALS.glob('*/invocation.json')
                  if not (path.parent / 'receipt.json').is_file())


def process_sample(process):
    status = {'pid': process.pid, 'returncode': process.poll()}
    try:
        for line in Path('/proc', str(process.pid), 'status').read_text().splitlines():
            key, value = line.split(':', 1)
            if key in ('State', 'VmRSS', 'VmPeak', 'Threads'):
                status[key] = value.strip()
    except FileNotFoundError:
        status['process_exited_during_sample'] = True
    return status


def supervisor_error_observation(report):
    """Retain dispatch/error categories without copying prompts or tracebacks."""
    error = report.get('error')
    invocations = report.get('provider_invocations')
    def label(value):
        return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_@.:-]{1,128}', value) else None
    return {
        'error_present': bool(error),
        'error_type': label(error.get('type')) if isinstance(error, dict) else None,
        'error_phase': label(report.get('error_phase')),
        'provider_invocation_count': len(invocations) if isinstance(invocations, list) else None,
        'coding_dispatch_possible': report.get('coding_dispatch_possible') is True,
        'unreceipted_provider_attempt': bool(report.get('unreceipted_provider_attempt')),
        'implementation_route': label(report.get('implementation_route')),
        'model_router_record_present': bool(report.get('model_router')),
        'error_category': ('worker_context_budget_exceeded'
                           if isinstance(error, dict) and error.get('message') == 'worker context exceeds configured budget'
                           else 'other' if error else None),
    }


def classify_receipt(receipt, native):
    """A completed setup timing is insufficient: Harbor records it on errors too."""
    if not (native.get('agent_execution') or {}).get('started_at'):
        return 'setup_failed', False
    if (receipt.get('schema') != 'terminal-full-supervisor-receipt@1'
            or receipt.get('complete_single_trial_receipt') is not True
            or receipt.get('trial_count') != 1 or len(receipt.get('trials', [])) != 1
            or receipt.get('native_job_result_present') is not True
            or not native.get('finished_at')):
        return 'incomplete_receipt', False
    trial = receipt['trials'][0]
    if not isinstance(trial.get('supervisor'), dict):
        return 'incomplete_supervisor_receipt', False
    dispatch = supervisor_error_observation(trial['supervisor'])
    if dispatch['error_present']:
        if dispatch['unreceipted_provider_attempt']:
            return 'incomplete_provider_dispatch_receipt', False
        if not dispatch['provider_invocation_count']:
            if (dispatch['coding_dispatch_possible'] or dispatch['model_router_record_present']
                    or dispatch['provider_invocation_count'] is None):
                return 'supervisor_dispatch_unknown', False
            return 'supervisor_predispatch_failed', False
    rewards = (native.get('verifier_result') or {}).get('rewards')
    if not isinstance(rewards, dict) or not rewards:
        return 'incomplete_verifier_receipt', False
    if any(isinstance(value, (int, float)) and value > 0 for value in rewards.values()):
        return 'task_passed', True
    return 'task_failed', True


def collect_outcome(trial, returncode):
    result = {'trial': trial['name'], 'process_returncode': returncode,
              'receipt_path': str(trial['output'] / 'receipt.json'),
              'classification': 'incomplete_receipt', 'continue_batch': False}
    native_paths = sorted(trial['job'].glob('*/result.json'))
    if len(native_paths) != 1:
        result['native_result_count'] = len(native_paths)
        return result
    native = read_json(native_paths[0])
    context = native.get('agent_result') or {}
    result.update(native_result_path=str(native_paths[0]), native_result_sha256=digest(native_paths[0]),
                  native_exception_type=(native.get('exception_info') or {}).get('exception_type'),
                  official_rewards=(native.get('verifier_result') or {}).get('rewards'),
                  usage={key: context.get(key) for key in ('n_input_tokens', 'n_cache_tokens', 'n_output_tokens', 'cost_usd')},
                  supervisor_usage=(context.get('metadata') or {}).get('usage'),
                  usage_scope='Observed native counters; cached input is a subset, missing values remain unknown.')
    path = trial['output'] / 'receipt.json'
    if not path.is_file():
        if not (native.get('agent_execution') or {}).get('started_at'):
            result['classification'] = 'setup_failed'
        return result
    receipt = read_json(path)
    result['receipt_sha256'] = digest(path)
    result['classification'], result['continue_batch'] = classify_receipt(receipt, native)
    rows = receipt.get('trials')
    if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0].get('supervisor'), dict):
        result['supervisor_error_observation'] = supervisor_error_observation(rows[0]['supervisor'])
    if returncode != 0:
        result.update(classification='launcher_or_harness_failed', continue_batch=False)
    return result


def run_trial(trial, *, env, overrides, max_wait, interval):
    state = STATE / trial['name']
    state.mkdir(exist_ok=False)
    with (state / 'events.jsonl').open('x') as events:
        try:
            await_resources(events, max_wait)
        except TimeoutError:
            result = {'trial': trial['name'], 'classification': 'resource_wait_exhausted',
                      'continue_batch': False, 'process_started': False}
            write_json(state / 'outcome.json', result)
            return result
        # Recheck after waiting, then acquire the durable one-shot claim before Popen.
        validate_trial(trial['name'])
        unresolved = unresolved_campaign_invocations()
        if unresolved:
            raise ValueError('unresolved campaign invocation requires review: ' + ', '.join(unresolved))
        argv = [str(HARBOR_PYTHON), '-m',
                'benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark',
                'execute', '--output', str(trial['output'])]
        claim = {'at': now(), 'trial': trial['name'], 'command': argv,
                 'cwd': str(SOURCE), 'environment_overrides': overrides,
                 'config_sha256': trial['config_sha256'], 'source_head': SOURCE_HEAD,
                 'archive_sha256': ARCHIVE_SHA256, 'automatic_retry': False}
        write_json(state / 'claim.json', claim)
        process = None
        try:
            with (state / 'execute.stdout').open('x') as stdout, (state / 'execute.stderr').open('x') as stderr:
                process = subprocess.Popen(argv, cwd=SOURCE, env=env, stdout=stdout, stderr=stderr)
                write_json(state / 'process.json', {'pid': process.pid, 'started_at': now()})
                while True:
                    sample = resource_sample()
                    emit(events, {'event': 'active_trial_sample', 'process': process_sample(process),
                                  'sample': sample, 'pressure_reasons': pressure_reasons(sample),
                                  'pressure_action': 'observe_only_no_termination'})
                    try:
                        returncode = process.wait(timeout=interval)
                        break
                    except subprocess.TimeoutExpired:
                        pass
            result = collect_outcome(trial, returncode)
        except BaseException as error:
            result = {'trial': trial['name'], 'classification': 'launcher_interrupted_or_failed',
                      'continue_batch': False, 'error_type': type(error).__name__,
                      'child_pid': process.pid if process else None,
                      'child_returncode': process.poll() if process else None,
                      'pressure_termination_performed': False,
                      'review_required': True}
            write_json(state / 'outcome.json', result)
            emit(events, {'event': 'launcher_stopped', 'outcome': result})
            raise
        write_json(state / 'outcome.json', result)
        emit(events, {'event': 'trial_finished', 'outcome': result})
        return result


def main():
    global SOURCE_HEAD, ARCHIVE_SHA256, DEPENDENCY_HEADS
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trials', nargs='+', help='Prepared trial directory names, in execution order')
    parser.add_argument('--preflight-only', action='store_true', help='Check configuration/resources without claims, containers, or model calls')
    parser.add_argument('--max-resource-wait-seconds', type=float, default=1800)
    parser.add_argument('--sample-interval-seconds', type=float, default=15)
    args = parser.parse_args()
    if len(set(args.trials)) != len(args.trials):
        parser.error('duplicate trial names would repeat an experiment')
    if not 0 <= args.max_resource_wait_seconds <= 86400 or not 1 <= args.sample_interval_seconds <= 30:
        parser.error('resource wait must be 0..86400 and sampling interval 1..30 seconds')
    protocol_path = CAMPAIGN / 'launcher-protocol.json'
    pins = validate_campaign_pins(read_json(protocol_path))
    SOURCE_HEAD, ARCHIVE_SHA256 = pins['source_head'], pins['archive_sha256']
    DEPENDENCY_HEADS = {'datasets': pins['datasets_head'], 'kit': pins['kit_head']}
    env, overrides = selected_environment()
    host = validate_host(env)
    selected = [validate_trial(name) for name in args.trials]
    sample = resource_sample()
    preflight = {'schema': 'terminal-sequential-launcher-preflight@1', 'host': host,
                 'campaign_protocol_sha256': digest(protocol_path),
                 'trials': args.trials, 'environment_overrides': overrides, 'resources': sample,
                 'pressure_reasons': pressure_reasons(sample),
                 'unresolved_invocations': unresolved_campaign_invocations(),
                 'provider_calls': 0, 'containers_launched': 0}
    if args.preflight_only:
        print(json.dumps(preflight, sort_keys=True))
        return 0
    STATE.mkdir(exist_ok=True)
    with (STATE / 'batch.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        outcomes = []
        batch = STATE / ('batch-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        for trial in selected:
            outcome = run_trial(trial, env=env, overrides=overrides,
                                max_wait=args.max_resource_wait_seconds, interval=args.sample_interval_seconds)
            outcomes.append(outcome)
            print(json.dumps(outcome, sort_keys=True), flush=True)
            if not outcome['continue_batch']:
                break
        write_json(batch, {'schema': 'terminal-sequential-launcher-batch@1', 'preflight': preflight,
                           'requested_trials': args.trials, 'outcomes': outcomes,
                           'all_requested_trials_finished': len(outcomes) == len(selected)
                                and all(row['continue_batch'] for row in outcomes),
                           'failed_task_usage_retained': True, 'automatic_retries': 0})
        return 0 if len(outcomes) == len(selected) and all(row['continue_batch'] for row in outcomes) else 2


if __name__ == '__main__':
    raise SystemExit(main())
