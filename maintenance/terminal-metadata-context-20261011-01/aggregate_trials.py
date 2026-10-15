#!/usr/bin/env python3
"""Read retained metadata trials; no provider calls, source imports or task execution."""
from __future__ import annotations
import argparse
import copy
import json
import re
from pathlib import Path

import accounting_snapshot as native
from metadata_dispatch_snapshot import _metadata_dispatch_observation

TOKENS = native.TOKENS
PROFILES = ('legacy', 'common-bindings@1')
CONTEXT_PROFILE = 'indexed-default@1'
REMOVED_AXES = ('jobs_dir', 'job_name', 'agents[0].kwargs.semantic_metadata_view')
CANONICALIZED_AXES = ('retry.exclude_exceptions (order and duplicate entries are immaterial)',)
read_json, mapping, count = native.read_json, native.mapping, native.count
digest, totals, usage = native.digest, native.totals, native.usage


def normalize_config(config):
    """Keep context limits, task, resources and every non-metadata option fixed."""
    value = copy.deepcopy(config)
    value.pop('jobs_dir', None)
    value.pop('job_name', None)
    agents = value.get('agents', [])
    if len(agents) == 1 and type(agents[0]) is dict:
        agents[0].get('kwargs', {}).pop('semantic_metadata_view', None)
    excluded = value.get('retry', {}).get('exclude_exceptions')
    if type(excluded) is list:
        value['retry']['exclude_exceptions'] = sorted(set(excluded))
    return value


def requested_mode(value):
    return 'legacy' if value is None else value


