#!/usr/bin/env python3
"""Content-free comparison of frozen requested Terminal Bench source-view arms.

Reads only the comparison protocol, explicit trial/state markers and structured
launcher/receipt fields. It never opens native model transcripts or task trees.
Default output is stdout; --output creates a new file and never overwrites one.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parent
SCHEMA = 'terminal-source-view-comparison@1'
MODES = ('source-view-raw@1', 'source-view-compact@1')
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_COUNT = 2**63 - 1


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def read_json(root, relative, *, required=False):
    path = root / relative
    try:
        if path.resolve(strict=True) != path or not path.is_relative_to(root):
            raise ValueError('canonical artifact required')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_JSON_BYTES:
                raise ValueError('bounded regular artifact required')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(MAX_JSON_BYTES + 1)
            if len(raw) > MAX_JSON_BYTES:
                raise ValueError('artifact byte bound exceeded')
        finally:
            os.close(fd)
        value = json.loads(raw, object_pairs_hook=_unique)
        if not isinstance(value, dict):
            raise ValueError('artifact object required')
        return value, {'state': 'read', 'sha256': _sha(raw), 'path': relative}
    except FileNotFoundError:
        if required:
            raise ValueError('required artifact missing: ' + relative) from None
        return None, {'state': 'missing', 'sha256': None, 'path': relative}
    except (OSError, ValueError, UnicodeError):
        if required:
            raise ValueError('required artifact invalid: ' + relative) from None
        return None, {'state': 'invalid', 'sha256': None, 'path': relative}


def _count(value):
    return value if type(value) is int and 0 <= value <= MAX_COUNT else None


def _label(value):
    return value if type(value) is str and re.fullmatch(r'[A-Za-z0-9_@.:-]{1,128}', value) else None


def _digest(value):
    return value if type(value) is str and re.fullmatch('[0-9a-f]{64}', value) else None


def _boolean(value):
    return value if type(value) is bool else None


def usage_observation(outcome):
    native = outcome.get('usage')
    metadata = outcome.get('supervisor_usage')
    native = native if isinstance(native, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    counts = {key: _count(native.get(exported)) for key, exported in (
        ('input_tokens', 'n_input_tokens'), ('cached_input_tokens', 'n_cache_tokens'), ('output_tokens', 'n_output_tokens'))}
    totals = {key: _count(metadata.get(key)) for key in (*counts, 'total_tokens')}
    complete = (metadata.get('usage_accounting_complete') is True
        and metadata.get('token_count_scope') == 'native_session_cumulative'
        and metadata.get('cache_included_in_input') is True
        and all(value is not None for value in counts.values())
        and all(value is not None for value in totals.values())
        and all(value == totals[key] for key, value in counts.items())
        and totals['cached_input_tokens'] <= totals['input_tokens']
        and totals['input_tokens'] + totals['output_tokens'] == totals['total_tokens'])
    return {'complete': complete, 'observed_counts': counts,
        'complete_total_tokens': totals['total_tokens'] if complete else None,
        'reported_total_tokens': totals['total_tokens'], 'cache_is_subset_of_input': True,
        'total_formula': 'input_tokens + output_tokens; cached_input_tokens is not added again',
        'scope': 'native_session_cumulative' if complete else 'unknown_or_incomplete',
        'billing_total_verified': False, 'dollar_cost': None}


def reward_observation(outcome):
    rewards = outcome.get('official_rewards')
    reward = rewards.get('reward') if isinstance(rewards, dict) else None
    valid = (type(reward) in (int, float)
        and (type(reward) is int or math.isfinite(reward)) and abs(reward) <= MAX_COUNT)
    return {'official_reward': reward if valid else None,
        'official_success': reward > 0 if valid else None}


def stop_observation(value):
    if value is None:
        return None
    if (not isinstance(value, dict) or value.get('schema') != 'terminal-provider-stop@1'
            or value.get('state') not in ('rate_limited', 'provider_blocked')
            or value.get('reason_code') not in ('rate_limit', 'authentication', 'billing', 'quota')):
        return {'state': 'invalid_stop_metadata'}
    delay = value.get('retry_after_seconds')
    delay = delay if type(delay) in (int, float) and 0 < delay <= 604800 else None
    return {key: value.get(key) for key in ('schema', 'state', 'reason_code')} | {
        'provider': value.get('provider') if value.get('provider') in ('codex_cli', 'grok_cli') else None,
        'observation_valid': _boolean(value.get('observation_valid')),
        'retry_after_seconds': delay, 'retry_after_unbounded': value.get('retry_after_unbounded') is True,
        'automatic_replay_allowed': False}


def helper_observation(supervisor):
    rows = supervisor.get('provider_invocations') if isinstance(supervisor, dict) else None
    unknown = {'status': 'unknown', 'coding_invocations': None, 'operations': None,
        'operation_counts': None, 'format_counts': None, 'changed_edits': None, 'no_op_edits': None,
        'response_bytes': None, 'helper_operations_observed': None, 'measurement_authority': 'worker-owned observations'}
    if (not isinstance(rows, list) or len(rows) > 1024
            or any(not isinstance(row, dict) for row in rows)):
        return unknown
    coding = [row for row in rows if row.get('phase') == 'coding']
    identities = [row.get('invocation_id') for row in coding]
    if (supervisor.get('unreceipted_provider_attempt') or any(_label(item) is None for item in identities)
            or len(set(identities)) != len(identities)):
        return {**unknown, 'coding_invocations': len(coding)}
    if not coding:
        return {**unknown, 'status': 'no_coding_invocation', 'coding_invocations': 0}
    operations, formats = Counter(), Counter()
    count = changed = no_ops = response_bytes = 0
    for row in coding:
        binding = row.get('source_view_policy')
        usage = binding.get('usage') if isinstance(binding, dict) else None
        if not isinstance(usage, dict):
            return {**unknown, 'coding_invocations': len(coding)}
        op_counts, fmt_counts = usage.get('operation_counts'), usage.get('format_counts')
        if (usage.get('schema') != 'code-source-view-usage@1'
                or usage.get('status') not in ('observed', 'not_observed')
                or not isinstance(op_counts, dict) or not set(op_counts) <= {'index', 'read', 'replace'}
                or not isinstance(fmt_counts, dict) or not set(fmt_counts) <= {'raw', 'compact'}
                or any(_count(value) is None for value in [*op_counts.values(), *fmt_counts.values()])
                or any(_count(usage.get(key)) is None for key in ('operations', 'changed_edits', 'no_op_edits', 'response_bytes'))
                or sum(op_counts.values()) != usage['operations']
                or sum(fmt_counts.values()) != op_counts.get('read', 0)
                or usage['changed_edits'] + usage['no_op_edits'] != op_counts.get('replace', 0)
                or (usage['operations'] > 0) != (usage['status'] == 'observed')):
            return {**unknown, 'coding_invocations': len(coding)}
        operations.update(op_counts)
        formats.update(fmt_counts)
        count += usage['operations']
        changed += usage['changed_edits']
        no_ops += usage['no_op_edits']
        response_bytes += usage['response_bytes']
    return {'status': 'observed' if count else 'not_observed', 'coding_invocations': len(coding),
        'operations': count, 'operation_counts': dict(operations), 'format_counts': dict(formats),
        'changed_edits': changed, 'no_op_edits': no_ops, 'response_bytes': response_bytes,
        'helper_operations_observed': bool(count), 'measurement_authority': 'worker-owned observations'}


def trial_observation(root, requested):
    name = requested['name']
    outcome, outcome_artifact = read_json(root, f'launcher-state/{name}/outcome.json')
    receipt, receipt_artifact = read_json(root, f'trials/{name}/receipt.json')
    invocation, invocation_artifact = read_json(root, f'trials/{name}/invocation.json')
    claim, claim_artifact = read_json(root, f'launcher-state/{name}/claim.json')
    process, process_artifact = read_json(root, f'launcher-state/{name}/process.json')
    outcome = outcome or {}
    receipt = receipt or {}
    binding = (outcome_artifact['state'] == 'read' and receipt_artifact['state'] == 'read'
        and invocation_artifact['state'] == 'read'
        and _digest(outcome.get('receipt_sha256')) == receipt_artifact['sha256'])
    expected_outcome_identity = outcome.get('trial') == name
    trusted_outcome = outcome if expected_outcome_identity and binding else {}
    usage = usage_observation(trusted_outcome)
    reward = reward_observation(trusted_outcome)
    rows = receipt.get('trials')
    row = rows[0] if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) else {}
    if receipt.get('schema') != 'terminal-full-supervisor-receipt@1':
        row = {}
    dispatch = row.get('source_view_dispatch')
    guidance = (dispatch.get('effective_advisory_observed') if isinstance(dispatch, dict)
        and dispatch.get('schema') == 'terminal-source-view-dispatch-observation@1'
        and dispatch.get('requested_policy') == requested['source_view_policy'] else None)
    classification = _label(outcome.get('classification')) if expected_outcome_identity else None
    attempted = invocation_artifact['state'] == 'read'
    state = ('finished' if outcome_artifact['state'] == 'read' and expected_outcome_identity
        else 'running_or_unresolved' if attempted or process_artifact['state'] == 'read'
        else 'claimed_without_observed_process' if claim_artifact['state'] == 'read' else 'unstarted')
    if classification in ('provider_deferred', 'resource_wait_exhausted'):
        state = classification
    if any(artifact['state'] == 'invalid' for artifact in (outcome_artifact, receipt_artifact,
            invocation_artifact, claim_artifact, process_artifact)):
        state = 'invalid_artifact'
    deferral = outcome.get('provider_deferral')
    deferral = deferral if isinstance(deferral, dict) else {}
    return {'name': name, 'task': requested['task'], 'requested_arm': requested['source_view_policy'],
        'state': state, 'attempted': attempted, 'launcher_process_observed': process_artifact['state'] == 'read',
        'classification': classification, 'complete_single_trial_receipt': _boolean(receipt.get('complete_single_trial_receipt')),
        'outcome_receipt_binding_verified': binding and expected_outcome_identity,
        'native_usage': usage, **reward, 'effective_guidance_observed': _boolean(guidance),
        'source_helper': helper_observation(row.get('supervisor')),
        'provider_stop': stop_observation(row.get('provider_stop')),
        'provider_deferral_reason': _label(deferral.get('reason')),
        'receipt_artifact': receipt_artifact, 'outcome_artifact': outcome_artifact,
        'raw_model_logs_read': False, 'hidden_task_files_read': False}


def aggregate(trials, mode):
    rows = [row for row in trials if row['requested_arm'] == mode]
    known = [row for row in rows if row['native_usage']['complete']]
    success = sum(row['official_success'] is True for row in rows)
    unknown_success = sum(row['official_success'] is None for row in rows)
    all_known = bool(rows) and len(known) == len(rows)
    subtotal = sum(row['native_usage']['complete_total_tokens'] for row in known)
    denominator_known = all_known and unknown_success == 0 and all(row['attempted'] for row in rows)
    return {'requested_arm': mode, 'requested_trials': len(rows),
        'attempted_trials': sum(row['attempted'] for row in rows),
        'unstarted_trials': sum(row['state'] == 'unstarted' for row in rows),
        'official_successes_observed': success, 'official_failures_observed': sum(row['official_success'] is False for row in rows),
        'official_success_unknown_trials': unknown_success, 'complete_native_usage_trials': len(known),
        'known_native_token_subtotal': subtotal if known else None,
        'all_requested_native_tokens': subtotal if all_known else None,
        'tokens_per_successfully_solved_task': subtotal / success if denominator_known and success else None,
        'helper_adoption_observed_trials': sum(row['source_helper']['helper_operations_observed'] is True for row in rows),
        'helper_nonadoption_observed_trials': sum(row['source_helper']['helper_operations_observed'] is False for row in rows),
        'helper_adoption_unknown_trials': sum(row['source_helper']['helper_operations_observed'] is None for row in rows),
        'failures_and_nonadoption_retained': True,
        'missing_trials_and_usage_not_imputed_as_zero': True}


def collect(root=ROOT):
    root = Path(root).absolute()
    if root.resolve(strict=True) != root:
        raise ValueError('canonical campaign root required')
    protocol, protocol_artifact = read_json(root, 'comparison-protocol.json', required=True)
    requested = protocol.get('trials')
    if (protocol.get('schema') != 'terminal-source-view-comparison-protocol@1'
            or not isinstance(requested, list) or not 1 <= len(requested) <= 32
            or any(not isinstance(row, dict) or not isinstance(row.get('name'), str)
                or re.fullmatch('[a-z0-9][a-z0-9-]{0,99}', row['name']) is None
                or row.get('source_view_policy') not in MODES or _label(row.get('task')) is None for row in requested)
            or len({row['name'] for row in requested}) != len(requested)):
        raise ValueError('bounded frozen requested trial population required')
    trials = [trial_observation(root, row) for row in requested]
    offline, offline_artifact = read_json(root, 'offline-final/qualification.json')
    offline = offline or {}
    offline_rows = offline.get('tasks')
    offline_rows = offline_rows if isinstance(offline_rows, list) and len(offline_rows) <= 8 else []
    projected_offline = []
    for row in offline_rows:
        if not isinstance(row, dict) or _label(row.get('task_name')) is None:
            continue
        projection = {'task': row['task_name'], 'qualified': _boolean(row.get('qualified'))}
        for mode in ('raw', 'compact'):
            values = row.get(mode)
            values = values if isinstance(values, dict) else {}
            projection[mode] = {}
            for scope in ('module_read_protocol', 'edit_cycle_protocol', 'normal_workflow_protocol', 'complete_qualification_protocol'):
                metrics = values.get(scope)
                metrics = metrics if isinstance(metrics, dict) else {}
                projection[mode][scope] = {key: _count(metrics.get(key)) for key in
                    ('protocol_messages', 'rendered_json_bytes', 'local_tokenizer_proxy_tokens')}
        projected_offline.append(projection)
    return {'schema': SCHEMA, 'protocol_artifact': protocol_artifact,
        'source_commit': protocol.get('source_commit') if type(protocol.get('source_commit')) is str
            and re.fullmatch('[0-9a-f]{40}', protocol['source_commit']) else None,
        'archive_sha256': _digest(protocol.get('archive_sha256')),
        'trials': trials, 'arms': [aggregate(trials, mode) for mode in MODES],
        'all_requested_trials_have_complete_native_usage': all(row['native_usage']['complete'] for row in trials),
        'all_requested_official_success_observed': all(row['official_success'] is not None for row in trials),
        'offline_summary': {'artifact': offline_artifact, 'metrics': projected_offline,
            'scope': 'local o200k tokenizer proxy; not provider usage'},
        'provider_calls_by_collector': 0, 'containers_started_by_collector': 0,
        'model_logs_read': False, 'hidden_task_files_read': False,
        'limitations': ['One repeat per arm on two tasks cannot establish statistical or causal improvement.',
            'Requested arms retain failed trials and observed helper nonadoption; missing accounting remains unknown.',
            'The source helper supplements the existing indexed capsule/admission/raw_sources/proof context pack; live totals count both when sent.',
            'Offline proxy totals cover helper protocol only, excluding existing context, model reasoning and provider message framing.',
            'Worker-owned helper counts establish observations, not universal interception, trusted proof, or guaranteed adoption.',
            'Native cumulative totals are provider-session observations, not verified billing or auxiliary-model accounting.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = collect(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(rendered)
    else:
        print(rendered, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
