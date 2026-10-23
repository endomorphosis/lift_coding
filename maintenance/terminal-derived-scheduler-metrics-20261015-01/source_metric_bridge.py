"""Derive both numeric interpretations from observed rows, never caller metrics."""
from copy import deepcopy
from fractions import Fraction
import math

from jsonl_io import wire, sha
from observed_files import decode_file, validate_bundle, compare_bundles
from strict_jsonl import parse_jsonl
from file_model_bridge import build_file_model

SOURCE_PATH = 'llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py'
CLAIMS = {key: False for key in (
    'source_body_execution', 'source_runtime_equivalence_proved', 'AST_lowering_equivalence_proved',
    'binary64_shadow_is_runtime_measurement', 'binary64_shadow_kernel_verified',
    'original_task_satisfaction', 'training_convergence_proved', 'execution_authority',
    'proof_authority', 'file_observations_authenticated')}


class DerivedMetricModelError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise DerivedMetricModelError(message)


def _fraction(value):
    _need(type(value) is dict and {'numerator', 'denominator'} <= set(value)
          and type(value['numerator']) is int and type(value['denominator']) is int
          and value['numerator'] >= 0 and value['denominator'] > 0, 'nonnegative exact metric fraction required')
    return Fraction(value['numerator'], value['denominator'])


def binary64_threshold_gate(contract, derivations):
    """A source-expression shadow cross-check, not runtime or kernel evidence."""
    clauses = [clause for clause in contract['clauses'] if clause['kind'] == 'thresholds']
    _need(len(clauses) == 2, 'exact two original candidate threshold clauses required')
    checks = []
    for clause in sorted(clauses, key=lambda row: row['parameters']['bucket_id']):
        bucket = clause['parameters']['bucket_id']
        _need(bucket in (1, 2), 'candidate threshold bucket is outside the file profile')
        derived = derivations[str(bucket)]
        for name, threshold in sorted(clause['parameters']['metrics'].items()):
            item = derived['binary64_metrics'][name]
            floating = float.fromhex(item['hex'])
            _need(math.isfinite(floating) and floating >= 0
                  and Fraction(floating) == _fraction(item), 'exact finite binary64 shadow binding required')
            bound = float(threshold['lexeme'])
            _need(math.isfinite(bound) and bound > 0, 'finite positive threshold literal required')
            rational_passed = _fraction(derived['exact_rational_metrics'][name]) < _fraction(threshold)
            shadow_passed = Fraction(floating) < Fraction(bound)
            checks.append({'bucket_id': bucket, 'metric': name,
                'rational_threshold_passed': rational_passed, 'binary64_threshold_passed': shadow_passed,
                'interpretations_agree': rational_passed == shadow_passed,
                'binary64_threshold_hex': bound.hex(),
                'binary64_threshold_ratio': {'numerator': Fraction(bound).numerator,
                                             'denominator': Fraction(bound).denominator}})
    return {'schema': 'terminal-source-metric-binary64-shadow-gate@1', 'checks': checks,
        'all_thresholds_passed': all(check['binary64_threshold_passed'] for check in checks),
        'all_threshold_interpretations_agree': all(check['interpretations_agree'] for check in checks),
        'source_execution_or_kernel_proof': False}


def build_derived_file_model(*, contract, source_profile, source_raw, before, after, case_id):
    from source_profile import validate_source_profile
    from source_metrics import derive_metrics
    validate_source_profile(source_profile, raw=source_raw, source_path=SOURCE_PATH, head=contract['head'])
    validate_bundle(before)
    validate_bundle(after)
    comparison = compare_bundles(before, after)
    _need(all(comparison.get(key) is True for key in (
        'roots_equal', 'directory_generations_equal', 'unchanged_inputs', 'same_file_generations')),
        'current stable four-file observation bracket required before metric derivation')
    derivations = {}
    for bucket in (1, 2):
        requests = parse_jsonl(decode_file(after, 'input_data/requests_bucket_' + str(bucket) + '.jsonl'),
                               kind='requests')['rows']
        plan = parse_jsonl(decode_file(after, 'output_data/plan_b' + str(bucket) + '.jsonl'), kind='plan')['rows']
        derivations[str(bucket)] = derive_metrics(source_profile=source_profile, requests=requests, plan=plan)
    metrics = {bucket: deepcopy(value['exact_rational_metrics']) for bucket, value in derivations.items()}
    for values in metrics.values():
        for item in values.values():
            _need(item['numerator'] <= 10**18 and item['denominator'] <= 10**18,
                  'derived metric exceeds the existing bounded rational model; no clipping permitted')
    model = build_file_model(contract=contract, before=before, after=after, metrics=metrics, case_id=case_id)
    gate = binary64_threshold_gate(contract, derivations)
    return {'schema': 'terminal-source-derived-file-metric-model@1', 'case_id': case_id,
        'source_profile_sha256': sha(wire(source_profile)), 'head': deepcopy(contract['head']),
        'contract_sha256': sha(wire(contract)), 'before_sha256': sha(wire(before)), 'after_sha256': sha(wire(after)),
        'derivations': derivations, 'derived_metrics': metrics, 'file_model': model, 'binary64_gate': gate,
        'rational_model_passed': model['evaluation']['evaluation_passed'],
        'accepted': model['evaluation']['evaluation_passed'] and gate['all_thresholds_passed'],
        'caller_supplied_metrics_accepted': False, 'claims': dict(CLAIMS)}


def validate_derived_file_model(report, *, contract, source_profile, source_raw, before, after, case_id):
    expected = build_derived_file_model(contract=contract, source_profile=source_profile, source_raw=source_raw,
                                      before=before, after=after, case_id=case_id)
    _need(wire(report) == wire(expected), 'derived metrics, exact file rows, shadow or source binding changed')
    return report