def metadata_observation(report, requested):
    """Correlate receipt selections with actual coding input; retain valid fallback."""
    report = mapping(report)
    if requested != 'legacy':
        value = _metadata_dispatch_observation(report, requested)
        value['report_requested_mode'] = mapping(report.get('semantic_metadata_view')).get('requested_mode')
        value['coding_invocations_observed'] = value['coding_receipts_seen']
        if value['status'] == 'unverified':
            value['effective_treatment_observed'] = None
        raw = report.get('provider_invocations')
        population = raw if type(raw) is list else []
        for row in value['invocations']:
            receipts = [item.get('semantic_metadata_view') for item in population
                if type(item) is dict and item.get('invocation_id') == row['invocation_id'] and item.get('phase') == 'coding']
            row['selection_receipt'] = receipts[0] if len(receipts) == 1 else None
        return value
    # Legacy has no selector receipt. Correlate the ordinary exact-input audit
    # against every coding invocation instead of interpreting absence as proof.
    declaration = report.get('semantic_metadata_view')
    declared = ('legacy' if declaration is None else mapping(declaration).get('requested_mode'))
    raw = report.get('provider_invocations')
    population = raw if type(raw) is list and len(raw) <= 4096 else []
    coding = [row for row in population if type(row) is dict and row.get('phase') == 'coding']
    audit = mapping(report.get('context_input_audit'))
    audit_rows, matches = audit.get('invocations'), audit.get('matches')
    audit_rows = audit_rows if type(audit_rows) is list and len(audit_rows) <= 16 else []
    matches = matches if type(matches) is list and len(matches) <= 512 else []
    ids = [row.get('invocation_id') for row in coding]
    audit_ids = [row.get('invocation_id') for row in audit_rows if type(row) is dict]
    valid_id = lambda value: type(value) is str and 0 < len(value) <= 4096
    distinct = all(valid_id(value) for value in ids) and len(set(ids)) == len(ids)
    correlated = (bool(coding) and distinct and len(audit_rows) == len(coding) == len(audit_ids)
        and all(valid_id(value) for value in audit_ids) and len(set(audit_ids)) == len(audit_ids)
        and set(audit_ids) == set(ids) and audit.get('status') == 'verified_all_observed_model_inputs'
        and audit.get('all_observed_coding_inputs_verified') is True
        and type(audit.get('coding_receipts_seen')) is int and audit['coding_receipts_seen'] == len(coding)
        and type(audit.get('usable_coding_receipts')) is int and audit['usable_coding_receipts'] == len(coding)
        and audit.get('read_errors') == [])
    problems = []
    if not coding: problems.append('no_observed_coding_receipts')
    if declared != requested: problems.append('requested_mode_report_mismatch')
    if not distinct: problems.append('coding_invocation_identities_missing_or_duplicate')
    if type(raw) is not list or any(type(row) is not dict for row in population): problems.append('malformed_provider_invocation_population')
    if report.get('unreceipted_provider_attempt'): problems.append('unreceipted_provider_attempt')
    rows = []
    for row in coding:
        identity = row.get('invocation_id')
        per_audit = [item for item in audit_rows if type(item) is dict and item.get('invocation_id') == identity]
        per_matches = [item for item in matches if type(item) is dict and item.get('invocation_id') == identity]
        prompt_hash, prompt_bytes = row.get('model_prompt_sha256'), row.get('model_prompt_bytes')
        valid_prompt = (type(prompt_hash) is str and re.fullmatch('[a-f0-9]{64}', prompt_hash) is not None
            and type(prompt_bytes) is int and 0 < prompt_bytes <= 2_000_000)
        def verified_match(item):
            checks = item.get('model_input_checks')
            return (item.get('model_input_verified') is True and item.get('model_prompt_sha256') == prompt_hash
                and type(item.get('model_prompt_bytes')) is int and item['model_prompt_bytes'] == prompt_bytes
                and type(checks) is dict and bool(checks) and all(value is True for value in checks.values()))
        bound = row.get('semantic_metadata_view') is None
        verified = (bound and valid_prompt and correlated and len(per_audit) == 1
            and per_audit[0].get('status') == 'verified_exact_model_input' and per_audit[0].get('model_input_verified') is True
            and bool(per_matches) and all(verified_match(item) for item in per_matches))
        rows.append({'invocation_id': identity if valid_id(identity) else None, 'selected_mode': 'legacy' if bound else None,
            'fallback_reason': None, 'selection_receipt_matches_model_input': bound,
            'retained_exact_input_audit_verified': bool(verified), 'selection_receipt': row.get('semantic_metadata_view')})
    bound = bool(rows) and not problems and all(row['selection_receipt_matches_model_input'] for row in rows)
    verified = bound and all(row['retained_exact_input_audit_verified'] for row in rows)
    return {'schema': 'terminal-legacy-metadata-dispatch-observation@1', 'requested_mode': requested,
        'report_requested_mode': declared, 'requested_mode_matches_report': declared == requested,
        'coding_receipts_seen': len(rows), 'coding_invocations_observed': len(rows), 'invocations': rows,
        'selected_modes': ['legacy'] if bound else [], 'fallback_reasons': [],
        'all_selection_receipts_bound_to_model_inputs': bound,
        'all_coding_inputs_verified_by_retained_audit': bool(verified),
        'effective_treatment_observed': False if verified else None,
        'status': 'verified_baseline' if verified else 'unverified', 'problems': problems,
        'source_audit_rerun': False, 'provider_usage_modified': False, 'token_savings_established': False}


def attempt_row(name, raw, report, *, native_present, source, selected, collector_observation=None):
    row = native.attempt_row(name, raw, report, native_present=native_present, source=source)
    row['semantic_metadata_dispatch'] = metadata_observation(report, selected['semantic_metadata_view'])
    row['collector_semantic_metadata_dispatch'] = collector_observation
    return row


