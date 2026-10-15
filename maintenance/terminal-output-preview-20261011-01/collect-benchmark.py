#!/usr/bin/env python3
"""Collect frozen ABBA receipts, retaining failures and nonadoption in requested arms."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import runpy
import re
import statistics
import subprocess
import sys

import telemetry_projection as telemetry

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
PREPARE = runpy.run_path(str(ROOT / 'prepare-campaign.py'))
MODES = PREPARE['MODES']
TOKENS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'total_tokens')
HELPER_COUNTS = ('capture_count', 'complete_capture_count', 'incomplete_capture_count',
    'command_failure_count', 'observed_bytes', 'retained_bytes', 'preview_bytes', 'omitted_bytes',
    'artifact_count', 'store_bytes', 'read_count', 'read_bytes')


def mapping(value):
    return value if type(value) is dict else {}


def read_json(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 16 * 1024**2:
        raise ValueError('bounded regular JSON required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def bounded_float(value):
        number = float(value)
        if not math.isfinite(number): raise ValueError('nonfinite JSON number')
        return number
    return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_float=bounded_float,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def count(value):
    return telemetry.count(value)


def total(rows, key):
    return sum(row[key] for row in rows) if rows and all(count(row.get(key)) is not None for row in rows) else None


def exact_audit(report, coding):
    audit = mapping(report.get('context_input_audit'))
    rows, matches = audit.get('invocations'), audit.get('matches')
    if (type(rows) is not list or type(matches) is not list or len(rows) > 16 or len(matches) > 512
            or audit.get('status') != 'verified_all_observed_model_inputs'
            or audit.get('all_observed_coding_inputs_verified') is not True or audit.get('read_errors') != []
            or type(audit.get('coding_receipts_seen')) is not int or audit['coding_receipts_seen'] != len(coding)
            or type(audit.get('usable_coding_receipts')) is not int or audit['usable_coding_receipts'] != len(coding)):
        return False
    ids = [row.get('invocation_id') for row in coding]
    audit_ids = [row.get('invocation_id') for row in rows if type(row) is dict]
    if (not coding or any(type(value) is not str for value in (*ids, *audit_ids))
            or len(audit_ids) != len(ids) or len(set(audit_ids)) != len(ids) or set(audit_ids) != set(ids)):
        return False
    for coding_row in coding:
        identity = coding_row['invocation_id']
        selected = [row for row in rows if row.get('invocation_id') == identity]
        joined = [row for row in matches if type(row) is dict and row.get('invocation_id') == identity]
        if (len(selected) != 1 or selected[0].get('model_input_verified') is not True
                or selected[0].get('status') != 'verified_exact_model_input' or not joined):
            return False
        for row in joined:
            checks = mapping(row.get('model_input_checks'))
            if (row.get('model_input_verified') is not True or not checks or not all(v is True for v in checks.values())
                    or telemetry.digest(row.get('model_prompt_sha256')) is None
                    or row['model_prompt_sha256'] != coding_row.get('model_prompt_sha256')
                    or type(row.get('model_prompt_bytes')) is not int
                    or row['model_prompt_bytes'] != coding_row.get('model_prompt_bytes')):
                return False
    return True


def project_report(report, requested, dispatch_validator):
    """Closed content-free projection; no commands, paths or output text exported."""
    report = mapping(report)
    problems, rows, identities, sessions = [], [], [], []
    population = report.get('provider_invocations')
    if type(population) is not list or not 0 < len(population) <= 16 or any(type(row) is not dict for row in population):
        problems.append('provider_invocation_population_invalid')
        population = []
    coding = [row for row in population if row.get('phase') == 'coding']
    for index, row in enumerate(population, 1):
        native = mapping(row.get('native_rollout_usage'))
        values = telemetry.usage(native.get('usage'))
        identity, session = row.get('invocation_id'), native.get('thread_id')
        identities.append(identity if type(identity) is str and 0 < len(identity) <= 256 else None)
        sessions.append(session if type(session) is str and 0 < len(session) <= 256 else None)
        complete = (native.get('schema') == 'native-codex-cumulative-usage@1'
            and native.get('usage_available') is True and native.get('task_complete_observed') is True
            and native.get('cache_included_in_input') is True and values is not None
            and 'cached_input_tokens' in values and row.get('provider') == 'codex_cli'
            and row.get('model') == 'gpt-6.1-sol')
        projected, errors = telemetry.project_telemetry(native.get('interaction_telemetry'))
        tool_pairs = projected['tool_pairs']
        stats = {key: count(mapping(projected['counts']).get(key)) for key in
                 ('observed_tool_call_events', 'observed_tool_output_events', 'observed_token_checkpoints')}
        stats['census_complete'] = projected['census_complete'] and not errors
        stats['retained_tool_input_byte_lower_bound'] = (sum(pair['input_bytes'] for pair in tool_pairs
            if pair['input_bytes'] is not None) if not errors else None)
        stats['retained_tool_output_byte_lower_bound'] = (sum(pair['observed_output_bytes'] for pair in tool_pairs
            if pair['observed_output_bytes'] is not None) if not errors else None)
        stats['observed_tool_input_bytes'] = stats['retained_tool_input_byte_lower_bound'] if stats['census_complete'] else None
        stats['observed_tool_output_bytes'] = stats['retained_tool_output_byte_lower_bound'] if stats['census_complete'] else None
        if not stats['census_complete']:
            stats['observed_tool_call_events'] = None
            stats['observed_tool_output_events'] = None
        if row.get('phase') == 'planning':
            planning = mapping(report.get('planning'))
            if (telemetry.digest(planning.get('model_request_sha256')) is None
                    or planning['model_request_sha256'] != row.get('model_prompt_sha256')
                    or row.get('native_prompt_sha256') != row.get('model_prompt_sha256')):
                problems.append('planning_input_binding_unverified')
        binding = mapping(row.get('tool_output_policy'))
        helper = mapping(binding.get('usage'))
        helper_valid = (helper.get('schema') == 'tool-output-artifact-usage@1'
            and all(count(helper.get(key)) is not None for key in HELPER_COUNTS)
            and helper.get('raw_content_exported') is False and helper.get('worker_owned_observation') is True
            and helper.get('proof_authority') is False and helper.get('completion_authority') is False
            and helper.get('capture_count') == helper.get('complete_capture_count', -1) + helper.get('incomplete_capture_count', -1))
        if helper_valid:
            captures = helper['capture_count']
            helper_valid = (captures <= 32 and helper['artifact_count'] <= 32
                and helper['command_failure_count'] <= captures
                and helper['store_bytes'] <= 32 * 1024**2
                and helper['read_count'] <= 100_000
                and helper['read_bytes'] <= min(1024**3, helper['read_count'] * 8192)
                and helper['observed_bytes'] <= captures * (8 * 1024**2 + 65536)
                and helper['retained_bytes'] <= helper['complete_capture_count'] * 8 * 1024**2
                and helper['preview_bytes'] <= captures * 8192
                and helper['preview_bytes'] + helper['omitted_bytes'] <= min(helper['observed_bytes'], captures * 8 * 1024**2)
                and helper['retained_bytes'] <= helper['observed_bytes']
                and helper.get('helper_operations_observed') is bool(captures or helper['read_count']))
        cleanup = helper.get('store_cleanup_complete') is True and helper.get('artifacts_retained_after_invocation') is False
        rows.append(dict(invocation_ordinal=index, phase=telemetry.choice(row.get('phase'), {'planning', 'coding'}),
            invocation_id_sha256=telemetry.sha(identity.encode()) if type(identity) is str else None,
            native_session_sha256=telemetry.sha(session.encode()) if type(session) is str else None,
            native_usage=values, native_usage_complete=complete,
            tool_observations=stats, telemetry_issues=errors,
            helper_usage={key: count(helper.get(key)) for key in HELPER_COUNTS} if binding else None,
            helper_usage_valid=helper_valid if binding else None,
            helper_capture_observed=(helper['capture_count'] > 0) if helper_valid else None,
            helper_store_cleanup_complete=cleanup if binding else None,
            helper_counts_worker_owned=True if binding else None))
    if {row['phase'] for row in rows} != {'planning', 'coding'}:
        problems.append('planning_and_coding_population_required')
    unique = bool(population) and None not in identities and None not in sessions and len(set(identities)) == len(identities) and len(set(sessions)) == len(sessions)
    usage_complete = unique and not report.get('unreceipted_provider_attempt') and all(row['native_usage_complete'] for row in rows)
    if not unique: problems.append('invocation_or_session_identity_missing_or_reused')
    if report.get('unreceipted_provider_attempt'): problems.append('unreceipted_provider_attempt')
    audit = unique and exact_audit(report, coding)
    if not audit: problems.append('exact_coding_input_audit_unverified')
    if requested == 'artifact-preview@1':
        dispatch = dispatch_validator(report, requested)
        advisory = dispatch.get('effective_advisory_observed') is True
        helper_complete = bool(coding) and all(row['helper_usage_valid'] is True and row['helper_store_cleanup_complete'] is True
            for row in rows if row['phase'] == 'coding')
    else:
        advisory = report.get('tool_output_policy', 'legacy') == 'legacy' and all('tool_output_policy' not in row for row in population)
        helper_complete = True
    if not advisory: problems.append('requested_advisory_not_verified')
    if not helper_complete: problems.append('helper_usage_or_cleanup_unverified')
    worker_cleanup = report.get('worker_cleanup_returncode') == 0 and report.get('remaining_processes') == 0
    if not worker_cleanup: problems.append('worker_cleanup_incomplete')
    tokens = {key: sum(row['native_usage'][key] for row in rows) if usage_complete else None for key in TOKENS}
    observed = {key: sum(row['native_usage'][key] for row in rows if row['native_usage'] is not None and key in row['native_usage'])
        if unique and any(row['native_usage'] is not None and key in row['native_usage'] for row in rows) else None for key in TOKENS}
    coding_rows = [row for row in rows if row['phase'] == 'coding']
    helper_totals = {key: sum(row['helper_usage'][key] for row in coding_rows)
        if coding_rows and all(row['helper_usage_valid'] is True for row in coding_rows) else None
        for key in HELPER_COUNTS}
    tool_totals = {key: total([row['tool_observations'] for row in rows], key)
        for key in ('observed_tool_call_events', 'observed_tool_input_bytes', 'observed_tool_output_bytes')}
    return dict(invocations=rows, native_usage_complete=usage_complete, complete_tokens=tokens,
        **tool_totals, helper_capture_count=helper_totals['capture_count'], helper_read_count=helper_totals['read_count'],
        helper_read_bytes=helper_totals['read_bytes'], helper_usage_totals=helper_totals,
        observed_token_subtotal=observed, uncached_input_tokens=tokens['input_tokens']-tokens['cached_input_tokens'] if usage_complete else None,
        exact_coding_audit_verified=audit, advisory_verified=advisory, helper_usage_and_cleanup_verified=helper_complete,
        worker_cleanup_complete=worker_cleanup, all_tool_censuses_complete=bool(rows) and all(row['tool_observations']['census_complete'] for row in rows),
        problems=problems, task_completed=report.get('task_completed') is True)


def collect_trial(root, selected, protocol, dispatch_validator):
    folder = root / 'trials' / selected['name']
    result = dict(name=selected['name'], requested_policy=selected['tool_output_policy'], repeat=selected['repeat'],
        state='pending', comparison_eligible=False, official_reward=None, durations_seconds={},
        native_usage_complete=False, complete_tokens=dict.fromkeys(TOKENS), problems=[])
    if not (folder / 'receipt.json').is_file():
        result['state'] = 'started_or_partial' if (folder / 'invocation.json').exists() else 'pending'
        return result
    receipt, prepared, config = (read_json(folder / name) for name in ('receipt.json', 'preparation.json', 'config.json'))
    frozen = mapping(protocol.get('preparations')).get(selected['task'], {})
    kwargs = mapping(config['agents'][0].get('kwargs'))
    controls = dict(configuration_sha256=telemetry.sha((folder/'config.json').read_bytes()) == prepared.get('config_sha256') == selected.get('config_sha256'),
        normalized_configuration=PREPARE['normalize_config'](config) == frozen.get('normalized_configuration'),
        archive=prepared.get('archive_sha256') == protocol.get('archive_sha256') == frozen.get('archive_sha256'),
        task_pins=bool(frozen.get('task_input_sha256')) and prepared.get('task_input_sha256') == frozen['task_input_sha256'],
        host_pins=bool(frozen.get('host_source_sha256')) and prepared.get('host_source_sha256') == frozen['host_source_sha256'],
        requested_policy=prepared.get('tool_output_policy', 'legacy') == kwargs.get('tool_output_policy', 'legacy') == selected['tool_output_policy'],
        fixed_context=prepared.get('semantic_context_profile') == kwargs.get('semantic_context_profile') == 'indexed-default@1'
            and prepared.get('semantic_metadata_view', 'legacy') == kwargs.get('semantic_metadata_view', 'legacy') == 'legacy',
        original_inputs_unchanged=receipt.get('original_task_inputs_unchanged') is True,
        provider_controls=all(prepared.get(key) == protocol.get(key) == expected for key, expected in
            [('model','gpt-6.1-sol'), ('reasoning_effort','high'), ('cli_version','0.160.0')]),
        resource_profile=prepared.get('resource_profile') == protocol.get('resource_profile') == 'source384-5cpu-16gib-extended@1')
    trials = receipt.get('trials')
    if type(trials) is not list or len(trials) != 1 or type(trials[0]) is not dict:
        result.update(state='unverified', problems=['one_retained_trial_required'], controls=controls)
        return result
    trial = trials[0]
    result.update(project_report(trial.get('supervisor'), selected['tool_output_policy'], dispatch_validator))
    result['state'] = 'finished' if receipt.get('native_job_result_present') is True else 'started_or_partial'
    reward = mapping(trial.get('reward')).get('reward')
    result['official_reward'] = reward if type(reward) in (int,float) and 0 <= reward <= 1 else None
    result['official_success'] = result['official_reward'] == 1.0
    result['durations_seconds'] = {key: value for key, value in mapping(trial.get('durations_seconds')).items()
        if key in {'environment_setup','agent_setup','agent_execution','verifier'} and type(value) in (int,float) and value >= 0}
    result['controls'] = controls
    result['problems'] += [key for key, value in controls.items() if not value]
    # Harbor's native task name includes its dataset namespace; the supervisor
    # envelope and frozen protocol retain the short task name. Check both exact
    # identities instead of comparing the differently scoped fields directly.
    if (receipt.get('task') != selected['task'] or prepared.get('task') != selected['task']
            or trial.get('exact_trial_task_matches') is not True
            or trial.get('task') != 'terminal-bench/' + selected['task']):
        result['problems'].append('trial_task_mismatch')
    if result['official_reward'] is None: result['problems'].append('official_reward_unknown')
    result['comparison_eligible'] = (result['state'] == 'finished' and result['native_usage_complete'] and not result['problems'])
    result['receipt_sha256'] = telemetry.sha((folder/'receipt.json').read_bytes())
    return result


def summarize(rows):
    arms = {}
    for mode in MODES:
        selected = [row for row in rows if row['requested_policy'] == mode]
        complete = len(selected) == 2 and all(row['state'] == 'finished' and row['native_usage_complete'] for row in selected)
        means = {key: statistics.mean(row['complete_tokens'][key] for row in selected) if complete else None for key in TOKENS}
        metric_names = ('uncached_input_tokens', 'observed_tool_call_events', 'observed_tool_input_bytes',
                        'observed_tool_output_bytes', 'helper_capture_count', 'helper_read_count', 'helper_read_bytes')
        metrics = {key: statistics.mean(row[key] for row in selected)
            if selected and all(count(row.get(key)) is not None for row in selected) else None for key in metric_names}
        durations = {key: statistics.mean(row['durations_seconds'][key] for row in selected)
            if selected and all(type(mapping(row.get('durations_seconds')).get(key)) in (int,float) for row in selected) else None
            for key in ('environment_setup','agent_setup','agent_execution','verifier')}
        arms[mode] = dict(trials=len(selected), complete_usage=complete, means=means,
            mean_metrics=metrics, mean_durations_seconds=durations,
            successes=sum(row.get('official_success') is True for row in selected),
            helper_capture_trials=sum(any(call.get('helper_capture_observed') is True for call in row.get('invocations', [])) for row in selected))
    qualified = len(rows) == 4 and all(row.get('comparison_eligible') is True for row in rows)
    pairs = []
    for repeat in (1,2):
        selected = {row['requested_policy']: row for row in rows if row['repeat'] == repeat}
        left, right = selected.get(MODES[0],{}), selected.get(MODES[1],{})
        valid = left.get('comparison_eligible') is True and right.get('comparison_eligible') is True
        old, new = mapping(left.get('complete_tokens')).get('total_tokens'), mapping(right.get('complete_tokens')).get('total_tokens')
        pairs.append(dict(repeat=repeat, qualified=valid,
            total_token_change_percent=100*(new-old)/old if valid and old else None))
    old, new = arms[MODES[0]]['means']['total_tokens'], arms[MODES[1]]['means']['total_tokens']
    return dict(arms=arms, pairs=pairs, all_trials_comparison_eligible=qualified,
        mean_total_token_change_percent=100*(new-old)/old if qualified and old else None,
        token_savings_established=False, statistically_significant_improvement_established=False)


def collect(root, dispatch_validator):
    path = root/'comparison-protocol.json'
    if not path.exists():
        return dict(schema='terminal-output-preview-benchmark@1', status='pending', trials=[],
            reason='campaign_not_prepared', provider_calls_by_collector=0)
    protocol = read_json(path)
    expected = PREPARE['planned_trials']()
    selected = protocol.get('trials')
    if (protocol.get('schema') != 'terminal-output-preview-comparison-protocol@1' or type(selected) is not list
            or any(type(row) is not dict for row in selected)
            or [{key: row.get(key) for key in reference} for row,reference in zip(selected,expected)] != expected
            or len(selected) != 4 or protocol.get('pairs_match_except') != PREPARE['AXES']):
        raise ValueError('closed ABBA campaign protocol required')
    if not re.fullmatch('[0-9a-f]{40}', str(protocol.get('source_commit', ''))) or not re.fullmatch('[0-9a-f]{64}', str(protocol.get('archive_sha256', ''))):
        raise ValueError('complete source and archive pins required')
    rows = []
    for item in selected:
        try:
            rows.append(collect_trial(root, item, protocol, dispatch_validator))
        except (ValueError, OSError, KeyError, TypeError, IndexError, RecursionError):
            rows.append(dict(name=item['name'], requested_policy=item['tool_output_policy'], repeat=item['repeat'],
                state='unverified', comparison_eligible=False, official_reward=None, durations_seconds={},
                native_usage_complete=False, complete_tokens=dict.fromkeys(TOKENS),
                problems=['retained_trial_artifact_invalid_or_unreadable']))
    identities = [call[key] for row in rows for call in row.get('invocations', [])
        for key in ('native_session_sha256', 'invocation_id_sha256') if call.get(key) is not None]
    unique = len(identities) == len(set(identities))
    if not unique:
        for row in rows:
            row['comparison_eligible'] = False
            row['problems'].append('cross_trial_invocation_or_session_reuse')
    summary = summarize(rows)
    return dict(schema='terminal-output-preview-benchmark@1', status='complete' if all(row['state']=='finished' for row in rows) else 'pending',
        source_commit=protocol.get('source_commit'), archive_sha256=protocol.get('archive_sha256'),
        trials=rows, **summary, cross_trial_identities_unique=unique,
        provider_calls_by_collector=0, raw_tool_data_exported=False,
        interpretation=['All failures and nonadoption remain in their requested arm; unavailable usage stays unknown.',
            'Cached input is included within input tokens. Provider totals include capture and retrieval overhead.',
            'Helper counts are worker-owned observations and do not prove that all commands used the helper.',
            'Two repeats on one task are noisy observations, not causal or statistical evidence of token savings.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();root=args.root.resolve()
    sys.path.insert(0,str(SOURCE))
    from benchmarks.agent_supervisor.container_coding.terminal_tool_output_policy import tool_output_dispatch_observation
    result=collect(root,tool_output_dispatch_observation)
    if result.get('source_commit'):
        head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
        result['collector_source_pin_matches']=head==result['source_commit']
        if not result['collector_source_pin_matches']:
            result['all_trials_comparison_eligible']=False
            result['mean_total_token_change_percent']=None
            result['status']='unverified'
    result['collector_sha256']=telemetry.sha(Path(__file__).read_bytes())
    (root/'benchmark.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    with (root/'benchmark.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['name','requested_policy','repeat','state','official_reward',*TOKENS,'uncached_input_tokens','observed_tool_call_events','observed_tool_output_bytes',
            'helper_capture_count','helper_read_count','helper_read_bytes','comparison_eligible'])
        writer.writeheader()
        for row in result['trials']:
            writer.writerow({key: row.get(key,mapping(row.get('complete_tokens')).get(key)) for key in writer.fieldnames})
    print(json.dumps({'status':result['status'],'trials':len(result['trials']),'comparison_eligible':result.get('all_trials_comparison_eligible',False),'provider_calls':0}))


if __name__=='__main__':main()
