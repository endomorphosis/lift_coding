#!/usr/bin/env python3
"""Audit NEW handoff transcriptions, not recovered experiment evidence.

Standard library only; no package imports, network, model, solver, or subprocess.
Inputs are explicit and bounded. Outputs require a nonexistent directory and use
exclusive creation. Arithmetic consistency is not empirical authenticity.

Example (run from the reconstructed package directory):
  python3 author_materials/verify_reported_numbers.py \
    --trials author_materials/reported_trials.jsonl \
    --audit-spec author_materials/numerical_audit.json \
    --output-dir numerical_audit_run_01

This is newly authored reconstruction code, NOT the unavailable supplied audit.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path
import sys

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_OBSERVATIONS = 200


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON object key: ' + key)
        result[key] = value
    return result


def reject_nonfinite_constant(value):
    raise AuditError('Nonfinite JSON value: ' + value)


def decode_json(text, label):
    try:
        return json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=reject_nonfinite_constant)
    except (ValueError, TypeError) as exc:
        raise AuditError(label + ': ' + str(exc)) from exc


def read_input(path):
    require(not path.is_symlink(), 'Explicit input must not be a symlink: ' + str(path))
    require(path.is_file(), 'Input is not a regular file: ' + str(path))
    require(path.stat().st_size <= MAX_INPUT_BYTES, 'Input exceeds the 2 MiB bound: ' + str(path))
    data = path.read_bytes()
    require(len(data) <= MAX_INPUT_BYTES, 'Input grew beyond its bound: ' + str(path))
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise AuditError('Input is not UTF-8: ' + str(path)) from exc
    return text, {'file_name': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                  'bytes': len(data)}


def count(value, label, nullable=False):
    if nullable and value is None:
        return
    require(type(value) is int and value >= 0, label + ' must be a nonnegative integer')


def percent_reduction(control, candidate, places=6):
    require(type(control) is int and control > 0, 'Percentage denominator must be positive')
    count(candidate, 'Percentage candidate')
    require(type(places) is int and 0 <= places <= 12, 'Invalid decimal precision')
    with localcontext() as ctx:
        ctx.prec = 64
        percent = Decimal(control - candidate) * Decimal(100) / Decimal(control)
        return format(percent.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), 'f')


def validate_record(row):
    require(isinstance(row, dict), 'Observation must be an object')
    oid = row.get('observation_id')
    require(isinstance(oid, str) and oid.startswith('handoff-'), 'Invalid local observation identifier')
    require(row.get('schema_version') == 'reconstructed-handoff-trial-observation/v1', oid + ': wrong schema')
    require(row.get('provenance') == 'user_handoff_transcription', oid + ': wrong provenance')
    require(row.get('empirical_authenticity') == 'unverified', oid + ': cannot promote authenticity')
    require(row.get('identity_status') == 'transcribed_observation_not_recovered_run', oid + ': wrong identity status')
    for key in ('original_task_id', 'original_run_id', 'original_invocation_id', 'actual_session_id'):
        require(row.get(key) is None or isinstance(row[key], str), oid + ': invalid ' + key)
    require(row.get('actual_session_id') is None, oid + ': newly recovered sessions require a separately reviewed evidence schema')
    require(row.get('deduplication_status') == 'actual_session_binding_unavailable', oid + ': invalid deduplication status')
    usage = row.get('usage')
    require(isinstance(usage, dict), oid + ': missing usage object')
    count(usage.get('reported_total_tokens'), oid + ': total')
    for key in ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens'):
        require(key in usage, oid + ': missing nullable counter ' + key)
        count(usage[key], oid + ': ' + key, nullable=True)
    require(usage.get('usage_completeness') == 'unknown', oid + ': completeness is not established by these inputs')
    require(usage.get('pipeline_cost_completeness') == 'unknown', oid + ': pipeline completeness is not established')
    inp, out, cached = (usage[key] for key in ('input_tokens', 'output_tokens', 'cached_input_tokens'))
    require((inp is None) == (out is None), oid + ': partial input/output pair needs an explicit accounting schema')
    if inp is not None:
        require(usage.get('accounting_schema') == 'input_plus_output_with_cached_input_subset', oid + ': component schema mismatch')
        require(inp + out == usage['reported_total_tokens'], oid + ': input + output does not equal total')
        if cached is not None:
            require(cached <= inp, oid + ': cached input exceeds input')
        component_status = 'input_plus_output_checked'
    else:
        require(usage.get('accounting_schema') == 'aggregate_total_only_components_unavailable', oid + ': aggregate schema mismatch')
        require(cached is None, oid + ': cannot check a cached subset without input count')
        component_status = 'unavailable_aggregate_total_only'
    outcome = row.get('reported_outcome')
    require(isinstance(outcome, dict), oid + ': missing reported outcome')
    for key in ('success_claim', 'supervisor_completion'):
        require(outcome.get(key) is None or type(outcome[key]) is bool, oid + ': invalid ' + key)
    reward = outcome.get('task_reward')
    require(reward is None or (type(reward) in (int, float) and math.isfinite(reward) and 0 <= reward <= 1), oid + ': invalid reward')
    require(not (outcome.get('success_claim') is False and reward == 1), oid + ': failed observation contradicts full reward')
    fallback = row.get('native_fallback_reported')
    require(fallback is None or type(fallback) is bool, oid + ': invalid fallback flag')
    if fallback is True:
        require(row.get('delivered_treatment') == 'native_fallback', oid + ': contradictory fallback delivery')
    for key in ('agent_seconds', 'setup_seconds'):
        value = row.get('reported_metrics', {}).get(key)
        require(value is None or (type(value) in (int, float) and math.isfinite(value) and value >= 0), oid + ': invalid clock ' + key)
    return {'observation_id': oid, 'reported_total_tokens': usage['reported_total_tokens'],
            'component_arithmetic': component_status,
            'cached_input_subset': 'checked' if cached is not None else 'unavailable',
            'usage_completeness': 'unknown', 'empirical_authenticity': 'unverified'}


def audit(trials_text, spec_text, inputs):
    lines = trials_text.splitlines()
    require(0 < len(lines) <= MAX_OBSERVATIONS, 'Observation count outside the 1..200 bound')
    require(all(line.strip() for line in lines), 'Blank JSONL observation lines are not allowed')
    records = [decode_json(line, 'Trial line ' + str(i + 1)) for i, line in enumerate(lines)]
    spec = decode_json(spec_text, 'Audit specification')
    require(isinstance(spec, dict), 'Audit specification must be an object')
    require(spec.get('schema_version') == 'reconstructed-numerical-audit-spec/v1', 'Invalid specification schema')
    require(spec.get('origin') == 'newly_authored_reconstruction_not_the_missing_supplied_audit', 'Invalid audit origin')
    require(spec.get('empirical_authenticity') == 'unverified', 'Audit cannot authenticate observations')
    rows = [validate_record(row) for row in records]
    by_id = {row['observation_id']: row for row in records}
    require(len(by_id) == len(records), 'Duplicate observation identifier')
    expected_ids = spec.get('required_observation_ids')
    require(isinstance(expected_ids, list) and all(isinstance(x, str) for x in expected_ids), 'Missing expected observation inventory')
    require(len(expected_ids) == len(set(expected_ids)), 'Duplicate expected observation identifier')
    require(set(by_id) == set(expected_ids), 'Observed inventory differs from declared inventory')
    expectations = spec.get('transcribed_total_expectations')
    require(isinstance(expectations, dict) and set(expectations) == set(by_id), 'Total expectation inventory mismatch')
    for oid, expected in expectations.items():
        count(expected, oid + ': expected total')
        require(by_id[oid]['usage']['reported_total_tokens'] == expected, oid + ': transcribed total mismatch')
    component_checks = spec.get('component_sum_expectations')
    require(isinstance(component_checks, list), 'Missing component expectations')
    component_ids = []
    for expected in component_checks:
        require(isinstance(expected, dict), 'Component expectation must be an object')
        oid = expected.get('observation_id')
        require(oid in by_id, 'Unknown component observation')
        component_ids.append(oid)
        usage = by_id[oid]['usage']
        for key in ('input_tokens', 'output_tokens', 'cached_input_tokens'):
            count(expected.get(key), oid + ': expected ' + key)
            require(usage[key] == expected[key], oid + ': component transcription mismatch for ' + key)
        count(expected.get('total_tokens'), oid + ': expected component total')
        require(expected['input_tokens'] + expected['output_tokens'] == expected['total_tokens'] == usage['reported_total_tokens'], oid + ': contradictory component expectation')
    require(len(component_ids) == len(set(component_ids)), 'Duplicate component expectation')
    require(set(component_ids) == {oid for oid, row in by_id.items() if row['usage']['input_tokens'] is not None}, 'Component expectation coverage mismatch')
    comparisons = spec.get('comparisons')
    require(isinstance(comparisons, list) and len(comparisons) <= MAX_OBSERVATIONS, 'Invalid comparison inventory')
    comparison_rows = []
    comparison_ids = set()
    for comparison in comparisons:
        require(isinstance(comparison, dict), 'Comparison must be an object')
        cid = comparison.get('comparison_id')
        require(isinstance(cid, str) and cid and cid not in comparison_ids, 'Duplicate or invalid comparison identifier')
        comparison_ids.add(cid)
        control_id, candidate_id = (comparison.get(key) for key in ('control_observation_id', 'candidate_observation_id'))
        require(control_id in by_id and candidate_id in by_id and control_id != candidate_id, cid + ': invalid comparison members')
        control, candidate = by_id[control_id], by_id[candidate_id]
        require(control['comparison_group'] == candidate['comparison_group'], cid + ': cannot compare unrelated groups')
        base, treatment = (row['usage']['reported_total_tokens'] for row in (control, candidate))
        comparison_rows.append({'comparison_id': cid, 'comparison_group': control['comparison_group'],
            'control_observation_id': control_id, 'candidate_observation_id': candidate_id,
            'control_reported_tokens': base, 'candidate_reported_tokens': treatment,
            'candidate_minus_control_tokens': treatment - base,
            'candidate_reduction_percent_of_control': percent_reduction(base, treatment),
            'control_success_claim': control['reported_outcome']['success_claim'],
            'candidate_success_claim': candidate['reported_outcome']['success_claim'],
            'interpretation': comparison.get('interpretation'),
            'accounting_scope': 'transcribed_reported_totals_only_usage_completeness_unknown'})
    aggregates = []
    for assertion in spec.get('manuscript_aggregate_assertions', []):
        require(isinstance(assertion, dict), 'Manuscript aggregate must be an object')
        require(assertion.get('provenance') == 'manuscript_aggregate_transcription' and assertion.get('empirical_authenticity') == 'unverified', 'Invalid manuscript aggregate provenance')
        count(assertion.get('reported_task_count'), 'Manuscript task count')
        control, candidate = assertion.get('control_tokens'), assertion.get('candidate_tokens')
        count(control, 'Manuscript control tokens')
        count(candidate, 'Manuscript candidate tokens')
        rounded = percent_reduction(control, candidate, assertion.get('rounding_decimal_places'))
        require(rounded == assertion.get('reported_reduction_percent'), 'Manuscript reported reduction does not match the stated rounding')
        aggregates.append({'assertion_id': assertion.get('assertion_id'),
            'control_tokens': control, 'candidate_tokens': candidate,
            'candidate_minus_control_tokens': candidate - control,
            'reported_task_count': assertion['reported_task_count'],
            'computed_reduction_percent': rounded, 'arithmetic_status': 'checked',
            'provenance': 'manuscript_aggregate_transcription',
            'source_reference': assertion.get('source_reference'),
            'source_expected_sha256': assertion.get('source_expected_sha256'),
            'source_binding_check': 'not_checked_by_this_arithmetic_script',
            'empirical_authenticity': 'unverified'})
    result = {'schema_version': 'reconstructed-numerical-audit-results/v1',
        'audit_origin': spec['origin'], 'arithmetic_status': 'passed',
        'empirical_authenticity': 'unverified', 'behavioral_reexecution': False,
        'source_binding_authentication': 'not_performed',
        'actual_session_deduplication': 'unavailable', 'project_total_tokens': None,
        'historical_2523452_token_subtotal': 'unreconciled',
        'usage_completeness': 'unknown',
        'observation_count': len(records),
        'component_sum_check_count': len(component_checks),
        'comparison_count': len(comparison_rows),
        'inputs': inputs, 'observation_checks': rows, 'comparisons': comparison_rows,
        'manuscript_aggregate_checks': aggregates,
        'unreconciled_claims': spec.get('unreconciled_claims', []),
        'limitations': spec.get('prohibited_inferences', [])}
    return result, comparison_rows


def exclusive_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--trials', required=True, type=Path)
    parser.add_argument('--audit-spec', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New directory, whose parent already exists; never overwritten')
    args = parser.parse_args()
    try:
        require(not args.output_dir.exists() and not args.output_dir.is_symlink(), 'Output directory must not already exist')
        require(args.output_dir.parent.is_dir(), 'Output parent directory must already exist')
        trials_text, trials_info = read_input(args.trials)
        spec_text, spec_info = read_input(args.audit_spec)
        result, comparison_rows = audit(trials_text, spec_text, {'trials': trials_info, 'specification': spec_info})
        json_text = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        csv_buffer = io.StringIO(newline='')
        fields = ['comparison_id', 'comparison_group', 'control_observation_id', 'candidate_observation_id',
                  'control_reported_tokens', 'candidate_reported_tokens', 'candidate_minus_control_tokens',
                  'candidate_reduction_percent_of_control', 'control_success_claim', 'candidate_success_claim',
                  'interpretation', 'accounting_scope']
        writer = csv.DictWriter(csv_buffer, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(comparison_rows)
        args.output_dir.mkdir(mode=0o700, exist_ok=False)
        exclusive_write(args.output_dir / 'numerical_audit_results.json', json_text)
        exclusive_write(args.output_dir / 'comparison_results.csv', csv_buffer.getvalue())
        print(json.dumps({'arithmetic_status': 'passed', 'empirical_authenticity': 'unverified',
                          'observation_count': result['observation_count'],
                          'component_sum_checks': result['component_sum_check_count'],
                          'comparisons': result['comparison_count'],
                          'project_total_tokens': None,
                          'outputs': ['numerical_audit_results.json', 'comparison_results.csv']}, sort_keys=True))
        return 0
    except (AuditError, OSError, UnicodeError, TypeError, KeyError) as exc:
        print('AUDIT FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
