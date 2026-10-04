#!/usr/bin/env python3
"""Independent finite encodings and mutation checks, not paper benchmark trials."""
from pathlib import Path
import argparse
import copy
import hashlib
import itertools
import json


def load_program(path):
    raw = path.read_bytes()
    module = {'__name__': 'af006_independent_validation', '__file__': str(path)}
    exec(compile(raw, str(path), 'exec'), module)
    return module


def independent_modal():
    counts = {'C01': 0, 'C02': 0, 'C03': 0}
    failures = {'C01': 0, 'C02': 0, 'C03': 0}
    # Independent integer adjacency/valuation masks, not functions from the SUT.
    for matrix in range(16):
        for valuation in range(4):
            for world in range(2):
                successors = (matrix >> (2 * world)) & 3
                box_p = (successors & (~valuation & 3)) == 0
                if (matrix & 9) == 9:
                    counts['C02'] += 1
                    failures['C02'] += int(box_p and not (valuation & (1 << world)))
                if matrix & 3 and matrix & 12:
                    counts['C03'] += 1
                    failures['C03'] += int(box_p and not (successors & valuation))
                for qval in range(4):
                    implication_mask = (~valuation | qval) & 3
                    antecedent = (successors & (~implication_mask & 3)) == 0
                    box_q = (successors & (~qval & 3)) == 0
                    counts['C01'] += 1
                    failures['C01'] += int(antecedent and box_p and not box_q)
    return counts, failures


def independent_until():
    rows = []
    for p_mask in range(8):
        for q_mask in range(8):
            p = [bool(p_mask & (1 << i)) for i in range(3)]
            q = [bool(q_mask & (1 << i)) for i in range(3)]
            # Reverse recurrence U_i = q_i or (p_i and U_(i+1)); U_3=False.
            state = False
            for i in (2, 1, 0):
                state = q[i] or (p[i] and state)
            conjunction = p[0] and q[0]
            if state != conjunction:
                rows.append({'p': p, 'q': q, 'strong_until': state,
                             'conjunction_at_zero': conjunction})
    return rows