def collect_trial(root, selected, protocol):
    errors = []
    folder = root / 'trials' / selected['name']
    prepared = mapping(read_json(folder / 'preparation.json', errors))
    config = mapping(read_json(folder / 'config.json', errors))
    receipt = mapping(read_json(folder / 'receipt.json', errors))
    frozen = mapping(protocol.get('preparations', {}).get(selected['task']))
    config_hash = digest((folder / 'config.json').read_bytes()) if config else None
    agents = config.get('agents')
    kwargs = mapping(agents[0].get('kwargs')) if type(agents) is list and len(agents) == 1 and type(agents[0]) is dict else {}
    controls = {
        'configuration_file_matches_preparation': bool(config) and config_hash == prepared.get('config_sha256'),
        'normalized_configuration_matches_frozen_protocol': bool(config) and normalize_config(config) == frozen.get('normalized_configuration'),
        'archive_matches_protocol': bool(prepared) and prepared.get('archive_sha256') == frozen.get('archive_sha256'),
        'task_input_pins_match_protocol': bool(prepared) and prepared.get('task_input_sha256') == frozen.get('task_input_sha256'),
        'host_adapter_pins_match_protocol': bool(prepared) and prepared.get('host_source_sha256') == frozen.get('host_source_sha256'),
        'selected_metadata_view_matches_preparation': bool(prepared) and requested_mode(prepared.get('semantic_metadata_view')) == selected['semantic_metadata_view'],
        'selected_metadata_view_matches_configuration': bool(kwargs) and requested_mode(kwargs.get('semantic_metadata_view')) == selected['semantic_metadata_view'],
        'fixed_context_profile_matches_preparation': prepared.get('semantic_context_profile') == selected['semantic_context_profile'] == CONTEXT_PROFILE,
        'fixed_context_profile_matches_configuration': kwargs.get('semantic_context_profile') == selected['semantic_context_profile'] == CONTEXT_PROFILE,
        'source_commit': protocol.get('source_commit'), 'archive_sha256': prepared.get('archive_sha256'),
        'model': prepared.get('model'), 'reasoning_effort': prepared.get('reasoning_effort'),
        'cli_version': prepared.get('cli_version'), 'resource_profile': prepared.get('resource_profile'),
        'original_task_inputs_unchanged_receipt': receipt.get('original_task_inputs_unchanged'),
        'complete_single_trial_receipt': receipt.get('complete_single_trial_receipt'),
        'note': 'Retained pins/configuration only; task solutions, verifiers and mutable source are not reread.',
    }
    attempts, seen = [], set()
    job_name = config.get('job_name')
    if type(job_name) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]+', job_name) or job_name in {'.', '..'}:
        job_name = 'unconfigured'
        errors.append({'error_type': 'invalid_job_name'})
    job = folder / 'jobs' / job_name
    retained = {row.get('trial'): row for row in receipt.get('trials', []) if type(row) is dict}
    if job.is_dir() and not job.is_symlink():
        for path in sorted(job.iterdir()):
            if not path.is_dir() or path.is_symlink():
                continue
            raw = read_json(path / 'result.json', errors)
            report = read_json(path / 'agent/supervisor-result.json', errors)
            if raw is not None or report is not None:
                attempts.append(attempt_row(path.name, raw, report,
                    native_present=raw is not None, source=str(path), selected=selected,
                    collector_observation=mapping(retained.get(path.name)).get('semantic_metadata_dispatch')))
                seen.add(path.name)
    for item in receipt.get('trials', []):
        if type(item) is not dict or item.get('trial') in seen:
            continue
        raw = {'task_name': item.get('task'), 'verifier_result': {'rewards': item.get('reward')},
            'exception_info': {'exception_type': item.get('exception_type')}}
        attempts.append(attempt_row(item.get('trial'), raw, item.get('supervisor'),
            native_present=True, source=str(folder / 'receipt.json'), selected=selected,
            collector_observation=item.get('semantic_metadata_dispatch')))
        seen.add(item.get('trial'))
    started = (folder / 'invocation.json').exists() or job.exists()
    final = bool(receipt.get('native_job_result_present')) or (job / 'result.json').is_file()
    state = ('pending' if not started and not attempts and not receipt else 'finished'
        if final and attempts and all(row['native_result_present'] for row in attempts) else 'started_or_partial')
    complete = bool(attempts) and state == 'finished' and not errors and all(row['provider_usage']['complete'] for row in attempts)
    sessions = [call['native_session_sha256'] for row in attempts for call in row['provider_usage']['calls'] if call['native_session_sha256'] is not None]
    distinct = len(sessions) == len(set(sessions))
    complete = complete and distinct
    controls.update(
        observed_tasks_match_selection=all(row['task'] in {selected['task'], 'terminal-bench/' + selected['task']} for row in attempts) if attempts else None,
        observed_context_profiles_match_selection=all(row['semantic_context_profile'] == selected['semantic_context_profile'] for row in attempts) if attempts else None,
        observed_requested_metadata_modes_match_selection=all(row['semantic_metadata_dispatch']['report_requested_mode'] == selected['semantic_metadata_view'] for row in attempts) if attempts else None,
        observed_models_match_selection=all(call['model'] == prepared.get('model') for row in attempts for call in row['provider_usage']['calls']) if sessions else None,
        cumulative_sessions_distinct_across_attempts=distinct if attempts else None,
    )
    complete_tokens = totals([{'tokens': row['provider_usage']['complete_tokens']} for row in attempts], 'tokens') if complete else dict.fromkeys(TOKENS)
    solved = True if any(row['solved'] is True for row in attempts) else False if final and attempts and all(row['solved'] is False for row in attempts) else None
    exclusions = []
    if state != 'finished': exclusions.append('trial_not_finished')
    if controls['original_task_inputs_unchanged_receipt'] is not True: exclusions.append('original_task_input_integrity_not_verified')
    if not complete: exclusions.append('complete_native_usage_unavailable')
    if not attempts or not all(row['genuine_model_implementation_observed'] for row in attempts): exclusions.append('model_implementation_not_observed_for_all_attempts')
    if not attempts or not all(row['context_input_audit']['all_observed_coding_inputs_verified'] is True for row in attempts): exclusions.append('exact_model_inputs_not_verified_for_all_attempts')
    if not attempts or not all(row['semantic_metadata_dispatch']['all_selection_receipts_bound_to_model_inputs'] for row in attempts): exclusions.append('metadata_selection_not_verified_for_all_attempts')
    if not attempts or not all(row['semantic_metadata_dispatch']['all_coding_inputs_verified_by_retained_audit'] for row in attempts): exclusions.append('metadata_exact_input_audit_not_correlated_for_all_attempts')
    if any(type(value) is bool and not value for key, value in controls.items() if key != 'complete_single_trial_receipt'): exclusions.append('declared_or_observed_controls_differ')
    effective_values = [row['semantic_metadata_dispatch']['effective_treatment_observed'] for row in attempts]
    effective = all(effective_values) if effective_values and all(type(value) is bool for value in effective_values) else None
    return {**selected, 'state': state, 'attempt_count_observed': len(attempts), 'attempts': attempts,
        'requested_arm_comparison_eligible': not exclusions,
        'effective_treatment_comparison_eligible': not exclusions and (selected['semantic_metadata_view'] == 'legacy' or effective is True),
        'comparison_exclusions': exclusions, 'effective_treatment_observed': effective,
        'solved': solved, 'usage_complete': complete, 'complete_tokens': complete_tokens,
        'known_token_subtotal': {key: sum(row['provider_usage']['known_token_subtotal'][key] for row in attempts if row['provider_usage']['known_token_subtotal'][key] is not None)
            if distinct and any(row['provider_usage']['known_token_subtotal'][key] is not None for row in attempts) else None for key in TOKENS},
        'tokens_per_solved_task': complete_tokens['total_tokens'] if complete and solved is True else None,
        'frozen_controls': controls, 'read_errors': errors}


