#!/usr/bin/env python3
"""Read one retained qualification receipt; export counts, never raw native data."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
SCHEMA = 'native-codex-interaction-telemetry@1'
TOKENS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
          'output_tokens', 'reasoning_output_tokens', 'total_tokens')
TOOLS = {'exec_command', 'write_stdin', 'apply_patch', 'view_image', 'functions.exec',
         'functions.wait', 'functions.exec_command', 'functions.write_stdin',
         'functions.apply_patch', 'functions.view_image', 'shell', 'shell_command',
         'update_plan', 'request_user_input', 'other'}
PAIRING = {'ambiguous_call_identity', 'output_without_observed_call',
           'call_without_observed_output', 'multiple_output_chunks_observed',
           'output_precedes_call', 'single_call_and_output_observed'}
INTERVAL = {'unknown_baseline', 'invalid_snapshot', 'counter_decrease',
            'adjacent_observations', 'repeated_snapshot', 'invalid_interval',
            'asserted_zero_origin', 'unknown_malformed_record_positions'}
BYTE_SCOPES = {'decoded_utf8_string', 'canonical_json_utf8', 'mixed_decoded_string_and_canonical_json'}
COUNTERS = ('observed_records', 'malformed_json_records', 'invalid_record_shapes',
            'observed_tool_call_events', 'observed_tool_output_events',
            'invalid_tool_identity_events', 'omitted_tool_events', 'observed_token_checkpoints',
            'omitted_token_observations', 'non_usage_token_events', 'invalid_token_snapshots',
            'counter_decrease_intervals', 'invalid_counter_intervals',
            'repeated_cumulative_snapshots', 'explicit_boundary_events_observed', 'valid_timestamp_events')
FALSE_FLAGS = ('raw_content_exported', 'provider_request_count_inferred',
               'provider_request_count_known', 'tool_token_attribution_available',
               'causal_tool_token_attribution', 'native_aggregate_usage_modified',
               'usage_completeness_established')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def count(value):
    return value if type(value) is int and 0 <= value <= (1 << 63) - 1 else None


def digest(value):
    return value if type(value) is str and re.fullmatch('[0-9a-f]{64}', value) else None


def choice(value, allowed):
    return value if type(value) is str and value in allowed else None


def mapping(value):
    return value if type(value) is dict else {}


def read(path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 16_000_000:
        raise ValueError('bounded_regular_json_required')
    return json.loads(path.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))


def usage(value):
    if type(value) is not dict:
        return None
    selected = {key: count(value[key]) for key in TOKENS if key in value}
    if (any(item is None for item in selected.values())
            or not {'input_tokens', 'output_tokens', 'total_tokens'} <= set(selected)
            or selected['input_tokens'] + selected['output_tokens'] != selected['total_tokens']):
        return None
    if any(selected.get(key, 0) > selected['input_tokens'] for key in ('cached_input_tokens', 'cache_write_input_tokens')):
        return None
    if selected.get('reasoning_output_tokens', 0) > selected['output_tokens']:
        return None
    return selected


def project_telemetry(value):
    """A closed projection cannot copy tool text, identities, or arbitrary labels."""
    value = mapping(value)
    problems = []
    if value.get('schema') != SCHEMA:
        problems.append('telemetry_schema_unavailable')
    if any(value.get(key) is not False for key in FALSE_FLAGS):
        problems.append('telemetry_observation_scope_invalid')
    for key in ('task_complete_observed', 'tool_observations_complete',
                'token_observations_complete', 'record_limit_exceeded'):
        if type(value.get(key)) is not bool:
            problems.append('telemetry_boolean_invalid')
    limits = {'records': 100_000, 'tool_pairs': 128, 'token_observations': 256, 'payload_bytes': 4_000_000}
    if value.get('limits') != limits:
        problems.append('telemetry_retention_limits_differ')
    pairs, checkpoints = value.get('tool_pairs'), value.get('token_observations')
    if type(pairs) is not list or len(pairs) > 128 or any(type(row) is not dict for row in pairs):
        problems.append('tool_population_invalid')
        pairs = []
    if type(checkpoints) is not list or len(checkpoints) > 256 or any(type(row) is not dict for row in checkpoints):
        problems.append('checkpoint_population_invalid')
        checkpoints = []
    projected_pairs = []
    for row in pairs:
        selected = {key: count(row.get(key)) for key in (
            'observation_ordinal', 'first_record_ordinal', 'session_scope_ordinal',
            'explicit_boundary_event_ordinal', 'call_event_count', 'output_event_count',
            'call_record_ordinal', 'output_record_ordinal', 'input_bytes', 'observed_output_bytes')}
        mandatory = {'observation_ordinal', 'first_record_ordinal', 'session_scope_ordinal',
                     'call_event_count', 'output_event_count'}
        if any(key not in row or (selected[key] is None and (key in mandatory or row[key] is not None))
               for key in selected):
            problems.append('tool_numeric_field_invalid')
        selected.update(tool_name=choice(row.get('tool_name'), TOOLS) or 'other',
                        tool_kind=choice(row.get('tool_kind'), {'function', 'custom'}),
                        pairing_status=choice(row.get('pairing_status'), PAIRING))
        for key in ('input_byte_scope', 'output_byte_scope'):
            selected[key] = choice(row.get(key), BYTE_SCOPES)
        code, elapsed = row.get('structured_exit_code'), row.get('recorded_observation_elapsed_seconds')
        selected['structured_exit_code'] = code if type(code) is int and -(1 << 31) <= code < (1 << 31) else None
        selected['recorded_observation_elapsed_seconds'] = (elapsed if type(elapsed) in (int, float)
            and math.isfinite(elapsed) and 0 <= elapsed <= 86_400 else None)
        if ((code is not None and selected['structured_exit_code'] is None)
                or (elapsed is not None and selected['recorded_observation_elapsed_seconds'] is None)):
            problems.append('tool_status_or_elapsed_invalid')
        if selected['pairing_status'] is None:
            problems.append('tool_pairing_status_invalid')
        projected_pairs.append(selected)
    projected_checkpoints = []
    for row in checkpoints:
        selected = {key: count(row.get(key)) for key in (
            'observation_ordinal', 'record_ordinal', 'session_scope_ordinal',
            'explicit_boundary_event_ordinal', 'observed_tool_call_events_since_previous_checkpoint',
            'observed_tool_output_events_since_previous_checkpoint')}
        if any(key not in row or (selected[key] is None and
               (key != 'explicit_boundary_event_ordinal' or row[key] is not None)) for key in selected):
            problems.append('checkpoint_numeric_field_invalid')
        status = row.get('interval_status')
        selected['interval_status'] = status if type(status) is str and status in INTERVAL else None
        selected['cumulative_counters'] = usage(row.get('cumulative_counters'))
        selected['adjacent_counter_delta'] = usage(row.get('adjacent_counter_delta'))
        if any(row.get(key) is not None and selected[key] is None
               for key in ('cumulative_counters', 'adjacent_counter_delta')):
            problems.append('checkpoint_counter_invalid')
        if selected['interval_status'] is None:
            problems.append('checkpoint_interval_status_invalid')
        projected_checkpoints.append(selected)
    counts = {key: count(value.get(key)) for key in COUNTERS}
    if any(item is None for item in counts.values()):
        problems.append('telemetry_counter_unavailable')
    if (counts['observed_token_checkpoints'] is not None and counts['omitted_token_observations'] is not None
            and counts['observed_token_checkpoints'] != len(checkpoints) + counts['omitted_token_observations']):
        problems.append('checkpoint_population_counts_differ')
    if all(counts[key] is not None for key in ('observed_tool_call_events', 'observed_tool_output_events',
                                             'invalid_tool_identity_events', 'omitted_tool_events')):
        retained_events = [row[key] for row in projected_pairs for key in ('call_event_count', 'output_event_count')]
        if None not in retained_events and (sum(retained_events) + counts['invalid_tool_identity_events']
                + counts['omitted_tool_events'] != counts['observed_tool_call_events'] + counts['observed_tool_output_events']):
            problems.append('tool_population_counts_differ')
    # Recompute intervals from consecutive retained cumulative endpoints. The
    # first checkpoint has no asserted origin in native rollout recovery.
    previous, previous_scope = None, None
    for row in projected_checkpoints:
        scope, counters, delta, status = (row['session_scope_ordinal'], row['cumulative_counters'],
                                         row['adjacent_counter_delta'], row['interval_status'])
        if scope != previous_scope:
            previous = None
        if counts['malformed_json_records'] != 0:
            valid = delta is None
        elif counters is None:
            valid = status == 'invalid_snapshot' and delta is None
        elif previous is None:
            valid = status == 'unknown_baseline' and delta is None
        else:
            common = set(counters) & set(previous)
            expected_delta = {key: counters[key] - previous[key] for key in common}
            if any(item < 0 for item in expected_delta.values()):
                valid = status == 'counter_decrease' and delta is None
            elif (any(expected_delta.get(key, 0) > expected_delta['input_tokens']
                      for key in ('cached_input_tokens', 'cache_write_input_tokens'))
                    or expected_delta.get('reasoning_output_tokens', 0) > expected_delta['output_tokens']):
                valid = status == 'invalid_interval' and delta is None
            else:
                expected_status = 'repeated_snapshot' if counters == previous else 'adjacent_observations'
                valid = status == expected_status and delta == expected_delta
        if not valid:
            problems.append('checkpoint_delta_recomputation_differs')
        previous = None if status in {'invalid_snapshot', 'counter_decrease', 'invalid_interval'} else counters
        previous_scope = scope
    for population in (projected_pairs, projected_checkpoints):
        if any(row['observation_ordinal'] != index for index, row in enumerate(population, 1)):
            problems.append('observation_ordinals_differ')
    all_records_known = (value.get('task_complete_observed') is True
        and counts['malformed_json_records'] == 0 and counts['invalid_record_shapes'] == 0
        and value.get('record_limit_exceeded') is False)
    tool_census = (all_records_known and counts['invalid_tool_identity_events'] == counts['omitted_tool_events'] == 0
        and all(row['pairing_status'] == 'single_call_and_output_observed'
            and row['call_event_count'] == row['output_event_count'] == 1
            and row['input_bytes'] is not None and row['observed_output_bytes'] is not None
            for row in projected_pairs))
    token_census = (all_records_known and all(counts[key] == 0 for key in (
        'omitted_token_observations', 'invalid_token_snapshots', 'counter_decrease_intervals', 'invalid_counter_intervals'))
        and all(row['cumulative_counters'] is not None for row in projected_checkpoints))
    if (tool_census != value.get('tool_observations_complete')
            or token_census != value.get('token_observations_complete')):
        problems.append('producer_census_completeness_differs')
    limitations = []
    if not value.get('tool_observations_complete'):
        limitations.append('tool_census_incomplete')
    if not value.get('token_observations_complete'):
        limitations.append('checkpoint_census_incomplete')
    if any(row['interval_status'] == 'unknown_baseline' for row in projected_checkpoints):
        limitations.append('first_observation_has_unknown_counter_origin')
    if any(row['pairing_status'] != 'single_call_and_output_observed' for row in projected_pairs):
        limitations.append('some_tool_records_lack_single_call_output_pairing')
    if any(row['recorded_observation_elapsed_seconds'] is None for row in projected_pairs):
        limitations.append('some_tool_observation_elapsed_times_unavailable')
    census_complete = not problems and tool_census and token_census
    return {
        'schema': SCHEMA, 'counts': counts, 'limits': limits, 'tool_pairs': projected_pairs,
        'token_observations': projected_checkpoints,
        'tool_observations_complete': value.get('tool_observations_complete') is True,
        'token_observations_complete': value.get('token_observations_complete') is True,
        'record_limit_exceeded': value.get('record_limit_exceeded') is True,
        'task_complete_observed': value.get('task_complete_observed') is True,
        'census_complete': census_complete, 'limitations': limitations,
        'adjacent_deltas_independently_checked': 'checkpoint_delta_recomputation_differs' not in problems,
        **dict.fromkeys(FALSE_FLAGS, False),
        'scope': 'Native record bytes and adjacent cumulative observations; no causal token attribution or execution latency.',
    }, sorted(set(problems))

