#!/usr/bin/env python3
"""Independent metadata-only review of the retained output-preview experiment."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
SOURCE_HEAD = '540c253f29c089368ccfb4657a5de0e27df8d20f'
ARCHIVE = 'c464f28bee18f5a394176d9ad9e8f3debbb944bc544eec2da3a3ee52d9c65d1f'
TOKEN_KEYS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'total_tokens')
ORDER = [('mjcf-legacy-01', 'legacy', 1), ('mjcf-preview-01', 'artifact-preview@1', 1),
         ('mjcf-preview-02', 'artifact-preview@1', 2), ('mjcf-legacy-02', 'legacy', 2)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 16 * 1024**2:
        raise ValueError('bounded regular metadata required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate metadata key')
            result[key] = value
        return result
    def finite_float(raw):
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError('nonfinite metadata number')
        return value
    value = json.loads(path.read_bytes(), object_pairs_hook=unique, parse_float=finite_float,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite metadata')))
    return value


def number(value):
    return type(value) is int and 0 <= value < 2**63


def normalized(config):
    value = copy.deepcopy(config)
    value.pop('jobs_dir', None)
    value.pop('job_name', None)
    value['agents'][0]['kwargs'].pop('tool_output_policy', None)
    return value


def usage(native):
    values = native.get('usage', {})
    valid = (all(number(values.get(key)) for key in TOKEN_KEYS)
             and values['input_tokens'] + values['output_tokens'] == values['total_tokens']
             and values['cached_input_tokens'] <= values['input_tokens'])
    for key, parent in [('cache_write_input_tokens', 'input_tokens'),
                        ('reasoning_output_tokens', 'output_tokens')]:
        if key in values:
            valid = valid and number(values[key]) and values[key] <= values[parent]
    complete = valid and all(native.get(key) is True for key in
        ('usage_available', 'task_complete_observed', 'cache_included_in_input'))
    return valid, complete


def main():
    checks, observed, cross_ids = [], [], {'invocation': [], 'session': []}
    def check(name, value):
        checks.append({'check': name, 'passed': bool(value)})
    protocol = read(ROOT / 'comparison-protocol.json')
    benchmark = read(ROOT / 'benchmark.json')
    if {row.get('name') for row in benchmark.get('trials', [])} != {row[0] for row in ORDER}:
        print(json.dumps({'campaign_complete': False, 'completed_receipts': 0,
                          'status': 'pending_benchmark_refresh', 'provider_calls': 0}))
        return
    check('frozen_protocol', protocol['source_commit'] == SOURCE_HEAD and protocol['archive_sha256'] == ARCHIVE)
    check('abba_order', [(r['name'], r['tool_output_policy'], r['repeat']) for r in protocol['trials']] == ORDER)
    check('clean_source_pin', subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE_HEAD
          and not subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip())
    by_name = {row['name']: row for row in benchmark['trials']}
    check('all_requested_trials_retained', list(by_name) == [row[0] for row in ORDER])
    common = None
    helper_hash = sha((SOURCE / 'ipfs_accelerate_py/agent_supervisor/runtime/tool_output_artifact.py').read_bytes())
    for expected, (name, policy, repeat) in zip(protocol['trials'], ORDER):
        folder = ROOT / 'trials' / name
        config, prepared = read(folder / 'config.json'), read(folder / 'preparation.json')
        projection = by_name[name]
        current = normalized(config)
        if common is None:
            common = current
        check(name + '.matched_configuration', current == common == protocol['preparations']['tune-mjcf']['normalized_configuration'])
        check(name + '.frozen_configuration', sha((folder / 'config.json').read_bytes()) == expected['config_sha256'] == prepared['config_sha256'])
        check(name + '.requested_arm_retained', projection['requested_policy'] == policy
              and prepared.get('tool_output_policy', 'legacy') == policy
              and config['agents'][0]['kwargs'].get('tool_output_policy', 'legacy') == policy)
        check(name + '.input_pins', all(prepared[key] == protocol['preparations']['tune-mjcf'][key]
              for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256')))
        task_path = Path(config['tasks'][0]['path'])
        public_task = task_path / 'task.toml'
        if public_task.is_symlink() or not 0 < public_task.stat().st_size <= 256000:
            raise ValueError('bounded public task configuration required')
        public_bytes = public_task.read_bytes()
        check(name + '.public_task_configuration_pin', sha(public_bytes) == prepared['task_input_sha256']['task.toml'])
        native_task_name = tomllib.loads(public_bytes.decode()).get('task', {}).get('name', task_path.name)
        if not (folder / 'receipt.json').exists():
            check(name + '.pending_not_fabricated', projection['comparison_eligible'] is False
                  and all(value is None for value in projection['complete_tokens'].values()))
            continue
        receipt = read(folder / 'receipt.json')
        check(name + '.settled_state_matches', (projection['state'] == 'finished') is
              (receipt.get('native_job_result_present') is True))
        check(name + '.receipt_projection_pin', projection['receipt_sha256'] == sha((folder / 'receipt.json').read_bytes()))
        check(name + '.original_inputs_preserved', receipt['original_task_inputs_unchanged'] is True)
        check(name + '.one_expected_task', len(receipt['trials']) == 1 and receipt['trials'][0]['task'] == native_task_name
              and receipt['task'] == prepared['task'] == 'tune-mjcf'
              and receipt['trials'][0]['exact_trial_task_matches'] is True)
        trial = receipt['trials'][0]
        report = trial['supervisor']
        calls = report['provider_invocations']
        check(name + '.bounded_phase_population', 0 < len(calls) <= 16 and {r['phase'] for r in calls} == {'planning', 'coding'})
        invocations = [r['invocation_id'] for r in calls]
        sessions = [r['native_rollout_usage']['thread_id'] for r in calls]
        unique = len(set(invocations)) == len(invocations) and len(set(sessions)) == len(sessions)
        check(name + '.unique_native_counts', unique)
        cross_ids['invocation'] += invocations
        cross_ids['session'] += sessions
        native_complete = unique and not report.get('unreceipted_provider_attempt') and all(usage(r['native_rollout_usage'])[1] for r in calls)
        check(name + '.native_completeness_preserved', projection['native_usage_complete'] is native_complete)
        totals = {key: sum(r['native_rollout_usage']['usage'][key] for r in calls) if native_complete else None for key in TOKEN_KEYS}
        check(name + '.native_token_arithmetic', projection['complete_tokens'] == totals)
        if native_complete:
            check(name + '.cache_is_subset', projection['uncached_input_tokens'] == totals['input_tokens'] - totals['cached_input_tokens'])
        audit = report['context_input_audit']
        coding = [r for r in calls if r['phase'] == 'coding']
        exact = (audit['status'] == 'verified_all_observed_model_inputs'
                 and audit['all_observed_coding_inputs_verified'] is True and audit['read_errors'] == []
                 and audit['coding_receipts_seen'] == audit['usable_coding_receipts'] == len(coding)
                 and {r['invocation_id'] for r in audit['invocations']} == {r['invocation_id'] for r in coding})
        helper_captures = helper_reads = 0 if policy == 'artifact-preview@1' else None
        for call in coding:
            joined = [r for r in audit['matches'] if r['invocation_id'] == call['invocation_id']]
            exact = exact and bool(joined) and all(r['model_input_verified'] is True
                and r['model_prompt_sha256'] == call['model_prompt_sha256']
                and r['model_prompt_bytes'] == call['model_prompt_bytes']
                and r['model_input_checks'] and all(v is True for v in r['model_input_checks'].values()) for r in joined)
            if policy == 'artifact-preview@1':
                binding = call['tool_output_policy']
                helper = binding['usage']
                check(name + '.exact_helper_binding', binding['requested_policy'] == policy
                      and binding['helper_sha256'] == helper_hash
                      and all(r['model_input_checks']['tool_output_helper_source'] is True for r in joined))
                check(name + '.unsigned_helper_observation', helper['worker_owned_observation'] is True
                      and helper['raw_content_exported'] is helper['proof_authority'] is helper['completion_authority'] is False)
                check(name + '.helper_bounds', 0 <= helper['capture_count'] <= 32 and 0 <= helper['artifact_count'] <= 32
                      and 0 <= helper['store_bytes'] <= 32 * 1024**2 and 0 <= helper['read_count'] <= 100000
                      and 0 <= helper['read_bytes'] <= min(1024**3, 8192 * helper['read_count'])
                      and helper['complete_capture_count'] + helper['incomplete_capture_count'] == helper['capture_count'])
                check(name + '.helper_cleanup', helper['store_cleanup_complete'] is True
                      and helper['artifacts_retained_after_invocation'] is False)
                check(name + '.observed_operations_consistent', helper['helper_operations_observed'] is bool(helper['capture_count'] or helper['read_count']))
                helper_captures += helper['capture_count']
                helper_reads += helper['read_count']
            else:
                check(name + '.legacy_advisory_absent', 'tool_output_policy' not in call)
        check(name + '.exact_input_join', exact and projection['exact_coding_audit_verified'] is True)
        check(name + '.worker_cleanup', report['worker_cleanup_returncode'] == report['remaining_processes'] == 0)
        check(name + '.official_outcome_retained', projection['official_reward'] == trial['reward']['reward'])
        if projection['all_tool_censuses_complete']:
            pairs = [pair for r in calls for pair in r['native_rollout_usage']['interaction_telemetry']['tool_pairs']]
            check(name + '.observed_output_byte_census', all(number(pair['observed_output_bytes']) for pair in pairs)
                  and projection['observed_tool_output_bytes'] == sum(pair['observed_output_bytes'] for pair in pairs))
        else:
            check(name + '.incomplete_output_bytes_unknown', projection['observed_tool_output_bytes'] is None)
        observed.append({'name': name, 'requested_policy': policy, 'state': projection['state'], 'complete_tokens': totals,
                         'official_reward': projection['official_reward'], 'helper_capture_count': helper_captures,
                         'helper_read_count': helper_reads,
                         'helper_adoption_is_worker_observation': True if policy == 'artifact-preview@1' else None})
    check('cross_trial_native_identities_unique', all(len(values) == len(set(values)) for values in cross_ids.values()))
    completed_receipts = sum(row['state'] == 'finished' for row in observed)
    complete = completed_receipts == 4
    if complete:
        for mode in ('legacy', 'artifact-preview@1'):
            selected = [r for r in observed if r['requested_policy'] == mode]
            for key in TOKEN_KEYS:
                expected = sum(r['complete_tokens'][key] for r in selected) / 2 if all(r['complete_tokens'][key] is not None for r in selected) else None
                check(mode + '.mean_' + key, benchmark['arms'][mode]['means'][key] == expected)
            check(mode + '.failures_retained_in_success_count', benchmark['arms'][mode]['successes'] == sum(r['official_reward'] == 1 for r in selected))
        if benchmark['all_trials_comparison_eligible']:
            left = benchmark['arms']['legacy']['means']['total_tokens']
            right = benchmark['arms']['artifact-preview@1']['means']['total_tokens']
            check('aggregate_percent_arithmetic', math.isclose(benchmark['mean_total_token_change_percent'], 100 * (right - left) / left, abs_tol=1e-10))
    sweep_path = ROOT / 'authored-output-size-sweep.json'
    if sweep_path.exists():
        sweep = read(sweep_path)
        check('authored_sweep_source_binding', sweep['source_commit'] == SOURCE_HEAD
              and sweep['helper_sha256'] == helper_hash
              and sweep['script_sha256'] == sha((ROOT / 'authored-output-size-sweep.py').read_bytes()))
        check('authored_sweep_byte_arithmetic', all(
            row['retained_raw_bytes'] == row['authored_stdout_bytes'] + row['authored_stderr_bytes']
            == row['preview_payload_bytes'] + row['omitted_raw_bytes']
            and row['cli_response_minus_raw_bytes'] == row['cli_stdout_json_bytes_including_newline'] - row['retained_raw_bytes']
            and row['json_envelope_bytes_excluding_authored_preview_characters'] + row['preview_payload_bytes']
            == row['cli_stdout_json_bytes_including_newline'] for row in sweep['rows']))
        check('authored_sweep_no_live_token_claim', sweep['token_measurement_performed'] is False
              and sweep['causal_live_token_difference_attribution'] is False and sweep['provider_calls'] == 0)
    resources_path = ROOT / 'resource-observations.json'
    if complete and resources_path.exists():
        resources = read(resources_path)
        check('resource_trial_population', resources['trial_order'] == [row[0] for row in ORDER]
              and [row['trial'] for row in resources['trials']] == resources['trial_order'])
        check('resource_sample_count_arithmetic', resources['aggregate_sampled_resources']['sample_count']
              == sum(row['resources']['sample_count'] for row in resources['trials']))
        check('resource_scope_is_observational', resources['pressure_injection_performed'] is False
              and resources['stress_test_performed'] is False and resources['system_stability_guaranteed'] is False
              and resources['provider_calls_by_collector'] == 0)
        for row in resources['trials']:
            name = row['trial']
            check(name + '.resource_receipt_pin', row['receipt_sha256'] == sha((ROOT / 'trials' / name / 'receipt.json').read_bytes()))
            check(name + '.resource_limits', row['configured_container']['override_cpus'] == 5
                  and row['configured_container']['override_memory_mb'] == 16384
                  and row['configured_container']['cpu_enforcement_policy'] == row['configured_container']['memory_enforcement_policy'] == 'limit')
            native_name = row['native_trial_name']
            if not re.fullmatch(r'tune-mjcf__[A-Za-z0-9]+', native_name):
                raise ValueError('closed native trial identity required')
            remaining = subprocess.check_output(['docker', 'ps', '-a', '--filter',
                'label=com.docker.compose.project=' + native_name.lower() + '__env', '--format', '{{json .Names}}'], timeout=15)
            check(name + '.owned_project_containers_absent_independently', not remaining.strip())
    check('no_established_savings_claim', benchmark['token_savings_established'] is False
          and benchmark['statistically_significant_improvement_established'] is False)
    result = {'schema': 'independent-output-preview-benchmark-review@1', 'source_commit': SOURCE_HEAD,
              'archive_sha256': ARCHIVE, 'campaign_complete': complete, 'completed_receipts': completed_receipts,
              'observed_checks_passed': all(row['passed'] for row in checks), 'check_count': len(checks),
              'checks': checks, 'trials': observed, 'benchmark_sha256': sha((ROOT / 'benchmark.json').read_bytes()),
              'raw_provider_data_exported': False, 'provider_calls': 0,
              'interpretation': 'Observed output bytes are not provider tokens; helper adoption remains unsigned worker observation. All requested failures and nonadoption remain in their arms.'}
    (ROOT / 'independent-review.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('campaign_complete', 'completed_receipts', 'observed_checks_passed', 'check_count')}))


if __name__ == '__main__':
    main()