def validate_protocol(protocol):
    rows = protocol.get('trials')
    if type(rows) is not list or not rows: raise ValueError('protocol requires trials')
    names, identities = set(), set()
    for row in rows:
        if type(row) is not dict: raise ValueError('trial must be an object')
        name = row.get('name')
        if type(name) is not str or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', name): raise ValueError('invalid trial name')
        if row.get('semantic_metadata_view') not in PROFILES: raise ValueError('unknown requested metadata arm')
        if row.get('semantic_context_profile') != CONTEXT_PROFILE: raise ValueError('fixed context profile drift')
        if type(row.get('repeat')) is not int or row['repeat'] < 1: raise ValueError('positive repeat required')
        if type(row.get('task')) is not str or not row['task']: raise ValueError('task required')
        identity = (row['task'], row['semantic_metadata_view'], row['repeat'])
        if name in names or identity in identities: raise ValueError('duplicate trial name or task/arm/repeat')
        names.add(name)
        identities.add(identity)
    if protocol.get('pairs_match_except') != list(REMOVED_AXES): raise ValueError('unexpected control normalization axes')
    if protocol.get('unordered_list_canonicalizations') != list(CANONICALIZED_AXES): raise ValueError('unordered-list policy mismatch')


def summarize_arm(rows):
    result = native.summarize_arm(rows)
    result.update(requested_arm_comparison_eligible=bool(rows) and all(row['requested_arm_comparison_eligible'] for row in rows),
        effective_treatment_trials=sum(row['effective_treatment_observed'] is True for row in rows),
        fallback_trials=sum(row['semantic_metadata_view'] != 'legacy' and row['effective_treatment_observed'] is False for row in rows),
        effective_treatment_comparison_eligible=bool(rows) and all(row['effective_treatment_comparison_eligible'] for row in rows),
        repeat_ids=[{'trial': row['name'], 'task': row['task'], 'repeat': row['repeat']} for row in rows],
        distinct_tasks=len({row['task'] for row in rows}),
        solved_trial_repeats=result.pop('solved_tasks'))
    return result


