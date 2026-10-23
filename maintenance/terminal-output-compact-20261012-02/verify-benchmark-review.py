#!/usr/bin/env python3
"""Independent metadata-only review of the retained compact output experiment."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
SOURCE_HEAD = None
ARCHIVE = None
TOKEN_KEYS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'total_tokens')
ORDER = [('mjcf-legacy-01', 'legacy', 1), ('mjcf-compact-01', 'artifact-preview@2', 1),
         ('mjcf-compact-02', 'artifact-preview@2', 2), ('mjcf-legacy-02', 'legacy', 2)]


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
    complete = native.get('schema') == 'native-codex-cumulative-usage@1' and valid and all(native.get(key) is True for key in
        ('usage_available', 'task_complete_observed', 'cache_included_in_input'))
    return valid, complete


def expected_instruction(binding):
    """Independent fixed policy-v2 text, without importing production validators."""
    python, helper, store = (shlex.quote(binding[key]) for key in
                             ('python_executable', 'helper_script', 'store_path'))
    return (
        'Optional bounded output helper:\n'
        'Keep targeted reads and existing command batches. Use normal tools for small outputs; '
        'do not add commands just to use this helper. For expected verbose, noninteractive output:\n'
        f'{python} {helper} run --store {store} --response-format compact --timeout 120 --preview-bytes 2048 -- PROGRAM ARG...\n'
        'Runs argv once without stdin/TTY; stdout and stderr stay separate. Limits: 8 MiB capture, '
        '32 MiB store, 120 seconds; exceeding limits can terminate the command. Check complete, '
        'exit_code, cleanup_complete and termination_reason. Small outputs use one exact encoding. '
        'Omitted output has head/tail and omitted_bytes; only complete omitted streams include a replay SHA256. '
        'Retrieve necessary ranges, especially missing failure details:\n'
        f'{python} {helper} read --store {store} --response-format compact --sha256 HASH --offset 0 --length 4096\n'
        'Pages contain exact UTF-8 text or base64, never both. Do not rerun commands to recover output; '
        'previews do not establish success. Artifacts expire after this invocation and carry no proof '
        'or completion authority.\n\n'
    ).encode()


def complete_tool_census(native):
    telemetry = native.get('interaction_telemetry', {})
    zeroes = ('omitted_tool_events', 'invalid_tool_identity_events', 'malformed_json_records',
              'invalid_record_shapes', 'omitted_token_observations', 'invalid_token_snapshots',
              'counter_decrease_intervals', 'invalid_counter_intervals')
    if (telemetry.get('schema') != 'native-codex-interaction-telemetry@1'
            or telemetry.get('tool_observations_complete') is not True
            or telemetry.get('token_observations_complete') is not True
            or telemetry.get('task_complete_observed') is not True
            or telemetry.get('record_limit_exceeded') is not False
            or any(type(telemetry.get(key)) is not int or telemetry[key] != 0 for key in zeroes)):
        return False
    pairs = telemetry.get('tool_pairs')
    if type(pairs) is not list or len(pairs) > 128:
        return False
    if not all(number(telemetry.get(key)) for key in ('observed_tool_call_events', 'observed_tool_output_events')):
        return False
    if not all(type(pair) is dict and number(pair.get('input_bytes'))
               and number(pair.get('observed_output_bytes'))
               and pair.get('pairing_status') == 'single_call_and_output_observed'
               and pair.get('call_event_count') == pair.get('output_event_count') == 1
               and pair.get('observation_ordinal') == index
               for index, pair in enumerate(pairs, 1)):
        return False
    return telemetry['observed_tool_call_events'] == telemetry['observed_tool_output_events'] == len(pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--archive-sha256', required=True)
    options = parser.parse_args()
    global SOURCE_HEAD, ARCHIVE
    SOURCE_HEAD, ARCHIVE = options.source_commit, options.archive_sha256
    if not re.fullmatch(r'[0-9a-f]{40}', SOURCE_HEAD) or not re.fullmatch(r'[0-9a-f]{64}', ARCHIVE):
        raise ValueError('independent exact source/archive pins required')
    checks, observed, cross_ids = [], [], {'invocation': [], 'session': []}
    def check(name, value):
        checks.append({'check': name, 'passed': bool(value)})
    if not (ROOT / 'comparison-protocol.json').exists():
        print(json.dumps({'campaign_complete': False, 'completed_receipts': 0,
                          'status': 'pending_frozen_protocol', 'provider_calls': 0}))
        return
    protocol = read(ROOT / 'comparison-protocol.json')
    if not (ROOT / 'benchmark.json').exists():
        print(json.dumps({'campaign_complete': False, 'completed_receipts': 0,
                          'status': 'pending_benchmark_refresh', 'provider_calls': 0}))
        return
    benchmark = read(ROOT / 'benchmark.json')
    if {row.get('name') for row in benchmark.get('trials', [])} != {row[0] for row in ORDER}:
        print(json.dumps({'campaign_complete': False, 'completed_receipts': 0,
                          'status': 'pending_benchmark_refresh', 'provider_calls': 0}))
        return
    check('compact_campaign_schemas', protocol['schema'] == 'terminal-output-compact-comparison-protocol@1'
          and benchmark['schema'] == 'terminal-output-compact-benchmark@1')
    check('frozen_protocol', protocol['source_commit'] == SOURCE_HEAD and protocol['archive_sha256'] == ARCHIVE)
    check('abba_order', [(r['name'], r['tool_output_policy'], r['repeat']) for r in protocol['trials']] == ORDER)
    check('clean_source_pin', subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE_HEAD
          and not subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip())
    by_name = {row['name']: row for row in benchmark['trials']}
    check('all_requested_trials_retained', list(by_name) == [row[0] for row in ORDER])
    check('requested_policy_is_combined_intervention', protocol['requested_axis'] == 'tool_output_policy'
          and protocol['failures_retained_in_requested_arm'] is True
          and protocol['nonadoption_retained_in_requested_arm'] is True
          and protocol['helper_adoption_guaranteed'] is False)
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
        if report is None:
            check(name + '.setup_failure_retained_without_invented_usage',
                  trial.get('exception_type') == 'AgentSetupTimeoutError'
                  and trial.get('agent_context') is None and trial.get('reward') is None
                  and trial.get('durations_seconds', {}).get('agent_execution') is None
                  and trial.get('durations_seconds', {}).get('verifier') is None
                  and projection['native_usage_complete'] is False
                  and projection['comparison_eligible'] is False
                  and projection.get('invocations') == []
                  and all(value is None for value in projection['complete_tokens'].values()))
            observed.append({'name': name, 'requested_policy': policy, 'state': projection['state'],
                             'complete_tokens': dict.fromkeys(TOKEN_KEYS),
                             'official_reward': projection['official_reward'],
                             'helper_capture_count': None, 'helper_read_count': None,
                             'comparison_eligible': False, 'setup_failure': trial.get('exception_type'),
                             'compact_format_adoption_established': False})
            continue
        calls = report['provider_invocations']
        check(name + '.bounded_phase_population', 0 < len(calls) <= 16 and {r['phase'] for r in calls} == {'planning', 'coding'})
        invocations = [r['invocation_id'] for r in calls]
        sessions = [r['native_rollout_usage']['thread_id'] for r in calls]
        unique = len(set(invocations)) == len(invocations) and len(set(sessions)) == len(sessions)
        check(name + '.unique_native_counts', unique)
        cross_ids['invocation'] += invocations
        cross_ids['session'] += sessions
        check(name + '.provider_model_controls', all(r['provider'] == 'codex_cli'
              and r['model'] == protocol['model'] for r in calls))
        planning = [r for r in calls if r['phase'] == 'planning']
        check(name + '.planning_input_binding', all(r['native_prompt_sha256'] == r['model_prompt_sha256']
              == report['planning']['model_request_sha256'] for r in planning))
        check(name + '.planning_policy_absent', all('tool_output_policy' not in r for r in planning))
        native_complete = unique and not report.get('unreceipted_provider_attempt') and all(
            usage(r['native_rollout_usage'])[1] and r['provider'] == 'codex_cli'
            and r['model'] == protocol['model'] for r in calls)
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
        helper_captures = helper_reads = 0 if policy == 'artifact-preview@2' else None
        for call in coding:
            joined = [r for r in audit['matches'] if r['invocation_id'] == call['invocation_id']]
            exact = exact and bool(joined) and all(r['model_input_verified'] is True
                and r['model_prompt_sha256'] == call['model_prompt_sha256']
                and r['model_prompt_bytes'] == call['model_prompt_bytes']
                and r['model_input_checks'] and all(v is True for v in r['model_input_checks'].values()) for r in joined)
            if policy == 'artifact-preview@2':
                binding = call['tool_output_policy']
                helper = binding['usage']
                advisory = expected_instruction(binding)
                check(name + '.exact_compact_advisory', binding['schema'] == 'supervisor-tool-output-policy@1'
                      and binding['instruction_bytes'] == len(advisory) <= 8192
                      and binding['instruction_sha256'] == sha(advisory)
                      and all(binding[key] is False for key in ('native_tool_interception',
                          'helper_adoption_guaranteed', 'token_savings_measured', 'execution_authority',
                          'completion_authority')))
                check(name + '.exact_helper_binding', binding['requested_policy'] == policy
                      and binding['helper_sha256'] == helper_hash
                      and all(r['model_input_checks']['tool_output_helper_source'] is True for r in joined))
                check(name + '.unsigned_helper_observation', helper['worker_owned_observation'] is True
                      and helper['raw_content_exported'] is helper['proof_authority'] is helper['completion_authority'] is False)
                check(name + '.helper_bounds', 0 <= helper['capture_count'] <= 32 and 0 <= helper['artifact_count'] <= 32
                      and 0 <= helper['store_bytes'] <= 32 * 1024**2 and 0 <= helper['read_count'] <= 100000
                      and 0 <= helper['read_bytes'] <= min(1024**3, 8192 * helper['read_count'])
                      and helper['complete_capture_count'] + helper['incomplete_capture_count'] == helper['capture_count'])
                check(name + '.helper_byte_census_bounds', all(number(helper[k]) for k in
                      ('observed_bytes', 'retained_bytes', 'preview_bytes', 'omitted_bytes', 'command_failure_count'))
                      and helper['command_failure_count'] <= helper['capture_count']
                      and helper['observed_bytes'] <= helper['capture_count'] * (8 * 1024**2 + 65536)
                      and helper['preview_bytes'] <= helper['capture_count'] * 8192
                      and helper['retained_bytes'] <= helper['complete_capture_count'] * 8 * 1024**2
                      and helper['retained_bytes'] <= helper['observed_bytes']
                      and helper['preview_bytes'] + helper['omitted_bytes'] <= min(
                          helper['observed_bytes'], helper['capture_count'] * 8 * 1024**2))
                check(name + '.helper_cleanup', helper['store_cleanup_complete'] is True
                      and helper['artifacts_retained_after_invocation'] is False)
                check(name + '.observed_operations_consistent', helper['helper_operations_observed'] is bool(helper['capture_count'] or helper['read_count']))
                helper_captures += helper['capture_count']
                helper_reads += helper['read_count']
            else:
                check(name + '.legacy_advisory_absent', 'tool_output_policy' not in call)
        check(name + '.exact_input_join', exact and projection['exact_coding_audit_verified'] is True)
        check(name + '.advisory_selection_verified', projection['advisory_verified'] is True
              and report.get('tool_output_policy', 'legacy') == policy)
        check(name + '.worker_cleanup', report['worker_cleanup_returncode'] == report['remaining_processes'] == 0)
        check(name + '.official_outcome_retained', projection['official_reward'] == trial['reward']['reward'])
        check(name + '.observed_output_census_completeness', projection['all_tool_censuses_complete'] is
              all(complete_tool_census(r['native_rollout_usage']) for r in calls))
        if projection['all_tool_censuses_complete']:
            pairs = [pair for r in calls for pair in r['native_rollout_usage']['interaction_telemetry']['tool_pairs']]
            check(name + '.observed_output_byte_census', all(number(pair['observed_output_bytes']) for pair in pairs)
                  and projection['observed_tool_output_bytes'] == sum(pair['observed_output_bytes'] for pair in pairs))
        else:
            check(name + '.incomplete_output_bytes_unknown', projection['observed_tool_output_bytes'] is None)
        check(name + '.helper_aggregate_projection', projection['helper_capture_count'] == helper_captures
              and projection['helper_read_count'] == helper_reads)
        observed.append({'name': name, 'requested_policy': policy, 'state': projection['state'], 'complete_tokens': totals,
                         'official_reward': projection['official_reward'], 'helper_capture_count': helper_captures,
                         'helper_read_count': helper_reads,
                         'comparison_eligible': projection['comparison_eligible'],
                         'helper_adoption_is_worker_observation': True if policy == 'artifact-preview@2' else None,
                         'compact_format_adoption_established': False if policy == 'artifact-preview@2' else None})
    check('cross_trial_native_identities_unique', all(len(values) == len(set(values)) for values in cross_ids.values()))
    completed_receipts = sum(row['state'] == 'finished' for row in observed)
    complete = completed_receipts == 4
    if complete:
        for mode in ('legacy', 'artifact-preview@2'):
            selected = [r for r in observed if r['requested_policy'] == mode]
            for key in TOKEN_KEYS:
                expected = sum(r['complete_tokens'][key] for r in selected) / 2 if all(r['complete_tokens'][key] is not None for r in selected) else None
                check(mode + '.mean_' + key, benchmark['arms'][mode]['means'][key] == expected)
            check(mode + '.failures_retained_in_success_count', benchmark['arms'][mode]['successes'] == sum(r['official_reward'] == 1 for r in selected))
        if benchmark['all_trials_comparison_eligible']:
            left = benchmark['arms']['legacy']['means']['total_tokens']
            right = benchmark['arms']['artifact-preview@2']['means']['total_tokens']
            check('aggregate_percent_arithmetic', math.isclose(benchmark['mean_total_token_change_percent'], 100 * (right - left) / left, abs_tol=1e-10))
    wire_path = ROOT / 'authored-wire-comparison.json'
    if wire_path.exists():
        wire = read(wire_path)
        check('authored_wire_source_binding', wire['source_commit'] == SOURCE_HEAD
              and wire['helper_sha256'] == helper_hash and wire['helper_matches_source_commit'] is True
              and wire['script_sha256'] == sha((ROOT / 'authored-wire-comparison.py').read_bytes()))
        check('authored_wire_byte_arithmetic', all(
            row['compact_minus_legacy_cli_json_bytes'] == row['compact']['cli_json_bytes_including_newline']
                - row['legacy']['cli_json_bytes_including_newline']
            and all(side['retained_bytes'] == row['authored_stdout_bytes'] + row['authored_stderr_bytes']
                    == side['preview_payload_bytes'] + side['omitted_bytes']
                    and side['cli_json_minus_raw_bytes'] == side['cli_json_bytes_including_newline'] - side['retained_bytes']
                    and side['cli_matches_pure_projection'] is True
                    and side['formatting_preserved_internal_result_and_store_bytes'] is True
                    and side['exact_retained_data_verified'] is True
                    and side['process_cleanup_complete'] is True and side['store_removed'] is True
                    for side in (row['legacy'], row['compact'])) for row in wire['rows']))
        check('authored_wire_no_live_token_claim', wire['token_measurement_performed'] is False
              and wire['causal_live_token_difference_attribution'] is False and wire['provider_calls'] == 0)
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
    result = {'schema': 'independent-output-compact-benchmark-review@1', 'source_commit': SOURCE_HEAD,
              'archive_sha256': ARCHIVE, 'campaign_complete': complete, 'completed_receipts': completed_receipts,
              'all_trials_comparison_eligible': benchmark['all_trials_comparison_eligible'],
              'observed_checks_passed': all(row['passed'] for row in checks), 'check_count': len(checks),
              'checks': checks, 'trials': observed, 'benchmark_sha256': sha((ROOT / 'benchmark.json').read_bytes()),
              'verifier_sha256': sha(Path(__file__).read_bytes()),
              'raw_provider_data_exported': False, 'provider_calls': 0,
              'compact_format_adoption_established': False,
              'comparison_scope': 'Intent-to-treat selected policy, combining compact-format guidance and command-choice advice.',
              'interpretation': 'Observed output bytes are not provider tokens; helper adoption remains unsigned worker observation. Version-one helper usage receipts do not record CLI response_format, so helper operations cannot establish actual compact-wire adoption. All requested failures and nonadoption remain in their arms.'}
    (ROOT / 'independent-review.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('campaign_complete', 'completed_receipts', 'observed_checks_passed', 'check_count')}))


if __name__ == '__main__':
    main()
