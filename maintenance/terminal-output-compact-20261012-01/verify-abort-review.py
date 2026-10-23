#!/usr/bin/env python3
"""Independent bounded metadata review of the aborted compact-policy campaign."""
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
HEAD = '4185bcabd7580a59d4afe34663df02158f693ba5'
ARCHIVE = '82c4893088339bdede7d473f1598059861650f203c60a2215e347bb0fe447f5d'
spec = importlib.util.spec_from_file_location('independent_review_primitives', ROOT / 'verify-benchmark-review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
read, sha = review.read, review.sha
checks = []


def check(name, value):
    checks.append({'check': name, 'passed': bool(value)})


def digest_file(path, maximum):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError('bounded regular artifact required')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


protocol = read(ROOT / 'comparison-protocol.json')
benchmark = read(ROOT / 'benchmark.json')
archive_verification = read(ROOT / 'runtime-archive-v1/verification.json')
manifest = read(ROOT / 'runtime-archive-v1/manifest.json')
source_validation = read(ROOT / 'source-validation.json')
receipt_path = ROOT / 'trials/mjcf-legacy-01/receipt.json'
receipt = read(receipt_path)
state = ROOT / 'launcher-state/mjcf-legacy-01'
claim, outcome = read(state / 'claim.json'), read(state / 'outcome.json')
batches = list((ROOT / 'launcher-state').glob('batch-*.json'))
check('single_batch', len(batches) == 1)
batch = read(batches[0])
rows = {row['name']: row for row in benchmark['trials']}
check('requested_abba_population_retained', list(rows) == [r[0] for r in review.ORDER]
      and [(r['name'], r['tool_output_policy'], r['repeat']) for r in protocol['trials']] == review.ORDER)
check('frozen_source_and_archive_bound', protocol['source_commit'] == benchmark['source_commit']
      == claim['source_head'] == archive_verification['source_repositories']['source']['head'] == HEAD
      and protocol['archive_sha256'] == benchmark['archive_sha256'] == claim['archive_sha256']
      == archive_verification['archive_sha256'] == manifest['archive_sha256'] == ARCHIVE)
check('archive_bytes_independently_rehashed', digest_file(ROOT / 'runtime-archive-v1/runtime.tar.gz', 2 * 1024**3) == ARCHIVE)
check('historical_archive_qualification_retained', archive_verification['all_archive_entries_match_inventory'] is True
      and archive_verification['all_packaged_source_matches_checkout_after_build'] is True
      and archive_verification['files_verified'] == 27435)
check('source_qualification_retained', source_validation['source_commit'] == HEAD
      and source_validation['source_tests_passed'] == 496
      and source_validation['source_worktree_clean_at_freeze'] is True)
for relative in ('ipfs_accelerate_py/agent_supervisor/runtime/tool_output_artifact.py',
                 'ipfs_accelerate_py/agent_supervisor/runtime/tool_output_policy.py',
                 'benchmarks/agent_supervisor/container_coding/full_supervisor_harbor_agent.py'):
    content = subprocess.check_output(['git', '-C', str(SOURCE), 'show', HEAD + ':' + relative], timeout=10)
    candidates = [item for item in manifest['files'] if item['path'] == 'source/' + relative]
    check('frozen_archive_source.' + Path(relative).name, len(candidates) == 1
          and candidates[0]['sha256'] == sha(content))

pending = []
for name, policy, repeat in review.ORDER:
    folder = ROOT / 'trials' / name
    config, prepared = read(folder / 'config.json'), read(folder / 'preparation.json')
    expected = next(item for item in protocol['trials'] if item['name'] == name)
    check(name + '.frozen_configuration', sha((folder / 'config.json').read_bytes())
          == expected['config_sha256'] == prepared['config_sha256'])
    check(name + '.normalized_controls', review.normalized(config)
          == protocol['preparations']['tune-mjcf']['normalized_configuration'])
    check(name + '.input_pins', all(prepared[key] == protocol['preparations']['tune-mjcf'][key]
          for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256')))
    check(name + '.selected_policy', config['agents'][0]['kwargs'].get('tool_output_policy', 'legacy')
          == prepared.get('tool_output_policy', 'legacy') == rows[name]['requested_policy'] == policy)
    check(name + '.usage_unknown_and_ineligible', rows[name]['comparison_eligible'] is False
          and rows[name]['native_usage_complete'] is False
          and all(rows[name]['complete_tokens'][key] is None for key in review.TOKEN_KEYS)
          and rows[name]['official_reward'] is None)
    if name != 'mjcf-legacy-01':
        unstarted = (not (folder / 'receipt.json').exists()
                     and not (ROOT / 'launcher-state' / name).exists()
                     and not list(folder.glob('jobs/*/*/result.json')))
        check(name + '.unstarted_without_invocation_claim', unstarted and rows[name]['state'] == 'pending'
              and rows[name]['durations_seconds'] == {} and rows[name].get('invocations', []) == [])
        pending.append({'name': name, 'launch_claim_absent': unstarted, 'state': rows[name]['state']})

trial = receipt['trials'][0]
check('single_expected_failed_trial', receipt['trial_count'] == len(receipt['trials']) == 1
      and receipt['task'] == 'tune-mjcf' and trial['task'] == 'terminal-bench/tune-mjcf'
      and trial['exact_trial_task_matches'] is True)
check('failed_setup_receipt_join', sha(receipt_path.read_bytes()) == rows['mjcf-legacy-01']['receipt_sha256']
      == outcome['receipt_sha256'] and outcome['native_result_sha256'] == trial['native_result_sha256'])
check('failed_setup_configuration_join', claim['config_sha256']
      == sha((ROOT / 'trials/mjcf-legacy-01/config.json').read_bytes()))
check('task_inputs_preserved', receipt['original_task_inputs_unchanged'] is True
      and receipt['comparison_controls']['configuration_unchanged'] is True)
check('setup_failure_before_recorded_agent_or_verifier', trial['exception_type'] == 'AgentSetupTimeoutError'
      and trial['supervisor'] is None and trial['agent_context'] is None and trial['reward'] is None
      and trial['durations_seconds']['agent_execution'] is None
      and trial['durations_seconds']['verifier'] is None
      and outcome['classification'] == 'setup_failed' and outcome['supervisor_usage'] is None)
check('batch_stopped_without_retry', batch['all_requested_trials_finished'] is False
      and batch['automatic_retries'] == 0 and len(batch['outcomes']) == 1
      and batch['outcomes'][0] == outcome and outcome['continue_batch'] is False
      and claim['automatic_retry'] is False)
check('missing_provider_usage_not_zeroed', rows['mjcf-legacy-01']['invocations'] == []
      and all(value is None for value in outcome['usage'].values())
      and all(value is None for value in rows['mjcf-legacy-01']['observed_token_subtotal'].values())
      and all(rows['mjcf-legacy-01'][key] is None for key in ('helper_capture_count',
          'helper_read_count', 'helper_read_bytes', 'observed_tool_call_events',
          'observed_tool_input_bytes', 'observed_tool_output_bytes', 'uncached_input_tokens')))
check('no_completed_comparison_or_savings', benchmark['status'] == 'pending'
      and benchmark['all_trials_comparison_eligible'] is False
      and benchmark['mean_total_token_change_percent'] is None
      and benchmark['token_savings_established'] is False
      and benchmark['statistically_significant_improvement_established'] is False
      and all(arm['complete_usage'] is False and all(v is None for v in arm['means'].values())
              for arm in benchmark['arms'].values()))

native_name = trial['trial']
if re.fullmatch(r'tune-mjcf__[A-Za-z0-9]+', native_name) is None:
    raise ValueError('exact native project identity required')
native_result = ROOT / 'trials/mjcf-legacy-01/jobs/supervisor-full-tune-mjcf' / native_name / 'result.json'
check('native_result_metadata_hash_join', str(native_result) == outcome['native_result_path']
      and digest_file(native_result, 16 * 1024**2) == trial['native_result_sha256'])
project = native_name.lower() + '__env'
containers = subprocess.check_output(['docker', 'ps', '-a', '--filter',
    'label=com.docker.compose.project=' + project, '--format', '{{json .Names}}'], timeout=15)
check('exact_owned_project_containers_absent', not containers.strip())

events_path = state / 'events.jsonl'
if events_path.is_symlink() or not 0 < events_path.stat().st_size <= 4 * 1024**2:
    raise ValueError('bounded launcher event metadata required')
lines = events_path.read_bytes().splitlines()
if len(lines) > 10000:
    raise ValueError('bounded launcher event count required')
events = [json.loads(line) for line in lines]
samples = [event['sample'] for event in events if type(event.get('sample')) is dict]
if not samples or not all(type(sample.get(key)) in (int, float) and math.isfinite(sample[key])
        and sample[key] >= 0 for sample in samples for key in
        ('mem_available_bytes', 'disk_free_bytes', 'load_1m', 'load_limit', 'affinity_cpus')):
    raise ValueError('finite bounded resource samples required')
pressured = sum(bool(event.get('pressure_reasons')) for event in events)
config = read(ROOT / 'trials/mjcf-legacy-01/config.json')
environment = config['environment']
check('fixed_container_limits', environment['override_cpus'] == 5
      and environment['override_memory_mb'] == 16384
      and environment['cpu_enforcement_policy'] == environment['memory_enforcement_policy'] == 'limit')
durations = trial['durations_seconds']
check('timing_metadata_preserved', rows['mjcf-legacy-01']['durations_seconds'] == {
      key: value for key, value in durations.items() if value is not None}
      and 0 < durations['agent_setup'] < receipt['invocation_seconds'] < 1800)

report = {
    'schema': 'independent-compact-campaign-abort-review@1',
    'reviewed_at': datetime.now(timezone.utc).isoformat(),
    'source_commit': HEAD, 'archive_sha256': ARCHIVE,
    'benchmark_sha256': sha((ROOT / 'benchmark.json').read_bytes()),
    'protocol_sha256': sha((ROOT / 'comparison-protocol.json').read_bytes()),
    'receipt_sha256': sha(receipt_path.read_bytes()),
    'script_sha256': sha(Path(__file__).read_bytes()),
    'events_sha256': sha(events_path.read_bytes()),
    'all_checks_passed': all(item['passed'] for item in checks),
    'check_count': len(checks), 'checks': checks,
    'outcome': 'setup_failed_before_recorded_agent_execution',
    'failure_type': trial['exception_type'], 'durations_seconds': durations,
    'invocation_seconds': receipt['invocation_seconds'],
    'three_remaining_trials': pending,
    'native_provider_invocations_observed': [], 'provider_token_cost_known': False,
    'comparison_eligible': False, 'compact_format_adoption_established': False,
    'live_token_savings_established': False,
    'resources': {
        'sample_count': len(samples), 'first_sample_at': samples[0]['at'], 'last_sample_at': samples[-1]['at'],
        'min_mem_available_bytes': min(s['mem_available_bytes'] for s in samples),
        'min_disk_free_bytes': min(s['disk_free_bytes'] for s in samples),
        'max_load_1m': max(s['load_1m'] for s in samples),
        'max_load_limit': max(s['load_limit'] for s in samples),
        'pressure_event_count': pressured,
        'admission_backoff_count': sum(event.get('event') == 'resource_admission'
                                      and event.get('admitted') is False for event in events),
        'configured_cpus': 5, 'configured_memory_bytes': 16384 * 1024**2,
        'observations_are_sampled_not_continuous': True,
        'pressure_injection_performed': False, 'stress_test_performed': False,
        'system_stability_guaranteed': False,
    },
    'cleanup': {'exact_compose_project': project, 'owned_containers_absent': not containers.strip(),
                'worker_cleanup_receipt_available': False,
                'scope': 'Read-only exact project-label query; no claims about unrelated containers.'},
    'reviewer_provider_calls': 0, 'raw_logs_or_provider_transcripts_read': False,
    'hidden_task_test_contents_read': False,
    'qualification': 'The 496-test source qualification and 129 authored byte probes remain valid. This aborted campaign provides no live model comparison; unavailable token costs remain unknown. Setup timing alone does not identify its cause.',
}
(ROOT / 'independent-abort-review.json').write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
print(json.dumps({key: report[key] for key in ('all_checks_passed', 'check_count', 'outcome', 'benchmark_sha256')}))
if not report['all_checks_passed']:
    print(json.dumps([item for item in checks if not item['passed']]))
    raise SystemExit(1)
