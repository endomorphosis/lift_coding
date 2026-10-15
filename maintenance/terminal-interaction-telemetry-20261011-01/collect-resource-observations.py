#!/usr/bin/env python3
"""Summarize completed launcher observations and query only owned trial containers.

This collector issues Docker read-only queries. It never removes containers or
executes task code, models, source changes, or pressure injection.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
GIB = 1024**3


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(samples):
    times = [datetime.fromisoformat(row['at']) for row in samples]
    return {
        'sample_count': len(samples),
        'first_sample_at': samples[0]['at'], 'last_sample_at': samples[-1]['at'],
        'minimum_sampled_mem_available_bytes': min(row['mem_available_bytes'] for row in samples),
        'minimum_sampled_disk_free_bytes': min(row['disk_free_bytes'] for row in samples),
        'maximum_sampled_load_1m': max(row['load_1m'] for row in samples),
        'affinity_cpu_counts': sorted({row['affinity_cpus'] for row in samples}),
        'maximum_observed_sample_interval_seconds': max(
            ((after - before).total_seconds() for before, after in zip(times, times[1:])), default=0),
    }


def collect_trial(name):
    state, trial = ROOT / 'launcher-state' / name, ROOT / 'trials' / name
    outcome = load(state / 'outcome.json')
    events = [json.loads(line) for line in (state / 'events.jsonl').read_text().splitlines()]
    if not events or events[-1].get('event') != 'trial_finished':
        raise ValueError('launcher event stream is not complete: ' + name)
    if outcome.get('process_returncode') is None:
        raise ValueError('trial process did not settle: ' + name)
    samples = [row['sample'] for row in events if 'sample' in row]
    config, receipt = load(trial / 'config.json'), load(trial / 'receipt.json')
    if receipt.get('complete_single_trial_receipt') is not True or len(receipt.get('trials', [])) != 1:
        raise ValueError('complete single-trial receipt required: ' + name)
    native_name = receipt['trials'][0]['trial']
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', native_name):
        raise ValueError('bounded native trial name required')
    project = (native_name + '__env').lower()
    command = ['docker', 'ps', '-a', '--filter', 'name=^/' + project + '-',
               '--filter', 'label=com.docker.compose.project=' + project,
               '--format', '{{json .ID}} {{json .Names}} {{json .Status}}']
    found = subprocess.check_output(command, text=True, timeout=15).splitlines()
    environment = config['environment']
    pressure = [row for row in events if row.get('pressure_reasons')]
    backoff = [row for row in events if row['event'] == 'resource_backoff']
    return {
        'trial': name, 'native_trial_name': native_name,
        'launcher_started_at': load(state / 'process.json')['started_at'],
        'launcher_finished_at': events[-1]['at'],
        'classification': outcome['classification'], 'official_rewards': outcome.get('official_rewards'),
        'process_returncode': outcome['process_returncode'],
        'events_sha256': digest(state / 'events.jsonl'), 'outcome_sha256': digest(state / 'outcome.json'),
        'receipt_sha256': digest(trial / 'receipt.json'),
        'resources': summary(samples),
        'pressure_event_count': len(pressure),
        'pressure_events': [{'at': row['at'], 'event': row['event'], 'reasons': row['pressure_reasons']} for row in pressure],
        'backoff_event_count': len(backoff), 'backoff_seconds': sum(row['sleep_seconds'] for row in backoff),
        'backoff_durations_seconds': [row['sleep_seconds'] for row in backoff],
        'admission_decisions': [{'at': row['at'], 'admitted': row['admitted']} for row in events if row['event'] == 'resource_admission'],
        'configured_container': {key: environment[key] for key in (
            'override_cpus', 'override_memory_mb', 'cpu_enforcement_policy', 'memory_enforcement_policy', 'force_build', 'delete')},
        'post_trial_container_observation': {
            'checked_at': datetime.now(timezone.utc).isoformat(), 'command': command,
            'matched_containers': found, 'owned_trial_containers_absent': not found,
            'harbor_cleanup_configured': environment.get('delete') is True,
            'cleanup_command_issued_by_collector': False,
            'scope': 'Exact native trial Compose project and matching container-name prefix only.',
        },
    }, samples


def main():
    names = [row['name'] for row in load(ROOT / 'comparison-protocol.json')['trials']]
    if (not 1 <= len(names) <= 16 or len(set(names)) != len(names)
            or any(not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}', name)
                   for name in names)):
        raise ValueError('unique bounded campaign trial names required')
    observations, samples = [], []
    for name in names:
        row, selected = collect_trial(name)
        observations.append(row)
        samples.extend(selected)
    samples.sort(key=lambda row: row['at'])
    aggregate = summary(samples)
    # A gap between sequential trials is not a within-trial monitoring gap.
    aggregate.pop('maximum_observed_sample_interval_seconds')
    aggregate['maximum_within_trial_sample_interval_seconds'] = max(
        row['resources']['maximum_observed_sample_interval_seconds'] for row in observations)
    report = {
        'schema': 'terminal-indexed-context-resource-observations@1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'trial_order': names,
        'sequential_trials': all(
            datetime.fromisoformat(before['launcher_finished_at']) <= datetime.fromisoformat(after['launcher_started_at'])
            for before, after in zip(observations, observations[1:])),
        'admission_criteria': {'minimum_mem_available_bytes': 24 * GIB,
                               'minimum_disk_free_bytes': 20 * GIB,
                               'maximum_load_1m_fraction_of_affinity_cpus': 0.85,
                               'backoff_initial_seconds': 5, 'backoff_multiplier': 2,
                               'backoff_maximum_seconds': 30},
        'monitor_sample_interval_seconds': 15,
        'active_pressure_policy': 'Observe active work; do not kill it for ordinary transient pressure.',
        'trials': observations, 'aggregate_sampled_resources': aggregate,
        'pressure_events': sum(row['pressure_event_count'] for row in observations),
        'backoff_events': sum(row['backoff_event_count'] for row in observations),
        'all_owned_trial_containers_absent_after_completion': all(
            row['post_trial_container_observation']['owned_trial_containers_absent'] for row in observations),
        'pressure_injection_performed': False, 'stress_test_performed': False,
        'system_stability_guaranteed': False,
        'limits': ['Periodic host observations can miss peaks between samples.',
                   'No outside-pressure injection was performed; these trials do not establish live backoff behavior under injected load.',
                   'Configured container limits and observed host headroom do not establish a system-stability guarantee.',
                   'Container absence is a post-completion observation; the collector issued no cleanup commands.'],
        'provider_calls_by_collector': 0, 'source_files_modified': False,
    }
    path = ROOT / 'resource-observations.json'
    with path.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'report': str(path), 'resources': aggregate,
                      'pressure_events': report['pressure_events'], 'backoff_events': report['backoff_events'],
                      'owned_trial_containers_absent': report['all_owned_trial_containers_absent_after_completion']}))


if __name__ == '__main__':
    main()