def validate(root):
    program = root / 'papers/completion/autoformalization/evaluation/reference_semantics.py'
    previous = root / 'papers/completion/autoformalization/receipts/snapshots/AF-006/computed-outcome-correction/previous-receipt.json'
    assert hashlib.sha256(previous.read_bytes()).hexdigest() == '870736eef0e2058edbec2c6fc5eae9b67e2450e32419157159206ff3dac69180'
    historical = json.loads(previous.read_text())
    for path, digest in historical['artifacts'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
    pairs_path = root / 'papers/completion/autoformalization/data/minimal_pairs.jsonl'
    assert hashlib.sha256(pairs_path.read_bytes()).hexdigest() == '7c7ad5f7ce7da2fda456982e903fe9a5e819fe54d354fac880362dbccb4a0a30'
    pairs = [json.loads(line) for line in pairs_path.read_text().splitlines() if line]
    assert len(pairs) == 12 and len({p['family_id'] for p in pairs}) == 12
    assert all(set(p['pair']) == {'supported', 'unsupported'} and p['witness'] and
               set(p['expected_supported_unsupported_behavior']) == {'supported', 'unsupported'} for p in pairs)
    provenance = json.loads((root / 'papers/completion/autoformalization/evidence/reference_provenance.json').read_text())
    assert provenance['historical_record']['status'] == 'reported_in_manuscript_but_program_and_result_not_recovered'
    assert provenance['new_reconstruction']['implementation']['sha256'] == hashlib.sha256(program.read_bytes()).hexdigest()
    module = load_program(program)
    result = module['evaluate_suite']()
    indexed = {row['check_id']: row for row in result['checks']}
    counts, failures = independent_modal()
    assert counts == {'C01': 512, 'C02': 32, 'C03': 72}
    assert failures == {'C01': 0, 'C02': 0, 'C03': 0}
    for cid in counts:
        assert indexed[cid]['case_count'] == counts[cid]
        assert indexed[cid]['actual_output']['counterexample_count'] == failures[cid]
    assert indexed['C03']['actual_output']['duality_failure_count'] == 0
    until = independent_until()
    assert len(until) == 26
    canonical = lambda rows: sorted(json.dumps(r, sort_keys=True) for r in rows)
    assert canonical(until) == canonical(indexed['C06']['actual_output']['disagreements'])
    assert indexed['C06']['case_count'] == 64
    assert sum(row['strong_until'] for row in until) == 26
    for cid in ('C04', 'C05'):
        observed = indexed[cid]['actual_output']
        witness = observed['witness']
        targets = {v for u, v in witness['relation'] if u == witness['actual_world']}
        truth = set(witness['p'])
        assert targets <= truth and witness['actual_world'] not in truth
        assert observed['modal_truth'] is True and observed['actual_truth'] is False
        assert observed['separates'] is True
    observed = indexed['C07']['actual_output']
    assert observed['trace_p'][0] is True and False in observed['trace_p']
    assert observed['always_truth'] is False and observed['separates'] is True
    observed = indexed['C08']['actual_output']
    domain = set(observed['witness']['domain'])
    rows = {x: {y for a, y in observed['witness']['relation'] if a == x} for x in domain}
    assert all(rows.values()) and not set.intersection(*rows.values())
    assert observed['for_all_exists'] is True and observed['exists_for_all'] is False
    observed = indexed['C09']['actual_output']
    expected_write = [case['write'] and case['approved'] is False for case in observed['cases']]
    assert len(expected_write) == 4 and sum(expected_write) == 1
    assert observed['violation_flags'] == expected_write
    assert observed['safe_relation_violation_count'] == 0
    assert observed['unsafe_relation_violation_count'] == 1
    observed = indexed['C10']['actual_output']
    # Binary1110 in request/complete/write/audit order is the sole violation.
    assert observed['violating_assignments'] == [dict(zip(
        ('request_observed', 'window_complete', 'write', 'audit'), (True, True, True, False)))]
    assert observed['violation_count'] == 1
    observed = indexed['C11']['actual_output']
    assert observed['cases'][0]['capture_complete'] is False
    assert observed['cases'][1]['policy_identity'] != observed['cases'][1]['trace_identity']
    assert observed['cases'][2]['capture_complete'] and observed['cases'][2]['audit_observed']
    assert observed['status_sequence'] == ['unknown', 'unresolved_identity', 'satisfied_within_observed_window']
    observed = indexed['C12']['actual_output']
    assert observed['original_source']['exception'] == 'exempt'
    assert 'exception' not in observed['first_ir']
    assert observed['first_ir'] == observed['recompiled_ir']
    independently_unequal = [dict(exempt=e, obligation_holds=o, source_truth=e or o, round_trip_truth=o)
                            for e, o in itertools.product((False, True), repeat=2) if (e or o) != o]
    assert observed['meaning_counterexamples'] == independently_unequal
    assert observed['meaning_disagreement_count'] == 1
    assert observed['source_meaning_equal'] is False
    assert result['summary']['case_counts'] == [512, 32, 72, 1, 1, 64, 1, 1, 4, 16, 3, 1]
    persisted = json.loads((program.parent / 'reference_results.json').read_text())
    assert persisted == json.loads(json.dumps(result))

    # Each mutation changes executed semantic behavior, not a status/expected flag.
    mutants = [
        ('material_implication_replaced_by_and', 'implication', lambda l, r: l and r, {'C01'}),
        ('box_always_true', 'box', lambda *a: True, {'C02', 'C03'}),
        ('diamond_always_false', 'diamond', lambda *a: False, {'C03'}),
        ('modal_witness_actual_truth_added', 'MODAL_WITNESS_VALUATION', frozenset({0, 1}), {'C04', 'C05'}),
        ('until_replaced_by_current_conjunction', 'strong_until', lambda p, q: p[0] and q[0], {'C06'}),
        ('always_replaced_by_current_truth', 'always', lambda t: t[0], {'C07'}),
        ('quantifier_order_swapped', 'quantified_values', lambda d, r: tuple(reversed(module['quantified_values'](d, r))), {'C08'}),
        ('write_violations_suppressed', 'write_violation', lambda *a: False, {'C09'}),
        ('audit_violations_suppressed', 'audit_violation', lambda **kw: False, {'C10'}),
        ('incomplete_and_identity_checks_ignored', 'trace_status', lambda c: 'satisfied_within_observed_window', {'C11'}),
        ('encoder_retains_exception_so_loss_witness_disappears', 'encode_norm', dict, {'C12'}),
        ('valuation_enumeration_truncated', 'valuations', lambda: iter((frozenset(),)), {'C01', 'C02', 'C03'}),
    ]
    mutation_results = []
    for name, symbol, replacement, required in mutants:
        mutant = load_program(program)
        # audit_violation is invoked with both keyword and positional forms.
        if symbol == 'audit_violation':
            replacement = lambda *a, **kw: False
        mutant[symbol] = replacement
        observation = mutant['evaluate_suite'](strict=False)
        failed = set(observation['summary']['failed_check_ids'])
        assert required <= failed, (name, required, failed)
        assert observation['summary']['all_expected_outcomes_matched'] is False
        try:
            mutant['evaluate_suite']()
        except AssertionError:
            raised = True
        else:
            raised = False
        assert raised, name
        mutation_results.append({'mutation': name, 'failed_check_ids': sorted(failed), 'strict_evaluation_rejected': raised})
    # Changing only an expectation must not change a computed observation.
    changed_expected = load_program(program)
    changed_expected['EXPECTED_VALUES'] = copy.deepcopy(changed_expected['EXPECTED_VALUES'])
    changed_expected['EXPECTED_VALUES']['C01']['counterexample_count'] = 1
    actual = changed_expected['evaluate_suite'](strict=False)
    assert actual['checks'][0]['actual_output']['counterexample_count'] == 0
    assert actual['checks'][0]['match'] is False
    return {'validation': 'passed', 'source_sha256': hashlib.sha256(program.read_bytes()).hexdigest(),
            'finite_case_counts': counts, 'independent_until_disagreements': len(until),
            'independent_until_trace_pairs': 64, 'full_inventory': list(indexed),
            'negative_mutations': mutation_results, 'expectation_echo_negative_rejected': True,
            'scope': 'new finite reconstruction and measurement-integrity checks only; no empirical benchmark or historical run'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(validate(args.root.resolve()), indent=2, sort_keys=True))
