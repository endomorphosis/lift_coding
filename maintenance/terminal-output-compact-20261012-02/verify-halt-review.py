#!/usr/bin/env python3
"""Independent content-free review of retained partial-campaign evidence."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
HEAD = '487647c68f8a419cd39586b4bd5eb2de8fc54012'
ARCHIVE = '54a2b6f65ac03a7b4694b7029333a66627aa8be0bbccbf16156f25b244aaf6b7'
spec = importlib.util.spec_from_file_location('independent_review_helpers', ROOT / 'verify-benchmark-review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
read, sha = review.read, review.sha
checks = []


def check(name, value):
    checks.append({'check': name, 'passed': bool(value)})


def digest_file(path, bound):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= bound:
        raise ValueError('bounded regular metadata artifact required')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_events(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 4 * 1024**2:
        raise ValueError('bounded regular launcher event metadata required')
    lines = path.read_bytes().splitlines()
    if len(lines) > 10000:
        raise ValueError('bounded launcher event count required')
    events = [json.loads(line) for line in lines]
    if not events or events[-1].get('event') != 'trial_finished':
        raise ValueError('settled launcher events required')
    return events


def summarize(samples):
    keys = ('mem_available_bytes', 'disk_free_bytes', 'load_1m', 'load_limit', 'affinity_cpus')
    if not samples or not all(type(row.get(key)) in (int, float) and math.isfinite(row[key])
                             and row[key] >= 0 for row in samples for key in keys):
        raise ValueError('finite resource census required')
    times = [datetime.fromisoformat(row['at']) for row in samples]
    if any(after < before for before, after in zip(times, times[1:])):
        raise ValueError('ordered resource census required')
    return {
        'sample_count': len(samples), 'first_sample_at': samples[0]['at'], 'last_sample_at': samples[-1]['at'],
        'minimum_sampled_mem_available_bytes': min(row['mem_available_bytes'] for row in samples),
        'minimum_sampled_disk_free_bytes': min(row['disk_free_bytes'] for row in samples),
        'maximum_sampled_load_1m': max(row['load_1m'] for row in samples),
        'affinity_cpu_counts': sorted({row['affinity_cpus'] for row in samples}),
        'maximum_within_trial_sample_interval_seconds': max(
            ((after - before).total_seconds() for before, after in zip(times, times[1:])), default=0),
    }


protocol = read(ROOT / 'comparison-protocol.json')
benchmark = read(ROOT / 'benchmark.json')
preparation_review = read(ROOT / 'independent-preparation-review.json')
previous_review = read(ROOT / 'independent-review.json')
by_name = {row['name']: row for row in benchmark['trials']}
batches = list((ROOT / 'launcher-state').glob('batch-*.json'))
check('one_batch_retained', len(batches) == 1)
batch = read(batches[0])
check('clean_frozen_source', subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'],
      text=True, timeout=15).strip() == HEAD and not subprocess.check_output(
      ['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True, timeout=15).strip())
check('source_archive_and_protocol_pins', protocol['source_commit'] == benchmark['source_commit']
      == preparation_review['source_commit'] == HEAD
      and protocol['archive_sha256'] == benchmark['archive_sha256'] == preparation_review['archive_sha256'] == ARCHIVE
      and sha((ROOT / 'comparison-protocol.json').read_bytes()) == preparation_review['protocol_sha256'])
check('all_requested_trials_retained', list(by_name) == [row[0] for row in review.ORDER]
      and [(row['name'], row['tool_output_policy'], row['repeat']) for row in protocol['trials']] == review.ORDER)
check('no_partial_campaign_comparison', benchmark['status'] == 'pending'
      and benchmark['all_trials_comparison_eligible'] is False
      and benchmark['mean_total_token_change_percent'] is None
      and benchmark['token_savings_established'] is False
      and benchmark['statistically_significant_improvement_established'] is False
      and all(arm['complete_usage'] is False and all(value is None for value in arm['means'].values())
              for arm in benchmark['arms'].values())
      and all(pair['qualified'] is False and pair['total_token_change_percent'] is None for pair in benchmark['pairs']))
check('batch_stopped_without_retries_or_exclusion', batch['all_requested_trials_finished'] is False
      and batch['automatic_retries'] == 0
      and [row['trial'] for row in batch['outcomes']] == ['mjcf-legacy-01', 'mjcf-compact-01']
      and batch['outcomes'][0]['continue_batch'] is True and batch['outcomes'][1]['continue_batch'] is False)

observed, resources, all_samples = [], [], []
all_invocation_ids, all_session_ids = [], []
for name, policy, repeat in review.ORDER:
    folder = ROOT / 'trials' / name
    state = ROOT / 'launcher-state' / name
    projected = by_name[name]
    config, prepared = read(folder / 'config.json'), read(folder / 'preparation.json')
    expected = next(row for row in protocol['trials'] if row['name'] == name)
    check(name + '.config_and_controls_preserved', sha((folder / 'config.json').read_bytes())
          == prepared['config_sha256'] == expected['config_sha256']
          and review.normalized(config) == protocol['preparations']['tune-mjcf']['normalized_configuration'])
    check(name + '.requested_arm_preserved', projected['requested_policy']
          == prepared.get('tool_output_policy', 'legacy')
          == config['agents'][0]['kwargs'].get('tool_output_policy', 'legacy') == policy)
    if not (folder / 'receipt.json').exists():
        check(name + '.unstarted_and_unknown', not state.exists()
              and not list(folder.glob('jobs/*/*/result.json'))
              and projected['state'] == 'pending' and projected['comparison_eligible'] is False
              and projected['native_usage_complete'] is False and projected['official_reward'] is None
              and all(value is None for value in projected['complete_tokens'].values()))
        observed.append({'name': name, 'requested_policy': policy, 'state': 'unstarted',
                         'complete_tokens': projected['complete_tokens'], 'official_reward': None})
        continue
    receipt_path = folder / 'receipt.json'
    receipt, outcome, claim = read(receipt_path), read(state / 'outcome.json'), read(state / 'claim.json')
    check(name + '.claim_frozen_pins', claim['archive_sha256'] == ARCHIVE and claim['source_head'] == HEAD
          and claim['config_sha256'] == sha((folder / 'config.json').read_bytes()))
    check(name + '.receipt_hash_join', sha(receipt_path.read_bytes()) == projected['receipt_sha256'] == outcome['receipt_sha256'])
    trial = receipt['trials'][0]
    check(name + '.exact_original_task', len(receipt['trials']) == 1 and receipt['task'] == 'tune-mjcf'
          and trial['task'] == 'terminal-bench/tune-mjcf' and trial['exact_trial_task_matches'] is True
          and receipt['original_task_inputs_unchanged'] is True)
    native_name = trial['trial']
    if not re.fullmatch(r'tune-mjcf__[A-Za-z0-9]+', native_name):
        raise ValueError('exact native project identity required')
    native_folder = folder / 'jobs/supervisor-full-tune-mjcf' / native_name
    check(name + '.native_result_hash_join', digest_file(native_folder / 'result.json', 16 * 1024**2)
          == trial['native_result_sha256'] == outcome['native_result_sha256'])
    deployment = read(native_folder / 'agent/deployment/deployment.json')
    boundary = read(native_folder / 'agent/worker-boundary/deployment.json')
    check(name + '.deployment_qualified', deployment['qualified'] is True and deployment['codex_installed'] is True
          and deployment['archive_sha256'] == ARCHIVE and boundary['qualified'] is True)
    supervisor = trial['supervisor']
    calls = supervisor['provider_invocations']
    all_invocation_ids.extend(call['invocation_id'] for call in calls)
    all_session_ids.extend(call['native_rollout_usage']['thread_id'] for call in calls)
    check(name + '.official_outcome_retained', projected['official_reward'] == trial['reward']['reward']
          == outcome['official_rewards']['reward'])
    row = {'name': name, 'requested_policy': policy, 'state': 'settled',
           'official_reward': projected['official_reward'], 'complete_tokens': projected['complete_tokens'],
           'provider_invocations_observed': len(calls),
           'provider_phases': [call['phase'] for call in calls],
           'durations_seconds': trial['durations_seconds'],
           'receipt_sha256': sha(receipt_path.read_bytes()), 'native_trial_name': native_name,
           'deployment_sha256': sha((native_folder / 'agent/deployment/deployment.json').read_bytes())}
    if name == 'mjcf-legacy-01':
        totals = {key: sum(call['native_rollout_usage']['usage'][key] for call in calls) for key in review.TOKEN_KEYS}
        check(name + '.native_usage_complete_and_counted_once', len(calls) == 2
              and {call['phase'] for call in calls} == {'planning', 'coding'}
              and all(review.usage(call['native_rollout_usage'])[1] for call in calls)
              and totals == projected['complete_tokens'] and totals['total_tokens'] == 460754
              and projected['uncached_input_tokens'] == totals['input_tokens'] - totals['cached_input_tokens'])
        control_checks = [check for check in previous_review['checks'] if check['check'].startswith(name + '.')]
        check(name + '.independent_input_audit_and_controls_passed', bool(control_checks)
              and all(check['passed'] for check in control_checks)
              and previous_review['benchmark_sha256'] == sha((ROOT / 'benchmark.json').read_bytes()))
        check(name + '.success_and_cleanup_qualification', receipt['complete_single_trial_receipt'] is True
              and projected['comparison_eligible'] is True and projected['official_reward'] == 1
              and supervisor['worker_cleanup_returncode'] == supervisor['remaining_processes'] == 0)
    else:
        failure = calls[0]
        native = failure['native_rollout_usage']
        check(name + '.structured_rate_limit_before_coding', len(calls) == 1 and failure['phase'] == 'planning'
              and failure['status'] == 'failed' and failure['error_type'] == 'LLMRouterError'
              and failure['provider_failure'] == {'phase': 'provider_invocation', 'reason_code': 'rate_limit'}
              and supervisor['error']['type'] == 'RuntimeError' and supervisor['error_phase'] == 'planning')
        check(name + '.unknown_tokens_not_zeroed_or_excluded', receipt['complete_single_trial_receipt'] is False
              and projected['comparison_eligible'] is False and projected['official_reward'] == 0
              and projected['native_usage_complete'] is False and native['usage_available'] is False
              and native['usage'] == {} and native['observed_token_count_records'] == 0
              and all(value is None for value in projected['complete_tokens'].values())
              and all(value is None for value in projected['observed_token_subtotal'].values())
              and all(value is None for value in outcome['usage'].values()))
        check(name + '.no_coding_advisory_or_helper_adoption_claim', not any(call['phase'] == 'coding' for call in calls)
              and all('tool_output_policy' not in call for call in calls)
              and projected['advisory_verified'] is False and projected['exact_coding_audit_verified'] is False
              and projected['helper_capture_count'] is projected['helper_read_count'] is None)
        check(name + '.worker_census_unknown_preserved', supervisor['worker_cleanup_returncode'] == 0
              and supervisor['remaining_processes'] is None and projected['worker_cleanup_complete'] is False)
        row.update(failure_reason_code=failure['provider_failure']['reason_code'],
                   failure_phase='planning', failure_type=failure['error_type'],
                   failed_provider_invocation_seconds=failure['seconds'],
                   native_usage_available=False, native_token_checkpoint_count=native['observed_token_count_records'],
                   coding_advisory_observed=False, compact_format_adoption_established=False)
    observed.append(row)
    project = native_name.lower() + '__env'
    remaining = subprocess.check_output(['docker', 'ps', '-a', '--filter',
        'label=com.docker.compose.project=' + project, '--format', '{{json .Names}}'], timeout=15)
    check(name + '.exact_owned_project_containers_absent', not remaining.strip())
    events = bounded_events(state / 'events.jsonl')
    samples = [event['sample'] for event in events if type(event.get('sample')) is dict]
    summary = summarize(samples)
    all_samples.extend(samples)
    environment = config['environment']
    check(name + '.fixed_container_resource_limits', environment['override_cpus'] == 5
          and environment['override_memory_mb'] == 16384
          and environment['cpu_enforcement_policy'] == environment['memory_enforcement_policy'] == 'limit')
    resources.append({'trial': name, 'samples': summary,
                      'events_sha256': sha((state / 'events.jsonl').read_bytes()),
                      'started_at': read(state / 'process.json')['started_at'], 'finished_at': events[-1]['at'],
                      'pressure_event_count': sum(bool(event.get('pressure_reasons')) for event in events),
                      'backoff_event_count': sum(event.get('event') == 'resource_backoff' for event in events),
                      'exact_compose_project': project, 'owned_containers_absent': not remaining.strip(),
                      'configured_cpus': 5, 'configured_memory_bytes': 16384 * 1024**2})

check('native_counts_unique_across_trials', len(all_invocation_ids) == len(set(all_invocation_ids))
      and len(all_session_ids) == len(set(all_session_ids)))
check('sequential_settled_trials', all(datetime.fromisoformat(left['finished_at'])
      <= datetime.fromisoformat(right['started_at']) for left, right in zip(resources, resources[1:])))
all_samples.sort(key=lambda row: row['at'])
aggregate = summarize(all_samples)
aggregate['maximum_within_trial_sample_interval_seconds'] = max(
    row['samples']['maximum_within_trial_sample_interval_seconds'] for row in resources)
report = {
    'schema': 'independent-compact-campaign-halt-review@1',
    'reviewed_at': datetime.now(timezone.utc).isoformat(),
    'source_commit': HEAD, 'archive_sha256': ARCHIVE,
    'benchmark_sha256': sha((ROOT / 'benchmark.json').read_bytes()),
    'protocol_sha256': sha((ROOT / 'comparison-protocol.json').read_bytes()),
    'script_sha256': sha(Path(__file__).read_bytes()),
    'all_checks_passed': all(check['passed'] for check in checks), 'check_count': len(checks), 'checks': checks,
    'trials': observed, 'settled_trial_count': 2, 'unstarted_trial_count': 2,
    'campaign_complete': False, 'live_comparison_eligible': False,
    'failed_trial_preserved_in_requested_arm': True, 'no_retroactive_trial_exclusion': True,
    'compact_format_adoption_established': False, 'token_savings_established': False,
    'resources': {'aggregate_sampled_resources': aggregate, 'trials': resources,
                  'pressure_event_count': sum(row['pressure_event_count'] for row in resources),
                  'backoff_event_count': sum(row['backoff_event_count'] for row in resources),
                  'all_owned_project_containers_absent': all(row['owned_containers_absent'] for row in resources),
                  'pressure_injection_performed': False, 'stress_test_performed': False,
                  'system_stability_guaranteed': False, 'observation_scope': 'Periodic sampled host resources; peaks between samples remain unknown.'},
    'provider_calls_by_reviewer': 0, 'raw_provider_logs_transcripts_or_auth_read': False,
    'hidden_task_test_contents_read': False,
    'interpretation': 'The control passed with complete native token counts. The first compact-assigned trial failed during planning with structured rate_limit, before coding/advisory observations; its token cost remains unknown and it stays in its assigned arm. Two trials remain unstarted, so no live token comparison is available. The rate_limit category establishes neither hard quota nor reset time nor compact-policy causality. Container absence is separate from the failed trial’s unavailable worker-process census.',
}
(ROOT / 'independent-halt-review.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
print(json.dumps({key: report[key] for key in ('all_checks_passed', 'check_count', 'settled_trial_count', 'unstarted_trial_count', 'benchmark_sha256')}))
if not report['all_checks_passed']:
    print(json.dumps([check for check in checks if not check['passed']]))
    raise SystemExit(1)