def aggregate(root):
    errors = []
    protocol = read_json(root / 'comparison-protocol.json', errors)
    if protocol is None: raise ValueError('comparison protocol unavailable: ' + repr(errors))
    validate_protocol(protocol)
    rows = [collect_trial(root, row, protocol) for row in protocol['trials']]
    ownership = {}
    for row in rows:
        for attempt in row['attempts']:
            for call in attempt['provider_usage']['calls']:
                session = call['native_session_sha256']
                if session: ownership.setdefault(session, set()).add(row['name'])
    duplicate_names = set().union(*(names for names in ownership.values() if len(names) > 1)) if ownership else set()
    for row in rows:
        row['frozen_controls']['cumulative_sessions_distinct_across_trials'] = row['name'] not in duplicate_names
        if row['name'] in duplicate_names:
            row.update(usage_complete=False, complete_tokens=dict.fromkeys(TOKENS), known_token_subtotal=dict.fromkeys(TOKENS),
                tokens_per_solved_task=None, requested_arm_comparison_eligible=False, effective_treatment_comparison_eligible=False)
            row['comparison_exclusions'].append('native_cumulative_session_reused_across_trials')
    populations = {profile: sorted({(row['task'], row['repeat']) for row in rows if row['semantic_metadata_view'] == profile}) for profile in PROFILES}
    matched_population = bool(populations['legacy']) and populations['legacy'] == populations['common-bindings@1']
    return {'schema': 'terminal-metadata-context-retained-aggregation@1',
        'requested_arm_populations_match': matched_population,
        'requested_arm_populations': {profile: [{'task': task, 'repeat': repeat} for task, repeat in values] for profile, values in populations.items()},
        'protocol_sha256': digest((root / 'comparison-protocol.json').read_bytes()),
        'aggregator_sha256': digest(Path(__file__).read_bytes()),
        'accounting_snapshot_sha256': digest(Path(native.__file__).read_bytes()),
        'provider_calls_by_aggregator': 0, 'source_commit': protocol.get('source_commit'),
        'trials': rows, 'arms': {profile: summarize_arm([row for row in rows if row['semantic_metadata_view'] == profile]) for profile in PROFILES if any(row['semantic_metadata_view'] == profile for row in rows)},
        'caveats': ['Requested-arm grouping retains valid fallbacks and failed-attempt costs in their originally requested arm.',
            'Effective treatment means common-bindings selected for all coding inputs and verified by correlated retained input audits; verified baseline remains effective_treatment_observed=false.',
            'Unknown usage and outcomes remain null; cached Codex input is included in input and is never counted twice.',
            'Success counts denote trial repeats; a task repeated twice is not two distinct tasks.',
            'All observed planning and coding attempts enter complete native token totals, including failures.',
            'Native token counters are not verified billing costs. Local bytes and proxy counts are not provider token measurements.',
            'Small counterbalanced samples are observational and do not establish statistical or causal improvement.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = aggregate(args.root.resolve())
    output = args.output or args.root / 'aggregate.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'output': str(output), 'arms': report['arms']}, indent=2))

if __name__ == '__main__': main()
